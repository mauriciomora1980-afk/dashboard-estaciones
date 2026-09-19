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
VOLUMEN_UTIL_MAX_HM3 = 12.11
VOLUMEN_MUERTO_HM3 = 1.40
def interpolar_volumen(c):
    return float(np.interp(c, COTAS_REF, VOLUMENES_REF))
def interpolar_area(c):
    return float(np.interp(c, COTAS_REF, AREAS_REF))
def calcular_hidraulica_embalse(cota: float, q_ptap_ls: float = 0.0):
    cota_val = max(818.0, min(float(cota), 886.00))
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
    
    return {
        "cota": cota_val,
        "volumen_total_hm3": vol_total_hm3,
        "volumen_util_hm3": vol_util_hm3,
        "porcentaje_util": porcentaje_util,
        "area_ha": area_ha,
        "m3_por_cm": m3_por_cm,
        "dias_autonomia": dias_autonomia,
        "autonomia_texto": autonomia_texto,
        "excedente_rebose": excedente_rebose
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
# 4. CLIENTE BIGQUERY CON ITERADOR NATIVO (SIN DB-DTYPES)
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
            c = float(df_emb.iloc[0].get('temperatura', 885.80))
            if 818.0 <= c <= 886.0:
                return c
    except:
        pass
    return 885.80
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
periodos_grafico = {
    "Últimas 24 horas": 24,
    "Últimos 3 días": 72,
    "Últimos 7 días": 168,
    "Últimos 15 días": 360,
    "Último mes": 720
}
if seleccion == "Embalse":
    p_sel = st.sidebar.selectbox("Período histórico:", list(periodos_grafico.keys()))
    horas = periodos_grafico[p_sel]
else:
    horas = st.sidebar.slider("⏱️ Horas históricas:", 1, 168, 24, step=1)
fecha_fin = datetime.now(colombia_tz)
fecha_inicio = fecha_fin - timedelta(hours=horas)
with st.spinner("🔄 Consultando telemetría en tiempo real..."):
    df_actual = get_last_reading(seleccion)
    df_hist = get_historical_data_range(seleccion, fecha_inicio, fecha_fin)
# ============================================================
# 6. EXPORTACIÓN Y EXCEL OPENPYXL
# ============================================================
def preparar_df_para_exportar(df):
    df_export = df.copy()
    if 'timestamp' in df_export.columns:
        df_export['timestamp'] = df_export['timestamp'].dt.tz_localize(None)
    return df_export
def generar_excel_con_formato(df, nombre_estacion, periodo_descripcion):
    df_export = preparar_df_para_exportar(df)
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_export.to_excel(writer, sheet_name='Datos', index=False)
        workbook = writer.book
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
            max_len = 0
            col_letter = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_len: max_len = len(str(cell.value))
                except: pass
            worksheet.column_dimensions[col_letter].width = min(max_len + 3, 50)
        
        metadata = pd.DataFrame({
            'Propiedad': ['Sistema', 'Proyecto', 'Estación', 'Período', 'Fecha exportación', 'Total registros', 'Responsable'],
            'Valor': [SISTEMA, "MIMAT-C26", nombre_estacion, periodo_descripcion, datetime.now(colombia_tz).strftime('%Y-%m-%d %H:%M:%S'), len(df_export), AUTOR]
        })
        metadata.to_excel(writer, sheet_name='Metadatos', index=False)
        m_sheet = writer.sheets['Metadatos']
        for col in range(1, 3):
            cell = m_sheet.cell(row=1, column=col)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
            
    return output.getvalue()
def generar_resumen_estadistico(df):
    if df.empty: return "No hay datos disponibles"
    resumen = [
        "📊 RESUMEN ESTADÍSTICO — MIMAT-C26 (amb)",
        "=" * 45,
        f"📋 Generado el {datetime.now(colombia_tz).strftime('%Y-%m-%d %H:%M')}",
        ""
    ]
    cols = ['temperatura', 'precipitacion', 'humedad', 'presion', 'velocidad_viento', 'direccion_viento', 'voltaje_bateria']
    for col in cols:
        if col in df.columns:
            datos = pd.to_numeric(df[col], errors='coerce').dropna()
            if not datos.empty:
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
            cota_actual = float(raw_c) if pd.notna(raw_c) and float(raw_c) > 800 else 885.80
            hidro = calcular_hidraulica_embalse(cota_actual, q_ptap_ls=0.0)
            
            if hidro["excedente_rebose"] >= 0:
                st.markdown(f"""
                <div class="alert-box alert-orange">
                    <span style="font-size: 24px;">🌊</span>
                    <div>
                        <strong>ESTADO: REBOSE ACTIVO (+{hidro['excedente_rebose']:.2f} msnm)</strong><br>
                        El embalse supera la cota de vertimiento (885.75 msnm). Descarga por Morning Glory.
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="alert-box alert-green">
                    <span style="font-size: 24px;">🟢</span>
                    <div>
                        <strong>ESTADO: OPERACIÓN NORMAL</strong><br>
                        Cota en {cota_actual:.2f} msnm ({abs(hidro['excedente_rebose']):.2f} msnm bajo rebose). Capacidad útil al {hidro['porcentaje_util']:.1f}%.
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("🌊 Cota Actual", f"{cota_actual:.2f} msnm", delta=f"{hidro['excedente_rebose']:+.2f} msnm")
            c2.metric("💧 Volumen Útil", f"{hidro['volumen_util_hm3']:.2f} hm³", delta=f"{hidro['porcentaje_util']:.1f}% útil")
            c3.metric("⏳ Autonomía PTAP", "Simulador (Tab 2)", help="Actualmente sin extracción activa hacia PTAP. Usa la pestaña de Gestión de Embalse para simular diferentes caudales.")
            c4.metric("📐 Área Espejo", f"{hidro['area_ha']:.1f} ha")
            
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
        q_sim = st.slider("Extracción hacia Plantas (L/s):", min_value=0, max_value=2500, value=0, step=50, help="Pon 0 para condición sin bombeo/válvula cerrada")
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
        """)
        
        if q_sim > 0:
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
            fig_emb = px.line(df_hist.sort_values('timestamp'), x='timestamp', y='temperatura', title='Evolución Cota Embalse (msnm)', labels={'temperatura': 'msnm', 'timestamp': 'Fecha/Hora'})
            fig_emb.add_hline(y=NIVEL_REBOSE_EMBALSE, line_dash="dash", line_color="red", annotation_text="Rebose Morning Glory")
            fig_emb.update_layout(height=350, template='plotly_white')
            st.plotly_chart(fig_emb, use_container_width=True)
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
    with col_per1: op_periodo = st.radio("Período:", ["Diario", "Semanal", "Mensual", "Semestral", "Anual"], index=0)
    with col_per2: op_custom = st.checkbox("📅 Personalizar fechas de descarga")
    hoy = datetime.now(colombia_tz)
    if op_custom:
        c_f1, c_f2 = st.columns(2)
        with c_f1: f_ini_d = st.date_input("Fecha Inicio:", value=hoy - timedelta(days=30), max_value=hoy)
        with c_f2: f_fin_d = st.date_input("Fecha Fin:", value=hoy, max_value=hoy)
        desc_periodo = f"Personalizado ({f_ini_d.strftime('%d/%m/%Y')} - {f_fin_d.strftime('%d/%m/%Y')})"
    else:
        dias_map = {"Diario": 1, "Semanal": 7, "Mensual": 30, "Semestral": 180, "Anual": 365}
        f_ini_d = hoy - timedelta(days=dias_map[op_periodo])
        f_fin_d = hoy
        desc_periodo = f"{op_periodo} ({f_ini_d.strftime('%d/%m/%Y')} - {f_fin_d.strftime('%d/%m/%Y')})"
        
    st.info(f"📊 **Período seleccionado para descarga:** {desc_periodo}")
    if st.button("📥 Cargar datos para exportar", use_container_width=True):
        with st.spinner("🔄 Procesando datos históricos en BigQuery..."):
            df_d = get_historical_data_range(seleccion, f_ini_d, f_fin_d)
            if not df_d.empty:
                st.session_state['df_descarga'] = df_d
                st.session_state['periodo_descarga'] = desc_periodo
                st.success(f"✅ Datos listos: {len(df_d)} registros")
            else:
                st.warning("⚠️ Sin datos para el rango seleccionado.")
                
    if 'df_descarga' in st.session_state:
        df_exp = st.session_state['df_descarga']
        per_exp = st.session_state['periodo_descarga']
        with st.expander("📊 Ver Resumen Estadístico"): st.text(generar_resumen_estadistico(df_exp))
        with st.expander("📋 Ver Matriz de Datos"): st.dataframe(df_exp, use_container_width=True)
        c_exp1, c_exp2 = st.columns(2)
        df_p = preparar_df_para_exportar(df_exp)
        csv_bytes = df_p.to_csv(index=False).encode('utf-8-sig')
        with c_exp1:
            try:
                xlsx_bytes = generar_excel_con_formato(df_exp, seleccion, per_exp)
                st.download_button("📊 Hoja de Cálculo (.xlsx)", xlsx_bytes, f"{seleccion}_{hoy.strftime('%Y%m%d_%H%M')}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
                st.caption("✅ Formato Excel oficial con metadatos amb")
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
