import streamlit as st
import pandas as pd
import json
import os
import base64
from google.cloud import bigquery
from google.oauth2 import service_account
from datetime import datetime
from pytz import timezone

# ============================================================
# 1. CONFIGURACIÓN DE PÁGINA
# ============================================================
st.set_page_config(page_title="Centro de Monitoreo - amb", page_icon="🌧️", layout="wide")

try:
    st.sidebar.image("amb_4_punto_cero.jpg", use_container_width=True)
except:
    st.sidebar.warning("Logo no encontrado")

st.title("🌧️ Centro de Monitoreo: Red Meteorológica amb")

colombia_tz = timezone('America/Bogota')
hora_colombia = datetime.now(colombia_tz).strftime('%Y-%m-%d %H:%M:%S')
st.caption(f"🕐 Última actualización: {hora_colombia} (hora Colombia)")

# ============================================================
# 2. MATRIZ DE UMBRALES
# ============================================================
umbrales = {
    "El_Pajal":          {"amarilla": 12.3, "naranja": 15.1, "roja": 20.4},
    "Yerbabuena":        {"amarilla": 10.9, "naranja": 20.0, "roja": 40.8},
    "La_Mariana":        {"amarilla": 11.7, "naranja": 18.0, "roja": 35.0},
    "Vegas_del_Quemado": {"amarilla": 27.2, "naranja": 36.8, "roja": 55.8}
}

# ============================================================
# 3. CONFIGURACIÓN DEL EMBALSE
# ============================================================
CONFIG_EMBALSE = {
    "nivel_rebose": 885.80  # msnm - Nivel antes de rebose
}

def obtener_alerta_embalse(nivel_actual):
    """Determina el nivel de alerta para el embalse"""
    nivel_rebose = CONFIG_EMBALSE["nivel_rebose"]
    excedente = nivel_actual - nivel_rebose
    
    if excedente > 0:
        return "ROJA", f"🚨 REBOSE SUPERADO: +{excedente:.2f} msnm", "#FF4B4B", "0.5s"
    elif excedente == 0:
        return "NARANJA", "⚖️ EN PUNTO DE REBOSE", "#FF9933", "1s"
    elif excedente >= -0.30:  # A 30cm del rebose
        return "AMARILLA", f"⚠️ CERCA DEL REBOSE: {abs(excedente):.2f} msnm", "#FFFF00", "2s"
    else:
        return "VERDE", f"✅ NORMAL: {abs(excedente):.2f} msnm bajo rebose", "#00CC96", "0s"

# ============================================================
# 4. FUNCIÓN DE ALERTAS (MEJORADA CON MONSALVE)
# ============================================================
def obtener_alerta(precipitacion, estacion):
    # Caso especial: Monsalve (en aprendizaje)
    if estacion == "Monsalve":
        if precipitacion > 0:
            return "VERDE", f"✅ Aprendizaje - Lluvia: {precipitacion:.1f} mm", "#00CC96", "0s"
        else:
            return "AZUL", "🛠️ En Aprendizaje - Sin lluvia", "#3399FF", "0s"
    
    # Estaciones sin umbrales definidos
    if estacion not in umbrales: 
        return "GRIS", "☁️ Sin umbrales definidos", "#CCCCCC", "0s"
    
    # Evaluación de umbrales para las demás estaciones
    u = umbrales[estacion]
    if precipitacion >= u["roja"]:
        return "ROJA", f"🚨 ROJA: Excede {u['roja']}mm", "#FF4B4B", "0.5s"
    elif precipitacion >= u["naranja"]:
        return "NARANJA", f"⚠️ NARANJA: Excede {u['naranja']}mm", "#FF9933", "1s"
    elif precipitacion >= u["amarilla"]:
        return "AMARILLA", f"🟡 AMARILLA: Excede {u['amarilla']}mm", "#FFFF00", "2s"
    elif precipitacion > 0:
        return "VERDE", "✅ Lluvia Normal", "#00CC96", "0s"
    return "GRIS", "☁️ Sin lluvia", "#CCCCCC", "0s"

# ============================================================
# 5. CONEXIÓN A BIGQUERY
# ============================================================
@st.cache_resource
def init_bigquery_client():
    try:
        json_str = st.secrets["GCP_JSON_B64"]
        key_dict = json.loads(base64.b64decode(json_str))
        creds = service_account.Credentials.from_service_account_info(key_dict)
        return bigquery.Client(credentials=creds, project=key_dict["project_id"])
    except Exception as e:
        st.error(f"❌ Error de conexión: {e}")
        st.stop()

client = init_bigquery_client()

# ============================================================
# 6. FUNCIONES DE CONSULTA
# ============================================================
@st.cache_data(ttl=300)
def get_last_reading(estacion):
    query = f"SELECT * FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones` WHERE id_estacion = '{estacion}' ORDER BY timestamp DESC LIMIT 1"
    df = client.query(query).to_dataframe()
    if not df.empty:
        df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize('UTC').dt.tz_convert('America/Bogota')
    return df

@st.cache_data(ttl=600)
def get_historical_data(estacion):
    query = f"SELECT * FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones` WHERE id_estacion = '{estacion}' ORDER BY timestamp DESC LIMIT 100"
    df = client.query(query).to_dataframe()
    df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize('UTC').dt.tz_convert('America/Bogota')
    return df

# ============================================================
# 7. INTERFAZ PRINCIPAL
# ============================================================
estaciones = ["La_Mariana", "Yerbabuena", "Vegas_del_Quemado", "El_Pajal", "Monsalve", "Embalse"]
seleccion = st.sidebar.selectbox("Seleccione Estación:", estaciones)
st.subheader(f"📡 Datos en Tiempo Real: {seleccion}")

df = get_last_reading(seleccion)

if not df.empty:
    row = df.iloc[0]
    
    # --- SEMÁFORO ---
    if seleccion == "Embalse":
        nivel_actual = float(row['temperatura'])
        nombre, msg, color, vel = obtener_alerta_embalse(nivel_actual)
    else:
        precip_actual = float(row.get('precipitacion', 0))
        nombre, msg, color, vel = obtener_alerta(precip_actual, seleccion)
    
    st.markdown(f'<div style="background-color:{color}; padding:20px; border-radius:15px; text-align:center; color:black; animation: blink {vel} infinite; border: 2px solid #333;"><h2>{nombre}</h2><b>{msg}</b></div><style>@keyframes blink {{0%{{opacity:1}} 50%{{opacity:0.3}} 100%{{opacity:1}}}}</style>', unsafe_allow_html=True)
    st.write("") 

    # --- MÉTRICAS ---
    if seleccion == "Embalse":
        nivel_actual = float(row['temperatura'])
        nivel_rebose = CONFIG_EMBALSE["nivel_rebose"]
        excedente = nivel_actual - nivel_rebose
        
        col1, col2, col3 = st.columns(3)
        col1.metric("🌊 Nivel Actual", f"{nivel_actual:.2f} msnm")
        col2.metric("📏 Nivel de Rebose", f"{nivel_rebose:.2f} msnm")
        
        if excedente > 0:
            col3.metric("⚠️ EXCEDENTE", f"+{excedente:.2f} msnm", delta=f"{excedente:.2f} msnm", delta_color="inverse")
            st.error(f"🚨 **¡ALERTA DE REBOSE!** El nivel ({nivel_actual:.2f} msnm) **EXCEDE** el rebose ({nivel_rebose:.2f} msnm) en **{excedente:.2f} msnm**")
        elif excedente < 0:
            col3.metric("📉 MARGEN", f"{abs(excedente):.2f} msnm", delta=f"{excedente:.2f} msnm", delta_color="normal")
            if abs(excedente) < 0.30:
                st.warning(f"⚠️ El nivel está a solo **{abs(excedente):.2f} msnm** del rebose")
            else:
                st.success(f"✅ El nivel está **{abs(excedente):.2f} msnm** por debajo del rebose")
        else:
            col3.metric("⚖️ EN REBOSE", f"{nivel_actual:.2f} msnm")
            st.warning(f"⚖️ El nivel está exactamente en el punto de rebose")
        
        col4, col5 = st.columns(2)
        col4.metric("🔋 Voltaje", f"{float(row['voltaje_bateria']):.1f} V")
        col5.metric("📊 Estado", "🟢 Activo" if float(row['voltaje_bateria']) > 11.0 else "🔴 Batería baja")
        
    else:
        # Estaciones meteorológicas
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🌡️ Temp", f"{float(row['temperatura']):.1f} °C")
        c2.metric("🌧️ Precip", f"{float(row['precipitacion']):.1f} mm")
        c3.metric("💧 Humedad", f"{float(row['humedad']):.1f} %")
        c4.metric("🔋 Voltaje", f"{float(row['voltaje_bateria']):.1f} V")

    st.info(f"📅 Última lectura (Hora Colombia): {row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")

    # --- TABS ---
    tab1, tab2, tab3 = st.tabs(["📈 Históricos", "📊 Reportes", "🤖 Asistente IA"])
    
    with tab1:
        df_hist = get_historical_data(seleccion)
        if not df_hist.empty:
            st.line_chart(df_hist.set_index('timestamp')[['temperatura', 'precipitacion']])
        else:
            st.warning("No hay datos históricos.")
    with tab2:
        st.write("Módulo de reportes en desarrollo.")
    with tab3:
        st.write("Asistente IA en desarrollo.")
else:
    st.warning("⚠️ Sin datos disponibles.")
