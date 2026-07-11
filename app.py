import streamlit as st
import json
import base64
from google.cloud import bigquery
from google.oauth2 import service_account

# Configuración de página
st.set_page_config(page_title="AMB Hidrología", layout="wide")
st.title("🌧️ Centro de Monitoreo: Red Meteorológica AMB")

# --- CONEXIÓN A BIGQUERY (Base64) ---
try:
    # Leemos el string base64 desde los Secrets de Streamlit
    b64_json = st.secrets["GCP_JSON_B64"]
    # Decodificamos y convertimos a diccionario
    key_dict = json.loads(base64.b64decode(b64_json))
    
    # Creamos las credenciales
    creds = service_account.Credentials.from_service_account_info(key_dict)
    client = bigquery.Client(credentials=creds, project=key_dict["project_id"])
except Exception as e:
    st.error(f"Error de conexión con BigQuery: {e}")
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
    
    # KPIs amigables
    c1, c2, c3 = st.columns(3)
    c1.metric("Temperatura", f"{float(row.get('temperatura', 0)):.1f} °C")
    c2.metric("Precipitación", f"{float(row.get('precipitacion', 0)):.1f} mm")
    c3.metric("Voltaje", f"{float(row.get('voltaje_bateria', 0)):.1f} V")
    
    st.info(f"Última lectura: {row['timestamp']}")
    
    # Visualización detallada
    with st.expander("Ver detalles técnicos"):
        st.write(df)
else:
    st.warning("No hay datos disponibles para esta estación.")

# Tabs para expansión futura
tab1, tab2, tab3 = st.tabs(["📊 Históricos", "📈 Reportes", "🤖 Asistente IA"])
with tab1:
    st.write("Módulo de históricos en desarrollo...")
with tab2:
    st.write("Reportes en desarrollo...")
with tab3:
    st.write("Asistente IA en desarrollo...")
