import streamlit as st
import pandas as pd
from datetime import datetime
import paho.mqtt.client as mqtt
import os
import json

st.set_page_config(page_title="SaaS OEE - Andón MQTT", layout="wide")

# =========================================================================
# CONTENEDOR GLOBAL EN MEMORIA (Compartido entre todas las pestañas de la planta)
# =========================================================================
@st.cache_resource
def obtener_estado_global():
    return {
        "DEMOWIDEM 1 (Inyectora)": {"Buenas": 0, "Meta": 60, "Estado": "PRODUCIENDO", "Ultimo": "Esperando primer golpe..."},
        "DEMOWIDEM 2 (Banco Manual)": {"Buenas": 0, "Meta": 40, "Estado": "SETUP", "Ultimo": "Sin eventos"},
        "DEMOWIDEM 3 (Prensa)": {"Buenas": 0, "Meta": 80, "Estado": "PARADA", "Ultimo": "Sin eventos"}
    }

estado_planta = obtener_estado_global()

# =========================================================================
# CLIENTE MQTT EN SEGUNDO PLANO (Conexión persistente a HiveMQ)
# =========================================================================
@st.cache_resource
def iniciar_escucha_hivemq():
    # Sacamos las credenciales desde los Secrets de Streamlit
    broker = st.secrets["MQTT_BROKER"] # Ej: xxxxx.s1.eu.hivemq.cloud
    user = st.secrets["MQTT_USER"]
    password = st.secrets["MQTT_PASS"]
    
    cliente = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    cliente.username_pw_set(user, password)
    
    def on_message(client, userdata, msg):
        payload = msg.payload.decode("utf-8") # Va a recibir "M1"
        ahora_str = datetime.now().strftime("%H:%M:%S")
        
        if payload == "M1":
            estado_planta["DEMOWIDEM 1 (Inyectora)"]["Buenas"] += 1
            estado_planta["DEMOWIDEM 1 (Inyectora)"]["Ultimo"] = f"Golpe detectado por ESP32 a las {ahora_str}"
        elif payload == "M2":
            estado_planta["DEMOWIDEM 2 (Banco Manual)"]["Buenas"] += 1
            estado_planta["DEMOWIDEM 2 (Banco Manual)"]["Ultimo"] = f"Golpe detectado por ESP32 a las {ahora_str}"
        elif payload == "M3":
            estado_planta["DEMOWIDEM 3 (Prensa)"]["Buenas"] += 1
            estado_planta["DEMOWIDEM 3 (Prensa)"]["Ultimo"] = f"Golpe detectado por ESP32 a las {ahora_str}"

    cliente.on_message = on_message
    cliente.tls_set() # Obligatorio para HiveMQ Cloud (SSL puerto 8883)
    
    try:
        cliente.connect(broker, 8883)
        cliente.subscribe("planta/golpes")
        cliente.loop_start() # Levanta el hilo en segundo plano de manera limpia
    except Exception as e:
        print(f"Error conectando a HiveMQ: {e}")
        
    return cliente

# Lanzamos el proceso de escucha de HiveMQ una sola vez
mqtt_client = iniciar_escucha_hivemq()

# =========================================================================
# INTERFAZ GRÁFICA DEL ANDÓN (Capa 7)
# =========================================================================
st.markdown("""
<style>
    .stApp { background-color: #0d1117; color: #ffffff; }
    .andon-card { border-radius: 8px; padding: 20px; margin-bottom: 15px; border: 1px solid #30363d; font-family: monospace; }
    .andon-marcha { background-color: #0c2519; border-left: 8px solid #00cc66; }
    .andon-setup { background-color: #2b220c; border-left: 8px solid #ffaa00; }
    .andon-parada { background-color: #2d1215; border-left: 8px solid #ff4b4b; }
</style>
""", unsafe_allow_html=True)

st.title("🚨 Monitor Andón de Planta - Conectado vía HiveMQ Cloud")

# Renderizado de las 3 celdas
cols = st.columns(3)
for i, (maq, datos) in enumerate(estado_planta.items()):
    clase = "andon-marcha" if datos["Estado"] == "PRODUCIENDO" else ("andon-setup" if datos["Estado"] == "SETUP" else "andon-parada")
    
    html_code = f"""
    <div class="andon-card {clase}">
        <h3>{maq}</h3>
        <p><b>ESTADO TR:</b> {datos['Estado']}</p>
        <hr style='border-color:#30363d;'>
        <h1 style='color:#00f2fe; margin:0;'>{datos['Buenas']} pz</h1>
        <p style='color:#8b949e; font-size:12px;'>Meta Base Hora: {datos['Meta']} pz</p>
        <p style='color:#ffaa00; font-size:11px; margin-top:10px;'>📡 {datos['Ultimo']}</p>
    </div>
    """
    with cols[i]:
        st.markdown(html_code, unsafe_allow_html=True)

# Refresco automático de la UI cada 2 segundos sin romper el DOM
st.ipc_handler = """
<script>
    if (!window.andonInterval) {
        window.andonInterval = setInterval(function() {
            var btn = window.parent.document.querySelector('button[title="Refresh"]');
            if (btn) btn.click();
        }, 2000);
    }
</script>
"""
st.markdown(st.ipc_handler, unsafe_allow_html=True)