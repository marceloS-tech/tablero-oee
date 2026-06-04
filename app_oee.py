import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os

# 1. CONFIGURACIÓN DE PANTALLA PRINCIPAL (Debe ser siempre la primera directiva)
st.set_page_config(page_title="SaaS OEE - Core Global de Planta", layout="wide")

# Credenciales seguras desde los Secrets
mqtt_user = st.secrets["MQTT_USER"]
mqtt_pass = st.secrets["MQTT_PASS"]

# =========================================================================
# BLOQUES DE INYECCIÓN WEB (Estilos y Automatización de Pestañas)
# =========================================================================

ESTILOS_CSS = """
<style>
    .stApp { background-color: #0d1117; color: #ffffff; }
    div[data-testid="stMetricValue"] { font-size: 32px; font-weight: bold; color: #00f2fe; }
    .kpi-title { font-size: 14px; color: #8b949e; font-weight: bold; text-align: left; margin-bottom: 12px; font-family: monospace; }
    .gauge-title { text-align: center; font-size: 15px; font-weight: bold; color: #8b949e; margin-bottom: -10px; font-family: monospace; }
    div[data-testid="stMetricLabel"] { font-size: 16px !important; font-weight: bold !important; color: #8b949e !important; }
    
    .vorne-card { background-color: #161b22; border-radius: 8px; border: 1px solid #30363d; color: white; padding: 20px; margin: 10px; font-family: sans-serif; }
    
    .stButton > button {
        width: 100%; background-color: #161b22; color: #c9d1d9; border: 1px solid #30363d;
        padding: 10px; border-radius: 6px; font-weight: bold; transition: all 0.3s ease;
    }
    .stButton > button:hover { border-color: #00f2fe; color: #00f2fe; background-color: #1f242c; }
    
    .andon-card { border-radius: 8px; padding: 20px; margin-bottom: 15px; border: 1px solid #30363d; font-family: monospace; }
    .andon-marcha { background-color: #0c2519; border-left: 8px solid #00cc66; }
    .andon-setup { background-color: #2b220c; border-left: 8px solid #ffaa00; }
    .andon-parada { background-color: #2d1215; border-left: 8px solid #ff4b4b; }
    
    .andon-header { font-size: 22px; font-weight: bold; margin-bottom: 5px; display: flex; justify-content: space-between; align-items: center; }
    .andon-meta-box { background: #1f242c; padding: 10px; border-radius: 4px; border: 1px solid #30363d; font-size: 13px; margin-top: 12px; }
    
    .wiidem-badge { display: inline-block; padding: 4px 8px; font-weight: bold; border-radius: 4px; font-size: 12px; color: #000; margin-right: 5px; }
    .badge-v { background-color: #00cc66; }
    .badge-a { background-color: #ffaa00; }
    .badge-r { background-color: #ff4b4b; }
</style>
"""

JS_AUTOMATIZACION = """
<script>
    var index = 0;
    setInterval(function() {
        var radios = window.parent.document.querySelectorAll('input[type="radio"]');
        if (radios.length > 0) {
            index = (index + 1) % radios.length;
            radios[index].click();
        }
    }, 10000); 

    setInterval(function() {
        var reloadButton = window.parent.document.querySelector('button[title="Refresh"]');
        if (reloadButton) {
            reloadButton.click();
        }
    }, 2000); 
</script>
"""

st.markdown(ESTILOS_CSS, unsafe_allow_html=True)

# =========================================================================
# 2. CONTROL DE SESIÓN Y PARED DE LOGUEO (CORREGIDO)
# =========================================================================
st.sidebar.title("🔐 Autenticación SaaS")

CLIENTES_DB = {
    "supervisor_planta": {"pass": "123", "plan": ["Capa 1", "Capa 3", "Capa 4"]},
    "director_general": {"pass": "456", "plan": ["Capa 1", "Capa 2", "Capa 3", "Capa 4", "Capa 5", "Capa 6", "Capa 7"]},
    "puesto_planta": {"pass": "000", "plan": ["Capa 1", "Capa 7"]}
}

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "usuario_conectado" not in st.session_state:
    st.session_state.usuario_conectado = None
if "permisos_usuario" not in st.session_state:
    st.session_state.permisos_usuario = []

if not st.session_state.autenticado:
    user_input = st.sidebar.text_input("Usuario Corporativo:", key="login_user")
    pass_input = st.sidebar.text_input("Contraseña:", type="password", key="login_pass")
    
    if st.sidebar.button("Ingresar al Sistema", use_container_width=True):
        if user_input in CLIENTES_DB and CLIENTES_DB[user_input]["pass"] == pass_input:
            st.session_state.usuario_conectado = user_input
            st.session_state.permisos_usuario = CLIENTES_DB[user_input]["plan"]
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.sidebar.error("❌ Credenciales incorrectas")
            
    st.warning("🔒 Por favor introduzca sus credenciales corporativas en el menú lateral.")
    st.info("💡 Credenciales Demo: Usuario: `director_general` | Clave: `456`")

# Si aún no está autenticado tras evaluar el botón, frenamos el renderizado de las capas de fondo
if not st.session_state.autenticado:
    st.stop()

# Menú de usuario autenticado
st.sidebar.markdown(f"👤 **Usuario:** `{st.session_state.usuario_conectado}`")
if st.sidebar.button("🔴 Cerrar Sesión", use_container_width=True):
    st.session_state.autenticado = False
    st.session_state.usuario_conectado = None
    st.session_state.permisos_usuario = []
    st.rerun()

st.sidebar.markdown("---")

# =========================================================================
# 3. ARQUITECTURA DE DATOS CENTRALIZADA (Solo corre post-login)
# =========================================================================
HORAS_TURNO = ["06:00-07:00", "07:00-08:00", "08:00-09:00", "09:00-10:00", "10:00-11:00", "11:00-12:00", "12:00-13:00", "13:00-14:00"]

if "db_objetivos" not in st.session_state:
    st.session_state.db_objetivos = {
        "DEMOWIDEM 1 (Inyectora)": {"Meta_Hora": 60, "Producto": "Carcasa Plástica A", "Estado_TR": "PRODUCIENDO", "Ultimo_Evento": "Ninguno"},
        "DEMOWIDEM 2 (Banco Manual)": {"Meta_Hora": 40, "Producto": "Ensamble Eléctrico B", "Estado_TR": "SETUP", "Ultimo_Evento": "Logística: Falta Piezas"},
        "DEMOWIDEM 3 (Prensa)": {"Meta_Hora": 80, "Producto": "Soporte Metálico C", "Estado_TR": "PARADA", "Ultimo_Evento": "Mantenimiento: Falla Mecánica"}
    }

if "db_historial_planta" not in st.session_state:
    st.session_state.db_historial_planta = pd.DataFrame([
        {"Hora": "06:00-07:00", "Maquina": "DEMOWIDEM 1 (Inyectora)", "Tipo": "Automático", "Operario": "VILLARROEL ENZO", "Meta": 60, "Buenas": 58, "Retrabajo": 1, "Observadas": 1, "Min_Parada": 0, "Falla": "Ninguna", "Es_Falla_Tecnica": False, "Validado": True},
        {"Hora": "07:00-08:00", "Maquina": "DEMOWIDEM 1 (Inyectora)", "Tipo": "Automático", "Operario": "VILLARROEL ENZO", "Meta": 60, "Buenas": 59, "Retrabajo": 0, "Observadas": 1, "Min_Parada": 0, "Falla": "Ninguna", "Es_Falla_Tecnica": False, "Validado": True},
        {"Hora": "08:00-09:00", "Maquina": "DEMOWIDEM 1 (Inyectora)", "Tipo": "Automático", "Operario": "VILLARROEL ENZO", "Meta": 60, "Buenas": 38, "Retrabajo": 2, "Observadas": 0, "Min_Parada": 15, "Falla": "Falla Robótica", "Es_Falla_Tecnica": True, "Validado": False},
        {"Hora": "06:00-07:00", "Maquina": "DEMOWIDEM 2 (Banco Manual)", "Tipo": "Manual", "Operario": "FRANCO MAXIMILIANO", "Meta": 40, "Buenas": 35, "Retrabajo": 2, "Observadas": 1, "Min_Parada": 5, "Falla": "Ajuste de Banco", "Es_Falla_Tecnica": False, "Validado": True},
        {"Hora": "07:00-08:00", "Maquina": "DEMOWIDEM 2 (Banco Manual)", "Tipo": "Manual", "Operario": "FRANCO MAXIMILIANO", "Meta": 40, "Buenas": 18, "Retrabajo": 1, "Observadas": 1, "Min_Parada": 25, "Falla": "Falla en la mesa de trabajo", "Es_Falla_Tecnica": True, "Validado": False},
        {"Hora": "06:00-07:00", "Maquina": "DEMOWIDEM 3 (Prensa)", "Tipo": "Automático", "Operario": "MOREIRA CRISTIAN", "Meta": 80, "Buenas": 75, "Retrabajo": 3, "Observadas": 0, "Min_Parada": 0, "Falla": "Ninguna", "Es_Falla_Tecnica": False, "Validado": True},
        {"Hora": "07:00-08:00", "Maquina": "DEMOWIDEM 3 (Prensa)", "Tipo": "Automático", "Operario": "MOREIRA CRISTIAN", "Meta": 80, "Buenas": 30, "Retrabajo": 2, "Observadas": 3, "Min_Parada": 40, "Falla": "Soporte del Líder", "Es_Falla_Tecnica": True, "Validado": False}
    ])

if "sub_modulo_analisis" not in st.session_state:
    st.session_state.sub_modulo_analisis = "Disponibilidad"

# =========================================================================
# 4. RECEPTOR DE GOLPES IOT URL (Procesa seguro con sesión abierta)
# =========================================================================
query_params = st.query_params

if "evento" in query_params and query_params["evento"] == "golpe":
    maquina_param = query_params.get("maquina", "M1")
    
    if maquina_param == "M1":
        maquina_nombre = "DEMOWIDEM 1 (Inyectora)"
        filas_maquina = st.session_state.db_historial_planta["Maquina"] == maquina_nombre
        
        if filas_maquina.any():
            ultimo_idx = st.session_state.db_historial_planta[filas_maquina].index[-1]
            st.session_state.db_historial_planta.at[ultimo_idx, "Buenas"] += 1
            st.session_state.db_objetivos[maquina_nombre]["Estado_TR"] = "PRODUCIENDO"
            st.session_state.db_objetivos[maquina_nombre]["Ultimo_Evento"] = f"Golpe IoT recibido ({datetime.now().strftime('%H:%M:%S')})"
        
        st.query_params.clear()
        st.rerun()

# =========================================================================
# 5. SELECTOR DE CAPAS MODULAR
# =========================================================================
st.sidebar.title("🎛️ Módulos Licenciados")
capa_mapeada = {
    "1. 🖥️ Capa de Puesto (Pie de Máquina)": "Capa 1",
    "2. 🎯 Capa de Objetivos (Ingeniería/PCP)": "Capa 2",
    "3. 📱 Capa de Operario (Tablet)": "Capa 3",