import streamlit as st
import pandas as pd
from datetime import datetime
import paho.mqtt.client as mqtt
import os
import time

# 1. CONFIGURACIÓN DE PANTALLA
st.set_page_config(page_title="SaaS OEE Industrial - Core Global", layout="wide")

# =========================================================================
# CONTENEDOR GLOBAL EN MEMORIA (Estado de Planta interconectado)
# =========================================================================
@st.cache_resource
def obtener_estado_global():
    # Agregamos "Ultimo_TS" (Timestamp) para controlar el tiempo entre golpes
    return {
        "DEMOWIDEM 1 (Inyectora)": {"Buenas": 0, "Meta": 60, "Estado": "PRODUCIENDO", "Producto": "Carcasa Plástica A", "Ultimo": "Esperando primer golpe MQTT...", "Retrabajos": 2, "Paradas_Min": 0, "Ultimo_TS": 0.0},
        "DEMOWIDEM 2 (Banco Manual)": {"Buenas": 15, "Meta": 40, "Estado": "SETUP", "Producto": "Ensamble Eléctrico B", "Ultimo": "Sin eventos recientes", "Retrabajos": 1, "Paradas_Min": 12, "Ultimo_TS": 0.0},
        "DEMOWIDEM 3 (Prensa)": {"Buenas": 42, "Meta": 80, "Estado": "PARADA", "Producto": "Soporte Metálico C", "Ultimo": "Mantenimiento en zona", "Retrabajos": 4, "Paradas_Min": 25, "Ultimo_TS": 0.0}
    }

estado_planta = obtener_estado_global()

if "historial_eventos" not in st.session_state:
    st.session_state.historial_eventos = [
        {"Hora": "10:15", "Maquina": "DEMOWIDEM 2 (Banco Manual)", "Tipo": "Falta de Material", "Duracion": 12, "Validado": True},
        {"Hora": "10:30", "Maquina": "DEMOWIDEM 3 (Prensa)", "Tipo": "Falla Mecánica Prensa", "Duracion": 25, "Validado": False}
    ]

# =========================================================================
# HILO DE ESCUCHA MQTT CON FILTRO DE DEBOUNCE (ANTI-REBOTE)
# =========================================================================
@st.cache_resource
def iniciar_escucha_hivemq():
    try:
        broker = st.secrets["MQTT_BROKER"]
        user = st.secrets["MQTT_USER"]
        password = st.secrets["MQTT_PASS"]
        
        cliente = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        cliente.username_pw_set(user, password)
        
        def on_message(client, userdata, msg):
            payload = msg.payload.decode("utf-8")
            ahora_str = datetime.now().strftime("%H:%M:%S")
            ahora_ts = time.time() # Tiempo actual en segundos de alta precisión
            
            # Filtro: 0.5 segundos de tolerancia mínima entre golpes legítimos
            if payload == "M1":
                if ahora_ts - estado_planta["DEMOWIDEM 1 (Inyectora)"]["Ultimo_TS"] > 0.5:
                    estado_planta["DEMOWIDEM 1 (Inyectora)"]["Buenas"] += 1
                    estado_planta["DEMOWIDEM 1 (Inyectora)"]["Ultimo"] = f"Golpe ESP32 recibido -> {ahora_str}"
                    estado_planta["DEMOWIDEM 1 (Inyectora)"]["Ultimo_TS"] = ahora_ts
            elif payload == "M2":
                if ahora_ts - estado_planta["DEMOWIDEM 2 (Banco Manual)"]["Ultimo_TS"] > 0.5:
                    estado_planta["DEMOWIDEM 2 (Banco Manual)"]["Buenas"] += 1
                    estado_planta["DEMOWIDEM 2 (Banco Manual)"]["Ultimo"] = f"Golpe ESP32 recibido -> {ahora_str}"
                    estado_planta["DEMOWIDEM 2 (Banco Manual)"]["Ultimo_TS"] = ahora_ts
            elif payload == "M3":
                if ahora_ts - estado_planta["DEMOWIDEM 3 (Prensa)"]["Ultimo_TS"] > 0.5:
                    estado_planta["DEMOWIDEM 3 (Prensa)"]["Buenas"] += 1
                    estado_planta["DEMOWIDEM 3 (Prensa)"]["Ultimo"] = f"Golpe ESP32 recibido -> {ahora_str}"
                    estado_planta["DEMOWIDEM 3 (Prensa)"]["Ultimo_TS"] = ahora_ts

        cliente.on_message = on_message
        cliente.tls_set() 
        cliente.connect(broker, 8883)
        cliente.subscribe("planta/golpes")
        cliente.loop_start()
        return cliente
    except Exception as e:
        return None

mqtt_client = iniciar_escucha_hivemq()

# =========================================================================
# DISEÑO E INYECCIÓN DE ESTILOS CSS INDUSTRIALES
# =========================================================================
st.markdown("""
<style>
    .stApp { background-color: #0d1117; color: #ffffff; }
    .andon-card { border-radius: 8px; padding: 20px; margin-bottom: 15px; border: 1px solid #30363d; font-family: monospace; }
    .andon-marcha { background-color: #0c2519; border-left: 8px solid #00cc66; }
    .andon-setup { background-color: #2b220c; border-left: 8px solid #ffaa00; }
    .andon-parada { background-color: #2d1215; border-left: 8px solid #ff4b4b; }
    .andon-header { font-size: 18px; font-weight: bold; display: flex; justify-content: space-between; align-items: center; }
    .andon-meta-box { background: #1f242c; padding: 8px; border-radius: 4px; border: 1px solid #30363d; font-size: 13px; margin-top: 10px; }
    .wiidem-badge { display: inline-block; padding: 3px 8px; font-weight: bold; border-radius: 4px; font-size: 11px; color: #000; }
    .badge-v { background-color: #00cc66; }
    .badge-a { background-color: #ffaa00; }
    .badge-r { background-color: #ff4b4b; }
</style>
""", unsafe_allow_html=True)

# =========================================================================
# INTERFAZ Y MENÚ LATERAL
# =========================================================================
st.sidebar.title("🎛️ Ecosistema SaaS OEE")
capas = {
    "Capa 1: Monitor de Máquina (Línea)": 1,
    "Capa 2: Configuración Ingeniería": 2,
    "Capa 3: Terminal de Operario": 3,
    "Capa 4: Validación Supervisor": 4,
    "Capa 5: Vista General Dirección": 5,
    "Capa 6: Análisis de Datos (BI)": 6,
    "Capa 7: Andón Digital (Tiempo Real)": 7
}
capa_seleccionada = st.sidebar.radio("Seleccionar módulo:", list(capas.keys()), index=6)

if mqtt_client is None:
    st.sidebar.error("⚠️ Alerta: Servidor MQTT desconectado. Revisar Secrets.")
else:
    st.sidebar.success("⚡ Conexión MQTT en segundo plano: ACTIVA")

# =========================================================================
# NÚCLEO DINÁMICO: CON AUTO-REFRESCO CADA 2 SEGUNDOS
# =========================================================================
@st.fragment(run_every=2)
def renderizar_capa_activa(id_capa):
    
    if id_capa == 1:
        st.title("📊 Capa 1: Monitor de Celdas e Inyecciones")
        maq_sel = st.selectbox("Seleccione Máquina para inspección técnica:", list(estado_planta.keys()))
        datos = estado_planta[maq_sel]
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Piezas Fabricadas", f"{datos['Buenas']} pz")
        c2.metric("Meta del Turno", f"{datos['Meta']} pz")
        pct = min(1.0, datos['Buenas'] / datos['Meta']) if datos['Meta'] > 0 else 0
        c3.metric("Progreso de Eficiencia", f"{round(pct*100, 1)}%")
        st.progress(pct)
        st.info(f"Última trama de telemetría: {datos['Ultimo']}")

    elif id_capa == 2:
        st.title("🛠️ Capa 2: Panel de Ingeniería y Procesos")
        maq_sel = st.selectbox("Máquina a modificar:", list(estado_planta.keys()))
        meta_nueva = st.number_input("Establecer nueva Meta Horaria:", min_value=1, value=int(estado_planta[maq_sel]["Meta"]))
        prod_nuevo = st.text_input("Producto / SKU en producción actual:", value=estado_planta[maq_sel]["Producto"])
        
        if st.button("Aplicar cambios a la Planta"):
            estado_planta[maq_sel]["Meta"] = meta_nueva
            estado_planta[maq_sel]["Producto"] = prod_nuevo
            st.success(f"Configuración actualizada para {maq_sel}.")

    elif id_capa == 3:
        st.title("💻 Capa 3: Terminal de Entrada del Operario")
        maq_sel = st.selectbox("Su puesto asignado:", list(estado_planta.keys()))
        estado_nuevo = st.selectbox("Cambiar Estado Operativo:", ["PRODUCIENDO", "SETUP", "PARADA"])
        tipo_falla = st.selectbox("Declarar causa de detención:", ["Ninguna", "Falta de Material", "Rotura Mecánica", "Ajuste de Parámetros"])
        min_parada = st.number_input("Minutos de parada estimados:", min_value=0, value=0)
        
        if st.button("Registrar Novedad en Turno"):
            estado_planta[maq_sel]["Estado"] = estado_nuevo
            if min_parada > 0:
                estado_planta[maq_sel]["Paradas_Min"] += min_parada
                st.session_state.historial_eventos.append({
                    "Hora": datetime.now().strftime("%H:%M"), "Maquina": maq_sel, "Tipo": tipo_falla, "Duracion": min_parada, "Validado": False
                })
            st.success("Evento registrado y enviado.")

    elif id_capa == 4:
        st.title("📋 Capa 4: Consola de Validación del Supervisor")
        df_eventos = pd.DataFrame(st.session_state.historial_eventos)
        if not df_eventos.empty:
            st.dataframe(df_eventos)
            idx_val = st.number_input("Ingrese índice de fila a validar:", min_value=0, max_value=len(df_eventos)-1, step=1)
            if st.button("Aprobar e imputar al OEE definitivo"):
                st.session_state.historial_eventos[idx_val]["Validado"] = True
                st.success(f"Fila {idx_val} validada.")
        else:
            st.info("No hay eventos pendientes de validación.")

    elif id_capa == 5:
        st.title("🎯 Capa 5: Tablero Kaizen para Dirección General")
        col_dis, col_ren, col_cal = st.columns(3)
        col_dis.metric("DISPONIBILIDAD TOTAL", "88.4%")
        col_ren.metric("RENDIMIENTO GLOBAL", "91.2%")
        col_cal.metric("CALIDAD DE PROCESO", "98.7%")
        st.markdown("---")
        for m, d in estado_planta.items():
            st.text(f"🔹 {m} | SKU: {d['Producto']} | Buenas: {d['Buenas']} pz | Paradas acumuladas: {d['Paradas_Min']} min")

    elif id_capa == 6:
        st.title("📈 Capa 6: Módulo Business Intelligence & Pareto")
        data_grafico = {
            "Máquina": list(estado_planta.keys()),
            "Minutos de Parada Acumulados": [d["Paradas_Min"] for d in estado_planta.values()],
            "Piezas de Retrabajo / Scrap": [d["Retrabajos"] for d in estado_planta.values()]
        }
        df_graf = pd.DataFrame(data_grafico).set_index("Máquina")
        st.bar_chart(df_graf)

    elif id_capa == 7:
        st.markdown("## 🚨 Monitor Andón de Planta (Tiempo Real - MQTT)")
        cols = st.columns(3)
        for i, (maq, datos) in enumerate(estado_planta.items()):
            estado = datos["Estado"]
            clase_andon = "andon-marcha" if estado == "PRODUCIENDO" else ("andon-setup" if estado == "SETUP" else "andon-parada")
            badge_color = "badge-v" if estado == "PRODUCIENDO" else ("badge-a" if estado == "SETUP" else "badge-r")
            
            html_code = f"""
            <div class="andon-card {clase_andon}">
                <div class="andon-header">
                    <span>{maq}</span>
                    <span class="wiidem-badge {badge_color}">{estado}</span>
                </div>
                <div style="margin-top:12px; font-size:13px; color:#8b949e;">PRODUCTO ACTIVO: <b>{datos['Producto']}</b></div>
                <div class="andon-meta-box">
                    <table style="width:100%; color:#c9d1d9; border-collapse:collapse;">
                        <tr><td><b>ESTADO DE PROCESO:</b></td><td style="text-align:right; color:#00f2fe;"><b>Sincronizado</b></td></tr>
                    </table>
                </div>
                <div class="andon-meta-box">
                    <table style="width:100%; font-size:12px; border-collapse:collapse;">
                        <tr><td>META ESTÁNDAR:</td><td style="text-align:right;"><b>{datos['Meta']} pz</b></td></tr>
                        <tr><td>REAL LOGRADO:</td><td style="text-align:right; color:#00f2fe; font-size:15px;"><b>{datos['Buenas']} pz</b></td></tr>
                    </table>
                </div>
                <div style="font-size:11px; color:#ffaa00; margin-top:10px;">📡 Telemetría: {datos['Ultimo']}</div>
            </div>
            """
            with cols[i]:
                st.markdown(html_code, unsafe_allow_html=True)

# Ejecutamos el fragmento pasando la capa elegida
renderizar_capa_activa(capas[capa_seleccionada])