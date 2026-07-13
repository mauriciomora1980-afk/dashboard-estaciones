import streamlit as st
import pandas as pd
import json
import base64
from google.cloud import bigquery
from google.oauth2 import service_account
from datetime import datetime
from pytz import timezone

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="AMB Hidrología", layout="wide")

# Cargar Logo (Asegúrate de que el archivo amb_4_punto_cero.jpg esté en el repo)
try:
    st.sidebar.image("amb_4_punto_cero.jpg", use_container_width=True)
except:
    st.sidebar.warning("Logo no encontrado")

st.title("🌧️ Centro de Monitoreo: Red Meteorológica amb")

# --- LÓGICA DE UMBRALES Y SEMÁFORO ---
umbrales = {
    "El_Pajal": {"amarilla": 12.3, "naranja": 15.1, "roja": 20.4},
    "Yerbabuena": {"amarilla": 10.9, "naranja": 20.0, "roja": 40.8},
    "La_Mariana": {"amarilla": 11.7, "naranja": 18.0, "roja": 35.0},
    "Vegas_del_Quemado": {"amarilla": 27.2, "naranja": 36.8, "roja": 55.8}
}

def obtener_alerta(precipitacion, estacion):
    if estacion == "Monsalve": return "AZUL", "🛠️ En Aprendizaje", "#3399FF", "0s"
    if estacion not in umbrales: return "GRIS", "☁️ Sin umbrales definidos", "#CCCCCC", "0s"
    u = umbrales[estacion]
    if precipitacion >= u["roja"]: return "ROJA", f"🚨 ROJA: Excede {u['roja']}mm", "#FF4B4B", "0.5s"
    elif precipitacion >= u["naranja"]: return "NARANJA", f"⚠️ NARANJA: Excede {u['naranja']}mm", "#FF9933", "1s"
    elif precipitacion >= u["amarilla"]: return "AMARILLA", f"🟡 AMARILLA: Excede {u['amarilla']}mm", "#FFFF00", "2s"
    elif precipitacion > 0: return "VERDE", "✅ Lluvia Normal", "#00CC96", "0s"
    return "GRIS", "☁️ Sin lluvia", "#CCCCCC", "0s"

# --- CONEXIÓN ---
@st.cache_resource
def init_bigquery_client():
    try:
        json_str = st.secrets["GCP_JSON_B64"]
        key_dict = json.loads(base64.b64decode(json_str))
        creds = service_account.Credentials.from_service_account_info(key_dict)
        return bigquery.Client(credentials=creds, project=key_dict["project_id"])
    except:
        st.error("Error de credenciales")
        st.stop()

client = init_bigquery_client()

# --- FUNCIONES DE CONSULTA ---
@st.cache_data(ttl=300)
def get_data(estacion):
    query = f"SELECT * FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones` WHERE id_estacion = '{estacion}' ORDER BY timestamp DESC LIMIT 1"
    return client.query(query).to_dataframe()

# --- INTERFAZ ---
estaciones = ["La_Mariana", "Yerbabuena", "Vegas_del_Quemado", "El_Pajal", "Monsalve", "Embalse"]
seleccion = st.sidebar.selectbox("Seleccione Estación:", estaciones)
df = get_data(seleccion)

if not df.empty:
    row = df.iloc[0]
    
    # KPIs y Semáforo
    if seleccion != "Embalse":
        nombre, msg, color, vel = obtener_alerta(float(row.get('precipitacion', 0)), seleccion)
        st.markdown(f'<div style="background-color:{color}; padding:15px; border-radius:10px; text-align:center; animation: blink {vel} infinite;"><h3>{nombre}</h3>{msg}</div><style>@keyframes blink {{0%{{opacity:1}} 50%{{opacity:0.3}} 100%{{opacity:1}}}}</style>', unsafe_allow_html=True)
        st.write("")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Temperatura", f"{row['temperatura']:.1f}°C")
        c2.metric("Precipitación", f"{row['precipitacion']:.1f}mm")
        c3.metric("Humedad", f"{row['humedad']:.1f}%")
        c4.metric("Voltaje", f"{row['voltaje_bateria']:.1f}V")
    else:
        st.metric("🌊 Nivel Embalse", f"{row['temperatura']:.2f} msnm")

    # --- TABS: AQUÍ RECUPERAMOS LOS HISTÓRICOS Y IA ---
    tab1, tab2 = st.tabs(["📈 Series de Tiempo", "🤖 Asistente IA"])
    
    with tab1:
        st.write("Visualización de histórico 24h")
        st.line_chart(get_historical_data(seleccion, 24).set_index('timestamp')[['temperatura', 'precipitacion']])
    
    with tab2:
        st.write("Consulta al Agente IA sobre los datos de esta estación:")
        st.text_input("Pregunta:")
        st.button("Enviar consulta")
else:
    st.warning("Sin datos.")
