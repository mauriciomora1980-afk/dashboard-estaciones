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
# 2. CONFIGURACIÓN DEL AGENTE IA
# ============================================================
# URL del agente IA en Cloud Run
AGENTE_API_URL = "https://querybigqueryamb-ia-661926446380.us-central1.run.app"

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
    if estacion == "Monsalve": 
        return "AZUL", "🛠️ En Aprendizaje", "#3399FF", "0s"
    if estacion == "Embalse":
        return "EMBALSE", "🌊 Nivel de Embalse", "#00BFFF", "0s"
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

def evaluar_nivel_embalse(nivel_actual):
    excedente = nivel_actual - NIVEL_REBASE_EMBALSE
    if excedente >= 0:
        return "🔴 EXCEDENTE", "#FF4B4B", f"{excedente:.2f} msnm por encima del nivel de rebase", excedente
    else:
        return "🟢 NORMAL", "#00CC96", f"{abs(excedente):.2f} msnm por debajo del nivel de rebase", excedente

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
# 5. FUNCIONES DE DATOS
# ============================================================
@st.cache_data(ttl=300)
def get_last_reading(estacion):
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
    try:
        if horas < 1:
            horas = 1
        if horas > 720:
            horas = 720
        
        query = f"""
        SELECT * FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones` 
        WHERE id_estacion = '{estacion}' 
        AND SAFE_CAST(timestamp AS TIMESTAMP) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {horas} HOUR)
        ORDER BY SAFE_CAST(timestamp AS TIMESTAMP) DESC 
        LIMIT 5000
        """
        
        df = client.query(query).to_dataframe()
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize('UTC').dt.tz_convert('America/Bogota')
        return df
    except Exception as e:
        st.error(f"❌ Error en datos históricos: {str(e)}")
        return pd.DataFrame()

# ============================================================
# 6. FUNCIÓN PARA CONSULTAR AGENTE IA (VERSIÓN MEJORADA)
# ============================================================
def consultar_agente_ia(pregunta):
    """
    Consulta el agente IA en Cloud Run querybigqueryamb-ia
    """
    try:
        headers = {"Content-Type": "application/json"}
        payload = {"prompt": pregunta}
        
        response = requests.post(AGENTE_API_URL, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            # Verificar si el agente devolvió datos estructurados
            if data.get("status") == "ok":
                # Si el agente ya devolvió un mensaje formateado
                if "mensaje" in data and data["mensaje"]:
                    return {
                        "status": "ok",
                        "mensaje": data["mensaje"],
                        "datos": data.get("datos", []),
                        "estacion": data.get("estacion", ""),
                        "variable": data.get("variable", ""),
                        "contexto": data.get("contexto", {}),
                        "fuente": data.get("fuente", ""),
                        "raw": data
                    }
                else:
                    # Construir respuesta formateada desde los datos estructurados
                    return formatear_respuesta_agente(data)
            else:
                return {
                    "status": "error",
                    "mensaje": data.get("mensaje", "Error al procesar la consulta.")
                }
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

def formatear_respuesta_agente(data):
    """
    Formatea la respuesta del agente en un mensaje legible
    """
    estacion = data.get("estacion", "Estación")
    variable = data.get("variable", "variable")
    datos = data.get("datos", [])
    contexto = data.get("contexto", {})
    fuente = data.get("fuente", "")
    periodo = data.get("periodo", {})
    
    # Mapeo de variables a nombres amigables
    nombres_variables = {
        "precipitacion": "Precipitación",
        "temperatura": "Temperatura",
        "humedad": "Humedad",
        "nivel": "Nivel",
        "caudal": "Caudal"
    }
    nombre_variable = nombres_variables.get(variable, variable.capitalize())
    
    # Construir mensaje
    mensaje = f"🌧️ **{estacion}** - {nombre_variable}\n\n"
    
    # Período
    if periodo:
        fecha_inicio = periodo.get("fecha_inicio", "")
        fecha_fin = periodo.get("fecha_fin", "")
        if fecha_inicio and fecha_fin:
            if fecha_inicio == fecha_fin:
                mensaje += f"📅 **Fecha:** {fecha_inicio}\n\n"
            else:
                mensaje += f"📅 **Período:** {fecha_inicio} al {fecha_fin}\n\n"
    
    # Datos
    if datos:
        # Calcular estadísticas
        valores = [d.get("valor", 0) for d in datos]
        promedio = sum(valores) / len(valores) if valores else 0
        maximo = max(valores) if valores else 0
        minimo = min(valores) if valores else 0
        
        mensaje += f"📊 **Estadísticas:**\n"
        mensaje += f"• Promedio: {promedio:.2f}\n"
        mensaje += f"• Máximo: {maximo:.2f}\n"
        mensaje += f"• Mínimo: {minimo:.2f}\n"
        mensaje += f"• Registros: {len(datos)}\n\n"
        
        # Mostrar datos por fecha (primeros 10)
        mensaje += f"📈 **Datos por fecha:**\n"
        for d in datos[:10]:
            fecha = d.get("fecha", "")
            valor = d.get("valor", 0)
            mensaje += f"• {fecha}: {valor:.2f}\n"
        if len(datos) > 10:
            mensaje += f"\n*... y {len(datos) - 10} registros más*"
    else:
        mensaje += "📊 No se encontraron datos para el período consultado."
    
    # Contexto geográfico
    if contexto:
        mensaje += "\n\n📍 **Contexto geográfico:**\n"
        if contexto.get("cuenca"):
            mensaje += f"• Cuenca: {contexto['cuenca']}\n"
        if contexto.get("afecta"):
            mensaje += f"• Afecta: {contexto['afecta']}\n"
    
    # Fuente
    if fuente:
        mensaje += f"\n📡 **Fuente:** {fuente}"
    
    return {
        "status": "ok",
        "mensaje": mensaje,
        "datos": datos,
        "estacion": estacion,
        "raw": data
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
def create_embalse_chart(df_hist):
    try:
        if df_hist.empty:
            return None
        
        df_ordenado = df_hist.sort_values('timestamp')
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df_ordenado['timestamp'],
            y=df_ordenado['temperatura'],
            mode='lines',
            name='Nivel del embalse',
            line=dict(color='#00BFFF', width=2),
            fill='tozeroy',
            fillcolor='rgba(0, 191, 255, 0.2)'
        ))
        
        fig.add_hline(
            y=NIVEL_REBASE_EMBALSE,
            line_dash="dash",
            line_color="red",
            line_width=2,
            annotation_text=f"Línea de rebase: {NIVEL_REBASE_EMBALSE} msnm",
            annotation_position="top right"
        )
        
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
estaciones = ["La_Mariana", "Yerbabuena", "Vegas_del_Quemado", "El_Pajal", "Monsalve", "Embalse"]
seleccion = st.sidebar.selectbox("Seleccione Estación:", estaciones)

# Opciones de período histórico
periodos = {
    "Últimas 24 horas": 24,
    "Últimos 3 días": 72,
    "Últimos 7 días": 168,
    "Últimos 15 días": 360,
    "Último mes": 720
}

if seleccion == "Embalse":
    st.sidebar.markdown("### 📊 Opciones de Histórico")
    periodo_seleccionado = st.sidebar.selectbox(
        "Seleccione período:",
        list(periodos.keys())
    )
    horas = periodos[periodo_seleccionado]
else:
    horas = st.sidebar.slider("⏱️ Horas históricas:", 1, 168, 24, step=1)

# Cargar datos
with st.spinner("🔄 Cargando datos..."):
    df = get_last_reading(seleccion)
    df_hist = get_historical_data(seleccion, horas)

# Tabs
tab1, tab2, tab3 = st.tabs(["📊 Situación Actual", "📈 Históricos", "🤖 Asistente IA"])

# ============================================================
# TAB 1: SITUACIÓN ACTUAL
# ============================================================
with tab1:
    if not df.empty:
        row = df.iloc[0]
        st.subheader(f"📡 Real-time: {seleccion}")
        
        if seleccion == "Embalse":
            nivel_actual = float(row.get('temperatura', 0))
            estado, color, mensaje, excedente = evaluar_nivel_embalse(nivel_actual)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🌊 Nivel actual", f"{nivel_actual:.2f} msnm", delta=f"{excedente:.2f} msnm")
            with col2:
                st.metric("📏 Nivel de Rebase", f"{NIVEL_REBASE_EMBALSE:.2f} msnm")
            with col3:
                st.metric("📊 Excédente", f"{excedente:+.2f} msnm")
            
            if excedente >= 0:
                st.error(f"🔴 {estado} - {mensaje}")
            else:
                st.success(f"🟢 {estado} - {mensaje}")
        else:
            nombre, msg, color, vel = obtener_alerta(float(row.get('precipitacion', 0)), seleccion)
            st.markdown(f'''
            <div style="background-color:{color}; padding:20px; border-radius:15px; text-align:center; color:black; animation: blink {vel} infinite; border: 2px solid #333;">
                <h2>🚦 {nombre}</h2>
                <b>{msg}</b>
            </div>
            <style>
            @keyframes blink {{
                0%{{opacity:1}} 
                50%{{opacity:0.3}} 
                100%{{opacity:1}}
            }}
            </style>
            ''', unsafe_allow_html=True)
            st.write("")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("🌡️ Temp", f"{float(row['temperatura']):.1f} °C")
            c2.metric("🌧️ Precip", f"{float(row['precipitacion']):.1f} mm")
            c3.metric("💧 Humedad", f"{float(row['humedad']):.1f} %")
            c4.metric("🔋 Voltaje", f"{float(row['voltaje_bateria']):.1f} V")
        
        st.info(f"📅 Última lectura: {row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        st.warning("⚠️ Sin datos.")

# ============================================================
# TAB 2: HISTÓRICOS
# ============================================================
with tab2:
    if not df_hist.empty:
        st.subheader("📈 Series de Tiempo")
        
        if seleccion == "Embalse":
            fig_embalse = create_embalse_chart(df_hist)
            if fig_embalse:
                st.plotly_chart(fig_embalse, use_container_width=True)
        else:
            st.markdown("### 🌡️ Temperatura")
            fig_temp = px.line(
                df_hist.sort_values('timestamp'), 
                x='timestamp', 
                y='temperatura',
                title=f'Temperatura - {seleccion}',
                labels={'temperatura': '°C', 'timestamp': 'Fecha/Hora'}
            )
            fig_temp.update_layout(height=300, template='plotly_white')
            st.plotly_chart(fig_temp, use_container_width=True)
            
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
            fig_precip.update_layout(height=300, template='plotly_white')
            st.plotly_chart(fig_precip, use_container_width=True)
        
        # Exportar datos
        st.markdown("### 📥 Exportar Datos")
        csv = df_hist.to_csv(index=False).encode('utf-8')
        col1, col2 = st.columns(2)
        with col1:
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
        st.info("ℹ️ No hay datos históricos disponibles")

# ============================================================
# TAB 3: ASISTENTE IA - EXACTAMENTE COMO EN EL DASHBOARD ANTIGUO
# ============================================================
with tab3:
    st.subheader("🤖 Asistente IA - Centro de Monitoreo")
    st.markdown("Pregunta sobre niveles, caudales, lluvias y estado de las estaciones.")
    
    # Verificar conexión con el agente
    with st.spinner("🔌 Verificando conexión..."):
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
                    
                    # Si hay datos crudos, mostrar opción para verlos (debug)
                    if "raw" in resultado and st.checkbox("🔍 Ver datos completos", key="show_raw"):
                        st.json(resultado["raw"])
                        
                elif resultado.get("status") == "sin_datos":
                    mensaje = f"ℹ️ {resultado.get('mensaje', 'No se encontraron datos.')}"
                    st.info(mensaje)
                    st.session_state.messages.append({"role": "assistant", "content": mensaje})
                else:
                    error_msg = resultado.get("mensaje", "❌ Error al procesar la consulta.")
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
    
    # Botones
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Limpiar conversación", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    with col2:
        with st.expander("💡 Ejemplos de preguntas"):
            st.markdown("""
            **🌊 Sobre el embalse:**
            - ¿Cómo está el nivel del embalse?
            - ¿Por qué subió el nivel del embalse?
            
            **🌧️ Sobre estaciones:**
            - ¿Cuánto llovió en El_Pajal ayer?
            - Temperatura máxima en La_Mariana este mes
            - ¿Cuál fue la humedad en Vegas del Quemado?
            
            **📊 Consultas avanzadas:**
            - Comparar lluvias entre El_Pajal y Yerbabuena
            - ¿Qué relación hay entre la lluvia y el nivel del embalse?
            """)

# ============================================================
# 9. FOOTER Y SIDEBAR
# ============================================================
st.sidebar.markdown("---")
st.sidebar.caption("🚀 Dashboard desarrollado por amb")
st.sidebar.caption(f"📊 Datos actualizados cada 5 minutos")

# Información del embalse
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

# Estado del agente IA
with st.sidebar.expander("🤖 Estado del Agente IA"):
    st.write(f"**URL:** {AGENTE_API_URL}")
    st.write("**Status:** ✅ Activo")
    st.write("**Capacidades:**")
    st.write("- 📊 Consultas SCADA (2026+)")
    st.write("- 📜 Históricos (2004-2025)")
    st.write("- 🌊 Análisis de embalse")
