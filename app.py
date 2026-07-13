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
st.title("🌧️ Centro de Monitoreo: Red Meteorológica amb")

colombia_tz = timezone('America/Bogota')
hora_colombia = datetime.now(colombia_tz).strftime('%Y-%m-%d %H:%M:%S')
st.caption(f"🕐 Última actualización: {hora_colombia} (hora Colombia)")

# --- MATRIZ DE UMBRALES ---
umbrales = {
    "El_Pajal":          {"amarilla": 12.3, "naranja": 15.1, "roja": 20.4},
    "Yerbabuena":        {"amarilla": 10.9, "naranja": 20.0, "roja": 40.8},
    "La_Mariana":        {"amarilla": 11.7, "naranja": 18.0, "roja": 35.0},
    "Vegas_del_Quemado": {"amarilla": 27.2, "naranja": 36.8, "roja": 55.8}
}

def obtener_alerta(precipitacion, estacion):
    if estacion == "Monsalve":
        return "AZUL", "🛠️ En Aprendizaje", "#3399FF", "0s"
    if estacion not in umbrales:
        return "GRIS", "☁️ Sin umbrales definidos", "#CCCCCC", "0s"
    
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
# 2. CONEXIÓN A BIGQUERY (Simplificada)
# ============================================================
@st.cache_resource
def init_bigquery_client():
    try:
        creds_json = os.environ.get("GCP_CREDENTIALS_JSON")
        if creds_json:
            key_dict = json.loads(creds_json)
        else:
            with open('gcp_key.json', 'r') as f:
                key_dict = json.load(f)
        creds = service_account.Credentials.from_service_account_info(key_dict)
        return bigquery.Client(credentials=creds, project=key_dict["project_id"])
    except Exception as e:
        st.error(f"❌ Error de conexión: {e}")
        st.stop()

client = init_bigquery_client()

# ============================================================
# 3. FUNCIONES DE CONSULTA
# ============================================================
@st.cache_data(ttl=300)
def get_last_reading(estacion):
    query = f"""SELECT * FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones`
                WHERE id_estacion = '{estacion}' ORDER BY timestamp DESC LIMIT 1"""
    return client.query(query).to_dataframe()

# ============================================================
# 5. INTERFAZ PRINCIPAL
# ============================================================
estaciones = ["La_Mariana", "Yerbabuena", "Vegas_del_Quemado", "El_Pajal", "Monsalve", "Embalse"]
seleccion = st.sidebar.selectbox("Seleccione Estación:", estaciones)
st.subheader(f"📡 Datos en Tiempo Real: {seleccion}")

df = get_last_reading(seleccion)

if not df.empty:
    row = df.iloc[0]
    
    # --- SEMÁFORO (Solo para meteo) ---
    if seleccion != "Embalse":
        precip_actual = float(row.get('precipitacion', 0))
        nombre, msg, color, vel = obtener_alerta(precip_actual, seleccion)
        st.markdown(f"""
            <div style="background-color:{color}; padding:20px; border-radius:15px; text-align:center; color:black; animation: blink {vel} infinite; border: 2px solid #333;">
                <h2 style="margin:0;">{nombre}</h2><b>{msg}</b>
            </div>
            <style>@keyframes blink {{0%{{opacity:1}} 50%{{opacity:0.3}} 100%{{opacity:1}}}}</style>
        """, unsafe_allow_html=True)
        st.write("") # Espacio

    # --- MÉTRICAS ---
    if seleccion == "Embalse":
        col1, col2 = st.columns(2)
        col1.metric("🌊 Nivel", f"{float(row['temperatura']):.2f} msnm")
        col2.metric("🔋 Voltaje", f"{float(row['voltaje_bateria']):.1f} V")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🌡️ Temp", f"{float(row['temperatura']):.1f} °C")
        c2.metric("🌧️ Precip", f"{float(row['precipitacion']):.1f} mm")
        c3.metric("💧 Humedad", f"{float(row['humedad']):.1f} %")
        c4.metric("🔋 Voltaje", f"{float(row['voltaje_bateria']):.1f} V")

    st.info(f"📅 Última lectura: {row['timestamp']}")
else:
    st.warning("⚠️ Sin datos")
