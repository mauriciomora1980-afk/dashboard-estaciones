import streamlit as st
import pandas as pd
import json
import base64
import os
import plotly.express as px
from google.cloud import bigquery
from google.oauth2 import service_account
from datetime import datetime, timedelta
from pytz import timezone

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Centro de Monitoreo - amb", layout="wide")

# Logo
logo_path = os.path.join(os.path.dirname(__file__), "amb_4_punto_cero.jpg")
if os.path.exists(logo_path):
    st.sidebar.image(logo_path, use_column_width=True)

st.title("🌧️ Centro de Monitoreo: Red Meteorológica amb")
colombia_tz = timezone('America/Bogota')
st.caption(f"🕐 Última actualización: {datetime.now(colombia_tz).strftime('%Y-%m-%d %H:%M:%S')} (Hora Colombia)")

# --- UMBRALES Y CLIENTE BQ ---
umbrales = {"El_Pajal": {"amarilla": 12.3, "naranja": 15.1, "roja": 20.4}, "Yerbabuena": {"amarilla": 10.9, "naranja": 20.0, "roja": 40.8}, "La_Mariana": {"amarilla": 11.7, "naranja": 18.0, "roja": 35.0}, "Vegas_del_Quemado": {"amarilla": 27.2, "naranja": 36.8, "roja": 55.8}}

@st.cache_resource
def init_bigquery_client():
    json_str = base64.b64decode(st.secrets["GCP_JSON_B64"]).decode('utf-8')
    key_dict = json.loads(json_str)
    creds = service_account.Credentials.from_service_account_info(key_dict)
    return bigquery.Client(credentials=creds, project=key_dict["project_id"])

client = init_bigquery_client()

# --- CONSULTAS ---
@st.cache_data(ttl=300)
def get_data(estacion, dias=1):
    query = f"SELECT * FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones` WHERE id_estacion = '{estacion}' AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {dias} DAY) ORDER BY timestamp DESC"
    df = client.query(query).to_dataframe()
    df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize('UTC').dt.tz_convert('America/Bogota')
    return df

# --- SIDEBAR ---
estaciones = ["La_Mariana", "Yerbabuena", "Vegas_del_Quemado", "El_Pajal", "Monsalve", "Embalse"]
seleccion = st.sidebar.selectbox("Seleccione Estación:", estaciones)
periodo_nombre = st.sidebar.selectbox("Período histórico:", ["Últimas 24 horas", "Últimos 3 días", "Últimos 7 días"])
mapa_dias = {"Últimas 24 horas": 1, "Últimos 3 días": 3, "Últimos 7 días": 7}

# --- LÓGICA ---
df_all = get_data(seleccion, dias=mapa_dias[periodo_nombre])
row = df_all.iloc[0] if not df_all.empty else None

if row is not None:
    st.subheader(f"📡 Real-time: {seleccion}")
    # Métricas y Semáforo aquí...
    
    tab1, tab2, tab3 = st.tabs(["📈 Históricos", "📊 Reportes", "🤖 Asistente IA"])
    with tab1:
        st.markdown("### 🌡️ Temperatura")
        st.line_chart(df_all.set_index('timestamp')[['temperatura']])
        st.markdown("### 🌧️ Precipitación")
        st.line_chart(df_all.set_index('timestamp')[['precipitacion']])
        
        # ROSA DE LOS VIENTOS
        st.markdown("### 🧭 Rosa de los Vientos")
        fig = px.bar_polar(df_all, r="velocidad_viento", theta="direccion_del_viento", color="velocidad_viento", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        csv = df_all.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar CSV Histórico", csv, "datos.csv", "text/csv")
