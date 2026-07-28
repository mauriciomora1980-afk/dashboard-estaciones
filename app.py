import streamlit as st
import pandas as pd
import json
import base64
from google.cloud import bigquery
from google.oauth2 import service_account
from datetime import datetime
from pytz import timezone
from io import BytesIO
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Centro de Monitoreo - amb", layout="wide")

try:
    st.sidebar.image("amb_4_punto_cero.jpg", use_column_width=True)
except:
    st.sidebar.warning("Logo no encontrado")

st.title("🌧️ Centro de Monitoreo: Red Meteorológica amb")

# --- LÓGICA DE ALERTAS ---
umbrales = {
    "El_Pajal": {"amarilla": 12.3, "naranja": 15.1, "roja": 20.4},
    "Yerbabuena": {"amarilla": 10.9, "naranja": 20.0, "roja": 40.8},
    "La_Mariana": {"amarilla": 11.7, "naranja": 18.0, "roja": 35.0},
    "Vegas_del_Quemado": {"amarilla": 27.2, "naranja": 36.8, "roja": 55.8}
}

def obtener_alerta(precip, estacion):
    if estacion == "Monsalve": return "AZUL", "🛠️ En Aprendizaje", "#3399FF", "0s"
    if estacion not in umbrales: return "GRIS", "☁️ Sin umbrales definidos", "#CCCCCC", "0s"
    u = umbrales[estacion]
    if precip >= u["roja"]: return "ROJA", f"🚨 ROJA: Excede {u['roja']}mm", "#FF4B4B", "0.5s"
    elif precip >= u["naranja"]: return "NARANJA", f"⚠️ NARANJA: Excede {u['naranja']}mm", "#FF9933", "1s"
    elif precip >= u["amarilla"]: return "AMARILLA", f"🟡 AMARILLA: Excede {u['amarilla']}mm", "#FFFF00", "2s"
    elif precip > 0: return "VERDE", "✅ Lluvia Normal", "#00CC96", "0s"
    return "GRIS", "☁️ Sin lluvia", "#CCCCCC", "0s"

# --- CLIENTE BQ ---
@st.cache_resource
def init_bigquery_client():
    json_str = base64.b64decode(st.secrets["GCP_JSON_B64"]).decode('utf-8')
    key_dict = json.loads(json_str)
    creds = service_account.Credentials.from_service_account_info(key_dict)
    return bigquery.Client(credentials=creds, project=key_dict["project_id"])

client = init_bigquery_client()

@st.cache_data(ttl=300)
def get_data(estacion, limit=100):
    query = f"SELECT * FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones` WHERE id_estacion = '{estacion}' ORDER BY timestamp DESC LIMIT {limit}"
    df = client.query(query).to_dataframe()
    df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize('UTC').dt.tz_convert('America/Bogota')
    return df

# --- INTERFAZ ---
estaciones = ["La_Mariana", "Yerbabuena", "Vegas_del_Quemado", "El_Pajal", "Monsalve", "Embalse"]
seleccion = st.sidebar.selectbox("Seleccione Estación:", estaciones)
df = get_data(seleccion, limit=100)

if not df.empty:
    row = df.iloc[0]
    st.subheader(f"📡 Real-time: {seleccion}")
    
    # Semáforo y Métricas
    if seleccion != "Embalse":
        nombre, msg, color, vel = obtener_alerta(float(row['precipitacion']), seleccion)
        st.markdown(f'<div style="background-color:{color}; padding:20px; border-radius:15px; text-align:center; animation: blink {vel} infinite;"><h2>{nombre}</h2><b>{msg}</b></div><style>@keyframes blink {{0%{{opacity:1}} 50%{{opacity:0.3}} 100%{{opacity:1}}}}</style>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🌡️ Temp", f"{float(row['temperatura']):.1f}°C")
        c2.metric("🌧️ Precip", f"{float(row['precipitacion']):.1f}mm")
        c3.metric("💧 Humedad", f"{float(row['humedad']):.1f}%")
        c4.metric("🔋 Voltaje", f"{float(row['voltaje_bateria']):.1f}V")
    else:
        st.metric("🌊 Nivel Embalse", f"{float(row['temperatura']):.2f} msnm")

    # Tabs con títulos arriba de las gráficas
    tab1, tab2, tab3 = st.tabs(["📈 Históricos", "📊 Reportes", "🤖 Asistente IA"])
    
    with tab1:
        st.markdown("### 🌡️ Tendencia de Temperatura")
        st.line_chart(df.set_index('timestamp')[['temperatura']])
        st.markdown("### 🌧️ Tendencia de Precipitación")
        st.line_chart(df.set_index('timestamp')[['precipitacion']])

    with tab2:
        st.subheader("📋 Módulo de Reportes")
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar CSV Histórico", csv, "datos.csv", "text/csv")
        st.write("PDF y Excel en proceso...")
    
    with tab3: st.write("IA activa.")
