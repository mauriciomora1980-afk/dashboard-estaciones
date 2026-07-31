# Versión completa con todas las mejoras
import streamlit as st
import pandas as pd
import json
import os
import base64
from google.cloud import bigquery
from google.oauth2 import service_account
from datetime import datetime, timedelta
from pytz import timezone
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

# Configuración
st.set_page_config(page_title="Centro de Monitoreo - amb", page_icon="🌧️", layout="wide")

# Logo
logo_path = os.path.join(os.path.dirname(__file__), "amb_4_punto_cero.jpg")
try:
    st.sidebar.image(logo_path, use_column_width=True)
except:
    st.sidebar.warning("Logo no cargado")

st.title("🌧️ Centro de Monitoreo: Red Meteorológica amb")
colombia_tz = timezone('America/Bogota')
st.caption(f"🕐 Última actualización: {datetime.now(colombia_tz).strftime('%Y-%m-%d %H:%M:%S')} (hora Colombia)")

# Umbrales
umbrales = {
    "El_Pajal": {"amarilla": 12.3, "naranja": 15.1, "roja": 20.4},
    "Yerbabuena": {"amarilla": 10.9, "naranja": 20.0, "roja": 40.8},
    "La_Mariana": {"amarilla": 11.7, "naranja": 18.0, "roja": 35.0},
    "Vegas_del_Quemado": {"amarilla": 27.2, "naranja": 36.8, "roja": 55.8}
}

# Función de alerta
def obtener_alerta(precipitacion, estacion):
    if estacion == "Monsalve": return "AZUL", "🛠️ En Aprendizaje", "#3399FF", "0s"
    if estacion not in umbrales: return "GRIS", "☁️ Sin umbrales definidos", "#CCCCCC", "0s"
    u = umbrales[estacion]
    if precipitacion >= u["roja"]: return "ROJA", f"🚨 ROJA: Excede {u['roja']}mm", "#FF4B4B", "0.5s"
    elif precipitacion >= u["naranja"]: return "NARANJA", f"⚠️ NARANJA: Excede {u['naranja']}mm", "#FF9933", "1s"
    elif precipitacion >= u["amarilla"]: return "AMARILLA", f"🟡 AMARILLA: Excede {u['amarilla']}mm", "#FFFF00", "2s"
    elif precipitacion > 0: return "VERDE", "✅ Lluvia Normal", "#00CC96", "0s"
    return "GRIS", "☁️ Sin lluvia", "#CCCCCC", "0s"

# Cliente BigQuery
@st.cache_resource
def init_bigquery_client():
    try:
        json_str = base64.b64decode(st.secrets["GCP_JSON_B64"]).decode('utf-8')
        key_dict = json.loads(json_str)
        creds = service_account.Credentials.from_service_account_info(key_dict)
        return bigquery.Client(credentials=creds, project=key_dict["project_id"])
    except:
        st.stop()

client = init_bigquery_client()

# Funciones de datos
@st.cache_data(ttl=300)
def get_last_reading(estacion):
    query = f"SELECT * FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones` WHERE id_estacion = '{estacion}' ORDER BY timestamp DESC LIMIT 1"
    df = client.query(query).to_dataframe()
    if not df.empty: 
        df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize('UTC').dt.tz_convert('America/Bogota')
    return df

@st.cache_data(ttl=600)
def get_historical_data(estacion, horas=24):
    query = f"""
    SELECT * FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones` 
    WHERE id_estacion = '{estacion}' 
    AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {horas} HOUR)
    ORDER BY timestamp DESC 
    LIMIT 1000
    """
    df = client.query(query).to_dataframe()
    df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize('UTC').dt.tz_convert('America/Bogota')
    return df

# Sidebar
estaciones = ["La_Mariana", "Yerbabuena", "Vegas_del_Quemado", "El_Pajal", "Monsalve", "Embalse"]
seleccion = st.sidebar.selectbox("Seleccione Estación:", estaciones)

# Filtro de horas
horas = st.sidebar.slider("⏱️ Horas históricas:", 1, 168, 24, help="1-24 horas, hasta 7 días (168 horas)")

# Cargar datos
df = get_last_reading(seleccion)
df_hist = get_historical_data(seleccion, horas)

# Tabs
tab1, tab2, tab3 = st.tabs(["📊 Situación Actual", "📈 Históricos", "🤖 Asistente IA"])

with tab1:
    if not df.empty:
        row = df.iloc[0]
        st.subheader(f"📡 Real-time: {seleccion}")
        
        if seleccion != "Embalse":
            nombre, msg, color, vel = obtener_alerta(float(row.get('precipitacion', 0)), seleccion)
            st.markdown(f'<div style="background-color:{color}; padding:20px; border-radius:15px; text-align:center; color:black; animation: blink {vel} infinite; border: 2px solid #333;"><h2>{nombre}</h2><b>{msg}</b></div><style>@keyframes blink {{0%{{opacity:1}} 50%{{opacity:0.3}} 100%{{opacity:1}}}}</style>', unsafe_allow_html=True)
            st.write("")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("🌡️ Temp", f"{float(row['temperatura']):.1f} °C")
            c2.metric("🌧️ Precip", f"{float(row['precipitacion']):.1f} mm")
            c3.metric("💧 Humedad", f"{float(row['humedad']):.1f} %")
            c4.metric("🔋 Voltaje", f"{float(row['voltaje_bateria']):.1f} V")
        else:
            st.metric("🌊 Nivel", f"{float(row['temperatura']):.2f} msnm")
        st.info(f"📅 Última lectura: {row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Estadísticas
        if not df_hist.empty:
            st.markdown("### 📊 Estadísticas del Período")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🔽 Temp Mínima", f"{df_hist['temperatura'].min():.1f}°C")
            with col2:
                st.metric("🔼 Temp Máxima", f"{df_hist['temperatura'].max():.1f}°C")
            with col3:
                st.metric("📊 Promedio Temp", f"{df_hist['temperatura'].mean():.1f}°C")
    else:
        st.warning("⚠️ Sin datos.")

with tab2:
    if not df_hist.empty:
        st.subheader("📈 Series de Tiempo")
        
        # Temperatura
        st.markdown("### 🌡️ Temperatura")
        fig_temp = px.line(df_hist.sort_values('timestamp'), x='timestamp', y='temperatura',
                          title=f'Temperatura - {seleccion}',
                          labels={'temperatura': '°C', 'timestamp': 'Fecha/Hora'})
        fig_temp.update_layout(height=300, template='plotly_white')
        st.plotly_chart(fig_temp, use_container_width=True)
        
        # Precipitación
        st.markdown("### 🌧️ Precipitación")
        fig_precip = px.bar(df_hist.sort_values('timestamp'), x='timestamp', y='precipitacion',
                           title=f'Precipitación - {seleccion}',
                           labels={'precipitacion': 'mm', 'timestamp': 'Fecha/Hora'},
                           color='precipitacion',
                           color_continuous_scale='Blues')
        fig_precip.update_layout(height=300, template='plotly_white')
        st.plotly_chart(fig_precip, use_container_width=True)
        
        # Vientos
        if 'direccion_del_viento' in df_hist.columns and 'velocidad_viento' in df_hist.columns:
            st.markdown("### 🧭 Rosa de los Vientos")
            df_viento = df_hist.dropna(subset=['direccion_del_viento', 'velocidad_viento'])
            if not df_viento.empty:
                fig_viento = px.bar_polar(df_viento, r="velocidad_viento", theta="direccion_del_viento",
                                         color="velocidad_viento", color_continuous_scale='Viridis',
                                         title=f'Rosa de Vientos - {seleccion}', template='plotly_white')
                fig_viento.update_layout(height=400)
                st.plotly_chart(fig_viento, use_container_width=True)
        
        # Descarga
        st.markdown("### 📥 Exportar Datos")
        csv = df_hist.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar CSV", csv, f"datos_{seleccion}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", "text/csv")
    else:
        st.info("No hay datos históricos disponibles")

with tab3:
    st.subheader("🤖 Asistente IA")
    st.text_input("Haz tu pregunta sobre los datos:")
    st.button("Enviar")
