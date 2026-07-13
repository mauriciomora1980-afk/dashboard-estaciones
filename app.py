import streamlit as st
import pandas as pd
import json
import os
import base64
from google.cloud import bigquery
from google.oauth2 import service_account
from datetime import datetime, timedelta
from pytz import timezone

# ============================================================
# 1. CONFIGURACIÓN DE PÁGINA
# ============================================================
st.set_page_config(
    page_title="Centro de Monitoreo - amb", 
    page_icon="🌧️", 
    layout="wide"
)

try:
    st.sidebar.image("amb_4_punto_cero.jpg", use_container_width=True)
except:
    st.sidebar.warning("Logo no encontrado")

st.title("🌧️ Centro de Monitoreo: Red Meteorológica amb")

colombia_tz = timezone('America/Bogota')
hora_colombia = datetime.now(colombia_tz).strftime('%Y-%m-%d %H:%M:%S')
st.caption(f"🕐 Última actualización: {hora_colombia} (hora Colombia)")

# ============================================================
# 2. MATRIZ DE UMBRALES
# ============================================================
umbrales = {
    "El_Pajal":          {"amarilla": 12.3, "naranja": 15.1, "roja": 20.4},
    "Yerbabuena":        {"amarilla": 10.9, "naranja": 20.0, "roja": 40.8},
    "La_Mariana":        {"amarilla": 11.7, "naranja": 18.0, "roja": 35.0},
    "Vegas_del_Quemado": {"amarilla": 27.2, "naranja": 36.8, "roja": 55.8}
}

# ============================================================
# 3. CONFIGURACIÓN DEL EMBALSE
# ============================================================
CONFIG_EMBALSE = {
    "nivel_rebose": 885.80  # msnm - Nivel antes de rebose
}

def obtener_alerta_embalse(nivel_actual):
    """Determina el nivel de alerta para el embalse"""
    nivel_rebose = CONFIG_EMBALSE["nivel_rebose"]
    excedente = nivel_actual - nivel_rebose
    
    if excedente > 0:
        return "ROJA", f"🚨 REBOSE SUPERADO: +{excedente:.2f} msnm", "#FF4B4B", "0.5s"
    elif excedente == 0:
        return "NARANJA", "⚖️ EN PUNTO DE REBOSE", "#FF9933", "1s"
    elif excedente >= -0.30:
        return "AMARILLA", f"⚠️ CERCA DEL REBOSE: {abs(excedente):.2f} msnm", "#FFFF00", "2s"
    else:
        return "VERDE", f"✅ NORMAL: {abs(excedente):.2f} msnm bajo rebose", "#00CC96", "0s"

# ============================================================
# 4. FUNCIÓN DE ALERTAS (CON MONSALVE MEJORADO)
# ============================================================
def obtener_alerta(precipitacion, estacion):
    # Caso especial: Monsalve (en aprendizaje)
    if estacion == "Monsalve":
        if precipitacion > 0:
            return "VERDE", f"✅ Aprendizaje - Lluvia: {precipitacion:.1f} mm", "#00CC96", "0s"
        else:
            return "AZUL", "🛠️ En Aprendizaje - Sin lluvia", "#3399FF", "0s"
    
    if estacion not in umbrales:
        return "GRIS", "☁️ Sin umbrales definidos", "#CCCCCC", "0s"
    
    u = umbrales[estacion]
    if precipitacion >= u["roja"]:
        return "ROJA", f"🚨 ROJA: Excede {u['roja']}mm", "#FF4B4B", "0.5s"
    elif precipitacion >= u["naranja"]:
        return "NARANJA", f"⚠️ NARANJA: Excede {u['naranja']}mm", "#FF9933", "1s"
    elif precipitacion >= u["amarilla"]:
        return "AMARILLA", f"🟡 AMARILLA: Excede {u['amarilla']}mm", "#FFFF00", "2s"
    elif precipitacion > 0:
        return "VERDE", "✅ Lluvia Normal", "#00CC96", "0s"
    return "GRIS", "☁️ Sin lluvia", "#CCCCCC", "0s"

# ============================================================
# 5. CONEXIÓN A BIGQUERY (DE TU CÓDIGO QUE FUNCIONA)
# ============================================================
@st.cache_resource
def init_bigquery_client():
    try:
        # Intentar con variable de entorno (Cloud)
        creds_json = os.environ.get("GCP_CREDENTIALS_JSON")
        if creds_json:
            key_dict = json.loads(creds_json)
        else:
            # Intentar con secrets.toml (local)
            json_str = st.secrets["GCP_JSON_B64"]
            key_dict = json.loads(base64.b64decode(json_str))
        
        creds = service_account.Credentials.from_service_account_info(key_dict)
        return bigquery.Client(credentials=creds, project=key_dict["project_id"])
    except Exception as e:
        st.error(f"❌ Error de conexión: {e}")
        st.stop()

client = init_bigquery_client()

# ============================================================
# 6. FUNCIONES DE CONSULTA (MEJORADAS CON HISTÓRICOS)
# ============================================================
@st.cache_data(ttl=300)
def get_last_reading(estacion):
    query = f"""
    SELECT * FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones` 
    WHERE id_estacion = '{estacion}' 
    ORDER BY timestamp DESC 
    LIMIT 1
    """
    df = client.query(query).to_dataframe()
    if not df.empty:
        df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize('UTC').dt.tz_convert('America/Bogota')
    return df

@st.cache_data(ttl=600)
def get_historical_data(estacion, dias=1):
    """Obtiene datos históricos de los últimos N días"""
    query = f"""
    SELECT * FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones` 
    WHERE id_estacion = '{estacion}' 
    AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {dias} DAY)
    ORDER BY timestamp ASC
    """
    df = client.query(query).to_dataframe()
    if not df.empty:
        df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize('UTC').dt.tz_convert('America/Bogota')
    return df

@st.cache_data(ttl=600)
def get_historical_data_range(estacion, fecha_inicio, fecha_fin):
    """Obtiene datos históricos en un rango de fechas específico"""
    query = f"""
    SELECT * FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones` 
    WHERE id_estacion = '{estacion}' 
    AND timestamp >= '{fecha_inicio}'
    AND timestamp <= '{fecha_fin}'
    ORDER BY timestamp ASC
    """
    df = client.query(query).to_dataframe()
    if not df.empty:
        df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize('UTC').dt.tz_convert('America/Bogota')
    return df

# ============================================================
# 7. SIDEBAR
# ============================================================
estaciones = ["La_Mariana", "Yerbabuena", "Vegas_del_Quemado", "El_Pajal", "Monsalve", "Embalse"]
seleccion = st.sidebar.selectbox("Seleccione Estación:", estaciones)

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Opciones de Histórico")

# Selector de período para históricos
periodo_historico = st.sidebar.selectbox(
    "Período histórico:",
    ["Últimas 24 horas", "Últimos 3 días", "Últimos 7 días", "Últimos 15 días", "Último mes", "Personalizado"]
)

# Si selecciona personalizado, mostrar selectores de fecha
fecha_inicio = None
fecha_fin = None
if periodo_historico == "Personalizado":
    st.sidebar.markdown("### 📅 Seleccionar rango:")
    fecha_inicio = st.sidebar.date_input("Fecha inicio", datetime.now(colombia_tz) - timedelta(days=7))
    fecha_fin = st.sidebar.date_input("Fecha fin", datetime.now(colombia_tz))

# Mapeo de períodos a días
dias_map = {
    "Últimas 24 horas": 1,
    "Últimos 3 días": 3,
    "Últimos 7 días": 7,
    "Últimos 15 días": 15,
    "Último mes": 30
}

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Refrescar Datos", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# ============================================================
# 8. INTERFAZ PRINCIPAL
# ============================================================
st.subheader(f"📡 Datos en Tiempo Real: {seleccion}")

df = get_last_reading(seleccion)

if not df.empty:
    row = df.iloc[0]
    
    # --- SEMÁFORO ---
    if seleccion == "Embalse":
        nivel_actual = float(row['temperatura'])
        nombre, msg, color, vel = obtener_alerta_embalse(nivel_actual)
    else:
        precip_actual = float(row.get('precipitacion', 0))
        nombre, msg, color, vel = obtener_alerta(precip_actual, seleccion)
    
    st.markdown(f"""
        <div style="background-color:{color}; padding:20px; border-radius:15px; text-align:center; color:black; animation: blink {vel} infinite; border: 2px solid #333;">
            <h2 style="margin:0;">{nombre}</h2>
            <b>{msg}</b>
        </div>
        <style>@keyframes blink {{0%{{opacity:1}} 50%{{opacity:0.3}} 100%{{opacity:1}}}}</style>
    """, unsafe_allow_html=True)
    st.write("")

    # --- MÉTRICAS ---
    if seleccion == "Embalse":
        nivel_actual = float(row['temperatura'])
        nivel_rebose = CONFIG_EMBALSE["nivel_rebose"]
        excedente = nivel_actual - nivel_rebose
        
        col1, col2, col3 = st.columns(3)
        col1.metric("🌊 Nivel Actual", f"{nivel_actual:.2f} msnm")
        col2.metric("📏 Nivel de Rebose", f"{nivel_rebose:.2f} msnm")
        
        if excedente > 0:
            col3.metric("⚠️ EXCEDENTE", f"+{excedente:.2f} msnm", 
                       delta=f"{excedente:.2f} msnm", delta_color="inverse")
            st.error(f"🚨 **¡ALERTA DE REBOSE!** El nivel ({nivel_actual:.2f} msnm) **EXCEDE** el rebose ({nivel_rebose:.2f} msnm) en **{excedente:.2f} msnm**")
            st.info(f"💧 **Excedente:** {excedente*100:.1f} cm por encima del nivel máximo.")
        elif excedente < 0:
            col3.metric("📉 MARGEN", f"{abs(excedente):.2f} msnm", 
                       delta=f"{excedente:.2f} msnm", delta_color="normal")
            if abs(excedente) < 0.30:
                st.warning(f"⚠️ El nivel está a solo **{abs(excedente):.2f} msnm** del rebose")
            else:
                st.success(f"✅ El nivel está **{abs(excedente):.2f} msnm** por debajo del rebose")
        else:
            col3.metric("⚖️ EN REBOSE", f"{nivel_actual:.2f} msnm")
            st.warning(f"⚖️ El nivel está exactamente en el punto de rebose")
        
        # Voltaje
        col4, col5 = st.columns(2)
        col4.metric("🔋 Voltaje", f"{float(row['voltaje_bateria']):.1f} V")
        estado_bateria = "🟢 Activa" if float(row['voltaje_bateria']) > 11.0 else "🔴 Batería baja"
        col5.metric("📊 Estado", estado_bateria)
        
        # Información adicional del embalse
        st.caption("📐 A la espera de datos batimétricos para calcular el volumen exacto del excedente.")
        
    else:
        # Estaciones meteorológicas
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🌡️ Temp", f"{float(row['temperatura']):.1f} °C")
        c2.metric("🌧️ Precip", f"{float(row['precipitacion']):.1f} mm")
        c3.metric("💧 Humedad", f"{float(row['humedad']):.1f} %")
        c4.metric("🔋 Voltaje", f"{float(row['voltaje_bateria']):.1f} V")

    st.info(f"📅 Última lectura (Hora Colombia): {row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")

    # --- TAB 1: HISTÓRICOS (MEJORADO) ---
    tab1, tab2, tab3 = st.tabs(["📈 Históricos", "📊 Reportes", "🤖 Asistente IA"])
    
    with tab1:
        st.subheader(f"📈 Datos Históricos - {seleccion}")
        
        # Obtener datos según el período seleccionado
        if periodo_historico == "Personalizado" and fecha_inicio and fecha_fin:
            df_hist = get_historical_data_range(seleccion, fecha_inicio, fecha_fin)
        else:
            dias = dias_map.get(periodo_historico, 1)
            df_hist = get_historical_data(seleccion, dias)
        
        if not df_hist.empty:
            # Mostrar selector de qué graficar
            if seleccion == "Embalse":
                # Para embalse: solo nivel
                st.line_chart(df_hist.set_index('timestamp')[['temperatura']], height=400)
                st.caption("🌊 Nivel del embalse (msnm)")
                
                # Agregar línea de rebose
                st.info(f"📏 Línea de rebose: {CONFIG_EMBALSE['nivel_rebose']} msnm")
            else:
                # Para estaciones meteorológicas: temperatura, precipitación, humedad
                col1, col2 = st.columns(2)
                with col1:
                    st.line_chart(df_hist.set_index('timestamp')[['temperatura']], height=300)
                    st.caption("🌡️ Temperatura (°C)")
                with col2:
                    st.line_chart(df_hist.set_index('timestamp')[['precipitacion']], height=300)
                    st.caption("🌧️ Precipitación (mm)")
                
                # Opcional: humedad
                st.line_chart(df_hist.set_index('timestamp')[['humedad']], height=200)
                st.caption("💧 Humedad (%)")
            
            # Mostrar datos en tabla
            with st.expander("📋 Ver datos detallados"):
                st.dataframe(df_hist, use_container_width=True)
            
            # Descargar CSV
            csv = df_hist.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descargar datos históricos (CSV)",
                data=csv,
                file_name=f"{seleccion}_historico_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.warning("⚠️ No hay datos históricos disponibles para el período seleccionado.")
            st.info("💡 Los datos comienzan a acumularse desde hoy. Vuelve en unos días para ver más tendencias.")

    with tab2:
        st.subheader("📋 Módulo de Reportes")
        st.info("🚧 Esta funcionalidad está en desarrollo.")
        st.markdown("""
        **Próximas características:**
        - Reportes diarios/semanales/mensuales
        - Exportación a PDF
        - Estadísticas y tendencias
        - Alertas por correo
        """)
        
        # Reporte rápido
        if st.button("📊 Generar Reporte Rápido"):
            with st.spinner("Generando reporte..."):
                import time
                time.sleep(1)
                st.success("✅ Reporte generado exitosamente!")
                
                if seleccion == "Embalse":
                    st.json({
                        "estacion": seleccion,
                        "fecha": row['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                        "nivel": float(row['temperatura']),
                        "excedente": float(row['temperatura']) - CONFIG_EMBALSE["nivel_rebose"],
                        "voltaje": float(row['voltaje_bateria'])
                    })
                else:
                    st.json({
                        "estacion": seleccion,
                        "fecha": row['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                        "temperatura": float(row['temperatura']),
                        "precipitacion": float(row['precipitacion']),
                        "humedad": float(row['humedad']),
                        "voltaje": float(row['voltaje_bateria'])
                    })

    with tab3:
        st.subheader("🤖 Asistente IA")
        st.info("🚧 Esta funcionalidad está en desarrollo.")
        st.markdown("""
        **Próximas características:**
        - Análisis predictivo de precipitación
        - Detección de anomalías
        - Recomendaciones automáticas
        - Alertas inteligentes
        """)
        
        # Simulación de IA
        if st.button("💬 Consultar al Asistente"):
            with st.spinner("Analizando datos..."):
                time.sleep(2)
                if seleccion == "Embalse":
                    nivel = float(row['temperatura'])
                    excedente = nivel - CONFIG_EMBALSE["nivel_rebose"]
                    st.success("🤖 Análisis del embalse:")
                    st.write(f"- Nivel actual: {nivel:.2f} msnm")
                    st.write(f"- Estado: {nombre}")
                    if excedente > 0:
                        st.warning("⚠️ ¡ALERTA! El nivel ha superado el rebose. Se recomienda monitoreo constante.")
                    elif abs(excedente) < 0.30:
                        st.warning("⚡ El nivel se acerca al rebose. Mantener vigilancia.")
                    else:
                        st.info("✅ Nivel dentro de parámetros normales.")
                else:
                    st.success(f"🤖 Análisis de la estación {seleccion}:")
                    st.write(f"- Temperatura: {float(row['temperatura']):.1f}°C")
                    st.write(f"- Precipitación: {float(row['precipitacion']):.1f} mm")
                    st.write(f"- Estado: {nombre}")

else:
    st.warning("⚠️ No hay datos disponibles para esta estación.")
    st.info("💡 Verifica la conexión a la base de datos o selecciona otra estación.")

# ============================================================
# 9. FOOTER
# ============================================================
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 20px;">
    <p>🌧️ Centro de Monitoreo - Red Meteorológica amb</p>
    <p style="font-size: 12px;">Desarrollado con ❤️ usando Streamlit | Datos en tiempo real desde BigQuery</p>
</div>
""", unsafe_allow_html=True)
