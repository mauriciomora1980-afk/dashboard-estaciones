import streamlit as st
import json
import os
from google.cloud import bigquery
from google.oauth2 import service_account

# Configuración de página
st.set_page_config(page_title="AMB Hidrología", layout="wide")
st.title("🌧️ Centro de Monitoreo: Red Meteorológica AMB")

# --- CONEXIÓN A BIGQUERY ---
# Intentamos leer desde Streamlit Secrets (que se mapea a variables de entorno)
try:
    # Si estamos en Streamlit Cloud, los secrets se cargan en st.secrets
    # Si la clave "GCP_JSON" existe, la usamos
    json_str = st.secrets["GCP_JSON"]
    key_dict = json.loads(json_str)
    creds = service_account.Credentials.from_service_account_info(key_dict)
    client = bigquery.Client(credentials=creds, project=key_dict["project_id"])
except Exception as e:
    st.error(f"Error de conexión: {e}")
    st.stop()

# --- FUNCIONES ---
@st.cache_data(ttl=600)
def get_data(estacion):
    query = f"""
        SELECT * FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones`
        WHERE id_estacion = '{estacion}'
        ORDER BY timestamp DESC LIMIT 1
    """
    return client.query(query).to_dataframe()

# --- INTERFAZ ---
estaciones = ["La_Mariana", "Yerbabuena", "Vegas_del_Quemado", "El_Pajal", "Monsalve", "Embalse"]
seleccion = st.sidebar.selectbox("Seleccione Estación:", estaciones)

st.subheader(f"Datos en Tiempo Real: {seleccion}")
df = get_data(seleccion)

if not df.empty:
    row = df.iloc[0]
    c1, c2, c3 = st.columns(3)
    c1.metric("Temperatura", f"{float(row['temperatura']):.1f} °C")
    c2.metric("Precipitación", f"{float(row['precipitacion']):.1f} mm")
    c3.metric("Voltaje", f"{float(row['voltaje_bateria']):.1f} V")
    st.info(f"Última lectura: {row['timestamp']}")
else:
    st.warning("No hay datos disponibles.")
