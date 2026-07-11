import streamlit as st
import pandas as pd
import json
import os
from google.cloud import bigquery
from google.oauth2 import service_account
from datetime import datetime

# ============================================================
# 1. CONFIGURACIÓN DE PÁGINA
# ============================================================
st.set_page_config(
    page_title="AMB Hidrología",
    page_icon="🌧️",
    layout="wide"
)

st.title("🌧️ Centro de Monitoreo: Red Meteorológica AMB")
st.caption(f"Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ============================================================
# 2. CONEXIÓN A BIGQUERY (USANDO VARIABLE DE ENTORNO)
# ============================================================
@st.cache_resource
def init_bigquery_client():
    try:
        # Leer credenciales desde variable de entorno
        creds_json = os.environ.get("GCP_CREDENTIALS_JSON")
        
        if creds_json:
            key_dict = json.loads(creds_json)
        else:
            # Fallback para desarrollo local (usando st.secrets)
            key_dict = {
                "type": "service_account",
                "project_id": st.secrets["gcp_service_account"]["project_id"],
                "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
                "private_key": st.secrets["gcp_service_account"]["private_key"].replace("\\n", "\n"),
                "client_email": st.secrets["gcp_service_account"]["client_email"],
                "client_id": st.secrets["gcp_service_account"]["client_id"],
                "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
                "token_uri": st.secrets["gcp_service_account"]["token_uri"],
                "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
                "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"],
                "universe_domain": st.secrets["gcp_service_account"]["universe_domain"]
            }
        
        creds = service_account.Credentials.from_service_account_info(key_dict)
        client = bigquery.Client(credentials=creds, project=key_dict["project_id"])
        
        return client
    except Exception as e:
        st.error(f"❌ Error de conexión con BigQuery: {e}")
        st.stop()

client = init_bigquery_client()

# ============================================================
# 3. FUNCIONES DE CONSULTA
# ============================================================
@st.cache_data(ttl=300)
def get_last_reading(estacion):
    query = f"""
        SELECT 
            timestamp,
            id_estacion,
            temperatura,
            precipitacion,
            humedad,
            voltaje_bateria,
            estado_bateria
        FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones`
        WHERE id_estacion = '{estacion}'
        ORDER BY timestamp DESC 
        LIMIT 1
    """
    try:
        df = client.query(query).to_dataframe()
        return df
    except Exception as e:
        st.error(f"Error en consulta: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=600)
def get_historical_data(estacion, hours=24):
    query = f"""
        SELECT 
            timestamp,
            temperatura,
            precipitacion,
            humedad,
            voltaje_bateria
        FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones`
        WHERE id_estacion = '{estacion}'
        AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {hours} HOUR)
        ORDER BY timestamp ASC
    """
    try:
        df = client.query(query).to_dataframe()
        return df
    except Exception as e:
        st.error(f"Error en consulta histórica: {e}")
        return pd.DataFrame()

# ============================================================
# 4. SIDEBAR
# ============================================================
estaciones = [
    "La_Mariana",
    "Yerbabuena", 
    "Vegas_del_Quemado",
    "El_Pajal",
    "Monsalve",
    "Embalse"
]

with st.sidebar:
    st.header("⚙️ Configuración")
    seleccion = st.selectbox("Seleccione Estación:", estaciones)
    
    st.divider()
    st.caption("🔹 Datos en tiempo real")
    st.caption("🔹 Actualización cada 5 minutos")
    
    if st.button("🔄 Refrescar Datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ============================================================
# 5. INTERFAZ PRINCIPAL
# ============================================================
st.subheader(f"📡 Datos en Tiempo Real: {seleccion}")

df = get_last_reading(seleccion)

if not df.empty:
    row = df.iloc[0]
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        temp = float(row['temperatura']) if pd.notna(row['temperatura']) else 0
        st.metric("🌡️ Temperatura", f"{temp:.1f} °C")
    
    with col2:
        precip = float(row['precipitacion']) if pd.notna(row['precipitacion']) else 0
        st.metric("🌧️ Precipitación", f"{precip:.1f} mm")
    
    with col3:
        humedad = float(row['humedad']) if pd.notna(row['humedad']) else 0
        st.metric("💧 Humedad", f"{humedad:.1f} %")
    
    with col4:
        voltaje = float(row['voltaje_bateria']) if pd.notna(row['voltaje_bateria']) else 0
        estado = row.get('estado_bateria', 'DESCONOCIDO')
        emoji = "🟢" if estado == "OK" else "🟡" if estado == "ADVERTENCIA" else "🔴"
        st.metric(f"{emoji} Voltaje", f"{voltaje:.1f} V")
    
    st.info(f"📅 Última lectura: {row['timestamp']}")
    
    with st.expander("📋 Ver detalles técnicos"):
        st.dataframe(df)
    
    with st.expander("📈 Tendencia últimas 24 horas"):
        df_hist = get_historical_data(seleccion)
        if not df_hist.empty:
            df_hist['timestamp'] = pd.to_datetime(df_hist['timestamp'])
            col1, col2 = st.columns(2)
            with col1:
                st.line_chart(df_hist.set_index('timestamp')[['temperatura']], height=300)
                st.caption("🌡️ Temperatura (°C)")
            with col2:
                st.line_chart(df_hist.set_index('timestamp')[['precipitacion']], height=300)
                st.caption("🌧️ Precipitación (mm)")
        else:
            st.info("No hay datos históricos disponibles")
else:
    st.warning("⚠️ No hay datos disponibles para esta estación")

# ============================================================
# 6. PIE DE PÁGINA
# ============================================================
st.divider()
st.caption(f"🏢 Área Metropolitana de Bucaramanga | ⏱️ {datetime.now().strftime('%H:%M:%S')}")
