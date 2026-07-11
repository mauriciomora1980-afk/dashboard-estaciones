import streamlit as st
import pandas as pd
import json
import os
import base64
from google.cloud import bigquery
from google.oauth2 import service_account
from datetime import datetime

# ============================================================
# 1. CONFIGURACIÓN DE PÁGINA
# ============================================================
st.set_page_config(
    page_title="Centro de Monitoreo - Acueducto Metropolitano de Bucaramanga",
    page_icon="🌧️",
    layout="wide"
)

st.title("🌧️ Centro de Monitoreo: Red Meteorológica amb")
st.caption(f"Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ============================================================
# 2. CONEXIÓN A BIGQUERY
# ============================================================
@st.cache_resource
def init_bigquery_client():
    try:
        # --- INTENTAR PRIMERO CON VARIABLE DE ENTORNO (CLOUD RUN) ---
        creds_json = os.environ.get("GCP_CREDENTIALS_JSON")
        
        if creds_json:
            st.info("🔐 Conectando con variable de entorno...")
            key_dict = json.loads(creds_json)
            st.success("✅ Conectado usando variable de entorno")
        
        # --- SI NO HAY VARIABLE DE ENTORNO, USAR SECRETS.TOML (LOCAL) ---
        else:
            st.info("🔐 Conectando con secrets.toml (modo local)...")
            try:
                import tomllib
                with open('.streamlit/secrets.toml', 'rb') as f:
                    secrets = tomllib.load(f)
            except ImportError:
                import toml
                with open('.streamlit/secrets.toml', 'r') as f:
                    secrets = toml.load(f)
            
            b64_json = secrets["GCP_JSON_B64"]
            json_str = base64.b64decode(b64_json).decode('utf-8')
            key_dict = json.loads(json_str)
            st.success("✅ Conectado usando secrets.toml")
        
        # --- CREAR CREDENCIALES Y CLIENTE ---
        creds = service_account.Credentials.from_service_account_info(key_dict)
        client = bigquery.Client(credentials=creds, project=key_dict["project_id"])
        return client
        
    except Exception as e:
        st.error(f"❌ Error de conexión con BigQuery: {e}")
        st.stop()

# Inicializar el cliente
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
    
    # --- KPIs ---
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
    
    # --- Información adicional ---
    st.info(f"📅 Última lectura: {row['timestamp']}")
    
    # --- Tabla detallada ---
    with st.expander("📋 Ver detalles técnicos del registro"):
        st.dataframe(df, use_container_width=True)
    
    # --- Gráfico histórico ---
    with st.expander("📈 Tendencia últimas 24 horas"):
        df_hist = get_historical_data(seleccion, hours=24)
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
col1, col2, col3 = st.columns(3)
with col1:
    st.caption("🏢 Acueducto Metropolitano de Bucaramanga")
with col2:
    st.caption("📊 Datos hidrometeorológicos")
with col3:
    st.caption(f"⏱️ {datetime.now().strftime('%H:%M:%S')}")

# ============================================================
# 7. TABS (FUTURAS FUNCIONALIDADES)
# ============================================================
tab1, tab2, tab3 = st.tabs(["📊 Históricos", "📈 Reportes", "🤖 Asistente IA"])

with tab1:
    st.info("📊 Módulo de históricos en desarrollo...")
    with st.expander("Seleccionar rango de fechas"):
        col1, col2 = st.columns(2)
        with col1:
            fecha_inicio = st.date_input("Fecha inicio")
        with col2:
            fecha_fin = st.date_input("Fecha fin")
        st.button("Consultar histórico")

with tab2:
    st.info("📈 Módulo de reportes en desarrollo...")
    st.selectbox("Tipo de reporte:", ["Diario", "Semanal", "Mensual"])
    st.button("Generar reporte")

with tab3:
    st.info("🤖 Asistente IA en desarrollo...")
    st.text_area("Haz una pregunta sobre los datos:")
    st.button("Consultar")
