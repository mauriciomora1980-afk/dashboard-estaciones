import streamlit as st
import pandas as pd
import json
import os
import base64
from google.cloud import bigquery
from google.oauth2 import service_account
from datetime import datetime
from pytz import timezone
import plotly.express as px
import plotly.graph_objects as go

# ============================================================
# 1. CONFIGURACIÓN Y LOGO
# ============================================================
st.set_page_config(page_title="Centro de Monitoreo - amb", page_icon="🌧️", layout="wide")

logo_path = os.path.join(os.path.dirname(__file__), "amb_4_punto_cero.jpg")
try:
    st.sidebar.image(logo_path, use_column_width=True)
except:
    st.sidebar.warning("Logo no cargado")

st.title("🌧️ Centro de Monitoreo: Red Meteorológica amb")
colombia_tz = timezone('America/Bogota')
st.caption(f"🕐 Última actualización: {datetime.now(colombia_tz).strftime('%Y-%m-%d %H:%M:%S')} (hora Colombia)")

# ============================================================
# 2. UMBRALES Y ALERTAS (SEMÁFORO)
# ============================================================
umbrales = {
    "El_Pajal": {"amarilla": 12.3, "naranja": 15.1, "roja": 20.4},
    "Yerbabuena": {"amarilla": 10.9, "naranja": 20.0, "roja": 40.8},
    "La_Mariana": {"amarilla": 11.7, "naranja": 18.0, "roja": 35.0},
    "Vegas_del_Quemado": {"amarilla": 27.2, "naranja": 36.8, "roja": 55.8}
}

def obtener_alerta(precipitacion, estacion):
    """
    Función que determina el nivel de alerta según la precipitación
    Retorna: (nombre_alerta, mensaje, color, velocidad_animacion)
    """
    # Casos especiales
    if estacion == "Monsalve":
        return "AZUL", "🛠️ En Aprendizaje", "#3399FF", "0s"
    if estacion not in umbrales:
        return "GRIS", "☁️ Sin umbrales definidos", "#CCCCCC", "0s"
    
    # Evaluación de umbrales
    u = umbrales[estacion]
    if precipitacion >= u["roja"]:
        return "ROJA", f"🚨 ROJA: Excede {u['roja']}mm", "#FF4B4B", "0.5s"
    elif precipitacion >= u["naranja"]:
        return "NARANJA", f"⚠️ NARANJA: Excede {u['naranja']}mm", "#FF9933", "1s"
    elif precipitacion >= u["amarilla"]:
        return "AMARILLA", f"🟡 AMARILLA: Excede {u['amarilla']}mm", "#FFFF00", "2s"
    elif precipitacion > 0:
        return "VERDE", "✅ Lluvia Normal", "#00CC96", "0s"
    else:
        return "GRIS", "☁️ Sin lluvia", "#CCCCCC", "0s"

# ============================================================
# 3. CLIENTE BIGQUERY
# ============================================================
@st.cache_resource
def init_bigquery_client():
    try:
        json_str = base64.b64decode(st.secrets["GCP_JSON_B64"]).decode('utf-8')
        key_dict = json.loads(json_str)
        creds = service_account.Credentials.from_service_account_info(key_dict)
        return bigquery.Client(credentials=creds, project=key_dict["project_id"])
    except Exception as e:
        st.error(f"❌ Error al conectar con BigQuery: {e}")
        st.stop()

client = init_bigquery_client()

# ============================================================
# 4. FUNCIONES DE CONSULTA A BIGQUERY
# ============================================================
@st.cache_data(ttl=300)
def get_last_reading(estacion):
    """
    Obtiene la última lectura de una estación
    """
    try:
        query = f"""
        SELECT * FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones` 
        WHERE id_estacion = '{estacion}' 
        ORDER BY SAFE_CAST(timestamp AS TIMESTAMP) DESC 
        LIMIT 1
        """
        df = client.query(query).to_dataframe()
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize('UTC').dt.tz_convert('America/Bogota')
        return df
    except Exception as e:
        st.error(f"❌ Error al obtener última lectura: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=600)
def get_historical_data(estacion, horas=24):
    """
    Obtiene datos históricos de una estación
    """
    try:
        # Validación de parámetros
        if horas < 1:
            horas = 1
        if horas > 72:  # Limitamos a 72 horas para evitar timeout
            horas = 72
            st.sidebar.info("⏱️ Máximo 72 horas permitido")
        
        # Consulta con SAFE_CAST para convertir timestamp
        query = f"""
        SELECT * FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones` 
        WHERE id_estacion = '{estacion}' 
        AND SAFE_CAST(timestamp AS TIMESTAMP) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {horas} HOUR)
        ORDER BY SAFE_CAST(timestamp AS TIMESTAMP) DESC 
        LIMIT 1000
        """
        
        df = client.query(query).to_dataframe()
        
        if df.empty:
            st.sidebar.warning(f"⚠️ No hay datos para {estacion} en las últimas {horas} horas")
            return df
            
        df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize('UTC').dt.tz_convert('America/Bogota')
        st.sidebar.success(f"✅ {len(df)} registros históricos")
        return df
        
    except Exception as e:
        st.error(f"❌ Error en datos históricos: {str(e)}")
        return pd.DataFrame()

# ============================================================
# 5. FUNCIÓN PARA CREAR ROSA DE LOS VIENTOS
# ============================================================
def create_wind_rose(df, estacion):
    """
    Crea la rosa de los vientos con Plotly
    """
    try:
        if 'direccion_del_viento' not in df.columns or 'velocidad_viento' not in df.columns:
            return None
            
        df_viento = df.dropna(subset=['direccion_del_viento', 'velocidad_viento'])
        if df_viento.empty:
            return None
            
        # Crear rosa de los vientos
        fig = px.bar_polar(
            df_viento,
            r="velocidad_viento",
            theta="direccion_del_viento",
            color="velocidad_viento",
            color_continuous_scale='Viridis',
            title=f'Rosa de Vientos - {estacion}',
            template='plotly_white'
        )
        fig.update_layout(height=400)
        return fig
    except Exception as e:
        st.warning(f"No se pudo generar la rosa de los vientos: {e}")
        return None

# ============================================================
# 6. INTERFAZ PRINCIPAL
# ============================================================
# Sidebar
estaciones = ["La_Mariana", "Yerbabuena", "Vegas_del_Quemado", "El_Pajal", "Monsalve", "Embalse"]
seleccion = st.sidebar.selectbox("Seleccione Estación:", estaciones)
horas = st.sidebar.slider("⏱️ Horas históricas:", 1, 72, 24, step=1, help="Máximo 72 horas (3 días)")

# Cargar datos con spinner
with st.spinner("🔄 Cargando datos..."):
    df = get_last_reading(seleccion)
    df_hist = get_historical_data(seleccion, horas)

# ============================================================
# 7. TABS
# ============================================================
tab1, tab2, tab3 = st.tabs(["📊 Situación Actual", "📈 Históricos", "🤖 Asistente IA"])

# ============================================================
# TAB 1: SITUACIÓN ACTUAL
# ============================================================
with tab1:
    if not df.empty:
        row = df.iloc[0]
        st.subheader(f"📡 Real-time: {seleccion}")
        
        # Mostrar semáforo solo para estaciones con umbrales
        if seleccion != "Embalse":
            # Obtener alerta
            precipitacion_actual = float(row.get('precipitacion', 0))
            nombre, msg, color, vel = obtener_alerta(precipitacion_actual, seleccion)
            
            # Mostrar semáforo con animación
            st.markdown(f'''
            <div style="background-color:{color}; padding:20px; border-radius:15px; text-align:center; color:black; animation: blink {vel} infinite; border: 3px solid #333; box-shadow: 0 4px 8px rgba(0,0,0,0.2);">
                <h1 style="margin:0;">🚦 {nombre}</h1>
                <h3 style="margin:5px 0;">{msg}</h3>
                <p style="margin:0; font-size:14px;">Precipitación: {precipitacion_actual:.1f} mm</p>
            </div>
            <style>
            @keyframes blink {{
                0%{{opacity:1}} 
                50%{{opacity:0.4}} 
                100%{{opacity:1}}
            }}
            </style>
            ''', unsafe_allow_html=True)
            st.write("")
            
            # Métricas principales
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("🌡️ Temperatura", f"{float(row['temperatura']):.1f} °C")
            with c2:
                st.metric("🌧️ Precipitación", f"{float(row['precipitacion']):.1f} mm")
            with c3:
                st.metric("💧 Humedad", f"{float(row['humedad']):.1f} %")
            with c4:
                st.metric("🔋 Voltaje", f"{float(row['voltaje_bateria']):.1f} V")
        else:
            # Embalse - mostrar solo nivel
            st.metric("🌊 Nivel del Embalse", f"{float(row['temperatura']):.2f} msnm")
        
        # Información de la última lectura
        st.info(f"📅 Última lectura: {row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Estadísticas del período
        if not df_hist.empty:
            st.markdown("### 📊 Estadísticas del Período")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🔽 Temp Mínima", f"{df_hist['temperatura'].min():.1f}°C")
            with col2:
                st.metric("🔼 Temp Máxima", f"{df_hist['temperatura'].max():.1f}°C")
            with col3:
                st.metric("📊 Temp Promedio", f"{df_hist['temperatura'].mean():.1f}°C")
            
            # Precipitación total
            st.metric("🌧️ Precipitación Total", f"{df_hist['precipitacion'].sum():.1f} mm")
    else:
        st.warning("⚠️ No hay datos disponibles para esta estación")
        st.info("💡 Verifica que la estación tenga datos en BigQuery")

# ============================================================
# TAB 2: HISTÓRICOS
# ============================================================
with tab2:
    if not df_hist.empty:
        st.subheader("📈 Series de Tiempo")
        
        # Gráfico de Temperatura
        st.markdown("### 🌡️ Temperatura")
        fig_temp = px.line(
            df_hist.sort_values('timestamp'), 
            x='timestamp', 
            y='temperatura',
            title=f'Temperatura - {seleccion}',
            labels={'temperatura': '°C', 'timestamp': 'Fecha/Hora'}
        )
        fig_temp.update_layout(
            height=350, 
            template='plotly_white',
            hovermode='x unified'
        )
        fig_temp.add_hline(
            y=df_hist['temperatura'].mean(), 
            line_dash="dash", 
            line_color="red",
            annotation_text=f"Promedio: {df_hist['temperatura'].mean():.1f}°C"
        )
        st.plotly_chart(fig_temp, use_container_width=True)
        
        # Gráfico de Precipitación
        st.markdown("### 🌧️ Precipitación")
        fig_precip = px.bar(
            df_hist.sort_values('timestamp'), 
            x='timestamp', 
            y='precipitacion',
            title=f'Precipitación - {seleccion}',
            labels={'precipitacion': 'mm', 'timestamp': 'Fecha/Hora'},
            color='precipitacion',
            color_continuous_scale='Blues'
        )
        fig_precip.update_layout(height=350, template='plotly_white')
        st.plotly_chart(fig_precip, use_container_width=True)
        
        # Rosa de los Vientos
        st.markdown("### 🧭 Rosa de los Vientos")
        fig_viento = create_wind_rose(df_hist, seleccion)
        if fig_viento:
            st.plotly_chart(fig_viento, use_container_width=True)
        else:
            st.info("ℹ️ No hay datos de viento disponibles para esta estación")
        
        # Exportar datos
        st.markdown("### 📥 Exportar Datos")
        col1, col2 = st.columns(2)
        
        with col1:
            # Descargar CSV
            csv = df_hist.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Descargar CSV",
                csv,
                f"datos_{seleccion}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                "text/csv",
                use_container_width=True
            )
        
        with col2:
            # Descargar Excel
            try:
                from io import BytesIO
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_hist.to_excel(writer, sheet_name='Datos', index=False)
                st.download_button(
                    "📊 Descargar Excel",
                    output.getvalue(),
                    f"datos_{seleccion}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            except:
                st.warning("⚠️ No se pudo generar el archivo Excel")
    else:
        st.info("ℹ️ No hay datos históricos disponibles para este período")

# ============================================================
# TAB 3: ASISTENTE IA
# ============================================================
with tab3:
    st.subheader("🤖 Asistente IA")
    st.info("🚧 Esta funcionalidad está en desarrollo")
    
    # Mostrar resumen de datos para el asistente
    if not df_hist.empty:
        st.markdown("### 📊 Resumen de Datos Disponibles")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📅 Período", f"{df_hist['timestamp'].min().strftime('%d/%m/%Y')} - {df_hist['timestamp'].max().strftime('%d/%m/%Y')}")
        with col2:
            st.metric("📊 Registros", len(df_hist))
        with col3:
            st.metric("🌧️ Lluvia Total", f"{df_hist['precipitacion'].sum():.1f} mm")
        
        # Mostrar últimas lecturas
        st.markdown("### 📋 Últimas 5 Lecturas")
        st.dataframe(df_hist.head(5), use_container_width=True)
    
    # Input para preguntas
    st.text_input("💬 Haz tu pregunta sobre los datos:", placeholder="Ej: ¿Cuál fue la temperatura máxima?")
    st.button("Enviar", disabled=True, help="Funcionalidad en desarrollo")
    
    st.caption("💡 Próximamente: Análisis con IA para predicciones y alertas avanzadas")

# ============================================================
# 8. FOOTER (PIE DE PÁGINA)
# ============================================================
st.sidebar.markdown("---")
st.sidebar.caption("🚀 Dashboard desarrollado por amb")
st.sidebar.caption(f"📊 Datos actualizados cada 5 minutos")

# Mostrar estaciones disponibles en el sidebar
with st.sidebar.expander("📋 Estaciones Disponibles"):
    for est in estaciones:
        if est in umbrales:
            st.write(f"✅ {est}")
        else:
            st.write(f"ℹ️ {est} (sin umbrales)")

# Mostrar umbrales en el sidebar
with st.sidebar.expander("📊 Umbrales de Alerta"):
    for estacion, valores in umbrales.items():
        st.write(f"**{estacion}:**")
        st.write(f"  🟡 Amarilla: {valores['amarilla']}mm")
        st.write(f"  🟠 Naranja: {valores['naranja']}mm")
        st.write(f"  🔴 Roja: {valores['roja']}mm")
        st.write("---")
