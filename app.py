import streamlit as st
import pandas as pd
import numpy as np
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
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from scipy.interpolate import PchipInterpolator

# ============================================================
# 0. CONFIGURACIÓN DE PÁGINA Y TEMA CORPORATIVO MIMAT-C26
# ============================================================
st.set_page_config(
    page_title="MIMAT-C26 | Centro de Monitoreo AMB", 
    page_icon="💧", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS Avanzados (Dark Navy Glassmorphism & Executive UI)
st.markdown("""
<style>
    /* Tipografía y fondo principal */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Encabezado principal estilo Hero Banner */
    .mimat-header {
        background: linear-gradient(135deg, #0A192F 0%, #172A45 50%, #005073 100%);
        padding: 24px;
        border-radius: 16px;
        color: white;
        margin-bottom: 25px;
        box-shadow: 0 10px 30px rgba(0, 80, 115, 0.25);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .mimat-title {
        font-size: 28px;
        font-weight: 800;
        letter-spacing: -0.5px;
        margin: 0;
        color: #64FFDA;
    }
    .mimat-subtitle {
        font-size: 14px;
        color: #8892B0;
        margin-top: 6px;
    }
    
    /* Tarjetas KPI con efecto Glassmorphism */
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border-radius: 14px;
        padding: 18px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0, 120, 215, 0.15);
    }
    
    /* Semáforo de alerta Súper Niño */
    .alert-box {
        padding: 16px 20px;
        border-radius: 12px;
        font-weight: 600;
        margin-bottom: 15px;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .alert-green { background: rgba(0, 204, 150, 0.15); color: #00CC96; border: 1px solid #00CC96; }
    .alert-yellow { background: rgba(255, 187, 0, 0.15); color: #FFBB00; border: 1px solid #FFBB00; }
    .alert-orange { background: rgba(255, 128, 0, 0.15); color: #FF8000; border: 1px solid #FF8000; }
    .alert-red { background: rgba(255, 75, 75, 0.15); color: #FF4B4B; border: 1px solid #FF4B4B; }
    
    /* Badges de estado */
    .badge-status {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
    }
</style>
""", unsafe_allow_html=True)

colombia_tz = timezone('America/Bogota')
utc_tz = timezone('UTC')

# ============================================================
# 1. ENCABEZADO INSTITUCIONAL MIMAT-C26
# ============================================================
st.markdown(f"""
<div class="mimat-header">
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
        <div>
            <div class="mimat-title">🏛️ MIMAT-C26 | Centro de Monitoreo Inteligente</div>
            <div class="mimat-subtitle">Monitoreo Inteligente de Meteorología, Análisis de Telemetría y Cuencas • AMB S.A. E.S.P.</div>
        </div>
        <div style="text-align: right;">
            <span class="badge-status" style="background: rgba(100, 255, 218, 0.2); color: #64FFDA; border: 1px solid #64FFDA;">● TELEMETRÍA 24/7 ACTIVA</span>
            <div style="font-size: 12px; color: #8892B0; margin-top: 5px;">🕐 {datetime.now(colombia_tz).strftime('%Y-%m-%d %H:%M:%S')} (Hora Colombia)</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Logo en barra lateral
logo_path = os.path.join(os.path.dirname(__file__), "amb_4_punto_cero.jpg")
try:
    st.sidebar.image(logo_path, use_column_width=True)
except:
    st.sidebar.markdown("### 💧 AMB S.A. E.S.P.")

st.sidebar.markdown("### 🧭 Panel de Control MIMAT-C26")
st.sidebar.caption("Proyecto Estratégico de Producción y Calidad")

# ============================================================
# 2. MODELO MATEMÁTICO PCHIP — BATIMETRÍA 2026 (TABLA 9)
# ============================================================
COTAS_REF = np.array([817.94, 830.00, 836.50, 841.00, 850.00, 860.00, 870.00, 883.00, 885.80])
VOLUMENES_REF = np.array([0.000, 0.520, 1.400, 1.980, 3.850, 6.420, 9.650, 14.090, 15.380]) # hm³
AREAS_REF = np.array([0.00, 8.50, 14.20, 18.60, 24.50, 30.80, 37.20, 44.60, 46.20]) # ha

interpolador_vol = PchipInterpolator(COTAS_REF, VOLUMENES_REF)
interpolador_area = PchipInterpolator(COTAS_REF, AREAS_REF)

NIVEL_MINIMO_TECNICO = 841.00
NIVEL_REBOSE_EMBALSE = 885.75
VOLUMEN_UTIL_MAX_HM3 = 12.11
VOLUMEN_MUERTO_HM3 = 1.40

def calcular_hidraulica_embalse(cota: float, q_ptap_ls: float = 1450.0):
    cota_val = max(817.94, min(float(cota), 886.00))
    vol_total_hm3 = float(interpolador_vol(cota_val))
    vol_total_m3 = vol_total_hm3 * 1_000_000.0
    area_ha = float(interpolador_area(cota_val))
    area_m2 = area_ha * 10_000.0
    
    m3_por_cm = area_m2 * 0.01
    
    # Volumen útil sobre cota 841.00 msnm
    vol_min_tecnico_m3 = 1.980 * 1_000_000.0
    vol_util_m3 = max(0.0, vol_total_m3 - vol_min_tecnico_m3)
    vol_util_hm3 = vol_util_m3 / 1_000_000.0
    porcentaje_util = min(100.0, (vol_util_hm3 / VOLUMEN_UTIL_MAX_HM3) * 100.0)
    
    # Autonomía estimada (días de agua sin aportes)
    q_ptap_m3_s = q_ptap_ls / 1000.0
    consumo_diario_m3 = q_ptap_m3_s * 86400.0
    dias_autonomia = vol_util_m3 / consumo_diario_m3 if consumo_diario_m3 > 0 else 0
    
    excedente_rebose = cota_val - NIVEL_REBOSE_EMBALSE
    
    return {
        "cota": cota_val,
        "volumen_total_hm3": vol_total_hm3,
        "volumen_util_hm3": vol_util_hm3,
        "porcentaje_util": porcentaje_util,
        "area_ha": area_ha,
        "m3_por_cm": m3_por_cm,
        "dias_autonomia": dias_autonomia,
        "excedente_rebose": excedente_rebose
    }

# ============================================================
# 3. CONEXIÓN A BIGQUERY Y AGENTE IA
# ============================================================
AGENTE_API_URL = "https://querybigqueryamb-ia-661926446380.us-central1.run.app"

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

@st.cache_data(ttl=60)
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
        return pd.DataFrame()

@st.cache_data(ttl=60)
def get_historical_data_range(estacion, fecha_inicio, fecha_fin):
    try:
        if isinstance(fecha_inicio, datetime):
            f_inicio_dt = fecha_inicio if fecha_inicio.tzinfo else colombia_tz.localize(fecha_inicio)
            f_inicio_str = f_inicio_dt.astimezone(utc_tz).strftime('%Y-%m-%d %H:%M:%S')
        else:
            f_inicio_dt = colombia_tz.localize(datetime.combine(fecha_inicio, datetime.min.time()))
            f_inicio_str = f_inicio_dt.astimezone(utc_tz).strftime('%Y-%m-%d %H:%M:%S')
        
        if isinstance(fecha_fin, datetime):
            f_fin_dt = fecha_fin if fecha_fin.tzinfo else colombia_tz.localize(fecha_fin)
            f_fin_str = f_fin_dt.astimezone(utc_tz).strftime('%Y-%m-%d %H:%M:%S')
        else:
            f_fin_dt = colombia_tz.localize(datetime.combine(fecha_fin, datetime.max.time()))
            f_fin_str = f_fin_dt.astimezone(utc_tz).strftime('%Y-%m-%d %H:%M:%S')
        
        query = f"""
        SELECT * FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones` 
        WHERE id_estacion = '{estacion}' 
        AND SAFE_CAST(timestamp AS TIMESTAMP) >= TIMESTAMP('{f_inicio_str}')
        AND SAFE_CAST(timestamp AS TIMESTAMP) <= TIMESTAMP('{f_fin_str}')
        ORDER BY SAFE_CAST(timestamp AS TIMESTAMP) DESC 
        LIMIT 50000
        """
        df = client.query(query).to_dataframe()
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize('UTC').dt.tz_convert('America/Bogota')
        return df
    except Exception as e:
        return pd.DataFrame()

# ============================================================
# 4. BARRA LATERAL Y CONTROLES
# ============================================================
estaciones = ["Embalse", "La_Mariana", "Yerbabuena", "Vegas_del_Quemado", "El_Pajal", "Monsalve"]
seleccion = st.sidebar.selectbox("Seleccione Estación / Módulo:", estaciones, index=0)

horas = st.sidebar.slider("⏱️ Ventana Histórica (Horas):", 1, 168, 24, step=1)

fecha_fin = datetime.now(colombia_tz)
fecha_inicio = fecha_fin - timedelta(hours=horas)

with st.spinner("🔄 Consultando telemetría en tiempo real..."):
    df_actual = get_last_reading(seleccion)
    df_hist = get_historical_data_range(seleccion, fecha_inicio, fecha_fin)

# ============================================================
# 5. PESTAÑAS PRINCIPALES DEL SISTEMA
# ============================================================
tab_monitoreo, tab_embalse_2026, tab_historicos, tab_ia = st.tabs([
    "📊 Situación Actual", 
    "🌊 Gestión Embalse & Sequía 2026", 
    "📈 Series de Tiempo", 
    "🤖 Asistente IA MIMAT-C"
])

# ------------------------------------------------------------
# TAB 1: SITUACIÓN ACTUAL
# ------------------------------------------------------------
with tab_monitoreo:
    if not df_actual.empty:
        row = df_actual.iloc[0]
        st.subheader(f"📡 Telemetría en Vivo: {seleccion.replace('_', ' ')}")
        
        if seleccion == "Embalse":
            cota_actual = float(row.get('temperatura', 885.80)) if pd.notna(row.get('temperatura')) else 885.80
            hidro = calcular_hidraulica_embalse(cota_actual)
            
            # Semáforo de estado
            if hidro["excedente_rebose"] >= 0:
                st.markdown(f"""
                <div class="alert-box alert-orange">
                    <span style="font-size: 24px;">🌊</span>
                    <div>
                        <strong>ESTADO: REBOSE ACTIVO (+{hidro['excedente_rebose']:.2f} msnm)</strong><br>
                        El embalse supera la cota de vertimiento (885.75 msnm). Descarga por vertedero Morning Glory.
                    </div>
                </div>
                """, unsafe_allow_html=True)
            elif hidro["dias_autonomia"] > 60:
                st.markdown(f"""
                <div class="alert-box alert-green">
                    <span style="font-size: 24px;">🟢</span>
                    <div>
                        <strong>ESTADO: SEGURIDAD HÍDRICA NORMAL ({hidro['dias_autonomia']:.0f} Días de Reserva)</strong><br>
                        Nivel en {cota_actual:.2f} msnm. Capacidad útil al {hidro['porcentaje_util']:.1f}%.
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="alert-box alert-red">
                    <span style="font-size: 24px;">🚨</span>
                    <div>
                        <strong>ALERTA DE SEQUÍA SÚPER NIÑO ({hidro['dias_autonomia']:.0f} Días de Reserva)</strong><br>
                        Nivel cercano a cota de contingencia técnica. Regular extracción hacia PTAP Bosconia.
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("🌊 Cota Actual", f"{cota_actual:.2f} msnm")
            c2.metric("💧 Volumen Útil", f"{hidro['volumen_util_hm3']:.2f} hm³", delta=f"{hidro['porcentaje_util']:.1f}% útil")
            c3.metric("⏳ Autonomía Bucaramanga", f"{hidro['dias_autonomia']:.0f} Días")
            c4.metric("📐 Área Espejo", f"{hidro['area_ha']:.1f} ha")
            
        else:
            p_val = float(row.get('precipitacion', 0)) if pd.notna(row.get('precipitacion')) else 0.0
            t_val = float(row.get('temperatura', 0)) if pd.notna(row.get('temperatura')) else 0.0
            h_val = float(row.get('humedad', 0)) if pd.notna(row.get('humedad')) else 0.0
            v_val = float(row.get('velocidad_viento', 0)) if pd.notna(row.get('velocidad_viento')) else 0.0
            d_val = float(row.get('direccion_viento', 0)) if pd.notna(row.get('direccion_viento')) else 0.0
            b_val = float(row.get('voltaje_bateria', 0)) if pd.notna(row.get('voltaje_bateria')) else 0.0
            
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            c1.metric("🌡️ Temp", f"{t_val:.1f} °C")
            c2.metric("🌧️ Precipitación", f"{p_val:.1f} mm")
            c3.metric("💧 Humedad", f"{h_val:.1f} %")
            c4.metric("💨 Viento", f"{v_val:.1f} km/h")
            c5.metric("🧭 Dirección", f"{d_val:.0f}°")
            c6.metric("🔋 Batería", f"{b_val:.1f} V")
            
        st.caption(f"🕐 Última lectura recibida: {row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        st.warning("⚠️ Sin datos recientes para esta estación.")

# ------------------------------------------------------------
# TAB 2: GESTIÓN EMBALSE & CONTINGENCIA SEQUÍA 2026
# ------------------------------------------------------------
with tab_embalse_2026:
    st.subheader("🌊 Módulo Especializado: Embalse Tona (Batimetría Multihaz 2026)")
    st.caption("Resolución centímetro a centímetro según Informe Técnico OPS 071 de 2026 - Batimetría S.A.S")
    
    c_embalse = float(df_actual.iloc[0].get('temperatura', 885.80)) if not df_actual.empty else 885.80
    
    col_sim1, col_sim2 = st.columns([1, 2])
    
    with col_sim1:
        st.markdown("### 🎛️ Simulador de Extracción PTAP")
        q_sim = st.slider("Extracción hacia Plantas (L/s):", 800, 2500, 1450, step=50)
        cota_eval = st.number_input("Cota de Evaluación (msnm):", 818.0, 886.0, float(c_embalse), step=0.1)
        
        datos_eval = calcular_hidraulica_embalse(cota_eval, q_sim)
        
        st.markdown("---")
        st.markdown(f"""
        **📋 Resultados Hidráulicos:**
        * **Volumen Útil:** `{datos_eval['volumen_util_hm3']:.3f} hm³`
        * **Volumen Muerto (Sedimentos):** `1.400 hm³`
        * **Volumen Total:** `{datos_eval['volumen_total_hm3']:.3f} hm³`
        * **Volumen por cada Centímetro:** `{datos_eval['m3_por_cm']:.1f} m³/cm`
        * **Autonomía estimada:** **`{datos_eval['dias_autonomia']:.0f} Días de Agua`**
        """)
    
    with col_sim2:
        # Gráfica de Curva Cota - Volumen 2026
        cotas_curva = np.linspace(818, 885.8, 100)
        vols_curva = [float(interpolador_vol(c)) for c in cotas_curva]
        
        fig_curva = go.Figure()
        fig_curva.add_trace(go.Scatter(
            x=vols_curva, 
            y=cotas_curva, 
            mode='lines', 
            name='Curva Batimetría 2026',
            line=dict(color='#00CC96', width=3)
        ))
        
        # Punto actual
        fig_curva.add_trace(go.Scatter(
            x=[datos_eval['volumen_total_hm3']], 
            y=[cota_eval], 
            mode='markers', 
            name=f'Nivel Evaluado ({cota_eval:.2f} msnm)',
            marker=dict(size=14, color='#FF4B4B', symbol='diamond')
        ))
        
        fig_curva.add_hline(y=NIVEL_MINIMO_TECNICO, line_dash="dash", line_color="orange", annotation_text="Mínimo Técnico: 841 msnm")
        fig_curva.add_hline(y=NIVEL_REBOSE_EMBALSE, line_dash="dash", line_color="red", annotation_text="Rebose Morning Glory: 885.75 msnm")
        
        fig_curva.update_layout(
            title="Curva Cota vs. Volumen 2026 (Embalse Tona)",
            xaxis_title="Volumen Acumulado (hm³)",
            yaxis_title="Cota (msnm)",
            height=420,
            template='plotly_white'
        )
        st.plotly_chart(fig_curva, use_container_width=True)

# ------------------------------------------------------------
# TAB 3: SERIES DE TIEMPO Y ROSA DE LOS VIENTOS
# ------------------------------------------------------------
with tab_historicos:
    st.subheader(f"📈 Series de Tiempo — {seleccion.replace('_', ' ')}")
    
    if not df_hist.empty:
        if seleccion == "Embalse":
            fig_emb = px.line(
                df_hist.sort_values('timestamp'), 
                x='timestamp', 
                y='temperatura',
                title='Evolución de Cota del Embalse (msnm)',
                labels={'temperatura': 'msnm', 'timestamp': 'Fecha/Hora'}
            )
            fig_emb.add_hline(y=NIVEL_REBOSE_EMBALSE, line_dash="dash", line_color="red", annotation_text="Cota Rebose")
            fig_emb.update_layout(height=380, template='plotly_white')
            st.plotly_chart(fig_emb, use_container_width=True)
        else:
            # Gráficos estándar
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                fig_p = px.bar(df_hist.sort_values('timestamp'), x='timestamp', y='precipitacion', title='Precipitación (mm)')
                fig_p.update_layout(height=280, template='plotly_white')
                st.plotly_chart(fig_p, use_container_width=True)
            with col_g2:
                fig_t = px.line(df_hist.sort_values('timestamp'), x='timestamp', y='temperatura', title='Temperatura (°C)')
                fig_t.update_layout(height=280, template='plotly_white')
                st.plotly_chart(fig_t, use_container_width=True)
            
            # Rosa de los Vientos
            if 'direccion_viento' in df_hist.columns and 'velocidad_viento' in df_hist.columns:
                st.markdown("### 🧭 Rosa de los Vientos")
                df_v = df_hist.copy()
                df_v['direccion_viento'] = pd.to_numeric(df_v['direccion_viento'], errors='coerce')
                df_v['velocidad_viento'] = pd.to_numeric(df_v['velocidad_viento'], errors='coerce')
                df_v = df_v.dropna(subset=['direccion_viento', 'velocidad_viento'])
                df_v = df_v[(df_v['direccion_viento'] > 0) | (df_v['velocidad_viento'] > 0)]
                
                if not df_v.empty:
                    fig_rosa = px.bar_polar(
                        df_v, 
                        r="velocidad_viento", 
                        theta="direccion_viento", 
                        color="velocidad_viento",
                        color_continuous_scale='Viridis',
                        title=f"Rosa de Vientos — {seleccion}"
                    )
                    fig_rosa.update_layout(height=400, template='plotly_white')
                    st.plotly_chart(fig_rosa, use_container_width=True)
                else:
                    st.info("ℹ️ Sin datos de viento en este rango.")
    else:
        st.info("ℹ️ Sin datos históricos disponibles.")

# ------------------------------------------------------------
# TAB 4: ASISTENTE IA MIMAT-C
# ------------------------------------------------------------
with tab_ia:
    st.subheader("🤖 Asistente Inteligente MIMAT-C26")
    st.caption("Consulta niveles, volúmenes de batimetría 2026, lluvias y cuencas en lenguaje natural.")
    
    # Ping status
    try:
        r_ping = requests.post(AGENTE_API_URL, json={"prompt": "ping"}, timeout=4)
        ia_online = r_ping.status_code == 200
    except:
        ia_online = False
        
    if ia_online:
        st.success("✅ Agente IA MIMAT-C conectado y operativo en Google Cloud Run")
    else:
        st.warning("⚠️ Microservicio de IA desconectado.")
        
    if "messages" not in st.session_state:
        st.session_state.messages = []
        
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            
    p_user = st.chat_input("Pregunta al Asistente MIMAT-C (Ej: ¿Cuál es el volumen útil del embalse?)...")
    if p_user:
        st.session_state.messages.append({"role": "user", "content": p_user})
        with st.chat_message("user"):
            st.markdown(p_user)
            
        with st.chat_message("assistant"):
            with st.spinner("🤔 Consultando BigQuery y analizando..."):
                try:
                    res = requests.post(AGENTE_API_URL, json={"prompt": p_user}, timeout=20).json()
                    ans = res.get("mensaje", "No se obtuvo respuesta.")
                    st.markdown(ans)
                    st.session_state.messages.append({"role": "assistant", "content": ans})
                except Exception as ex:
                    err_msg = f"❌ Error al consultar IA: {ex}"
                    st.error(err_msg)
                    st.session_state.messages.append({"role": "assistant", "content": err_msg})
        st.rerun()

# ============================================================
# 6. SIDEBAR FOOTER
# ============================================================
st.sidebar.markdown("---")
st.sidebar.markdown("**Líder Técnico:** Ing. Mauricio Mora")
st.sidebar.caption("Proyecto MIMAT-C26 • AMB S.A. E.S.P.")
