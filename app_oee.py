import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os  # Manejo del archivo de golpes en disco

# 1. CONFIGURACIÓN DE PANTALLA (Debe ser la primera directiva de Streamlit)
st.set_page_config(page_title="SaaS OEE - Core Global de Planta", layout="wide")

# Definimos las claves para conectar a la nube
mqtt_user = st.secrets["MQTT_USER"]
mqtt_pass = st.secrets["MQTT_PASS"]

# =========================================================================
# MOTOR DE ESTILOS CSS PREMIUM (DARK MODE + TARJETAS ANDÓN INDUSTRIALES)
# =========================================================================
st.markdown("""
    <style>
    /* Estructura general */
    .stApp { background-color: #0d1117; color: #ffffff; }
    div[data-testid="stMetricValue"] { font-size: 32px; font-weight: bold; color: #00f2fe; }
    .kpi-title { font-size: 14px; color: #8b949e; font-weight: bold; text-align: left; margin-bottom: 12px; font-family: monospace; }
    .gauge-title { text-align: center; font-size: 15px; font-weight: bold; color: #8b949e; margin-bottom: -10px; font-family: monospace; }
    div[data-testid="stMetricLabel"] { font-size: 16px !important; font-weight: bold !important; color: #8b949e !important; }
    
    /* Tarjetas tipo Vorne */
    .vorne-card { background-color: #161b22; border-radius: 8px; border: 1px solid #30363d; color: white; padding: 20px; margin: 10px; font-family: sans-serif; }
    .vorne-header { padding: 10px; font-size: 16px; font-weight: bold; border-radius: 4px; margin-bottom: 15px; color: white; }
    
    /* Botones de analítica */
    .stButton > button {
        width: 100%; background-color: #161b22; color: #c9d1d9; border: 1px solid #30363d;
        padding: 10px; border-radius: 6px; font-weight: bold; transition: all 0.3s ease;
    }
    .stButton > button:hover { border-color: #00f2fe; color: #00f2fe; background-color: #1f242c; }
    
    /* Contenedores del Andón Digital Profesional */
    .andon-card { border-