import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

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
    .andon-card { border-radius: 8px; padding: 20px; margin-bottom: 15px; border: 1px solid #30363d; font-family: monospace; }
    .andon-marcha { background-color: #0c2519; border-left: 8px solid #00cc66; }
    .andon-setup { background-color: #2b220c; border-left: 8px solid #ffaa00; }
    .andon-parada { background-color: #2d1215; border-left: 8px solid #ff4b4b; }
    
    .andon-header { font-size: 22px; font-weight: bold; margin-bottom: 5px; display: flex; justify-content: space-between; align-items: center; }
    .andon-status { font-size: 16px; font-weight: bold; letter-spacing: 0.5px; }
    .andon-meta-box { background: #1f242c; padding: 10px; border-radius: 4px; border: 1px solid #30363d; font-size: 13px; margin-top: 12px; }
    
    /* Cuadrantes de OEE Miniatura */
    .wiidem-badge { display: inline-block; padding: 4px 8px; font-weight: bold; border-radius: 4px; font-size: 12px; color: #000; margin-right: 5px; }
    .badge-v { background-color: #00cc66; }
    .badge-a { background-color: #ffaa00; }
    .badge-r { background-color: #ff4b4b; }
    </style>
    """, unsafe_allow_html=True)

# =========================================================================
# 1. ARQUITECTURA DE DATOS CENTRALIZADA
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
# 2. CONTROL DE SESIÓN Y PARED DE LOGUEO (PAYWALL)
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
    st.stop()  # Detiene la ejecución aquí si no puso la clave correcta

# Si está autenticado, muestra datos de cuenta y botón para salir
st.sidebar.markdown(f"👤 **Usuario:** `{st.session_state.usuario_conectado}`")
if st.sidebar.button("🔴 Cerrar Sesión", use_container_width=True):
    st.session_state.autenticado = False
    st.session_state.usuario_conectado = None
    st.session_state.permisos_usuario = []
    st.rerun()

st.sidebar.markdown("---")

# =========================================================================
# 3. SELECTOR DE CAPAS MODULAR
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

# Validar si el plan contratado incluye la capa seleccionada
if capa_codigo not in st.session_state.permisos_usuario:
    st.markdown(f"""
    <div style='background-color:#2d1215; padding:30px; border-radius:8px; border:1px solid #ff4b4b; text-align:center;'>
        <h2 style='color:#ff4b4b; margin-top:0;'>🔒 Módulo No Contratado</h2>
        <p style='font-size:16px; color:#c9d1d9;'>Su cuenta actual no posee la licencia activa para utilizar la <b>{capa_activa}</b>.</p>
        <p style='font-size:14px; color:#8b949e;'>Para dar de alta este módulo en su célula de producción, contacte al ejecutivo de cuentas Pulsar/Wiidem.</p>
        <br>
        <a href='#' style='background-color:#ff4b4b; color:white; padding:10px 20px; text-decoration:none; border-radius:5px; font-weight:bold;'>Solicitar Cotización de Licencia</a>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Motores de cálculo base para KPI
tiempo_programado = len(df_global) * 60
df_tecnico = df_global[df_global["Es_Falla_Tecnica"] == True]
total_fallas = len(df_tecnico)
tiempo_reparaciones = df_tecnico["Min_Parada"].sum()
mttr = round(tiempo_reparaciones / total_fallas, 2) if total_fallas > 0 else 0.0
mtbf = round((tiempo_programado - tiempo_reparaciones) / total_fallas, 2) if total_fallas > 0 else tiempo_programado

# =========================================================================
# FUNCIÓN AUXILIAR: RELOJES (GAUGES) SÓLIDOS SIN ERRORES DE PLOTLY
# =========================================================================
def draw_scada_gauge(titulo_gauge, value):
    color_semaforo = "#00cc66" if value >= 85.0 else ("#ffaa00" if value >= 70.0 else "#ff4b4b")
    fig = go.Figure(go.Indicator(
        mode = "gauge+number", 
        value = value, 
        number = {'suffix': "%", 'font': {'size': 24}},
        title = {'text': titulo_gauge, 'font': {'size': 14, 'color': '#8b949e'}},
        gauge = {
            'axis': {'range': [0, 100], 'tickcolor': '#30363d'}, 
            'bar': {'color': color_semaforo}, 
            'bgcolor': '#161b22', 
            'borderwidth': 0
        }
    ))
    fig.update_layout(height=130, margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor='rgba(0,0,0,0)')
    return fig

# =========================================================================
# EJECUCIÓN MODULAR DE CAPAS (ESTRUCTURA DE FLUJO PLANO)
# =========================================================================

if "1." in capa_activa:
    st.title("🖥️ Capa de Puesto - Monitor de Máquina")
    maq_puesto = st.selectbox("Seleccione el Puesto a mostrar en este Monitor:", list(st.session_state.db_objetivos.keys()))
    st.markdown(f"### 📍 Celda Activa: {maq_puesto} | **Producto:** `{st.session_state.db_objetivos[maq_puesto]['Producto']}`")
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
        st.success("🔓 Acceso Concedido a la Configuración de Metas")
        
        # Obtenemos las claves de las máquinas
        if "db_objetivos" in st.session_state:
            maq_obj = st.selectbox("Seleccione la Máquina a configurar:", list(st.session_state.db_objetivos.keys()))
            
            # --- CORRECCIÓN DE SEGURIDAD ---
            # Obtenemos el diccionario de la máquina o uno vacío si no existe
            datos_maq = st.session_state.db_objetivos.get(maq_obj, {})
            
            # Definimos valores por defecto seguros por si faltan claves
            meta_actual = datos_maq.get("Meta_Hora", 50)
            prod_actual = datos_maq.get("Producto", "Sin Definir")
            
            c_obj1, c_obj2 = st.columns(2)
            with c_obj1:
                nueva_meta = st.number_input("Establecer nueva Meta de piezas por hora:", min_value=1, value=int(meta_actual))
            with c_obj2:
                nuevo_prod = st.text_input("Código o Nombre del Producto a fabricar:", value=prod_actual)
                
            if st.button("💾 Aplicar y Forzar Nuevos Objetivos de Planta", use_container_width=True):
                # Nos aseguramos de que la máquina exista en el diccionario antes de asignar
                if maq_obj not in st.session_state.db_objetivos:
                    st.session_state.db_objetivos[maq_obj] = {}
                
                # Actualizamos
                st.session_state.db_objetivos[maq_obj]["Meta_Hora"] = nueva_meta
                st.session_state.db_objetivos[maq_obj]["Producto"] = nuevo_prod
                st.success(f"¡Objetivos actualizados con éxito!")
        else:
            st.error("Error: La base de datos de objetivos no está cargada.")
            
    elif clave_ing != "":
        st.error("🔒 Clave inválida.")
elif "3." in capa_activa:
    st.title("📱 Capa de Operario - Terminal Interactiva")
    st.markdown("---")
    
    col_op1, col_op2 = st.columns(2)
    
    with col_op1:
        operario_nom = st.selectbox(
            "Seleccione su Nombre y Apellido:", 
            ["VILLARROEL ENZO", "FRANCO MAXIMILIANO", "MOREIRA CRISTIAN"]
        )
        # Verificamos que existan datos en db_objetivos antes de intentar listarlos
        if "db_objetivos" in st.session_state and st.session_state.db_objetivos:
            maq_op = st.selectbox("Puesto Físico donde está operando:", list(st.session_state.db_objetivos.keys()))
        else:
            st.error("Error: Base de datos de objetivos no cargada.")
            st.stop()
            
        hora_op = st.selectbox("Seleccione la Hora a declarar:", HORAS_TURNO)
        
    with col_op2:
        # --- CORRECCIÓN DE SEGURIDAD PARA EL KEYERROR ---
        datos_maq = st.session_state.db_objetivos.get(maq_op, {})
        meta_automatica = datos_maq.get("Meta_Hora", 0) 
        
        if meta_automatica == 0:
            st.warning("⚠️ Meta no configurada para este puesto. Contactar a Ingeniería.")
        else:
            st.info(f"📋 **Meta dictada por Ingeniería para este puesto:** {meta_automatica} piezas/hora")
            
        buenas_op = st.number_input("Piezas BUENAS producidas en este bloque:", min_value=0, value=50)
        ret_op = st.number_input("Piezas para RETRABAJO:", min_value=0, value=0)
        obs_op = st.number_input("Piezas OBSERVADAS / SCRAP:", min_value=0, value=0)
        
    st.markdown("### 🛑 Reportar Estados de Parada Técnica")
    col_po1, col_po2 = st.columns(2)
    
    with col_po1:
        minutos_op = st.number_input("Minutos Totales de inactividad (0-60):", min_value=0, max_value=60, value=0)
    with col_po2:
        falla_op = st.selectbox(
            "Causa Raíz de la detención:", 
            ["Ninguna", "Falla en la mesa de trabajo", "Falla Robótica", "Asistencia de Mantenimiento", "Ajuste de Banco", "Soporte del Líder"]
        )
        es_tec = st.checkbox("¿Es un desperfecto/rotura técnica?", value=False if falla_op == "Ninguna" else True)
        
    if st.button("💾 Enviar Bloque Hora a Hora a la Nube", use_container_width=True):
        nuevo_reg = {
            "Hora": hora_op, 
            "Maquina": maq_op, 
            "Tipo": "Manual" if "Manual" in maq_op else "Automático",
            "Operario": operario_nom, 
            "Meta": meta_automatica, 
            "Buenas": buenas_op, 
            "Retrabajo": ret_op,
            "Observadas": obs_op, 
            "Min_Parada": minutos_op, 
            "Falla": falla_op, 
            "Es_Falla_Tecnica": es_tec, 
            "Validado": False
        }
        
        # Actualización segura del historial
        if "db_historial_planta" in st.session_state:
            df_limpio = st.session_state.db_historial_planta[~((st.session_state.db_historial_planta["Hora"] == hora_op) & (st.session_state.db_historial_planta["Maquina"] == maq_op))]
            st.session_state.db_historial_planta = pd.concat([df_limpio, pd.DataFrame([nuevo_reg])], ignore_index=True)
            st.success(f"¡Registro inyectado online con éxito!")
        else:
            st.error("Error: Historial no disponible.")
elif "4." in capa_activa:
    st.title("👔 Capa de Supervisor - Validación y Auditoría")
    df_pendientes = df_global[df_global["Validado"] == False]
    if len(df_pendientes) > 0:
        st.warning(f"Atención: Hay {len(df_pendientes)} bloques horarios esperando auditoría.")
        fila_a_validar = st.selectbox("Seleccione el bloque que desea auditar:", df_pendientes.index.map(lambda x: f"Fila {x}: {df_global.loc[x, 'Maquina']} en {df_global.loc[x, 'Hora']}"))
        idx_f = int(fila_a_validar.split(":")[0].replace("Fila ", ""))
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            motivo_corregido = st.selectbox("Causa Raíz:", ["Ninguna", "Falla en la mesa de trabajo", "Falla Robótica", "Ajuste de Banco"], index=0)
        with col_v2:
            min_corregidos = st.number_input("Minutos de Parada reales:", min_value=0, max_value=60, value=int(df_global.loc[idx_f, "Min_Parada"]))
        if st.button("🟢 Validar y Liberar Registro", use_container_width=True):
            st.session_state.db_historial_planta.loc[idx_f, "Falla"] = motivo_corregido
            st.session_state.db_historial_planta.loc[idx_f, "Min_Parada"] = min_corregidos
            st.session_state.db_historial_planta.loc[idx_f, "Validado"] = True
            st.success("¡Registro auditado y liberado!")
            st.rerun()
    else:
        st.success("🟢 Todos los registros se encuentran auditados correctamente.")
    st.dataframe(df_global, use_container_width=True, hide_index=True)

elif "5." in capa_activa:
    st.markdown("<h2 style='text-align: center; color: #00f2fe;'>SaaS OEE - Vista General de Planta</h2>", unsafe_allow_html=True)
    st.markdown("---")
    col_v1, col_v2, col_v3, col_v4, col_cards_g = st.columns([1, 1, 1, 1, 3])
    
    Buenas_g = df_global["Buenas"].sum()
    total_g = Buenas_g + df_global["Retrabajo"].sum() + df_global["Observadas"].sum()
    disp_g = round(((tiempo_programado - df_global["Min_Parada"].sum()) / tiempo_programado) * 100, 1) if tiempo_programado > 0 else 100
    perf_g = round((total_g / df_global["Meta"].sum()) * 100, 1) if df_global["Meta"].sum() > 0 else 100
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
        st.markdown("**Minutos de Parada acumulados por Celda de Trabajo**")
        fig_b1 = px.bar(df_global, x="Min_Parada", y="Maquina", color="Falla", orientation='h', height=280)
        fig_b1.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color="#ffffff"))
        st.plotly_chart(fig_b1, use_container_width=True)
    with col_b2:
        st.markdown("**Rendimiento Operativo por Colaborador Asignado**")
        df_op_g = df_global.groupby("Operario")["Buenas"].sum().reset_index()
        fig_b2 = px.bar(df_op_g, x="Buenas", y="Operario", orientation='h', height=280, labels={"Buenas": "Piezas Buenas"})
        fig_b2.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color="#ffffff"))
        st.plotly_chart(fig_b2, use_container_width=True)

elif "6." in capa_activa:
    st.markdown("<h2 style='color: #ffffff;'>📈 Analítica Avanzada e Históricos de Planta</h2>", unsafe_allow_html=True)
    
    # Inicialización del estado de navegación
    if "sub_modulo_analisis" not in st.session_state:
        st.session_state.sub_modulo_analisis = "Disponibilidad"

    c_btn1, c_btn2, c_btn3, c_btn4 = st.columns(4)
    with c_btn1: 
        if st.button("⏱️ Disponibilidad"): st.session_state.sub_modulo_analisis = "Disponibilidad"
    with c_btn2: 
        if st.button("🛑 Paradas"): st.session_state.sub_modulo_analisis = "Paradas"
    with c_btn3: 
        if st.button("⚙️ Causas"): st.session_state.sub_modulo_analisis = "Causas"
    with c_btn4: 
        if st.button("📦 Producción"): st.session_state.sub_modulo_analisis = "Producción"
        
    st.markdown(f"### 📊 Módulo Activo: `{st.session_state.sub_modulo_analisis.upper()}`")
    
    # Verificación de datos
    if "db_historial_planta" in st.session_state and not st.session_state.db_historial_planta.empty:
        df_global = st.session_state.db_historial_planta
        import plotly.express as px
        
        if st.session_state.sub_modulo_analisis == "Disponibilidad":
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                df_calc = df_global.copy()
                df_calc["Disp_Hora"] = df_calc.apply(lambda r: round(((60 - r.get("Min_Parada", 0))/60)*100, 1), axis=1)
                fig1 = px.line(df_calc, x="Hora", y="Disp_Hora", color="Maquina", markers=True, title="Disponibilidad (%)")
                st.plotly_chart(fig1, use_container_width=True)
            with col_g2:
                fig2 = px.bar(df_global, x="Maquina", y="Min_Parada", color="Hora", title="Minutos de Parada")
                st.plotly_chart(fig2, use_container_width=True)
                
        elif st.session_state.sub_modulo_analisis == "Paradas":
            fig_paradas = px.bar(df_global, x="Hora", y="Min_Parada", color="Maquina", title="Paradas por Bloque Horario")
            st.plotly_chart(fig_paradas, use_container_width=True)
            
        elif st.session_state.sub_modulo_analisis == "Causas":
            fig_causas = px.pie(df_global, names="Falla", title="Distribución de Causas Raíz")
            st.plotly_chart(fig_causas, use_container_width=True)
            
        elif st.session_state.sub_modulo_analisis == "Producción":
            fig_prod = px.bar(df_global, x="Hora", y=["Buenas", "Retrabajo", "Observadas"], barmode="group", title="Producción por Hora")
            st.plotly_chart(fig_prod, use_container_width=True)
            
    else:
        st.info("⚠️ No hay datos registrados en el historial para generar gráficos.")
elif "7." in capa_activa:
    st.markdown("## 🚨 Monitor Andón de Planta (Tiempo Real)")
    
    # Cálculo de tiempo para Meta Proporcional
    ahora = datetime.now()
    # Asumimos turno desde las 06:00
    minutos_transcurridos_turno = (ahora.hour * 60 + ahora.minute) - (6 * 60)
    minutos_en_hora = minutos_transcurridos_turno % 60
    if minutos_en_hora == 0: minutos_en_hora = 1 # Evitar división por cero
    
    df = st.session_state.db_historial_planta
    cols = st.columns(3)
    
    for i, (maq, d) in enumerate(st.session_state.db_objetivos.items()):
        df_maq = df[df["Maquina"] == maq]
        
        # Meta dinámica por hora actual
        meta_hora_base = d.get("Meta_Hora", 60)
        meta_proporcional = round((meta_hora_base / 60) * minutos_en_hora)
        
        total_buenas = int(df_maq["Buenas"].sum())
        eficiencia_real = round((total_buenas / meta_proporcional * 100), 1) if meta_proporcional > 0 else 0.0
        oee = round(eficiencia_real * 0.95, 1) 
        
        estado = d.get("Estado_TR", "PARADA")
        operario = df_maq["Operario"].iloc[-1] if not df_maq.empty else "N/A"
        evento = d.get("Ultimo_Evento", "Ninguno")
        tiempo = "⏱️ En proceso..." # Aquí podrías vincular tu contador real
        
        color_estado = "#00cc66" if estado == "PRODUCIENDO" else ("#ffaa00" if estado == "SETUP" else "#ff4b4b")
        
        with cols[i]:
            with st.container(border=True):
                st.markdown(f"<h3 style='background-color:{color_estado}; padding:10px; border-radius:5px; color:white; text-align:center;'>{maq}</h3>", unsafe_allow_html=True)
                st.markdown(f"<div style='text-align:center;'><small>EFFICIENCY</small><br><span style='font-size:42px; font-weight:bold;'>{eficiencia_real}%</span></div>", unsafe_allow_html=True)
                st.markdown(f"<div style='text-align:center;'><small>OEE</small><br><span style='font-size:28px; font-weight:bold; color:#00f2fe;'>{oee}%</span></div>", unsafe_allow_html=True)
                st.divider()
                st.markdown(f"<div style='text-align:center;'><small>PRODUCCIÓN (REAL / META {minutos_en_hora}min)</small><br><span style='font-size:24px; font-weight:bold;'>{total_buenas} / {meta_proporcional}</span></div>", unsafe_allow_html=True)
                st.divider()
                st.caption(f"👤 Op: {operario}")
                if estado != "PRODUCIENDO":
                    st.markdown(f"<div style='background-color:{color_estado}; color:white; padding:5px; border-radius:3px; text-align:center;'><b>{estado}:</b> {evento}</div>", unsafe_allow_html=True)
                else:
                    st.success(f"🟢 {estado}")
# --- LOGICA DE MODO TV (CARRUSEL AUTOMÁTICO) ---
# Inyectamos JS para que cambie de capa cada 10 segundos
st.markdown("""
<script>
    // Buscamos los radio buttons del sidebar (los módulos licenciados)
    // Streamlit asigna índices, iteramos y hacemos clic
    var index = 0;
    setInterval(function() {
        var radios = window.parent.document.querySelectorAll('input[type="radio"]');
        if (radios.length > 0) {
            index = (index + 1) % radios.length; // Cicla entre 0 y 10 (11 vistas)
            radios[index].click();
        }
    }, 10000); // 10000ms = 10 segundos
</script>
""", unsafe_allow_html=True)