import streamlit as st
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

# Configuración
st.set_page_config(page_title="AMB Hidrología", layout="wide")

# Credenciales desde Streamlit Secrets
key_dict = st.secrets["gcp_service_account"]
creds = service_account.Credentials.from_service_account_info(key_dict)
client = bigquery.Client(credentials=creds, project=key_dict["project_id"])

st.title("🌧️ Centro de Monitoreo: Red Meteorológica AMB")

# --- FUNCIONES ---
@st.cache_data(ttl=600)
def get_data(estacion):
    query = f"""
        SELECT * FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones`
        WHERE id_estacion = '{estacion}'
        ORDER BY timestamp DESC LIMIT 1
    """
    return client.query(query).to_dataframe()

# --- SIDEBAR ---
estaciones = ["La_Mariana", "Yerbabuena", "Vegas_del_Quemado", "El_Pajal", "Monsalve", "Embalse"]
seleccion = st.sidebar.selectbox("Seleccione Estación:", estaciones)

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["📊 Situación Actual", "📅 Reportes", "🤖 Asistente IA"])

with tab1:
    st.subheader(f"Datos en Tiempo Real: {seleccion}")
    df = get_data(seleccion)
    if not df.empty:
        row = df.iloc[0]
        c1, c2, c3 = st.columns(3)
        c1.metric("Temperatura", f"{row['temperatura']:.1f} °C")
        c2.metric("Precipitación", f"{row['precipitacion']:.1f} mm")
        c3.metric("Voltaje", f"{row['voltaje_bateria']:.1f} V")
        st.info(f"Última lectura: {row['timestamp']}")
    else:
        st.error("Esperando datos...")

with tab2:
    st.write("Configurando reportes históricos...")

with tab3:
    st.write("Agente IA en construcción...")
