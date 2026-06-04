import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import json

# 1. CONFIGURACIÓN DE PANTALLA PRINCIPAL (Debe ser la primera directiva)
st.set_page_config(page_title="SaaS OEE - Core Global de Planta", layout="wide")

# Credenciales desde los Secrets
mqtt_user = st.secrets["MQTT_USER"]
mqtt_pass = st.secrets["MQTT_PASS"]

# Archivos de persistencia de datos (La "Base de Datos" de la prueba)
HISTORIAL_FILE = "db_historial_planta.csv"
OBJETIVOS_FILE = "db_objetivos_planta.json"

# --- Inicialización de archivos locales si no existen ---
if not os.path.exists(HISTORIAL_FILE):
    df_init = pd.DataFrame([
        {"Hora": "06:00-07:00", "Maquina": "DEMOWIDEM 1 (Inyectora)", "Tipo": "Automático", "Operario": "VILLARROEL ENZO", "Meta": 60, "Buenas": 58, "Retrabajo": 1, "Observadas": 1, "Min_Parada": 0, "Falla": "Ninguna", "Es_Falla_Tecnica": False, "Validado": True},
        {"Hora": "07:00-08:00", "Maquina": "DEMOWIDEM 1 (Inyectora)", "Tipo": "Automático", "Operario": "VILLARROEL ENZO", "Meta": 60, "Buenas": 59, "Retrabajo": 0, "Observadas": 1, "Min_Parada": 0, "Falla": "Ninguna", "Es_Falla_Tecnica": False, "Validado": True},
        {"Hora": "08:00-09:00", "Maquina": "DEMOWIDEM 1 (Inyectora)", "Tipo": "Automático", "Operario": "VILLARROEL ENZO", "Meta": 60, "Buenas": 38, "Retrabajo": 2, "Observadas": 0, "Min_Parada": 15, "Falla": "Falla Robótica", "Es_Falla_Tecnica": True, "Validado": False},
        {"Hora": "06:00-07:00", "Maquina": "DEMOWIDEM 2 (Banco Manual)", "Tipo": "Manual", "Operario": "FRANCO MAXIMILIANO", "Meta": 40, "Buenas": 35, "Retrabajo": 2, "Observadas": 1, "Min_Parada": 5, "Falla": "Ajuste de Banco", "Es_Falla_Tecnica": False, "Validado": True},
        {"Hora": "07:00-08:00", "Maquina": "DEMOWIDEM 2 (Banco Manual)", "Tipo": "Manual", "Operario": "FRANCO MAXIMILIANO", "Meta": 40, "Buenas": 18, "Retrabajo": 1, "Observadas": 1, "Min_Parada": 25, "Falla": "Falla en la mesa de trabajo", "Es_Falla_Tecnica": True, "Validado": False},
        {"Hora": "06:00-07:00", "Maquina": "DEMOWIDEM 3 (Prensa)", "Tipo": "Automático", "Operario": "MOREIRA CRISTIAN", "Meta": 80, "Buenas": 75, "Retrabajo": 3, "Observadas": 0, "Min_Parada": 0, "Falla": "Ninguna", "Es_Falla_Tecnica": False, "Validado": True},
        {"Hora": "07:00-08:00", "Maquina": "DEMOWIDEM 3 (Prensa)", "Tipo": "Automático", "Operario": "MOREIRA CRISTIAN", "Meta": 80, "Buenas": 30, "Retrabajo": 2, "Observadas": 3, "Min_Parada": 40, "Falla": "Soporte del Líder", "Es_Falla_Tecnica": True, "Validado": False}
    ])
    df_init.to_csv(HISTORIAL_FILE, index=False)

if not os.path.exists(OBJETIVOS_FILE):
    obj_init = {
        "DEMOWIDEM 1 (Inyectora)": {"Meta_Hora": 60, "Producto": "Carcasa Plástica A", "Estado_TR": "PRODUCIENDO", "Ultimo_Evento": "Ninguno"},
        "DEMOWIDEM 2 (Banco Manual)": {"Meta_Hora": 40, "Producto": "Ensamble Eléctrico B", "Estado_TR": "SETUP", "Ultimo_Evento": "Logística: Falta Piezas"},
        "DEMOWIDEM 3 (Prensa)": {"Meta_Hora": 80, "Producto": "Soporte Metálico C", "Estado_TR": "PARADA", "Ultimo_Evento": "Mantenimiento: Falla Mecánica"}
    }
    with open(OBJETIVOS_FILE, "w", encoding="utf-8") as f:
        json.dump(obj_init, f, indent=4, ensure_ascii=False)

# =========================================================================
# RECEPTOR DE GOLPES IOT URL (ZONA LIBRE - Ejecuta antes del Login para el ESP)
# =========================================================================
query_params = st.query_params

if "evento" in query_params and query_params["evento"] == "golpe":
    maquina_param = query_params.get("maquina", "M1")
    
    # Mapeo de parámetro corto a nombre real
    maquina_nombre = "DEMOWIDEM 1 (Inyectora)"
    if maquina_param == "M2": maquina_nombre = "DEMOWIDEM 2 (Banco Manual)"
    if maquina_param == "M3": maquina_nombre = "DEMOWIDEM 3 (Prensa)"
    
    # 1. Sumar pieza en el archivo CSV
    if os.path.exists(HISTORIAL_FILE):
        df_db = pd.read_csv(HISTORIAL_FILE)
        filas_maquina = df_db["Maquina"] == maquina_nombre
        if filas_maquina.any():
            ultimo_idx = df_db[filas_maquina].index[-1]
            df_db.at[ultimo_idx, "Buenas"] += 1
            df_db.to_csv(HISTORIAL_FILE, index=False)
            
    # 2. Modificar estado en el archivo JSON
    if os.path.exists(OBJETIVOS_FILE):
        with open(OBJETIVOS_FILE, "r", encoding="utf-8") as f:
            objs_db = json.load(f)
        if maquina_nombre in objs_db:
            objs_db[maquina_nombre]["Estado_TR"] = "PRODUCIENDO"
            objs_db[maquina_nombre]["Ultimo_Evento"] = f"Golpe IoT recibido ({datetime.now().strftime('%H:%M:%S')})"
        with open(OBJETIVOS_FILE, "w", encoding="utf-8") as f:
            json.dump(objs_db, f, indent=4, ensure_ascii=False)
            
    # Retorno ultra rápido para el hardware. No gasta recursos en armar la web.
    st.text(f"OK - Golpe registrado en {maquina_nombre}")
    st.stop()

# =========================================================================
# BLOQUES DE INYECCIÓN WEB (Estilos CSS y Script de TV)
# =========================================================================
ESTILOS_CSS = """
<style>
    .stApp { background-color: #0d1117; color: #ffffff; }
    div[data-testid="stMetricValue"] { font-size: 32px; font-weight: bold; color: #00f2fe; }
    .kpi-title { font-size: 14px; color: #8b949e; font-weight: bold; text-align: left; margin-bottom: 12px; font-family: monospace; }
    .gauge-title { text-align: center; font-size: 15px; font-weight: bold; color: #8b949e; margin-bottom: -10px; font-family: monospace; }
    div[data-testid="stMetricLabel"] { font-size: 16px !important; font-weight: bold !important; color: #8b949e !important; }
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
# 2. CONTROL DE SESIÓN Y PARED DE LOGUEO
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

if not st.session_state.autenticado:
    st.stop()

st.sidebar.markdown(f"👤 **Usuario:** `{st.session_state.usuario_conectado}`")
if st.sidebar.button("🔴 Cerrar Sesión", use_container_width=True):
    st.session_state.autenticado = False
    st.session_state.usuario_conectado = None
    st.session_state.permisos_usuario = []
    st.rerun()

st.sidebar.markdown("---")

# =========================================================================
# 3. LECTURA DE DATOS DESDE LOS ARCHIVOS VIVOS
# =========================================================================
HORAS_TURNO = ["06:00-07:00", "07:00-08:00", "08:00-09:00", "09:00-10:00", "10:00-11:00", "11:00-12:00", "12:00-13:00", "13:00-14:00"]

df_global = pd.read_csv(HISTORIAL_FILE)
df_global["Es_Falla_Tecnica"] = df_global["Es_Falla_Tecnica"].astype(bool)
df_global["Validado"] = df_global["Validado"].astype(bool)

with open(OBJETIVOS_FILE, "r", encoding="utf-8") as f:
    db_objetivos = json.load(f)

if "sub_modulo_analisis" not in st.session_state:
    st.session_state.sub_modulo_analisis = "Producción"

# =========================================================================
# 5. SELECTOR DE CAPAS MODULAR
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

if capa_codigo not in st.session_state.permisos_usuario:
    st.markdown(f"""
    <div style='background-color:#2d1215; padding:30px; border-radius:8px; border:1px solid #ff4b4b; text-align:center;'>
        <h2 style='color:#ff4b4b; margin-top:0;'>🔒 Módulo No Contratado</h2>
        <p style='font-size:16px; color:#c9d1d9;'>Su cuenta actual no posee la licencia activa para utilizar la <b>{capa_activa}</b>.</p>
    </div>
    """, unsafe_allow_html=True)
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
# 6. RENDERIZADO DE LAS CAPAS VISUALES 
# =========================================================================

if "1." in capa_activa:
    st.title("🖥️ Capa de Puesto - Monitor de Máquina")
    maq_puesto = st.selectbox("Seleccione el Puesto a mostrar en este Monitor:", list(db_objetivos.keys()))
    st.markdown(f"### 📍 Celda Activa: {maq_puesto} | **Producto:** `{db_objetivos[maq_puesto]['Producto']}`")
    st.markdown("---")
    
    df_puesto = df_global[df_global["Maquina"] == maq_puesto].sort_values(by="Hora")
    df_m1 = df_puesto.copy()
    df_m1["Utilización (Min)"] = 60 - df_m1["Min_Parada"]
    df_m1["Rendimiento (%)"] = round((df_m1["Buenas"] / df_m1["Meta"]) * 100, 1) if len(df_m1) > 0 else 0
    df_m1["Estado"] = df_m1["Min_Parada"].apply(lambda x: "🔴 Parada" if x > 15 else ("🟡 Desvío" if x > 0 else "🟢 Marcha Normal"))
    
    col_tab_m, col_gra_m = st.columns([4, 3])
    with col_tab_m:
        st.markdown("#### 🕒 Registro de Marcha y Rendimiento Hora a Hora Online")
        st.dataframe(df_m1[["Hora", "Meta", "Buenas", "Retrabajo", "Observadas", "Utilización (Min)", "Rendimiento (%)", "Estado"]], use_container_width=True, hide_index=True)
    with col_gra_m:
        fig_puesto = go.Figure()
        fig_puesto.add_trace(go.Scatter(x=df_puesto["Hora"], y=df_puesto["Meta"], mode='lines+markers', name='Meta de Ingeniería', line=dict(color='#8b949e', dash='dash')))
        fig_puesto.add_trace(go.Bar(x=df_puesto["Hora"], y=df_puesto["Buenas"], name='Buenas Logradas', marker_color='#00cc66'))
        fig_puesto.update_layout(title="Avance del Ritmo vs Meta de Producción", barmode='group', height=250, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color="#ffffff"))
        st.plotly_chart(fig_puesto, use_container_width=True)

elif "2." in capa_activa:
    st.title("🎯 Capa de Objetivos - Configuración de Ingeniería")
    st.markdown("---")
    clave_ing = st.text_input("Ingrese la Clave de Seguridad de Admin:", type="password")
    
    if clave_ing == "admin789":
        st.success("🔓 Acceso Concedido")
        maq_obj = st.selectbox("Seleccione la Máquina a configurar:", list(db_objetivos.keys()))
        datos_maq = db_objetivos.get(maq_obj, {})
        c_obj1, c_obj2 = st.columns(2)
        with c_obj1:
            nueva_meta = st.number_input("Establecer nueva Meta de piezas por hora:", min_value=1, value=int(datos_maq.get("Meta_Hora", 50)))
        with c_obj2:
            nuevo_prod = st.text_input("Código o Nombre del Producto a fabricar:", value=datos_maq.get("Producto", "Sin Definir"))
            
        if st.button("💾 Aplicar Objetivos", use_container_width=True):
            db_objetivos[maq_obj]["Meta_Hora"] = nueva_meta
            db_objetivos[maq_obj]["Producto"] = nuevo_prod
            with open(OBJETIVOS_FILE, "w", encoding="utf-8") as f:
                json.dump(db_objetivos, f, indent=4, ensure_ascii=False)
            st.success("¡Objetivos actualizados en archivo maestro!")
            st.rerun()

elif "3." in capa_activa:
    st.title("📱 Capa de Operario - Terminal Interactiva")
    st.markdown("---")
    col_op1, col_op2 = st.columns(2)
    with col_op1:
        operario_nom = st.selectbox("Seleccione su Nombre:", ["VILLARROEL ENZO", "FRANCO MAXIMILIANO", "MOREIRA CRISTIAN"])
        maq_op = st.selectbox("Puesto Físico:", list(db_objetivos.keys()))
        hora_op = st.selectbox("Hora a declarar:", HORAS_TURNO)
    with col_op2:
        buenas_op = st.number_input("Piezas BUENAS:", min_value=0, value=50)
        ret_op = st.number_input("Piezas RETRABAJO:", min_value=0, value=0)
        obs_op = st.number_input("Piezas OBSERVADAS:", min_value=0, value=0)
    if st.button("💾 Enviar Bloque Hora a Hora", use_container_width=True):
        nueva_fila = {
            "Hora": hora_op, "Maquina": maq_op, "Tipo": "Manual" if "Manual" in maq_op else "Automático",
            "Operario": operario_nom, "Meta": db_objetivos[maq_op]["Meta_Hora"], "Buenas": buenas_op,
            "Retrabajo": ret_op, "Observadas": obs_op, "Min_Parada": 0, "Falla": "Ninguna", "Es_Falla_Tecnica": False, "Validado": False
        }
        df_global = pd.concat([df_global, pd.DataFrame([nueva_fila])], ignore_index=True)
        df_global.to_csv(HISTORIAL_FILE, index=False)
        st.success("¡Registro inyectado en archivo de planta!")
        st.rerun()

elif "4." in capa_activa:
    st.title("👔 Capa de Supervisor - Validación y Auditoría")
    st.dataframe(df_global, use_container_width=True, hide_index=True)

elif "5." in capa_activa:
    st.markdown("<h2 style='text-align: center; color: #00f2fe;'>SaaS OEE - Vista General de Planta</h2>", unsafe_allow_html=True)
    st.markdown("---")
    col_v1, col_v2, col_v3, col_v4, col_cards_g = st.columns([1, 1, 1, 1, 3])
    
    Buenas_g = df_global["Buenas"].sum()
    total_g = Buenas_g + df_global["Retrabajo"].sum() + df_global["Observadas"].sum()
    disp_g = round(((tiempo_programado - df_global["Min_Parada"].sum()) / tiempo_programado) * 100, 1)
    perf_g = round((total_g / df_global["Meta"].sum()) * 100, 1)
    cal_g = round((Buenas_g / total_g) * 100, 1) if total_g > 0 else 100
    oee_g = round((disp_g/100) * (perf_g/100) * (cal_g/100) * 100, 1)

    with col_v1: st.plotly_chart(draw_scada_gauge("OEE GLOBAL", oee_g), use_container_width=True)
    with col_v2: st.plotly_chart(draw_scada_gauge("PERFORMANCE", perf_g), use_container_width=True)
    with col_v3: st.plotly_chart(draw_scada_gauge("DISPONIBILIDAD", disp_g), use_container_width=True)
    with col_v4: st.plotly_chart(draw_scada_gauge("CALIDAD", cal_g), use_container_width=True)

    with col_cards_g:
        st.markdown("<br>", unsafe_allow_html=True)
        cg1, cg2, cg3 = st.columns(3)
        cg1.metric("MTTR (Calculado)", f"{mttr} min")
        cg2.metric("MTBF (Calculado)", f"{mtbf} min")
        cg3.metric("Celdas Conectadas", f"{len(df_global['Maquina'].unique())} Puestos")
        
    st.markdown("---")
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        fig_b1 = px.bar(df_global, x="Min_Parada", y="Maquina", color="Falla", orientation='h', height=280)
        st.plotly_chart(fig_b1, use_container_width=True)
    with col_b2:
        df_op_g = df_global.groupby("Operario")["Buenas"].sum().reset_index()
        fig_b2 = px.bar(df_op_g, x="Buenas", y="Operario", orientation='h', height=280)
        st.plotly_chart(fig_b2, use_container_width=True)

elif "6." in capa_activa:
    st.markdown("<h2 style='color: #ffffff;'>📈 Analítica Avanzada e Históricos de Planta</h2>", unsafe_allow_html=True)
    c_btn1, c_btn2, c_btn3, c_btn4 = st.columns(4)
    with c_btn1: 
        if st.button("⏱️ Tiempos de Parada", use_container_width=True): st.session_state.sub_modulo_analisis = "Disponibilidad"
    with c_btn2: 
        if st.button("🛑 Distribución de Fallas", use_container_width=True): st.session_state.sub_modulo_analisis = "Paradas"
    with c_btn3: 
        if st.button("⚙️ Frecuencias", use_container_width=True): st.session_state.sub_modulo_analisis = "Causas"
    with c_btn4: 
        if st.button("📦 Evolución de Producción", use_container_width=True): st.session_state.sub_modulo_analisis = "Producción"
        
    st.markdown(f"### Análisis de Módulo: `{st.session_state.sub_modulo_analisis}`")
    
    if st.session_state.sub_modulo_analisis == "Disponibilidad":
        fig_disp = px.bar(df_global, x="Hora", y="Min_Parada", color="Maquina", title="Minutos Totales de Parada por Hora")
        st.plotly_chart(fig_disp, use_container_width=True)
    elif st.session_state.sub_modulo_analisis == "Paradas":
        df_paradas = df_global[df_global["Min_Parada"] > 0]
        if not df_paradas.empty:
            fig_paradas = px.pie(df_paradas, values="Min_Parada", names="Falla", title="Paretos de Pérdidas de Disponibilidad")
            st.plotly_chart(fig_paradas, use_container_width=True)
        else:
            st.info("Sin paradas registradas en el turno activo.")
    elif st.session_state.sub_modulo_analisis == "Causas":
        fig_causas = px.histogram(df_global, x="Falla", color="Maquina", title="Historial y Recurrencia de Alarmas")
        st.plotly_chart(fig_causas, use_container_width=True)
    else:
        fig_prod = px.bar(df_global, x="Hora", y=["Buenas", "Retrabajo", "Observadas"], barmode="group", title="Cumplimiento de Volumen")
        st.plotly_chart(fig_prod, use_container_width=True)

elif "7." in capa_activa:
    st.markdown("## 🚨 Monitor Andón de Planta (Tiempo Real)")
    ahora = datetime.now()
    minutos_transcurridos_turno = (ahora.hour * 60 + ahora.minute) - (6 * 60)
    minutos_en_hora = minutos_transcurridos_turno % 60
    if minutos_en_hora <= 0: minutos_en_hora = 1
    
    cols = st.columns(3)
    for i, (maq, d) in enumerate(db_objetivos.items()):
        df_maq = df_global[df_global["Maquina"] == maq]
        meta_hora_base = d.get("Meta_Hora", 60)
        meta_proporcional = round((meta_hora_base / 60) * minutos_en_hora)
        total_buenas = int(df_maq["Buenas"].sum())
        eficiencia_real = round((total_buenas / meta_proporcional * 100), 1) if meta_proporcional > 0 else 0.0
        oee = round(eficiencia_real * 0.95, 1) 
        
        estado = d.get("Estado_TR", "PARADA")
        operario = df_maq["Operario"].iloc[-1] if not df_maq.empty else "N/A"
        evento = d.get("Ultimo_Evento", "Ninguno")
        
        clase_andon = "andon-marcha" if estado == "PRODUCIENDO" else ("andon-setup" if estado == "SETUP" else "andon-parada")
        badge_color = "badge-v" if estado == "PRODUCIENDO" else ("badge-a" if estado == "SETUP" else "badge-r")
        
        html_code = f"""<div class="andon-card {clase_andon}">
<div class="andon-header">
<span>{maq}</span>
<span class="wiidem-badge {badge_color}">{estado}</span>
</div>
<div style="margin-top:15px; font-size:14px; color:#8b949e;">PRODUCTO ACTIVO:</div>
<div style="font-size:18px; font-weight:bold; color:#ffffff; font-family:sans-serif;">{d.get('Producto','-')}</div>
<div class="andon-meta-box">
<table style="width:100%; color:#c9d1d9; border-collapse:collapse;">
<tr><td><b>EFFICIENCY:</b></td><td style="text-align:right; color:#00cc66; font-size:18px;"><b>{eficiencia_real}%</b></td></tr>
<tr><td><b>OEE ESTIMADO:</b></td><td style="text-align:right; color:#00f2fe;"><b>{oee}%</b></td></tr>
</table>
</div>
<div class="andon-meta-box">
<table style="width:100%; font-size:12px; border-collapse:collapse;">
<tr><td>META PARCIAL ({minutos_en_hora} min):</td><td style="text-align:right;"><b>{meta_proporcional} pz</b></td></tr>
<tr><td>REAL LOGRADO:</td><td style="text-align:right; color:#00f2fe;"><b>{total_buenas} pz</b></td></tr>
</table>
</div>
<div style="font-size:11px; color:#8b949e; margin-top:10px;">👤 OP: {operario}</div>
<div style="font-size:11px; color:#8b949e;">🚨 ÚLTIMO EVENTO: {evento}</div>
</div>"""
        with cols[i]: st.markdown(html_code, unsafe_allow_html=True)

# Inyección final para el carrusel de TV
st.markdown(JS_AUTOMATIZACION, unsafe_allow_html=True)