import streamlit as st
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

# 1. Configuración de página
st.set_page_config(page_title="AMB Hidrología", layout="wide")
st.title("🌧️ Centro de Monitoreo: Red Meteorológica AMB")

# 2. Cargar credenciales desde los Secrets de Streamlit
# Usamos dict() para asegurar que Streamlit pase los datos como un diccionario puro
try:
    key_dict = dict(st.secrets["gcp_service_account"])
    creds = service_account.Credentials.from_service_account_info(key_dict)
    client = bigquery.Client(credentials=creds, project=key_dict["project_id"])
except Exception as e:
    st.error(f"Error de credenciales: {e}")
    st.stop()

# 3. Función optimizada para traer el último dato válido
@st.cache_data(ttl=600)
def get_data(estacion):
    query = f"""
        SELECT * FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones`
        WHERE id_estacion = '{estacion}'
        ORDER BY timestamp DESC LIMIT 1
    """
    df = client.query(query).to_dataframe()
    return df

# 4. --- SIDEBAR ---
estaciones = ["La_Mariana", "Yerbabuena", "Vegas_del_Quemado", "El_Pajal", "Monsalve", "Embalse"]
seleccion = st.sidebar.selectbox("Seleccione Estación:", estaciones)

# 5. --- INTERFAZ ---
st.subheader(f"Datos en Tiempo Real: {seleccion}")
df = get_data(seleccion)

if not df.empty:
    row = df.iloc[0]
    
    # KPIs amigables
    c1, c2, c3 = st.columns(3)
    c1.metric("Temperatura", f"{float(row['temperatura']):.1f} °C")
    c2.metric("Precipitación", f"{float(row['precipitacion']):.1f} mm")
    c3.metric("Voltaje", f"{float(row['voltaje_bateria']):.1f} V")
    
    st.info(f"Última lectura: {row['timestamp']}")
    
    # Mostrar tabla completa del registro
    with st.expander("Ver detalles técnicos del registro"):
        st.write(df)
else:
    st.warning("No hay datos disponibles para esta estación en la última hora.")

# Tabs para futuras fases
tab1, tab2, tab3 = st.tabs(["📊 Históricos", "📈 Reportes", "🤖 Asistente IA"])
with tab1:
    st.write("Módulo de históricos en desarrollo...")
with tab2:
    st.write("Reportes en desarrollo...")
with tab3:
    st.write("Agente IA en desarrollo...")
