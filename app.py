import streamlit as st
import pandas as pd
import json
import os
import base64
import requests
from google.cloud import bigquery
from google.oauth2 import service_account
from datetime import datetime, timedelta
from pytz import timezone
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

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
# 2. CONFIGURACIÓN DEL AGENTE IA (URL CORREGIDA)
# ============================================================
# URL de tu Cloud Run con el endpoint webhook
AGENTE_API_URL = "https://ingesta-amb-oficial-661926446380.us-central1.run.app/webhook"

# ============================================================
# 3. UMBRALES Y ALERTAS (SEMÁFORO)
# ============================================================
umbrales = {
    "El_Pajal": {"amarilla": 12.3, "naranja": 15.1, "roja": 20.4},
    "Yerbabuena": {"amarilla": 10.9, "naranja": 20.0, "roja": 40.8},
    "La_Mariana": {"amarilla": 11.7, "naranja": 18.0, "roja": 35.0},
    "Vegas_del_Quemado": {"amarilla": 27.2, "naranja": 36.8, "roja": 55.8}
}

# Nivel de rebase del embalse
NIVEL_REBASE_EMBALSE = 885.80

def obtener_alerta(precipitacion, estacion):
    """
    Función que determina el nivel de alerta según la precipitación
    Retorna: (nombre_alerta, mensaje, color, velocidad_animacion)
    """
    # Casos especiales
    if estacion == "Monsalve":
        return "AZUL", "🛠️ En Aprendizaje", "#3399FF", "0s"
    if estacion == "Embalse":
        return "EMBALSE", "🌊 Nivel de Embalse", "#00BFFF", "0s"
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

def evaluar_nivel_embalse(nivel_actual):
    """
    Evalúa el nivel del embalse y retorna el estado
    """
    excedente = nivel_actual - NIVEL_REBASE_EMBALSE
    if excedente >= 0:
        estado = "🔴 EXCEDENTE"
        color = "#FF4B4B"
        mensaje = f"{excedente:.2f} msnm por encima del nivel de rebase"
    else:
        estado = "🟢 NORMAL"
        color = "#00CC96"
        mensaje = f"{abs(excedente):.2f} msnm por debajo del nivel de rebase"
    return estado, color, mensaje, excedente

# ============================================================
# 4. CLIENTE BIGQUERY
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
# 5. FUNCIONES DE CONSULTA A BIGQUERY
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
        if horas > 720:  # 30 días máximo
            horas = 720
        
        # Consulta con SAFE_CAST para convertir timestamp
        query = f"""
        SELECT * FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones` 
        WHERE id_estacion = '{estacion}' 
        AND SAFE_CAST(timestamp AS TIMESTAMP) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {horas} HOUR)
        ORDER BY SAFE_CAST(timestamp AS TIMESTAMP) DESC 
        LIMIT 5000
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
# 6. FUNCIÓN PARA CONSULTAR AGENTE IA
# ============================================================
@st.cache_data(ttl=60)
def consultar_agente_ia(pregunta):
    """
    Consulta el agente IA desplegado en Cloud Run
    """
    try:
        headers = {"Content-Type": "application/json"}
        payload = {"prompt": pregunta}
        
        response = requests.post(AGENTE_API_URL, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "status": "error",
                "mensaje": f"Error en la API: {response.status_code}"
            }
    except requests.exceptions.Timeout:
        return {
            "status": "error",
            "mensaje": "⏱️ Tiempo de espera agotado. La consulta está tomando demasiado tiempo."
        }
    except requests.exceptions.ConnectionError:
        return {
            "status": "error",
            "mensaje": "❌ No se pudo conectar al agente IA. Verifica que el servicio esté corriendo."
        }
    except Exception as e:
        return {
            "status": "error",
            "mensaje": f"❌ Error al consultar el agente: {str(e)}"
        }

def verificar_agente_ia():
    """
    Verifica si el agente IA está disponible
    """
    try:
        response = requests.post(
            AGENTE_API_URL,
            json={"prompt": "ping"},
            timeout=5
        )
        return response.status_code == 200 or response.status_code == 400
    except:
        return False

# ============================================================
# 7. FUNCIONES DE VISUALIZACIÓN
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

def create_embalse_chart(df_hist):
    """
    Crea el gráfico del nivel del embalse con línea de rebase
    """
    try:
        if df_hist.empty:
            return None
            
        # Ordenar por timestamp
        df_ordenado = df_hist.sort_values('timestamp')
        
        # Crear gráfico
        fig = go.Figure()
        
        # Línea del nivel del embalse (usando temperatura como nivel)
        fig.add_trace(go.Scatter(
            x=df_ordenado['timestamp'],
            y=df_ordenado['temperatura'],
            mode='lines',
            name='Nivel del embalse',
            line=dict(color='#00BFFF', width=2),
            fill='tozeroy',
            fillcolor='rgba(0, 191, 255, 0.2)'
        ))
        
        # Línea de rebase
        fig.add_hline(
            y=NIVEL_REBASE_EMBALSE,
            line_dash="dash",
            line_color="red",
            line_width=2,
            annotation_text=f"Línea de rebase: {NIVEL_REBASE_EMBALSE} msnm",
            annotation_position="top right"
        )
        
        # Configuración del layout
        fig.update_layout(
            title='Nivel del Embalse (msnm)',
            xaxis_title='Fecha/Hora',
            yaxis_title='Nivel (msnm)',
            height=400,
            template='plotly_white',
            hovermode='x unified'
        )
        
        return fig
    except Exception as e:
        st.warning(f"No se pudo generar el gráfico del embalse: {e}")
        return None

# ============================================================
# 8. INTERFAZ PRINCIPAL
# ============================================================
# Sidebar
estaciones = ["La_Mariana", "Yerbabuena", "Vegas_del_Quemado", "El_Pajal", "Monsalve", "Embalse"]
seleccion = st.sidebar.selectbox("Seleccione Estación:", estaciones)

# Opciones de período histórico
periodos = {
    "Últimas 24 horas": 24,
    "Últimos 3 días": 72,
    "Últimos 7 días": 168,
    "Últimos 15 días": 360,
    "Último mes": 720,
    "Personalizado": 0
}

if seleccion == "Embalse":
    st.sidebar.markdown("### 📊 Opciones de Histórico")
    periodo_seleccionado = st.sidebar.selectbox(
        "Seleccione período:",
        list(periodos.keys())
    )
    
    if periodo_seleccionado == "Personalizado":
        dias = st.sidebar.number_input("Días:", min_value=1, max_value=30, value=7)
        horas = dias * 24
    else:
        horas = periodos[periodo_seleccionado]
else:
    horas = st.sidebar.slider("⏱️ Horas históricas:", 1, 168, 24, step=1, help="Máximo 7 días (168 horas)")

# Cargar datos con spinner
with st.spinner("🔄 Cargando datos..."):
    df = get_last_reading(seleccion)
    df_hist = get_historical_data(seleccion, horas)

# ============================================================
# 9. TABS
# ============================================================
if seleccion == "Embalse":
    tab1, tab2, tab3 = st.tabs(["📊 Datos en Tiempo Real", "📈 Históricos", "🤖 Asistente IA"])
else:
    tab1, tab2, tab3 = st.tabs(["📊 Situación Actual", "📈 Históricos", "🤖 Asistente IA"])

# ============================================================
# TAB 1: DATOS EN TIEMPO REAL / SITUACIÓN ACTUAL
# ============================================================
with tab1:
    if not df.empty:
        row = df.iloc[0]
        
        if seleccion == "Embalse":
            # ============================================
            # SECCIÓN ESPECIAL PARA EMBALSE
            # ============================================
            st.subheader(f"📡 Datos en Tiempo Real: {seleccion}")
            
            # Obtener nivel actual (usando temperatura como nivel)
            nivel_actual = float(row.get('temperatura', 0))
            
            # Evaluar nivel
            estado, color, mensaje, excedente = evaluar_nivel_embalse(nivel_actual)
            
            # Mostrar métricas del embalse
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    "🌊 Nivel actual",
                    f"{nivel_actual:.2f} msnm",
                    delta=f"{excedente:.2f} msnm",
                    delta_color="inverse"
                )
            with col2:
                st.metric(
                    "📏 Nivel de Rebase",
                    f"{NIVEL_REBASE_EMBALSE:.2f} msnm"
                )
            with col3:
                st.metric(
                    "📊 Excédente",
                    f"{excedente:+.2f} msnm",
                    delta_color="inverse"
                )
            
            # Mostrar estado del embalse con indicador visual
            if excedente >= 0:
                st.error(f"🔴 {estado} - {mensaje}")
                st.warning("⚠️ El embalse está por encima del nivel de rebase. ¡Monitorear constantemente!")
            else:
                st.success(f"🟢 {estado} - {mensaje}")
            
            # Información adicional
            st.info(f"📅 Última lectura: {row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Voltaje de la batería
            if 'voltaje_bateria' in row:
                st.metric("🔋 Voltaje", f"{float(row['voltaje_bateria']):.1f} V")
            
            # Botones de acción
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📊 Ver datos detallados", use_container_width=True):
                    st.session_state['ver_detalles'] = True
            with col2:
                if st.button("📥 Descargar datos históricos (CSV)", use_container_width=True):
                    if not df_hist.empty:
                        csv = df_hist.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            "📥 Descargar CSV",
                            csv,
                            f"embalse_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                            "text/csv"
                        )
            
        else:
            # ============================================
            # SECCIÓN PARA OTRAS ESTACIONES
            # ============================================
            st.subheader(f"📡 Situación Actual: {seleccion}")
            
            # Mostrar semáforo
            precipitacion_actual = float(row.get('precipitacion', 0))
            nombre, msg, color, vel = obtener_alerta(precipitacion_actual, seleccion)
            
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
    else:
        st.warning("⚠️ No hay datos disponibles para esta estación")

# ============================================================
# TAB 2: HISTÓRICOS
# ============================================================
with tab2:
    if not df_hist.empty:
        st.subheader("📈 Datos Históricos")
        
        if seleccion == "Embalse":
            # ============================================
            # GRÁFICO ESPECIAL PARA EMBALSE
            # ============================================
            st.markdown("### 🌊 Nivel del Embalse")
            
            # Gráfico del embalse
            fig_embalse = create_embalse_chart(df_hist)
            if fig_embalse:
                st.plotly_chart(fig_embalse, use_container_width=True)
            
            # Mostrar última lectura
            ultima_lectura = df_hist.iloc[0]
            st.info(f"📊 Último nivel registrado: {ultima_lectura['temperatura']:.2f} msnm")
            
            # Tabla de datos recientes
            with st.expander("📋 Ver datos detallados"):
                st.dataframe(df_hist.head(20), use_container_width=True)
            
        else:
            # ============================================
            # GRÁFICOS PARA OTRAS ESTACIONES
            # ============================================
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
            if len(df_hist) > 1:
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
        
        # Exportar datos (común para todos)
        st.markdown("### 📥 Exportar Datos")
        col1, col2 = st.columns(2)
        
        with col1:
            csv = df_hist.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Descargar CSV",
                csv,
                f"datos_{seleccion}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                "text/csv",
                use_container_width=True
            )
        
        with col2:
            try:
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
    st.subheader("🤖 Asistente IA para Estaciones Meteorológicas")
    st.markdown("💬 **Haz preguntas sobre datos históricos, niveles del embalse, precipitaciones y más**")
    
    # Verificar estado del agente
    with st.spinner("🔌 Verificando conexión con el agente IA..."):
        if verificar_agente_ia():
            st.success("✅ Agente IA conectado")
        else:
            st.warning("⚠️ No se pudo conectar al agente IA. Verifica la configuración.")
    
    # Inicializar historial del chat
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Mostrar mensajes anteriores
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Input del usuario
    if prompt := st.chat_input("Escribe tu pregunta sobre las estaciones..."):
        # Agregar mensaje del usuario
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Procesar consulta con el agente IA
        with st.chat_message("assistant"):
            with st.spinner("🤔 Analizando tu pregunta..."):
                resultado = consultar_agente_ia(prompt)
                
                if resultado.get("status") == "ok":
                    respuesta = resultado.get("mensaje", "✅ Consulta procesada exitosamente.")
                    st.markdown(respuesta)
                    st.session_state.messages.append({"role": "assistant", "content": respuesta})
                    
                elif resultado.get("status") == "sin_datos":
                    mensaje = f"ℹ️ {resultado.get('mensaje', 'No se encontraron datos para tu consulta.')}"
                    st.info(mensaje)
                    st.session_state.messages.append({"role": "assistant", "content": mensaje})
                    
                else:
                    error_msg = resultado.get("mensaje", "❌ Error al procesar la consulta.")
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": error_msg
                    })
    
    # Botones de acción
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Limpiar conversación", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    
    with col2:
        # Ejemplos de preguntas
        with st.expander("💡 Ejemplos de preguntas"):
            st.markdown("""
            **🌊 Sobre el embalse:**
            - ¿Cómo está el nivel del embalse?
            - ¿Por qué subió el nivel del embalse?
            - ¿Qué estaciones afectan el embalse?
            
            **🌧️ Sobre estaciones:**
            - ¿Cuánto llovió en El_Pajal en los últimos 7 días?
            - Temperatura máxima en La_Mariana este mes
            - ¿Cuál fue la humedad promedio en Vegas del Quemado?
            
            **📊 Consultas avanzadas:**
            - Comparar lluvias entre El_Pajal y Yerbabuena
            - ¿Qué relación hay entre la lluvia en El_Pajal y el nivel del embalse?
            """)

# ============================================================
# 10. FOOTER Y SIDEBAR
# ============================================================
st.sidebar.markdown("---")
st.sidebar.caption("🚀 Dashboard desarrollado por amb")
st.sidebar.caption(f"📊 Datos actualizados cada 5 minutos")

# Mostrar información del embalse en sidebar
with st.sidebar.expander("🌊 Información del Embalse"):
    st.write(f"**Nivel de Rebase:** {NIVEL_REBASE_EMBALSE} msnm")
    if not df.empty and seleccion == "Embalse":
        nivel_actual = float(df.iloc[0].get('temperatura', 0))
        excedente = nivel_actual - NIVEL_REBASE_EMBALSE
        st.write(f"**Nivel Actual:** {nivel_actual:.2f} msnm")
        if excedente >= 0:
            st.error(f"**Excédente:** +{excedente:.2f} msnm")
        else:
            st.success(f"**Déficit:** {excedente:.2f} msnm")

# Mostrar estaciones disponibles
with st.sidebar.expander("📋 Estaciones Disponibles"):
    for est in estaciones:
        if est in umbrales:
            st.write(f"✅ {est}")
        elif est == "Embalse":
            st.write(f"🌊 {est} (Nivel)")
        else:
            st.write(f"ℹ️ {est} (sin umbrales)")

# Mostrar umbrales
with st.sidebar.expander("📊 Umbrales de Alerta"):
    for estacion, valores in umbrales.items():
        st.write(f"**{estacion}:**")
        st.write(f"  🟡 Amarilla: {valores['amarilla']}mm")
        st.write(f"  🟠 Naranja: {valores['naranja']}mm")
        st.write(f"  🔴 Roja: {valores['roja']}mm")
        st.write("---")

# Estado del agente IA en sidebar
with st.sidebar.expander("🤖 Estado del Agente IA"):
    st.write(f"**URL:** {AGENTE_API_URL}")
    st.write("**Status:** ✅ Activo")
    st.write("**Capacidades:**")
    st.write("- 📊 Consultas SCADA (2026+)")
    st.write("- 📜 Históricos (2004-2025)")
    st.write("- 🌊 Análisis de embalse")
