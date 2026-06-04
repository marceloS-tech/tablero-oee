import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os

# 1. CONFIGURACIÓN DE PANTALLA PRINCIPAL (Debe ser siempre la primera directiva)
st.set_page_config(page_title="SaaS OEE - Core Global de Planta", layout="wide")

# Credenciales seguras desde los Secrets (con fallback para evitar crash si no están definidas)
mqtt_user = st.secrets.get("MQTT_USER", "")
mqtt_pass = st.secrets.get("MQTT_PASS", "")

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
# 2. CONTROL DE SESIÓN Y PARED DE LOGUEO
# =========================================================================
st.sidebar.title("🔐 Autenticación SaaS")

CLIENTES_DB = {
    "supervisor_planta": {"pass": "123", "plan": ["Capa 1", "Capa 3", "Capa 4"]},
    "director_general":  {"pass": "456", "plan": ["Capa 1", "Capa 2", "Capa 3", "Capa 4", "Capa 5", "Capa 6", "Capa 7"]},
    "puesto_planta":     {"pass": "000", "plan": ["Capa 1", "Capa 7"]}
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

# Usuario autenticado
st.sidebar.markdown(f"👤 **Usuario:** `{st.session_state.usuario_conectado}`")
if st.sidebar.button("🔴 Cerrar Sesión", use_container_width=True):
    st.session_state.autenticado = False
    st.session_state.usuario_conectado = None
    st.session_state.permisos_usuario = []
    st.rerun()

st.sidebar.markdown("---")

# =========================================================================
# 3. ARQUITECTURA DE DATOS CENTRALIZADA
# =========================================================================
HORAS_TURNO = [
    "06:00-07:00", "07:00-08:00", "08:00-09:00", "09:00-10:00",
    "10:00-11:00", "11:00-12:00", "12:00-13:00", "13:00-14:00"
]

if "db_objetivos" not in st.session_state:
    st.session_state.db_objetivos = {
        "DEMOWIDEM 1 (Inyectora)":   {"Meta_Hora": 60, "Producto": "Carcasa Plástica A",   "Estado_TR": "PRODUCIENDO", "Ultimo_Evento": "Ninguno"},
        "DEMOWIDEM 2 (Banco Manual)":{"Meta_Hora": 40, "Producto": "Ensamble Eléctrico B", "Estado_TR": "SETUP",       "Ultimo_Evento": "Logística: Falta Piezas"},
        "DEMOWIDEM 3 (Prensa)":      {"Meta_Hora": 80, "Producto": "Soporte Metálico C",   "Estado_TR": "PARADA",      "Ultimo_Evento": "Mantenimiento: Falla Mecánica"}
    }

if "db_historial_planta" not in st.session_state:
    st.session_state.db_historial_planta = pd.DataFrame([
        {"Hora": "06:00-07:00", "Maquina": "DEMOWIDEM 1 (Inyectora)",    "Tipo": "Automático", "Operario": "VILLARROEL ENZO",    "Meta": 60, "Buenas": 58, "Retrabajo": 1, "Observadas": 1, "Min_Parada": 0,  "Falla": "Ninguna",           "Es_Falla_Tecnica": False, "Validado": True},
        {"Hora": "07:00-08:00", "Maquina": "DEMOWIDEM 1 (Inyectora)",    "Tipo": "Automático", "Operario": "VILLARROEL ENZO",    "Meta": 60, "Buenas": 59, "Retrabajo": 0, "Observadas": 1, "Min_Parada": 0,  "Falla": "Ninguna",           "Es_Falla_Tecnica": False, "Validado": True},
        {"Hora": "08:00-09:00", "Maquina": "DEMOWIDEM 1 (Inyectora)",    "Tipo": "Automático", "Operario": "VILLARROEL ENZO",    "Meta": 60, "Buenas": 38, "Retrabajo": 2, "Observadas": 0, "Min_Parada": 15, "Falla": "Falla Robótica",    "Es_Falla_Tecnica": True,  "Validado": False},
        {"Hora": "06:00-07:00", "Maquina": "DEMOWIDEM 2 (Banco Manual)", "Tipo": "Manual",     "Operario": "FRANCO MAXIMILIANO", "Meta": 40, "Buenas": 35, "Retrabajo": 2, "Observadas": 1, "Min_Parada": 5,  "Falla": "Ajuste de Utillaje","Es_Falla_Tecnica": False, "Validado": True},
        {"Hora": "07:00-08:00", "Maquina": "DEMOWIDEM 2 (Banco Manual)", "Tipo": "Manual",     "Operario": "FRANCO MAXIMILIANO", "Meta": 40, "Buenas": 38, "Retrabajo": 1, "Observadas": 0, "Min_Parada": 0,  "Falla": "Ninguna",           "Es_Falla_Tecnica": False, "Validado": True},
        {"Hora": "08:00-09:00", "Maquina": "DEMOWIDEM 2 (Banco Manual)", "Tipo": "Manual",     "Operario": "FRANCO MAXIMILIANO", "Meta": 40, "Buenas": 22, "Retrabajo": 3, "Observadas": 0, "Min_Parada": 20, "Falla": "Falta de Material", "Es_Falla_Tecnica": False, "Validado": False},
        {"Hora": "06:00-07:00", "Maquina": "DEMOWIDEM 3 (Prensa)",       "Tipo": "Automático", "Operario": "GOMEZ RODRIGO",      "Meta": 80, "Buenas": 75, "Retrabajo": 2, "Observadas": 3, "Min_Parada": 0,  "Falla": "Ninguna",           "Es_Falla_Tecnica": False, "Validado": True},
        {"Hora": "07:00-08:00", "Maquina": "DEMOWIDEM 3 (Prensa)",       "Tipo": "Automático", "Operario": "GOMEZ RODRIGO",      "Meta": 80, "Buenas": 45, "Retrabajo": 4, "Observadas": 1, "Min_Parada": 30, "Falla": "Falla Mecánica",    "Es_Falla_Tecnica": True,  "Validado": False},
    ])

MAQUINAS = list(st.session_state.db_objetivos.keys())
PERMISOS = st.session_state.permisos_usuario

# =========================================================================
# 4. FUNCIONES AUXILIARES DE CÁLCULO OEE
# =========================================================================
def calcular_oee(df_maquina):
    """Calcula Disponibilidad, Rendimiento, Calidad y OEE para una máquina."""
    if df_maquina.empty:
        return 0.0, 0.0, 0.0, 0.0

    total_horas = len(df_maquina)
    tiempo_total_min = total_horas * 60
    tiempo_parada = df_maquina["Min_Parada"].sum()
    tiempo_operativo = max(tiempo_total_min - tiempo_parada, 0)

    disponibilidad = (tiempo_operativo / tiempo_total_min * 100) if tiempo_total_min > 0 else 0

    total_producido = df_maquina["Buenas"].sum() + df_maquina["Retrabajo"].sum() + df_maquina["Observadas"].sum()
    meta_total = df_maquina["Meta"].sum()
    rendimiento = (total_producido / meta_total * 100) if meta_total > 0 else 0

    total_buenas = df_maquina["Buenas"].sum()
    calidad = (total_buenas / total_producido * 100) if total_producido > 0 else 0

    oee = (disponibilidad / 100) * (rendimiento / 100) * (calidad / 100) * 100

    return round(disponibilidad, 1), round(rendimiento, 1), round(calidad, 1), round(oee, 1)


def color_oee(valor):
    if valor >= 85:
        return "#00cc66"
    elif valor >= 65:
        return "#ffaa00"
    else:
        return "#ff4b4b"


def gauge_plotly(valor, titulo, max_val=100):
    color = color_oee(valor)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=valor,
        number={"suffix": "%", "font": {"size": 28, "color": color}},
        gauge={
            "axis": {"range": [0, max_val], "tickcolor": "#8b949e", "tickfont": {"color": "#8b949e"}},
            "bar": {"color": color},
            "bgcolor": "#161b22",
            "bordercolor": "#30363d",
            "steps": [
                {"range": [0, 65],  "color": "#2d1215"},
                {"range": [65, 85], "color": "#2b220c"},
                {"range": [85, 100],"color": "#0c2519"},
            ],
            "threshold": {"line": {"color": color, "width": 3}, "thickness": 0.75, "value": valor}
        }
    ))
    fig.update_layout(
        paper_bgcolor="#0d1117", font_color="#ffffff",
        margin=dict(t=30, b=10, l=20, r=20), height=200
    )
    return fig


# =========================================================================
# 5. NAVEGACIÓN POR CAPAS EN SIDEBAR
# =========================================================================
CAPAS_DISPONIBLES = {
    "Capa 1": "🟢 Andon Wall (Tiempo Real)",
    "Capa 2": "📊 OEE Global de Planta",
    "Capa 3": "🔍 Análisis por Máquina",
    "Capa 4": "📋 Carga de Producción",
    "Capa 5": "⚠️ Gestión de Fallas",
    "Capa 6": "⚙️ Configuración de Metas",
    "Capa 7": "📺 Modo TV / Pantalla Pública",
}

capas_accesibles = [k for k in CAPAS_DISPONIBLES if k in PERMISOS]

st.sidebar.markdown("### 🗂️ Módulos Activos")
seleccion = st.sidebar.radio(
    "Navegación:",
    options=capas_accesibles,
    format_func=lambda x: CAPAS_DISPONIBLES[x],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
st.sidebar.caption(f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}")

# =========================================================================
# CAPA 1 — ANDON WALL (TIEMPO REAL)
# =========================================================================
if seleccion == "Capa 1":
    st.title("🟢 Andon Wall — Estado en Tiempo Real")
    st.caption("Vista operativa de todas las máquinas activas en planta")

    df = st.session_state.db_historial_planta
    objetivos = st.session_state.db_objetivos

    for maquina, datos in objetivos.items():
        estado = datos["Estado_TR"]
        producto = datos["Producto"]
        meta_hora = datos["Meta_Hora"]
        ultimo_evento = datos["Ultimo_Evento"]

        df_maq = df[df["Maquina"] == maquina]
        buenas_turno = int(df_maq["Buenas"].sum()) if not df_maq.empty else 0
        meta_turno = int(df_maq["Meta"].sum()) if not df_maq.empty else 0
        diferencia = buenas_turno - meta_turno

        if estado == "PRODUCIENDO":
            clase_card = "andon-marcha"
            icono = "🟢"
            badge_clase = "badge-v"
        elif estado == "SETUP":
            clase_card = "andon-setup"
            icono = "🟡"
            badge_clase = "badge-a"
        else:
            clase_card = "andon-parada"
            icono = "🔴"
            badge_clase = "badge-r"

        signo = "+" if diferencia >= 0 else ""
        color_dif = "#00cc66" if diferencia >= 0 else "#ff4b4b"

        st.markdown(f"""
        <div class="andon-card {clase_card}">
            <div class="andon-header">
                <span>{icono} {maquina}</span>
                <span class="wiidem-badge {badge_clase}">{estado}</span>
            </div>
            <div style="color:#8b949e; font-size:13px;">Producto: {producto} | Meta/hora: {meta_hora} uds.</div>
            <div class="andon-meta-box">
                <b>Producción Turno:</b>
                &nbsp;&nbsp;✅ Buenas: <b style="color:#00f2fe">{buenas_turno}</b>
                &nbsp;&nbsp;🎯 Meta: <b>{meta_turno}</b>
                &nbsp;&nbsp;Δ: <b style="color:{color_dif}">{signo}{diferencia}</b>
                &nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;
                📌 Último evento: <i>{ultimo_evento}</i>
            </div>
        </div>
        """, unsafe_allow_html=True)

# =========================================================================
# CAPA 2 — OEE GLOBAL DE PLANTA
# =========================================================================
elif seleccion == "Capa 2":
    st.title("📊 OEE Global de Planta")
    st.caption("Indicadores consolidados de Disponibilidad, Rendimiento y Calidad")

    df = st.session_state.db_historial_planta

    disp_total, rend_total, cal_total, oee_total = [], [], [], []

    for maquina in MAQUINAS:
        df_m = df[df["Maquina"] == maquina]
        d, r, c, o = calcular_oee(df_m)
        disp_total.append(d)
        rend_total.append(r)
        cal_total.append(c)
        oee_total.append(o)

    d_p = round(sum(disp_total) / len(disp_total), 1)
    r_p = round(sum(rend_total) / len(rend_total), 1)
    c_p = round(sum(cal_total) / len(cal_total), 1)
    o_p = round(sum(oee_total) / len(oee_total), 1)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown('<div class="gauge-title">DISPONIBILIDAD</div>', unsafe_allow_html=True)
        st.plotly_chart(gauge_plotly(d_p, "Disponibilidad"), use_container_width=True, key="g_disp")
    with col2:
        st.markdown('<div class="gauge-title">RENDIMIENTO</div>', unsafe_allow_html=True)
        st.plotly_chart(gauge_plotly(r_p, "Rendimiento"), use_container_width=True, key="g_rend")
    with col3:
        st.markdown('<div class="gauge-title">CALIDAD</div>', unsafe_allow_html=True)
        st.plotly_chart(gauge_plotly(c_p, "Calidad"), use_container_width=True, key="g_cal")
    with col4:
        st.markdown('<div class="gauge-title">OEE GLOBAL</div>', unsafe_allow_html=True)
        st.plotly_chart(gauge_plotly(o_p, "OEE"), use_container_width=True, key="g_oee")

    st.markdown("---")
    st.subheader("OEE por Máquina")

    filas = []
    for maquina in MAQUINAS:
        df_m = df[df["Maquina"] == maquina]
        d, r, c, o = calcular_oee(df_m)
        filas.append({"Máquina": maquina, "Disponibilidad %": d, "Rendimiento %": r, "Calidad %": c, "OEE %": o})

    df_tabla = pd.DataFrame(filas)

    fig_bar = px.bar(
        df_tabla.melt(id_vars="Máquina", var_name="Indicador", value_name="Valor"),
        x="Máquina", y="Valor", color="Indicador", barmode="group",
        color_discrete_sequence=["#00f2fe", "#00cc66", "#ffaa00", "#ff4b4b"],
        template="plotly_dark"
    )
    fig_bar.update_layout(paper_bgcolor="#0d1117", plot_bgcolor="#161b22", font_color="#c9d1d9")
    st.plotly_chart(fig_bar, use_container_width=True)

    st.dataframe(
        df_tabla.style.applymap(
            lambda v: f"color: {color_oee(v)}" if isinstance(v, (int, float)) else "",
            subset=["Disponibilidad %", "Rendimiento %", "Calidad %", "OEE %"]
        ),
        use_container_width=True
    )

# =========================================================================
# CAPA 3 — ANÁLISIS POR MÁQUINA
# =========================================================================
elif seleccion == "Capa 3":
    st.title("🔍 Análisis Detallado por Máquina")

    maquina_sel = st.selectbox("Seleccionar máquina:", MAQUINAS)
    df = st.session_state.db_historial_planta
    df_m = df[df["Maquina"] == maquina_sel].copy()

    d, r, c, o = calcular_oee(df_m)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Disponibilidad", f"{d}%")
    col2.metric("Rendimiento", f"{r}%")
    col3.metric("Calidad", f"{c}%")
    col4.metric("OEE", f"{o}%")

    st.markdown("---")

    if not df_m.empty:
        fig_prod = px.bar(
            df_m, x="Hora",
            y=["Buenas", "Retrabajo", "Observadas"],
            barmode="stack",
            color_discrete_sequence=["#00cc66", "#ffaa00", "#ff4b4b"],
            title=f"Producción por hora — {maquina_sel}",
            template="plotly_dark"
        )
        fig_prod.update_layout(paper_bgcolor="#0d1117", plot_bgcolor="#161b22")
        st.plotly_chart(fig_prod, use_container_width=True)

        fig_parada = px.bar(
            df_m, x="Hora", y="Min_Parada",
            color="Falla",
            title="Minutos de parada por hora",
            template="plotly_dark"
        )
        fig_parada.update_layout(paper_bgcolor="#0d1117", plot_bgcolor="#161b22")
        st.plotly_chart(fig_parada, use_container_width=True)

        st.subheader("Detalle por hora")
        st.dataframe(df_m[["Hora", "Operario", "Meta", "Buenas", "Retrabajo", "Observadas", "Min_Parada", "Falla", "Validado"]], use_container_width=True)
    else:
        st.info("Sin datos registrados para esta máquina.")

# =========================================================================
# CAPA 4 — CARGA DE PRODUCCIÓN
# =========================================================================
elif seleccion == "Capa 4":
    st.title("📋 Carga de Producción")
    st.caption("Ingrese los datos de producción hora a hora")

    with st.form("form_carga"):
        col1, col2 = st.columns(2)
        with col1:
            maquina_f   = st.selectbox("Máquina:", MAQUINAS)
            hora_f      = st.selectbox("Hora:", HORAS_TURNO)
            operario_f  = st.text_input("Operario:", placeholder="APELLIDO NOMBRE")
            tipo_f      = st.selectbox("Tipo:", ["Automático", "Manual", "Semi-automático"])
        with col2:
            meta_f      = st.number_input("Meta:", min_value=0, value=int(st.session_state.db_objetivos[MAQUINAS[0]]["Meta_Hora"]))
            buenas_f    = st.number_input("Piezas Buenas:", min_value=0, value=0)
            retrabajo_f = st.number_input("Retrabajo:", min_value=0, value=0)
            observadas_f= st.number_input("Observadas:", min_value=0, value=0)
            min_parada_f= st.number_input("Minutos de Parada:", min_value=0, value=0)
            falla_f     = st.text_input("Descripción de Falla:", value="Ninguna")
            tecnica_f   = st.checkbox("¿Es falla técnica?")

        submitted = st.form_submit_button("✅ Registrar Hora", use_container_width=True)

    if submitted:
        nueva_fila = {
            "Hora": hora_f, "Maquina": maquina_f, "Tipo": tipo_f,
            "Operario": operario_f.upper(), "Meta": meta_f,
            "Buenas": buenas_f, "Retrabajo": retrabajo_f,
            "Observadas": observadas_f, "Min_Parada": min_parada_f,
            "Falla": falla_f, "Es_Falla_Tecnica": tecnica_f, "Validado": False
        }
        st.session_state.db_historial_planta = pd.concat(
            [st.session_state.db_historial_planta, pd.DataFrame([nueva_fila])],
            ignore_index=True
        )
        st.success(f"✅ Hora {hora_f} de {maquina_f} registrada correctamente.")
        st.rerun()

    st.markdown("---")
    st.subheader("Historial del turno (sin validar)")
    df_pend = st.session_state.db_historial_planta[~st.session_state.db_historial_planta["Validado"]]
    if not df_pend.empty:
        st.dataframe(df_pend, use_container_width=True)
    else:
        st.info("No hay registros pendientes de validación.")

# =========================================================================
# CAPA 5 — GESTIÓN DE FALLAS
# =========================================================================
elif seleccion == "Capa 5":
    st.title("⚠️ Gestión de Fallas y Paradas")

    df = st.session_state.db_historial_planta
    df_fallas = df[df["Falla"] != "Ninguna"].copy()

    if df_fallas.empty:
        st.success("✅ No se registraron fallas en el turno actual.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total de eventos de parada", len(df_fallas))
        with col2:
            st.metric("Minutos perdidos totales", int(df_fallas["Min_Parada"].sum()))

        st.markdown("---")

        fig_pareto = px.bar(
            df_fallas.groupby("Falla")["Min_Parada"].sum().reset_index().sort_values("Min_Parada", ascending=False),
            x="Falla", y="Min_Parada",
            title="Pareto de Fallas (por minutos perdidos)",
            color="Min_Parada",
            color_continuous_scale=["#ffaa00", "#ff4b4b"],
            template="plotly_dark"
        )
        fig_pareto.update_layout(paper_bgcolor="#0d1117", plot_bgcolor="#161b22")
        st.plotly_chart(fig_pareto, use_container_width=True)

        st.subheader("Detalle de eventos")
        st.dataframe(
            df_fallas[["Hora", "Maquina", "Operario", "Falla", "Min_Parada", "Es_Falla_Tecnica", "Validado"]],
            use_container_width=True
        )

        st.markdown("---")
        st.subheader("Validar registros")
        idx_a_validar = st.multiselect(
            "Seleccionar filas a validar (por índice):",
            options=df_fallas.index.tolist()
        )
        if st.button("✅ Marcar como validado"):
            st.session_state.db_historial_planta.loc[idx_a_validar, "Validado"] = True
            st.success("Registros validados correctamente.")
            st.rerun()

# =========================================================================
# CAPA 6 — CONFIGURACIÓN DE METAS
# =========================================================================
elif seleccion == "Capa 6":
    st.title("⚙️ Configuración de Metas y Productos")

    objetivos = st.session_state.db_objetivos

    for maquina, datos in objetivos.items():
        st.subheader(f"🔧 {maquina}")
        with st.form(f"form_config_{maquina}"):
            col1, col2, col3 = st.columns(3)
            with col1:
                nueva_meta = st.number_input("Meta por hora (uds.):", value=datos["Meta_Hora"], min_value=1, key=f"meta_{maquina}")
            with col2:
                nuevo_producto = st.text_input("Producto:", value=datos["Producto"], key=f"prod_{maquina}")
            with col3:
                nuevo_estado = st.selectbox("Estado Tiempo Real:", ["PRODUCIENDO", "SETUP", "PARADA"], index=["PRODUCIENDO","SETUP","PARADA"].index(datos["Estado_TR"]), key=f"est_{maquina}")

            nuevo_evento = st.text_input("Último evento:", value=datos["Ultimo_Evento"], key=f"ev_{maquina}")

            if st.form_submit_button(f"💾 Guardar cambios — {maquina}"):
                st.session_state.db_objetivos[maquina]["Meta_Hora"]    = nueva_meta
                st.session_state.db_objetivos[maquina]["Producto"]      = nuevo_producto
                st.session_state.db_objetivos[maquina]["Estado_TR"]     = nuevo_estado
                st.session_state.db_objetivos[maquina]["Ultimo_Evento"] = nuevo_evento
                st.success(f"✅ Configuración de {maquina} guardada.")
                st.rerun()

        st.markdown("---")

# =========================================================================
# CAPA 7 — MODO TV / PANTALLA PÚBLICA
# =========================================================================
elif seleccion == "Capa 7":
    st.title("📺 Modo TV — Pantalla Pública de Planta")
    st.caption("Vista simplificada para pantallas en piso de producción")

    st.markdown(JS_AUTOMATIZACION, unsafe_allow_html=True)

    df = st.session_state.db_historial_planta
    objetivos = st.session_state.db_objetivos

    col_tv = st.columns(len(MAQUINAS))

    for i, (maquina, datos) in enumerate(objetivos.items()):
        with col_tv[i]:
            estado = datos["Estado_TR"]
            df_m = df[df["Maquina"] == maquina]
            buenas = int(df_m["Buenas"].sum()) if not df_m.empty else 0
            meta = int(df_m["Meta"].sum()) if not df_m.empty else 0
            _, _, _, oee = calcular_oee(df_m)

            color_estado = {"PRODUCIENDO": "#00cc66", "SETUP": "#ffaa00", "PARADA": "#ff4b4b"}.get(estado, "#8b949e")

            st.markdown(f"""
            <div class="vorne-card" style="border-top: 6px solid {color_estado}; text-align:center;">
                <div style="font-size:16px; color:#8b949e; font-family:monospace;">{maquina}</div>
                <div style="font-size:13px; color:#8b949e; margin-bottom:10px;">{datos['Producto']}</div>
                <div style="font-size:48px; font-weight:bold; color:#00f2fe;">{buenas}</div>
                <div style="font-size:13px; color:#8b949e;">PIEZAS BUENAS / TURNO</div>
                <div style="font-size:22px; font-weight:bold; color:{color_estado}; margin-top:10px;">{estado}</div>
                <div style="font-size:13px; color:#8b949e; margin-top:6px;">OEE: <b style="color:{color_oee(oee)}">{oee}%</b> &nbsp;|&nbsp; Meta turno: {meta}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f"<div style='text-align:center; color:#8b949e; font-family:monospace; font-size:12px;'>Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} | SaaS OEE - Plataforma WIIDEM</div>", unsafe_allow_html=True)