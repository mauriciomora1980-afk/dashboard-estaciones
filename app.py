import streamlit as st
import pandas as pd
import json
import base64
import os
from google.cloud import bigquery
from google.oauth2 import service_account
from datetime import datetime, timedelta
from pytz import timezone

st.set_page_config(page_title="Centro de Monitoreo - amb", layout="wide")

# Logo
logo_path = os.path.join(os.path.dirname(__file__), "amb_4_punto_cero.jpg")
if os.path.exists(logo_path):
    st.sidebar.image(logo_path, use_column_width=True)

st.title("🌧️ Centro de Monitoreo: Red Meteorológica amb")
colombia_tz = timezone('America/Bogota')
st.caption(f"🕐 Última actualización: {datetime.now(colombia_tz).strftime('%Y-%m-%d %H:%M:%S')} (Hora Colombia)")

# --- UMBRALES Y CONFIG ---
umbrales = {
    "El_Pajal": {"amarilla": 12.3, "naranja": 15.1, "roja": 20.4},
    "Yerbabuena": {"amarilla": 10.9, "naranja": 20.0, "roja": 40.8},
    "La_Mariana": {"amarilla": 11.7, "naranja": 18.0, "roja": 35.0},
    "Vegas_del_Quemado": {"amarilla": 27.2, "naranja": 36.8, "roja": 55.8}
}
Cota_Rebose = 885.80

def obtener_alerta(precip, estacion):
    if estacion == "Monsalve": return "AZUL", "🛠️ En Aprendizaje", "#3399FF", "0s"
    if estacion not in umbrales: return "GRIS", "☁️ Sin umbrales definidos", "#CCCCCC", "0s"
    u = umbrales[estacion]
    if precip >= u["roja"]: return "ROJA", f"🚨 ROJA: Excede {u['roja']}mm", "#FF4B4B", "0.5s"
    elif precip >= u["naranja"]: return "NARANJA", f"⚠️ NARANJA: Excede {u['naranja']}mm", "#FF9933", "1s"
    elif precip >= u["amarilla"]: return "AMARILLA", f"🟡 AMARILLA: Excede {u['amarilla']}mm", "#FFFF00", "2s"
    elif precip > 0: return "VERDE", "✅ Lluvia Normal", "#00CC96", "0s"
    return "GRIS", "☁️ Sin lluvia", "#CCCCCC", "0s"

# --- CONEXIÓN ---
@st.cache_resource
def init_bigquery_client():
    json_str = base64.b64decode(st.secrets["GCP_JSON_B64"]).decode('utf-8')
    key_dict = json.loads(json_str)
    creds = service_account.Credentials.from_service_account_info(key_dict)
    return bigquery.Client(credentials=creds, project=key_dict["project_id"])

client = init_bigquery_client()

@st.cache_data(ttl=300)
def get_data(estacion, dias=1):
    query = f"SELECT * FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones` WHERE id_estacion = '{estacion}' AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {dias} DAY) ORDER BY timestamp DESC"
    df = client.query(query).to_dataframe()
    df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize('UTC').dt.tz_convert('America/Bogota')
    return df

# --- INTERFAZ ---
estaciones = ["La_Mariana", "Yerbabuena", "Vegas_del_Quemado", "El_Pajal", "Monsalve", "Embalse"]
seleccion = st.sidebar.selectbox("Seleccione Estación:", estaciones)
periodo = st.sidebar.selectbox("Período histórico:", ["Últimas 24 horas", "Últimos 3 días", "Últimos 7 días"])
dias_map = {"Últimas 24 horas": 1, "Últimos 3 días": 3, "Últimos 7 días": 7}

st.subheader(f"📡 Real-time: {seleccion}")
df = get_data(seleccion, limit=1)

if not df.empty:
    row = df.iloc[0]
    if seleccion == "Embalse":
        nivel = float(row['temperatura'])
        excedente = (nivel - Cota_Rebose) * 100
        if excedente > 0:
            st.markdown(f'<div style="background-color:#FF4B4B; padding:15px; border-radius:10px; text-align:center;"><h2>⚠️ Nivel supera el rebose: +{excedente:.1f} cm</h2></div>', unsafe_allow_html=True)
        st.metric("🌊 Nivel Actual", f"{nivel:.2f} msnm")
        st.metric("📏 Nivel de Rebose", f"{Cota_Rebose:.2f} msnm")
    else:
        nombre, msg, color, vel = obtener_alerta(float(row.get('precipitacion', 0)), seleccion)
        st.markdown(f'<div style="background-color:{color}; padding:20px; border-radius:15px; text-align:center; color:black; animation: blink {vel} infinite; border: 2px solid #333;"><h2>{nombre}</h2><b>{msg}</b></div><style>@keyframes blink {{0%{{opacity:1}} 50%{{opacity:0.3}} 100%{{opacity:1}}}}</style>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🌡️ Temp", f"{float(row['temperatura']):.1f} °C")
        c2.metric("🌧️ Precip", f"{float(row['precipitacion']):.1f} mm")
        c3.metric("💧 Humedad", f"{float(row['humedad']):.1f} %")
        c4.metric("🔋 Voltaje", f"{float(row['voltaje_bateria']):.1f} V")

    # TABS
    tab1, tab2, tab3 = st.tabs(["📈 Históricos", "📊 Reportes", "🤖 Asistente IA"])
    with tab1:
        df_hist = get_data(seleccion, dias=dias_map[periodo])
        st.markdown("### 🌡️ Tendencia de Temperatura")
        st.line_chart(df_hist.set_index('timestamp')[['temperatura']])
        st.markdown("### 🌧️ Tendencia de Precipitación")
        st.line_chart(df_hist.set_index('timestamp')[['precipitacion']])
    with tab2:
        csv = df_hist.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar CSV Histórico", csv, "datos.csv", "text/csv")
    with tab3: st.write("Asistente IA activo.")
else:
    st.warning("⚠️ Sin datos.")
