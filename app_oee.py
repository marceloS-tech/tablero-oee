import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os  # <-- Importamos la librería para manejar el archivo de golpes en disco

# Definimos las claves para conectar a la nube
mqtt_user = st.secrets["MQTT_USER"]
mqtt_pass = st.secrets["MQTT_PASS"]

# Configuración de pantalla ancha para terminales industriales y Smart TVs
st.set_page_config(page_title="SaaS OEE - Core Global de Planta", layout="wide")
st.markdown("""
    <style>
    /* Estructura general */
    .stApp { background-color: #0d1117; color: #ffffff; }
    
    /* Tarjetas tipo Vorne */
    .vorne-card { background-color: #161b22; border-radius: 8px; border: 1px solid #30363d; color: white; padding: 20px; margin: 10px; font-family: sans-serif; }
    .vorne-header { padding: 10px; font-size: 16px; font-weight: bold; border-radius: 4px; margin-bottom: 15px; color: white; }
    
    /* Colores de estado */
    .bg-running { background-color: #0c2519; border-left: 8px solid #00cc66; }
    .bg-setup { background-color: #2b220c; border-left: 8px solid #ffaa00; }
    .bg-stopped { background-color: #2d1215; border-left: 8px solid #ff4b4b; }
    
    /* Valores internos */
    .vorne-main-value { font-size: 32px; font-weight: bold; margin-bottom: 5px; }
    .vorne-sub-label { font-size: 11px; color: #8b949e; text-transform: uppercase; margin-bottom: 10px; }
    .vorne-info-bar { font-size: 12px; color: #8b949e; margin-top: 15px; border-top: 1px solid #30363d; padding-top: 10px; }
    </style>
""", unsafe_allow_html=True)

if "db_objetivos" not in st.session_state:
    st.session_state.db_objetivos = {
        "DEMOWIDEM 1 (Inyectora)": {"Estado_TR": "PRODUCIENDO", "Producto": "Carcasa Plástica A", "Ultimo_Evento": "Running Normally"},
        "DEMOWIDEM 2 (Banco Manual)": {"Estado_TR": "SETUP", "Producto": "Ensamble Eléctrico B", "Ultimo_Evento": "Waiting for Materials"},
        "DEMOWIDEM 3 (Prensa)": {"Estado_TR": "PARADA", "Producto": "Soporte Metálico C", "Ultimo_Evento": "Die Change"}
    }

# =========================================================================
# MOTOR DE ESTILOS CSS PREMIUM (DARK MODE + TARJETAS ANDÓN INDUSTRIALES)
# =========================================================================
st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #ffffff; }
    div[data-testid="stMetricValue"] { font-size: 32px; font-weight: bold; color: #00f2fe; }
    .kpi-title { font-size: 14px; color: #8b949e; font-weight: bold; text-align: left; margin-bottom: 12px; font-family: monospace; }
    .gauge-title { text-align: center; font-size: 15px; font-weight: bold; color: #8b949e; margin-bottom: -10px; font-family: monospace; }
    div[data-testid="stMetricLabel"] { font-size: 16px !important; font-weight: bold !important; color: #8b949e !important; }
    
    /* Botones de analítica */
    .stButton > button {
        width: 100%; background-color: #161b22; color: #c9d1d9; border: 1px solid #30363d;
        padding: 10px; border-radius: 6px; font-weight: bold; transition: all 0.3s ease;
    }
    .stButton > button:hover { border-color: #00f2fe; color: #00f2fe; background-color: #1f242c; }
    
    /* Contenedores del Andón Digital Profesional */
    .andon-card { border-radius: 8px; padding: 20px; margin-bottom: 1