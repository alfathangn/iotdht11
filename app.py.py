# app_streamlit.py
import streamlit as st
import paho.mqtt.client as mqtt
import json
import time
import threading
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import ssl

# Page configuration
st.set_page_config(
    page_title="Dashboard Monitoring Suhu DHT22",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #4361ee;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        padding: 20px;
        color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .status-indicator {
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        margin-right: 8px;
    }
    .status-connected {
        background-color: #4cc9f0;
        box-shadow: 0 0 10px #4cc9f0;
    }
    .status-disconnected {
        background-color: #f72585;
        box-shadow: 0 0 10px #f72585;
    }
    .led-indicator {
        width: 20px;
        height: 20px;
        border-radius: 50%;
        display: inline-block;
        margin: 0 5px;
        box-shadow: 0 0 10px rgba(0,0,0,0.2);
    }
    .led-off {
        background-color: #cccccc;
    }
    .led-red {
        background-color: #f72585;
        box-shadow: 0 0 15px #f72585;
    }
    .led-green {
        background-color: #4cc9f0;
        box-shadow: 0 0 15px #4cc9f0;
    }
    .led-yellow {
        background-color: #f8961e;
        box-shadow: 0 0 15px #f8961e;
    }
</style>
""", unsafe_allow_html=True)

# MQTT Configuration
MQTT_CONFIG = {
    'broker': "f67e6c21fe35482f81f17e93855110a4.s1.eu.hivemq.cloud",
    'port': 8883,
    'username': "hivemq.webclient.1764927232479",
    'password': "D7165is;l@CYrUZmM>&h",
    'pub_topic': "sic/dibimbing/kelompok-SENSOR/FARIZ/pub/dht",
    'sub_topic': "sic/dibimbing/kelompok-SENSOR/FARIZ/sub/led"
}

# Initialize session state for data storage
if 'sensor_data' not in st.session_state:
    st.session_state.sensor_data = {
        'temperature': 24.0,
        'humidity': 65.0,
        'status': 'Normal',
        'timestamp': datetime.now().strftime('%H:%M:%S'),
        'led_states': {'LED_MERAH': False, 'LED_HIJAU': True, 'LED_KUNING': False},
        'led_status': 'LED Hijau Menyala',
        'history': [],
        'mqtt_connected': False,
        'last_update': datetime.now()
    }

if 'temperature_history' not in st.session_state:
    st.session_state.temperature_history = []
if 'humidity_history' not in st.session_state:
    st.session_state.humidity_history = []
if 'time_history' not in st.session_state:
    st.session_state.time_history = []

# MQTT Client Setup
def setup_mqtt_client():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(MQTT_CONFIG['username'], MQTT_CONFIG['password'])
    
    # Disable SSL verification for development
    client.tls_set(tls_version=ssl.PROTOCOL_TLS)
    client.tls_insecure_set(True)
    
    def on_connect(client, userdata, flags, rc, properties=None):
        if rc == 0:
            st.session_state.sensor_data['mqtt_connected'] = True
            client.subscribe(MQTT_CONFIG['pub_topic'])
            client.subscribe(MQTT_CONFIG['sub_topic'])
            st.success("✅ Terhubung ke MQTT Broker!")
        else:
            st.session_state.sensor_data['mqtt_connected'] = False
            st.error(f"❌ Gagal koneksi MQTT: {rc}")
    
    def on_disconnect(client, userdata, rc, properties=None):
        st.session_state.sensor_data['mqtt_connected'] = False
        st.warning("⚠️ Terputus dari MQTT Broker")
    
    def on_message(client, userdata, msg):
        try:
            payload = msg.payload.decode()
            
            if msg.topic == MQTT_CONFIG['pub_topic']:
                data = json.loads(payload)
                
                temperature = float(data.get('temperature', 24.0))
                humidity = float(data.get('humidity', 65.0))
                
                # Determine status
                if temperature < 22:
                    status = 'Dingin'
                    led_states = {'LED_MERAH': False, 'LED_HIJAU': False, 'LED_KUNING': True}
                    led_status = 'LED Kuning Menyala'
                elif temperature > 25:
                    status = 'Panas'
                    led_states = {'LED_MERAH': True, 'LED_HIJAU': False, 'LED_KUNING': False}
                    led_status = 'LED Merah Menyala'
                else:
                    status = 'Normal'
                    led_states = {'LED_MERAH': False, 'LED_HIJAU': True, 'LED_KUNING': False}
                    led_status = 'LED Hijau Menyala'
                
                # Update session state
                st.session_state.sensor_data.update({
                    'temperature': temperature,
                    'humidity': humidity,
                    'status': status,
                    'timestamp': datetime.now().strftime('%H:%M:%S'),
                    'led_states': led_states,
                    'led_status': led_status,
                    'last_update': datetime.now()
                })
                
                # Add to history
                st.session_state.temperature_history.append(temperature)
                st.session_state.humidity_history.append(humidity)
                st.session_state.time_history.append(datetime.now().strftime('%H:%M:%S'))
                
                # Keep only last 50 readings
                if len(st.session_state.temperature_history) > 50:
                    st.session_state.temperature_history.pop(0)
                    st.session_state.humidity_history.pop(0)
                    st.session_state.time_history.pop(0)
                
            elif msg.topic == MQTT_CONFIG['sub_topic']:
                # Update LED states based on control messages
                payload_lower = payload.lower()
                
                if payload_lower == 'merah':
                    st.session_state.sensor_data['led_states'] = {'LED_MERAH': True, 'LED_HIJAU': False, 'LED_KUNING': False}
                    st.session_state.sensor_data['led_status'] = 'LED Merah Menyala'
                elif payload_lower == 'hijau':
                    st.session_state.sensor_data['led_states'] = {'LED_MERAH': False, 'LED_HIJAU': True, 'LED_KUNING': False}
                    st.session_state.sensor_data['led_status'] = 'LED Hijau Menyala'
                elif payload_lower == 'kuning':
                    st.session_state.sensor_data['led_states'] = {'LED_MERAH': False, 'LED_HIJAU': False, 'LED_KUNING': True}
                    st.session_state.sensor_data['led_status'] = 'LED Kuning Menyala'
                elif payload_lower == 'off':
                    st.session_state.sensor_data['led_states'] = {'LED_MERAH': False, 'LED_HIJAU': False, 'LED_KUNING': False}
                    st.session_state.sensor_data['led_status'] = 'Semua LED Mati'
                    
        except Exception as e:
            st.error(f"Error processing message: {e}")
    
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    
    return client

# Function to control LEDs
def control_led(led, action):
    if st.session_state.sensor_data['mqtt_connected']:
        try:
            mqtt_client = st.session_state.get('mqtt_client')
            if action == 'on':
                if led == 'LED_MERAH':
                    mqtt_client.publish(MQTT_CONFIG['sub_topic'], 'merah')
                elif led == 'LED_HIJAU':
                    mqtt_client.publish(MQTT_CONFIG['sub_topic'], 'hijau')
                elif led == 'LED_KUNING':
                    mqtt_client.publish(MQTT_CONFIG['sub_topic'], 'kuning')
            elif action == 'off':
                mqtt_client.publish(MQTT_CONFIG['sub_topic'], 'off')
            
            st.success(f"✅ Perintah dikirim: {led} -> {action}")
            return True
        except Exception as e:
            st.error(f"❌ Gagal mengirim perintah: {e}")
            return False
    else:
        st.warning("⚠️ Tidak terkoneksi ke MQTT")
        return False

# Sidebar for controls
with st.sidebar:
    st.markdown("## ⚙️ Kontrol Dashboard")
    
    # Connection Status
    st.markdown("### 🔗 Status Koneksi")
    if st.session_state.sensor_data['mqtt_connected']:
        st.markdown('<span class="status-indicator status-connected"></span> Terhubung ke MQTT', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-indicator status-disconnected"></span> Terputus dari MQTT', unsafe_allow_html=True)
    
    # Manual Data Input (for testing)
    st.markdown("### 🎮 Input Manual (Testing)")
    col1, col2 = st.columns(2)
    with col1:
        manual_temp = st.number_input("Suhu (°C)", value=24.0, min_value=0.0, max_value=50.0, step=0.1)
    with col2:
        manual_hum = st.number_input("Kelembaban (%)", value=65.0, min_value=0.0, max_value=100.0, step=0.1)
    
    if st.button("Simpan Data Manual", type="secondary"):
        st.session_state.sensor_data.update({
            'temperature': manual_temp,
            'humidity': manual_hum,
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'last_update': datetime.now()
        })
        st.rerun()
    
    # LED Controls
    st.markdown("### 💡 Kontrol LED")
    
    st.markdown("**LED Individual:**")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔴 LED Merah ON", use_container_width=True):
            control_led('LED_MERAH', 'on')
        if st.button("🟢 LED Hijau ON", use_container_width=True):
            control_led('LED_HIJAU', 'on')
        if st.button("🟡 LED Kuning ON", use_container_width=True):
            control_led('LED_KUNING', 'on')
    with col2:
        if st.button("LED Merah OFF", use_container_width=True, type="secondary"):
            control_led('LED_MERAH', 'off')
        if st.button("LED Hijau OFF", use_container_width=True, type="secondary"):
            control_led('LED_HIJAU', 'off')
        if st.button("LED Kuning OFF", use_container_width=True, type="secondary"):
            control_led('LED_KUNING', 'off')
    
    st.markdown("**Kontrol Semua:**")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🎯 ALL ON", use_container_width=True, type="primary"):
            for led in ['LED_MERAH', 'LED_HIJAU', 'LED_KUNING']:
                control_led(led, 'on')
    with col2:
        if st.button("🚫 ALL OFF", use_container_width=True, type="secondary"):
            control_led('LED_MERAH', 'off')
    
    # Clear History
    if st.button("🗑️ Hapus Riwayat", type="secondary"):
        st.session_state.temperature_history.clear()
        st.session_state.humidity_history.clear()
        st.session_state.time_history.clear()
        st.success("Riwayat data telah dihapus!")
        st.rerun()

# Main Dashboard
st.markdown('<h1 class="main-header">🌡️ Dashboard Monitoring Suhu DHT22</h1>', unsafe_allow_html=True)

# Row 1: Metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    with st.container():
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric(
            label="🌡️ Suhu",
            value=f"{st.session_state.sensor_data['temperature']:.1f}°C",
            delta=None
        )
        status_color = {
            'Dingin': '🟦',
            'Normal': '🟩', 
            'Panas': '🟥'
        }.get(st.session_state.sensor_data['status'], '⚪')
        st.caption(f"{status_color} Status: {st.session_state.sensor_data['status']}")
        st.markdown('</div>', unsafe_allow_html=True)

with col2:
    with st.container():
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric(
            label="💧 Kelembaban",
            value=f"{st.session_state.sensor_data['humidity']:.1f}%",
            delta=None
        )
        # Progress bar for humidity
        progress = min(st.session_state.sensor_data['humidity'] / 100, 1.0)
        st.progress(progress)
        st.markdown('</div>', unsafe_allow_html=True)

with col3:
    with st.container():
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric(
            label="🕒 Update Terakhir",
            value=st.session_state.sensor_data['timestamp'],
            delta=None
        )
        elapsed = (datetime.now() - st.session_state.sensor_data['last_update']).seconds
        st.caption(f"⏱️ {elapsed} detik yang lalu")
        st.markdown('</div>', unsafe_allow_html=True)

with col4:
    with st.container():
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("### 💡 Status LED")
        
        led_states = st.session_state.sensor_data['led_states']
        led_html = ""
        if led_states['LED_MERAH']:
            led_html += '<span class="led-indicator led-red"></span>'
        else:
            led_html += '<span class="led-indicator led-off"></span>'
        
        if led_states['LED_HIJAU']:
            led_html += '<span class="led-indicator led-green"></span>'
        else:
            led_html += '<span class="led-indicator led-off"></span>'
        
        if led_states['LED_KUNING']:
            led_html += '<span class="led-indicator led-yellow"></span>'
        else:
            led_html += '<span class="led-indicator led-off"></span>'
        
        st.markdown(led_html, unsafe_allow_html=True)
        st.caption(st.session_state.sensor_data['led_status'])
        st.markdown('</div>', unsafe_allow_html=True)

# Row 2: Charts
st.markdown("## 📈 Grafik Monitoring")

# Create tabs for different charts
tab1, tab2, tab3 = st.tabs(["📊 Grafik Suhu", "💧 Grafik Kelembaban", "📋 Data Riwayat"])

with tab1:
    if st.session_state.time_history:
        fig_temp = go.Figure()
        fig_temp.add_trace(go.Scatter(
            x=st.session_state.time_history,
            y=st.session_state.temperature_history,
            mode='lines+markers',
            name='Suhu',
            line=dict(color='#4361ee', width=3),
            marker=dict(size=8)
        ))
        
        # Add threshold lines
        fig_temp.add_hline(y=22, line_dash="dash", line_color="blue", annotation_text="Bawah Normal")
        fig_temp.add_hline(y=25, line_dash="dash", line_color="red", annotation_text="Atas Normal")
        
        fig_temp.update_layout(
            title='Riwayat Suhu (°C)',
            xaxis_title='Waktu',
            yaxis_title='Suhu (°C)',
            template='plotly_white',
            height=400
        )
        st.plotly_chart(fig_temp, use_container_width=True)
    else:
        st.info("⏳ Menunggu data sensor...")

with tab2:
    if st.session_state.time_history:
        fig_hum = go.Figure()
        fig_hum.add_trace(go.Scatter(
            x=st.session_state.time_history,
            y=st.session_state.humidity_history,
            mode='lines+markers',
            name='Kelembaban',
            line=dict(color='#4cc9f0', width=3),
            marker=dict(size=8)
        ))
        
        fig_hum.update_layout(
            title='Riwayat Kelembaban (%)',
            xaxis_title='Waktu',
            yaxis_title='Kelembaban (%)',
            template='plotly_white',
            height=400
        )
        st.plotly_chart(fig_hum, use_container_width=True)
    else:
        st.info("⏳ Menunggu data sensor...")

with tab3:
    if st.session_state.time_history:
        # Create DataFrame for table view
        df = pd.DataFrame({
            'Waktu': st.session_state.time_history,
            'Suhu (°C)': st.session_state.temperature_history,
            'Kelembaban (%)': st.session_state.humidity_history
        })
        st.dataframe(df[::-1], use_container_width=True)  # Show latest first
        
        # Statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Rata-rata Suhu", f"{df['Suhu (°C)'].mean():.1f}°C")
        with col2:
            st.metric("Suhu Tertinggi", f"{df['Suhu (°C)'].max():.1f}°C")
        with col3:
            st.metric("Suhu Terendah", f"{df['Suhu (°C)'].min():.1f}°C")
    else:
        st.info("⏳ Menunggu data sensor...")

# Row 3: System Information
st.markdown("## 🖥️ Informasi Sistem")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🔧 Konfigurasi MQTT")
    st.code(f"""Broker: {MQTT_CONFIG['broker']}
Port: {MQTT_CONFIG['port']}
Username: {MQTT_CONFIG['username']}
Topic Publish: {MQTT_CONFIG['pub_topic']}
Topic Subscribe: {MQTT_CONFIG['sub_topic']}""")

with col2:
    st.markdown("### 📋 Informasi Perangkat")
    info_html = """
    <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px;">
        <p><strong>🌐 WiFi Network:</strong> Wokwi-GUEST</p>
        <p><strong>☁️ MQTT Server:</strong> HiveMQ Cloud</p>
        <p><strong>📡 Sensor:</strong> DHT22</p>
        <p><strong>🎯 Range Normal:</strong> 22°C - 25°C</p>
        <p><strong>🔌 Mikrokontroller:</strong> ESP32</p>
    </div>
    """
    st.markdown(info_html, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666;">
    <p>Sistem Monitoring Suhu DHT22 &copy; 2024 | Dibimbing IoT Project</p>
    <p>Fariz | Update Real-time via MQTT + Streamlit</p>
</div>
""", unsafe_allow_html=True)

# Auto-refresh every 2 seconds
if st.button("🔄 Refresh Data", type="secondary"):
    st.rerun()

# Add auto-refresh checkbox
auto_refresh = st.checkbox("🔄 Auto-refresh setiap 2 detik", value=True)

# MQTT Connection Management
if 'mqtt_client' not in st.session_state:
    try:
        mqtt_client = setup_mqtt_client()
        mqtt_client.connect(MQTT_CONFIG['broker'], MQTT_CONFIG['port'], 60)
        mqtt_client.loop_start()
        st.session_state.mqtt_client = mqtt_client
    except Exception as e:
        st.error(f"❌ Gagal koneksi MQTT: {e}")
        st.info("📡 Dashboard akan berjalan dengan mode simulasi")

# Auto-refresh logic
if auto_refresh:
    time.sleep(2)
    st.rerun()