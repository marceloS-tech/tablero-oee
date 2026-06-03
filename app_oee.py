import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os

# 1. CONFIGURACIÓN DE PANTALLA PRINCIPAL
st.set_page_config(page_title="SaaS OEE - Core Global de Planta", layout="wide")

# Credenciales seguras
mqtt_user = st.secrets["MQTT_USER"]
mqtt_pass = st.secrets["MQTT_PASS"]

# =========================================================================
# BLOQUES DE INYECCIÓN WEB (Separados para evitar errores de comillas)
# =========================================================================

ESTILOS_CSS = """
<style>
    .stApp { background-color: #0d1117; color: #ffffff; }
    div[data-testid="stMetricValue"] { font-size: 32px; font-weight: bold; color: #00f2fe; }
    .kpi-title { font-size: 14px; color: #8b949e; font-weight: bold; text-align: left; margin-bottom: 12px; font-family: monospace; }
    .gauge-title { text-align: center; font-size: 15px; font-weight: bold; color: #8b949e; margin-bottom: -10px; font-family: monospace; }
    div[data-testid="stMetricLabel"] { font-size: 16px !important; font-weight: bold !important; color: #8b949e !important; }
    .vorne-card { background-color: #161b22; border-radius: 8px; border: 1px solid #30363d; color: white; padding: 20px; margin: 10px; font-family: sans-serif; }
    .stButton > button { width: 100%; background-color: #161b22; color: #c9d1d9; border: 1px solid #30363d; padding: 10px; border-radius: 6px; font-weight: bold; }
    .stButton > button:hover { border-color: #00f2fe; color: #00f2fe; background-color: #1f242c; }
    .andon-card { border-radius: 8px; padding: 20px; margin-bottom: 15px; border: 1px solid #30363d; font-family: monospace; }
    .andon-marcha { background-color: #0c2519; border-left: 8px solid #00cc66; }
    .andon-setup { background-color: #2b220c; border-left: 8px solid #ffaa00; }
    .andon-parada { background-color: #2d1215; border-left: 8px solid #ff4b4b; }
</style>
"""

JS_CONTROL_TV = """
<script>
    // 1. Carrusel dinámico de pestañas cada 10 segundos
    var index = 0;
    setInterval(function() {
        var radios = window.parent.document.querySelectorAll('input[type="radio"]');
        if (radios.length > 0) {
            index = (index + 1) % radios.length;
            radios[index].click();
        }
    }, 10000); 

    // 2. Refresco en vivo del core de datos cada 2 segundos
    setInterval(function() {
        var reloadButton = window.parent.document.querySelector('button[title="Refresh"]');
        if (reloadButton) {
            reloadButton.click();
        }
    }, 2000); 
</script>
"""

# Inyectamos los estilos base en la aplicación de forma segura
st.markdown(ESTILOS_CSS, unsafe_allow_html=True)

# =========================================================================
# 2. ARQUITECTURA DE DATOS CENTRALIZADA
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
# RECEPTOR DE IMPACTOS IOT (ESCUCHA ACTIVA DE PARÁMETROS URL)
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
            st.session_state.db_objetivos[maquina_nombre]["Ultimo_Evento"] = f"Impacto IoT recibido ({datetime.now().strftime('%H:%M:%S')})"
        
        st.query_params.clear()
        st.rerun()

# =========================================================================
# 3. FILTRO DE ACCESO Y LOGIN DE SEGURIDAD
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
    st.stop()

st.sidebar.markdown(f"👤 **Usuario:** `{st.session_state.usuario_conectado}`")
if st.sidebar.button("🔴 Cerrar Sesión", use_container_width=True):
    st.session_state.autenticado = False
    st.session_state.usuario_conectado = None
    st.session_state.permisos_usuario = []
    st.rerun()

st.sidebar.markdown("---")

# =========================================================================
# 4. SELECTOR DE CAPAS MODULAR
# =========================================================================
st.sidebar.title("🎛️ Módulos Licenciados")
capa_mapeada = {
    "1. 🖥️ Capa de Puesto (Pie de Máquina)": "Capa 1",
    "2. 🎯 Capa de Objetivos (Ingeniería/PCP)": "Capa 2",
    "3. 📱 Capa de Operario (Tablet)": "Capa 3",
    "4. 👔 Capa de Supervisor (Validación)": "Capa 4",
    "5. 📊 Capa de Visión General (Dirección)": "Capa 5",
    "6. 📈 Capa de Análisis de Datos (BI)": "Capa 6",
    "7. 🚨 Capa de Andón Digital (Wiidem Style)": "Capa 7"
}

capa_activa = st.sidebar.radio("Seleccione el nivel de pantalla:", list(capa_mapeada.keys()))
st.sidebar.markdown("---")

capa_codigo = capa_mapeada[capa_activa]
df_global = st.session_state.db_historial_planta

if capa_codigo not in st.session_state.permisos_usuario:
    st.error("🔒 Módulo No Contratado en su Plan Actual.")
    st.stop()

tiempo_programado = len(df_global) * 60
df_tecnico = df_global[df_global["Es_Falla_Tecnica"] == True]
total_fallas = len(df_tecnico)
tiempo_reparaciones = df_tecnico["Min_Parada"].sum()
mttr = round(tiempo_reparaciones / total_fallas, 2) if total_fallas > 0 else 0.0
mtbf = round((tiempo_programado - tiempo_reparaciones) / total_fallas, 2) if total_fallas > 0 else tiempo_programado

def draw_scada_gauge(titulo_gauge, value):
    color_semaforo = "#00cc66" if value >= 85.0 else ("#ffaa00" if value >= 70.0 else "#ff4b4b")
    fig = go.Figure(go.Indicator(
        mode = "gauge+number", value = value, number = {'suffix': "%", 'font': {'size': 24}},
        title = {'text': titulo_gauge, 'font': {'size': 14, 'color': '#8b949e'}},
        gauge = {'axis': {'range': [0, 100], 'tickcolor': '#30363d'}, 'bar': {'color': color_semaforo}, 'bgcolor': '#161b22', 'borderwidth': 0}
    ))
    fig.update_layout(height=130, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor='rgba(0,0,0,0)')
    return fig

# =========================================================================
# 5. RENDERIZADO DE CAPAS
# =========================================================================

if "1." in capa_activa:
    st.title("🖥️ Capa de Puesto - Monitor de Máquina")
    maq_puesto = st.selectbox("Seleccione el Puesto:", list(st.session_state.db_objetivos.keys()))
    df_puesto = df_global[df_global["Maquina"] == maq_puesto].sort_values(by="Hora")
    st.dataframe(df_puesto, use_container_width=True, hide_index=True)

elif "2." in capa_activa:
    st.title("🎯 Capa de Objetivos - Configuración")
    st.info("Módulo de administración técnica de ritmos base.")

elif "3." in capa_activa:
    st.title("📱 Capa de Operario - Terminal Interactiva")
    operario_nom = st.selectbox("Operario:", ["VILLARROEL ENZO", "FRANCO MAXIMILIANO", "MOREIRA CRISTIAN"])
    buenas_op = st.number_input("Piezas BUENAS:", min_value=0, value=50)
    if st.button("💾 Enviar Datos Manuales"):
        st.success("Datos acoplados al historial.")

elif "4." in capa_activa:
    st.title("👔 Capa de Supervisor - Validación")
    st.dataframe(df_global, use_container_width=True, hide_index=True)

elif "5." in capa_activa:
    st.markdown("<h2 style='text-align: center; color: #00f2fe;'>SaaS OEE - Vista General de Planta</h2>", unsafe_allow_html=True)
    Buenas_g = df_global["Buenas"].sum()
    total_g = Buenas_g + df_global["Retrabajo"].sum() + df_global["Observadas"].sum()
    disp_g = round(((tiempo_programado - df_global["Min_Parada"].sum()) / tiempo_programado) * 100, 1)
    perf_g = round((total_g / df_global["Meta"].sum()) * 100, 1)
    cal_g = round((Buenas_g / total_g) * 100, 1) if total_g > 0 else 100
    oee_g = round((disp_g/100) * (perf_g/100) * (cal_g/100) * 100, 1)

    c1, c2, c3, c4 = st.columns(4)
    c1.plotly_chart(draw_scada_gauge("OEE GLOBAL", oee_g), use_container_width=True)
    c2.plotly_chart(draw_scada_gauge("PERFORMANCE", perf_g), use_container_width=True)
    c3.plotly_chart(draw_scada_gauge("DISPONIBILIDAD", disp_g), use_container_width=True)
    c4.plotly_chart(draw_scada_gauge("CALIDAD", cal_g), use_container_width=True)

elif "6." in capa_activa:
    st.title("📈 Analítica Avanzada (BI)")
    fig_prod = px.bar(df_global, x="Hora", y="Buenas", color="Maquina", title="Producción Real por Hora")
    st.plotly_chart(fig_prod, use_container_width=True)

elif "7." in capa_activa:
    st.markdown("## 🚨 Monitor Andón de Planta (Tiempo Real)")
    cols = st.columns(3)
    for i, (maq, d) in enumerate(st.session_state.db_objetivos.items()):
        df_maq = df_global[df_global["Maquina"] == maq]
        total_buenas = int(df_maq["Buenas"].sum())
        estado = d.get("Estado_TR", "PARADA")
        with cols[i]:
            st.metric(label=f"🤖 {maq}", value=f"{total_buenas} Pz", delta=f"Estado: {estado}")

# Inyección final y limpia del script de automatización de TV
st.markdown(JS_CONTROL_TV, unsafe_allow_html=True)