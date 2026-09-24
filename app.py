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
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows
from PIL import Image

# ============================================================
# 0. CONFIGURACIÓN DE PÁGINA Y ESTILOS MIMAT-C26 (amb)
# ============================================================
st.set_page_config(
    page_title="MIMAT-C26 | Centro de Monitoreo - amb", 
    page_icon="💧", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS Avanzados (amb minúscula + Flecha lateral destacada + UI Ejecutiva)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    [data-testid="stSidebarCollapsedControl"] {
        display: block !important;
        background: linear-gradient(135deg, #005073 0%, #0A192F 100%) !important;
        color: #64FFDA !important;
        border-radius: 10px !important;
        padding: 8px 12px !important;
        border: 2px solid #64FFDA !important;
        box-shadow: 0 4px 15px rgba(0, 80, 115, 0.4) !important;
        transform: scale(1.15) !important;
    }
    [data-testid="stSidebarCollapsedControl"]:hover {
        transform: scale(1.25) !important;
        box-shadow: 0 6px 20px rgba(100, 255, 218, 0.6) !important;
    }
    
    .mimat-header {
        background: linear-gradient(135deg, #0A192F 0%, #172A45 50%, #005073 100%);
        padding: 20px 24px;
        border-radius: 16px;
        color: white;
        margin-bottom: 15px;
        box-shadow: 0 10px 30px rgba(0, 80, 115, 0.25);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .mimat-title { font-size: 24px; font-weight: 800; color: #64FFDA; margin: 0; }
    .mimat-subtitle { font-size: 13px; color: #8892B0; margin-top: 4px; }
    
    .alert-box {
        padding: 14px 18px;
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
    
    .badge-status {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
    }
</style>
""", unsafe_allow_html=True)

colombia_tz = timezone('America/Bogota')
utc_tz = timezone('UTC')

# ============================================================
# 1. ENCABEZADO Y LOGO (amb minúscula)
# ============================================================
st.markdown(f"""
<div class="mimat-header">
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
        <div>
            <div class="mimat-title">🏛️ MIMAT-C26 | Centro de Monitoreo - amb</div>
            <div class="mimat-subtitle">Monitoreo Inteligente de Meteorología, Análisis de Telemetría y Cuencas • amb s.a. e.s.p.</div>
        </div>
        <div style="text-align: right;">
            <span class="badge-status" style="background: rgba(100, 255, 218, 0.2); color: #64FFDA; border: 1px solid #64FFDA;">● TELEMETRÍA 24/7 ACTIVA</span>
            <div style="font-size: 12px; color: #8892B0; margin-top: 4px;">🕐 {datetime.now(colombia_tz).strftime('%Y-%m-%d %H:%M:%S')} (Hora Colombia)</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Carga de Logo amb en barra lateral
def render_logo_sidebar():
    posibles_rutas = [
        "amb_4_punto_cero.jpg",
        os.path.join(os.path.dirname(__file__), "amb_4_punto_cero.jpg"),
        os.path.join(os.getcwd(), "amb_4_punto_cero.jpg"),
        "amb.jpg"
    ]
    for ruta in posibles_rutas:
        if os.path.exists(ruta):
            try:
                img = Image.open(ruta)
                st.sidebar.image(img, use_container_width=True)
                return
            except:
                pass
    st.sidebar.markdown("""
    <div style="background: linear-gradient(135deg, #005073, #0A192F); padding: 16px; border-radius: 12px; text-align: center; margin-bottom: 15px; border: 1px solid #64FFDA;">
        <h1 style="color: #64FFDA; margin: 0; font-size: 32px; font-weight: 900; letter-spacing: -1px;">amb</h1>
        <div style="color: #E6F1FF; font-size: 11px; text-transform: lowercase; margin-top: 2px;">acueducto metropolitano de bucaramanga</div>
    </div>
    """, unsafe_allow_html=True)

render_logo_sidebar()

# ============================================================
# 2. METADATOS Y CONSTANTES
# ============================================================
AUTOR = "Ing. Mauricio Mora"
VERSION = "MIMAT-C26 v2.6"
SISTEMA = "Sistema Automatizado de Monitoreo MIMAT-C26 - amb"
AGENTE_API_URL = "https://querybigqueryamb-ia-661926446380.us-central1.run.app"

umbrales = {
    "El_Pajal": {"amarilla": 12.3, "naranja": 15.1, "roja": 20.4},
    "Yerbabuena": {"amarilla": 10.9, "naranja": 20.0, "roja": 40.8},
    "La_Mariana": {"amarilla": 11.7, "naranja": 18.0, "roja": 35.0},
    "Vegas_del_Quemado": {"amarilla": 27.2, "naranja": 36.8, "roja": 55.8}
}

# ============================================================
# 3. MODELO MATEMÁTICO — BATIMETRÍA 2026 (NUMPY NATIVO)
# ============================================================
COTAS_REF = np.array([817.94, 830.00, 836.50, 841.00, 850.00, 860.00, 870.00, 883.00, 885.80])
VOLUMENES_REF = np.array([0.000, 0.520, 1.400, 1.980, 3.850, 6.420, 9.650, 14.090, 15.380]) # hm³
AREAS_REF = np.array([0.00, 8.50, 14.20, 18.60, 24.50, 30.80, 37.20, 44.60, 46.20]) # ha

NIVEL_MINIMO_TECNICO = 841.00
NIVEL_REBOSE_EMBALSE = 885.75
OFFSET_RADAR_EMBALSE = 0.05 # Desfase del sensor radar OTT (5 cm)
VOLUMEN_UTIL_MAX_HM3 = 12.11
VOLUMEN_MUERTO_HM3 = 1.40

# Calibración Oficial Rebosadero Morning Glory (Plano As-Built CONALVÍAS / INAR & Aforos 2017)
COTAS_MG_REF = np.array([0.00, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10, 0.11, 0.12, 0.13, 0.14, 0.16, 0.18, 0.19, 0.20, 0.22, 1.00, 2.02, 2.75, 3.40, 4.05, 4.70, 4.75, 4.85, 4.95, 5.20, 5.50, 5.80])
CAUDAL_MG_REF = np.array([0.00, 0.78, 1.82, 2.86, 3.90, 4.94, 5.98, 7.02, 8.06, 9.10, 10.14, 11.18, 12.23, 13.27, 15.37, 17.47, 18.52, 19.58, 21.69, 114.60, 347.90, 556.80, 827.20, 1041.70, 1284.00, 1305.70, 1347.90, 1374.60, 1407.70, 1425.10, 1452.00]) # m³/s

def interpolar_volumen(c):
    return float(np.interp(c, COTAS_REF, VOLUMENES_REF))

def interpolar_area(c):
    return float(np.interp(c, COTAS_REF, AREAS_REF))

def calcular_caudal_morning_glory(cota_real: float):
    h_sobre_vertedero = max(0.0, cota_real - NIVEL_REBOSE_EMBALSE)
    if h_sobre_vertedero <= 0.0:
        return 0.0, 0.0
    q_m3_s = float(np.interp(h_sobre_vertedero, COTAS_MG_REF, CAUDAL_MG_REF))
    q_ls = q_m3_s * 1000.0
    return q_m3_s, q_ls

def calcular_balance_dinamico(df_hist):
    if df_hist.empty or len(df_hist) < 2:
        return None
    df_s = df_hist.sort_values('timestamp').dropna(subset=['temperatura'])
    if len(df_s) < 2:
        return None
    
    t_ini = df_s.iloc[0]['timestamp']
    t_fin = df_s.iloc[-1]['timestamp']
    delta_horas = (t_fin - t_ini).total_seconds() / 3600.0
    if delta_horas < 0.2:
        return None
        
    c_ini_raw = float(df_s.iloc[0]['temperatura'])
    c_fin_raw = float(df_s.iloc[-1]['temperatura'])
    c_ini = c_ini_raw - OFFSET_RADAR_EMBALSE
    c_fin = c_fin_raw - OFFSET_RADAR_EMBALSE
    
    delta_cota_m = c_fin - c_ini
    delta_cota_cm = delta_cota_m * 100.0
    
    vel_cm_hora = delta_cota_cm / delta_horas
    vel_cm_dia = vel_cm_hora * 24.0
    
    v_ini_m3 = interpolar_volumen(c_ini) * 1_000_000.0
    v_fin_m3 = interpolar_volumen(c_fin) * 1_000_000.0
    delta_v_m3 = v_fin_m3 - v_ini_m3
    
    delta_s = (t_fin - t_ini).total_seconds()
    q_neto_m3_s = - (delta_v_m3 / delta_s) # Positivo si vacía, negativo si llena
    q_neto_ls = q_neto_m3_s * 1000.0
    vaciado_diario_m3 = q_neto_m3_s * 86400.0
    
    vol_util_m3 = max(0.0, (interpolar_volumen(c_fin) - 1.980) * 1_000_000.0)
    if q_neto_m3_s > 0:
        dias_autonomia = vol_util_m3 / (q_neto_m3_s * 86400.0)
    else:
        dias_autonomia = None
        
    return {
        "horas": delta_horas,
        "cota_ini": c_ini,
        "cota_fin": c_fin,
        "delta_cota_cm": delta_cota_cm,
        "vel_cm_hora": vel_cm_hora,
        "vel_cm_dia": vel_cm_dia,
        "delta_v_m3": delta_v_m3,
        "q_neto_ls": q_neto_ls,
        "vaciado_diario_m3": vaciado_diario_m3,
        "dias_autonomia": dias_autonomia
    }

def calcular_hidraulica_embalse(cota_calibrada: float, q_ptap_ls: float = 0.0):
    cota_val = max(818.0, min(float(cota_calibrada), 886.00))
    vol_total_hm3 = interpolar_volumen(cota_val)
    vol_total_m3 = vol_total_hm3 * 1_000_000.0
    area_ha = interpolar_area(cota_val)
    area_m2 = area_ha * 10_000.0
    
    m3_por_cm = area_m2 * 0.01
    
    vol_min_tecnico_m3 = 1.980 * 1_000_000.0
    vol_util_m3 = max(0.0, vol_total_m3 - vol_min_tecnico_m3)
    vol_util_hm3 = vol_util_m3 / 1_000_000.0
    porcentaje_util = min(100.0, (vol_util_hm3 / VOLUMEN_UTIL_MAX_HM3) * 100.0)
    
    # Manejo de extracción cero / sin caudalímetro activo
    if q_ptap_ls > 0:
        q_ptap_m3_s = q_ptap_ls / 1000.0
        consumo_diario_m3 = q_ptap_m3_s * 86400.0
        dias_autonomia = vol_util_m3 / consumo_diario_m3
        autonomia_texto = f"{dias_autonomia:.0f} Días"
    else:
        dias_autonomia = None
        autonomia_texto = "∞ Indefinida (Sin Extracción)"
        
    excedente_rebose = cota_val - NIVEL_REBOSE_EMBALSE
    q_rebose_m3_s, q_rebose_ls = calcular_caudal_morning_glory(cota_val)
    
    return {
        "cota": cota_val,
        "volumen_total_hm3": vol_total_hm3,
        "volumen_util_hm3": vol_util_hm3,
        "porcentaje_util": porcentaje_util,
        "area_ha": area_ha,
        "m3_por_cm": m3_por_cm,
        "dias_autonomia": dias_autonomia,
        "autonomia_texto": autonomia_texto,
        "excedente_rebose": excedente_rebose,
        "q_rebose_m3_s": q_rebose_m3_s,
        "q_rebose_ls": q_rebose_ls
    }

def obtener_alerta(precipitacion, estacion):
    if estacion == "Monsalve": return "AZUL", "🛠️ En Aprendizaje", "#3399FF", "0s"
    if estacion == "Embalse": return "EMBALSE", "🌊 Nivel de Embalse", "#00BFFF", "0s"
    if estacion not in umbrales: return "GRIS", "☁️ Sin umbrales definidos", "#CCCCCC", "0s"
    
    u = umbrales[estacion]
    if precipitacion >= u["roja"]: return "ROJA", f"🚨 ROJA: Excede {u['roja']}mm", "#FF4B4B", "0.5s"
    elif precipitacion >= u["naranja"]: return "NARANJA", f"⚠️ NARANJA: Excede {u['naranja']}mm", "#FF9933", "1s"
    elif precipitacion >= u["amarilla"]: return "AMARILLA", f"🟡 AMARILLA: Excede {u['amarilla']}mm", "#FFFF00", "2s"
    elif precipitacion > 0: return "VERDE", "✅ Lluvia Normal", "#00CC96", "0s"
    return "GRIS", "☁️ Sin lluvia", "#CCCCCC", "0s"

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

@st.cache_data(ttl=60)
def get_last_reading(estacion):
    try:
        query = f"""
        SELECT * FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones` 
        WHERE id_estacion = '{estacion}' 
        ORDER BY SAFE_CAST(timestamp AS TIMESTAMP) DESC 
        LIMIT 1
        """
        query_job = client.query(query)
        rows = [dict(row) for row in query_job.result()]
        df = pd.DataFrame(rows)
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
        query_job = client.query(query)
        rows = [dict(row) for row in query_job.result()]
        df = pd.DataFrame(rows)
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize('UTC').dt.tz_convert('America/Bogota')
        return df
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=60)
def get_cota_embalse_actual_segura():
    try:
        df_emb = get_last_reading("Embalse")
        if not df_emb.empty:
            c = float(df_emb.iloc[0].get('temperatura', 885.80)) - OFFSET_RADAR_EMBALSE
            if 818.0 <= c <= 886.0:
                return c
    except:
        pass
    return 885.75

# ============================================================
# 4.1 METADATOS HIDROLÓGICOS & GEORREFERENCIACIÓN OFICIAL (amb)
# ============================================================
METADATA_ESTACIONES_AMB = {
    "Embalse": {
        "nombre_completo": "Embalse Tona (Radar OTT)",
        "tipo_sensor": "Radar Hidrométrico OTT (Nivel Vaso)",
        "cuenca_principal": "Cuenca Regulada del Río Tona",
        "subsistema_abastecimiento": "Alimentación a PTAP Bosconia (vía CRC Bosconia)",
        "zona": "Presa / Vaso del Embalse",
        "dms": "7°09'12.96\"N 73°02'44.88\"W",
        "lat": 7.153600,
        "lon": -73.045800,
        "altitud_msnm": 885.75,
        "peso_cuenca": 0.0,
        "lag_horas": "0 min (In Situ)",
        "microcuencas": "Vaso Principal de Almacenamiento Tona",
        "descripcion": "Medición milimétrica continua del nivel del vaso para cálculo de balance de masas, tasa neta de vaciado y resiliencia útil hacia PTAP Bosconia.",
        "color": "#005073"
    },
    "La_Mariana": {
        "nombre_completo": "Estación La Mariana",
        "tipo_sensor": "Estación Meteorológica Automática",
        "cuenca_principal": "Parte Alta Cuenca Río Frío",
        "subsistema_abastecimiento": "Alimentación a PTAP La Florida",
        "zona": "Filo Divisorio / Cabecera Río Frío",
        "dms": "7°07'21.86\"N 73°00'25.27\"W",
        "lat": 7.122739,
        "lon": -73.007019,
        "altitud_msnm": 2050.0,
        "peso_cuenca": 0.15,
        "lag_horas": "1.5 - 2.5 h",
        "microcuencas": "Escorrentía Lateral & Flanco Oriental Pajal-Golondrinas",
        "descripcion": "Monitorea la parte alta de la cuenca del Río Frío (fuente de abastecimiento de PTAP La Florida) y el filo divisorio oriental colindante con Golondrinas y El Pajal.",
        "color": "#AB63FA"
    },
    "El_Pajal": {
        "nombre_completo": "Estación El Pajal",
        "tipo_sensor": "Estación Meteorológica Automática",
        "cuenca_principal": "Parte Alta Quebrada Golondrinas & Ladera Sur Tona",
        "subsistema_abastecimiento": "Captación Golondrinas (RQ30) & Afluentes Ladera Sur",
        "zona": "Ladera Media-Alta Sur / Microcuenca Golondrinas",
        "dms": "7°08'26.09\"N 72°59'59.10\"W",
        "lat": 7.140581,
        "lon": -72.999750,
        "altitud_msnm": 2300.0,
        "peso_cuenca": 0.20,
        "lag_horas": "30 - 60 min",
        "microcuencas": "Qda. el Gualilo (mitad embalse) & Qda. La Reforma (cercana a presa)",
        "descripcion": "Monitorea la ladera sur del embalse (Quebrada el Gualilo en la mitad y Quebrada La Reforma cercana a la presa/radar) y la Captación Golondrinas (RQ30).",
        "color": "#FFA15A"
    },
    "Vegas_del_Quemado": {
        "nombre_completo": "Estación Vegas del Quemado",
        "tipo_sensor": "Estación Meteorológica Automática",
        "cuenca_principal": "Parte Alta Quebrada Arnania & Ladera Norte Tona",
        "subsistema_abastecimiento": "Captación Arnania (RQ30) & Qda. Los Monos (Litoral Derecho)",
        "zona": "Cuenca Media Norte / Valle de Arnania",
        "dms": "7°12'54.10\"N 73°00'46.10\"W",
        "lat": 7.215028,
        "lon": -73.012806,
        "altitud_msnm": 2150.0,
        "peso_cuenca": 0.30,
        "lag_horas": "1.0 - 2.0 h",
        "microcuencas": "Qda. Los Monos (Litoral Derecho frente a Reforma) & Cabecera Arnania",
        "descripcion": "Monitorea la ladera norte del embalse (Quebrada Los Monos en el litoral derecho frente a La Reforma) y la Captación Arnania (RQ30).",
        "color": "#00CC96"
    },
    "Yerbabuena": {
        "nombre_completo": "Estación Yerbabuena",
        "tipo_sensor": "Estación Meteorológica Automática",
        "cuenca_principal": "Alta Cuenca / Nacimiento Río Tona (Zona Páramo)",
        "subsistema_abastecimiento": "Recarga Principal Embalse Tona & PTAP Bosconia",
        "zona": "Cabecera Alta / Páramo de Tona",
        "dms": "7°11'44.99\"N 72°54'52.99\"W",
        "lat": 7.195831,
        "lon": -72.914719,
        "altitud_msnm": 3250.0,
        "peso_cuenca": 0.35,
        "lag_horas": "2.0 - 3.5 h",
        "microcuencas": "Río Tona (Cauce Principal) & Quebrada Ranás (Entrada Fondo Cola)",
        "descripcion": "Ubicada en el páramo de nacimiento del Río Tona. Monitorea la recarga pluvial principal y la Quebrada Ranás que desemboca directamente en la zona fondo cola del embalse.",
        "color": "#005073"
    },
    "Monsalve": {
        "nombre_completo": "Estación Monsalve",
        "tipo_sensor": "Estación Meteorológica Automática",
        "cuenca_principal": "Alta Cuenca / Zona Páramo del Río Suratá (Santurbán / Sisavita)",
        "subsistema_abastecimiento": "Cuenca Alta Río Suratá (Captaciones Norte & Futura PTAP Los Angelinos)",
        "zona": "Páramo de Santurbán / Sisavita / Cachirí",
        "dms": "7°26'30.50\"N 72°55'51.30\"W",
        "lat": 7.441806,
        "lon": -72.930917,
        "altitud_msnm": 3550.0,
        "peso_cuenca": 0.0,
        "lag_horas": "3.0 - 5.0 h",
        "microcuencas": "Cabecera Alta Río Suratá & Microcuenca Sisavita",
        "descripcion": "Ubicada en la alta montaña del Páramo de Santurbán y Sisavita. Monitorea la cabecera del Río Suratá, eje hídrico norte del sistema metropolitano de abastecimiento.",
        "color": "#3399FF"
    }
}

@st.cache_data(ttl=120)
def obtener_precipitacion_cuenca_tona(fecha_inicio, fecha_fin):
    try:
        if isinstance(fecha_inicio, datetime):
            f_ini_dt = fecha_inicio if fecha_inicio.tzinfo else colombia_tz.localize(fecha_inicio)
            f_ini_str = f_ini_dt.astimezone(utc_tz).strftime('%Y-%m-%d %H:%M:%S')
        else:
            f_ini_dt = colombia_tz.localize(datetime.combine(fecha_inicio, datetime.min.time()))
            f_ini_str = f_ini_dt.astimezone(utc_tz).strftime('%Y-%m-%d %H:%M:%S')
            
        if isinstance(fecha_fin, datetime):
            f_fin_dt = fecha_fin if fecha_fin.tzinfo else colombia_tz.localize(fecha_fin)
            f_fin_str = f_fin_dt.astimezone(utc_tz).strftime('%Y-%m-%d %H:%M:%S')
        else:
            f_fin_dt = colombia_tz.localize(datetime.combine(fecha_fin, datetime.max.time()))
            f_fin_str = f_fin_dt.astimezone(utc_tz).strftime('%Y-%m-%d %H:%M:%S')
            
        estaciones_cuenca = ['Yerbabuena', 'Vegas_del_Quemado', 'El_Pajal', 'La_Mariana']
        estaciones_str = "', '".join(estaciones_cuenca)
        
        query = f"""
        SELECT id_estacion, 
               SUM(SAFE_CAST(precipitacion AS FLOAT64)) as precip_total,
               MAX(SAFE_CAST(precipitacion AS FLOAT64)) as precip_max_evento,
               COUNT(*) as num_registros
        FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones`
        WHERE id_estacion IN ('{estaciones_str}')
        AND SAFE_CAST(timestamp AS TIMESTAMP) >= TIMESTAMP('{f_ini_str}')
        AND SAFE_CAST(timestamp AS TIMESTAMP) <= TIMESTAMP('{f_fin_str}')
        GROUP BY id_estacion
        """
        query_job = client.query(query)
        rows = [dict(row) for row in query_job.result()]
        return pd.DataFrame(rows)
    except Exception as e:
        return pd.DataFrame()

def calcular_atribucion_cuenca_tona(df_cuenca, q_afluente_ls):
    registros = []
    suma_precip_pura = 0.0
    suma_ponderada = 0.0
    
    mapa_precip = {}
    if not df_cuenca.empty and 'id_estacion' in df_cuenca.columns:
        for _, r in df_cuenca.iterrows():
            est_id = r['id_estacion']
            p_tot = float(r.get('precip_total', 0.0) or 0.0)
            p_max = float(r.get('precip_max_evento', 0.0) or 0.0)
            mapa_precip[est_id] = {'total': p_tot, 'max': p_max}
            
    for est_id in ['Yerbabuena', 'Vegas_del_Quemado', 'El_Pajal', 'La_Mariana']:
        meta = METADATA_ESTACIONES_AMB[est_id]
        p_info = mapa_precip.get(est_id, {'total': 0.0, 'max': 0.0})
        p_val = max(0.0, p_info['total'])
        suma_precip_pura += p_val
        aporte_pond = p_val * meta['peso_cuenca']
        suma_ponderada += aporte_pond
        
        registros.append({
            "id_estacion": est_id,
            "nombre": meta["nombre_completo"],
            "zona": meta["zona"],
            "microcuencas": meta["microcuencas"],
            "subsistema": meta["subsistema_abastecimiento"],
            "altitud_msnm": meta["altitud_msnm"],
            "peso_cuenca": meta["peso_cuenca"],
            "lag_horas": meta["lag_horas"],
            "color": meta["color"],
            "precipitacion_mm": p_val,
            "precip_max_mm": p_info['max'],
            "aporte_ponderado": aporte_pond,
            "lat": meta["lat"],
            "lon": meta["lon"]
        })
        
    df_atrib = pd.DataFrame(registros)
    
    if suma_ponderada > 0:
        df_atrib['porcentaje_atribucion'] = (df_atrib['aporte_ponderado'] / suma_ponderada) * 100.0
        estado_cuenca = "LLUVIA ACTIVA"
        est_dominante = df_atrib.sort_values('porcentaje_atribucion', ascending=False).iloc[0]
        mensaje_diagnostico = f"🌧️ <strong>Recarga Activa por Precipitación en Cuenca:</strong> El caudal afluente estimado (~{q_afluente_ls:,.0f} L/s) está originado principalmente en <strong>{est_dominante['nombre']}</strong> ({est_dominante['porcentaje_atribucion']:.1f}% de influencia con {est_dominante['precipitacion_mm']:.1f} mm acumulados), activando la escorrentía en <strong>{est_dominante['microcuencas']}</strong> ({est_dominante['subsistema']}) con un tiempo de tránsito (Lag) de <strong>{est_dominante['lag_horas']}</strong> hacia la cola del embalse."
    else:
        df_atrib['porcentaje_atribucion'] = df_atrib['peso_cuenca'] * 100.0
        estado_cuenca = "ESTIAJE BASE"
        est_dominante = df_atrib.sort_values('peso_cuenca', ascending=False).iloc[0]
        mensaje_diagnostico = f"☀️ <strong>Régimen de Estiaje / Flujo Base Subterráneo:</strong> Sin precipitaciones acumuladas en las estaciones durante esta ventana de tiempo. El caudal continuo de recarga en cola (~{q_afluente_ls:,.0f} L/s) proviene del rendimiento hidrogeológico base natural de las microcuencas (Río Tona cabecera, Las Ranas, Gualilo, La Reforma y Los Monos)."
        
    df_atrib['caudal_estimado_ls'] = (df_atrib['porcentaje_atribucion'] / 100.0) * max(0.0, q_afluente_ls)
    
    return {
        "df": df_atrib,
        "estado": estado_cuenca,
        "suma_precip_mm": suma_precip_pura,
        "estacion_dominante": est_dominante['nombre'],
        "diagnostico": mensaje_diagnostico
    }

def mostrar_ficha_geografica_estacion(nombre_estacion):
    if nombre_estacion not in METADATA_ESTACIONES_AMB:
        return
    meta = METADATA_ESTACIONES_AMB[nombre_estacion]
    
    st.markdown("---")
    st.subheader(f"📍 Georreferenciación & Contexto Hidrológico — {meta['nombre_completo']}")
    
    col_info, col_map = st.columns([1.3, 1])
    with col_info:
        st.markdown(f"""
        <div style="background: rgba(0,80,115,0.05); padding: 14px 18px; border-radius: 10px; border-left: 5px solid {meta['color']}; font-size: 13px; line-height: 1.6;">
            <strong>🏞️ Cuenca Hidrológica:</strong> {meta['cuenca_principal']}<br>
            <strong>🏢 Subsistema / PTAP Abastecida:</strong> <span style="color: #005073; font-weight: 700;">{meta['subsistema_abastecimiento']}</span><br>
            <strong>🏔️ Altitud Oficial:</strong> <strong>{meta['altitud_msnm']:,.1f} msnm</strong><br>
            <strong>📍 Coordenadas Sexagesimales (DMS):</strong> <code>{meta['dms']}</code><br>
            <strong>🌐 Coordenadas Decimales:</strong> <code>{meta['lat']:.6f}°N, {meta['lon']:.6f}°W</code><br>
            <strong>📡 Instrumentación Operativa:</strong> {meta['tipo_sensor']}<br>
            <div style="margin-top: 8px; padding-top: 6px; border-top: 1px dashed rgba(0,80,115,0.2); font-style: italic; color: #444;">
                {meta['descripcion']}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with col_map:
        df_punto = pd.DataFrame([{
            'lat': meta['lat'],
            'lon': meta['lon'],
            'nombre': meta['nombre_completo'],
            'altitud': f"{meta['altitud_msnm']:.0f} msnm",
            'sistema': meta['subsistema_abastecimiento']
        }])
        fig_map_ind = px.scatter_mapbox(
            df_punto,
            lat='lat',
            lon='lon',
            hover_name='nombre',
            hover_data={'lat': False, 'lon': False, 'altitud': True, 'sistema': True},
            zoom=12,
            height=240
        )
        fig_map_ind.update_traces(marker=dict(size=16, color=meta['color']))
        fig_map_ind.update_layout(
            mapbox_style="open-street-map",
            margin=dict(t=0, b=0, l=0, r=0)
        )
        st.plotly_chart(fig_map_ind, use_container_width=True)

def mostrar_modulo_atribucion_cuenca(df_cuenca, q_afluente_ls, horas):
    res = calcular_atribucion_cuenca_tona(df_cuenca, q_afluente_ls)
    df_atrib = res["df"]
    
    st.markdown("---")
    st.subheader("🛰️ Inteligencia de Cuenca: Trazabilidad & Atribución de Aportes Hídricos")
    st.caption(f"Identificación en tiempo real del origen de la recarga en la cola del Río Tona en las últimas **{horas:.1f} horas**.")
    
    color_border = "#00CC96" if res["estado"] == "LLUVIA ACTIVA" else "#005073"
    icono = "🌧️" if res["estado"] == "LLUVIA ACTIVA" else "☀️"
    
    st.markdown(f"""
    <div style="background: rgba(0,80,115,0.06); padding: 14px 18px; border-radius: 10px; border-left: 5px solid {color_border}; margin-bottom: 15px; font-size: 13.5px; line-height: 1.5;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; flex-wrap: wrap;">
            <strong style="color: #005073; font-size: 14px;">{icono} DIAGNÓSTICO INTELIGENTE DE RECARGA DE CUENCA:</strong>
            <span class="badge-status" style="background: rgba(0,80,115,0.15); color: #005073; border: 1px solid #005073;">ESTADO: {res['estado']}</span>
        </div>
        {res['diagnostico']}
    </div>
    """, unsafe_allow_html=True)
    
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        fig_donut = px.pie(
            df_atrib, 
            names='id_estacion', 
            values='porcentaje_atribucion', 
            title='🍰 % Distribución de Aportes a la Cola del Embalse',
            hole=0.45,
            color='id_estacion',
            color_discrete_map={row['id_estacion']: row['color'] for _, row in df_atrib.iterrows()}
        )
        fig_donut.update_traces(textposition='inside', textinfo='percent+label')
        fig_donut.update_layout(height=300, template='plotly_white', margin=dict(t=40, b=10, l=10, r=10))
        st.plotly_chart(fig_donut, use_container_width=True)
        
    with col_g2:
        fig_bar = px.bar(
            df_atrib,
            x='id_estacion',
            y='precipitacion_mm',
            title='🌧️ Precipitación Registrada en Cuenca (mm)',
            color='id_estacion',
            color_discrete_map={row['id_estacion']: row['color'] for _, row in df_atrib.iterrows()},
            text='precipitacion_mm'
        )
        fig_bar.update_traces(texttemplate='%{text:.1f} mm', textposition='outside')
        fig_bar.update_layout(height=300, template='plotly_white', xaxis_title="Estación Meteorológica", yaxis_title="Lluvia Acumulada (mm)", showlegend=False, margin=dict(t=40, b=10, l=10, r=10))
        st.plotly_chart(fig_bar, use_container_width=True)
        
    st.markdown("#### 📋 Matriz Hidrológica de Cuenca & Tiempos de Tránsito (Lag Time):")
    df_tabla = df_atrib[['nombre', 'zona', 'microcuencas', 'subsistema', 'precipitacion_mm', 'lag_horas', 'porcentaje_atribucion', 'caudal_estimado_ls']].copy()
    df_tabla.columns = ['Estación', 'Zona Cuenca', 'Microcuencas / Quebradas', 'Subsistema Abastecido', 'Lluvia (mm)', 'Retardo (Lag)', 'Aporte (%)', 'Q Estimado (L/s)']
    df_tabla['Lluvia (mm)'] = df_tabla['Lluvia (mm)'].apply(lambda x: f"{x:.1f} mm")
    df_tabla['Aporte (%)'] = df_tabla['Aporte (%)'].apply(lambda x: f"{x:.1f} %")
    df_tabla['Q Estimado (L/s)'] = df_tabla['Q Estimado (L/s)'].apply(lambda x: f"{x:,.0f} L/s")
    
    st.dataframe(df_tabla, use_container_width=True, hide_index=True)
    
    # Mapa General de Cuenca en el Bloque del Embalse
    st.markdown("#### 🗺️ Mapa de Trazabilidad Espacial de la Cuenca Tona & Estaciones:")
    df_mapa_cuenca = pd.DataFrame([
        {
            'lat': m['lat'],
            'lon': m['lon'],
            'nombre': m['nombre_completo'],
            'tipo': m['tipo_sensor'],
            'altitud': f"{m['altitud_msnm']:.0f} msnm",
            'subsistema': m['subsistema_abastecimiento'],
            'color': m['color']
        }
        for k, m in METADATA_ESTACIONES_AMB.items()
    ])
    fig_map_cuenca = px.scatter_mapbox(
        df_mapa_cuenca,
        lat='lat',
        lon='lon',
        hover_name='nombre',
        hover_data={'tipo': True, 'altitud': True, 'subsistema': True, 'lat': False, 'lon': False},
        color='nombre',
        zoom=10,
        height=340
    )
    fig_map_cuenca.update_traces(marker=dict(size=14))
    fig_map_cuenca.update_layout(
        mapbox_style="open-street-map",
        margin=dict(t=10, b=10, l=10, r=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_map_cuenca, use_container_width=True)

# ============================================================
# 5. SELECTOR DE ESTACIÓN (BARRA HORIZONTAL SUPERIOR)
# ============================================================
estaciones = ["Embalse", "La_Mariana", "Yerbabuena", "Vegas_del_Quemado", "El_Pajal", "Monsalve"]

if 'estacion_seleccionada' not in st.session_state:
    st.session_state.estacion_seleccionada = "Embalse"

st.markdown("""
<div style="background: rgba(0,80,115,0.08); padding: 8px 14px; border-radius: 10px; margin-bottom: 12px; border-left: 5px solid #005073; display: flex; justify-content: space-between; align-items: center;">
    <span style="font-weight: 700; color: #005073; font-size: 14px;">📍 SELECCIONE LA ESTACIÓN:</span>
    <span style="font-size: 12px; color: #555;">👈 También disponible en el menú lateral</span>
</div>
""", unsafe_allow_html=True)

seleccion = st.radio(
    "Estación:",
    estaciones,
    index=estaciones.index(st.session_state.estacion_seleccionada) if st.session_state.estacion_seleccionada in estaciones else 0,
    horizontal=True,
    label_visibility="collapsed"
)
st.session_state.estacion_seleccionada = seleccion

# Sincronizar barra lateral
st.sidebar.markdown("---")
st.sidebar.markdown("### 📍 Selector de Estación")
seleccion_sidebar = st.sidebar.selectbox(
    "Cambiar Estación:",
    estaciones,
    index=estaciones.index(seleccion)
)
if seleccion_sidebar != seleccion:
    st.session_state.estacion_seleccionada = seleccion_sidebar
    st.rerun()

horas = st.sidebar.slider("⏱️ Horas históricas:", 1, 168, 24, step=1, help="Rango de horas para consultar y graficar telemetría histórica")

fecha_fin = datetime.now(colombia_tz)
fecha_inicio = fecha_fin - timedelta(hours=horas)

with st.spinner("🔄 Consultando telemetría en tiempo real..."):
    df_actual = get_last_reading(seleccion)
    df_hist = get_historical_data_range(seleccion, fecha_inicio, fecha_fin)

# ============================================================
# 6. EXPORTACIÓN Y EXCEL OPENPYXL (CON BALANCE BOSCONIA 24H)
# ============================================================
def enriquecer_datos_embalse(df):
    if df.empty or 'temperatura' not in df.columns:
        return df
    df_e = df.copy().sort_values('timestamp')
    c_raw = pd.to_numeric(df_e['temperatura'], errors='coerce')
    df_e['cota_embalse_msnm'] = (c_raw - OFFSET_RADAR_EMBALSE).round(3)
    
    df_e['volumen_total_hm3'] = df_e['cota_embalse_msnm'].apply(lambda c: round(interpolar_volumen(c), 4) if pd.notna(c) else None)
    df_e['volumen_util_hm3'] = df_e['volumen_total_hm3'].apply(lambda v: round(max(0.0, v - 1.980), 4) if pd.notna(v) else None)
    
    c_ini = df_e['cota_embalse_msnm'].iloc[0]
    v_ini_m3 = (df_e['volumen_total_hm3'].iloc[0] or 0) * 1_000_000.0
    
    df_e['descenso_acumulado_cm'] = ((c_ini - df_e['cota_embalse_msnm']) * 100.0).round(2)
    df_e['m3_consumidos_bosconia'] = df_e['volumen_total_hm3'].apply(lambda v: max(0.0, round(v_ini_m3 - (v * 1_000_000.0), 1)) if pd.notna(v) else 0.0)
    df_e['caudal_rebose_ls'] = df_e['cota_embalse_msnm'].apply(lambda c: round(calcular_caudal_morning_glory(c)[1], 1) if pd.notna(c) else 0.0)
    
    t_ini = df_e['timestamp'].iloc[0]
    df_e['delta_segundos_acum'] = (df_e['timestamp'] - t_ini).dt.total_seconds()
    df_e['caudal_medio_bosconia_ls'] = df_e.apply(
        lambda r: round((r['m3_consumidos_bosconia'] / r['delta_segundos_acum']) * 1000.0, 1) if r['delta_segundos_acum'] > 300 else 0.0,
        axis=1
    )
    
    return df_e

def consolidar_balance_diario_embalse(df_emb_enr):
    if df_emb_enr.empty:
        return pd.DataFrame()
    df_c = df_emb_enr.copy()
    if 'timestamp' in df_c.columns:
        df_c['fecha_dia'] = df_c['timestamp'].dt.strftime('%Y-%m-%d')
    else:
        return pd.DataFrame()
        
    resumen_dias = []
    for fecha_dia, grupo in df_c.groupby('fecha_dia'):
        g_s = grupo.sort_values('timestamp')
        if len(g_s) < 2:
            continue
        c_ini = g_s.iloc[0]['cota_embalse_msnm']
        c_fin = g_s.iloc[-1]['cota_embalse_msnm']
        v_ini = g_s.iloc[0]['volumen_total_hm3'] * 1_000_000.0
        v_fin = g_s.iloc[-1]['volumen_total_hm3'] * 1_000_000.0
        
        t_ini = g_s.iloc[0]['timestamp']
        t_fin = g_s.iloc[-1]['timestamp']
        delta_s = max(1.0, (t_fin - t_ini).total_seconds())
        delta_horas = delta_s / 3600.0
        
        delta_cm = (c_ini - c_fin) * 100.0
        m3_dia = max(0.0, v_ini - v_fin)
        q_ls = (m3_dia / delta_s) * 1000.0 if delta_s > 60 else 0.0
        
        resumen_dias.append({
            "Fecha": fecha_dia,
            "Horas Monitoreadas": round(delta_horas, 1),
            "Cota Inicial (msnm)": round(c_ini, 3),
            "Cota Final (msnm)": round(c_fin, 3),
            "Descenso (cm)": round(delta_cm, 2),
            "Metros Cúbicos Entregados Bosconia (m³)": round(m3_dia, 1),
            "Caudal Medio Estimado (L/s)": round(q_ls, 1),
            "Vol. Útil Remanente (hm³)": round(g_s.iloc[-1]['volumen_util_hm3'], 3)
        })
    return pd.DataFrame(resumen_dias)

def preparar_df_para_exportar(df):
    df_export = df.copy()
    if 'timestamp' in df_export.columns:
        df_export['timestamp'] = df_export['timestamp'].dt.tz_localize(None)
    return df_export

def generar_excel_con_formato(df, nombre_estacion, periodo_descripcion):
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        if nombre_estacion == "Embalse" and 'temperatura' in df.columns:
            df_enr = enriquecer_datos_embalse(df)
            df_balance_24h = consolidar_balance_diario_embalse(df_enr)
            df_enr_export = preparar_df_para_exportar(df_enr)
            
            # Hoja 1: Balance Consolidado 24h
            if not df_balance_24h.empty:
                df_balance_24h.to_excel(writer, sheet_name='Balance_Bosconia_24h', index=False)
                ws_bal = writer.sheets['Balance_Bosconia_24h']
                header_font = Font(bold=True, color="FFFFFF")
                header_fill = PatternFill(start_color="005073", end_color="005073", fill_type="solid")
                header_alignment = Alignment(horizontal="center", vertical="center")
                for col in range(1, len(df_balance_24h.columns) + 1):
                    cell = ws_bal.cell(row=1, column=col)
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.alignment = header_alignment
                for col in ws_bal.columns:
                    max_len = max(len(str(cell.value or '')) for cell in col)
                    col_letter = col[0].column_letter
                    ws_bal.column_dimensions[col_letter].width = min(max_len + 4, 40)
            
            # Hoja 2: Telemetría Detallada
            df_enr_export.to_excel(writer, sheet_name='Telemetria_Embalse', index=False)
            worksheet = writer.sheets['Telemetria_Embalse']
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="172A45", end_color="172A45", fill_type="solid")
            for col in range(1, len(df_enr_export.columns) + 1):
                cell = worksheet.cell(row=1, column=col)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center", vertical="center")
            for col in worksheet.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = col[0].column_letter
                worksheet.column_dimensions[col_letter].width = min(max_len + 3, 50)
            df_registros_len = len(df_enr_export)
        else:
            df_export = preparar_df_para_exportar(df)
            df_export.to_excel(writer, sheet_name='Datos', index=False)
            worksheet = writer.sheets['Datos']
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="005073", end_color="005073", fill_type="solid")
            header_alignment = Alignment(horizontal="center", vertical="center")
            for col in range(1, len(df_export.columns) + 1):
                cell = worksheet.cell(row=1, column=col)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
            for col in worksheet.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = col[0].column_letter
                worksheet.column_dimensions[col_letter].width = min(max_len + 3, 50)
            df_registros_len = len(df_export)
        
        if es_embalse:
            meta_rows = [
                ['Sistema de Información', SISTEMA],
                ['Proyecto Institucional', 'MIMAT-C26 • amb s.a. e.s.p.'],
                ['Estación / Sensor', 'Embalse Tona — Radar OTT (Nivel Vaso)'],
                ['Período de Consulta', periodo_descripcion],
                ['Fecha de Generación', datetime.now(colombia_tz).strftime('%Y-%m-%d %H:%M:%S')],
                ['Total Registros', df_registros_len],
                ['Líder Técnico / Autor', AUTOR],
                ['Cota de Rebose Base', f"{NIVEL_REBOSE_EMBALSE} msnm"],
                ['Cota Mínima Técnica', f"{NIVEL_MINIMO_TECNICO} msnm"],
                ['Volumen Útil Batimetría 2026', f"{VOLUMEN_UTIL_MAX_HM3} hm³"],
                ['Válvula de Salida PTAP', 'CRC Bosconia (Cámara de Rompimiento de Carga)'],
                ['---', '---'],
                ['AFLUENTES & MORFOLOGÍA DIRECTA DEL EMBALSE', 'UBICACIÓN ESPACIAL & FUNCIÓN'],
                ['Río Tona (Cauce Principal)', 'Ingreso por Zona Fondo Cola (Cabecera Páramo Yerbabuena)'],
                ['Quebrada Ranás', 'Desembocadura directa en Zona Fondo Cola del Embalse'],
                ['Quebrada el Gualilo', 'Margen Sur (Litoral Izquierdo, en la mitad del vaso)'],
                ['Quebrada La Reforma', 'Margen Sur (Litoral Izquierdo, cercana a presa y radar OTT)'],
                ['Quebrada Los Monos', 'Margen Norte (Litoral Derecho, frente a Quebrada La Reforma)'],
                ['---', '---'],
                ['Ecuación de Continuidad', 'Q_CRC_Bosconia = Q_Tasa_Neta_Vaciado + ∑ Q_Afluentes_Cuenca']
            ]
            metadata = pd.DataFrame(meta_rows, columns=['Parámetro / Microcuenca', 'Descripción Técnica'])
        else:
            metadata = pd.DataFrame({
                'Propiedad': ['Sistema', 'Proyecto', 'Estación', 'Período', 'Fecha exportación', 'Total registros', 'Responsable'],
                'Valor': [SISTEMA, "MIMAT-C26", nombre_estacion, periodo_descripcion, datetime.now(colombia_tz).strftime('%Y-%m-%d %H:%M:%S'), df_registros_len, AUTOR]
            })
            
        metadata.to_excel(writer, sheet_name='Metadatos', index=False)
        m_sheet = writer.sheets['Metadatos']
        for col in range(1, 3):
            cell = m_sheet.cell(row=1, column=col)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
        for col in m_sheet.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = col[0].column_letter
            m_sheet.column_dimensions[col_letter].width = min(max_len + 4, 60)
            
    return output.getvalue()

def generar_resumen_estadistico(df, nombre_estacion=""):
    if df.empty: return "No hay datos disponibles"
    resumen = [
        f"📊 RESUMEN ESTADÍSTICO — MIMAT-C26 (amb) [{nombre_estacion or 'Telemetría'}]",
        "=" * 50,
        f"📋 Generado el {datetime.now(colombia_tz).strftime('%Y-%m-%d %H:%M')}",
        ""
    ]
    
    # Manejo especializado para el Embalse Tona
    if nombre_estacion == "Embalse" or (len(df) > 0 and pd.to_numeric(df.get('temperatura', pd.Series()), errors='coerce').mean() > 800):
        df_enr = enriquecer_datos_embalse(df)
        c_ini = df_enr['cota_embalse_msnm'].iloc[0]
        c_fin = df_enr['cota_embalse_msnm'].iloc[-1]
        c_max = df_enr['cota_embalse_msnm'].max()
        c_min = df_enr['cota_embalse_msnm'].min()
        c_mean = df_enr['cota_embalse_msnm'].mean()
        
        m3_tot = df_enr['m3_consumidos_bosconia'].max()
        desc_cm = (c_ini - c_fin) * 100.0
        
        t_ini = df_enr['timestamp'].iloc[0]
        t_fin = df_enr['timestamp'].iloc[-1]
        delta_s = max(1.0, (t_fin - t_ini).total_seconds())
        q_medio_ls = (m3_tot / delta_s) * 1000.0 if delta_s > 60 else 0.0
        
        vol_util_act = df_enr['volumen_util_hm3'].iloc[-1]
        dias_aut = (vol_util_act * 1_000_000.0) / (q_medio_ls * 86.4) if q_medio_ls > 0 else None
        
        resumen.append("🌊 PARÁMETROS HIDRÁULICOS DEL EMBALSE:")
        resumen.append(f"   • Cota Actual:                 {c_fin:.3f} msnm")
        resumen.append(f"   • Cota Inicial del Período:    {c_ini:.3f} msnm")
        resumen.append(f"   • Cota Promedio:               {c_mean:.3f} msnm")
        resumen.append(f"   • Cota Máxima:                 {c_max:.3f} msnm")
        resumen.append(f"   • Cota Mínima:                 {c_min:.3f} msnm")
        resumen.append(f"   • Descenso Acumulado:          {desc_cm:+.2f} cm")
        resumen.append("")
        resumen.append("💧 EXTRACCIÓN & BALANCE DE MASAS PTAP BOSCONIA:")
        resumen.append(f"   • Metros Cúbicos Entregados:   {m3_tot:,.1f} m³")
        resumen.append(f"   • Tasa Neta Vaciado Embalse:    {q_medio_ls:,.1f} L/s ({q_medio_ls/1000.0:.3f} m³/s)")
        resumen.append(f"   • Volumen Útil Remanente:       {vol_util_act:.3f} hm³")
        resumen.append(f"   • Autonomía Hídrica:           {f'{dias_aut:.1f} Días' if dias_aut else 'Indefinida'}")
        resumen.append(f"   • Registros Analizados:         {len(df)}")
        resumen.append("")
        resumen.append("⚖️ ECUACIÓN DE BALANCE HIDROLÓGICO:")
        resumen.append(f"   Q_CRC_Bosconia (~400 L/s) = Q_Tasa_Neta ({q_medio_ls:,.0f} L/s) + Q_Afluentes_Cuenca (~{max(0, 400 - q_medio_ls):,.0f} L/s)")
        resumen.append("   * Afluentes tributarios: Río Tona + Qda. Ranás (fondo cola) + Qda. el Gualilo (mitad) + Qda. La Reforma (presa) + Qda. Los Monos (litoral derecho frente a Reforma).")
        resumen.append("")
        resumen.append("ℹ️ NOTA TÉCNICA: La estación Embalse registra exclusivamente niveles hidrométricos (msnm) y volúmenes hídricos.")
        return "\n".join(resumen)
        
    # Para estaciones meteorológicas (La Mariana, Yerbabuena, etc.)
    cols = ['temperatura', 'precipitacion', 'humedad', 'presion', 'velocidad_viento', 'direccion_viento', 'voltaje_bateria']
    for col in cols:
        if col in df.columns:
            datos = pd.to_numeric(df[col], errors='coerce').dropna()
            if not datos.empty and (datos.abs().max() > 0 or col in ['temperatura', 'precipitacion']):
                resumen.append(f"📈 {col.upper()}:")
                resumen.append(f"   • Promedio: {datos.mean():.2f}")
                resumen.append(f"   • Máximo:  {datos.max():.2f}")
                resumen.append(f"   • Mínimo:  {datos.min():.2f}")
                resumen.append(f"   • Registros: {len(datos)}")
                resumen.append("")
    return "\n".join(resumen)

# ============================================================
# 7. MÓDULO EDV (EXTENSÓMETROS)
# ============================================================
@st.cache_data(ttl=600)
def get_edv_data(extensometro='izquierdo'):
    try:
        table = f"edv_{extensometro}"
        query = f"SELECT fecha, anillo, lectura, cota_referencia, cota, asiento, dist_datum, notas FROM `gen-lang-client-0342049346.amb_hidrologia.{table}` ORDER BY fecha DESC, CAST(anillo AS INT64) DESC"
        query_job = client.query(query)
        rows = [dict(row) for row in query_job.result()]
        df = pd.DataFrame(rows)
        if not df.empty:
            df['fecha'] = pd.to_datetime(df['fecha']).dt.tz_localize('UTC').dt.tz_convert('America/Bogota')
        return df
    except:
        return pd.DataFrame()

def create_edv_profile(df, fecha_sel=None, titulo="Perfil de Deformaciones"):
    if fecha_sel is None: fecha_sel = df['fecha'].max()
    df_f = df[df['fecha'].dt.date == fecha_sel.date()].sort_values('anillo', ascending=False)
    if df_f.empty: return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_f['asiento'], y=df_f['anillo'], mode='lines+markers', name=f'Perfil {fecha_sel.strftime("%d/%m/%Y")}', line=dict(color='#FF4B4B', width=3), marker=dict(size=10, color='#FF4B4B')))
    fig.add_vline(x=0, line_dash="dash", line_color="gray", line_width=1)
    fig.add_hline(y=0, line_dash="dash", line_color="green", line_width=2, annotation_text="FONDO")
    fig.update_layout(title=f'{titulo} - {fecha_sel.strftime("%d/%m/%Y")}', xaxis_title='Asiento (cm)', yaxis_title='Anillo', template='plotly_white', height=420)
    return fig

def mostrar_seccion_edv():
    st.markdown("---")
    st.subheader("📏 Instrumentación Geotécnica - Extensómetros (EDV)")
    st.caption("Medición de asentamientos verticales en la presa del embalse")
    c1, c2 = st.columns(2)
    with c1: ext_sel = st.selectbox("Extensómetro:", ["izquierdo", "derecho"], index=0)
    with c2: vista_sel = st.selectbox("Vista Geotécnica:", ["Perfil Individual", "Evolución Histórica"], index=0)
    df_edv = get_edv_data(ext_sel)
    if df_edv.empty:
        st.info("Sin datos EDV disponibles.")
        return
    if vista_sel == "Perfil Individual":
        fechas = sorted(df_edv['fecha'].unique(), reverse=True)
        f_sel = st.selectbox("Fecha del perfil:", fechas, format_func=lambda x: x.strftime('%d/%m/%Y'))
        fig = create_edv_profile(df_edv, f_sel, f"EDV {ext_sel.capitalize()}")
        if fig: st.plotly_chart(fig, use_container_width=True)

# ============================================================
# 8. PESTAÑAS PRINCIPALES DEL SISTEMA (5 PESTAÑAS)
# ============================================================
tab_situacion, tab_embalse_2026, tab_series, tab_ia, tab_matematica = st.tabs([
    "📊 Situación Actual", 
    "🌊 Gestión Embalse & Sequía 2026", 
    "📈 Series de Tiempo & Descargas", 
    "🤖 Asistente IA MIMAT-C",
    "📐 Fundamento Matemático & Auditoría"
])

# ------------------------------------------------------------
# TAB 1: SITUACIÓN ACTUAL
# ------------------------------------------------------------
with tab_situacion:
    if not df_actual.empty:
        row = df_actual.iloc[0]
        st.subheader(f"📡 Telemetría en Vivo: {seleccion.replace('_', ' ')}")
        
        if seleccion == "Embalse":
            raw_c = row.get('temperatura', 885.80)
            cota_raw = float(raw_c) if pd.notna(raw_c) and float(raw_c) > 800 else 885.80
            cota_actual = cota_raw - OFFSET_RADAR_EMBALSE
            hidro = calcular_hidraulica_embalse(cota_actual, q_ptap_ls=0.0)
            bal = calcular_balance_dinamico(df_hist)
            
            # Descenso total acumulado desde inicio de maniobra en cota de rebose (885.75 msnm)
            descenso_total_cm = (cota_actual - NIVEL_REBOSE_EMBALSE) * 100.0
            vol_max_rebose_m3 = interpolar_volumen(NIVEL_REBOSE_EMBALSE) * 1_000_000.0
            vol_actual_m3 = interpolar_volumen(cota_actual) * 1_000_000.0
            vol_entregado_total_m3 = max(0.0, vol_max_rebose_m3 - vol_actual_m3)
            
            if hidro["excedente_rebose"] > 0:
                st.markdown(f"""
                <div class="alert-box alert-green" style="border-left: 5px solid #00CC96; background: rgba(0, 204, 150, 0.12);">
                    <span style="font-size: 24px;">🌊</span>
                    <div>
                        <strong>ESTADO: ALTA DISPONIBILIDAD HÍDRICA — REBOSE ACTIVO HACIA PUENTE TONA (+{hidro['excedente_rebose']:.2f} msnm)</strong><br>
                        Cota calibrada en <strong>{cota_actual:.2f} msnm</strong>. Entregando <strong>{hidro['q_rebose_m3_s']:.2f} m³/s ({hidro['q_rebose_ls']:,.0f} L/s)</strong> por el pozo Morning Glory hacia Puente Tona (confluencia con Río Suratá). Mayor disponibilidad de agua cruda en cuenca para maximizar captación hacia PTAP Bosconia y futura PTAP Los Angelinos.
                    </div>
                </div>
                """, unsafe_allow_html=True)
            elif abs(hidro["excedente_rebose"]) < 0.01:
                st.markdown(f"""
                <div class="alert-box alert-green">
                    <span style="font-size: 24px;">🟢</span>
                    <div>
                        <strong>ESTADO: EMBALSE A CAPACIDAD MÁXIMA (885.75 msnm)</strong><br>
                        Nivel exacto al labio del vertedero. Sin rebose activo (0 L/s). Capacidad útil al 100%.
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="alert-box alert-green">
                    <span style="font-size: 24px;">🟢</span>
                    <div>
                        <strong>ESTADO: OPERACIÓN NORMAL (EXTRACCIÓN ACTIVA HACIA CRC BOSCONIA)</strong><br>
                        Cota calibrada en <strong>{cota_actual:.2f} msnm</strong>. Descenso total acumulado de <strong>{abs(descenso_total_cm):.1f} cm</strong> ({abs(hidro['excedente_rebose']):.2f} msnm bajo vertedero). Volumen acumulado entregado: <strong>{vol_entregado_total_m3:,.0f} m³</strong>. Capacidad útil al <strong>{hidro['porcentaje_util']:.1f}%</strong> ({hidro['volumen_util_hm3']:.2f} hm³).
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("🌊 Cota Calibrada", f"{cota_actual:.2f} msnm", delta=f"{descenso_total_cm:+.1f} cm vs Rebose", help=f"Sensor OTT: {cota_raw:.2f} msnm | Offset calibrado: -{OFFSET_RADAR_EMBALSE*100:.0f} cm")
            c2.metric("💧 Volumen Útil", f"{hidro['volumen_util_hm3']:.2f} hm³", delta=f"{hidro['porcentaje_util']:.1f}% útil")
            c3.metric("📉 Descenso Total Acumulado", f"{abs(descenso_total_cm):.1f} cm", delta=f"~{vol_entregado_total_m3:,.0f} m³ a CRC", delta_color="inverse", help="Descenso total medido desde la cota de rebose 885.75 msnm")
            if hidro["q_rebose_ls"] > 0:
                c4.metric("🌊 Caudal Rebose MG", f"{hidro['q_rebose_m3_s']:.2f} m³/s", delta=f"{hidro['q_rebose_ls']:,.0f} L/s hacia Puente Tona")
            elif bal and bal["q_neto_ls"] > 0:
                c4.metric("⚡ Tasa Neta Vaciado", f"{bal['q_neto_ls']:.0f} L/s", delta=f"{bal['vaciado_diario_m3']:,.0f} m³/día", delta_color="inverse", help=f"Velocidad neta de vaciado en las últimas {bal['horas']:.1f} horas. Salida Válvula CRC = Tasa Neta + Aporte Río Tona.")
            else:
                c4.metric("📐 Área Espejo", f"{hidro['area_ha']:.1f} ha", delta=f"{hidro['m3_por_cm']:.0f} m³/cm")
            
            # Tarjeta de Balance Dinámico en Tiempo Real (Derivada Batimétrica)
            if bal:
                st.markdown("---")
                st.markdown("### ⚖️ Balance Hídrico Dinámico en Vivo (Extracción CRC Bosconia)")
                st.caption(f"Descenso total de la maniobra y tasa neta reciente calculada con la telemetría de las últimas **{bal['horas']:.1f} horas**.")
                
                bc1, bc2, bc3, bc4 = st.columns(4)
                bc1.metric("📉 Descenso Total Maniobra", f"{abs(descenso_total_cm):.1f} cm", delta=f"{vol_entregado_total_m3:,.0f} m³ acumulados", delta_color="inverse", help="Descenso total desde que inició la descarga en 885.75 msnm")
                bc2.metric("⚡ Tasa Neta Reciente", f"{bal['q_neto_ls']:.0f} L/s", delta=f"{bal['vel_cm_dia']:+.1f} cm/día", delta_color="inverse", help=f"Velocidad neta de vaciado en las últimas {bal['horas']:.1f} horas")
                bc3.metric(f"🚰 Volumen Ventana ({bal['horas']:.1f}h)", f"{abs(bal['delta_v_m3']):,.0f} m³", delta=f"{bal['delta_cota_cm']:+.1f} cm en ventana")
                bc4.metric("⏳ Autonomía Real Dinámica", f"{bal['dias_autonomia']:.0f} Días" if bal['dias_autonomia'] else "N/A", help="Días restantes de agua continua hasta el Nivel Mínimo Técnico (841 msnm)")
                
                st.markdown(f"""
                <div style="background: rgba(0,80,115,0.06); padding: 14px 18px; border-radius: 8px; border-left: 4px solid #005073; margin-top: 10px; font-size: 13px; line-height: 1.5;">
                    <strong style="color: #005073; font-size: 14px;">⚖️ Principio Físico: Balance de Masas & Continuidad Hidráulica</strong><br>
                    <div style="margin-top: 6px; font-family: monospace; background: rgba(255,255,255,0.7); padding: 6px 10px; border-radius: 4px; border: 1px solid #cce0eb;">
                        <strong>Q_Salida_CRC_Bosconia</strong> = <strong>Q_Tasa_Neta_Vaciado ({bal['q_neto_ls']:.0f} L/s)</strong> + <strong>∑ Q_Afluentes_Cuenca_Tona (~{max(0, 400 - bal['q_neto_ls']):.0f} L/s)</strong>
                    </div>
                    <div style="margin-top: 8px;">
                        <strong>🌊 ¿Por qué el embalse desciende a menor tasa (~{bal['q_neto_ls']:.0f} L/s) de lo que sale a Bosconia (~400 L/s)?</strong><br>
                        El embalse no es un tanque cerrado estanco, sino un sistema dinámico regulador en balance de masas continuo:
                        <ul style="margin: 4px 0 6px 18px; padding: 0;">
                            <li><strong>Entradas (Afluentes de Cuenca):</strong> Recarga continua del <strong>Río Tona</strong> y sus quebradas tributarias directas: <strong>Quebrada Ranás</strong> (desemboca en fondo cola), <strong>Quebrada el Gualilo</strong> (mitad del vaso), <strong>Quebrada La Reforma</strong> (cercana a la presa/radar) y <strong>Quebrada Los Monos</strong> (litoral derecho norte, frente a La Reforma) con un aporte sumado estimado en cola de <strong>~{max(0, 400 - bal['q_neto_ls']):.0f} L/s</strong>.</li>
                            <li><strong>Salida (Consumo PTAP):</strong> Conducción y entrega por gravedad hacia la válvula <strong>CRC Bosconia</strong> (fijada en <strong>~400 L/s</strong>).</li>
                            <li><strong>Variación de Almacenamiento (ΔV/Δt):</strong> El vaso del embalse solo cede la diferencia neta (<strong>{bal['q_neto_ls']:.0f} L/s</strong>), acumulando un descenso real de <strong>{abs(descenso_total_cm):.1f} cm</strong> ({vol_entregado_total_m3:,.0f} m³ entregados a planta) desde el inicio de la descarga.</li>
                        </ul>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Módulo de Inteligencia de Cuenca (Trazabilidad y Atribución Hidrológica)
                q_afluente_calc_ls = max(0.0, 400.0 - bal['q_neto_ls'])
                df_cuenca_tona = obtener_precipitacion_cuenca_tona(fecha_inicio, fecha_fin)
                mostrar_modulo_atribucion_cuenca(df_cuenca_tona, q_afluente_calc_ls, bal['horas'])
                    
            st.info(f"📅 Última lectura: {row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
            mostrar_seccion_edv()
            
        else:
            p_val = float(row.get('precipitacion', 0)) if pd.notna(row.get('precipitacion')) else 0.0
            nombre, msg, color, vel = obtener_alerta(p_val, seleccion)
            
            st.markdown(f'''
            <div style="background-color:{color}; padding:16px; border-radius:12px; text-align:center; color:black; animation: blink {vel} infinite; border: 2px solid #333;">
                <h3 style="margin:0;">🚦 {nombre}</h3>
                <b>{msg}</b>
            </div>
            <style>
            @keyframes blink {{ 0%{{opacity:1}} 50%{{opacity:0.3}} 100%{{opacity:1}} }}
            </style>
            ''', unsafe_allow_html=True)
            st.write("")
            
            t_val = float(row.get('temperatura', 0)) if pd.notna(row.get('temperatura')) else 0.0
            h_val = float(row.get('humedad', 0)) if pd.notna(row.get('humedad')) else 0.0
            v_val = float(row.get('velocidad_viento', 0)) if pd.notna(row.get('velocidad_viento')) else 0.0
            d_val = float(row.get('direccion_viento', 0)) if pd.notna(row.get('direccion_viento')) else 0.0
            b_val = float(row.get('voltaje_bateria', 0)) if pd.notna(row.get('voltaje_bateria')) else 0.0
            
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            c1.metric("🌡️ Temp", f"{t_val:.1f} °C")
            c2.metric("🌧️ Precip", f"{p_val:.1f} mm")
            c3.metric("💧 Humedad", f"{h_val:.1f} %")
            c4.metric("💨 Viento", f"{v_val:.1f} km/h")
            c5.metric("🧭 Dir. Viento", f"{d_val:.0f}°")
            c6.metric("🔋 Voltaje", f"{b_val:.1f} V")
            
            st.info(f"📅 Última lectura: {row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
            
            if not df_hist.empty and 'temperatura' in df_hist.columns:
                t_series = pd.to_numeric(df_hist['temperatura'], errors='coerce').dropna()
                if not t_series.empty:
                    st.markdown("### 📊 Estadísticas del Período")
                    col1, col2, col3 = st.columns(3)
                    with col1: st.metric("🔽 Temp Mínima", f"{t_series.min():.1f}°C")
                    with col2: st.metric("🔼 Temp Máxima", f"{t_series.max():.1f}°C")
                    with col3: st.metric("📊 Temp Promedio", f"{t_series.mean():.1f}°C")
                    
            mostrar_ficha_geografica_estacion(seleccion)
    else:
        st.warning("⚠️ Sin datos recientes para esta estación.")

# ------------------------------------------------------------
# TAB 2: GESTIÓN EMBALSE & SEQUÍA 2026
# ------------------------------------------------------------
with tab_embalse_2026:
    st.subheader("🌊 Módulo de Gestión: Embalse Tona (Batimetría Multihaz 2026)")
    st.caption("Resolución centímetro a centímetro según Informe Técnico Oficial OPS 071 de 2026")
    
    cota_segura = get_cota_embalse_actual_segura()
            
    col_sim1, col_sim2 = st.columns([1, 2])
    with col_sim1:
        st.markdown("### 🎛️ Simulador de Extracción PTAP")
        q_sim = st.slider("Extracción hacia Plantas / PTAP (L/s):", min_value=0, max_value=2500, value=0, step=50, help="Simulador de extracción hacia PTAP Bosconia / Los Angelinos y escenarios de estrés hasta 2,500 L/s. Pon 0 para retención/vaciado cero.")
        cota_eval = st.number_input("Cota a Evaluar (msnm):", min_value=818.0, max_value=886.0, value=float(cota_segura), step=0.1)
        
        datos_eval = calcular_hidraulica_embalse(cota_eval, q_sim)
        
        st.markdown("---")
        st.markdown(f"""
        **📋 Parámetros Hidráulicos:**
        * **Volumen Útil Disponible:** `{datos_eval['volumen_util_hm3']:.3f} hm³`
        * **Volumen Muerto (Sedimentos):** `1.400 hm³`
        * **Volumen Total Acumulado:** `{datos_eval['volumen_total_hm3']:.3f} hm³`
        * **Volumen por cada Centímetro:** `{datos_eval['m3_por_cm']:.1f} m³/cm`
        * **Autonomía Estimada:** **`{datos_eval['autonomia_texto']}`**
        * **Caudal Rebose Morning Glory:** `{datos_eval['q_rebose_m3_s']:.2f} m³/s ({datos_eval['q_rebose_ls']:,.0f} L/s)`
        """)
        
        if datos_eval['q_rebose_ls'] > 0:
            st.success(f"🌊 **Excedente hídrico activo hacia Puente Tona:** Descargando {datos_eval['q_rebose_m3_s']:.2f} m³/s ({datos_eval['q_rebose_ls']:,.0f} L/s) por encima de la cota 885.75 msnm hacia la confluencia con el Río Suratá (mayor disponibilidad para PTAP Bosconia y futura PTAP Los Angelinos).")
        elif q_sim > 0:
            st.caption(f"💡 Extrayendo {q_sim} L/s ({q_sim*86.4:.0f} m³/día) sin aportes del río Tona.")
        else:
            st.info("ℹ️ Extracción en 0 L/s: El embalse se encuentra en retención o llenado natural.")
        
    with col_sim2:
        cotas_curva = np.linspace(818, 885.8, 100)
        vols_curva = [interpolar_volumen(c) for c in cotas_curva]
        
        fig_curva = go.Figure()
        fig_curva.add_trace(go.Scatter(x=vols_curva, y=cotas_curva, mode='lines', name='Curva Batimetría 2026', line=dict(color='#00CC96', width=3)))
        fig_curva.add_trace(go.Scatter(x=[datos_eval['volumen_total_hm3']], y=[cota_eval], mode='markers', name=f'Cota ({cota_eval:.2f} msnm)', marker=dict(size=13, color='#FF4B4B', symbol='diamond')))
        fig_curva.add_hline(y=NIVEL_MINIMO_TECNICO, line_dash="dash", line_color="orange", annotation_text="Mínimo Técnico: 841 msnm")
        fig_curva.add_hline(y=NIVEL_REBOSE_EMBALSE, line_dash="dash", line_color="red", annotation_text="Rebose Morning Glory: 885.75 msnm")
        fig_curva.update_layout(title="Curva Cota vs. Volumen 2026", xaxis_title="Volumen (hm³)", yaxis_title="Cota (msnm)", height=400, template='plotly_white')
        st.plotly_chart(fig_curva, use_container_width=True)

# ------------------------------------------------------------
# TAB 3: SERIES DE TIEMPO, ROSA DE VIENTOS Y DESCARGAS
# ------------------------------------------------------------
with tab_series:
    st.subheader(f"📈 Series de Tiempo — {seleccion.replace('_', ' ')}")
    
    if not df_hist.empty:
        if seleccion == "Embalse":
            df_enr_hist = enriquecer_datos_embalse(df_hist)
            
            # Gráfica 1: Cota de Nivel del Embalse
            fig_emb = px.line(df_enr_hist, x='timestamp', y='cota_embalse_msnm', title='🌊 Evolución de la Cota del Embalse (msnm)', labels={'cota_embalse_msnm': 'Cota (msnm)', 'timestamp': 'Fecha/Hora'})
            fig_emb.add_hline(y=NIVEL_REBOSE_EMBALSE, line_dash="dash", line_color="red", annotation_text="Rebose Morning Glory (885.75 msnm)")
            fig_emb.update_layout(height=320, template='plotly_white')
            st.plotly_chart(fig_emb, use_container_width=True)
            
            # Gráficas 2 y 3: Metros Cúbicos Consumidos y Caudal (L/s)
            col_emb1, col_emb2 = st.columns(2)
            with col_emb1:
                fig_m3 = px.area(df_enr_hist, x='timestamp', y='m3_consumidos_bosconia', title='📦 Volumen Entregado a CRC Bosconia (m³ Acumulados)', labels={'m3_consumidos_bosconia': 'Metros Cúbicos (m³)', 'timestamp': 'Fecha/Hora'}, color_discrete_sequence=['#00CC96'])
                fig_m3.update_layout(height=280, template='plotly_white')
                st.plotly_chart(fig_m3, use_container_width=True)
                
            with col_emb2:
                fig_q = go.Figure()
                fig_q.add_trace(go.Scatter(x=df_enr_hist['timestamp'], y=df_enr_hist['caudal_medio_bosconia_ls'], mode='lines', name='Caudal CRC Bosconia (L/s)', line=dict(color='#005073', width=2.5)))
                if df_enr_hist['caudal_rebose_ls'].max() > 0:
                    fig_q.add_trace(go.Scatter(x=df_enr_hist['timestamp'], y=df_enr_hist['caudal_rebose_ls'], mode='lines', name='Caudal Rebose Morning Glory (L/s)', line=dict(color='#FF4B4B', width=2, dash='dot')))
                fig_q.update_layout(title='⚡ Caudal CRC Bosconia & Rebose (L/s)', xaxis_title='Fecha/Hora', yaxis_title='Caudal (L/s)', height=280, template='plotly_white', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                st.plotly_chart(fig_q, use_container_width=True)
            
            # Bloque de Balance Volumétrico Bosconia en Vivo
            if not df_enr_hist.empty:
                st.markdown("### 💧 Balance Volumétrico & Extracción CRC Bosconia")
                m3_totales_periodo = df_enr_hist['m3_consumidos_bosconia'].max()
                c_ini_p = df_enr_hist['cota_embalse_msnm'].iloc[0]
                c_fin_p = df_enr_hist['cota_embalse_msnm'].iloc[-1]
                desc_tot_cm = (c_ini_p - c_fin_p) * 100.0
                
                t_ini_p = df_enr_hist['timestamp'].iloc[0]
                t_fin_p = df_enr_hist['timestamp'].iloc[-1]
                delta_s_p = max(1.0, (t_fin_p - t_ini_p).total_seconds())
                q_medio_ls = (m3_totales_periodo / delta_s_p) * 1000.0 if delta_s_p > 60 else 0.0
                
                cb1, cb2, cb3, cb4 = st.columns(4)
                cb1.metric("📦 Metros Cúbicos Entregados", f"{m3_totales_periodo:,.1f} m³", help="Volumen acumulado entregado a CRC Bosconia en el período visualizado")
                cb2.metric("⚡ Tasa Neta Vaciado", f"{q_medio_ls:,.1f} L/s", help="Tasa neta calculada por gradiente batimétrico")
                cb3.metric("📉 Descenso Acumulado", f"{desc_tot_cm:+.2f} cm")
                cb4.metric("🌊 Cota Calibrada Actual", f"{c_fin_p:.2f} msnm")
                
                st.markdown(f"""
                <div style="background: rgba(0,80,115,0.05); padding: 10px 14px; border-radius: 6px; border-left: 3px solid #005073; margin: 8px 0; font-size: 12.5px;">
                    ⚖️ <strong>Balance de Masas & Continuidad:</strong> Tasa neta calculada en el período: <strong>{q_medio_ls:,.0f} L/s</strong>.<br>
                    <code>Q_CRC_Bosconia (~400 L/s) = Tasa_Neta ({q_medio_ls:,.0f} L/s) + ∑ Q_Afluentes (~{max(0, 400 - q_medio_ls):,.0f} L/s)</code><br>
                    <em>El caudal afluente corresponde a la recarga continua de cuenca: <strong>Río Tona principal</strong> + microcuencas tributarias <strong>Quebrada Las Ranas, Quebrada Gualilo, Quebrada La Reforma y Quebrada Los Monos</strong>.</em>
                </div>
                """, unsafe_allow_html=True)
                
                df_bal_24h_vista = consolidar_balance_diario_embalse(df_enr_hist)
                if not df_bal_24h_vista.empty:
                    st.markdown("#### 📅 Consolidado por Bloques de 24 Horas Exactas:")
                    st.dataframe(df_bal_24h_vista, use_container_width=True)
        else:
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                fig_t = px.line(df_hist.sort_values('timestamp'), x='timestamp', y='temperatura', title='Temperatura (°C)')
                fig_t.update_layout(height=280, template='plotly_white')
                st.plotly_chart(fig_t, use_container_width=True)
            with col_g2:
                fig_p = px.bar(df_hist.sort_values('timestamp'), x='timestamp', y='precipitacion', title='Precipitación (mm)', color='precipitacion', color_continuous_scale='Blues')
                fig_p.update_layout(height=280, template='plotly_white')
                st.plotly_chart(fig_p, use_container_width=True)
                
            if 'humedad' in df_hist.columns:
                fig_h = px.line(df_hist.sort_values('timestamp'), x='timestamp', y='humedad', title='Humedad Relativa (%)')
                fig_h.update_layout(height=250, template='plotly_white')
                st.plotly_chart(fig_h, use_container_width=True)
                
            if 'direccion_viento' in df_hist.columns and 'velocidad_viento' in df_hist.columns:
                st.markdown("### 🧭 Rosa de los Vientos")
                df_v = df_hist.copy()
                df_v['direccion_viento'] = pd.to_numeric(df_v['direccion_viento'], errors='coerce')
                df_v['velocidad_viento'] = pd.to_numeric(df_v['velocidad_viento'], errors='coerce')
                df_v = df_v.dropna(subset=['direccion_viento', 'velocidad_viento'])
                df_v = df_v[(df_v['direccion_viento'] > 0) | (df_v['velocidad_viento'] > 0)]
                
                if not df_v.empty:
                    fig_rosa = px.bar_polar(df_v, r="velocidad_viento", theta="direccion_viento", color="velocidad_viento", color_continuous_scale='Viridis', title=f"Rosa de Vientos — {seleccion}")
                    fig_rosa.update_layout(height=400, template='plotly_white')
                    st.plotly_chart(fig_rosa, use_container_width=True)
                    
                    cv1, cv2, cv3 = st.columns(3)
                    with cv1: st.metric("💨 Vel. Promedio", f"{df_v['velocidad_viento'].mean():.1f} km/h")
                    with cv2: st.metric("💨 Vel. Máxima", f"{df_v['velocidad_viento'].max():.1f} km/h")
                    with cv3:
                        m_dir = df_v['direccion_viento'].mode()
                        st.metric("🧭 Dir. Predominante", f"{m_dir.iloc[0]:.0f}°" if not m_dir.empty else "N/A")
    
    # Descarga Oficial
    st.markdown("---")
    st.subheader("📥 Descarga Oficial de Datos")
    col_per1, col_per2 = st.columns(2)
    with col_per1: 
        opciones_periodo = ["Diario (24h)", "Semanal", "Mensual", "Semestral", "Anual"]
        op_periodo = st.radio("Período predefinido:", opciones_periodo, index=0)
    with col_per2: 
        op_custom = st.checkbox("📅 Personalizar fechas de descarga")
        
    hoy = datetime.now(colombia_tz)
    if op_custom:
        c_f1, c_f2 = st.columns(2)
        with c_f1: f_ini_d = st.date_input("Fecha Inicio:", value=hoy - timedelta(days=7), max_value=hoy)
        with c_f2: f_fin_d = st.date_input("Fecha Fin:", value=hoy, max_value=hoy)
        desc_periodo = f"Personalizado ({f_ini_d.strftime('%d/%m/%Y')} - {f_fin_d.strftime('%d/%m/%Y')})"
    else:
        dias_map = {"Diario (24h)": 1, "Semanal": 7, "Mensual": 30, "Semestral": 180, "Anual": 365}
        f_ini_d = hoy - timedelta(days=dias_map.get(op_periodo, 1))
        f_fin_d = hoy
        desc_periodo = f"{op_periodo} ({f_ini_d.strftime('%d/%m/%Y')} - {f_fin_d.strftime('%d/%m/%Y')})"
        
    st.info(f"📊 **Período seleccionado para descarga:** {desc_periodo}")
    if st.button("📥 Cargar datos para exportar", use_container_width=True):
        with st.spinner("🔄 Procesando datos históricos en BigQuery..."):
            df_d = get_historical_data_range(seleccion, f_ini_d, f_fin_d)
            if not df_d.empty:
                st.session_state['df_descarga'] = df_d
                st.session_state['periodo_descarga'] = desc_periodo
                st.success(f"✅ Datos listos: {len(df_d)} registros procesados")
            else:
                st.warning("⚠️ Sin datos para el rango seleccionado.")
                
    if 'df_descarga' in st.session_state:
        df_exp = st.session_state['df_descarga']
        per_exp = st.session_state['periodo_descarga']
        
        with st.expander("📊 Ver Resumen Estadístico"): 
            st.text(generar_resumen_estadistico(df_exp, seleccion))
            
        if seleccion == "Embalse" and 'temperatura' in df_exp.columns:
            df_enr_exp = enriquecer_datos_embalse(df_exp)
            df_bal_exp = consolidar_balance_diario_embalse(df_enr_exp)
            if not df_bal_exp.empty:
                st.markdown("### 📊 Balance Diario Consolidado hacia PTAP Bosconia (24 Horas Exactas):")
                st.dataframe(df_bal_exp, use_container_width=True)
            with st.expander("📋 Ver Matriz Detallada Enriquecida"):
                st.dataframe(df_enr_exp, use_container_width=True)
        else:
            with st.expander("📋 Ver Matriz de Datos"): 
                st.dataframe(df_exp, use_container_width=True)
                
        c_exp1, c_exp2 = st.columns(2)
        df_p = preparar_df_para_exportar(df_exp)
        csv_bytes = df_p.to_csv(index=False).encode('utf-8-sig')
        with c_exp1:
            try:
                xlsx_bytes = generar_excel_con_formato(df_exp, seleccion, per_exp)
                st.download_button("📊 Hoja de Cálculo (.xlsx)", xlsx_bytes, f"{seleccion}_{hoy.strftime('%Y%m%d_%H%M')}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
                st.caption("✅ Formato Excel oficial amb (con Hoja de Balance 24h)")
            except:
                st.download_button("📊 Hoja de Datos (CSV)", csv_bytes, f"{seleccion}_{hoy.strftime('%Y%m%d_%H%M')}.csv", "text/csv", use_container_width=True)
        with c_exp2:
            st.download_button("📝 Google Sheets (CSV)", csv_bytes, f"{seleccion}_{hoy.strftime('%Y%m%d_%H%M')}.csv", "text/csv", use_container_width=True)
            st.caption("📤 Compatible con Google Sheets")

# ------------------------------------------------------------
# TAB 4: ASISTENTE IA MIMAT-C
# ------------------------------------------------------------
with tab_ia:
    st.subheader("🤖 Asistente Inteligente MIMAT-C26")
    st.caption("Consultas hidrológicas, batimétricas y meteorológicas en lenguaje natural.")
    try:
        r_ping = requests.post(AGENTE_API_URL, json={"prompt": "ping"}, timeout=4)
        ia_online = r_ping.status_code == 200
    except:
        ia_online = False
        
    if ia_online: st.success("✅ Agente IA MIMAT-C conectado y operativo en Google Cloud Run")
    else: st.warning("⚠️ Agente IA no disponible.")
    
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])
        
    p_user = st.chat_input("Escribe tu pregunta sobre el embalse o las estaciones...")
    if p_user:
        st.session_state.messages.append({"role": "user", "content": p_user})
        with st.chat_message("user"): st.markdown(p_user)
        with st.chat_message("assistant"):
            with st.spinner("🤔 Analizando en BigQuery..."):
                try:
                    res = requests.post(AGENTE_API_URL, json={"prompt": p_user}, timeout=20).json()
                    ans = res.get("mensaje", "No se obtuvo respuesta.")
                    st.markdown(ans)
                    st.session_state.messages.append({"role": "assistant", "content": ans})
                except Exception as ex:
                    st.error(f"❌ Error: {ex}")
        st.rerun()
        
    if st.button("🗑️ Limpiar conversación", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ------------------------------------------------------------
# TAB 5: FUNDAMENTO MATEMÁTICO & AUDITORÍA DE INGENIERÍA
# ------------------------------------------------------------
with tab_matematica:
    st.subheader("📐 Fundamentos Físicos, Matemáticos y Normativos")
    st.caption("Transparencia metodológica y ecuaciones de ingeniería implementadas en MIMAT-C26")
    
    with st.expander("📊 1. Modelo de Batimetría Multihaz y Cálculo de Volúmenes (OPS 071-2026)", expanded=True):
        st.markdown(r"""
        El cálculo de volumen acumulado $V(h)$ y área superficial de espejo de agua $A(h)$ se basa en el **Levantamiento Batimétrico Multihaz de Alta Definición (Agosto 2026)** realizado con ecosonda NORBIT iWBMSc y perfilador acústico AML-3.
        
        Para garantizar precisión continua al centímetro ($0.01\text{ m}$) sin saltos discretos, se emplea interpolación continua monótona:
        $$\Delta V = V(h_2) - V(h_1) = \int_{h_1}^{h_2} A(h) \, dh$$
        
        **Matriz Oficial de Calibración 2026 (Tabla 9 del Informe):**
        """)
        df_matriz = pd.DataFrame({
            "Cota (msnm)": COTAS_REF,
            "Volumen Acumulado (hm³)": VOLUMENES_REF,
            "Volumen Acumulado (m³)": [f"{v*1e6:,.0f}" for v in VOLUMENES_REF],
            "Área Espejo (ha)": AREAS_REF,
            "Volumen por cada 1 cm (m³/cm)": [f"{a*10000*0.01:,.1f}" for a in AREAS_REF]
        })
        st.dataframe(df_matriz, use_container_width=True)
        st.caption("Normatividad: Cumplimiento Orden Especial Norma S-44 v6.1/2023 de la Organización Hidrográfica Internacional (IOH). Pérdida de volumen útil calculada en -0.8% anual, otorgando vigencia CNO de 5 años (2026-2031).")
        
    with st.expander("⚖️ 2. Balance Hídrico y Reconstrucción del Caudal del Río Tona"):
        st.markdown(r"""
        La conservación de masa en el vaso del embalse se rige por la ecuación diferencial de continuidad:
        $$\frac{dV}{dt} = Q_{\text{afluente (Tona)}} - Q_{\text{PTAP}} - Q_{\text{MorningGlory}} - Q_{\text{ecológico}}$$
        
        Despejando el caudal de aporte natural del río sin requerir sensor físico en el cauce:
        $$Q_{\text{Tona}} = A(h) \cdot \frac{\Delta h}{\Delta t} + Q_{\text{PTAP}} + Q_{\text{rebose}}$$
        """)
        
    with st.expander("⏳ 3. Autonomía Hídrica y Contingencia Sequía Súper Niño"):
        st.markdown(r"""
        La autonomía de suministro continuo para el Área Metropolitana de Bucaramanga hasta el Nivel Mínimo Técnico ($841.00\text{ msnm}$) se modela como:
        $$\text{Autonomía (Días)} = \frac{V_{\text{útil actual}} (\text{m}^3) - V(841.00)}{Q_{\text{PTAP}} (\text{m}^3/\text{s}) \times 86.400\text{ s/día}}$$
        """)
        
    with st.expander("📏 4. Calibración de Mira Virtual (Radar Sommer RQ-30)"):
        st.markdown(r"""
        Relación entre la lectura de radar no intrusivo y la regla limnimétrica física leída por el tomero a las 6:00 AM y 6:00 PM:
        $$h_{\text{mira\_real}} (\text{cm}) = h_{\text{RQ30}} (\text{cm}) - \text{Offset}_{\text{calibración}} (\text{cm})$$
        """)
        
    with st.expander("🌊 5. Curva Hidráulica Oficial del Rebosadero Morning Glory (885.75 msnm)"):
        st.markdown(r"""
        El rebosadero de excesos tipo tulipa (*Morning Glory*) inicia vertimiento en la cota de cresta **$885.75\text{ msnm}$** según planos de obra construida (Plano CEB-402AB-VER-030 Conalvías / INAR 2016).
        
        La ecuación polinómica oficial de calibración ($R^2 = 0.99938$) para una sobre-elevación $x = h - 885.75\text{ m}$ es:
        $$Q_{\text{Morning Glory}} (\text{m}^3/\text{s}) = -3.18926 x^4 + 23.22934 x^3 - 2.37295 x^2 + 103.93073 x - 1.29492$$
        
        **Matriz de Calibración de Vertimiento (Aforos Históricos):**
        * $h = 885.75\text{ msnm} \rightarrow x = 0.00\text{ m} \rightarrow Q_{\text{rebose}} = 0.00\text{ m}^3/\text{s}$ (Cresta del vertedero / Sin Rebose)
        * $h = 885.80\text{ msnm} \rightarrow x = 0.05\text{ m} \rightarrow Q_{\text{rebose}} = 3.90\text{ m}^3/\text{s}$ ($3.900\text{ L/s}$)
        * $h = 885.85\text{ msnm} \rightarrow x = 0.10\text{ m} \rightarrow Q_{\text{rebose}} = 9.10\text{ m}^3/\text{s}$ ($9.100\text{ L/s}$)
        * $h = 885.95\text{ msnm} \rightarrow x = 0.20\text{ m} \rightarrow Q_{\text{rebose}} = 19.58\text{ m}^3/\text{s}$ ($19.580\text{ L/s}$)
        """)

# ============================================================
# 9. SIDEBAR FOOTER
# ============================================================
st.sidebar.markdown("---")
st.sidebar.markdown(f"**Desarrollado por:** {AUTOR}")
st.sidebar.caption("Proyecto MIMAT-C26 • amb s.a. e.s.p.")

with st.sidebar.expander("🌊 Información del Embalse"):
    st.write(f"**Nivel de Rebose:** {NIVEL_REBOSE_EMBALSE} msnm")
    c_act = get_cota_embalse_actual_segura()
    st.write(f"**Cota Actual:** {c_act:.2f} msnm")
    st.write(f"**Volumen Útil (2026):** {VOLUMEN_UTIL_MAX_HM3} hm³")
    st.write(f"**Volumen Muerto:** {VOLUMEN_MUERTO_HM3} hm³")

with st.sidebar.expander("🤖 Estado del Agente IA"):
    st.write(f"**Servicio:** Cloud Run (MIMAT-C26)")
    st.write(f"**Estado:** {'✅ Activo' if ia_online else '⚠️ Desconectado'}")

with st.sidebar.expander("📏 Extensómetros (EDV)"):
    st.write("**Base de Datos Geotécnica:** BigQuery")
    st.write("- EDV Izquierdo: Activo")
    st.write("- EDV Derecho: Activo")

# ============================================================
# FIN DEL CÓDIGO — SISTEMA MIMAT-C26 (amb)
# ============================================================
