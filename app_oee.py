import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import json

# 1. CONFIGURACIÓN DE PANTALLA PRINCIPAL
st.set_page_config(page_title="SaaS OEE - Core Global de Planta", layout="wide")

# Credenciales desde los Secrets
mqtt_user = st.secrets["MQTT_USER"]
mqtt_pass = st.secrets["MQTT_PASS"]

# Archivos de persistencia de datos
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
# RECEPTOR IOT URL (Para el ESP32)
# =========================================================================
query_params = st.query_params

if "evento" in query_params and query_params["evento"] == "golpe":
    maquina_param = query_params.get("maquina", "M1")
    maquina_nombre = "DEMOWIDEM 1 (Inyectora)"
    if maquina_param == "M2": maquina_nombre = "DEMOWIDEM 2 (Banco Manual)"
    if maquina_param == "M3": maquina_nombre = "DEMOWIDEM 3 (Prensa)"
    
    # Sumar pieza en el CSV
    if os.path.exists(HISTORIAL_FILE):
        df_db = pd.read_csv(HISTORIAL_FILE)
        filas_maquina = df_db["Maquina"] == maquina_nombre
        if filas_maquina.any():
            ultimo_idx = df_db[filas_maquina].index[-1]
            df_db.at[ultimo_idx, "Buenas"] += 1
            df_db.to_csv(HISTORIAL_FILE, index=False)
            
    # Modificar estado en el JSON
    if os.path.exists(OBJETIVOS_FILE):
        with open(OBJETIVOS_FILE, "r", encoding="utf-8") as f:
            objs_db = json.load(f)
        if maquina_nombre in objs_db:
            objs_db[maquina_nombre]["Estado_TR"] = "PRODUCIENDO"
            objs_db[maquina_nombre]["Ultimo_Evento"] = f"Golpe IoT ({datetime.now().strftime('%H:%M:%S')})"
        with open(OBJETIVOS_FILE, "w", encoding="utf-8") as f:
            json.dump(objs_db, f, indent=4, ensure_ascii=False)
            
    st.text(f"OK - {maquina_nombre}")
    st.stop()

# =========================================================================
# ESTILOS INTERFAZ
# =========================================================================
ESTILOS_CSS = """
<style>
    .stApp { background-color: #0d1117; color: #ffffff; }
    div[data-testid="stMetricValue"] { font-size: 32px; font-weight: bold; color: #00f2fe; }
    .andon-card { border-radius: 8px; padding: 20px; margin-bottom: 15px; border: 1px solid #30363d; font-family: monospace; }
    .andon-marcha { background-color: #0c2519; border-left: 8px solid #00cc66; }
    .andon-setup { background-color: #2b220c; border-left: 8px solid #ffaa00; }
    .andon-parada { background-color: #2d1215; border-left: 8px solid #ff4b4b; }
    .andon-header { font-size: 20px; font-weight: bold; display: flex; justify-content: space-between; align-items: center; }
    .andon-meta-box { background: #1f242c; padding: 10px; border-radius: 4px; border: 1px solid #30363d; font-size: 13px; margin-top: 12px; }
    .wiidem-badge { display: inline-block; padding: 4px 8px; font-weight: bold; border-radius: 4px; font-size: 12px; color: #000; }
    .badge-v { background-color: #00cc66; }
    .badge-a { background-color: #ffaa00; }
    .badge-r { background-color: #ff4b4b; }
</style>
"""
st.markdown(ESTILOS_CSS, unsafe_allow_html=True)

# =========================================================================
# ACCESO Y LOGUEO
# =========================================================================
st.sidebar.title("🔐 Autenticación SaaS")
CLIENTES_DB = {
    "supervisor_planta": {"pass": "123", "plan": ["Capa 1", "Capa 3", "Capa 4"]},
    "director_general": {"pass": "456", "plan": ["Capa 1", "Capa 2", "Capa 3", "Capa 4", "Capa 5", "Capa 6", "Capa 7"]},
    "puesto_planta": {"pass": "000", "plan": ["Capa 1", "Capa 7"]}
}

if "autenticado" not in st.session_state: st.session_state.autenticado = False

if not st.session_state.autenticado:
    user_input = st.sidebar.text_input("Usuario:")
    pass_input = st.sidebar.text_input("Contraseña:", type="password")
    if st.sidebar.button("Ingresar"):
        if user_input in CLIENTES_DB and CLIENTES_DB[user_input]["pass"] == pass_input:
            st.session_state.usuario_conectado = user_input
            st.session_state.permisos_usuario = CLIENTES_DB[user_input]["plan"]
            st.session_state.autenticado = True
            st.rerun()
    st.warning("Introduzca credenciales en el lateral para activar el panel.")
    st.stop()

# =========================================================================
# LECTURA DE ARCHIVOS VIVOS
# =========================================================================
df_global = pd.read_csv(HISTORIAL_FILE)
with open(OBJETIVOS_FILE, "r", encoding="utf-8") as f:
    db_objetivos = json.load(f)

# SELECTOR DE CAPAS
st.sidebar.title("🎛️ Módulos")
capa_mapeada = {
    "1. Monitor de Máquina": "Capa 1",
    "2. Configuración Ingeniería": "Capa 2",
    "3. Terminal de Operario": "Capa 3",
    "4. Validación Supervisor": "Capa 4",
    "5. Vista General Dirección": "Capa 5",
    "6. Análisis de Datos (BI)": "Capa 6",
    "7. Andón Digital (Tiempo Real)": "Capa 7"
}
capa_activa = st.sidebar.radio("Nivel de pantalla:", list(capa_mapeada.keys()), index=6) # Por defecto entra al Andón

if capa_mapeada[capa_activa] not in st.session_state.permisos_usuario:
    st.error("🔒 Módulo No Contratado para este perfil.")
    st.stop()

# =========================================================================
# RENDERS DE CAPAS (Reducido para optimizar foco en Capa 7)
# =========================================================================
if "7." in capa_activa:
    st.markdown("## 🚨 Monitor Andón de Planta (Tiempo Real)")
    
    # Simulación de tiempo de turno para metas parciales
    ahora = datetime.now()
    minutos_en_hora = ahora.minute if ahora.minute > 0 else 1
    
    cols = st.columns(3)
    for i, (maq, d) in enumerate(db_objetivos.items()):
        df_maq = df_global[df_global["Maquina"] == maq]
        meta_hora_base = d.get("Meta_Hora", 60)
        meta_proporcional = max(1, round((meta_hora_base / 60) * minutos_en_hora))
        total_buenas = int(df_maq["Buenas"].sum())
        eficiencia_real = round((total_buenas / meta_proporcional * 100), 1)
        
        estado = d.get("Estado_TR", "PARADA")
        evento = d.get("Ultimo_Evento", "Ninguno")
        
        clase_andon = "andon-marcha" if estado == "PRODUCIENDO" else ("andon-setup" if estado == "SETUP" else "andon-parada")
        badge_color = "badge-v" if estado == "PRODUCIENDO" else ("badge-a" if estado == "SETUP" else "badge-r")
        
        html_code = f"""
        <div class="andon-card {clase_andon}">
            <div class="andon-header">
                <span>{maq}</span>
                <span class="wiidem-badge {badge_color}">{estado}</span>
            </div>
            <div style="margin-top:12px; font-size:13px; color:#8b949e;">PRODUCTO: <b>{d.get('Producto','-')}</b></div>
            <div class="andon-meta-box">
                <table style="width:100%; color:#c9d1d9; border-collapse:collapse;">
                    <tr><td><b>EFICIENCIA:</b></td><td style="text-align:right; color:#00cc66; font-size:16px;"><b>{eficiencia_real}%</b></td></tr>
                </table>
            </div>
            <div class="andon-meta-box">
                <table style="width:100%; font-size:12px; border-collapse:collapse;">
                    <tr><td>META PARCIAL ({minutos_en_hora} min):</td><td style="text-align:right;"><b>{meta_proporcional} pz</b></td></tr>
                    <tr><td>REAL LOGRADO:</td><td style="text-align:right; color:#00f2fe;"><b>{total_buenas} pz</b></td></tr>
                </table>
            </div>
            <div style="font-size:11px; color:#8b949e; margin-top:10px;">🚨 ÚLTIMO EVENTO: {evento}</div>
        </div>
        """
        with cols[i]: 
            st.markdown(html_code, unsafe_allow_html=True)

else:
    st.info(f"Pantalla base cargada para {capa_activa}. Enfocando pruebas en módulo 7.")

# =========================================================================
# SCRIPT DE REFRESCO SEGURO (Evita el bucle infinito en el navegador)
# =========================================================================
JS_REFRESCO_SEGURO = """
<script>
    if (!window.andonRefreshSet) {
        window.andonRefreshSet = true;
        setInterval(function() {
            var reloadButton = window.parent.document.querySelector('button[title="Refresh"]');
            if (reloadButton) { reloadButton.click(); }
        }, 3000); // Intento de refresh cada 3 segundos estable
    }
</script>
"""
st.markdown(JS_REFRESCO_SEGURO, unsafe_allow_html=True)