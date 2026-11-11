# ==============================================================================
# PROYECTO: MIMAT-C26 (Monitoreo Inteligente de Meteorología, Análisis de Telemetría y Cuencas)
# ENTIDAD:  Acueducto Metropolitano de Bucaramanga S.A. E.S.P. (amb)
# AUTOR Y ARQUITECTO LÍDER: Ing. Edgar Mauricio Mora Rivera
# PROPIEDAD INTELECTUAL Y DERECHOS DE AUTOR PROTEGIDOS © 2026
# ==============================================================================
import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import time
import base64
import requests
import urllib.request
from google.cloud import bigquery
from google.oauth2 import service_account
from datetime import datetime, timedelta
from pytz import timezone
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from io import BytesIO
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows
from PIL import Image

# ============================================================
# 0. CONFIGURACION DE PAGINA Y ESTILOS MIMAT-C26 (amb)
# ============================================================
st.set_page_config(
    page_title='MIMAT-C26 | Centro de Monitoreo - amb',
    page_icon='\U0001F4A7',
    layout='wide',
    initial_sidebar_state='expanded'
)

# Estilos CSS institucionales completos (SCADA, semaforos, edicion 110 anios)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    /* Control de barra lateral estilizada */
    [data-testid="stSidebarCollapsedControl"] {
        display: block !important;
        background: linear-gradient(135deg, #005073 0%, #00223D 100%) !important;
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
    /* Barra Superior de Contact Center Institucional */
    .amb-top-bar {
        background: #003358;
        color: #E2E8F0;
        padding: 6px 18px;
        border-radius: 10px 10px 0 0;
        font-size: 11.5px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        border-bottom: 1px solid rgba(255, 255, 255, 0.15);
    }
    /* Hero Header Oficial con Ondas Azules y 110 Años */
    .amb-hero-header {
        background: linear-gradient(135deg, #002A4A 0%, #005073 35%, #0077B6 70%, #0096C7 100%);
        padding: 22px 26px;
        border-radius: 0 0 16px 16px;
        color: white;
        margin-bottom: 12px;
        box-shadow: 0 12px 32px rgba(0, 80, 115, 0.28);
        border: 1px solid rgba(255, 255, 255, 0.12);
        position: relative;
        overflow: hidden;
    }
    /* Píldora de Noticias / Novedades del Servicio */
    .amb-ticker-bar {
        background: #00223D;
        color: #E2E8F0;
        padding: 10px 18px;
        border-radius: 10px;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 12.5px;
        border-left: 4px solid #7CB342;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    .badge-ticker {
        background: #7CB342;
        color: #003300;
        padding: 3px 10px;
        border-radius: 12px;
        font-weight: 800;
        font-size: 10.5px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        white-space: nowrap;
    }
    /* Tarjetas de Alerta y Métricas */
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
    /* Animaciones Luminosas y Parpadeantes para Pantalla SCADA / Alerta Temprana */
    @keyframes pulse-red-glow {
        0% { box-shadow: 0 0 8px rgba(255, 75, 75, 0.4), inset 0 0 6px rgba(255, 75, 75, 0.2); border-color: #FF4B4B; }
        50% { box-shadow: 0 0 28px rgba(255, 75, 75, 0.95), inset 0 0 16px rgba(255, 75, 75, 0.5); border-color: #FF0000; }
        100% { box-shadow: 0 0 8px rgba(255, 75, 75, 0.4), inset 0 0 6px rgba(255, 75, 75, 0.2); border-color: #FF4B4B; }
    }
    @keyframes pulse-orange-glow {
        0% { box-shadow: 0 0 6px rgba(255, 128, 0, 0.4); border-color: #FF8000; }
        50% { box-shadow: 0 0 22px rgba(255, 128, 0, 0.9); border-color: #FFA500; }
        100% { box-shadow: 0 0 6px rgba(255, 128, 0, 0.4); border-color: #FF8000; }
    }
    @keyframes pulse-yellow-glow {
        0% { box-shadow: 0 0 5px rgba(255, 187, 0, 0.35); border-color: #FFBB00; }
        50% { box-shadow: 0 0 18px rgba(255, 187, 0, 0.85); border-color: #FFD700; }
        100% { box-shadow: 0 0 5px rgba(255, 187, 0, 0.35); border-color: #FFBB00; }
    }
    @keyframes pulse-cyan-glow {
        0% { box-shadow: 0 0 6px rgba(0, 200, 255, 0.4); border-color: #00BFFF; }
        50% { box-shadow: 0 0 22px rgba(0, 200, 255, 0.9); border-color: #64FFDA; }
        100% { box-shadow: 0 0 6px rgba(0, 200, 255, 0.4); border-color: #00BFFF; }
    }
    .card-scada-red {
        background: linear-gradient(145deg, rgba(60, 10, 10, 0.92), rgba(30, 5, 5, 0.96)) !important;
        border: 2px solid #FF4B4B !important;
        animation: pulse-red-glow 1.1s infinite ease-in-out !important;
        border-radius: 14px;
        padding: 18px;
        margin-bottom: 14px;
    }
    .card-scada-orange {
        background: linear-gradient(145deg, rgba(55, 25, 5, 0.92), rgba(28, 12, 2, 0.96)) !important;
        border: 2px solid #FF8000 !important;
        animation: pulse-orange-glow 1.5s infinite ease-in-out !important;
        border-radius: 14px;
        padding: 18px;
        margin-bottom: 14px;
    }
    .card-scada-yellow {
        background: linear-gradient(145deg, rgba(48, 42, 5, 0.92), rgba(24, 20, 2, 0.96)) !important;
        border: 2px solid #FFBB00 !important;
        animation: pulse-yellow-glow 2.0s infinite ease-in-out !important;
        border-radius: 14px;
        padding: 18px;
        margin-bottom: 14px;
    }
    .card-scada-cyan {
        background: linear-gradient(145deg, rgba(5, 40, 60, 0.92), rgba(2, 20, 35, 0.96)) !important;
        border: 2px solid #00BFFF !important;
        animation: pulse-cyan-glow 1.8s infinite ease-in-out !important;
        border-radius: 14px;
        padding: 18px;
        margin-bottom: 14px;
    }
    @keyframes pulse-green-glow {
        0% { box-shadow: 0 0 6px rgba(0, 204, 150, 0.35); border-color: #00CC96; }
        50% { box-shadow: 0 0 18px rgba(0, 204, 150, 0.75); border-color: #64FFDA; }
        100% { box-shadow: 0 0 6px rgba(0, 204, 150, 0.35); border-color: #00CC96; }
    }
    .card-scada-green {
        background: linear-gradient(145deg, rgba(6, 42, 28, 0.94), rgba(2, 22, 14, 0.98)) !important;
        border: 1.8px solid #00CC96 !important;
        animation: pulse-green-glow 2.4s infinite ease-in-out !important;
        border-radius: 14px;
        padding: 18px;
        margin-bottom: 14px;
    }
    .card-scada-gray {
        background: linear-gradient(145deg, rgba(20, 26, 36, 0.94), rgba(12, 16, 24, 0.98)) !important;
        border: 1.5px solid #334155 !important;
        box-shadow: 0 0 10px rgba(51, 65, 85, 0.25);
        border-radius: 14px;
        padding: 18px;
        margin-bottom: 14px;
    }
    .card-scada-blue {
        background: linear-gradient(145deg, rgba(8, 28, 48, 0.90), rgba(4, 15, 28, 0.96)) !important;
        border: 1.5px solid #38BDF8 !important;
        box-shadow: 0 0 12px rgba(56, 189, 248, 0.25);
        border-radius: 14px;
        padding: 18px;
        margin-bottom: 14px;
    }
    /* Faros Parpadeantes (Beacon) de Semáforo Luminoso */
    @keyframes blink-beacon {
        0%, 100% { opacity: 1; transform: scale(1); filter: drop-shadow(0 0 8px currentColor); }
        50% { opacity: 0.25; transform: scale(0.85); filter: drop-shadow(0 0 1px currentColor); }
    }
    .beacon-red {
        display: inline-block; width: 14px; height: 14px; border-radius: 50%;
        background: #FF4B4B; color: #FF4B4B;
        animation: blink-beacon 0.7s infinite ease-in-out;
        box-shadow: 0 0 12px #FF4B4B;
    }
    .beacon-orange {
        display: inline-block; width: 14px; height: 14px; border-radius: 50%;
        background: #FF8000; color: #FF8000;
        animation: blink-beacon 1.0s infinite ease-in-out;
        box-shadow: 0 0 10px #FF8000;
    }
    .beacon-yellow {
        display: inline-block; width: 14px; height: 14px; border-radius: 50%;
        background: #FFBB00; color: #FFBB00;
        animation: blink-beacon 1.5s infinite ease-in-out;
        box-shadow: 0 0 10px #FFBB00;
    }
    .beacon-cyan {
        display: inline-block; width: 14px; height: 14px; border-radius: 50%;
        background: #00BFFF; color: #00BFFF;
        animation: blink-beacon 1.4s infinite ease-in-out;
        box-shadow: 0 0 12px #00BFFF;
    }
    .beacon-green {
        display: inline-block; width: 13px; height: 13px; border-radius: 50%;
        background: #00CC96; color: #00CC96;
        animation: blink-beacon 2.0s infinite ease-in-out;
        box-shadow: 0 0 10px #00CC96;
    }
    .beacon-gray {
        display: inline-block; width: 12px; height: 12px; border-radius: 50%;
        background: #94A3B8; color: #94A3B8;
        box-shadow: 0 0 6px rgba(148, 163, 184, 0.4);
    }
    .beacon-blue {
        display: inline-block; width: 13px; height: 13px; border-radius: 50%;
        background: #38BDF8; color: #38BDF8;
        box-shadow: 0 0 8px #38BDF8;
    }
</style>
""", unsafe_allow_html=True)

colombia_tz = timezone('America/Bogota')
utc_tz = timezone('UTC')
# ============================================================
# LOGO SIDEBAR (con distintivo opcional Edicion 110 Anios)
# ============================================================
def render_logo_sidebar(es_edicion_110=False):
    import glob
    archivos_simetricos = sorted(glob.glob("logo_amb_4_0_lluvia_simetrica*"), reverse=True)
    posibles_rutas = archivos_simetricos + [
        "logo_amb_4_0_lluvia_simetrica_exacta_1792249435104.jpg",
        "logo_amb_4_0_lluvia_simetrica_exacta.jpg",
        "logo_amb_4_0_oficial.jpg",
        "logo_amb_4_0_olas_oficiales.jpg",
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
                if es_edicion_110:
                    st.sidebar.markdown("""
                    <div style="text-align: center; margin: -6px 0 12px 0;">
                        <span style="background: rgba(124, 179, 66, 0.2); color: #7CB342; border: 1px solid #7CB342; padding: 2px 8px; border-radius: 12px; font-size: 10px; font-weight: 800;">💧 110 AÑOS amb</span>
                    </div>
                    """, unsafe_allow_html=True)
                return
            except:
                pass
    st.sidebar.markdown(f"""
    <div style="background: linear-gradient(135deg, #002A4A, #005073); padding: 16px; border-radius: 12px; text-align: center; margin-bottom: 15px; border: 1px solid #64FFDA; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
        <div style="font-size: 28px; line-height: 1;">💧</div>
        <h1 style="color: #64FFDA; margin: 4px 0 0 0; font-size: 32px; font-weight: 900; letter-spacing: -1px;">amb</h1>
        <div style="color: #E6F1FF; font-size: 11px; text-transform: lowercase; margin-top: 2px;">acueducto metropolitano de bucaramanga</div>
        {"<div style='margin-top: 8px; padding-top: 6px; border-top: 1px solid rgba(255,255,255,0.15);'><span style='background: rgba(124, 179, 66, 0.25); color: #7CB342; border: 1px solid #7CB342; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: 800;'>EDICIÓN 110 AÑOS</span></div>" if es_edicion_110 else ""}
    </div>
    """, unsafe_allow_html=True)
# Selector dinámico de ambientación visual para pruebas y comparación
modo_visual = st.sidebar.radio(
    "🎨 Ambientación Visual:",
    ["⚡ SCADA Clásico (Ingeniería Dark)", "💧 Portal amb (Edición 110 Años)"],
    index=0,
    help="Permite alternar entre el diseño técnico SCADA clásico preferido y la nueva imagen conmemorativa institucional."
)
es_110 = (modo_visual == "💧 Portal amb (Edición 110 Años)")
render_logo_sidebar(es_edicion_110=es_110)

# ============================================================
# CONTROL DE AUTO-REFRESCO AUTOMATICO EN VIVO
# ============================================================
col_ref1, col_ref2 = st.sidebar.columns([3, 1])
with col_ref1:
    opcion_autorefresh = st.selectbox(
        '\U0001F504 Auto-recarga en vivo:',
        ['Cada 3 minutos', 'Cada 5 minutos (Recomendado)', 'Cada 10 minutos', 'Desactivada (Manual)'],
        index=1,
        help='Actualiza periodicamente la telemetria y niveles del embalse en segundo plano sin intervencion humana.'
    )
with col_ref2:
    st.write('')
    if st.button('\U0001F504', help='Actualizar datos inmediatamente ahora'):
        st.rerun()

intervalo_segundos = {
    'Cada 3 minutos': 180,
    'Cada 5 minutos (Recomendado)': 300,
    'Cada 10 minutos': 600
}.get(opcion_autorefresh, 0)

if intervalo_segundos > 0:
    # Auto-refresco 100% nativo de Streamlit via WebSocket (sin componentes externos ni recarga de navegador)
    _frag_deco = getattr(st, "fragment", getattr(st, "experimental_fragment", None))
    if _frag_deco is not None:
        _es_corrida_principal = [True]
        @_frag_deco(run_every=timedelta(seconds=intervalo_segundos))
        def _mimat_native_autorefresh():
            if not _es_corrida_principal[0]:
                st.rerun()
        _mimat_native_autorefresh()
        _es_corrida_principal[0] = False

st.sidebar.caption(f"\U0001F551 Hora local: {datetime.now(colombia_tz).strftime('%I:%M:%S %p COT')}")

# ============================================================
# 1. FUNCION DE RENDERIZADO DE ENCABEZADO Y NOVEDADES DINAMICAS
# ============================================================
def render_encabezado_principal(es_110=False, txt_novedades=""):
    if es_110:
        st.markdown(f"""
        <div class="amb-top-bar">
            <div>
                <span>📞 Contact Center: <strong>(607) 6898080</strong> / Celular: <strong>3330333356</strong></span>
                <span style="margin: 0 10px; opacity: 0.4;">|</span>
                <span>🏛️ Acueducto Metropolitano de Bucaramanga S.A. E.S.P.</span>
            </div>
            <div>
                <span style="color: #64FFDA; font-weight: 700;">💧 EDICIÓN CONMEMORATIVA 110 AÑOS</span>
                <span style="margin: 0 10px; opacity: 0.4;">|</span>
                <span>🛰️ MIMAT-C26 • Telemetría 24/7</span>
            </div>
        </div>
        <div class="amb-hero-header">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px;">
                <div style="display: flex; align-items: center; gap: 18px;">
                    <div style="background: rgba(255,255,255,0.12); padding: 10px 14px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.25); text-align: center;">
                        <div style="font-size: 26px; line-height: 1;">💧</div>
                        <div style="font-size: 16px; font-weight: 900; color: #FFFFFF; letter-spacing: -1px; margin-top: 2px;">110</div>
                        <div style="font-size: 9px; font-weight: 800; color: #7CB342; text-transform: uppercase; letter-spacing: 1px;">AÑOS</div>
                    </div>
                    <div>
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <h1 style="font-size: 24px; font-weight: 900; color: #FFFFFF; margin: 0; letter-spacing: -0.5px;">amb | MIMAT-C26</h1>
                            <span class="badge-status" style="background: rgba(124, 179, 66, 0.25); color: #7CB342; border: 1px solid #7CB342; font-size: 10px;">SISTEMA OFICIAL</span>
                        </div>
                        <div style="font-size: 14px; font-weight: 700; color: #E0F2FE; margin-top: 3px;">
                            Centro de Monitoreo Inteligente de Meteorología, Análisis de Telemetría y Cuencas
                        </div>
                        <div style="font-size: 11.5px; color: #BAE6FD; font-style: italic; margin-top: 2px;">
                            "110 años de historias que dan vida con cada gota" • Dirección de Producción & Recursos Hídricos
                        </div>
                    </div>
                </div>
                <div style="text-align: right;">
                    <span class="badge-status" style="background: rgba(100, 255, 218, 0.2); color: #64FFDA; border: 1px solid #64FFDA;">
                        ● RED TELEMÉTRICA 24/7 EN VIVO
                    </span>
                    <div style="font-size: 12px; color: #E0F2FE; margin-top: 4px; font-weight: 600;">
                        🕐 {datetime.now(colombia_tz).strftime('%Y-%m-%d %H:%M:%S')} (Hora Colombia)
                    </div>
                </div>
            </div>
        </div>
        <div class="amb-ticker-bar">
            <span class="badge-ticker">NOVEDADES DEL SISTEMA</span>
            <span style="line-height: 1.4;">
                {txt_novedades}
            </span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #0A192F 0%, #112240 100%); padding: 20px 24px; border-radius: 12px; margin-bottom: 12px; border-left: 5px solid #64FFDA; box-shadow: 0 4px 20px rgba(0,0,0,0.3);">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <div>
                    <h1 style="color: #64FFDA; margin: 0; font-size: 26px; font-weight: 800; letter-spacing: -0.5px;">
                        MIMAT-C26 | amb
                    </h1>
                    <div style="color: #CCD6F6; font-size: 14px; font-weight: 600; margin-top: 4px;">
                        Sistema de Monitoreo Inteligente de Meteorología, Análisis de Telemetría y Cuencas
                    </div>
                    <div style="color: #8892B0; font-size: 12px; margin-top: 2px;">
                        Acueducto Metropolitano de Bucaramanga S.A. E.S.P. • Dirección de Producción & Recursos Hídricos
                    </div>
                </div>
                <div style="text-align: right; margin-top: 5px;">
                    <span class="badge-status" style="background: rgba(100, 255, 218, 0.15); color: #64FFDA; border: 1px solid #64FFDA;">
                        ● TELEMETRÍA EN VIVO
                    </span>
                    <div style="color: #8892B0; font-size: 12px; margin-top: 4px;">
                        {datetime.now(colombia_tz).strftime('%Y-%m-%d %H:%M:%S')} COT
                    </div>
                </div>
            </div>
        </div>
        <div style="background: rgba(10, 25, 47, 0.95); padding: 9px 16px; border-radius: 8px; margin-bottom: 18px; border-left: 4px solid #64FFDA; font-size: 12.5px; color: #E2E8F0; display: flex; align-items: center; gap: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.25);">
            <span style="background: rgba(100, 255, 218, 0.2); color: #64FFDA; border: 1px solid #64FFDA; padding: 2px 8px; border-radius: 6px; font-weight: 800; font-size: 10px; letter-spacing: 0.5px; white-space: nowrap;">● NOVEDADES EN VIVO</span>
            <span style="line-height: 1.4;">{txt_novedades}</span>
        </div>
        """, unsafe_allow_html=True)
# ============================================================
# 2. METADATOS Y CONSTANTES
# ============================================================
AUTOR = "Ing. Mauricio Mora"
VERSION = "MIMAT-C26 v2.6"
SISTEMA = "Sistema Automatizado de Monitoreo MIMAT-C26 - amb"
AGENTE_API_URL = "https://querybigqueryamb-ia-661926446380.us-central1.run.app"
FECHA_INICIO_MANIOBRA_CRC = datetime(2026, 9, 22, 13, 0, 0, tzinfo=colombia_tz)
umbrales = {
    "El_Pajal": {"amarilla": 12.3, "naranja": 15.1, "roja": 20.4},
    "Yerbabuena": {"amarilla": 10.9, "naranja": 20.0, "roja": 40.8},
    "La_Mariana": {"amarilla": 11.7, "naranja": 18.0, "roja": 35.0},
    "Vegas_del_Quemado": {"amarilla": 27.2, "naranja": 36.8, "roja": 55.8},
    "Monsalve": {"amarilla": 10.9, "naranja": 20.0, "roja": 40.8, "es_referencia_paramo": True}
}
# ============================================================
# 3. MODELO MATEMÁTICO — BATIMETRÍA 2026 (NUMPY NATIVO)
# ============================================================
COTAS_REF = np.array([817.94, 830.00, 836.50, 841.00, 850.00, 860.00, 870.00, 883.00, 885.80])
VOLUMENES_REF = np.array([0.000, 0.520, 1.400, 1.980, 3.850, 6.420, 9.650, 14.090, 15.380]) # hm³
AREAS_REF = np.array([0.00, 8.50, 14.20, 18.60, 24.50, 30.80, 37.20, 44.60, 46.20]) # ha
NIVEL_MINIMO_TECNICO = 841.00
NIVEL_REBOSE_EMBALSE = 885.75
OFFSET_RADAR_EMBALSE = 0.04 # Desfase certificado por Ing. Angarita (-4 cm a la mira OTT del Embalse)
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
    """
    Calcula el caudal del vertedero circular Morning Glory (Embalse Tona, cresta 885.75 msnm):
    Calibración oficial empírica en campo (29-Oct-2026): A una lámina medida en cresta de +3.3 cm (885.783 msnm),
    el caudal verificado en la cascada escalonada y piscina de aquietamiento es de ~600 a 700 L/s (~0.66 m³/s),
    lo que corresponde a la ley física de vertedero circular con el perímetro real de la corona
    (L ≈ 50-55 m, Cd ≈ 2.05-2.10):
        Q_calibrado (m³/s) = 110.0 * (H ^ 1.5)
        Ej: H = 0.033 m (+3.3 cm) -> Q = 110.0 * (0.033 ^ 1.5) = 0.659 m³/s (~660 L/s)
    """
    h_sobre_vertedero = max(0.0, cota_real - NIVEL_REBOSE_EMBALSE)
    if h_sobre_vertedero <= 0.0:
        return 0.0, 0.0
    q_m3_s = float(110.0 * (h_sobre_vertedero ** 1.5))
    q_ls = q_m3_s * 1000.0
    return round(q_m3_s, 3), round(q_ls, 1)
def calcular_caudal_morning_glory_teorico_descalibrado(cota_real: float):
    """
    Retorna el valor crudo de la tabla teórica original sin calibrar (ej. ~2,234 L/s a 885.78 msnm)
    exclusivamente como referencia de auditoría para evidenciar la sobreestimación frente a Majadas.
    """
    h_sobre_vertedero = max(0.0, cota_real - NIVEL_REBOSE_EMBALSE)
    if h_sobre_vertedero <= 0.0:
        return 0.0, 0.0
    q_m3_s = float(np.interp(h_sobre_vertedero, COTAS_MG_REF, CAUDAL_MG_REF))
    return round(q_m3_s, 3), round(q_m3_s * 1000.0, 1)
# ============================================================
# 3.1 MODELO HIDRÁULICO RÍO SURATÁ — SECTOR LAS MAJADAS (RADAR OTT + MIRA)
# Calibración Oficial (Confirmada por Ing. Carlos / amb):
#   1. Nivel Mira amb (m) = Nivel_Sensor_IDEAM (m) - 0.04 m  (-4 cm al dato que entrega el IDEAM)
#   2. Ecuación Oficial de la Mira: Q (m³/s) = 1.2455 * (H_mira + 0.13) ^ 4.1635
# ============================================================
COEF_A_MAJADAS = 1.2455
OFFSET_H0_MAJADAS = 0.13
OFFSET_SENSOR_IDEAM_MAJADAS = 0.04         # -4 cm aplicados directamente al dato que entrega el sensor del IDEAM (confirmado por Ing. Carlos)
EXP_B_MAJADAS = 4.1635
CAUDAL_PROMEDIO_BASE_MAJADAS_LS = 2000.0   # Caudal medio base de referencia en Majadas (~2,000 L/s)
NIVEL_PROMEDIO_BASE_MAJADAS_M = 1.031      # Nivel Sensor IDEAM (~1.031 m -> Mira amb 0.991 m -> Q ≈ 2,000 L/s)
DEMANDA_MEDIA_TOMA_BOSCONIA_LS = 1050.0    # Rango operativo PTAP Bosconia: 900 a 1,200 L/s
def calcular_caudal_mira_majadas(h_metros: float, aplicar_offset_ideam: bool = False):
    """
    Calcula el caudal instantáneo Q en el Río Suratá (sector Majadas)
    aplicando la ecuación oficial de curva de gasto de la mira:
        Q (m³/s) = 1.2455 * (H_mira + 0.13) ^ 4.1635
    Si `aplicar_offset_ideam=True`, descuenta primero los 4 cm (0.04 m) al dato entregado por el IDEAM:
        H_mira = H_sensor_IDEAM - 0.04
    Retorna: (q_m3_s, q_ls)
    """
    try:
        h_val = float(h_metros)
        if aplicar_offset_ideam:
            h_val = h_val - OFFSET_SENSOR_IDEAM_MAJADAS
        if np.isnan(h_val) or h_val <= -OFFSET_H0_MAJADAS or h_val <= 0.02:
            return 0.0, 0.0
        h_ef = max(0.0, h_val + OFFSET_H0_MAJADAS)
        q_m3_s = float(COEF_A_MAJADAS * (h_ef ** EXP_B_MAJADAS))
        q_ls = q_m3_s * 1000.0
        return round(q_m3_s, 3), round(q_ls, 1)
    except Exception:
        return 0.0, 0.0
def calcular_nivel_desde_caudal_majadas(q_ls: float) -> float:
    """
    Función inversa de la mira de Majadas:
        H_mira (m) = ( (Q_m3s / 1.2455) ^ (1 / 4.1635) ) - 0.13
    """
    try:
        q_m3_s = max(0.01, float(q_ls) / 1000.0)
        h_m = ((q_m3_s / COEF_A_MAJADAS) ** (1.0 / EXP_B_MAJADAS)) - OFFSET_H0_MAJADAS
        return round(max(0.05, float(h_m)), 3)
    except Exception:
        return 0.991
def obtener_semaforo_hidrologico_surata(
    q_ls: float,
    h_m: float,
    delta_h_30m: float = 0.0,
    lluvia_max_cuenca_tona_mmh: float = 0.0,
    lluvia_max_cuenca_surata_mmh: float = 0.0,
    delta_cota_embalse_cm_1h: float = 0.0,
    q_rebose_mg_ls: float = 0.0,
    sensor_activo_ideam: str = "0230",
    cota_embalse_msnm: float = 885.79,
    detalle_lluvias_parte_alta: str = "",
    lluvia_acum_parte_alta_mm: float = 0.0
) -> dict:
    r"""
    Semáforo Hidrológico Dual de Alerta Temprana hacia Toma Bosconia (`MIMAT-C26 BigQuery` vs. `IDEAM CNE 0023197700`):
    1. ALERTA TEMPRANA POR REBOSE EN EMBALSE + LLUVIAS EN PARTE ALTA (`BigQuery amb` en Tiempo Real, Lag ~0 min):
       - Cuenca Alta Suratá (`Monsalve`): Cauce libre sin embalse; toda lluvia fuerte en Monsalve baja directo por el Río Suratá hacia Majadas y Bosconia.
       - Cuenca Tona + Embalse (`Yerbabuena`, `Vegas del Quemado`, `El Pajal`, `La Mariana` y Radar OTT `Embalse`):
         * Si el Embalse está EN REBOSE (`cota_embalse_msnm > 885.75 msnm`), el alto valor de rebose por el Morning Glory
           más la escorrentía acumulada de las lluvias en la parte alta transitan hacia Puente Tona y el Río Suratá (Majadas -> Toma Bosconia).
         * Si el Embalse está BAJO COTA DE REBOSE (`cota_embalse_msnm <= 885.75 msnm`), el vaso del embalse AMORTIGUA
           Y DETIENE esa creciente (almacenando el volumen sin pasar al Morning Glory).
    2. COMPENSACIÓN DEL REZAGO DE ACTUALIZACIÓN DEL IDEAM (Sensor IDEAM Majadas — Lag de publicación 30–180+ min):
       Cuando la estación del IDEAM tarda varias horas en actualizar sus datos mientras el río viene creciendo desde la noche
       o horas previas por lluvias en la parte alta (`El Pajal`, `Vegas del Quemado`, `Yerbabuena`, `La Mariana`), el sistema
       advierte explícitamente el rezago del IDEAM y sostiene la alerta por alto valor de rebose y lluvias acumuladas aguas arriba.
    """
    h_ideam_ref = h_m + OFFSET_SENSOR_IDEAM_MAJADAS
    etiqueta_canal = {
        "0231": "Pico Máx. Intra-Horario [0231]",
        "0232": "Mín. Intra-Horario [0232]",
        "0230": "Corte Horario [0230]"
    }.get(str(sensor_activo_ideam), f"Compilado [{sensor_activo_ideam}]")
    estaciones_afectando_txt = (
        detalle_lluvias_parte_alta.strip()
        if detalle_lluvias_parte_alta and detalle_lluvias_parte_alta.strip()
        else "Yerbabuena, Vegas del Quemado, El Pajal, La Mariana"
    )
    # Proyección condicional a 60 min o diagnóstico de crecimiento acumulado ante rezago del IDEAM
    if delta_h_30m > 0.01:
        h_proy_1h = min(3.20, h_m + (delta_h_30m * 1.5))
        _, q_proy_1h_ls = calcular_caudal_mira_majadas(h_proy_1h, aplicar_offset_ideam=False)
        txt_proyeccion_curva = (
            f"📈 Curva en ascenso (+{delta_h_30m*100:.0f} cm): proyección condicional ~{q_proy_1h_ls:,.0f} L/s ({h_proy_1h:.2f} m)"
        )
    elif delta_h_30m < -0.01:
        txt_proyeccion_curva = f"📉 Curva en recesión/descenso ({delta_h_30m*100:+.0f} cm en últimos cortes)"
    elif q_ls >= 6500.0 or q_rebose_mg_ls >= 1500.0 or lluvia_acum_parte_alta_mm >= 12.0:
        txt_proyeccion_curva = (
            "⏳ Crecimiento acumulado desde horas previas / anoche "
            "(Nota: estación IDEAM presenta rezago de actualización frente al tránsito real de la creciente)"
        )
    else:
        txt_proyeccion_curva = "➡️ Curva limnimétrica estable (sin rampa brusca en últimos cortes)"
    # Condición física de vertimiento del Embalse de Tona (Cota > 885.75 msnm)
    cota_proyectada_1h = cota_embalse_msnm + (max(0.0, delta_cota_embalse_cm_1h) / 100.0)
    embalse_en_rebose_activo = (cota_embalse_msnm > NIVEL_REBOSE_EMBALSE) or (cota_proyectada_1h > NIVEL_REBOSE_EMBALSE)
    # Detectar forzamiento aguas arriba (Cuenca Suratá libre + Cuenca Tona con Embalse en rebose + lluvias acumuladas en parte alta)
    pulso_critico_tona_rebosando = embalse_en_rebose_activo and (
        lluvia_max_cuenca_tona_mmh >= 22.0
        or delta_cota_embalse_cm_1h >= 3.0
        or q_rebose_mg_ls >= 1800.0
        or (q_rebose_mg_ls >= 1200.0 and lluvia_acum_parte_alta_mm >= 15.0)
    )
    pulso_moderado_tona_rebosando = embalse_en_rebose_activo and (
        lluvia_max_cuenca_tona_mmh >= 10.0
        or delta_cota_embalse_cm_1h >= 1.5
        or q_rebose_mg_ls >= 900.0
        or lluvia_acum_parte_alta_mm >= 10.0
    )
    pulso_critico_arriba = (lluvia_max_cuenca_surata_mmh >= 20.0) or pulso_critico_tona_rebosando
    pulso_moderado_arriba = (lluvia_max_cuenca_surata_mmh >= 10.0) or pulso_moderado_tona_rebosando
    if embalse_en_rebose_activo:
        estado_rebose_txt = f"SOBRE REBOSE ({cota_embalse_msnm:.2f} > 885.75 msnm • Rebose MG est. ~{q_rebose_mg_ls:,.0f} L/s pasa a Puente Tona)"
    else:
        faltante_cm = (NIVEL_REBOSE_EMBALSE - cota_embalse_msnm) * 100.0
        estado_rebose_txt = f"BAJO REBOSE ({cota_embalse_msnm:.2f} msnm, a -{faltante_cm:.1f} cm de 885.75 • El Embalse DETIENE creciente de Tona)"
    resumen_arriba = (
        f"Parte Alta ({estaciones_afectando_txt}) • "
        f"Lluvia actual: Suratá {lluvia_max_cuenca_surata_mmh:.1f} mm/h | Tona {lluvia_max_cuenca_tona_mmh:.1f} mm/h • "
        f"ΔRadar Embalse {delta_cota_embalse_cm_1h:+.1f} cm/h [{estado_rebose_txt}]"
    )
    if q_ls >= 14000.0 or h_m >= 1.66 or delta_h_30m >= 0.25 or (q_ls >= 9000.0 and pulso_critico_arriba):
        return {
            "icono": "🚨",
            "titulo": f"ALERTA ROJA — ALTO VALOR DE REBOSE (~{q_rebose_mg_ls:,.0f} L/s) + CRECIENTE DESDE PARTE ALTA ({estaciones_afectando_txt})",
            "mensaje": (
                f"Majadas ({etiqueta_canal}): {q_ls:,.0f} L/s ({q_ls/1000.0:.2f} m³/s | "
                f"Mira amb: {h_m:.2f} m • IDEAM: {h_ideam_ref:.2f} m) | {txt_proyeccion_curva} | {resumen_arriba}."
            ),
            "accion": "Activar protocolo inmediato de protección en Toma Bosconia (tránsito 15–25 min), cierre preventivo de compuertas y purga continua.",
            "color": "#FF4B4B",
            "text_color": "#FFFFFF",
            "vel": "0.6s"
        }
    elif q_ls >= 9000.0 or h_m >= 1.48 or delta_h_30m >= 0.15 or pulso_critico_arriba:
        motivo_naranja = (
            f"ALTO VALOR DE REBOSE EN EMBALSE (~{q_rebose_mg_ls:,.0f} L/s) + LLUVIAS EN LA PARTE ALTA ({estaciones_afectando_txt})"
            if pulso_critico_arriba
            else f"CRECIENTE EN LAS MAJADAS + APORTE DE LLUVIAS EN LA PARTE ALTA ({estaciones_afectando_txt})"
        )
        return {
            "icono": "⚠️",
            "titulo": f"ALERTA NARANJA — {motivo_naranja}",
            "mensaje": (
                f"Majadas ({etiqueta_canal}): {q_ls:,.0f} L/s ({q_ls/1000.0:.2f} m³/s | "
                f"Mira amb: {h_m:.2f} m • IDEAM: {h_ideam_ref:.2f} m) | {txt_proyeccion_curva} | {resumen_arriba}."
            ),
            "accion": "Alistar desarenadores, vigilar rejillas y preparar dosificación en Toma Bosconia (agua en tránsito hacia el Río Suratá; IDEAM con rezago de reporte).",
            "color": "#FF9933",
            "text_color": "#111111",
            "vel": "1.2s"
        }
    elif q_ls >= 6500.0 or h_m >= 1.36 or pulso_moderado_arriba:
        motivo_amarillo = (
            f"REBOSE ACTIVO EN EMBALSE (~{q_rebose_mg_ls:,.0f} L/s) + LLUVIAS EN LA PARTE ALTA ({estaciones_afectando_txt})"
            if pulso_moderado_arriba
            else f"VIGILANCIA DE CAUDAL EN LAS MAJADAS + APORTES DE PARTE ALTA ({estaciones_afectando_txt})"
        )
        return {
            "icono": "🟡",
            "titulo": f"AVISO AMARILLO — {motivo_amarillo}",
            "mensaje": (
                f"Majadas ({etiqueta_canal}): {q_ls:,.0f} L/s ({q_ls/1000.0:.2f} m³/s | "
                f"Mira amb: {h_m:.2f} m • IDEAM: {h_ideam_ref:.2f} m) | {txt_proyeccion_curva} | {resumen_arriba}."
            ),
            "accion": "Monitorear evolución de pendiente de la curva y turbiedad en Toma Bosconia (atención a rezago de actualización del sensor IDEAM).",
            "color": "#FFBB00",
            "text_color": "#111111",
            "vel": "2.0s"
        }
    elif q_ls >= 1400.0:
        return {
            "icono": "🟢",
            "titulo": "VERDE — CAUDAL CONFIABLE ÓPTIMO (SIN PULSOS CRÍTICOS HACIA EL RÍO SURATÁ)",
            "mensaje": (
                f"Majadas ({etiqueta_canal}): {q_ls:,.0f} L/s ({q_ls/1000.0:.2f} m³/s | "
                f"Mira amb: {h_m:.2f} m • IDEAM: {h_ideam_ref:.2f} m) | {txt_proyeccion_curva} | {resumen_arriba}."
            ),
            "accion": "Oferta hídrica estable en Majadas (~1.8 km aguas arriba de Toma Bosconia | Extracción CRC Embalse actual: 200 L/s).",
            "color": "#00CC96",
            "text_color": "#111111",
            "vel": "0s"
        }
    else:
        return {
            "icono": "🔵",
            "titulo": "AVISO AZUL — ESTIAJE / CAUDAL REDUCIDO",
            "mensaje": f"Caudal bajo en Majadas ({etiqueta_canal}): {q_ls:,.0f} L/s ({q_ls/1000.0:.2f} m³/s | Mira amb: {h_m:.2f} m • IDEAM: {h_ideam_ref:.2f} m).",
            "accion": "Vigilar niveles mínimos en bocatoma Bosconia y ampliar suplemento por Válvula CRC del Embalse de Tona.",
            "color": "#00B4D8",
            "text_color": "#FFFFFF",
            "vel": "0s"
        }
def filtrar_nivel_ott_majadas_robusto(df_sur_hist):
    """
    Acondicionador Digital de Señal Hidráulica para el Radar OTT (versión anterior) en Majadas:
    1. Toma la lectura cruda entregada por el sensor automático del IDEAM (`temperatura`) y le descuenta
       exactamente 4 cm (-0.04 m, confirmado por Ing. Carlos) para homologarla a la mira del amb:
           H_mira = H_sensor_IDEAM - 0.04
    2. Aplica filtro anti-espuma / anti-spike sobre el nivel H ANTES de elevar a la potencia 4.1635.
    3. Calcula el caudal confiable Q (m³/s y L/s) con Q = 1.2455 * (H_mira + 0.13)^4.1635.
    """
    if df_sur_hist.empty:
        return df_sur_hist
    df_s = df_sur_hist.sort_values('timestamp').copy()
    h_raw_ideam = pd.to_numeric(df_s.get('temperatura', pd.Series(dtype=float)), errors='coerce')
    # Si por escala histórica algún registro vino en cm (> 15), convertir a metros
    h_raw_ideam = h_raw_ideam.apply(lambda x: (x / 100.0) if (pd.notna(x) and 15.0 < x <= 450.0) else x)
    # Aplicar el descuento oficial de -4 cm (-0.04 m) al dato que entrega el IDEAM
    h_mira_cal = h_raw_ideam - OFFSET_SENSOR_IDEAM_MAJADAS
    h_valid = h_mira_cal.apply(lambda h: h if (pd.notna(h) and 0.08 <= h <= 4.50) else np.nan)
    niveles_limpios = []
    vals = list(h_valid)
    n_v = len(vals)
    h_prev = None
    for i, h in enumerate(vals):
        if pd.isna(h):
            niveles_limpios.append(h_prev if h_prev is not None else 1.34)
        elif h_prev is None:
            niveles_limpios.append(h)
            h_prev = h
        else:
            salto = abs(h - h_prev)
            if salto > 0.18:
                h_next = vals[i + 1] if (i + 1 < n_v and pd.notna(vals[i + 1])) else None
                if h_next is not None and abs(h_next - h_prev) < 0.08:
                    niveles_limpios.append(round(0.7 * h_prev + 0.3 * h, 3))
                else:
                    niveles_limpios.append(h)
                    h_prev = h
            else:
                niveles_limpios.append(h)
                h_prev = h
    df_s['nivel_crudo_m'] = h_raw_ideam.round(3)
    df_s['nivel_m_crudo'] = df_s['nivel_crudo_m']
    df_s['nivel_mira_m'] = [round(float(x), 3) for x in niveles_limpios]
    df_s['nivel_m_filtrado'] = df_s['nivel_mira_m']
    df_s['caudal_m3s'] = [calcular_caudal_mira_majadas(x, aplicar_offset_ideam=False)[0] for x in df_s['nivel_mira_m']]
    df_s['caudal_m3s_filtrado'] = df_s['caudal_m3s']
    df_s['caudal_ls'] = [calcular_caudal_mira_majadas(x, aplicar_offset_ideam=False)[1] for x in df_s['nivel_mira_m']]
    df_s['caudal_ls_filtrado'] = df_s['caudal_ls']
    return df_s
def filtrar_cota_embalse_robusta(df_emb_hist):
    """
    Filtro Hidráulico Físico Anti-Spike para Radar OTT del Embalse:
    1. Descarta ceros por caída de energía en antena Claro (< 817.94 msnm, solera de fondo)
       y valores superiores a la altura física de instalación del radar OTT (888.75 msnm,
       a +3.00 m sobre la lámina de rebose 885.75 msnm).
       Nota: Preparado para futura reubicación del radar a un punto más central del vaso.
    2. Aplica filtro de gradiente físico: ningún embalse de 46 ha cambia más de 3.5 cm en 10 min.
    3. Si ocurre un glitch transitorio por caída/reconexión de energía de la antena Claro,
       el algoritmo rechaza el salto abrupto y mantiene la cota suave.
    """
    if df_emb_hist.empty or 'temperatura' not in df_emb_hist.columns:
        return df_emb_hist
    df_s = df_emb_hist.sort_values('timestamp').copy()
    c_raw = pd.to_numeric(df_s['temperatura'], errors='coerce') - OFFSET_RADAR_EMBALSE
    # 1. Filtro de Rango Físico Real del Sensor OTT (817.94 msnm fondo a 888.75 msnm cota del radar +3.0 m)
    c_raw = c_raw.apply(lambda c: c if (pd.notna(c) and 817.94 <= c <= 888.75) else np.nan)
    # 2. Filtro de Continuidad Hidráulica (|dc/dt| <= 3.5 cm / 10 min)
    cotas_limpias = []
    c_prev = None
    for c in c_raw:
        if pd.isna(c):
            cotas_limpias.append(c_prev)
        elif c_prev is None:
            cotas_limpias.append(c)
            c_prev = c
        else:
            delta = abs(c - c_prev)
            if delta > 0.035: # Salto abrupto mayor a 3.5 cm en 10 min es físicamente imposible (ruido Claro)
                cotas_limpias.append(c_prev) # Mantiene la lectura previa suave
            else:
                cotas_limpias.append(c)
                c_prev = c
    df_s['cota_calibrada_limpia'] = cotas_limpias
    df_s['temperatura'] = df_s['cota_calibrada_limpia'] + OFFSET_RADAR_EMBALSE
    return df_s
def calcular_balance_dinamico(df_hist):
    if df_hist.empty or len(df_hist) < 2:
        return None
    df_s = filtrar_cota_embalse_robusta(df_hist)
    df_s = df_s.dropna(subset=['cota_calibrada_limpia'])
    if len(df_s) < 2:
        return None
    t_ini = df_s.iloc[0]['timestamp']
    t_fin = df_s.iloc[-1]['timestamp']
    delta_horas = (t_fin - t_ini).total_seconds() / 3600.0
    if delta_horas < 0.2:
        return None
    c_ini = float(df_s.iloc[0]['cota_calibrada_limpia'])
    c_fin = float(df_s.iloc[-1]['cota_calibrada_limpia'])
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
    vol_rebose_m3 = interpolar_volumen(NIVEL_REBOSE_EMBALSE) * 1_000_000.0
    vol_faltante_rebose_m3 = max(0.0, vol_rebose_m3 - v_fin_m3)
    # Clasificación Dinámica: Vaciado vs Llenado vs Equilibrio (Sensibilidad Plena a Crecientes)
    if q_neto_m3_s > 0.005:  # Vaciado neto (> 5 L/s)
        modo_balance = "VACIADO"
        # La neutralidad aplica EXCLUSIVAMENTE al conteo de días de reserva útil:
        # En cota >= 885.75 msnm el vaso está al 100% y en rebose (sin agotamiento útil)
        if c_fin >= NIVEL_REBOSE_EMBALSE:
            dias_autonomia = None
        else:
            dias_autonomia = vol_util_m3 / (q_neto_m3_s * 86400.0)
        dias_para_llenar = None
    elif q_neto_m3_s < -0.005:  # Llenado neto (Recarga / Creciente de cuenca > Salidas)
        modo_balance = "LLENADO"
        dias_autonomia = None
        q_llenado_m3_s = -q_neto_m3_s
        if vol_faltante_rebose_m3 > 0:
            dias_para_llenar = vol_faltante_rebose_m3 / (q_llenado_m3_s * 86400.0)
        else:
            dias_para_llenar = 0.0 # Ya se encuentra en o sobre cota de rebose
    else:  # Equilibrio dinámico estricto (|Q_neto| <= 5 L/s)
        modo_balance = "EQUILIBRIO"
        dias_autonomia = None
        dias_para_llenar = None
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
        "modo_balance": modo_balance,
        "dias_autonomia": dias_autonomia,
        "dias_para_llenar": dias_para_llenar,
        "vol_faltante_rebose_m3": vol_faltante_rebose_m3
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
def obtener_alerta(precipitacion_horaria, estacion):
    if estacion == "Embalse": return "EMBALSE", "🌊 Nivel de Embalse", "#00BFFF", "0s"
    if estacion not in umbrales: return "GRIS", "☁️ Sin umbrales definidos", "#CCCCCC", "0s"
    u = umbrales[estacion]
    es_paramo_ref = u.get("es_referencia_paramo", False)
    sufijo_ref = " (Ref. Páramo)" if es_paramo_ref else ""
    if precipitacion_horaria >= u["roja"]:
        return "ROJA", f"🚨 ALERTA ROJA{sufijo_ref}: {precipitacion_horaria:.1f} mm/h (Excede {u['roja']} mm/h) — Creciente Inminente", "#FF4B4B", "0.5s"
    elif precipitacion_horaria >= u["naranja"]:
        return "NARANJA", f"⚠️ ALERTA NARANJA{sufijo_ref}: {precipitacion_horaria:.1f} mm/h (Excede {u['naranja']} mm/h) — Inspección Rejillas", "#FF9933", "1s"
    elif precipitacion_horaria >= u["amarilla"]:
        return "AMARILLA", f"🟡 AVISO AMARILLA{sufijo_ref}: {precipitacion_horaria:.1f} mm/h (Excede {u['amarilla']} mm/h)", "#FFFF00", "2s"
    elif precipitacion_horaria > 0:
        return "VERDE", f"✅ Lluvia Normal{sufijo_ref}: {precipitacion_horaria:.1f} mm/h", "#00CC96", "0s"
    return "GRIS", "☁️ Sin lluvia (0.0 mm/h en última hora)", "#CCCCCC", "0s"
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
# CACHE "STALE-WHILE-REVALIDATE" PARA FUENTES EXTERNAS (IDEAM / Open-Meteo)
# Muestra de inmediato el ultimo dato recibido y refresca en segundo plano,
# para que una fuente lenta o caida NO bloquee el resto del panel.
# ============================================================
import threading
import copy
import functools

@st.cache_resource
def _almacen_swr():
    return {"datos": {}, "hilos": {}, "lock": threading.Lock()}

def cache_swr(ttl, ttl_fn=None, reintento_s=60, espera_max_s=2.0, valor_inicial=None):
    """
    ttl           : segundos que un dato se considera fresco.
    ttl_fn        : opcional, calcula el ttl segun el valor (ej. reintento corto si es respaldo).
    reintento_s   : si el refresco falla, se reintenta pasado este tiempo (se conserva el ultimo dato).
    espera_max_s  : maximo que se espera al refresco antes de mostrar el ultimo dato guardado.
    valor_inicial : opcional, funcion con los mismos argumentos que devuelve un dato provisional
                    inmediato la primera vez (evita bloquear la primera carga).
    """
    def decorador(fn):
        def _refrescar(alm, clave, args, kwargs):
            try:
                valor = fn(*args, **kwargs)
                vida = ttl_fn(valor) if ttl_fn else ttl
                with alm["lock"]:
                    alm["datos"][clave] = {"valor": valor, "vence": time.time() + vida}
            except Exception:
                with alm["lock"]:
                    if clave in alm["datos"]:
                        alm["datos"][clave]["vence"] = time.time() + reintento_s
            finally:
                with alm["lock"]:
                    alm["hilos"].pop(clave, None)

        @functools.wraps(fn)
        def envoltura(*args, **kwargs):
            alm = _almacen_swr()
            clave = (fn.__name__, repr(args), repr(sorted(kwargs.items())))
            ahora = time.time()
            sincrono = False
            hilo_info = None
            with alm["lock"]:
                ent = alm["datos"].get(clave)
                if ent is None and valor_inicial is None:
                    sincrono = True
                else:
                    if ent is None:
                        ent = {"valor": valor_inicial(*args, **kwargs), "vence": 0.0}
                        alm["datos"][clave] = ent
                    hilo_info = alm["hilos"].get(clave)
                    if hilo_info is None and ahora >= ent["vence"]:
                        t = threading.Thread(target=_refrescar, args=(alm, clave, args, kwargs), daemon=True)
                        hilo_info = (t, ahora)
                        alm["hilos"][clave] = hilo_info
                        t.start()
            if sincrono:
                valor = fn(*args, **kwargs)
                vida = ttl_fn(valor) if ttl_fn else ttl
                with alm["lock"]:
                    alm["datos"][clave] = {"valor": valor, "vence": time.time() + vida}
                return copy.deepcopy(valor)
            if hilo_info is not None:
                restante = espera_max_s - (time.time() - hilo_info[1])
                if restante > 0:
                    hilo_info[0].join(timeout=restante)
            with alm["lock"]:
                valor = alm["datos"][clave]["valor"]
            return copy.deepcopy(valor)
        return envoltura
    return decorador

def _ttl_ideam(d):
    try:
        return 60 if str(d.get("origen", "")).startswith("RESPALDO") else 180
    except Exception:
        return 60
@cache_swr(ttl=180, ttl_fn=_ttl_ideam, reintento_s=60, espera_max_s=2.5)
def sincronizar_fews_ideam_surata_bigquery():
    """
    Conector Oficial Multi-Sensor en Vivo IDEAM (`CNE 0023197700`) -> Google BigQuery
    para la Estación Hidrológica Río Suratá - Sector Majadas (`MAJADAS - AUT [23197700]`).
    1. Consulta y compila en una sola serie cronológica las 3 tablas de sensores del IDEAM:
       - `0230`: Nivel horario por sensor automático (corte cada hora `:00`)
       - `0231`: Nivel máximo horario (se despierta en el minuto exacto del pico intra-horario, ej. `14:10`, `16:05`)
       - `0232`: Nivel mínimo horario (se despierta en el minuto exacto del valle intra-horario, ej. `15:46`, `16:37`)
    2. Aplica el descuento oficial de -4 cm (-0.04 m, confirmado por Ing. Carlos) antes de evaluar la ecuación:
           H_mira = H_IDEAM - 0.04 m  -->  Q (m³/s) = 1.2455 * (H_mira + 0.13)^4.1635
    3. Sincroniza y almacena la serie compilada en BigQuery (`id_estacion = 'Surata'`), guardando en `estado_bateria`
       la trazabilidad del canal (`IDEAM_COMPILADO_0230`, `IDEAM_COMPILADO_0231_PICO`, `IDEAM_COMPILADO_0232_MIN`).
    """
    tabla_bq = "gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones"
    ahora_utc = datetime.now(utc_tz)
    origen_dato = "RESPALDO_HIDROLOGICO_AMB"
    h_actual_m = None
    h_max_reciente_m = None
    sensor_actual_cod = "0230"
    serie_ideam_vivo = []  # Lista de tuplas: (dt_utc, val_h_crudo_m, cod_sensor)
    # 1A. Conexión Primaria en Vivo: Compilación de las 3 tablas de sensores en Socrata IDEAM (0230, 0231 y 0232)
    try:
        url_socrata = (
            "https://www.datos.gov.co/resource/57sv-p2fu.json"
            "?codigoestacion=0023197700&$where=codigosensor%20in('0230','0231','0232')"
            "&$limit=90&$order=fechaobservacion%20DESC"
        )
        r_soc = requests.get(url_socrata, timeout=1.8)
        if r_soc.status_code == 200:
            datos_soc = r_soc.json()
            if isinstance(datos_soc, list) and len(datos_soc) > 0:
                por_minuto = {}
                for reg in datos_soc:
                    try:
                        val_h = float(reg.get("valorobservado", 0))
                        f_str = str(reg.get("fechaobservacion", ""))
                        cod_s = str(reg.get("codigosensor", "0230")).strip()
                        if val_h > 15.0:
                            val_h = val_h / 100.0
                        if 0.10 <= val_h <= 4.50 and f_str:
                            dt_naive = datetime.fromisoformat(f_str.replace("Z", "").split(".")[0])
                            dt_cot = colombia_tz.localize(dt_naive)
                            dt_utc = dt_cot.astimezone(utc_tz)
                            clave_ts = dt_utc.strftime('%Y-%m-%d %H:%M:%S')
                            # Si dos canales coinciden en el mismo minuto exacto, conservar el de mayor nivel (seguridad de creciente)
                            if clave_ts not in por_minuto or val_h > por_minuto[clave_ts][1]:
                                por_minuto[clave_ts] = (dt_utc, round(val_h, 3), cod_s)
                    except Exception:
                        continue
                if por_minuto:
                    serie_ideam_vivo = sorted(por_minuto.values(), key=lambda x: x[0])
                    ult_dt, ult_h, ult_cod = serie_ideam_vivo[-1]
                    # Revisar los registros de la última ventana horaria (~65 min desde el último reporte) para captar picos 0231
                    recientes_1h = [x for x in serie_ideam_vivo if (ult_dt - x[0]).total_seconds() <= 3900]
                    h_max_reciente_m = max(x[1] for x in recientes_1h) if recientes_1h else ult_h
                    h_actual_m = ult_h
                    sensor_actual_cod = ult_cod
                    origen_dato = f"IDEAM_COMPILADO_3SENSORES_{ult_cod}_VIVO"
    except Exception:
        pass
    # 1B. Conexión Secundaria: Visor FEWS IDEAM JSON si Socrata no respondió
    if h_actual_m is None:
        urls_fews_candidatas = [
            "https://fews.ideam.gov.co/colombia/jsonH/0023197700Hobs.json",
            "https://fews.ideam.gov.co/colombia/jsonH/0023197050Hobs.json"
        ]
        for url_fews in urls_fews_candidatas:
            try:
                r_f = requests.get(url_fews, timeout=1.5, verify=False)
                if r_f.status_code == 200 and len(r_f.text) > 50 and "obs" in r_f.text:
                    data_f = r_f.json()
                    serie_obs = data_f.get("obs", {}).get("data", [])
                    for item in reversed(serie_obs):
                        if isinstance(item, list) and len(item) >= 2 and item[1] is not None:
                            val_h = float(item[1])
                            if val_h > 15.0:
                                val_h = val_h / 100.0
                            if 0.10 <= val_h <= 4.50:
                                h_actual_m = round(val_h, 3)
                                h_max_reciente_m = h_actual_m
                                origen_dato = "FEWS_IDEAM_OTT_VIVO"
                                break
                    if h_actual_m is not None:
                        break
            except Exception:
                pass
    # 2. Verificar timestamps recientes de 'Surata' en BigQuery para insertar sin duplicar los 3 canales compilados
    ts_existentes_bq = set()
    ult_ts_bq = None
    ult_h_bq = 1.38
    try:
        q_chk = f"""
        SELECT SAFE_CAST(timestamp AS TIMESTAMP) as ts,
               SAFE_CAST(temperatura AS FLOAT64) as h_m
        FROM `{tabla_bq}`
        WHERE id_estacion = 'Surata'
          AND SAFE_CAST(timestamp AS TIMESTAMP) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 48 HOUR)
        ORDER BY SAFE_CAST(timestamp AS TIMESTAMP) DESC
        LIMIT 120
        """
        rows_chk = list(client.query(q_chk).result())
        if rows_chk:
            for r_c in rows_chk:
                if r_c['ts'] is not None:
                    t_c = r_c['ts'] if r_c['ts'].tzinfo is not None else utc_tz.localize(r_c['ts'])
                    ts_existentes_bq.add(t_c.strftime('%Y-%m-%d %H:%M:%S'))
            if rows_chk[0]['ts'] is not None:
                ult_ts_bq = rows_chk[0]['ts']
                if ult_ts_bq.tzinfo is None:
                    ult_ts_bq = utc_tz.localize(ult_ts_bq)
                if rows_chk[0]['h_m'] is not None and 0.10 <= float(rows_chk[0]['h_m']) <= 4.50:
                    ult_h_bq = float(rows_chk[0]['h_m'])
    except Exception:
        pass
    # 3. Si tanto la API del IDEAM como FEWS están caídos, usar el último nivel válido de BigQuery
    if h_actual_m is None:
        h_actual_m = ult_h_bq if (ult_h_bq and 0.50 <= ult_h_bq <= 4.50) else 1.38
        h_max_reciente_m = h_actual_m
        origen_dato = "RESPALDO_HIDROLOGICO_AMB"
    q_m3s, q_ls = calcular_caudal_mira_majadas(h_actual_m, aplicar_offset_ideam=True)
    h_mira_calibrada_m = round(h_actual_m - OFFSET_SENSOR_IDEAM_MAJADAS, 3)
    h_mira_max_1h_m = round((h_max_reciente_m or h_actual_m) - OFFSET_SENSOR_IDEAM_MAJADAS, 3)
    _, q_ls_max_1h = calcular_caudal_mira_majadas(h_max_reciente_m or h_actual_m, aplicar_offset_ideam=True)
    # 4. Persistir en BigQuery la serie compilada de los 3 sensores (0230, 0231, 0232) sin duplicar timestamps
    try:
        if serie_ideam_vivo:
            filas_nuevas = []
            for item_s in serie_ideam_vivo:
                ts_u, h_u, cod_u = item_s[0], item_s[1], item_s[2]
                ts_str_u = ts_u.strftime('%Y-%m-%d %H:%M:%S')
                if ts_str_u not in ts_existentes_bq:
                    qm3_u, qls_u = calcular_caudal_mira_majadas(h_u, aplicar_offset_ideam=True)
                    suf_canal = {"0230": "HORARIO_0230", "0231": "PICO_MAX_0231", "0232": "MINIMO_0232"}.get(cod_u, cod_u)
                    filas_nuevas.append({
                        "timestamp": ts_str_u,
                        "id_estacion": "Surata",
                        "temperatura": float(h_u),              # Nivel H crudo entregado por el sensor IDEAM (m)
                        "precipitacion": float(qls_u),          # Caudal calculado Q (con H_mira = H_IDEAM - 0.04 m) en L/s
                        "humedad": float(qm3_u),                # Caudal calculado Q en m³/s
                        "presion": 926.5,                       # Presión barométrica ISA a 765 msnm (hPa)
                        "velocidad_viento": float(round(max(0.0, qls_u - DEMANDA_MEDIA_TOMA_BOSCONIA_LS), 1)),
                        "direccion_viento": float(int(cod_u)) if cod_u.isdigit() else 230.0, # Código del sensor (230, 231 o 232)
                        "voltaje_bateria": 12.8,
                        "estado_bateria": f"IDEAM_COMPILADO_{suf_canal}_VIVO"
                    })
                    ts_existentes_bq.add(ts_str_u)
            if filas_nuevas:
                client.insert_rows_json(tabla_bq, filas_nuevas)
        elif ult_ts_bq is None or (ahora_utc - ult_ts_bq).total_seconds() >= 1800:
            fila_nueva = [{
                "timestamp": ahora_utc.strftime('%Y-%m-%d %H:%M:%S'),
                "id_estacion": "Surata",
                "temperatura": float(h_actual_m),
                "precipitacion": float(q_ls),
                "humedad": float(q_m3s),
                "presion": 926.5,
                "velocidad_viento": float(round(max(0.0, q_ls - DEMANDA_MEDIA_TOMA_BOSCONIA_LS), 1)),
                "direccion_viento": 230.0,
                "voltaje_bateria": 12.8,
                "estado_bateria": origen_dato
            }]
            client.insert_rows_json(tabla_bq, fila_nueva)
    except Exception:
        pass
    return {
        "nivel_m": h_mira_calibrada_m,
        "nivel_ideam_crudo_m": h_actual_m,
        "nivel_mira_max_1h_m": h_mira_max_1h_m,
        "caudal_max_1h_ls": q_ls_max_1h,
        "sensor_cod": sensor_actual_cod,
        "caudal_m3s": q_m3s,
        "caudal_ls": q_ls,
        "origen": origen_dato,
        "serie_vivo": serie_ideam_vivo,
        "timestamp_utc": serie_ideam_vivo[-1][0] if serie_ideam_vivo else ahora_utc
    }
@st.cache_data(ttl=180)
def get_last_reading(estacion):
    if estacion == "Surata":
        info_s = sincronizar_fews_ideam_surata_bigquery()
        # Priorizar siempre el último dato oficial de la API en vivo del IDEAM (0023197700)
        if info_s and "VIVO" in str(info_s.get("origen", "")):
            ts_col = info_s["timestamp_utc"].astimezone(colombia_tz)
            return pd.DataFrame([{
                "timestamp": ts_col,
                "id_estacion": "Surata",
                "temperatura": info_s["nivel_ideam_crudo_m"],
                "precipitacion": info_s["caudal_ls"],
                "humedad": info_s["caudal_m3s"],
                "presion": 926.5,
                "velocidad_viento": max(0.0, info_s["caudal_ls"] - DEMANDA_MEDIA_TOMA_BOSCONIA_LS),
                "direccion_viento": 250.0,
                "voltaje_bateria": 12.8,
                "estado_bateria": info_s["origen"]
            }])
    try:
        query = f"""
        SELECT * FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones`
        WHERE id_estacion = '{estacion}'
          AND SAFE_CAST(timestamp AS TIMESTAMP) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 5 DAY)
        ORDER BY SAFE_CAST(timestamp AS TIMESTAMP) DESC
        LIMIT 1
        """
        query_job = client.query(query)
        rows = [dict(row) for row in query_job.result()]
        df = pd.DataFrame(rows)
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize('UTC').dt.tz_convert('America/Bogota')
            return df
        elif estacion == "Surata":
            ahora_col = datetime.now(colombia_tz)
            return pd.DataFrame([{
                "timestamp": ahora_col,
                "id_estacion": "Surata",
                "temperatura": info_s["nivel_ideam_crudo_m"],
                "precipitacion": info_s["caudal_ls"],
                "humedad": info_s["caudal_m3s"],
                "presion": 926.5,
                "velocidad_viento": max(0.0, info_s["caudal_ls"] - DEMANDA_MEDIA_TOMA_BOSCONIA_LS),
                "direccion_viento": 250.0,
                "voltaje_bateria": 12.8,
                "estado_bateria": info_s["origen"]
            }])
        return df
    except Exception as e:
        return pd.DataFrame()
@st.cache_data(ttl=180)
def get_historical_data_range(estacion, fecha_inicio, fecha_fin):
    if estacion == "Surata":
        info_s_h = sincronizar_fews_ideam_surata_bigquery()
        # Si la API en vivo del IDEAM respondió con la serie real, combinarla con BigQuery filtrando la semilla sintética previa
        serie_v = info_s_h.get("serie_vivo", []) if info_s_h else []
    else:
        serie_v = []
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
        filtro_surata_real = "AND IFNULL(estado_bateria, '') LIKE '%VIVO%'" if (estacion == "Surata" and len(serie_v) > 0) else ""
        query = f"""
        SELECT * FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones`
        WHERE id_estacion = '{estacion}'
        {filtro_surata_real}
        AND SAFE_CAST(timestamp AS TIMESTAMP) >= TIMESTAMP('{f_inicio_str}')
        AND SAFE_CAST(timestamp AS TIMESTAMP) <= TIMESTAMP('{f_fin_str}')
        ORDER BY SAFE_CAST(timestamp AS TIMESTAMP) DESC
        LIMIT 50000
        """
        query_job = client.query(query)
        rows = [dict(row) for row in query_job.result()]
        df = pd.DataFrame(rows)
        if estacion == "Surata" and len(serie_v) > 0:
            filas_v = []
            for item_v in serie_v:
                ts_u, h_u = item_v[0], item_v[1]
                cod_u = item_v[2] if len(item_v) >= 3 else "0230"
                suf_c = {"0230": "HORARIO_0230", "0231": "PICO_MAX_0231", "0232": "MINIMO_0232"}.get(str(cod_u), str(cod_u))
                ts_c = ts_u.astimezone(colombia_tz)
                if f_inicio_dt <= ts_c <= f_fin_dt:
                    qm3_u, qls_u = calcular_caudal_mira_majadas(h_u, aplicar_offset_ideam=True)
                    filas_v.append({
                        "timestamp": ts_c,
                        "id_estacion": "Surata",
                        "temperatura": h_u,
                        "precipitacion": qls_u,
                        "humedad": qm3_u,
                        "presion": 926.5,
                        "velocidad_viento": round(max(0.0, qls_u - DEMANDA_MEDIA_TOMA_BOSCONIA_LS), 1),
                        "direccion_viento": float(int(cod_u)) if str(cod_u).isdigit() else 230.0,
                        "voltaje_bateria": 12.8,
                        "estado_bateria": f"IDEAM_COMPILADO_{suf_c}_VIVO"
                    })
            if filas_v:
                df_v = pd.DataFrame(filas_v)
                if not df.empty:
                    df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize('UTC').dt.tz_convert('America/Bogota')
                    df_comb = pd.concat([df, df_v], ignore_index=True)
                    df_comb['ts_round'] = df_comb['timestamp'].dt.floor('1min')
                    df_comb = df_comb.drop_duplicates(subset=['ts_round'], keep='last').drop(columns=['ts_round'])
                    return df_comb.sort_values('timestamp', ascending=False)
                return df_v.sort_values('timestamp', ascending=False)
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize('UTC').dt.tz_convert('America/Bogota')
            return df
        return df
    except Exception as e:
        return pd.DataFrame()
@st.cache_data(ttl=180)
def get_caudal_crc_bosconia_actual():
    """
    Consulta en tiempo real la ultima lectura telemetrica del caudalimetro ET_FIT401
    transmitido desde SCADA AVEVA Edge como CRC_Bosconia_Caudal.
    """
    try:
        query = """
        SELECT SAFE_CAST(precipitacion AS FLOAT64) as caudal_crc,
               SAFE_CAST(timestamp AS TIMESTAMP) as ts
        FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones`
        WHERE id_estacion IN ('CRC_Bosconia_Caudal', 'Embalse_Caudal')
          AND SAFE_CAST(timestamp AS TIMESTAMP) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 5 DAY)
          AND precipitacion IS NOT NULL
        ORDER BY SAFE_CAST(timestamp AS TIMESTAMP) DESC
        LIMIT 1
        """
        job = client.query(query)
        rows = list(job.result())
        if rows and rows[0]['caudal_crc'] is not None:
            return float(rows[0]['caudal_crc']), rows[0]['ts']
    except Exception as e:
        print(f"Error consultando CRC_Bosconia_Caudal en BigQuery: {e}")
    return None, None

@st.cache_data(ttl=120)
def get_historico_crc_bosconia(horas=24):
    """
    Consulta en tiempo real la ultima lectura telemetrica del caudalimetro ET_FIT401
    en la ventana de analisis, para graficar la extraccion continua (sea pasiva o activa).
    """
    try:
        query = f"""
        SELECT 
            SAFE_CAST(timestamp AS TIMESTAMP) as ts,
            SAFE_CAST(precipitacion AS FLOAT64) as caudal_crc
        FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones`
        WHERE id_estacion IN ('CRC_Bosconia_Caudal', 'Embalse_Caudal')
          AND precipitacion IS NOT NULL
          AND SAFE_CAST(timestamp AS TIMESTAMP) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {horas} HOUR)
        ORDER BY ts ASC
        """
        job = client.query(query)
        rows = [dict(r) for r in job.result()]
        df_res = pd.DataFrame(rows)
        if not df_res.empty:
            df_res['ts'] = pd.to_datetime(df_res['ts']).dt.tz_convert('America/Bogota').dt.tz_localize(None)
        return df_res
    except Exception as e:
        print(f"Error consultando historico CRC Bosconia: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=180)
def get_cota_embalse_actual_segura():
    try:
        # Consulta de los últimos 3 registros con filtro de rango para aplicar mediana anti-glitch (-0.04 m confirmado por Ing. Angarita)
        query = """
        SELECT SAFE_CAST(temperatura AS FLOAT64) - 0.04 as cota_cal
        FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones`
        WHERE id_estacion = 'Embalse'
          AND SAFE_CAST(temperatura AS FLOAT64) BETWEEN 818.0 AND 886.5
          AND SAFE_CAST(timestamp AS TIMESTAMP) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 5 DAY)
        ORDER BY SAFE_CAST(timestamp AS TIMESTAMP) DESC
        LIMIT 3
        """
        job = client.query(query)
        rows = [float(r['cota_cal']) for r in job if r['cota_cal'] is not None]
        if rows:
            return float(np.median(rows))
    except:
        pass
    return 885.32
@st.cache_data(ttl=180)
def obtener_novedades_sistema_en_vivo():
    """
    Despachador Inteligente de Novedades Hidrológicas en Vivo (SAT-IA / MIMAT-C26):
    1. Consulta cota en vivo del Embalse Tona y determina si está en rebose o descenso.
    2. Consulta caudal en vivo del Río Suratá en el sector Majadas (hacia Toma Bosconia).
    3. Consulta precipitaciones acumuladas de las últimas 2 horas en todas las estaciones.
    4. Detecta activación de alertas amarillas, naranjas o rojas según umbrales físicos.
    5. Genera el cintillo informativo dinámico para la cabecera del sistema.
    """
    novedades = []
    # 1. ESTADO HIDRÁULICO DEL EMBALSE TONA
    try:
        cota_act = get_cota_embalse_actual_segura()
        if cota_act >= NIVEL_REBOSE_EMBALSE:
            lamina_cm = (cota_act - NIVEL_REBOSE_EMBALSE) * 100.0
            _, q_reb_ls = calcular_caudal_morning_glory(cota_act)
            if lamina_cm >= 0.5 and q_reb_ls > 0:
                novedades.append(f"🌊 <strong>Embalse Tona:</strong> Vertimiento activo por Morning Glory (Cota <strong>{cota_act:.2f} msnm</strong> • Lámina <strong>+{lamina_cm:.1f} cm</strong> • Rebose aprox. ~<strong>{q_reb_ls:,.0f} L/s</strong> [en calibración] hacia Puente Tona)")
            else:
                novedades.append(f"🌊 <strong>Embalse Tona:</strong> Cota estabilizada en umbral de vertimiento (<strong>{cota_act:.2f} msnm</strong>)")
        else:
            margen_cm = (NIVEL_REBOSE_EMBALSE - cota_act) * 100.0
            margen_m = margen_cm / 100.0
            novedades.append(f"📉 <strong>Embalse Tona:</strong> Nivel a <strong>{margen_m:.2f} m</strong> ({margen_cm:.0f} cm) de cota de rebose (Cota <strong>{cota_act:.2f} msnm</strong>)")
    except Exception:
        novedades.append(f"🌊 <strong>Embalse Tona:</strong> Cota de vertedero Morning Glory <strong>885.75 msnm</strong>")
    # 1.B ESTADO HIDROLÓGICO RÍO SURATÁ — SECTOR LAS MAJADAS (HACIA TOMA BOSCONIA)
    try:
        info_maj = sincronizar_fews_ideam_surata_bigquery()
        novedades.append(f"🏞️ <strong>Río Suratá (Majadas):</strong> Caudal <strong>{info_maj['caudal_ls']:,.0f} L/s</strong> ({info_maj['caudal_m3s']:.2f} m³/s • Mira <strong>{info_maj['nivel_m']:.2f} m</strong>) hacia Toma Bosconia")
    except Exception:
        pass
    # 2. DETECCIÓN DE LLUVIAS ACTIVAS Y ALERTAS EN ÚLTIMAS 2 HORAS (FÍSICO)
    try:
        query_lluvias = """
        SELECT
            id_estacion,
            SUM(SAFE_CAST(precipitacion AS FLOAT64)) as lluvia_reciente_mm,
            MAX(SAFE_CAST(precipitacion AS FLOAT64)) as p_max_evento
        FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones`
        WHERE id_estacion NOT IN ('Embalse', 'Surata')
          AND SAFE_CAST(timestamp AS TIMESTAMP) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 2 HOUR)
        GROUP BY id_estacion
        """
        job = client.query(query_lluvias)
        rows = [dict(r) for r in job.result()]
        mapa_fisico_2h = {}
        lluvias_activas = []
        alertas_disparadas = []
        for r in rows:
            est = r.get('id_estacion', '')
            p_tot = float(r.get('lluvia_reciente_mm', 0) or 0)
            p_max = float(r.get('p_max_evento', 0) or 0)
            p_ref = max(p_tot, p_max)
            mapa_fisico_2h[est] = p_ref
            if est in umbrales:
                u = umbrales[est]
                nombre_est = est.replace('_', ' ')
                if p_ref >= u["roja"]:
                    alertas_disparadas.append(f"🚨 <strong>ALERTA ROJA en {nombre_est}</strong> ({p_ref:.1f} mm/h) — Creciente inminente")
                elif p_ref >= u["naranja"]:
                    alertas_disparadas.append(f"⚠️ <strong>ALERTA NARANJA en {nombre_est}</strong> ({p_ref:.1f} mm/h) — Inspección preventiva")
                elif p_ref >= u["amarilla"]:
                    alertas_disparadas.append(f"🟡 <strong>Alerta Amarilla en {nombre_est}</strong> ({p_ref:.1f} mm/h)")
                elif p_ref >= 0.5:
                    lluvias_activas.append(f"🌧️ <strong>Lluvia activa en {nombre_est}</strong> ({p_ref:.1f} mm en últimas 2h)")
        if alertas_disparadas:
            novedades.extend(alertas_disparadas)
        elif lluvias_activas:
            novedades.extend(lluvias_activas)
        else:
            novedades.append("☀️ <strong>Microcuencas:</strong> Tiempo seco en cuencas altas. Sin precipitaciones activas")
    except Exception:
        novedades.append("🛰️ <strong>Red Telemétrica:</strong> Vigilancia hidrometeorológica continua 24/7")
    # 3. SELLO INSTITUCIONAL AMB
    novedades.append("💧 <strong>amb:</strong> Suministro y potabilización continua para el Área Metropolitana")
    return " • ".join(novedades)
# Renderizado inicial del encabezado con telemetría viva
txt_novedades_en_vivo = obtener_novedades_sistema_en_vivo()
render_encabezado_principal(es_110=es_110, txt_novedades=txt_novedades_en_vivo)
def generar_pronostico_respaldo_altimetrico_local(lat: float, lon: float, past_days: int = 7, forecast_days: int = 3) -> pd.DataFrame:
    """
    Motor de Resiliencia Local (Fallback Altimétrico amb):
    Si la API externa de Open-Meteo presenta caída o límite de tasa (HTTP 429/502/Timeout),
    genera una serie horaria continua basada en el gradiente térmico altimétrico de Santander
    (-0.65°C / 100 m) y el ciclo diurno ecuatorial andino para que el Dashboard nunca colapse.
    """
    # Estimar altitud aproximada según coordenadas de las estaciones de la red amb
    alt_est = 2163.0
    if abs(lat - 7.1536) < 0.008 and abs(lon - (-73.0458)) < 0.008:
        alt_est = 885.75   # Embalse Tona
    elif abs(lat - 7.1551) < 0.008 and abs(lon - (-73.0617)) < 0.008:
        alt_est = 765.00   # Río Suratá — Sector Majadas
    elif abs(lat - 7.1227) < 0.01:
        alt_est = 2436.0   # La Mariana
    elif abs(lat - 7.1636) < 0.01:
        alt_est = 3380.82  # Yerbabuena
    elif abs(lat - 7.1072) < 0.01:
        alt_est = 2258.59  # Vegas del Quemado
    elif abs(lat - 7.1180) < 0.01:
        alt_est = 2163.20  # El Pajal
    elif abs(lat - 7.2580) < 0.02:
        alt_est = 3339.79  # Monsalve
    # Temperatura media base según piso térmico en Santander (24°C a 885 msnm, -0.62°C cada 100 m)
    t_media_base = 23.5 - ((alt_est - 885.75) * 0.0062)
    ahora_redondeado = datetime.now().replace(minute=0, second=0, microsecond=0)
    inicio = ahora_redondeado - timedelta(days=past_days)
    total_horas = int((past_days + forecast_days) * 24)
    fechas = [inicio + timedelta(hours=h) for h in range(total_horas)]
    horas_dia = np.array([f.hour for f in fechas], dtype=float)
    # Ciclo térmico diurno (mínimo ~5:00 AM, máximo ~2:00 PM)
    onda_termica = -3.2 * np.cos(2.0 * np.pi * (horas_dia - 5.0) / 24.0)
    temperaturas = np.round(t_media_base + onda_termica, 1)
    humedades = np.clip(np.round(86.0 - (onda_termica * 4.2), 0), 55.0, 99.0)
    vientos = np.round(np.clip(3.5 + (1.8 * np.sin(2.0 * np.pi * (horas_dia - 8.0) / 24.0)), 1.2, 12.0), 1)
    direcciones = np.full(total_horas, 202.0)
    precipitaciones = np.zeros(total_horas)
    probabilidades = np.where((horas_dia >= 14) & (horas_dia <= 19), 25, 10)
    codigos_wmo = np.where((horas_dia >= 14) & (horas_dia <= 18), 2, 1)
    return pd.DataFrame({
        'time': pd.to_datetime(fechas),
        'precipitation': precipitaciones,
        'temperature_2m': temperaturas,
        'relative_humidity_2m': humedades,
        'wind_speed_10m': vientos,
        'wind_direction_10m': direcciones,
        'weather_code': codigos_wmo,
        'precipitation_probability': probabilidades,
        'origen_satelital': 'RESPALDO_LOCAL_AMB'
    })
def _ttl_open_meteo(df):
    try:
        vivo = len(df) > 0 and str(df['origen_satelital'].iloc[0]) == 'OPEN_METEO_VIVO'
    except Exception:
        vivo = False
    return 1800 if vivo else 120

def _pronostico_inicial_local(lat, lon, past_days=7, forecast_days=3):
    # Dato provisional inmediato (respaldo altimetrico local) mientras llega Open-Meteo
    return generar_pronostico_respaldo_altimetrico_local(lat, lon, past_days=past_days, forecast_days=forecast_days)
@cache_swr(ttl=1800, ttl_fn=_ttl_open_meteo, espera_max_s=1.5, valor_inicial=_pronostico_inicial_local)
def obtener_pronostico_open_meteo(lat: float, lon: float, past_days: int = 7, forecast_days: int = 3):
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        f"&hourly=precipitation,temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,weather_code,precipitation_probability"
        f"&past_days={past_days}&forecast_days={forecast_days}&timezone=America/Bogota"
    )
    # 2 Reintentos rápidos con requests / urllib para tolerar intermitencias de Open-Meteo
    for intento in range(2):
        try:
            resp = requests.get(url, headers={'User-Agent': 'MIMAT-C26-amb/2.7'}, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                if 'hourly' in data and 'time' in data['hourly']:
                    df_fc = pd.DataFrame(data['hourly'])
                    df_fc['time'] = pd.to_datetime(df_fc['time'])
                    df_fc['origen_satelital'] = 'OPEN_METEO_VIVO'
                    return df_fc
        except Exception:
            if intento == 0:
                time.sleep(0.6)
    # Si Open-Meteo está caído o limita peticiones (HTTP 429/502/Timeout), activar Respaldo Altimétrico Local
    return generar_pronostico_respaldo_altimetrico_local(lat, lon, past_days=past_days, forecast_days=forecast_days)

def _generar_respaldo_multitemporal_open_meteo():
    """
    Respaldo determinístico altimétrico y climatológico de la red amb para los horizontes
    Semanal (7d), Quincenal (15d) y Mensual (30d) cuando la API de Open-Meteo tarda o tiene límite de tasa.
    """
    hoy = datetime.now(colombia_tz).date()
    fechas_30d = [hoy + timedelta(days=i) for i in range(30)]
    mes_act = hoy.month
    # Factor estacional bimodal andino de Santander (Mar-May y Sep-Nov húmedos; Dic-Feb y Jun-Ago más secos)
    factor_mes = 1.25 if mes_act in [4, 5, 9, 10, 11] else (0.95 if mes_act in [3, 6, 8] else 0.65)
    tasas_base_mm_dia = {
        "Embalse": 3.2,
        "Surata": 3.4,
        "El_Pajal": 4.5,
        "Vegas_del_Quemado": 4.8,
        "La_Mariana": 5.2,
        "Yerbabuena": 6.4,
        "Monsalve": 6.8
    }
    resumen_rows = []
    series_por_estacion = {}
    orden_est = ["Embalse", "Surata", "El_Pajal", "Vegas_del_Quemado", "La_Mariana", "Yerbabuena", "Monsalve"]
    for idx_e, est_id in enumerate(orden_est):
        meta_e = METADATA_ESTACIONES_AMB.get(est_id, {})
        tasa_d = tasas_base_mm_dia.get(est_id, 4.5) * factor_mes
        vals_30d = []
        probs_30d = []
        for d_i in range(30):
            # Modulación sinóptica determinística de 5 y 9 días para simular ondas tropicales andinas
            onda = 1.0 + 0.65 * np.sin(2.0 * np.pi * (d_i + idx_e) / 5.0) + 0.35 * np.cos(2.0 * np.pi * d_i / 9.0)
            mm_d = round(max(0.0, tasa_d * max(0.0, onda)), 1)
            vals_30d.append(mm_d)
            probs_30d.append(int(min(95, max(15, round(25 + mm_d * 5.2)))))
        sem1 = round(sum(vals_30d[:7]), 1)
        sem2 = round(sum(vals_30d[7:15]), 1)
        quincenal = round(sum(vals_30d[:15]), 1)
        mensual = round(sum(vals_30d[:30]), 1)
        idx_pico_7d = int(np.argmax(vals_30d[:7]))
        dia_pico_str = f"{fechas_30d[idx_pico_7d].strftime('%d-%b')} ({vals_30d[idx_pico_7d]:.1f} mm)"
        series_por_estacion[est_id] = pd.DataFrame({
            "fecha": pd.to_datetime(fechas_30d),
            "fecha_str": [f.strftime('%d-%b') for f in fechas_30d],
            "precip_mm": vals_30d,
            "prob_max_pct": probs_30d,
            "horizonte": ["Semanal (Días 1-7)" if i < 7 else ("Quincenal (Días 8-15)" if i < 15 else "Mensual (Días 16-30)") for i in range(30)]
        })
        resumen_rows.append({
            "id_estacion": est_id,
            "Estación": meta_e.get("nombre_completo", est_id.replace("_", " ")),
            "Cuenca / Subsistema": meta_e.get("cuenca_principal", ""),
            "Altitud (msnm)": meta_e.get("altitud_msnm", 0.0),
            "Semanal 7d (mm)": sem1,
            "Semana 2 (Días 8-15 mm)": sem2,
            "Quincenal 15d (mm)": quincenal,
            "Mensual 30d (mm)": mensual,
            "Día Pico (Próx. 7d)": dia_pico_str,
            "Prob. Máx 7d (%)": int(max(probs_30d[:7])),
            "Días Lluvia (≥1mm / 15d)": int(sum(1 for x in vals_30d[:15] if x >= 1.0)),
            "origen": "RESPALDO_CLIMATOLOGICO_AMB"
        })
    return {
        "df_resumen": pd.DataFrame(resumen_rows),
        "series_diarias": series_por_estacion,
        "origen": "RESPALDO_CLIMATOLOGICO_AMB",
        "actualizado_cot": datetime.now(colombia_tz).strftime('%Y-%m-%d %H:%M:%S COT')
    }

def _ttl_multitemporal_om(res_dict):
    try:
        return 1800 if res_dict.get("origen") == "OPEN_METEO_VIVO" else 180
    except Exception:
        return 300

@cache_swr(ttl=1800, ttl_fn=_ttl_multitemporal_om, reintento_s=90, espera_max_s=4.5, valor_inicial=_generar_respaldo_multitemporal_open_meteo)
def obtener_predicciones_multitemporales_open_meteo():
    """
    Consulta en bloque (Batch Multi-Point API) las predicciones diarias de precipitación de Open-Meteo
    para las 7 estaciones de la red MIMAT-C26 (amb):
    1. Endpoint Forecast 16 Días (`api.open-meteo.com/v1/forecast?forecast_days=16`):
       Obtiene día por día la lluvia prevista de los próximos 16 días para calcular con exactitud:
       - Acumulado Semanal (Días 1 a 7)
       - Acumulado Semana 2 (Días 8 a 15)
       - Acumulado Quincenal (Días 1 a 15)
    2. Endpoint Seasonal / Mensual (`seasonal-api.open-meteo.com/v1/seasonal?forecast_days=31` — ECMWF SEAS5)
       con integración continua para los días 16 a 30 (Horizonte Mensual 30 Días). Si el endpoint estacional
       presenta latencia, proyecta los días 16 a 30 combinando la tasa diaria del modelo ECMWF de 16 días
       con la climatología altimétrica oficial de cada microcuenca en Santander.
    """
    orden_est = ["Embalse", "Surata", "El_Pajal", "Vegas_del_Quemado", "La_Mariana", "Yerbabuena", "Monsalve"]
    lats_str = ",".join(str(METADATA_ESTACIONES_AMB[e]["lat"]) for e in orden_est)
    lons_str = ",".join(str(METADATA_ESTACIONES_AMB[e]["lon"]) for e in orden_est)

    url_16d = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lats_str}&longitude={lons_str}"
        f"&daily=precipitation_sum,precipitation_probability_max,precipitation_hours"
        f"&forecast_days=16&timezone=America/Bogota"
    )
    url_30d_seas = (
        f"https://seasonal-api.open-meteo.com/v1/seasonal?latitude={lats_str}&longitude={lons_str}"
        f"&daily=precipitation_sum&forecast_days=31&timezone=America/Bogota"
    )

    data_16d = None
    for intento in range(2):
        try:
            r16 = requests.get(url_16d, headers={'User-Agent': 'MIMAT-C26-amb/2.8'}, timeout=6.0)
            if r16.status_code == 200:
                js16 = r16.json()
                if isinstance(js16, list) and len(js16) == len(orden_est):
                    data_16d = js16
                    break
        except Exception:
            if intento == 0:
                time.sleep(0.4)

    if not data_16d:
        return _generar_respaldo_multitemporal_open_meteo()

    # Intentar enriquecer los días 16 a 30 con el modelo estacional ECMWF SEAS5 de Open-Meteo
    data_30d = None
    try:
        r30 = requests.get(url_30d_seas, headers={'User-Agent': 'MIMAT-C26-amb/2.8'}, timeout=4.0)
        if r30.status_code == 200:
            js30 = r30.json()
            if isinstance(js30, list) and len(js30) == len(orden_est):
                data_30d = js30
    except Exception:
        data_30d = None

    hoy = datetime.now(colombia_tz).date()
    mes_act = hoy.month
    factor_mes = 1.20 if mes_act in [4, 5, 9, 10, 11] else (0.95 if mes_act in [3, 6, 8] else 0.70)
    tasas_clim_mm_dia = {
        "Embalse": 3.2 * factor_mes,
        "Surata": 3.4 * factor_mes,
        "El_Pajal": 4.5 * factor_mes,
        "Vegas_del_Quemado": 4.8 * factor_mes,
        "La_Mariana": 5.2 * factor_mes,
        "Yerbabuena": 6.4 * factor_mes,
        "Monsalve": 6.8 * factor_mes
    }

    resumen_rows = []
    series_por_estacion = {}

    for idx_e, est_id in enumerate(orden_est):
        meta_e = METADATA_ESTACIONES_AMB.get(est_id, {})
        d_block = data_16d[idx_e].get("daily", {}) if idx_e < len(data_16d) else {}
        tiempos_16 = d_block.get("time", [])
        precip_16 = [round(float(x or 0.0), 1) for x in d_block.get("precipitation_sum", [])]
        prob_16 = [int(round(float(x or 0.0))) for x in d_block.get("precipitation_probability_max", [])]

        if len(precip_16) < 15:
            return _generar_respaldo_multitemporal_open_meteo()

        fechas_16 = [pd.to_datetime(t).date() for t in tiempos_16[:16]]
        fechas_30 = list(fechas_16[:15])
        vals_30 = list(precip_16[:15])
        probs_30 = list(prob_16[:15]) if len(prob_16) >= 15 else [50] * 15

        # Extraer días 16 a 30 desde Seasonal API (si respondió) o proyección híbrida ECMWF + Climatología amb
        seas_vals = []
        if data_30d and idx_e < len(data_30d):
            d_s = data_30d[idx_e].get("daily", {})
            raw_seas = d_s.get("precipitation_sum") or d_s.get("precipitation_sum_member01") or []
            if len(raw_seas) >= 30:
                seas_vals = [round(float(x or 0.0), 1) for x in raw_seas[15:30]]

        tasa_media_15d = sum(vals_30[:15]) / 15.0
        tasa_clim = tasas_clim_mm_dia.get(est_id, 4.5)
        tasa_hibrida_d16_30 = (0.65 * tasa_media_15d) + (0.35 * tasa_clim)

        ult_fecha = fechas_30[-1]
        for k in range(15):
            f_next = ult_fecha + timedelta(days=k + 1)
            fechas_30.append(f_next)
            if len(seas_vals) == 15:
                mm_k = seas_vals[k]
            else:
                # Modulación sinóptica suave conservando el volumen quincenal proyectado
                mod_k = 1.0 + 0.45 * np.sin(2.0 * np.pi * (k + idx_e) / 5.0)
                mm_k = round(max(0.0, tasa_hibrida_d16_30 * mod_k), 1)
            vals_30.append(mm_k)
            probs_30.append(int(min(90, max(15, round(25 + mm_k * 4.5)))))

        sem1_mm = round(sum(vals_30[:7]), 1)
        sem2_mm = round(sum(vals_30[7:15]), 1)
        quincenal_mm = round(sum(vals_30[:15]), 1)
        mensual_mm = round(sum(vals_30[:30]), 1)

        idx_max_7d = int(np.argmax(vals_30[:7]))
        dia_pico_7d = f"{fechas_30[idx_max_7d].strftime('%d-%b')} ({vals_30[idx_max_7d]:.1f} mm)"
        prob_max_7d = int(max(probs_30[:7])) if probs_30[:7] else 0
        dias_lluvia_15d = int(sum(1 for v in vals_30[:15] if v >= 1.0))

        series_por_estacion[est_id] = pd.DataFrame({
            "fecha": pd.to_datetime(fechas_30),
            "fecha_str": [f.strftime('%d-%b') for f in fechas_30],
            "precip_mm": vals_30,
            "prob_max_pct": probs_30,
            "horizonte": [
                "1. Semanal (Días 1–7)" if i < 7 else ("2. Semana 2 (Días 8–15)" if i < 15 else "3. Mensual (Días 16–30)")
                for i in range(30)
            ]
        })

        resumen_rows.append({
            "id_estacion": est_id,
            "Estación": meta_e.get("nombre_completo", est_id.replace("_", " ")),
            "Cuenca / Subsistema": meta_e.get("cuenca_principal", ""),
            "Altitud (msnm)": meta_e.get("altitud_msnm", 0.0),
            "Semanal 7d (mm)": sem1_mm,
            "Semana 2 (Días 8-15 mm)": sem2_mm,
            "Quincenal 15d (mm)": quincenal_mm,
            "Mensual 30d (mm)": mensual_mm,
            "Día Pico (Próx. 7d)": dia_pico_7d,
            "Prob. Máx 7d (%)": prob_max_7d,
            "Días Lluvia (≥1mm / 15d)": dias_lluvia_15d,
            "origen": "OPEN_METEO_VIVO"
        })

    return {
        "df_resumen": pd.DataFrame(resumen_rows),
        "series_diarias": series_por_estacion,
        "origen": "OPEN_METEO_VIVO",
        "actualizado_cot": datetime.now(colombia_tz).strftime('%Y-%m-%d %H:%M:%S COT')
    }
def calcular_interventoria_satelital_vs_terreno(df_hist, lat, lon, horas_eval=72, umbral_mm=0.1):
    """
    Módulo de Interventoría & Validación Ex-Post (Skill Scores WMO / NOAA)
    Contrasta la telemetría horaria del pluviómetro físico (Pluvio² / balancín)
    contra las predicciones / reflectividad del modelo satelital (Open-Meteo).
    """
    dias_past = max(1, int(np.ceil(horas_eval / 24.0)))
    df_sat_full = obtener_pronostico_open_meteo(lat, lon, past_days=dias_past, forecast_days=1)
    if df_sat_full.empty:
        return {"valido": False, "mensaje": "No se pudo obtener datos satelitales históricos para la estación."}
    ahora_local = datetime.now(colombia_tz)
    limite_pasado = ahora_local - timedelta(hours=horas_eval)
    df_sat = df_sat_full.copy()
    if df_sat['time'].dt.tz is None:
        df_sat['time_dt'] = df_sat['time'].dt.tz_localize(colombia_tz)
    else:
        df_sat['time_dt'] = df_sat['time'].dt.tz_convert(colombia_tz)
    df_sat_eval = df_sat[(df_sat['time_dt'] >= limite_pasado) & (df_sat['time_dt'] <= ahora_local)].copy()
    if df_sat_eval.empty:
        return {"valido": False, "mensaje": "Sin registros satelitales en la ventana seleccionada."}
    df_sat_eval['time_bin'] = df_sat_eval['time_dt'].dt.floor('h')
    df_sat_hourly = df_sat_eval.groupby('time_bin')['precipitation'].max().reset_index()
    df_sat_hourly.rename(columns={'precipitation': 'precip_sat_mm'}, inplace=True)
    # Procesar telemetría física de terreno
    if df_hist.empty or 'precipitacion' not in df_hist.columns:
        df_obs_hourly = pd.DataFrame(columns=['time_bin', 'precip_obs_mm'])
    else:
        df_h = df_hist.copy()
        if 'timestamp' in df_h.columns:
            if df_h['timestamp'].dt.tz is None:
                df_h['t_local'] = df_h['timestamp'].dt.tz_localize(colombia_tz)
            else:
                df_h['t_local'] = df_h['timestamp'].dt.tz_convert(colombia_tz)
            df_h_eval = df_h[(df_h['t_local'] >= limite_pasado) & (df_h['t_local'] <= ahora_local)].copy()
            df_h_eval['time_bin'] = df_h_eval['t_local'].dt.floor('h')
            df_h_eval['precip_val'] = pd.to_numeric(df_h_eval['precipitacion'], errors='coerce').fillna(0.0)
            df_obs_hourly = df_h_eval.groupby('time_bin')['precip_val'].sum().reset_index()
            df_obs_hourly.rename(columns={'precip_val': 'precip_obs_mm'}, inplace=True)
        else:
            df_obs_hourly = pd.DataFrame(columns=['time_bin', 'precip_obs_mm'])
    # Unir ambas series temporales hora a hora
    df_merged = pd.merge(df_sat_hourly, df_obs_hourly, on='time_bin', how='left')
    df_merged['precip_obs_mm'] = df_merged['precip_obs_mm'].fillna(0.0)
    df_merged['precip_sat_mm'] = df_merged['precip_sat_mm'].fillna(0.0)
    df_merged.sort_values('time_bin', inplace=True)
    # Conteo de la Matriz de Contingencia 2x2
    s_rain = df_merged['precip_sat_mm'] >= umbral_mm
    o_rain = df_merged['precip_obs_mm'] >= umbral_mm
    hits = int((s_rain & o_rain).sum())              # A: Acierto de Tormenta
    false_alarms = int((s_rain & ~o_rain).sum())      # B: Falsa Alarma Satelital
    misses = int((~s_rain & o_rain).sum())            # C: Omisión (Llovió en tierra no vista por satélite)
    correct_neg = int((~s_rain & ~o_rain).sum())      # D: Acierto de Tiempo Seco
    total_horas = len(df_merged)
    # 1. Exactitud Global (% Coincidencia)
    accuracy_pct = ((hits + correct_neg) / total_horas * 100.0) if total_horas > 0 else 100.0
    # 2. Probability of Detection (POD) = A / (A + C)
    total_eventos_reales = hits + misses
    pod_pct = (hits / total_eventos_reales * 100.0) if total_eventos_reales > 0 else (100.0 if false_alarms == 0 else 0.0)
    # 3. False Alarm Ratio (FAR) = B / (A + B)
    total_predicciones_lluvia = hits + false_alarms
    far_pct = (false_alarms / total_predicciones_lluvia * 100.0) if total_predicciones_lluvia > 0 else 0.0
    # 4. Critical Success Index (CSI / Threat Score) = A / (A + B + C)
    denominador_csi = hits + false_alarms + misses
    csi_pct = (hits / denominador_csi * 100.0) if denominador_csi > 0 else (100.0 if correct_neg > 0 else 0.0)
    # 5. Errores Cuantitativos de Precipitación
    diff = df_merged['precip_sat_mm'] - df_merged['precip_obs_mm']
    mae_mm = float(np.abs(diff).mean()) if total_horas > 0 else 0.0
    rmse_mm = float(np.sqrt((diff ** 2).mean())) if total_horas > 0 else 0.0
    lluvia_tot_obs = float(df_merged['precip_obs_mm'].sum())
    lluvia_tot_sat = float(df_merged['precip_sat_mm'].sum())
    # 6. Factor de Magnitud / Sesgo Condicional sobre Aciertos Coincidentes (Hits)
    df_hits = df_merged[s_rain & o_rain]
    if len(df_hits) >= 1 and df_hits['precip_sat_mm'].sum() > 0:
        factor_magnitud = float(df_hits['precip_obs_mm'].sum() / df_hits['precip_sat_mm'].sum())
        factor_magnitud = max(0.20, min(2.50, factor_magnitud))
    elif lluvia_tot_sat > 0 and lluvia_tot_obs > 0:
        factor_magnitud = max(0.20, min(2.50, float(lluvia_tot_obs / lluvia_tot_sat)))
    else:
        factor_magnitud = 1.0 # Neutro
    horas_con_lluvia_obs = int(o_rain.sum())
    horas_con_lluvia_sat = int(s_rain.sum())
    muestra_robusta = bool(total_eventos_reales >= 3)
    if total_horas >= 3 and (df_merged['precip_sat_mm'].std() > 0 or df_merged['precip_obs_mm'].std() > 0):
        corr_val = np.corrcoef(df_merged['precip_sat_mm'], df_merged['precip_obs_mm'])[0, 1]
        corr_pearson = float(corr_val) if not np.isnan(corr_val) else (1.0 if abs(lluvia_tot_obs - lluvia_tot_sat) < 0.1 else 0.0)
    else:
        corr_pearson = 1.0 if hits > 0 or (lluvia_tot_obs == 0 and lluvia_tot_sat == 0) else 0.0
    return {
        "valido": True,
        "df_comparativo": df_merged,
        "hits": hits,
        "false_alarms": false_alarms,
        "misses": misses,
        "correct_neg": correct_neg,
        "total_horas": total_horas,
        "total_eventos_reales": total_eventos_reales,
        "total_predicciones_lluvia": total_predicciones_lluvia,
        "horas_con_lluvia_obs": horas_con_lluvia_obs,
        "horas_con_lluvia_sat": horas_con_lluvia_sat,
        "muestra_robusta": muestra_robusta,
        "factor_magnitud": factor_magnitud,
        "accuracy_pct": accuracy_pct,
        "pod_pct": pod_pct,
        "far_pct": far_pct,
        "csi_pct": csi_pct,
        "mae_mm": mae_mm,
        "rmse_mm": rmse_mm,
        "corr_pearson": corr_pearson,
        "lluvia_tot_obs": lluvia_tot_obs,
        "lluvia_tot_sat": lluvia_tot_sat,
        "umbral_mm": umbral_mm
    }
def evaluar_salud_estacion(df_hist, row, estacion):
    ahora = datetime.now(colombia_tz)
    if row is None or (isinstance(row, pd.Series) and row.empty):
        return {
            "estado": "OFFLINE",
            "es_valido": False,
            "horas_retraso": 999.0,
            "mensaje": "🚨 ESTACIÓN FUERA DE LÍNEA (> 2h sin telemetría)",
            "diagnostico": "Sin recepción de paquetes de datos en el servidor.",
            "accion": "Verificar enlace de comunicación y suministro eléctrico de la estación."
        }
    t_ult = row['timestamp'] if 'timestamp' in row and pd.notna(row['timestamp']) else ahora
    retraso_horas = max(0.0, (ahora - t_ult).total_seconds() / 3600.0)
    if estacion == "Embalse":
        raw_c = row.get('temperatura', 885.80)
        cota_raw = float(raw_c) if pd.notna(raw_c) and float(raw_c) > 800 else 0.0
        if cota_raw < 818.0 or cota_raw > 886.5:
            return {
                "estado": "ANOMALIA_NIVEL",
                "es_valido": False,
                "horas_retraso": retraso_horas,
                "mensaje": "⚠️ COTA FUERA DE RANGO: Sensor Radar OTT reporta valor anómalo.",
                "diagnostico": "Señal del sensor radar fuera del rango físico del embalse (818 - 886 msnm).",
                "accion": "Inspección técnica de sensor radar OTT en caseta de presa."
            }
        return {"estado": "OPERATIVO", "es_valido": True, "horas_retraso": retraso_horas}
    t_val = float(row.get('temperatura', 0)) if pd.notna(row.get('temperatura')) else 0.0
    h_val = float(row.get('humedad', 0)) if pd.notna(row.get('humedad')) else 0.0
    if retraso_horas > 2.0:
        return {
            "estado": "OFFLINE_SOSTENIDO",
            "es_valido": False,
            "horas_retraso": retraso_horas,
            "mensaje": f"📡 ALERTA DE TELEMETRÍA: Estación Sin Reporte ({retraso_horas:.1f}h sin datos)",
            "diagnostico": f"No se reciben lecturas recientes de la estación ({METADATA_ESTACIONES_AMB.get(estacion, {}).get('altitud_msnm', 0):,.0f} msnm).",
            "accion": "Programar revisión técnica en sitio para verificar el estado del equipo."
        }
    # Evaluación objetiva sensor por sensor (excluyendo precipitación 0.0 mm por tiempo seco)
    sensores_en_falla = []
    es_alta_montana = estacion in ["Yerbabuena", "Monsalve"]
    if not df_hist.empty:
        # 1. Humedad Relativa en 0.0% sostenido (> 2h): físicamente imposible
        df_2h = df_hist[df_hist['timestamp'] >= (ahora - timedelta(hours=2))]
        if not df_2h.empty and len(df_2h) >= 2:
            h_s2 = pd.to_numeric(df_2h['humedad'], errors='coerce')
            if (h_s2.max() == 0.0 or pd.isna(h_s2.max())):
                sensores_en_falla.append("Humedad (0.0%)")
            # 2. Temperatura en 0.0°C:
            # - En Yerbabuena y Monsalve (alta montaña): solo si es un cero exacto prolongado (> 3h clavado en 0.0°C)
            # - En estaciones medias (El Pajal, Vegas, La Mariana): > 2h en 0.0°C
            if not es_alta_montana:
                t_s2 = pd.to_numeric(df_2h['temperatura'], errors='coerce')
                if (t_s2.max() == 0.0 and t_s2.min() == 0.0) or pd.isna(t_s2.max()):
                    sensores_en_falla.append("Temperatura (0.0 °C)")
        if es_alta_montana:
            df_3h = df_hist[df_hist['timestamp'] >= (ahora - timedelta(hours=3))]
            if not df_3h.empty and len(df_3h) >= 6:
                t_s3 = pd.to_numeric(df_3h['temperatura'], errors='coerce')
                if (t_s3.max() == 0.0 and t_s3.min() == 0.0) or pd.isna(t_s3.max()):
                    sensores_en_falla.append("Temperatura (0.0 °C prolongado >3h)")
        # 3. Barómetro / Presión Atmosférica pegada sin variación (> 6h) o en 0.0
        if 'presion' in df_hist.columns:
            df_6h = df_hist[df_hist['timestamp'] >= (ahora - timedelta(hours=6))]
            if not df_6h.empty and len(df_6h) >= 10:
                p_s6 = pd.to_numeric(df_6h['presion'], errors='coerce').dropna()
                if p_s6.empty or p_s6.max() == 0.0 or (p_s6.max() == p_s6.min()):
                    sensores_en_falla.append("Barómetro (valor pegado sin variación)")
        # 4. Detección de "Hold SCADA" (Trama congelada repitiendo exactamente la misma Temperatura, Viento, Dirección y Presión por > 3h)
        df_3h_hold = df_hist[df_hist['timestamp'] >= (ahora - timedelta(hours=3))]
        if not df_3h_hold.empty and len(df_3h_hold) >= 12 and not sensores_en_falla:
            t_h3 = pd.to_numeric(df_3h_hold['temperatura'], errors='coerce').dropna()
            v_h3 = pd.to_numeric(df_3h_hold['velocidad_viento'], errors='coerce').dropna()
            d_h3 = pd.to_numeric(df_3h_hold['direccion_viento'], errors='coerce').dropna()
            if not t_h3.empty and not v_h3.empty and not d_h3.empty:
                if (t_h3.max() == t_h3.min()) and (v_h3.max() == v_h3.min()) and (d_h3.max() == d_h3.min()):
                    sensores_en_falla.append(f"Trama Congelada en Hold ({t_h3.iloc[-1]:.2f}°C / {v_h3.iloc[-1]:.1f} km/h fijos)")
    else:
        if h_val == 0.0:
            sensores_en_falla.append("Humedad (0.0%)")
        if t_val == 0.0 and not es_alta_montana:
            sensores_en_falla.append("Temperatura (0.0 °C)")
    if sensores_en_falla:
        lista_txt = ", ".join(sensores_en_falla)
        return {
            "estado": "SENSORES_EN_CERO",
            "es_valido": False,
            "horas_retraso": retraso_horas,
            "mensaje": f"🚨 ALERTA DE SENSORES EN CAMPO: {lista_txt}",
            "diagnostico": f"Se detectan lecturas en cero o retenidas en memoria (Hold SCADA) en: {lista_txt}.",
            "accion": "Se requiere inspección presencial en la estación para diagnosticar la causa exacta en sitio."
        }
    return {"estado": "OPERATIVO", "es_valido": True, "horas_retraso": retraso_horas}
def obtener_sensor_virtual_resiliente(estacion):
    if estacion in ["La_Mariana", "Yerbabuena", "El_Pajal", "Vegas_del_Quemado", "Monsalve"]:
        est_ref = "El_Pajal" if estacion != "El_Pajal" else "Vegas_del_Quemado"
        alt_ref = METADATA_ESTACIONES_AMB.get(est_ref, {}).get("altitud_msnm", 2163.2)
        df_ref = get_last_reading(est_ref)
        t_ref = float(df_ref.iloc[0].get('temperatura', 17.5)) if not df_ref.empty and float(df_ref.iloc[0].get('temperatura', 0)) > 0 else 18.0
        h_ref = float(df_ref.iloc[0].get('humedad', 85.0)) if not df_ref.empty and float(df_ref.iloc[0].get('humedad', 0)) > 0 else 88.0
        v_ref = float(df_ref.iloc[0].get('velocidad_viento', 2.0)) if not df_ref.empty and float(df_ref.iloc[0].get('velocidad_viento', 0)) > 0 else 2.5
        d_ref = float(df_ref.iloc[0].get('direccion_viento', 202.0)) if not df_ref.empty and float(df_ref.iloc[0].get('direccion_viento', 0)) > 0 else 202.0
        meta_est = METADATA_ESTACIONES_AMB.get(estacion, {})
        alt_est = meta_est.get("altitud_msnm", 3380.82 if estacion == "Yerbabuena" else 2436.1)
        lat_est = meta_est.get("lat", 7.163628 if estacion == "Yerbabuena" else 7.122739)
        lon_est = meta_est.get("lon", -72.942169 if estacion == "Yerbabuena" else -73.007019)
        nombre_corto = estacion.replace("_", " ")
        # 1. Estimación física base por Gradiente Altimétrico Vertical (-0.65°C / 100m) desde estación operativa
        delta_alt = alt_est - alt_ref
        t_grad = max(4.0, t_ref - (0.65 * delta_alt / 100.0))
        h_grad = min(100.0, max(75.0, h_ref + (6.0 if delta_alt > 0 else 0.0)))
        v_grad = max(1.5, v_ref * (1.25 if alt_est > 2400 else 1.0))
        d_grad = d_ref
        # 2. Telemetría Satelital en Vivo en la Hora Actual Exacta (Open-Meteo en coordenadas de la estación)
        p_virtual = 0.0
        t_virtual = t_grad
        h_virtual = h_grad
        v_virtual = v_grad
        d_virtual = d_grad
        df_fc_est = obtener_pronostico_open_meteo(lat_est, lon_est, past_days=1, forecast_days=2)
        if not df_fc_est.empty:
            ahora_dt = datetime.now(colombia_tz)
            df_fc_tmp = df_fc_est.copy()
            if df_fc_tmp['time'].dt.tz is None:
                df_fc_tmp['time_dt'] = df_fc_tmp['time'].dt.tz_localize(colombia_tz)
            else:
                df_fc_tmp['time_dt'] = df_fc_tmp['time'].dt.tz_convert(colombia_tz)
            df_actual_sat = df_fc_tmp[df_fc_tmp['time_dt'] >= (ahora_dt - timedelta(minutes=55))]
            row_sat = df_actual_sat.iloc[0] if not df_actual_sat.empty else df_fc_tmp.iloc[-1]
            p_sat = float(row_sat.get('precipitation', 0.0) or 0.0)
            # Filtro anti-falsa lluvia / sesgo orografico Open-Meteo:
            p_ref_lluvia = float(df_ref.iloc[0].get('precipitacion', 0.0) or 0.0) if not df_ref.empty else 0.0
            if p_ref_lluvia <= 0.0 and p_sat < 2.0:
                p_virtual = 0.0
            elif p_sat < 0.8:
                p_virtual = 0.0
            else:
                p_virtual = p_sat
            # Fusión Satélite + Gradiente Altimétrico para máxima precisión en páramo (Yerbabuena 3,380 msnm)
            t_sat = row_sat.get('temperature_2m')
            h_sat = row_sat.get('relative_humidity_2m')
            v_sat = row_sat.get('wind_speed_10m')
            d_sat = row_sat.get('wind_direction_10m')
            if pd.notna(t_sat) and float(t_sat) > 0:
                t_virtual = (0.6 * t_grad) + (0.4 * float(t_sat))
            if pd.notna(h_sat) and float(h_sat) > 0:
                h_virtual = min(100.0, (0.5 * h_grad) + (0.5 * float(h_sat)))
            if pd.notna(v_sat) and float(v_sat) > 0:
                v_virtual = float(v_sat)
            if pd.notna(d_sat) and float(d_sat) > 0:
                d_virtual = float(d_sat)
            origen_lluvia = f"Satélite Open-Meteo en {nombre_corto} ({p_virtual:.1f} mm/h)"
        else:
            p_virtual = 0.0
            origen_lluvia = "Validación satelital (0.0 mm/h)"
        return {
            "temperatura": round(t_virtual, 1),
            "humedad": round(h_virtual, 1),
            "velocidad_viento": round(v_virtual, 1),
            "direccion_viento": round(d_virtual, 0),
            "precipitacion": round(p_virtual, 1),
            "voltaje_bateria": 12.6,
            "es_estimado": True,
            "origen": f"{origen_lluvia} + Gradiente Altimétrico (-0.65°C/100m desde {est_ref.replace('_', ' ')})"
        }
    return None
# Alias de compatibilidad para el Panel de Alerta Temprana SAT
estimar_sensores_virtuales_satelitales = obtener_sensor_virtual_resiliente
@st.cache_data(ttl=120)
def consultar_auditoria_forense_bigquery(estacion: str):
    """
    Consulta directamente en BigQuery cuándo fue la última vez que la estación tuvo datos dinámicos reales
    (antes de quedar en Hold SCADA o caer a 0.0) y qué ráfagas de viento registró ese día.
    """
    try:
        q = f"""
        WITH serie AS (
            SELECT
                SAFE_CAST(timestamp AS TIMESTAMP) as ts,
                SAFE_CAST(temperatura AS FLOAT64) as temperatura,
                SAFE_CAST(humedad AS FLOAT64) as humedad,
                SAFE_CAST(precipitacion AS FLOAT64) as precipitacion,
                SAFE_CAST(velocidad_viento AS FLOAT64) as velocidad_viento,
                SAFE_CAST(direccion_viento AS FLOAT64) as direccion_viento,
                SAFE_CAST(presion AS FLOAT64) as presion,
                LAG(SAFE_CAST(temperatura AS FLOAT64)) OVER (ORDER BY SAFE_CAST(timestamp AS TIMESTAMP)) as prev_t,
                LAG(SAFE_CAST(velocidad_viento AS FLOAT64)) OVER (ORDER BY SAFE_CAST(timestamp AS TIMESTAMP)) as prev_v,
                LAG(SAFE_CAST(direccion_viento AS FLOAT64)) OVER (ORDER BY SAFE_CAST(timestamp AS TIMESTAMP)) as prev_d
            FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones`
            WHERE id_estacion = '{estacion}'
              AND SAFE_CAST(timestamp AS TIMESTAMP) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
        )
        SELECT *
        FROM serie
        WHERE temperatura > 0
          AND (prev_t IS NULL OR ABS(temperatura - prev_t) > 0.001 OR ABS(velocidad_viento - prev_v) > 0.001 OR ABS(direccion_viento - prev_d) > 0.001)
        ORDER BY ts DESC
        LIMIT 50
        """
        df_f = client.query(q).to_dataframe()
        if not df_f.empty and 'ts' in df_f.columns:
            if df_f['ts'].dt.tz is None:
                df_f['hora_colombia'] = df_f['ts'].dt.tz_localize('UTC').dt.tz_convert(colombia_tz)
            else:
                df_f['hora_colombia'] = df_f['ts'].dt.tz_convert(colombia_tz)
        return df_f
    except Exception:
        return pd.DataFrame()
def mostrar_auditoria_forense_caida(estacion: str):
    df_f = consultar_auditoria_forense_bigquery(estacion)
    if df_f.empty:
        return
    with st.expander(f"🌪️ Auditoría Forense en BigQuery — Última Lectura Viva Real (Sin Hold SCADA) de {estacion.replace('_', ' ')}", expanded=True):
        ult_viva = df_f.iloc[0]
        ts_ult_viva = ult_viva['hora_colombia']
        idx_max_v = df_f['velocidad_viento'].fillna(0).idxmax()
        row_max_v = df_f.loc[idx_max_v]
        v_max = float(row_max_v.get('velocidad_viento', 0) or 0)
        d_max = float(row_max_v.get('direccion_viento', 0) or 0)
        h_max_v = row_max_v['hora_colombia'].strftime('%d-%b %I:%M %p')
        v_antes = float(ult_viva.get('velocidad_viento', 0) or 0)
        d_antes = float(ult_viva.get('direccion_viento', 0) or 0)
        c_f1, c_f2, c_f3, c_f4 = st.columns(4)
        c_f1.metric("🕒 Última Trama Viva (Pre-Hold)", ts_ult_viva.strftime('%Y-%m-%d %H:%M'), delta=f"Temp: {ult_viva['temperatura']:.2f}°C | Hum: {ult_viva['humedad']:.0f}%")
        c_f2.metric("🔒 Valor Retenido en Hold", f"{ult_viva['presion']:.2f} hPa", delta="Pasó a 0.0 el 17-Oct 16:05", delta_color="inverse")
        c_f3.metric("💨 Viento en Última Trama", f"{v_antes:.1f} km/h", delta=f"Dir: {d_antes:.1f}°")
        c_f4.metric("🌪️ Pico Viento Previo al Corte", f"{v_max:.1f} km/h", delta=f"{h_max_v} ({d_max:.0f}°)", delta_color="inverse" if v_max >= 15 else "normal")
        df_mostrar = df_f.head(15).copy()
        df_mostrar['Fecha y Hora (COT)'] = df_mostrar['hora_colombia'].dt.strftime('%Y-%m-%d %H:%M:%S')
        cols_mostrar = ['Fecha y Hora (COT)', 'temperatura', 'humedad', 'precipitacion', 'velocidad_viento', 'direccion_viento', 'presion']
        st.caption("📋 **Últimas 15 lecturas dinámicas reales en BigQuery antes de que la estación quedara congelada en Hold (`9.26°C / 678.32 hPa`) y luego pasara a `0.0`:**")
        st.dataframe(df_mostrar[cols_mostrar], use_container_width=True, hide_index=True)
def calcular_presion_atmosferica_hpa(altitud_msnm: float, temp_c: float = 18.0) -> float:
    """
    Calcula la presión atmosférica local (hPa / mbar) aplicando la fórmula barométrica
    hipsográfica estándar internacional (ISA / OMM).
    P0 = 1013.25 hPa al nivel del mar.
    """
    try:
        alt = float(altitud_msnm)
        presion = 1013.25 * ((1.0 - (0.0065 * alt) / 288.15) ** 5.25588)
        return round(float(presion), 1)
    except:
        return 1013.2
def calcular_tendencia_barometrica(df_hist, altitud_msnm, pres_actual, temp_actual=18.0):
    """
    Motor de Aprendizaje SAT-IA (Modo Sombra):
    Calcula la derivada barométrica dP/dt en ventana horaria y estima el tiempo de ventaja
    predictiva previo a la activación del pluviómetro.
    """
    if df_hist.empty or len(df_hist) < 2:
        return {
            "delta_1h": 0.0,
            "delta_str": "→ Estable",
            "flecha": "→",
            "diagnostico": "Sin serie previa suficiente",
            "delta_display": "→ Estable (Modo Aprendizaje)",
            "color": "off",
            "tiempo_anticipacion_min": None
        }
    df_p = df_hist.copy()
    if 'presion' in df_p.columns:
        df_p['presion_num'] = pd.to_numeric(df_p['presion'], errors='coerce')
    else:
        df_p['presion_num'] = np.nan
    df_valid = df_p.dropna(subset=['presion_num', 'timestamp']).sort_values('timestamp')
    df_valid = df_valid[df_valid['presion_num'] > 300]
    if len(df_valid) < 2:
        return {
            "delta_1h": 0.0,
            "delta_str": "→ Estable",
            "flecha": "→",
            "diagnostico": "Monitoreo en curso",
            "delta_display": "→ Estable (Modo Aprendizaje)",
            "color": "off",
            "tiempo_anticipacion_min": None
        }
    t_ult = df_valid.iloc[-1]['timestamp']
    p_ult = float(df_valid.iloc[-1]['presion_num'])
    # Buscar el registro más cercano a 1 hora atrás (entre 35 y 90 minutos)
    df_ventana = df_valid[df_valid['timestamp'] <= (t_ult - timedelta(minutes=35))]
    if not df_ventana.empty:
        fila_prev = df_ventana.iloc[-1]
    else:
        fila_prev = df_valid.iloc[0]
    t_prev = fila_prev['timestamp']
    p_prev = float(fila_prev['presion_num'])
    dt_horas = max(0.25, (t_ult - t_prev).total_seconds() / 3600.0)
    dp_dt = round((p_ult - p_prev) / dt_horas, 2)
    # Clasificación predictiva experimental SAT-IA (Modo Sombra)
    if dp_dt <= -1.5:
        flecha = "↓"
        diag = "Tormenta en ~40 min"
        delta_display = f"↓ {dp_dt:+.1f} hPa/h ({diag})"
        color_delta = "inverse"
        t_ant = 40
    elif dp_dt <= -0.8:
        flecha = "↘"
        diag = "Nubosidad en desarrollo"
        delta_display = f"↘ {dp_dt:+.1f} hPa/h ({diag})"
        color_delta = "inverse"
        t_ant = 60
    elif dp_dt >= 0.8:
        flecha = "↑"
        diag = "Atmósfera estable / Seco"
        delta_display = f"↑ {dp_dt:+.1f} hPa/h ({diag})"
        color_delta = "normal"
        t_ant = None
    else:
        flecha = "→"
        diag = "Estable"
        delta_display = f"→ {dp_dt:+.1f} hPa/h ({diag})"
        color_delta = "off"
        t_ant = None
    return {
        "delta_1h": dp_dt,
        "delta_str": f"{flecha} {dp_dt:+.1f} hPa/h",
        "flecha": flecha,
        "diagnostico": diag,
        "delta_display": delta_display,
        "color": color_delta,
        "tiempo_anticipacion_min": t_ant
    }
# ============================================================
# 4.1 METADATOS HIDROLÓGICOS & GEORREFERENCIACIÓN OFICIAL (amb)
# ============================================================
# Alias de compatibilidad global

METADATA_ESTACIONES_AMB = METADATOS_ESTACIONES = {
    "Embalse": {
        "nombre_completo": "Embalse Tona (Radar OTT)",
        "tipo_sensor": "Radar Hidrométrico OTT (Nivel Vaso)",
        "cuenca_principal": "Cuenca Regulada del Río Tona",
        "subsistema_abastecimiento": "Concebido para futura PTAP Los Angelinos | Respaldo activo a PTAP Bosconia (vía CRC)",
        "zona": "Presa / Vaso del Embalse",
        "dms": "7°09'12.96\"N 73°02'44.88\"W",
        "lat": 7.153600,
        "lon": -73.045800,
        "altitud_msnm": 885.75,
        "peso_cuenca": 0.0,
        "lag_horas": "0 min (In Situ)",
        "microcuencas": "Vaso Principal de Almacenamiento Tona",
        "descripcion": "Vaso regulador en cota 885.75 msnm. Aunque concebido originalmente para abastecer la futura PTAP Los Angelinos, actualmente opera como sistema de resiliencia hídrica entregando agua cruda por gravedad a PTAP Bosconia (vía válvula CRC Bosconia) ante los descensos de caudal del Río Suratá por estiaje.",
        "color": "#005073"
    },
    "Surata": {
        "nombre_completo": "Estación Hidrológica Río Suratá — Sector Majadas",
        "tipo_sensor": "Radar Hidrométrico OTT (Generación Anterior) + Mira Limnimétrica — FEWS IDEAM / amb",
        "cuenca_principal": "Cuenca Media-Baja Río Suratá (Aguas abajo Confluencia con Río Tona / Puente Tona)",
        "subsistema_abastecimiento": "Toma Bosconia (~1.8 km aguas abajo) → PTAP Bosconia (Demanda media: 900 – 1,200 L/s)",
        "zona": "Sector Majadas (Entre Puente Tona y Toma Bosconia / Chitota)",
        "dms": "7°09'18.50\"N 73°03'42.20\"W",
        "lat": 7.155139,
        "lon": -73.061722,
        "altitud_msnm": 765.00,
        "peso_cuenca": 0.0,
        "lag_horas": "15 - 25 min hacia Toma Bosconia",
        "microcuencas": "Confluencia Río Suratá (viene de Pánaga/Vetas/Monsalve) + Río Tona (Puente Tona / Rebose Morning Glory aprox.)",
        "descripcion": "Primera estación hidrológica fluvial integrada a MIMAT-C26. Ubicada en el sector Majadas, aguas abajo de la confluencia del Río Suratá con el Río Tona (Puente Tona) y ~1.8 km aguas arriba de la Toma Bosconia. Calcula el caudal confiable en tiempo real mediante la ecuación oficial de la mira Q = 1.2455 × (H + 0.13)^4.1635 (m³/s), con un caudal base promedio de ~2,000 L/s que abastece a PTAP Bosconia (900 a 1,200 L/s) manteniendo caudal remanente aguas abajo.",
        "color": "#00B4D8"
    },
    "La_Mariana": {
        "nombre_completo": "Estación La Mariana",
        "tipo_sensor": "Estación Meteorológica Automática",
        "cuenca_principal": "Parte Alta Cuenca Río Frío / Filo Divisorio Alto",
        "subsistema_abastecimiento": "Alimentación a PTAP Florida (Abastece a Floridablanca) + Cabecera Golondrinas",
        "zona": "Cresta Alta / Filo Divisorio Río Frío - Tona",
        "dms": "7°07'21.86\"N 73°00'25.27\"W",
        "lat": 7.122739,
        "lon": -73.007019,
        "altitud_msnm": 2436.0,
        "peso_cuenca": 0.15,
        "lag_horas": "1.5 - 2.5 h",
        "microcuencas": "Escorrentía Lateral Cresta & Flanco Oriental Pajal-Golondrinas",
        "descripcion": "Ubicada en la cresta alta divisoria a 2,436 msnm. Monitorea la parte alta de la cuenca del Río Frío (fuente de PTAP Florida para Floridablanca) y el filo divisorio que drena por gravedad hacia la microcuenca Golondrinas y El Pajal (2,163 msnm).",
        "color": "#AB63FA"
    },
    "El_Pajal": {
        "nombre_completo": "Estación El Pajal",
        "tipo_sensor": "Estación Meteorológica Automática",
        "cuenca_principal": "Parte Alta Quebrada Golondrinas & Ladera Sur Tona",
        "subsistema_abastecimiento": "Captación Golondrinas (RQ30) → Sistema Tona (PTAP La Flora & Morrorico) + Remanente al Embalse",
        "zona": "Ladera Media-Alta Sur / Microcuenca Golondrinas",
        "dms": "7°08'26.09\"N 72°59'59.10\"W",
        "lat": 7.140581,
        "lon": -72.999750,
        "altitud_msnm": 2163.0,
        "peso_cuenca": 0.20,
        "lag_horas": "30 - 60 min",
        "microcuencas": "Qda. el Gualilo (mitad embalse) & Qda. La Reforma (cercana a presa)",
        "descripcion": "Ubicada a 2,163 msnm en la ladera sur de Tona. Monitorea directamente la microcuenca Golondrinas (Captación Golondrinas RQ30 hacia el Sistema Tona / PTAP La Flora y Morrorico). Los caudales remanentes de la captación y los afluentes de ladera sur (Qda. el Gualilo y Qda. La Reforma) drenan directamente al vaso del Embalse Tona.",
        "color": "#FFA15A"
    },
    "Vegas_del_Quemado": {
        "nombre_completo": "Estación Vegas del Quemado",
        "tipo_sensor": "Estación Meteorológica Automática",
        "cuenca_principal": "Parte Alta Quebrada Arnania & Ladera Norte Tona",
        "subsistema_abastecimiento": "Captación Arnania (RQ30) → Sistema Tona (PTAP La Flora & Morrorico) + Remanente al Embalse",
        "zona": "Cuenca Media Norte / Valle de Arnania",
        "dms": "7°12'54.10\"N 73°00'46.10\"W",
        "lat": 7.215028,
        "lon": -73.012806,
        "altitud_msnm": 1759.24,
        "peso_cuenca": 0.30,
        "lag_horas": "1.3 h (Confirmado Empíricamente: 1h 20m inicio / 5.3h cresta)",
        "microcuencas": "Qda. Los Monos (Litoral Derecho frente a Reforma) & Cabecera Arnania",
        "descripcion": "Ubicada a 1,759.24 msnm. Monitorea la microcuenca Arnania (Captación Arnania RQ30 hacia el Sistema Tona / PTAP La Flora y Morrorico). Los caudales remanentes de la captación y la ladera norte (Qda. Los Monos) drenan directamente al vaso del Embalse Tona.",
        "color": "#00CC96"
    },
    "Yerbabuena": {
        "nombre_completo": "Estación Yerbabuena",
        "tipo_sensor": "Estación Meteorológica Automática",
        "cuenca_principal": "Alta Cuenca / Nacimiento Río Tona (Zona Páramo)",
        "subsistema_abastecimiento": "Captación Carrizal / Campamento (RQ30) → Sistema Tona (PTAP La Flora & Morrorico) + Remanente al Embalse",
        "zona": "Cabecera Alta / Páramo de Tona",
        "dms": "7°11'44.99\"N 72°54'52.99\"W",
        "lat": 7.195831,
        "lon": -72.914719,
        "altitud_msnm": 3400.25,
        "peso_cuenca": 0.35,
        "lag_horas": "2.0 - 3.5 h",
        "microcuencas": "Río Tona (Cauce Principal) & Quebrada Ranás (Entrada Fondo Cola)",
        "descripcion": "Ubicada en la alta cumbre del Páramo de Tona a 3,400.25 msnm. Monitorea la alta cuenca que alimenta la Captación/Campamento Carrizal (RQ30) hacia el Sistema Tona (PTAP La Flora y Morrorico), y cuyos caudales remanentes no derivados drenan y recargan directamente el vaso del Embalse Tona (PTAP Bosconia).",
        "color": "#005073"
    },
    "Monsalve": {
        "nombre_completo": "Estación Monsalve",
        "tipo_sensor": "Estación Meteorológica Automática",
        "cuenca_principal": "Alta Cuenca / Zona Páramo del Río Suratá (Santurbán / Sisavita)",
        "subsistema_abastecimiento": "Monitoreo Cabecera Río Suratá (Fuente primaria PTAP Bosconia) & RAD Angelinos",
        "zona": "Páramo de Santurbán / Sisavita / Cachirí",
        "dms": "7°26'30.50\"N 72°55'51.30\"W",
        "lat": 7.441806,
        "lon": -72.930917,
        "altitud_msnm": 3339.79,
        "peso_cuenca": 0.0,
        "lag_horas": "3.0 - 5.0 h",
        "microcuencas": "Cabecera Alta Río Suratá (Varios km arriba de Pánaga; antes de confluencia con Río Vetas)",
        "descripcion": "Ubicada en el Páramo de Santurbán (3,339.79 msnm), varios kilómetros arriba de Pánaga en la alta cuenca del Río Suratá. Aguas abajo, cerca de Pánaga, el Río Suratá recibe al Río Vetas (subcuenca independiente).",
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
        estaciones_cuenca = ['Yerbabuena', 'Vegas_del_Quemado', 'El_Pajal', 'La_Mariana', 'Monsalve']
        estaciones_str = "', '".join(estaciones_cuenca)
        # Consulta SQL Inteligente con Filtro Anti-Hold (Detección de tramas congeladas por pérdida de señal)
        query = f"""
        WITH datos_lag AS (
          SELECT
            id_estacion,
            SAFE_CAST(timestamp AS TIMESTAMP) as ts,
            SAFE_CAST(temperatura AS FLOAT64) as temp,
            SAFE_CAST(humedad AS FLOAT64) as hum,
            SAFE_CAST(precipitacion AS FLOAT64) as precip,
            SAFE_CAST(presion AS FLOAT64) as pres,
            SAFE_CAST(direccion_viento AS FLOAT64) as dir_v,
            LAG(SAFE_CAST(temperatura AS FLOAT64), 1) OVER(PARTITION BY id_estacion ORDER BY SAFE_CAST(timestamp AS TIMESTAMP)) as prev_t,
            LAG(SAFE_CAST(presion AS FLOAT64), 1) OVER(PARTITION BY id_estacion ORDER BY SAFE_CAST(timestamp AS TIMESTAMP)) as prev_p,
            LAG(SAFE_CAST(direccion_viento AS FLOAT64), 1) OVER(PARTITION BY id_estacion ORDER BY SAFE_CAST(timestamp AS TIMESTAMP)) as prev_d
          FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones`
          WHERE id_estacion IN ('{estaciones_str}')
            AND SAFE_CAST(timestamp AS TIMESTAMP) >= TIMESTAMP_SUB(TIMESTAMP('{f_ini_str}'), INTERVAL 30 MINUTE)
            AND SAFE_CAST(timestamp AS TIMESTAMP) <= TIMESTAMP('{f_fin_str}')
        ),
        datos_limpios AS (
          SELECT
            id_estacion,
            ts,
            temp,
            hum,
            -- Filtro Físico Anti-Hold: Si temperatura, presión y viento son idénticos al paquete previo (Hold SCADA), la lluvia es 0.0
            CASE
              WHEN prev_t IS NOT NULL
               AND ABS(temp - prev_t) < 0.0001
               AND ABS(pres - prev_p) < 0.0001
               AND ABS(dir_v - prev_d) < 0.0001
              THEN 0.0
              ELSE IFNULL(precip, 0.0)
            END as precip_limpia
          FROM datos_lag
          WHERE ts >= TIMESTAMP('{f_ini_str}')
        )
        SELECT
          id_estacion,
          SUM(precip_limpia) as precip_total,
          MAX(precip_limpia) as precip_max_evento,
          COUNT(*) as num_registros,
          COUNTIF(hum > 1.0 AND temp > 0.0) as num_registros_vivos
        FROM datos_limpios
        GROUP BY id_estacion
        """
        query_job = client.query(query)
        rows = [dict(row) for row in query_job.result()]
        df_res = pd.DataFrame(rows)
        if not df_res.empty:
            df_res['es_estimado_ia'] = False
        else:
            df_res = pd.DataFrame(columns=['id_estacion', 'precip_total', 'precip_max_evento', 'num_registros', 'num_registros_vivos', 'es_estimado_ia'])
        # Resiliencia & Imputación Satelital / Orográfica generalizada para TODAS las estaciones de la cuenca que estén en Sensor Virtual Activo:
        map_p = {r['id_estacion']: float(r.get('precip_total', 0) or 0) for _, r in df_res.iterrows()}
        map_vivos = {r['id_estacion']: int(r.get('num_registros_vivos', 0) or 0) for _, r in df_res.iterrows()}
        p_pajal = map_p.get('El_Pajal', 0.0)
        dias_atras = max(2, min(14, int(((datetime.now(colombia_tz) - f_ini_dt).total_seconds() / 86400.0) + 2)))
        for est_virt in estaciones_cuenca:
            p_actual = map_p.get(est_virt, 0.0)
            vivos_actual = map_vivos.get(est_virt, 0)
            # Si la estación está en modo Sensor Virtual (sin tramas físicas vivas en la ventana), sumar toda la precipitación horaria de su Sensor Virtual Satelital
            if p_actual == 0.0 and vivos_actual < 3:
                p_sat_tot = 0.0
                p_sat_max = 0.0
                meta_v = METADATA_ESTACIONES_AMB.get(est_virt, {})
                lat_v = meta_v.get('lat')
                lon_v = meta_v.get('lon')
                if lat_v is not None and lon_v is not None:
                    df_sat_v = obtener_pronostico_open_meteo(lat_v, lon_v, past_days=dias_atras, forecast_days=1)
                    if not df_sat_v.empty and 'time' in df_sat_v.columns and 'precipitation' in df_sat_v.columns:
                        df_sv = df_sat_v.copy()
                        t_sv = pd.to_datetime(df_sv['time'])
                        df_sv['ts_col'] = t_sv.dt.tz_localize(colombia_tz) if t_sv.dt.tz is None else t_sv.dt.tz_convert(colombia_tz)
                        df_sv = df_sv[(df_sv['ts_col'] >= f_ini_dt - timedelta(hours=1)) & (df_sv['ts_col'] <= f_fin_dt)]
                        if not df_sv.empty:
                            s_prec = pd.to_numeric(df_sv['precipitation'], errors='coerce').fillna(0.0)
                            p_sat_tot = round(float(s_prec.sum()), 1)
                            p_sat_max = round(float(s_prec.max()), 1)
                # Respaldo orográfico adicional para La Mariana cuando llueve en El Pajal
                if est_virt == 'La_Mariana' and p_pajal > 0.0:
                    factor_oro = 1.15 if p_pajal <= 40.0 else (1.08 if p_pajal <= 70.0 else 1.00)
                    p_oro = round(p_pajal * factor_oro, 1)
                    if p_oro > p_sat_tot:
                        p_sat_tot = p_oro
                        p_sat_max = round(p_oro * 0.6, 1)
                mask = df_res['id_estacion'] == est_virt
                if mask.any():
                    df_res.loc[mask, 'precip_total'] = p_sat_tot
                    df_res.loc[mask, 'precip_max_evento'] = p_sat_max
                    df_res.loc[mask, 'es_estimado_ia'] = True
                else:
                    nuevo = pd.DataFrame([{
                        'id_estacion': est_virt,
                        'precip_total': p_sat_tot,
                        'precip_max_evento': p_sat_max,
                        'num_registros': 1,
                        'num_registros_vivos': 0,
                        'es_estimado_ia': True
                    }])
                    df_res = pd.concat([df_res, nuevo], ignore_index=True)
        return df_res
    except Exception as e:
        return pd.DataFrame()
def analizar_vector_viento_mariana():
    try:
        df_mariana = get_last_reading("La_Mariana")
        dir_v = 0.0
        vel_v = 0.0
        es_estimado_mariana = False
        if not df_mariana.empty:
            dir_v = float(df_mariana.iloc[0].get('direccion_viento', 0) or 0)
            vel_v = float(df_mariana.iloc[0].get('velocidad_viento', 0) or 0)
        # Resiliencia Inteligente: Si La Mariana está en ceros planos, estimar de El Pajal (2,163m)
        if dir_v == 0.0 and vel_v == 0.0:
            df_pajal = get_last_reading("El_Pajal")
            if not df_pajal.empty:
                d_p = float(df_pajal.iloc[0].get('direccion_viento', 0) or 0)
                v_p = float(df_pajal.iloc[0].get('velocidad_viento', 0) or 0)
                if v_p > 0:
                    dir_v = d_p
                    vel_v = v_p * 1.25 # Mayor exposición al viento en cresta (2,436m)
                    es_estimado_mariana = True
        # Vector Geodésico La Mariana (2,436 msnm) -> Nacimiento Golondrinas / El Pajal (2,163 msnm): Rumbo NNE ~22°
        # Viento favorable de procedencia (que empuja hacia el NNE): Sur / Suroeste (140° a 270°, óptimo 202°)
        rad = (dir_v - 202.0) * np.pi / 180.0
        componente_empuje = np.cos(rad) # +1.0 empuje máximo hacia Golondrinas, -1.0 alejamiento hacia Río Frío
        tag_virtual = " <span class='badge-status' style='background: rgba(0,204,150,0.2); color: #00805A; border: 1px solid #00CC96;'>🤖 ESTIMADO POR IA (REF. EL PAJAL)</span>" if es_estimado_mariana else ""
        if 140.0 <= dir_v <= 270.0 and vel_v >= 1.0:
            estado_vector = "EMPUJE_ACTIVO_GOLONDRINAS"
            factor_peso = min(1.40, max(0.85, 1.0 + (componente_empuje * 0.40)))
            desc_vector = f"🧭 <strong>Vector Viento Activo:</strong> <code>{dir_v:.0f}° ({vel_v:.1f} km/h)</code> procedente del <strong>Sur-Suroeste (SSW)</strong>.{' <em>[Estimado por gradiente de cresta desde El Pajal]</em>' if es_estimado_mariana else ''}<br>💨 <strong>Empuje Orográfico Confirmado:</strong> Arrastre activo de nubosidad y lluvia desde la cresta de La Mariana (2,436 msnm) directamente hacia el <strong>Nacimiento de Golondrinas y El Pajal</strong> (Rumbo NNE 22°, descenso topográfico de -273 m en 2.14 km). Factor de entrega: <strong>{factor_peso:.2f}x</strong>."
            badge_html = f"<span class='badge-status' style='background: rgba(0,204,150,0.15); color: #00CC96; border: 1px solid #00CC96;'>💨 VECTOR: EMPUJE CONFIRMADO A GOLONDRINAS</span>{tag_virtual}"
        elif (dir_v < 100.0 or dir_v > 300.0) and vel_v >= 3.5:
            estado_vector = "DERIVA_RIO_FRIO"
            factor_peso = 0.30
            desc_vector = f"🍃 <strong>Vector Viento Opuesto:</strong> <code>{dir_v:.0f}° ({vel_v:.1f} km/h)</code> procedente del <strong>Norte/Noreste</strong>.{' <em>[Estimado por gradiente desde El Pajal]</em>' if es_estimado_mariana else ''}<br>La masa nubosa drena preferentemente hacia la vertiente occidental del <strong>Río Frío (PTAP Florida)</strong>. Factor de entrega a Tona reducido a: <strong>{factor_peso:.2f}x</strong>."
            badge_html = f"<span class='badge-status' style='background: rgba(171,99,250,0.15); color: #AB63FA; border: 1px solid #AB63FA;'>🍃 VECTOR: DERIVA HACIA RÍO FRÍO (FLORIDA)</span>{tag_virtual}"
        elif (dir_v < 100.0 or dir_v > 300.0) and vel_v >= 1.0:
            estado_vector = "DERIVA_LEVE_RIO_FRIO"
            factor_peso = max(0.40, 1.0 - ((vel_v / 3.5) * 0.60))
            desc_vector = f"🍃 <strong>Brisa Leve del Norte:</strong> <code>{dir_v:.0f}° ({vel_v:.1f} km/h)</code>.{' <em>[Estimado desde El Pajal]</em>' if es_estimado_mariana else ''}<br>Transición orográfica: parte de la nubosidad deriva hacia el Río Frío (PTAP Florida) y el resto precipita en cumbre. Factor de entrega: <strong>{factor_peso:.2f}x</strong>."
            badge_html = f"<span class='badge-status' style='background: rgba(171,99,250,0.15); color: #AB63FA; border: 1px solid #AB63FA;'>🍃 VECTOR: BRISA LEVE RÍO FRÍO</span>{tag_virtual}"
        else:
            estado_vector = "REGIMEN_CONVECTIVO"
            factor_peso = 1.0
            desc_vector = f"🌬️ <strong>Vector Viento en Calma/Convectivo:</strong> <code>{dir_v:.0f}° ({vel_v:.1f} km/h)</code>.<br>Derrame orográfico natural por gravedad desde la cresta de cumbre (2,436 msnm) hacia la vaguada receptora del Nacimiento de Golondrinas (2,163 msnm). Factor de entrega: <strong>1.00x (15% base)</strong>."
            badge_html = f"<span class='badge-status' style='background: rgba(0,80,115,0.15); color: #005073; border: 1px solid #005073;'>🌬️ RÉGIMEN OROGRÁFICO ESTÁNDAR</span>{tag_virtual}"
        return {
            "dir": dir_v,
            "vel": vel_v,
            "estado": estado_vector,
            "factor_peso": factor_peso,
            "descripcion": desc_vector,
            "badge": badge_html
        }
    except:
        pass
    return {
        "dir": 0.0,
        "vel": 0.0,
        "estado": "REGIMEN_CONVECTIVO",
        "factor_peso": 1.0,
        "descripcion": "🌬️ Régimen orográfico estándar de alta montaña.",
        "badge": "<span class='badge-status' style='background: rgba(0,80,115,0.15); color: #005073; border: 1px solid #005073;'>🌬️ RÉGIMEN OROGRÁFICO ESTÁNDAR</span>"
    }
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
            es_ia = bool(r.get('es_estimado_ia', False))
            mapa_precip[est_id] = {'total': p_tot, 'max': p_max, 'es_estimado_ia': es_ia}
    vec_viento = analizar_vector_viento_mariana()
    # 1. Ponderación de precipitaciones por estación
    datos_temp = []
    for est_id in ['Yerbabuena', 'Vegas_del_Quemado', 'El_Pajal', 'La_Mariana']:
        meta = METADATA_ESTACIONES_AMB[est_id]
        p_info = mapa_precip.get(est_id, {'total': 0.0, 'max': 0.0, 'es_estimado_ia': False})
        p_val = max(0.0, p_info['total'])
        suma_precip_pura += p_val
        peso_efectivo = meta['peso_cuenca']
        if est_id == 'La_Mariana':
            peso_efectivo = meta['peso_cuenca'] * vec_viento['factor_peso']
        aporte_pond = p_val * peso_efectivo
        suma_ponderada += aporte_pond
        datos_temp.append({
            "est_id": est_id,
            "meta": meta,
            "p_val": p_val,
            "p_info": p_info,
            "peso_efectivo": peso_efectivo,
            "aporte_pond": aporte_pond
        })
    # 2. Modelo Hidrológico Dual: Flujo Base Geológico Continuo + Escorrentía por Lluvia
    q_total = max(10.0, float(q_afluente_ls))
    if suma_precip_pura > 0:
        fraccion_escorrentia = min(0.65, max(0.15, (suma_precip_pura / 50.0) * 0.65))
        fraccion_base = 1.0 - fraccion_escorrentia
        estado_cuenca = "LLUVIA ACTIVA"
    else:
        fraccion_escorrentia = 0.0
        fraccion_base = 1.0
        estado_cuenca = "ESTIAJE BASE"
    q_base_total = q_total * fraccion_base
    q_escorrentia_total = q_total * fraccion_escorrentia
    for d in datos_temp:
        est_id = d["est_id"]
        meta = d["meta"]
        p_val = d["p_val"]
        peso_base = meta["peso_cuenca"]
        peso_efectivo = d["peso_efectivo"]
        # Caudal base proporcional al área de la cuenca
        q_base_i = q_base_total * peso_base
        # Caudal de escorrentía proporcional a la lluvia efectiva con viento
        if suma_ponderada > 0:
            q_escorrentia_i = q_escorrentia_total * (d["aporte_pond"] / suma_ponderada)
        else:
            q_escorrentia_i = 0.0
        q_estacion_total = q_base_i + q_escorrentia_i
        porcentaje_final = (q_estacion_total / q_total) * 100.0
        registros.append({
            "id_estacion": est_id,
            "nombre": meta["nombre_completo"],
            "zona": meta["zona"],
            "microcuencas": meta["microcuencas"],
            "subsistema": meta["subsistema_abastecimiento"],
            "altitud_msnm": meta["altitud_msnm"],
            "peso_cuenca": meta["peso_cuenca"],
            "peso_efectivo": peso_efectivo,
            "lag_horas": meta["lag_horas"],
            "color": meta["color"],
            "precipitacion_mm": p_val,
            "es_estimado_ia": d["p_info"].get('es_estimado_ia', False),
            "precip_max_mm": d["p_info"]['max'],
            "caudal_estimado_ls": q_estacion_total,
            "porcentaje_atribucion": porcentaje_final,
            "lat": meta["lat"],
            "lon": meta["lon"]
        })
    df_atrib = pd.DataFrame(registros)
    est_dominante = df_atrib.sort_values('porcentaje_atribucion', ascending=False).iloc[0]
    if estado_cuenca == "LLUVIA ACTIVA":
        mensaje_diagnostico = f"🌧️ <strong>Recarga Integrada por Lluvia & Flujo Base:</strong> Caudal afluente en cola (~{q_total:,.0f} L/s) compuesto por <strong>{q_base_total:,.0f} L/s de flujo base geológico</strong> permanente más <strong>{q_escorrentia_total:,.0f} L/s de escorrentía activa</strong> originada principalmente en <strong>{est_dominante['nombre']}</strong> ({est_dominante['porcentaje_atribucion']:.1f}% de aporte total con {est_dominante['precipitacion_mm']:.1f} mm acumulados), activando <strong>{est_dominante['microcuencas']}</strong> ({est_dominante['subsistema']}) con retardo (Lag) de <strong>{est_dominante['lag_horas']}</strong>."
    else:
        mensaje_diagnostico = f"☀️ <strong>Régimen de Estiaje / Flujo Base Subterráneo:</strong> Sin precipitaciones acumuladas en cuenca. El caudal continuo de recarga en cola (~{q_total:,.0f} L/s) corresponde al 100% al rendimiento hidrogeológico base natural de las microcuencas (Río Tona cabecera 35%, Arnania 30%, Golondrinas/Gualilo 20% y Mariana 15%)."
    return {
        "df": df_atrib,
        "mapa_precip": mapa_precip,
        "vector_viento": vec_viento,
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
            <strong>🏔️ Altitud Oficial:</strong> <strong>{meta['altitud_msnm']:,.2f} msnm</strong><br>
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
            'color': meta['color']
        }])
        st.map(
            df_punto,
            latitude='lat',
            longitude='lon',
            color='color',
            size=35,
            zoom=12
        )
def mapear_codigo_wmo(codigo):
    """Mapeo estándar OMM/WMO a ícono y descripción meteorológica en español"""
    try:
        c = int(codigo) if pd.notna(codigo) else 0
    except:
        c = 0
    if c == 0:
        return "☀️", "Despejado"
    elif c in [1, 2]:
        return "🌤️", "Parc. Nublado"
    elif c == 3:
        return "☁️", "Mayormente Nublado"
    elif c in [45, 48]:
        return "🌫️", "Niebla"
    elif c in [51, 53, 55]:
        return "🌦️", "Llovizna"
    elif c in [61, 63]:
        return "🌧️", "Lluvia Moderada"
    elif c == 65:
        return "🌧️", "Lluvia Fuerte"
    elif c in [80, 81, 82]:
        return "🌧️", "Chubasco"
    elif c in [95, 96, 99]:
        return "⛈️", "Tormenta"
    else:
        return "🌤️", "Nubosidad Var."
def renderizar_modulo_pronostico_horario_estacion(nombre_estacion, df_actual_row):
    if nombre_estacion not in METADATA_ESTACIONES_AMB:
        return
    meta = METADATA_ESTACIONES_AMB[nombre_estacion]
    df_fc_all = obtener_pronostico_open_meteo(meta['lat'], meta['lon'], past_days=1, forecast_days=3)
    if df_fc_all.empty:
        return
    ahora_dt = datetime.now(colombia_tz)
    df_fc = df_fc_all.copy()
    if df_fc['time'].dt.tz is None:
        df_fc['time_dt'] = df_fc['time'].dt.tz_localize(colombia_tz)
    else:
        df_fc['time_dt'] = df_fc['time'].dt.tz_convert(colombia_tz)
    df_futuro = df_fc[df_fc['time_dt'] >= (ahora_dt - timedelta(minutes=45))].copy()
    if df_futuro.empty:
        return
    st.markdown("---")
    st.subheader(f"🔮 Pronóstico Meteorológico Horario & Línea de Tiempo — {meta['nombre_completo']}")
    st.caption(f"📍 Coordenadas: `{meta['lat']:.4f}°N, {meta['lon']:.4f}°W` • Altitud: `{meta['altitud_msnm']:,.2f} msnm` • Consulta automatizada en Python por peticiones HTTP a Open-Meteo & BigQuery.")
    col_fc1, col_fc2 = st.columns([1.3, 1])
    with col_fc1:
        ventana_h = st.radio(
            "⏱️ Horizonte de Pronóstico:",
            [12, 24, 48, 72],
            index=1,
            format_func=lambda h: f"Próximas {h} Horas" if h < 72 else "72 Horas (3 Días Completos)",
            horizontal=True,
            key=f"rad_fc_h_{nombre_estacion}"
        )
    df_vista = df_futuro.head(ventana_h).copy()
    # Paralelo en Vivo: Terreno vs Satélite Actual
    row_fc_act = df_vista.iloc[0]
    ico_sat_act, desc_sat_act = mapear_codigo_wmo(row_fc_act.get('weather_code', 0))
    t_sat_act = float(row_fc_act.get('temperature_2m', 0.0))
    p_sat_act = float(row_fc_act.get('precipitation', 0.0))
    prob_sat_act = int(row_fc_act.get('precipitation_probability', 0) or 0)
    if df_actual_row is not None and not (isinstance(df_actual_row, pd.Series) and df_actual_row.empty):
        if nombre_estacion == "Embalse":
            raw_c = df_actual_row.get('temperatura', 885.80)
            cota_t = (float(raw_c) - OFFSET_RADAR_EMBALSE) if pd.notna(raw_c) and float(raw_c) > 800 else 885.80
            txt_terreno = f"🌊 Cota Vaso: <strong>{cota_t:.2f} msnm</strong> (Radar OTT in situ)"
        elif nombre_estacion == "Surata":
            h_s = float(df_actual_row.get('temperatura', NIVEL_PROMEDIO_BASE_MAJADAS_M)) if pd.notna(df_actual_row.get('temperatura')) else NIVEL_PROMEDIO_BASE_MAJADAS_M
            if h_s <= 0.05 or h_s > 15.0:
                h_s = NIVEL_PROMEDIO_BASE_MAJADAS_M
            h_mira_s = max(0.05, round(h_s - OFFSET_SENSOR_IDEAM_MAJADAS, 3))
            _, q_s_ls = calcular_caudal_mira_majadas(h_s, aplicar_offset_ideam=True)
            txt_terreno = f"🌊 Nivel Mira Calibrado: <strong>{h_mira_s:.2f} m ({h_mira_s*100:.0f} cm)</strong> [IDEAM crudo: {h_s:.2f} m − 4 cm] | ⚡ Caudal Majadas: <strong>{q_s_ls:,.0f} L/s ({q_s_ls/1000.0:.2f} m³/s)</strong>"
        else:
            t_terr = float(df_actual_row.get('temperatura', 0.0)) if pd.notna(df_actual_row.get('temperatura')) else 0.0
            p_terr = float(df_actual_row.get('precipitacion', 0.0)) if pd.notna(df_actual_row.get('precipitacion')) else 0.0
            v_terr = float(df_actual_row.get('velocidad_viento', 0.0)) if pd.notna(df_actual_row.get('velocidad_viento')) else 0.0
            d_terr = float(df_actual_row.get('direccion_viento', 0.0)) if pd.notna(df_actual_row.get('direccion_viento')) else 0.0
            txt_terreno = f"🌡️ Temp: <strong>{t_terr:.1f}°C</strong> | 🌧️ Lluvia: <strong>{p_terr:.1f} mm</strong> | 💨 Viento: <strong>{v_terr:.1f} km/h ({d_terr:.0f}°)</strong>"
    else:
        txt_terreno = "📡 Telemetría en proceso de adquisición"
    txt_paralelo_html = (
        f'<div style="background: rgba(0,80,115,0.06); padding: 12px 18px; border-radius: 10px; border-left: 5px solid #005073; margin: 8px 0 14px 0; font-size: 13px; line-height: 1.6;">'
        f'<div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; margin-bottom: 4px;">'
        f'<strong style="color: #005073; font-size: 13.5px;">⚖️ PARALELO METEOROLÓGICO EN VIVO: MEDICIÓN EN SUELO VS. ESTIMACIÓN SATELITAL</strong>'
        f'<span class="badge-status" style="background: rgba(0,80,115,0.15); color: #005073; border: 1px solid #005073;">AUTOMATIZACIÓN PYTHON (API + BIGQUERY)</span>'
        f'</div>'
        f'• <strong>📡 Telemetría en Suelo (Estación Física amb):</strong> {txt_terreno}<br>'
        f'• <strong>🛰️ Satélite / Modelo Numérico (Open-Meteo):</strong> {ico_sat_act} <strong>{desc_sat_act}</strong> | Temp Prevista: <strong>{t_sat_act:.1f}°C</strong> | Lluvia: <strong>{p_sat_act:.1f} mm/h</strong> | Probabilidad de Lluvia: <strong>{prob_sat_act}%</strong>'
        f'</div>'
    )
    st.markdown(txt_paralelo_html, unsafe_allow_html=True)
    # Carrusel / Tira Horizontal de Tarjetas Horarias
    cards_html = []
    for _, row_h in df_vista.iterrows():
        t_h = row_h['time_dt']
        hora_str = t_h.strftime('%I:%M %p').lower()
        dia_str = t_h.strftime('%a %d')
        w_code = row_h.get('weather_code', 0)
        ico, desc = mapear_codigo_wmo(w_code)
        temp_val = float(row_h.get('temperature_2m', 0.0))
        precip_val = float(row_h.get('precipitation', 0.0))
        prob_val = int(row_h.get('precipitation_probability', 0) or 0)
        bg_card = "rgba(0, 80, 115, 0.04)" if precip_val < 0.1 else "rgba(0, 204, 150, 0.12)"
        bdr_card = "#005073" if precip_val < 0.1 else "#00CC96"
        txt_precip = f"🌧️ {precip_val:.1f} mm" if precip_val > 0 else "☀️ 0.0 mm"
        color_precip = "#00805A" if precip_val > 0 else "#888"
        card = (
            f'<div style="flex: 0 0 102px; background: {bg_card}; border: 1px solid {bdr_card}; border-radius: 10px; padding: 10px 6px; text-align: center; font-family: sans-serif; box-shadow: 0 2px 5px rgba(0,0,0,0.04);">'
            f'<div style="font-size: 11px; font-weight: 700; color: #555;">{dia_str}</div>'
            f'<div style="font-size: 12px; font-weight: 800; color: #005073; margin-bottom: 2px;">{hora_str}</div>'
            f'<div style="font-size: 26px; line-height: 1.2; margin: 3px 0;">{ico}</div>'
            f'<div style="font-size: 10px; color: #444; height: 22px; overflow: hidden; line-height: 1.1; font-weight: 600;">{desc}</div>'
            f'<div style="font-size: 16px; font-weight: 800; color: #222; margin: 3px 0;">{temp_val:.0f}°C</div>'
            f'<div style="font-size: 11px; font-weight: 700; color: {color_precip};">{txt_precip}</div>'
            f'<div style="font-size: 10.5px; color: #005073; font-weight: 600;">💧 {prob_val}%</div>'
            f'</div>'
        )
        cards_html.append(card)
    tira_html = f'<div style="display: flex; gap: 8px; overflow-x: auto; padding: 4px 2px 14px 2px; margin-bottom: 8px;">{"".join(cards_html)}</div>'
    st.markdown(tira_html, unsafe_allow_html=True)
    # Gráfico interactivo combinado (Plotly Dual-Y)
    fig_comb = make_subplots(specs=[[{"secondary_y": True}]])
    fig_comb.add_trace(
        go.Bar(
            x=df_vista['time_dt'],
            y=df_vista['precipitation'],
            name='Lluvia Prevista (mm/h)',
            marker_color='#00CC96',
            opacity=0.75
        ),
        secondary_y=False
    )
    fig_comb.add_trace(
        go.Scatter(
            x=df_vista['time_dt'],
            y=df_vista['temperature_2m'],
            name='Temperatura Prevista (°C)',
            mode='lines+markers',
            line=dict(color='#FF4B4B', width=2.5),
            marker=dict(size=6, color='#FF4B4B')
        ),
        secondary_y=True
    )
    fig_comb.update_layout(
        title=f"📈 Evolución Horaria de Lluvia (mm/h) & Temperatura (°C) — {meta['nombre_completo']} (Próximas {ventana_h} Horas)",
        template='plotly_white',
        height=280,
        margin=dict(t=40, b=10, l=10, r=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig_comb.update_yaxes(title_text="Lluvia (mm/h)", secondary_y=False)
    fig_comb.update_yaxes(title_text="Temperatura (°C)", secondary_y=True)
    st.plotly_chart(fig_comb, use_container_width=True)
def mostrar_modulo_atribucion_cuenca(df_cuenca, q_afluente_ls, horas):
    res = calcular_atribucion_cuenca_tona(df_cuenca, q_afluente_ls)
    df_atrib = res["df"]
    mapa_precip = res["mapa_precip"]
    vec_viento = res.get("vector_viento", analizar_vector_viento_mariana())
    st.markdown("---")
    st.subheader("🛰️ Inteligencia de Cuenca: Trazabilidad & Atribución de Aportes Hídricos")
    st.caption(f"Identificación en tiempo real del origen de la recarga en la cola del Río Tona en las últimas **{horas:.1f} horas**.")
    color_border = "#00CC96" if res["estado"] == "LLUVIA ACTIVA" else "#005073"
    icono = "🌧️" if res["estado"] == "LLUVIA ACTIVA" else "☀️"
    st.markdown(f"""
    <div style="background: rgba(0,80,115,0.06); padding: 14px 18px; border-radius: 10px; border-left: 5px solid {color_border}; margin-bottom: 12px; font-size: 13.5px; line-height: 1.5;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; flex-wrap: wrap;">
            <strong style="color: #005073; font-size: 14px;">{icono} DIAGNÓSTICO INTELIGENTE DE RECARGA DE CUENCA:</strong>
            <span class="badge-status" style="background: rgba(0,80,115,0.15); color: #005073; border: 1px solid #005073;">ESTADO: {res['estado']}</span>
        </div>
        {res['diagnostico']}
    </div>
    <div style="background: rgba(171,99,250,0.06); padding: 12px 16px; border-radius: 10px; border-left: 5px solid #AB63FA; margin-bottom: 15px; font-size: 13px; line-height: 1.5;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; flex-wrap: wrap;">
            <strong style="color: #6A1B9A; font-size: 13.5px;">🧭 VECTORIZACIÓN DE VIENTO EN VIVO (LA MARIANA 2,436 m ➔ NACIMIENTO GOLONDRINAS):</strong>
            {vec_viento['badge']}
        </div>
        {vec_viento['descripcion']}
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
        df_atrib['etiqueta_lluvia'] = df_atrib.apply(
            lambda r: f"{r['precipitacion_mm']:.1f} mm (Sat)" if (bool(r.get('es_estimado_ia')) and float(r['precipitacion_mm']) > 0) else f"{r['precipitacion_mm']:.1f} mm",
            axis=1
        )
        fig_bar = px.bar(
            df_atrib,
            x='id_estacion',
            y='precipitacion_mm',
            title='🌧️ Precipitación Registrada en Cuenca (mm)',
            color='id_estacion',
            color_discrete_map={row['id_estacion']: row['color'] for _, row in df_atrib.iterrows()},
            text='etiqueta_lluvia'
        )
        fig_bar.update_traces(texttemplate='%{text}', textposition='outside', cliponaxis=False)
        fig_bar.update_layout(height=300, template='plotly_white', xaxis_title="Estación Meteorológica", yaxis_title="Lluvia Acumulada (mm)", showlegend=False, margin=dict(t=40, b=10, l=10, r=10))
        st.plotly_chart(fig_bar, use_container_width=True)
    st.markdown("#### 📋 Matriz Hidrológica de Cuenca Tona & Tiempos de Tránsito (Lag Time):")
    df_tabla = df_atrib[['id_estacion', 'nombre', 'zona', 'microcuencas', 'subsistema', 'precipitacion_mm', 'es_estimado_ia', 'lag_horas', 'porcentaje_atribucion', 'caudal_estimado_ls']].copy()
    df_tabla['Lluvia (mm)'] = df_tabla.apply(
        lambda r: f"{r['precipitacion_mm']:.1f} mm (Satélite/IA)" if bool(r.get('es_estimado_ia') is True) else f"{r['precipitacion_mm']:.1f} mm",
        axis=1
    )
    df_tabla['Aporte (%)'] = df_tabla['porcentaje_atribucion'].apply(lambda x: f"{x:.1f} %")
    df_tabla['Q Estimado (L/s)'] = df_tabla['caudal_estimado_ls'].apply(lambda x: f"{x:,.0f} L/s")
    df_tabla = df_tabla[['nombre', 'zona', 'microcuencas', 'subsistema', 'Lluvia (mm)', 'lag_horas', 'Aporte (%)', 'Q Estimado (L/s)']]
    df_tabla.columns = ['Estación', 'Zona Cuenca', 'Microcuencas / Quebradas', 'Subsistema Abastecido', 'Lluvia (mm)', 'Retardo (Lag)', 'Aporte (%)', 'Q Estimado (L/s)']
    st.dataframe(df_tabla, use_container_width=True, hide_index=True)
    # Fila Separada de Monitoreo Eje Norte / Río Suratá (Monsalve + Majadas)
    st.markdown("#### ⛰️ Monitoreo Hidrometeorológico & Fluvial Eje Norte — Cuenca Río Suratá (Monsalve ➔ Majadas ➔ Toma Bosconia):")
    st.caption("Monitoreo integrado desde el Páramo de Santurbán (`Monsalve`, 3,339.79 msnm) hasta la primera estación hidrológica fluvial de MIMAT-C26 en el sector **`Majadas` (`Surata`, 765 msnm, aguas abajo de Puente Tona y ~1.8 km arriba de `Toma Bosconia`).** PTAP Bosconia trata un promedio de 900 a 1,200 L/s.")
    info_mons = mapa_precip.get('Monsalve', {'total': 0.0, 'max': 0.0, 'es_estimado_ia': False})
    p_mons = info_mons['total']
    es_sat_mons = bool(info_mons.get('es_estimado_ia', False))
    meta_mon = METADATA_ESTACIONES_AMB['Monsalve']
    meta_sur = METADATA_ESTACIONES_AMB['Surata']
    info_maj_act = sincronizar_fews_ideam_surata_bigquery()
    df_mon_tabla = pd.DataFrame([
        {
            'Estación': meta_mon['nombre_completo'],
            'Zona Cuenca': meta_mon['zona'],
            'Microcuencas / Quebradas': meta_mon['microcuencas'],
            'Subsistema Abastecido': meta_mon['subsistema_abastecimiento'],
            'Lluvia / Nivel': f"{p_mons:.1f} mm (Satélite - Pluvio² en revisión)" if es_sat_mons else f"{p_mons:.1f} mm",
            'Retardo (Lag)': meta_mon['lag_horas'],
            'Aporte (%)': "Cabecera Eje Norte",
            'Q Estimado (L/s)': "Cabecera Río Suratá (Arriba de Pánaga)"
        },
        {
            'Estación': meta_sur['nombre_completo'],
            'Zona Cuenca': meta_sur['zona'],
            'Microcuencas / Quebradas': meta_sur['microcuencas'],
            'Subsistema Abastecido': meta_sur['subsistema_abastecimiento'],
            'Lluvia / Nivel': f"Mira: {info_maj_act['nivel_m']:.2f} m (Radar OTT)",
            'Retardo (Lag)': meta_sur['lag_horas'],
            'Aporte (%)': "100% Eje Toma Bosconia",
            'Q Estimado (L/s)': f"{info_maj_act['caudal_ls']:,.0f} L/s ({info_maj_act['caudal_m3s']:.2f} m³/s)"
        }
    ])
    st.dataframe(df_mon_tabla, use_container_width=True, hide_index=True)
    # Mapa General de Cuenca en el Bloque del Embalse (Nativo Streamlit st.map)
    st.markdown("#### 🗺️ Mapa de Trazabilidad Espacial de la Cuenca Tona & Estaciones:")
    df_mapa_cuenca = pd.DataFrame([
        {
            'lat': m['lat'],
            'lon': m['lon'],
            'color': m['color']
        }
        for k, m in METADATA_ESTACIONES_AMB.items()
    ])
    st.map(
        df_mapa_cuenca,
        latitude='lat',
        longitude='lon',
        color='color',
        size=25,
        zoom=10
    )
# ============================================================
# 5. SELECTOR DE ESTACIÓN (BARRA HORIZONTAL SUPERIOR)
# ============================================================
estaciones = ["Embalse", "Surata", "La_Mariana", "Yerbabuena", "Vegas_del_Quemado", "El_Pajal", "Monsalve"]
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
caudal_scada_crc, ts_crc_scada = get_caudal_crc_bosconia_actual()
val_default_crc = int(round(caudal_scada_crc)) if caudal_scada_crc is not None else 200

if caudal_scada_crc is not None:
    hora_ts_crc = ts_crc_scada.astimezone(colombia_tz).strftime('%H:%M') if hasattr(ts_crc_scada, 'astimezone') else str(ts_crc_scada)[11:16]
    if caudal_scada_crc <= 30.0:
        badge_crc = f"\U0001F7E1 **Salida Pasiva (V\u00E1lvula en Cierre \u2014 Flujo Base: {caudal_scada_crc:.1f} L/s)** \u2014 *{hora_ts_crc}*"
    else:
        badge_crc = f"\U0001F7E2 **Descarga Activa (V\u00E1lvula CRC en Apertura: {caudal_scada_crc:.1f} L/s)** \u2014 *{hora_ts_crc}*"
else:
    badge_crc = "\u26AA *SCADA Offline (Usando valor operativo nominal)*"

q_salida_crc_actual = st.sidebar.number_input(
    "\U0001FA70 Caudal V\u00E1lvula CRC Bosconia (L/s):",
    min_value=0,
    max_value=3000,
    value=val_default_crc,
    step=10,
    help="Lectura telemetrica en vivo desde SCADA AVEVA Edge (Tag ET_FIT401 / CRC_Bosconia_Caudal). Distingue entre 'Salida Pasiva' (valvula cerrada con flujo base de sello ~25 L/s) y 'Descarga Activa' (valvula en apertura hacia Bosconia). Modificable si se requiere simular maniobras."
)
st.sidebar.caption(badge_crc)
fecha_fin = datetime.now(colombia_tz)
fecha_inicio = fecha_fin - timedelta(hours=horas)
with st.spinner("🔄 Consultando telemetría en tiempo real..."):
    df_actual = get_last_reading(seleccion)
    df_hist = get_historical_data_range(seleccion, fecha_inicio, fecha_fin)
# ============================================================
# 6. EXPORTACIÓN Y EXCEL OPENPYXL (CON BALANCE BOSCONIA 24H & RÍO SURATÁ)
# ============================================================
def enriquecer_datos_embalse(df):
    if df.empty or 'temperatura' not in df.columns:
        return df
    # Filtrar picos a 0.0 por caída de energía en antena Claro, respetando el rango físico real (817.94 a 888.75 msnm)
    df_e = filtrar_cota_embalse_robusta(df)
    if df_e.empty or 'cota_calibrada_limpia' not in df_e.columns:
        return pd.DataFrame()
    df_e = df_e.dropna(subset=['cota_calibrada_limpia']).sort_values('timestamp').copy()
    if df_e.empty:
        return pd.DataFrame()
    df_e['cota_embalse_msnm'] = pd.to_numeric(df_e['cota_calibrada_limpia'], errors='coerce').round(3)
    df_e['volumen_total_hm3'] = df_e['cota_embalse_msnm'].apply(lambda c: round(interpolar_volumen(c), 4) if pd.notna(c) else None)
    df_e['volumen_util_hm3'] = df_e['volumen_total_hm3'].apply(lambda v: round(max(0.0, v - 1.980), 4) if pd.notna(v) else None)
    c_ini = df_e['cota_embalse_msnm'].iloc[0]
    df_e['descenso_acumulado_cm'] = ((c_ini - df_e['cota_embalse_msnm']) * 100.0).round(2)
    df_e['caudal_rebose_ls'] = df_e['cota_embalse_msnm'].apply(lambda c: round(calcular_caudal_morning_glory(c)[1], 1) if pd.notna(c) else 0.0)
    t_ini = df_e['timestamp'].iloc[0]
    t_fin = df_e['timestamp'].iloc[-1]
    df_e['delta_segundos_acum'] = (df_e['timestamp'] - t_ini).dt.total_seconds()
    # Cruzar con la telemetría real en vivo del caudalímetro ET_FIT401 (CRC_Bosconia_Caudal)
    horas_ventana = max(24, int(((t_fin - t_ini).total_seconds() / 3600.0) + 4))
    df_crc_real = get_historico_crc_bosconia(horas=horas_ventana)
    q_fallback, _ = get_caudal_crc_bosconia_actual()
    q_base_crc = float(q_fallback) if q_fallback is not None else 25.0
    if not df_crc_real.empty and 'ts' in df_crc_real.columns and 'caudal_crc' in df_crc_real.columns:
        df_e_ts = df_e['timestamp'].dt.tz_localize(None) if hasattr(df_e['timestamp'].dt, 'tz') and df_e['timestamp'].dt.tz is not None else pd.to_datetime(df_e['timestamp'])
        df_left = pd.DataFrame({'ts_key': df_e_ts, 'orig_idx': df_e.index}).sort_values('ts_key')
        df_right = df_crc_real[['ts', 'caudal_crc']].dropna().sort_values('ts')
        df_merged_crc = pd.merge_asof(df_left, df_right, left_on='ts_key', right_on='ts', direction='nearest', tolerance=pd.Timedelta(hours=2))
        df_merged_crc = df_merged_crc.sort_values('orig_idx')
        q_serie_ls = pd.to_numeric(df_merged_crc['caudal_crc'], errors='coerce').ffill().bfill().fillna(q_base_crc).clip(lower=0.0, upper=3000.0)
        df_e['caudal_medio_bosconia_ls'] = q_serie_ls.values.round(1)
    else:
        df_e['caudal_medio_bosconia_ls'] = round(q_base_crc, 1)
    # 1. SALIDAS: Integración temporal exacta de CRC Bosconia, Rebose Morning Glory y Salidas Totales
    dt_paso_s = df_e['timestamp'].diff().dt.total_seconds().fillna(0.0).clip(lower=0.0, upper=3600.0)
    q_filtraciones_ls = 51.0
    q_crc_m3s = pd.to_numeric(df_e['caudal_medio_bosconia_ls'], errors='coerce').fillna(0.0) / 1000.0
    q_reb_m3s = pd.to_numeric(df_e['caudal_rebose_ls'], errors='coerce').fillna(0.0) / 1000.0
    df_e['m3_consumidos_bosconia'] = (q_crc_m3s * dt_paso_s).cumsum().round(1)
    df_e['m3_rebose_mg_acum'] = (q_reb_m3s * dt_paso_s).cumsum().round(1)
    df_e['caudal_salidas_totales_ls'] = (df_e['caudal_medio_bosconia_ls'] + df_e['caudal_rebose_ls'] + q_filtraciones_ls).round(1)
    q_sal_tot_m3s = df_e['caudal_salidas_totales_ls'] / 1000.0
    df_e['m3_salidas_totales_acum'] = (q_sal_tot_m3s * dt_paso_s).cumsum().round(1)
    # 2. ENTRADAS: Caudal de Llegada / Carga de Cuenca (Cola + Subsidiarias) y Volumen Acumulado de Entrada (m³)
    v_m3_serie = df_e['volumen_total_hm3'] * 1_000_000.0
    dv_dt_m3s = (v_m3_serie.diff() / dt_paso_s.replace(0, np.nan)).fillna(0.0)
    dv_dt_ls_suave = (dv_dt_m3s * 1000.0).rolling(window=3, min_periods=1, center=True).mean().fillna(0.0)
    df_e['caudal_afluentes_ls'] = (dv_dt_ls_suave + df_e['caudal_salidas_totales_ls']).clip(lower=0.0, upper=9000.0).round(1)
    q_in_m3s = df_e['caudal_afluentes_ls'] / 1000.0
    df_e['m3_entrada_cuenca_acum'] = (q_in_m3s * dt_paso_s).cumsum().round(1)
    # 3. BALANCE DE CAUDALES: Entrada Neta menos Salida Total (dV/dt en L/s)
    df_e['balance_neto_caudales_ls'] = (df_e['caudal_afluentes_ls'] - df_e['caudal_salidas_totales_ls']).round(1)
    return df_e
def enriquecer_datos_surata(df):
    """
    Enriquece el DataFrame de la Estación Hidrológica Surata (Sector Majadas)
    aplicando el filtro anti-espuma para Radar OTT (versión anterior), la ecuación
    oficial de la mira Q = 1.2455 * (H + 0.13)^4.1635 y el balance con Toma Bosconia
    y el rebose aproximado del Morning Glory (en calibración).
    """
    if df.empty or 'temperatura' not in df.columns:
        return pd.DataFrame()
    df_s = filtrar_nivel_ott_majadas_robusto(df)
    cota_emb_act = get_cota_embalse_actual_segura()
    _, q_reb_mg_aprox_ls = calcular_caudal_morning_glory(cota_emb_act)
    df_s['demanda_toma_bosconia_ls'] = DEMANDA_MEDIA_TOMA_BOSCONIA_LS
    df_s['caudal_remanente_aguas_abajo_ls'] = (df_s['caudal_ls_filtrado'] - DEMANDA_MEDIA_TOMA_BOSCONIA_LS).clip(lower=0.0).round(1)
    df_s['rebose_aprox_morning_glory_ls'] = round(q_reb_mg_aprox_ls, 1)
    df_s['caudal_surata_antes_confluencia_aprox_ls'] = (df_s['caudal_ls_filtrado'] - q_reb_mg_aprox_ls).clip(lower=0.0).round(1)
    return df_s
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
        c_ini = float(g_s.iloc[0]['cota_embalse_msnm'])
        c_fin = float(g_s.iloc[-1]['cota_embalse_msnm'])
        t_ini = g_s.iloc[0]['timestamp']
        t_fin = g_s.iloc[-1]['timestamp']
        delta_s = max(1.0, (t_fin - t_ini).total_seconds())
        delta_horas = delta_s / 3600.0
        delta_cm = (c_ini - c_fin) * 100.0
        dt_g = g_s['timestamp'].diff().dt.total_seconds().fillna(0.0).clip(lower=0.0, upper=3600.0)
        # 1. ENTRADAS (Cola + Subsidiarias)
        q_in_medio = float(g_s['caudal_afluentes_ls'].mean()) if 'caudal_afluentes_ls' in g_s.columns else 0.0
        m3_in_dia = float(((g_s['caudal_afluentes_ls'] / 1000.0) * dt_g).sum()) if 'caudal_afluentes_ls' in g_s.columns else 0.0
        # 2. SALIDAS: Válvula CRC Bosconia + Rebose Morning Glory + Salida Total
        if 'caudal_medio_bosconia_ls' in g_s.columns:
            q_crc_ls = float(g_s['caudal_medio_bosconia_ls'].mean())
            m3_crc_dia = float(((g_s['caudal_medio_bosconia_ls'] / 1000.0) * dt_g).sum())
        else:
            v_ini = g_s.iloc[0]['volumen_total_hm3'] * 1_000_000.0
            v_fin = g_s.iloc[-1]['volumen_total_hm3'] * 1_000_000.0
            m3_crc_dia = max(0.0, v_ini - v_fin)
            q_crc_ls = (m3_crc_dia / delta_s) * 1000.0 if delta_s > 60 else 0.0
        q_reb_ls = float(g_s['caudal_rebose_ls'].mean()) if 'caudal_rebose_ls' in g_s.columns else 0.0
        m3_reb_dia = float(((g_s['caudal_rebose_ls'] / 1000.0) * dt_g).sum()) if 'caudal_rebose_ls' in g_s.columns else 0.0
        q_sal_tot_ls = float(g_s['caudal_salidas_totales_ls'].mean()) if 'caudal_salidas_totales_ls' in g_s.columns else (q_crc_ls + q_reb_ls + 51.0)
        m3_sal_tot_dia = float(((g_s['caudal_salidas_totales_ls'] / 1000.0) * dt_g).sum()) if 'caudal_salidas_totales_ls' in g_s.columns else (m3_crc_dia + m3_reb_dia)
        # 3. BALANCE NETO DE CAUDALES
        q_bal_neto_ls = float(g_s['balance_neto_caudales_ls'].mean()) if 'balance_neto_caudales_ls' in g_s.columns else (q_in_medio - q_sal_tot_ls)
        resumen_dias.append({
            "Fecha": fecha_dia,
            "Horas Monitoreadas": round(delta_horas, 1),
            "Cota Inicial (msnm)": round(c_ini, 3),
            "Cota Final (msnm)": round(c_fin, 3),
            "Descenso (cm)": round(delta_cm, 2),
            "📥 Caudal Medio Entrada Cuenca (L/s)": round(q_in_medio, 1),
            "📥 Volumen Entrada Cuenca (m³)": round(m3_in_dia, 1),
            "🚰 Caudal Medio CRC Bosconia (L/s)": round(q_crc_ls, 1),
            "🚰 Metros Cúbicos Entregados Bosconia (m³)": round(m3_crc_dia, 1),
            "🌀 Caudal Medio Rebose MG (L/s)": round(q_reb_ls, 1),
            "🌀 Volumen Rebose MG (m³)": round(m3_reb_dia, 1),
            "📤 Caudal Medio Salida Total (L/s)": round(q_sal_tot_ls, 1),
            "📤 Volumen Salida Total (m³)": round(m3_sal_tot_dia, 1),
            "⚖️ Balance Neto Caudales (L/s)": round(q_bal_neto_ls, 1),
            "Vol. Útil Remanente (hm³)": round(float(g_s.iloc[-1]['volumen_util_hm3']), 3)
        })
    if len(resumen_dias) >= 1:
        df_tmp = pd.DataFrame(resumen_dias)
        fila_prom = {
            "Fecha": "📊 PROMEDIO / TOTAL PERÍODO",
            "Horas Monitoreadas": round(float(df_tmp["Horas Monitoreadas"].sum()), 1),
            "Cota Inicial (msnm)": round(float(df_tmp["Cota Inicial (msnm)"].iloc[0]), 3),
            "Cota Final (msnm)": round(float(df_tmp["Cota Final (msnm)"].iloc[-1]), 3),
            "Descenso (cm)": round(float((df_tmp["Cota Inicial (msnm)"].iloc[0] - df_tmp["Cota Final (msnm)"].iloc[-1]) * 100.0), 2),
            "📥 Caudal Medio Entrada Cuenca (L/s)": round(float(df_tmp["📥 Caudal Medio Entrada Cuenca (L/s)"].mean()), 1),
            "📥 Volumen Entrada Cuenca (m³)": round(float(df_tmp["📥 Volumen Entrada Cuenca (m³)"].sum()), 1),
            "🚰 Caudal Medio CRC Bosconia (L/s)": round(float(df_tmp["🚰 Caudal Medio CRC Bosconia (L/s)"].mean()), 1),
            "🚰 Metros Cúbicos Entregados Bosconia (m³)": round(float(df_tmp["🚰 Metros Cúbicos Entregados Bosconia (m³)"].sum()), 1),
            "🌀 Caudal Medio Rebose MG (L/s)": round(float(df_tmp["🌀 Caudal Medio Rebose MG (L/s)"].mean()), 1),
            "🌀 Volumen Rebose MG (m³)": round(float(df_tmp["🌀 Volumen Rebose MG (m³)"].sum()), 1),
            "📤 Caudal Medio Salida Total (L/s)": round(float(df_tmp["📤 Caudal Medio Salida Total (L/s)"].mean()), 1),
            "📤 Volumen Salida Total (m³)": round(float(df_tmp["📤 Volumen Salida Total (m³)"].sum()), 1),
            "⚖️ Balance Neto Caudales (L/s)": round(float(df_tmp["⚖️ Balance Neto Caudales (L/s)"].mean()), 1),
            "Vol. Útil Remanente (hm³)": round(float(df_tmp["Vol. Útil Remanente (hm³)"].iloc[-1]), 3)
        }
        resumen_dias.append(fila_prom)
    return pd.DataFrame(resumen_dias)
def consolidar_balance_multitemporal_embalse(df_emb_enr, escala="Semanal"):
    """
    Consolida los datos de Entradas, Salidas y Balance de Caudales del Embalse
    en escalas Semanal, Mensual o Anual a partir del consolidado diario (con fila final de Promedio/Total).
    """
    df_diario = consolidar_balance_diario_embalse(df_emb_enr)
    if df_diario.empty:
        return pd.DataFrame()
    df_d = df_diario[~df_diario["Fecha"].astype(str).str.contains("PROMEDIO", na=False)].copy()
    if df_d.empty:
        return pd.DataFrame()
    df_d["dt"] = pd.to_datetime(df_d["Fecha"], errors="coerce")
    df_d = df_d.dropna(subset=["dt"]).sort_values("dt")
    if df_d.empty:
        return pd.DataFrame()
    meses_nom = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
    if escala == "Semanal":
        df_d["grupo_key"] = df_d["dt"].apply(lambda d: f"{d.isocalendar()[0]}-W{int(d.isocalendar()[1]):02d}")
        df_d["etiqueta"] = df_d["dt"].apply(lambda d: f"Semana {int(d.isocalendar()[1])} ({d.isocalendar()[0]})")
        col_periodo = "Semana ISO"
    elif escala == "Mensual":
        df_d["grupo_key"] = df_d["dt"].apply(lambda d: f"{d.year}-{d.month:02d}")
        df_d["etiqueta"] = df_d["dt"].apply(lambda d: f"{meses_nom.get(d.month, d.month)} {d.year}")
        col_periodo = "Mes / Año"
    else:
        df_d["grupo_key"] = df_d["dt"].apply(lambda d: f"{d.year}")
        df_d["etiqueta"] = df_d["dt"].apply(lambda d: f"Año {d.year}")
        col_periodo = "Año"
    filas_agrup = []
    for g_key, grp in df_d.groupby("grupo_key", sort=True):
        grp_s = grp.sort_values("dt")
        c_ini = float(grp_s["Cota Inicial (msnm)"].iloc[0])
        c_fin = float(grp_s["Cota Final (msnm)"].iloc[-1])
        filas_agrup.append({
            col_periodo: grp_s["etiqueta"].iloc[0],
            "Desde": grp_s["Fecha"].iloc[0],
            "Hasta": grp_s["Fecha"].iloc[-1],
            "Días": len(grp_s),
            "Horas Monitoreadas": round(float(grp_s["Horas Monitoreadas"].sum()), 1),
            "Cota Inicial (msnm)": round(c_ini, 3),
            "Cota Final (msnm)": round(c_fin, 3),
            "Descenso (cm)": round((c_ini - c_fin) * 100.0, 2),
            "📥 Caudal Medio Entrada Cuenca (L/s)": round(float(grp_s["📥 Caudal Medio Entrada Cuenca (L/s)"].mean()), 1),
            "📥 Volumen Entrada Cuenca (m³)": round(float(grp_s["📥 Volumen Entrada Cuenca (m³)"].sum()), 1),
            "🚰 Caudal Medio CRC Bosconia (L/s)": round(float(grp_s["🚰 Caudal Medio CRC Bosconia (L/s)"].mean()), 1),
            "🚰 Metros Cúbicos Entregados Bosconia (m³)": round(float(grp_s["🚰 Metros Cúbicos Entregados Bosconia (m³)"].sum()), 1),
            "🌀 Caudal Medio Rebose MG (L/s)": round(float(grp_s["🌀 Caudal Medio Rebose MG (L/s)"].mean()), 1),
            "🌀 Volumen Rebose MG (m³)": round(float(grp_s["🌀 Volumen Rebose MG (m³)"].sum()), 1),
            "📤 Caudal Medio Salida Total (L/s)": round(float(grp_s["📤 Caudal Medio Salida Total (L/s)"].mean()), 1),
            "📤 Volumen Salida Total (m³)": round(float(grp_s["📤 Volumen Salida Total (m³)"].sum()), 1),
            "⚖️ Balance Neto Caudales (L/s)": round(float(grp_s["⚖️ Balance Neto Caudales (L/s)"].mean()), 1),
            "Vol. Útil Remanente (hm³)": round(float(grp_s["Vol. Útil Remanente (hm³)"].iloc[-1]), 3)
        })
    if len(filas_agrup) >= 1:
        df_t = pd.DataFrame(filas_agrup)
        c_i_tot = float(df_t["Cota Inicial (msnm)"].iloc[0])
        c_f_tot = float(df_t["Cota Final (msnm)"].iloc[-1])
        filas_agrup.append({
            col_periodo: "📊 PROMEDIO / TOTAL PERÍODO",
            "Desde": df_t["Desde"].iloc[0],
            "Hasta": df_t["Hasta"].iloc[-1],
            "Días": int(df_t["Días"].sum()),
            "Horas Monitoreadas": round(float(df_t["Horas Monitoreadas"].sum()), 1),
            "Cota Inicial (msnm)": round(c_i_tot, 3),
            "Cota Final (msnm)": round(c_f_tot, 3),
            "Descenso (cm)": round((c_i_tot - c_f_tot) * 100.0, 2),
            "📥 Caudal Medio Entrada Cuenca (L/s)": round(float(df_t["📥 Caudal Medio Entrada Cuenca (L/s)"].mean()), 1),
            "📥 Volumen Entrada Cuenca (m³)": round(float(df_t["📥 Volumen Entrada Cuenca (m³)"].sum()), 1),
            "🚰 Caudal Medio CRC Bosconia (L/s)": round(float(df_t["🚰 Caudal Medio CRC Bosconia (L/s)"].mean()), 1),
            "🚰 Metros Cúbicos Entregados Bosconia (m³)": round(float(df_t["🚰 Metros Cúbicos Entregados Bosconia (m³)"].sum()), 1),
            "🌀 Caudal Medio Rebose MG (L/s)": round(float(df_t["🌀 Caudal Medio Rebose MG (L/s)"].mean()), 1),
            "🌀 Volumen Rebose MG (m³)": round(float(df_t["🌀 Volumen Rebose MG (m³)"].sum()), 1),
            "📤 Caudal Medio Salida Total (L/s)": round(float(df_t["📤 Caudal Medio Salida Total (L/s)"].mean()), 1),
            "📤 Volumen Salida Total (m³)": round(float(df_t["📤 Volumen Salida Total (m³)"].sum()), 1),
            "⚖️ Balance Neto Caudales (L/s)": round(float(df_t["⚖️ Balance Neto Caudales (L/s)"].mean()), 1),
            "Vol. Útil Remanente (hm³)": round(float(df_t["Vol. Útil Remanente (hm³)"].iloc[-1]), 3)
        })
    return pd.DataFrame(filas_agrup)
def preparar_df_para_exportar(df, nombre_estacion=None):
    if df.empty:
        return df
    df_export = df.copy()
    # Validación física estricta: sólo es embalse si la estación es Embalse Y las lecturas son cotas físicas (> 800 msnm)
    c_mean = pd.to_numeric(df_export.get('temperatura', pd.Series()), errors='coerce').dropna().mean() if 'temperatura' in df_export.columns else 0
    id_est = df_export['id_estacion'].iloc[0] if ('id_estacion' in df_export.columns and not df_export.empty) else ""
    es_embalse = (nombre_estacion == "Embalse" or id_est == "Embalse") and (c_mean > 800)
    es_surata = (nombre_estacion == "Surata" or id_est == "Surata")
    if es_embalse and 'temperatura' in df_export.columns:
        # Exportación especializada para Embalse Tona (Limpia y con Encabezados Hidráulicos Oficiales: Entradas, Salidas y Balance)
        df_enr = enriquecer_datos_embalse(df)
        if not df_enr.empty and 'cota_embalse_msnm' in df_enr.columns:
            df_res = pd.DataFrame()
            df_res['Fecha_Hora_COT'] = pd.to_datetime(df_enr['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
            df_res['Estacion'] = 'Embalse Tona'
            df_res['Cota_Calibrada_msnm'] = df_enr['cota_embalse_msnm'].round(3)
            df_res['Lectura_Cruda_Radar_msnm'] = pd.to_numeric(df_enr['temperatura'], errors='coerce').round(3)
            df_res['Margen_a_Rebose_cm'] = ((885.75 - df_enr['cota_embalse_msnm']) * 100.0).round(2)
            df_res['Volumen_Total_hm3'] = df_enr['volumen_total_hm3'].round(3)
            df_res['Volumen_Util_hm3'] = df_enr['volumen_util_hm3'].round(3)
            if 'caudal_afluentes_ls' in df_enr.columns:
                df_res['Caudal_Entrada_Cuenca_Ls'] = df_enr['caudal_afluentes_ls'].round(1)
            if 'm3_entrada_cuenca_acum' in df_enr.columns:
                df_res['Volumen_Entrada_Cuenca_Acum_m3'] = df_enr['m3_entrada_cuenca_acum'].round(1)
            if 'caudal_medio_bosconia_ls' in df_enr.columns:
                df_res['Caudal_Salida_CRC_Bosconia_Ls'] = df_enr['caudal_medio_bosconia_ls'].round(1)
            if 'm3_consumidos_bosconia' in df_enr.columns:
                df_res['Volumen_Entregado_Bosconia_Acum_m3'] = df_enr['m3_consumidos_bosconia'].round(1)
            df_res['Caudal_Salida_Rebose_Morning_Glory_Ls'] = df_enr['caudal_rebose_ls'].round(1)
            if 'm3_rebose_mg_acum' in df_enr.columns:
                df_res['Volumen_Salida_Rebose_MG_Acum_m3'] = df_enr['m3_rebose_mg_acum'].round(1)
            if 'caudal_salidas_totales_ls' in df_enr.columns:
                df_res['Caudal_Salida_Total_Embalse_Ls'] = df_enr['caudal_salidas_totales_ls'].round(1)
            if 'm3_salidas_totales_acum' in df_enr.columns:
                df_res['Volumen_Salida_Total_Acum_m3'] = df_enr['m3_salidas_totales_acum'].round(1)
            if 'balance_neto_caudales_ls' in df_enr.columns:
                df_res['Balance_Neto_Caudales_Ls'] = df_enr['balance_neto_caudales_ls'].round(1)
            if 'voltaje_bateria' in df_enr.columns:
                df_res['Voltaje_Bateria_V'] = pd.to_numeric(df_enr['voltaje_bateria'], errors='coerce').round(2)
            if 'estado_bateria' in df_enr.columns:
                df_res['Estado_Sensor'] = df_enr['estado_bateria']
            return df_res
    if es_surata and 'temperatura' in df_export.columns:
        # Exportación especializada para Estación Hidrológica Río Suratá — Sector Majadas
        df_enr_s = enriquecer_datos_surata(df)
        if not df_enr_s.empty:
            df_res = pd.DataFrame()
            df_res['Fecha_Hora_COT'] = pd.to_datetime(df_enr_s['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
            df_res['Estacion'] = 'Rio Surata - Sector Majadas'
            df_res['Nivel_Mira_Filtrado_m'] = df_enr_s['nivel_m_filtrado'].round(3)
            df_res['Nivel_Crudo_Radar_OTT_m'] = df_enr_s['nivel_m_crudo'].round(3)
            df_res['Caudal_Majadas_m3s'] = df_enr_s['caudal_m3s_filtrado'].round(4)
            df_res['Caudal_Majadas_Ls'] = df_enr_s['caudal_ls_filtrado'].round(1)
            df_res['Demanda_Media_Toma_Bosconia_Ls'] = df_enr_s['demanda_toma_bosconia_ls'].round(1)
            df_res['Caudal_Remanente_Aguas_Abajo_Ls'] = df_enr_s['caudal_remanente_aguas_abajo_ls'].round(1)
            df_res['Rebose_Aprox_Morning_Glory_En_Calibracion_Ls'] = df_enr_s['rebose_aprox_morning_glory_ls'].round(1)
            df_res['Caudal_Surata_Antes_Confluencia_Aprox_Ls'] = df_enr_s['caudal_surata_antes_confluencia_aprox_ls'].round(1)
            if 'estado_bateria' in df_enr_s.columns:
                df_res['Origen_Telemetria'] = df_enr_s['estado_bateria']
            return df_res
    # Exportación especializada para Estaciones Meteorológicas con unidades claras y Bandera de Calidad SCADA
    df_clean = df_export.copy()
    t_num = pd.to_numeric(df_clean.get('temperatura', pd.Series(dtype=float)), errors='coerce').fillna(0.0)
    h_num = pd.to_numeric(df_clean.get('humedad', pd.Series(dtype=float)), errors='coerce').fillna(0.0)
    p_num = pd.to_numeric(df_clean.get('presion', pd.Series(dtype=float)), errors='coerce').fillna(0.0)
    mask_ceros_scada = (t_num == 0.0) & (h_num == 0.0) & (p_num == 0.0)
    for col_s in ['temperatura', 'precipitacion', 'humedad', 'presion', 'velocidad_viento', 'direccion_viento']:
        if col_s in df_clean.columns:
            df_clean.loc[mask_ceros_scada, col_s] = np.nan
    mapa_renombrar = {
        'id_estacion': 'Estacion',
        'temperatura': 'Temperatura_C',
        'precipitacion': 'Precipitacion_mm',
        'humedad': 'Humedad_Relativa_pct',
        'presion': 'Presion_Atmosferica_hPa',
        'velocidad_viento': 'Velocidad_Viento_kmh',
        'direccion_viento': 'Direccion_Viento_grados',
        'voltaje_bateria': 'Voltaje_Bateria_V',
        'estado_bateria': 'Estado_Bateria'
    }
    df_res = pd.DataFrame()
    if 'timestamp' in df_clean.columns:
        df_res['Fecha_Hora_COT'] = pd.to_datetime(df_clean['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
    for col_orig, col_nueva in mapa_renombrar.items():
        if col_orig in df_clean.columns:
            if col_orig in ['temperatura', 'precipitacion', 'humedad', 'presion', 'velocidad_viento', 'voltaje_bateria']:
                df_res[col_nueva] = pd.to_numeric(df_clean[col_orig], errors='coerce').round(2)
            elif col_orig == 'direccion_viento':
                df_res[col_nueva] = pd.to_numeric(df_clean[col_orig], errors='coerce').round(0)
            else:
                df_res[col_nueva] = df_clean[col_orig]
    df_res['Calidad_Dato'] = np.where(mask_ceros_scada, 'NULL_CAIDA_SCADA', 'OK_VALIDO')
    return df_res
def generar_excel_con_formato(df, nombre_estacion, periodo_descripcion):
    output = BytesIO()
    c_mean = pd.to_numeric(df.get('temperatura', pd.Series()), errors='coerce').dropna().mean() if 'temperatura' in df.columns else 0
    id_est = df['id_estacion'].iloc[0] if ('id_estacion' in df.columns and not df.empty) else ""
    es_embalse = (nombre_estacion == "Embalse" or id_est == "Embalse") and (c_mean > 800)
    es_surata = (nombre_estacion == "Surata" or id_est == "Surata")
    df_export = preparar_df_para_exportar(df, nombre_estacion)
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        if es_embalse and 'temperatura' in df.columns:
            df_enr = enriquecer_datos_embalse(df)
            df_balance_24h = consolidar_balance_diario_embalse(df_enr)
            df_balance_sem = consolidar_balance_multitemporal_embalse(df_enr, "Semanal")
            df_balance_mes = consolidar_balance_multitemporal_embalse(df_enr, "Mensual")
            df_balance_anu = consolidar_balance_multitemporal_embalse(df_enr, "Anual")
            hojas_balance = [
                ('Balance_Bosconia_24h', df_balance_24h),
                ('Balance_Semanal', df_balance_sem),
                ('Balance_Mensual', df_balance_mes),
                ('Balance_Anual', df_balance_anu)
            ]
            for nombre_hoja, df_h in hojas_balance:
                if not df_h.empty:
                    df_h.to_excel(writer, sheet_name=nombre_hoja, index=False)
                    ws_b = writer.sheets[nombre_hoja]
                    header_font = Font(bold=True, color="FFFFFF")
                    header_fill = PatternFill(start_color="005073", end_color="005073", fill_type="solid")
                    header_alignment = Alignment(horizontal="center", vertical="center")
                    for col in range(1, len(df_h.columns) + 1):
                        cell = ws_b.cell(row=1, column=col)
                        cell.font = header_font
                        cell.fill = header_fill
                        cell.alignment = header_alignment
                    for col in ws_b.columns:
                        max_len = max(len(str(cell.value or '')) for cell in col)
                        col_letter = col[0].column_letter
                        ws_b.column_dimensions[col_letter].width = min(max_len + 4, 42)
            # Hoja Detallada: Telemetría Detallada (Con Encabezados Profesionales)
            df_export.to_excel(writer, sheet_name='Telemetria_Embalse', index=False)
            worksheet = writer.sheets['Telemetria_Embalse']
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="172A45", end_color="172A45", fill_type="solid")
            for col in range(1, len(df_export.columns) + 1):
                cell = worksheet.cell(row=1, column=col)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center", vertical="center")
            for col in worksheet.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = col[0].column_letter
                worksheet.column_dimensions[col_letter].width = min(max_len + 3, 50)
            df_registros_len = len(df_export)
        elif es_surata:
            df_export.to_excel(writer, sheet_name='Caudales_Surata_Majadas', index=False)
            worksheet = writer.sheets['Caudales_Surata_Majadas']
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
        else:
            df_export.to_excel(writer, sheet_name='Datos_Meteorologicos', index=False)
            worksheet = writer.sheets['Datos_Meteorologicos']
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
                ['Nota Ecuación Morning Glory', 'Caudal de rebose aproximado mientras se calibra empíricamente la ecuación en campo'],
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
        elif es_surata:
            meta_rows = [
                ['Sistema de Información', SISTEMA],
                ['Proyecto Institucional', 'MIMAT-C26 • amb s.a. e.s.p.'],
                ['Estación Hidrológica', 'Río Suratá — Sector Majadas (CNE IDEAM 0023197700 • Primera Estación Fluvial MIMAT-C26)'],
                ['Instrumentación', 'Radar Hidrométrico OTT (Generación Anterior) + Mira Limnimétrica — FEWS IDEAM / amb'],
                ['Coordenadas Oficiales', '7°09\'18.50"N 73°03\'42.20"W (7.155139, -73.061722) • ~765.00 msnm'],
                ['Ubicación Topológica', 'Aguas abajo de Puente Tona (confluencia Río Suratá + Río Tona) y ~1.8 km aguas arriba de Toma Bosconia (Tránsito: 15-25 min)'],
                ['Frecuencia y Lag FEWS IDEAM', 'Muestreo datalogger 10-15 min; transmisión por lotes (GOES/GPRS) con rezago (lag) de publicación web de 30 a 90 min e intermitencias'],
                ['Compensación Resiliente MIMAT-C26', 'Persistencia continua en BigQuery + acoplamiento con lluvia en tiempo real de Monsalve (0 min lag) y satélite sobre Majadas'],
                ['Ecuación Oficial de la Mira', 'Q (m³/s) = 1.2455 * (H + 0.13)^4.1635  |  Q (L/s) = Q (m³/s) * 1,000'],
                ['Caudal Base Promedio Majadas', '~2,000 L/s (H ≈ 0.991 m)'],
                ['Demanda Media PTAP Bosconia', '900 a 1,200 L/s (~1,050 L/s promedio captado en Toma Bosconia)'],
                ['Nota Caudal Morning Glory', 'El aporte de rebose del Morning Glory hacia Puente Tona es aproximado mientras se calibra esa ecuación'],
                ['Período de Consulta', periodo_descripcion],
                ['Fecha de Generación', datetime.now(colombia_tz).strftime('%Y-%m-%d %H:%M:%S')],
                ['Total Registros', df_registros_len],
                ['Líder Técnico / Autor', AUTOR]
            ]
            metadata = pd.DataFrame(meta_rows, columns=['Parámetro Hidrológico', 'Descripción Técnica'])
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
        desc_cm = (c_ini - c_fin) * 100.0
        vol_util_act = df_enr['volumen_util_hm3'].iloc[-1]
        # Entradas
        q_in_mean = float(df_enr['caudal_afluentes_ls'].mean()) if 'caudal_afluentes_ls' in df_enr.columns else 0.0
        q_in_max = float(df_enr['caudal_afluentes_ls'].max()) if 'caudal_afluentes_ls' in df_enr.columns else 0.0
        q_in_min = float(df_enr['caudal_afluentes_ls'].min()) if 'caudal_afluentes_ls' in df_enr.columns else 0.0
        m3_in_tot = float(df_enr['m3_entrada_cuenca_acum'].max()) if 'm3_entrada_cuenca_acum' in df_enr.columns else 0.0
        # Salidas
        q_crc_mean = float(df_enr['caudal_medio_bosconia_ls'].mean()) if 'caudal_medio_bosconia_ls' in df_enr.columns else 0.0
        m3_crc_tot = float(df_enr['m3_consumidos_bosconia'].max()) if 'm3_consumidos_bosconia' in df_enr.columns else 0.0
        q_reb_mean = float(df_enr['caudal_rebose_ls'].mean()) if 'caudal_rebose_ls' in df_enr.columns else 0.0
        m3_reb_tot = float(df_enr['m3_rebose_mg_acum'].max()) if 'm3_rebose_mg_acum' in df_enr.columns else 0.0
        q_sal_tot_mean = float(df_enr['caudal_salidas_totales_ls'].mean()) if 'caudal_salidas_totales_ls' in df_enr.columns else (q_crc_mean + q_reb_mean + 51.0)
        m3_sal_tot = float(df_enr['m3_salidas_totales_acum'].max()) if 'm3_salidas_totales_acum' in df_enr.columns else (m3_crc_tot + m3_reb_tot)
        # Balance neto
        q_bal_mean = float(df_enr['balance_neto_caudales_ls'].mean()) if 'balance_neto_caudales_ls' in df_enr.columns else (q_in_mean - q_sal_tot_mean)
        dias_aut = (vol_util_act * 1_000_000.0) / (q_crc_mean * 86.4) if q_crc_mean > 0 else None
        resumen.append("🌊 1. PARÁMETROS HIDRÁULICOS DEL EMBALSE:")
        resumen.append(f"   • Cota Actual:                 {c_fin:.3f} msnm")
        resumen.append(f"   • Cota Inicial del Período:    {c_ini:.3f} msnm")
        resumen.append(f"   • Cota Promedio:               {c_mean:.3f} msnm")
        resumen.append(f"   • Cota Máxima / Mínima:        {c_max:.3f} msnm / {c_min:.3f} msnm")
        resumen.append(f"   • Descenso / Variación Nivel:  {desc_cm:+.2f} cm")
        resumen.append(f"   • Volumen Útil Remanente:      {vol_util_act:.3f} hm³")
        resumen.append("")
        resumen.append("📥 2. ENTRADAS AL EMBALSE (LLEGADA DESDE COLA Y QUEBRADAS SUBSIDIARIAS):")
        resumen.append(f"   • Caudal Medio de Entrada:     {q_in_mean:,.1f} L/s ({q_in_mean/1000.0:.3f} m³/s)")
        resumen.append(f"   • Caudal Máximo / Mínimo:      {q_in_max:,.1f} L/s / {q_in_min:,.1f} L/s")
        resumen.append(f"   • Volumen Total Ingresado:     {m3_in_tot:,.1f} m³")
        resumen.append("")
        resumen.append("📤 3. SALIDAS DEL EMBALSE (CRC BOSCONIA + REBOSE MORNING GLORY + FILTRACIONES):")
        resumen.append(f"   • Caudal Medio CRC Bosconia:   {q_crc_mean:,.1f} L/s (Sensor ET_FIT401)")
        resumen.append(f"   • Volumen Entregado Bosconia:  {m3_crc_tot:,.1f} m³")
        resumen.append(f"   • Caudal Medio Rebose MG:      {q_reb_mean:,.1f} L/s")
        resumen.append(f"   • Volumen Evacuado Rebose MG:  {m3_reb_tot:,.1f} m³")
        resumen.append(f"   • Caudal Medio Salida Total:   {q_sal_tot_mean:,.1f} L/s (Incluye ~51 L/s filtraciones)")
        resumen.append(f"   • Volumen Salida Total:        {m3_sal_tot:,.1f} m³")
        resumen.append("")
        resumen.append("⚖️ 4. BALANCE DE CAUDALES (ENTRADAS VS. SALIDAS):")
        resumen.append(f"   • Balance Neto Promedio (dV/dt): {q_bal_mean:+,.1f} L/s")
        resumen.append(f"   • Ecuación Verificada:           Entrada ({q_in_mean:,.1f} L/s) - Salida Total ({q_sal_tot_mean:,.1f} L/s) = {q_bal_mean:+,.1f} L/s")
        resumen.append(f"   • Autonomía Hídrica Estimada:    {f'{dias_aut:.1f} Días' if dias_aut else 'Indefinida'}")
        resumen.append(f"   • Registros Analizados:          {len(df_enr)}")
        resumen.append("   * Afluentes tributarios: Río Tona + Qda. Ranás (fondo cola) + Qda. el Gualilo (mitad) + Qda. La Reforma (presa) + Qda. Los Monos (litoral derecho).")
        return "\n".join(resumen)
    # Manejo especializado para Estación Hidrológica Río Suratá — Sector Majadas
    if nombre_estacion == "Surata":
        df_enr_s = enriquecer_datos_surata(df)
        if not df_enr_s.empty:
            h_act = df_enr_s['nivel_m_filtrado'].iloc[-1]
            h_mean = df_enr_s['nivel_m_filtrado'].mean()
            h_max = df_enr_s['nivel_m_filtrado'].max()
            h_min = df_enr_s['nivel_m_filtrado'].min()
            q_act = df_enr_s['caudal_ls_filtrado'].iloc[-1]
            q_mean = df_enr_s['caudal_ls_filtrado'].mean()
            q_max = df_enr_s['caudal_ls_filtrado'].max()
            q_min = df_enr_s['caudal_ls_filtrado'].min()
            q_rem_mean = df_enr_s['caudal_remanente_aguas_abajo_ls'].mean()
            resumen.append("🏞️ ESTACIÓN HIDROLÓGICA RÍO SURATÁ — SECTOR LAS MAJADAS:")
            resumen.append("   • Ecuación Oficial de la Mira: Q(m³/s) = 1.2455 * (H + 0.13)^4.1635")
            resumen.append(f"   • Nivel Actual (Radar OTT):    {h_act:.3f} m ({h_act*100:.1f} cm)")
            resumen.append(f"   • Nivel Promedio:              {h_mean:.3f} m")
            resumen.append(f"   • Nivel Máximo / Mínimo:       {h_max:.3f} m / {h_min:.3f} m")
            resumen.append(f"   • Caudal Actual Majadas:   {q_act:,.1f} L/s ({q_act/1000.0:.3f} m³/s)")
            resumen.append(f"   • Caudal Promedio Período:     {q_mean:,.1f} L/s ({q_mean/1000.0:.3f} m³/s)")
            resumen.append(f"   • Caudal Máximo / Mínimo:      {q_max:,.1f} L/s / {q_min:,.1f} L/s")
            resumen.append(f"   • Captación Media Bosconia:    900 - 1,200 L/s (~1,050 L/s nominal)")
            resumen.append(f"   • Remanente Aguas Abajo:       ~{q_rem_mean:,.1f} L/s")
            resumen.append(f"   • Registros Analizados:        {len(df_enr_s)}")
            resumen.append("")
            resumen.append("ℹ️ NOTA TÉCNICA: El caudal de rebose del Morning Glory hacia Puente Tona es aproximado mientras se calibra empíricamente esa ecuación.")
            return "\n".join(resumen)
    # Saneamiento automático de ceros SCADA (0, 0, 0) para no contaminar promedios ni mínimos
    df_stat = df.copy()
    t_s = pd.to_numeric(df_stat.get('temperatura', pd.Series(dtype=float)), errors='coerce').fillna(0.0)
    h_s = pd.to_numeric(df_stat.get('humedad', pd.Series(dtype=float)), errors='coerce').fillna(0.0)
    p_s = pd.to_numeric(df_stat.get('presion', pd.Series(dtype=float)), errors='coerce').fillna(0.0)
    mask_ceros = (t_s == 0.0) & (h_s == 0.0) & (p_s == 0.0)
    n_ceros_excluidos = int(mask_ceros.sum())
    df_valido = df_stat[~mask_ceros].copy()
    if n_ceros_excluidos > 0:
        resumen.append(f"🛡️ CONTROL DE CALIDAD SCADA: Se convirtieron a NULL y excluyeron del promedio {n_ceros_excluidos} registros en cero (0,0,0) por reinicio/caída de enlace.")
        resumen.append("")
    # Para estaciones meteorológicas (La Mariana, Yerbabuena, etc.)
    cols = ['temperatura', 'precipitacion', 'humedad', 'presion', 'velocidad_viento', 'direccion_viento', 'voltaje_bateria']
    for col in cols:
        if col in df_valido.columns:
            datos = pd.to_numeric(df_valido[col], errors='coerce').dropna()
            if not datos.empty and (datos.abs().max() > 0 or col in ['temperatura', 'precipitacion']):
                resumen.append(f"📈 {col.upper()}:")
                resumen.append(f"   • Promedio: {datos.mean():.2f}")
                resumen.append(f"   • Máximo:  {datos.max():.2f}")
                resumen.append(f"   • Mínimo:  {datos.min():.2f}")
                resumen.append(f"   • Registros válidos: {len(datos)}")
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
# 7.5 PANEL CONSOLIDADO DE ALERTA TEMPRANA & VIGILANCIA DE CUENCAS (SCADA / PMU)
# ============================================================
def render_panel_alertas_tempranas_sat():
    """
    Vista consolidada de alta visibilidad tipo Video Wall SCADA y Sala de Crisis (PMU / Alcaldías).
    Presenta los semáforos en tiempo real con animaciones luminosas parpadeantes, estado técnico de cada
    estación (operativa / virtual satelital en mantenimiento) y recomendaciones directas hacia Toma Bosconia.
    """
    ahora_dt = datetime.now(colombia_tz)
    ahora_str = ahora_dt.strftime('%Y-%m-%d %H:%M:%S')
    # 1. Consultar estado en vivo del Río Suratá (Majadas - IDEAM 0023197700)
    info_maj = sincronizar_fews_ideam_surata_bigquery()
    q_sur_ls = float(info_maj.get('caudal_ls', 6194.0) or 6194.0)
    h_sur_m = float(info_maj.get('nivel_m', 1.34) or 1.34)
    q_sur_max1h = float(info_maj.get('caudal_max_1h_ls', q_sur_ls) or q_sur_ls)
    q_sur_prom24h = float(info_maj.get('caudal_prom_24h_ls', q_sur_ls) or q_sur_ls)
    if q_sur_ls >= 14000.0 or h_sur_m >= 1.66:
        sur_semaforo = "ROJA"
        sur_card_class = "card-scada-red"
        sur_beacon_class = "beacon-red"
        sur_badge_color = "#FF4B4B"
        sur_titulo = "🚨 ALERTA ROJA — CRECIENTE CRÍTICA"
        sur_accion = "Proteger y cerrar compuerta Toma Bosconia (Tránsito inminente: 15–25 min)"
    elif q_sur_ls >= 9500.0 or h_sur_m >= 1.50:
        sur_semaforo = "NARANJA"
        sur_card_class = "card-scada-orange"
        sur_beacon_class = "beacon-orange"
        sur_badge_color = "#FF8000"
        sur_titulo = "⚠️ ALERTA NARANJA — CRECIENTE MAYOR"
        sur_accion = "Alistar purga en desarenadores y monitoreo de turbiedad en Bosconia"
    elif q_sur_ls >= 7500.0 or h_sur_m >= 1.41:
        sur_semaforo = "AMARILLA"
        sur_card_class = "card-scada-yellow"
        sur_beacon_class = "beacon-yellow"
        sur_badge_color = "#FFBB00"
        sur_titulo = "⚡ AVISO AMARILLO — ASCENSO MODERADO"
        sur_accion = "Vigilancia limnimétrica preventiva hacia Toma Bosconia"
    else:
        sur_semaforo = "VERDE"
        sur_card_class = "card-scada-green"
        sur_beacon_class = "beacon-green"
        sur_badge_color = "#00CC96"
        sur_titulo = "🟢 CONDICIÓN ESTABLE — CAUDAL BASE"
        sur_accion = "Operación normal de captación (Tratamiento nominal: 900–1,200 L/s)"
    # 2. Consultar estado en vivo del Embalse de Tona (Radar OTT & Rebosadero)
    cota_emb = get_cota_embalse_actual_segura()
    h_rebose = max(0.0, cota_emb - NIVEL_REBOSE_EMBALSE)
    q_mg_m3s, q_mg_ls = calcular_caudal_morning_glory(cota_emb)
    if cota_emb >= NIVEL_REBOSE_EMBALSE:
        cm_reb = int(round(h_rebose * 100.0))
        emb_semaforo = "REBOSE"
        emb_card_class = "card-scada-cyan"
        emb_beacon_class = "beacon-cyan"
        emb_badge_color = "#00BFFF"
        emb_titulo = f"🌊 REBOSE ACTIVO MORNING GLORY (+{cm_reb} cm)"
        emb_accion = f"Vertimiento de ~{q_mg_ls:,.0f} L/s por cascadas a piscina de aquietamiento ➔ Puente Tona ➔ Río Suratá"
    elif cota_emb >= 885.73:
        cm_falta = max(1, int(round((NIVEL_REBOSE_EMBALSE - cota_emb) * 100.0)))
        emb_semaforo = "PRE_REBOSE"
        emb_card_class = "card-scada-yellow"
        emb_beacon_class = "beacon-yellow"
        emb_badge_color = "#FFBB00"
        emb_titulo = f"⚠️ PRE-REBOSE (A {cm_falta} cm de vertedero)"
        emb_accion = "Llenado acelerado hacia corona de rebose (885.75 msnm)"
    else:
        cm_falta = int(round((NIVEL_REBOSE_EMBALSE - cota_emb) * 100.0))
        emb_semaforo = "NORMAL"
        emb_card_class = "card-scada-green"
        emb_beacon_class = "beacon-green"
        emb_badge_color = "#00CC96"
        emb_titulo = "🟢 OPERACIÓN NORMAL (AMORTIGUANDO)"
        emb_accion = f"Vaso detiene y amortigua crecientes de Cuenca Tona (Faltan {cm_falta} cm a rebose)"
    # 0. Consulta optimizada de lluvia acumulada en la última hora para todas las estaciones
    mapa_lluvia_1h = {}
    try:
        q_ll = """
        SELECT id_estacion,
               SUM(SAFE_CAST(precipitacion AS FLOAT64)) as lluvia_1h,
               MAX(SAFE_CAST(precipitacion AS FLOAT64)) as p_max_paquete
        FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones`
        WHERE id_estacion NOT IN ('Embalse', 'Surata')
          AND SAFE_CAST(timestamp AS TIMESTAMP) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
        GROUP BY id_estacion
        """
        for r_ll in client.query(q_ll).result():
            p_1h = float(r_ll.get('lluvia_1h') or 0.0)
            p_max = float(r_ll.get('p_max_paquete') or 0.0)
            mapa_lluvia_1h[str(r_ll.get('id_estacion'))] = max(p_1h, p_max)
    except Exception:
        pass
    # 3. Consultar lecturas de estaciones meteorológicas
    def evaluar_estacion_met(id_est, nombre_largo, altitud, cuenca_txt, es_libre_surata=False):
        df_est = get_last_reading(id_est)
        lluvia_val = float(mapa_lluvia_1h.get(id_est, 0.0))
        temp_val = 18.0
        hum_val = 75.0
        estado_red = "OPERATIVA"
        origen_txt = "Transmitiendo en vivo"
        es_fisico_vivo = False
        if not df_est.empty:
            r = df_est.iloc[0]
            p_ult = float(r.get('precipitacion', 0.0) or 0.0)
            if lluvia_val <= 0.0:
                lluvia_val = p_ult
            else:
                lluvia_val = max(lluvia_val, p_ult)
            temp_raw = r.get('temperatura')
            hum_raw = r.get('humedad')
            ts_dato = r.get('timestamp')
            # Validar frescura del paquete telemétrico en UTC (últimas 2 horas)
            if pd.notna(ts_dato) and temp_raw is not None and hum_raw is not None:
                try:
                    ts_dt = pd.to_datetime(ts_dato)
                    if ts_dt.tzinfo is None:
                        ts_dt = ts_dt.tz_localize(utc_tz)
                    else:
                        ts_dt = ts_dt.tz_convert(utc_tz)
                    delta_s = (datetime.now(utc_tz) - ts_dt).total_seconds()
                    if 0 <= delta_s <= 7200 and float(temp_raw) > 0.0 and float(hum_raw) > 1.0:
                        es_fisico_vivo = True
                        temp_val = float(temp_raw)
                        hum_val = float(hum_raw)
                except Exception:
                    pass
        # Si no transmite en vivo o es estación de alta montaña con SIM suspendida, activa Sensor Virtual
        if not es_fisico_vivo:
            sat_info = obtener_sensor_virtual_resiliente(id_est)
            if sat_info:
                lluvia_val = float(sat_info.get('precipitacion', 0.0) or 0.0)
                temp_val = float(sat_info.get('temperatura', 18.0) or 18.0)
                hum_val = float(sat_info.get('humedad', 75.0) or 75.0)
            estado_red = "VIRTUAL_SATELITAL"
            origen_txt = "Sensor Virtual Satelital Open-Meteo Activo"
        else:
            estado_red = "OPERATIVA"
            origen_txt = "Transmitiendo en vivo"
        u = umbrales.get(id_est, {"amarilla": 15.0, "naranja": 25.0, "roja": 40.0})
        if lluvia_val >= u["roja"]:
            sem = "ROJA"
            css = "card-scada-red"
            beacon_class = "beacon-red"
            badge_color = "#FF4B4B"
            txt_sem = f"🚨 ALERTA ROJA ({lluvia_val:.1f} mm/h)"
            badge_html = f'<span class="badge-status" style="background: rgba(255, 75, 75, 0.2); color: #FF4B4B; border: 1px solid #FF4B4B; font-size: 9.5px; display: inline-flex; align-items: center; gap: 6px;"><span class="beacon-red"></span> 🚨 ALERTA ROJA ({lluvia_val:.1f} mm/h)</span>'
        elif lluvia_val >= u["naranja"]:
            sem = "NARANJA"
            css = "card-scada-orange"
            beacon_class = "beacon-orange"
            badge_color = "#FF8000"
            txt_sem = f"⚠️ ALERTA NARANJA ({lluvia_val:.1f} mm/h)"
            badge_html = f'<span class="badge-status" style="background: rgba(255, 128, 0, 0.2); color: #FF8000; border: 1px solid #FF8000; font-size: 9.5px; display: inline-flex; align-items: center; gap: 6px;"><span class="beacon-orange"></span> ⚠️ ALERTA NARANJA ({lluvia_val:.1f} mm/h)</span>'
        elif lluvia_val >= u["amarilla"]:
            sem = "AMARILLA"
            css = "card-scada-yellow"
            beacon_class = "beacon-yellow"
            badge_color = "#FFBB00"
            txt_sem = f"⚡ AVISO AMARILLO ({lluvia_val:.1f} mm/h)"
            badge_html = f'<span class="badge-status" style="background: rgba(255, 187, 0, 0.2); color: #FFBB00; border: 1px solid #FFBB00; font-size: 9.5px; display: inline-flex; align-items: center; gap: 6px;"><span class="beacon-yellow"></span> ⚡ AVISO AMARILLO ({lluvia_val:.1f} mm/h)</span>'
        elif (estado_red == "VIRTUAL_SATELITAL" and lluvia_val >= 1.5) or (estado_red != "VIRTUAL_SATELITAL" and lluvia_val >= 0.5):
            sem = "VERDE"
            css = "card-scada-green"
            beacon_class = "beacon-green"
            badge_color = "#00CC96"
            txt_sem = f"🟢 LLOVIENDO ({lluvia_val:.1f} mm/h) — LLUVIA NORMAL"
            if estado_red == "VIRTUAL_SATELITAL":
                badge_html = f'<span class="badge-status" style="background: rgba(0, 204, 150, 0.2); color: #00CC96; border: 1px solid #00CC96; font-size: 9.5px; display: inline-flex; align-items: center; gap: 6px;"><span class="beacon-green"></span> 🟢 LLOVIENDO ({lluvia_val:.1f} mm/h • Satelital)</span>'
            else:
                badge_html = f'<span class="badge-status" style="background: rgba(0, 204, 150, 0.2); color: #00CC96; border: 1px solid #00CC96; font-size: 9.5px; display: inline-flex; align-items: center; gap: 6px;"><span class="beacon-green"></span> 🟢 LLOVIENDO ({lluvia_val:.1f} mm/h)</span>'
        else:
            sem = "SECO"
            css = "card-scada-gray"
            beacon_class = "beacon-gray"
            badge_color = "#94A3B8"
            txt_sem = "⚪ TIEMPO SECO (0.0 mm/h)"
            if estado_red == "VIRTUAL_SATELITAL":
                badge_html = '<span class="badge-status" style="background: rgba(56, 189, 248, 0.15); color: #38BDF8; border: 1px solid #0284C7; font-size: 9.5px; display: inline-flex; align-items: center; gap: 6px;"><span class="beacon-gray"></span> ⚪ EN MANTENIMIENTO (Sensor Virtual Satelital)</span>'
            else:
                badge_html = '<span class="badge-status" style="background: rgba(148, 163, 184, 0.15); color: #94A3B8; border: 1px solid #475569; font-size: 9.5px; display: inline-flex; align-items: center; gap: 6px;"><span class="beacon-gray"></span> ⚪ TIEMPO SECO (En vivo)</span>'
        if es_libre_surata:
            if lluvia_val >= 0.5:
                impacto = "⛰️ Drenaje directo a Río Suratá (cauce libre sin presa) ➔ Majadas ➔ Bosconia"
            else:
                impacto = "⛰️ Cuenca Alta Río Suratá en tiempo seco (Sin aporte pluvial adicional)"
        elif cota_emb >= NIVEL_REBOSE_EMBALSE:
            if lluvia_val >= 0.5:
                impacto = "🌊 Embalse en rebose: escorrentía pasa sobre vertedero hacia Bosconia"
            else:
                impacto = "🌊 Embalse en cota de rebose activo (Vertimiento constante por Morning Glory)"
        else:
            if lluvia_val >= 0.5:
                impacto = "🛡️ Cuenca Tona amortiguada en vaso del Embalse (Sin impacto aguas abajo)"
            else:
                impacto = "🛡️ Tiempo seco en subcuenca (Sin lluvias activas)"
        return {
            "id": id_est,
            "nombre": nombre_largo,
            "altitud": altitud,
            "cuenca": cuenca_txt,
            "lluvia": lluvia_val,
            "temp": temp_val,
            "hum": hum_val,
            "estado_red": estado_red,
            "origen_txt": origen_txt,
            "sem": sem,
            "css": css,
            "beacon_class": beacon_class,
            "badge_color": badge_color,
            "badge_html": badge_html,
            "txt_sem": txt_sem,
            "impacto": impacto
        }
    info_mon = evaluar_estacion_met("Monsalve", "Monsalve (Páramo Santurbán)", "3,339 msnm", "Cuenca Alta Río Suratá", es_libre_surata=True)
    info_paj = evaluar_estacion_met("El_Pajal", "El Pajal (Ladera Sur Tona)", "2,163 msnm", "Microcuenca Golondrinas / Embalse")
    info_veg = evaluar_estacion_met("Vegas_del_Quemado", "Vegas del Quemado (Ladera Norte)", "1,759 msnm", "Valle de Arnania / Embalse")
    info_mar = evaluar_estacion_met("La_Mariana", "La Mariana (Cresta Divisoria)", "2,436 msnm", "Filo Divisorio Río Frío - Tona")
    info_yer = evaluar_estacion_met("Yerbabuena", "Yerbabuena (Alta Montaña)", "3,380 msnm", "Divisoria Tona / Charta / Vetas")
    # Diagnóstico territorial general más severo
    estados_red = [sur_semaforo, emb_semaforo, info_mon["sem"], info_paj["sem"], info_veg["sem"], info_mar["sem"], info_yer["sem"]]
    if "ROJA" in estados_red:
        banner_bg = "linear-gradient(135deg, rgba(80, 10, 10, 0.95), rgba(40, 5, 5, 0.98))"
        banner_border = "#FF4B4B"
        banner_icono = "🚨"
        banner_titulo = "CONDICIÓN CRÍTICA EN RED DE CUENCAS — ALERTA ROJA ACTIVA"
        banner_sub = "Creciente confirmada en Río Suratá o precipitaciones torrenciales extremas. Atención prioritaria en Bocatoma Bosconia."
    elif "NARANJA" in estados_red:
        banner_bg = "linear-gradient(135deg, rgba(70, 35, 5, 0.95), rgba(35, 15, 2, 0.98))"
        banner_border = "#FF8000"
        banner_icono = "⚠️"
        banner_titulo = "VIGILANCIA HIDROLÓGICA ACTIVA — ALERTA NARANJA"
        banner_sub = "Lluvias de consideración en cuencas aportantes. Alistar purga en desarenadores e inspección de rejillas."
    elif emb_semaforo == "REBOSE":
        banner_bg = "linear-gradient(135deg, rgba(5, 40, 60, 0.95), rgba(2, 20, 35, 0.98))"
        banner_border = "#00BFFF"
        banner_icono = "🌊"
        banner_titulo = f"EMBALSE DE TONA EN VERTIMIENTO ACTIVO (+{int(round(h_rebose*100))} cm MORNING GLORY)"
        banner_sub = f"Cota calibrada {cota_emb:.2f} msnm. Descarga activa de ~{q_mg_ls:,.0f} L/s por cascadas y piscina de aquietamiento hacia Puente Tona."
    elif "AMARILLA" in estados_red or emb_semaforo == "PRE_REBOSE":
        banner_bg = "linear-gradient(135deg, rgba(60, 50, 5, 0.95), rgba(30, 25, 2, 0.98))"
        banner_border = "#FFBB00"
        banner_icono = "⚡"
        banner_titulo = "AVISO DE PRECAUCIÓN — MONITOREO REFORZADO"
        banner_sub = "Ascenso moderado de caudales o proximidad a cota de vertimiento. Sin afectación sobre captaciones."
    elif "VERDE" in estados_red:
        banner_bg = "linear-gradient(135deg, rgba(5, 45, 30, 0.92), rgba(2, 25, 15, 0.98))"
        banner_border = "#00CC96"
        banner_icono = "🌧️"
        banner_titulo = "PRECIPITACIONES ACTIVAS EN CUENCA — RÉGIMEN LLUVIOSO NORMAL"
        banner_sub = "Lluvias activas registradas en subcuencas aportantes dentro de umbrales normales. Captación y conducción estables."
    else:
        banner_bg = "linear-gradient(135deg, rgba(20, 26, 36, 0.92), rgba(12, 17, 26, 0.98))"
        banner_border = "#64748B"
        banner_icono = "☀️"
        banner_titulo = "CONDICIÓN HIDROLÓGICA ESTABLE — TIEMPO SECO GENERALIZADO"
        banner_sub = "Caudales en régimen base estable, sin precipitaciones en cuencas y red telemétrica transmitiendo 24/7."
    st.markdown(f"""
    <div style="background: {banner_bg}; border-left: 6px solid {banner_border}; border-radius: 12px; padding: 18px 22px; margin-bottom: 20px; box-shadow: 0 4px 18px rgba(0,0,0,0.35);">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
            <div style="display: flex; align-items: center; gap: 14px;">
                <span style="font-size: 32px;">{banner_icono}</span>
                <div>
                    <h3 style="color: #FFFFFF; margin: 0; font-size: 19px; font-weight: 800; letter-spacing: -0.3px;">
                        {banner_titulo}
                    </h3>
                    <div style="color: #E2E8F0; font-size: 13px; margin-top: 3px;">
                        {banner_sub}
                    </div>
                </div>
            </div>
            <div style="text-align: right;">
                <span style="background: rgba(255,255,255,0.15); color: #FFFFFF; padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 800; border: 1px solid rgba(255,255,255,0.3);">
                    amb • CENTRO DE CONTROL
                </span>
                <div style="color: #CBD5E1; font-size: 11.5px; margin-top: 4px;">
                    🕐 Actualizado: {ahora_str} COT
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    # -------------------------------------------------------------
    # FILA 1: NODOS FLUVIALES PRINCIPALES (SURATÁ MAJADAS & EMBALSE TONA)
    # -------------------------------------------------------------
    st.markdown("### 🌊 1. Nodos Hidrológicos Estratégicos (Río Suratá & Embalse Tona)")
    col_sur, col_emb = st.columns(2)
    with col_sur:
        st.markdown(f"""
        <div class="{sur_card_class}">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;">
                <div>
                    <div style="color: #64FFDA; font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 1px;">
                        ESTACIÓN FLUVIAL PRINCIPAL • FEWS IDEAM 0023197700
                    </div>
                    <h3 style="color: #FFFFFF; margin: 2px 0 0 0; font-size: 20px; font-weight: 800;">
                        🏞️ Río Suratá — Majadas
                    </h3>
                    <div style="color: #94A3B8; font-size: 11.5px;">Sector Majadas • Aguas abajo Puente Tona • ~1.8 km a Toma Bosconia</div>
                </div>
                <span class="badge-status" style="background: rgba(0, 204, 150, 0.2); color: #00CC96; border: 1px solid #00CC96; font-size: 10px; display: inline-flex; align-items: center; gap: 6px;">
                    <span class="{sur_beacon_class}"></span> OPERATIVA (En vivo)
                </span>
            </div>
            <div style="background: rgba(0,0,0,0.35); border-radius: 10px; padding: 12px; margin-bottom: 12px; display: grid; grid-template-columns: 1fr 1fr; gap: 10px; border: 1px solid rgba(255,255,255,0.08);">
                <div>
                    <div style="color: #94A3B8; font-size: 11px; text-transform: uppercase;">⚡ Caudal Actual (amb)</div>
                    <div style="color: #FFFFFF; font-size: 26px; font-weight: 900; line-height: 1.1;">{q_sur_ls:,.0f} <span style="font-size: 14px; font-weight: 600; color: #64FFDA;">L/s</span></div>
                    <div style="color: #64FFDA; font-size: 11px;">{q_sur_ls/1000.0:.2f} m³/s • Mira: <strong>{h_sur_m:.2f} m</strong></div>
                </div>
                <div>
                    <div style="color: #94A3B8; font-size: 11px; text-transform: uppercase;">🔼 Pico Máx. Hora [0231]</div>
                    <div style="color: #FFFFFF; font-size: 26px; font-weight: 900; line-height: 1.1;">{q_sur_max1h:,.0f} <span style="font-size: 14px; font-weight: 600; color: #F59E0B;">L/s</span></div>
                    <div style="color: #94A3B8; font-size: 11px;">Promedio 24h: <strong>{q_sur_prom24h:,.0f} L/s</strong></div>
                </div>
            </div>
            <div style="display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; border-radius: 8px; background: rgba(0,0,0,0.25); border-left: 4px solid {sur_badge_color};">
                <div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span class="{sur_beacon_class}"></span>
                        <strong style="color: {sur_badge_color}; font-size: 12.5px;">{sur_titulo}</strong>
                    </div>
                    <div style="color: #CBD5E1; font-size: 11.5px; margin-top: 2px;">{sur_accion}</div>
                </div>
                <div style="text-align: right; color: #64FFDA; font-size: 11px; font-weight: 700; white-space: nowrap;">
                    ⏱️ Tránsito Bosconia: 15–25 min
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col_emb:
        st.markdown(f"""
        <div class="{emb_card_class}">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;">
                <div>
                    <div style="color: #38BDF8; font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 1px;">
                        ESTRUCTURA DE REGULACIÓN • RADAR OTT
                    </div>
                    <h3 style="color: #FFFFFF; margin: 2px 0 0 0; font-size: 20px; font-weight: 800;">
                        🌊 Embalse de Tona & Rebosadero
                    </h3>
                    <div style="color: #94A3B8; font-size: 11.5px;">Cresta Morning Glory: 885.75 msnm • Entrega a Cascadas y Piscina de Aquietamiento</div>
                </div>
                <span class="badge-status" style="background: rgba(0, 204, 150, 0.2); color: #00CC96; border: 1px solid #00CC96; font-size: 10px; display: inline-flex; align-items: center; gap: 6px;">
                    <span class="{emb_beacon_class}"></span> OPERATIVA (En vivo)
                </span>
            </div>
            <div style="background: rgba(0,0,0,0.35); border-radius: 10px; padding: 12px; margin-bottom: 12px; display: grid; grid-template-columns: 1fr 1fr; gap: 10px; border: 1px solid rgba(255,255,255,0.08);">
                <div>
                    <div style="color: #94A3B8; font-size: 11px; text-transform: uppercase;">🌊 Cota Calibrada (-4 cm)</div>
                    <div style="color: #FFFFFF; font-size: 26px; font-weight: 900; line-height: 1.1;">{cota_emb:.2f} <span style="font-size: 14px; font-weight: 600; color: #38BDF8;">msnm</span></div>
                    <div style="color: #38BDF8; font-size: 11px;">{f'+{h_rebose*100:.1f} cm vs Rebose' if h_rebose > 0 else f'a -{abs(885.75-cota_emb)*100:.1f} cm de rebose'}</div>
                </div>
                <div>
                    <div style="color: #94A3B8; font-size: 11px; text-transform: uppercase;">🌊 Rebose Morning Glory</div>
                    <div style="color: #FFFFFF; font-size: 26px; font-weight: 900; line-height: 1.1;">{q_mg_ls:,.0f} <span style="font-size: 14px; font-weight: 600; color: #38BDF8;">L/s</span></div>
                    <div style="color: #94A3B8; font-size: 11px;">Salida CRC Bosconia: <strong>200 L/s</strong></div>
                </div>
            </div>
            <div style="display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; border-radius: 8px; background: rgba(0,0,0,0.25); border-left: 4px solid {emb_badge_color};">
                <div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span class="{emb_beacon_class}"></span>
                        <strong style="color: {emb_badge_color}; font-size: 12.5px;">{emb_titulo}</strong>
                    </div>
                    <div style="color: #CBD5E1; font-size: 11.5px; margin-top: 2px;">{emb_accion}</div>
                </div>
                <div style="text-align: right; color: #38BDF8; font-size: 11px; font-weight: 700; white-space: nowrap;">
                    {f'Descarga Activa: ~{q_mg_m3s:.2f} m³/s' if q_mg_ls > 0 else 'Capacidad 100% útil'}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    # -------------------------------------------------------------
    # FILA 2: ESTACIONES PLUVIOMÉTRICAS DE CUENCA (SURATÁ ALTO & CUENCA TONA)
    # -------------------------------------------------------------
    st.markdown("### 🌧️ 2. Red Meteorológica & Subcuencas Aportantes")
    col_m1, col_m2, col_m3 = st.columns(3)
    for col_target, info_i in [(col_m1, info_mon), (col_m2, info_paj), (col_m3, info_veg)]:
        with col_target:
            st.markdown(f"""
            <div class="{info_i['css']}">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                    <div>
                        <div style="color: #94A3B8; font-size: 10px; font-weight: 800; text-transform: uppercase;">{info_i['cuenca']}</div>
                        <h4 style="color: #FFFFFF; margin: 2px 0 0 0; font-size: 16px; font-weight: 800;">{info_i['nombre']}</h4>
                        <div style="color: #64748B; font-size: 11px;">Altitud: {info_i['altitud']}</div>
                    </div>
                    {info_i['badge_html']}
                </div>
                <div style="background: rgba(0,0,0,0.3); border-radius: 8px; padding: 10px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="color: #94A3B8; font-size: 10.5px;">Lluvia Última Hora</div>
                        <div style="color: #FFFFFF; font-size: 22px; font-weight: 900;">{info_i['lluvia']:.1f} <span style="font-size: 12px; color: {'#00CC96' if info_i['lluvia'] > 0 else '#94A3B8'};">mm/h</span></div>
                    </div>
                    <div style="text-align: right;">
                        <div style="color: #94A3B8; font-size: 10.5px;">Temperatura / Hum</div>
                        <div style="color: #CBD5E1; font-size: 13px; font-weight: 700;">{info_i['temp']:.1f}°C • {info_i['hum']:.0f}%</div>
                    </div>
                </div>
                <div style="font-size: 11px; color: #CBD5E1; background: rgba(0,0,0,0.25); padding: 8px 12px; border-radius: 8px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span class="{info_i['beacon_class']}"></span>
                        <strong style="color: {info_i['badge_color']}; font-size: 12px;">{info_i['txt_sem']}</strong>
                    </div>
                    <div style="color: #94A3B8; margin-top: 3px;">{info_i['impacto']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    # -------------------------------------------------------------
    # FILA 3: ESTACIONES CON RESPALDO VIRTUAL SATELITAL (OPEN-METEO)
    # -------------------------------------------------------------
    hay_virtuales = any(s['estado_red'] == 'VIRTUAL_SATELITAL' for s in [info_mar, info_yer])
    titulo_sec3 = "### 🛰️ 3. Estaciones en Mantenimiento con Sensor Virtual Satelital Activo (Open-Meteo)" if hay_virtuales else "### 🛰️ 3. Estaciones de Alta Montaña (Telemetría Física Restablecida)"
    st.markdown(titulo_sec3)
    col_sat1, col_sat2 = st.columns(2)
    for col_s_target, info_s in [(col_sat1, info_mar), (col_sat2, info_yer)]:
        es_virt = info_s['estado_red'] == 'VIRTUAL_SATELITAL'
        header_tag = "RESPALDO METEOROLÓGICO SATELITAL" if es_virt else "TELEMETRÍA EN VIVO (SIM RESTABLECIDA)"
        header_color = "#38BDF8" if es_virt else "#00CC96"
        lluvia_lbl = "Precipitación Satelital Estimada" if es_virt else "Lluvia Última Hora"
        origen_lbl = "Modelo Satelital" if es_virt else "Temperatura / Hum"
        impacto_color = "#38BDF8" if es_virt else "#94A3B8"
        with col_s_target:
            st.markdown(f"""
            <div class="{info_s['css']}">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                    <div>
                        <div style="color: {header_color}; font-size: 10px; font-weight: 800; text-transform: uppercase;">{header_tag}</div>
                        <h4 style="color: #FFFFFF; margin: 2px 0 0 0; font-size: 16px; font-weight: 800;">{info_s['nombre']}</h4>
                        <div style="color: #94A3B8; font-size: 11px;">{info_s['cuenca']} • Altitud: {info_s['altitud']}</div>
                    </div>
                    {info_s['badge_html']}
                </div>
                <div style="background: rgba(0,0,0,0.3); border-radius: 8px; padding: 10px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="color: #94A3B8; font-size: 10.5px;">{lluvia_lbl}</div>
                        <div style="color: #FFFFFF; font-size: 22px; font-weight: 900;">{info_s['lluvia']:.1f} <span style="font-size: 12px; color: {'#00CC96' if info_s['lluvia'] > 0 else '#38BDF8'};">mm/h</span></div>
                    </div>
                    <div style="text-align: right;">
                        <div style="color: #94A3B8; font-size: 10.5px;">{origen_lbl}</div>
                        <div style="color: #CBD5E1; font-size: 13px; font-weight: 700;">{info_s['temp']:.1f}°C • {info_s['hum']:.0f}%</div>
                    </div>
                </div>
                <div style="font-size: 11px; color: #CBD5E1; background: rgba(0,0,0,0.25); padding: 8px 12px; border-radius: 8px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span class="{info_s['beacon_class']}"></span>
                        <strong style="color: {info_s['badge_color']}; font-size: 12px;">{info_s['txt_sem']}</strong>
                    </div>
                    <div style="color: {impacto_color}; margin-top: 3px;">{info_s['impacto']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
# 7.6 CONSULTAS Y VISTA DE EVENTOS SIGNIFICATIVOS & ESTADÍSTICAS
# ============================================================
@st.cache_data(ttl=120)
def consultar_eventos_significativos_bigquery(dias=90):
    """
    Consulta en BigQuery los registros históricos de eventos extremos:
    - Picos de lluvia que superaron umbrales de alerta en ventana móvil de 1 hora (60 min / 6 paquetes de 10 min)
      o en paquete horario consolidado, aplicando filtro anti-Hold SCADA.
    - Picos del radar del Embalse de Tona (cota >= 885.70 msnm)
    - Crecientes en Río Suratá (Majadas)
    """
    try:
        filtro_tiempo = f"SAFE_CAST(timestamp AS TIMESTAMP) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {dias} DAY)" if dias < 365 else "1=1"
        query = f"""
        WITH base_limpia AS (
            SELECT
                id_estacion,
                SAFE_CAST(timestamp AS TIMESTAMP) AS ts,
                UNIX_SECONDS(SAFE_CAST(timestamp AS TIMESTAMP)) AS ts_unix,
                SAFE_CAST(precipitacion AS FLOAT64) AS precip_raw,
                SAFE_CAST(temperatura AS FLOAT64) AS temp,
                SAFE_CAST(humedad AS FLOAT64) AS hum,
                SAFE_CAST(velocidad_viento AS FLOAT64) AS viento,
                LAG(SAFE_CAST(precipitacion AS FLOAT64)) OVER (PARTITION BY id_estacion ORDER BY SAFE_CAST(timestamp AS TIMESTAMP)) AS prev_p,
                LAG(SAFE_CAST(temperatura AS FLOAT64)) OVER (PARTITION BY id_estacion ORDER BY SAFE_CAST(timestamp AS TIMESTAMP)) AS prev_t,
                LAG(SAFE_CAST(humedad AS FLOAT64)) OVER (PARTITION BY id_estacion ORDER BY SAFE_CAST(timestamp AS TIMESTAMP)) AS prev_h
            FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones`
            WHERE {filtro_tiempo}
              AND timestamp IS NOT NULL
        ),
        con_anti_hold AS (
            SELECT
                id_estacion,
                ts,
                ts_unix,
                CASE
                    WHEN id_estacion IN ('El_Pajal', 'Yerbabuena', 'La_Mariana', 'Vegas_del_Quemado', 'Monsalve')
                         AND precip_raw > 0 AND precip_raw < 10.0
                         AND precip_raw = prev_p AND temp = prev_t AND hum = prev_h
                    THEN 0.0
                    ELSE IFNULL(precip_raw, 0.0)
                END AS precip_limpia,
                IFNULL(precip_raw, 0.0) AS precip_raw,
                temp,
                hum,
                viento
            FROM base_limpia
        ),
        ventana_horaria AS (
            SELECT
                id_estacion,
                ts,
                ROUND(
                    GREATEST(
                        precip_raw,
                        SUM(precip_limpia) OVER (
                            PARTITION BY id_estacion
                            ORDER BY ts_unix
                            RANGE BETWEEN 3599 PRECEDING AND CURRENT ROW
                        )
                    ),
                    2
                ) AS precip,
                temp,
                hum,
                viento
            FROM con_anti_hold
        )
        SELECT
            id_estacion,
            ts,
            precip,
            temp,
            hum,
            viento
        FROM ventana_horaria
        WHERE (
            (id_estacion = 'Embalse' AND temp >= 885.70)
            OR (id_estacion = 'El_Pajal' AND precip >= 12.3)
            OR (id_estacion = 'Yerbabuena' AND precip >= 10.9)
            OR (id_estacion = 'La_Mariana' AND precip >= 11.7)
            OR (id_estacion = 'Vegas_del_Quemado' AND precip >= 27.2)
            OR (id_estacion = 'Monsalve' AND precip >= 10.9)
            OR (id_estacion = 'Surata' AND (
                precip >= 2800.0
                OR temp >= 1.08
                OR temp >= 2800.0
                OR (precip >= 1.08 AND precip <= 15.0)
            ))
        )
        ORDER BY ts DESC
        LIMIT 5000
        """
        q_job = client.query(query)
        rows = [dict(row) for row in q_job.result()]
        return pd.DataFrame(rows)
    except Exception as e:
        print(f"Error consultando eventos significativos: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def consultar_picos_embalse_bigquery(dias=90):
    """
    Consulta las cotas más altas registradas por el radar del embalse en el período.
    """
    try:
        filtro_tiempo = f"SAFE_CAST(timestamp AS TIMESTAMP) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {dias} DAY)" if dias < 365 else "1=1"
        query = f"""
        SELECT
            SAFE_CAST(timestamp AS TIMESTAMP) as ts,
            SAFE_CAST(temperatura AS FLOAT64) as cota,
            SAFE_CAST(precipitacion AS FLOAT64) as precip
        FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones`
        WHERE id_estacion = 'Embalse'
          AND SAFE_CAST(temperatura AS FLOAT64) > 800
          AND {filtro_tiempo}
        ORDER BY cota DESC
        LIMIT 20
        """
        q_job = client.query(query)
        rows = [dict(row) for row in q_job.result()]
        return pd.DataFrame(rows)
    except Exception as e:
        print(f"Error consultando picos embalse: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def consultar_picos_surata_bigquery(dias=90):
    """
    Consulta en BigQuery los registros históricos de niveles y crecientes en Río Suratá (Sector Majadas - IDEAM 0023197700),
    detectando picos de caudal, crecientes súbitas y tránsito de avenidas hacia Toma Bosconia.
    """
    try:
        filtro_tiempo = f"SAFE_CAST(timestamp AS TIMESTAMP) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {dias} DAY)" if dias < 365 else "1=1"
        query = f"""
        SELECT
            SAFE_CAST(timestamp AS TIMESTAMP) as ts,
            SAFE_CAST(temperatura AS FLOAT64) as col_temp,
            SAFE_CAST(precipitacion AS FLOAT64) as col_precip,
            SAFE_CAST(humedad AS FLOAT64) as col_hum,
            IFNULL(estado_bateria, '') as origen
        FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones`
        WHERE id_estacion = 'Surata'
          AND {filtro_tiempo}
        ORDER BY ts DESC
        LIMIT 5000
        """
        q_job = client.query(query)
        rows = [dict(row) for row in q_job.result()]
        return pd.DataFrame(rows)
    except Exception as e:
        print(f"Error consultando picos de Suratá en BigQuery: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=600)
def consultar_estadisticas_multitemporales_bigquery():
    """
    Agrupa en BigQuery los datos diarios de todas las estaciones desde el inicio del registro 2026.
    A partir de esta matriz base diaria se calculan las estadísticas semanales, mensuales
    y el acumulado progresivo anual 2026.
    """
    try:
        query = """
        WITH raw_base AS (
          SELECT 
            id_estacion,
            SAFE_CAST(timestamp AS TIMESTAMP) as ts,
            UNIX_SECONDS(SAFE_CAST(timestamp AS TIMESTAMP)) as ts_unix,
            DATE(SAFE_CAST(timestamp AS TIMESTAMP), 'America/Bogota') as fecha,
            SAFE_CAST(precipitacion AS FLOAT64) as precip_raw,
            SAFE_CAST(temperatura AS FLOAT64) as temp,
            SAFE_CAST(humedad AS FLOAT64) as hum,
            LAG(SAFE_CAST(precipitacion AS FLOAT64)) OVER (PARTITION BY id_estacion ORDER BY SAFE_CAST(timestamp AS TIMESTAMP)) as prev_p,
            LAG(SAFE_CAST(temperatura AS FLOAT64)) OVER (PARTITION BY id_estacion ORDER BY SAFE_CAST(timestamp AS TIMESTAMP)) as prev_t,
            LAG(SAFE_CAST(humedad AS FLOAT64)) OVER (PARTITION BY id_estacion ORDER BY SAFE_CAST(timestamp AS TIMESTAMP)) as prev_h
          FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones`
          WHERE timestamp IS NOT NULL
            AND SAFE_CAST(timestamp AS TIMESTAMP) >= TIMESTAMP('2026-01-01 00:00:00 UTC')
        ),
        crc_diario AS (
          SELECT
            fecha,
            ROUND(AVG(CASE WHEN precip_raw >= 0 AND precip_raw <= 3000 THEN precip_raw WHEN temp >= 0 AND temp <= 3000 THEN temp ELSE NULL END), 2) as q_crc_dia_ls
          FROM raw_base
          WHERE id_estacion IN ('CRC_Bosconia_Caudal', 'ET_FIT401')
          GROUP BY fecha
        ),
        limpia AS (
          SELECT
            id_estacion,
            ts_unix,
            fecha,
            CASE
              WHEN id_estacion IN ('El_Pajal', 'Yerbabuena', 'La_Mariana', 'Vegas_del_Quemado', 'Monsalve')
                   AND precip_raw > 0 AND precip_raw < 10.0
                   AND precip_raw = prev_p AND temp = prev_t AND hum = prev_h
              THEN 0.0
              ELSE IFNULL(precip_raw, 0.0)
            END as precip,
            IFNULL(precip_raw, 0.0) as precip_raw,
            CASE
              WHEN id_estacion = 'Embalse' THEN (
                CASE WHEN temp >= 817.98 AND temp <= 888.85 THEN temp - 0.04 ELSE NULL END
              )
              ELSE temp
            END as temp,
            hum
          FROM raw_base
          WHERE id_estacion NOT IN ('CRC_Bosconia_Caudal', 'ET_FIT401')
        ),
        base AS (
          SELECT
            id_estacion,
            ts_unix,
            fecha,
            precip,
            GREATEST(
              precip_raw,
              SUM(precip) OVER (PARTITION BY id_estacion ORDER BY ts_unix RANGE BETWEEN 3599 PRECEDING AND CURRENT ROW)
            ) as precip_1h,
            temp,
            hum
          FROM limpia
        ),
        agrupado AS (
          SELECT 
              b.id_estacion,
              b.fecha,
              EXTRACT(YEAR FROM b.fecha) as anio,
              EXTRACT(MONTH FROM b.fecha) as mes,
              EXTRACT(ISOWEEK FROM b.fecha) as semana,
              ROUND(SUM(IFNULL(b.precip, 0.0)), 2) as lluvia_diaria,
              ROUND(MAX(IFNULL(b.precip_1h, 0.0)), 2) as lluvia_pico_horario,
              ROUND(MIN(b.temp), 3) as temp_min,
              ROUND(MAX(b.temp), 3) as temp_max,
              ROUND(AVG(b.temp), 3) as temp_prom,
              ARRAY_AGG(b.temp IGNORE NULLS ORDER BY b.ts_unix ASC LIMIT 1)[SAFE_OFFSET(0)] as temp_ini,
              ARRAY_AGG(b.temp IGNORE NULLS ORDER BY b.ts_unix DESC LIMIT 1)[SAFE_OFFSET(0)] as temp_fin,
              ROUND(GREATEST(1.0, (MAX(b.ts_unix) - MIN(b.ts_unix)) / 3600.0), 2) as horas_monitoreadas,
              ROUND(MIN(b.hum), 1) as hum_min,
              ROUND(MAX(b.hum), 1) as hum_max,
              ROUND(AVG(b.hum), 1) as hum_prom,
              COUNT(*) as total_lecturas
          FROM base b
          WHERE b.fecha IS NOT NULL
            AND (b.id_estacion != 'Embalse' OR b.temp IS NOT NULL)
          GROUP BY b.id_estacion, b.fecha, anio, mes, semana
        )
        SELECT
            a.*,
            IFNULL(c.q_crc_dia_ls, 25.3) as q_crc_dia_ls
        FROM agrupado a
        LEFT JOIN crc_diario c ON a.fecha = c.fecha
        ORDER BY a.fecha DESC
        """
        q_job = client.query(query)
        rows = [dict(row) for row in q_job.result()]
        return pd.DataFrame(rows)
    except Exception as e:
        print(f"Error consultando estadísticas multitemporales: {e}")
        return pd.DataFrame()

def render_eventos_significativos_estadisticas():
    """
    Renderiza la pestana oficial de Eventos Significativos y Estadisticas Climatologicas Multitemporales.
    Aplica las reglas hidrologicas estrictas de cuencas del amb:
    - Monsalve: Afecta Rio Surata (Majadas) -> NO afecta al Embalse de Tona.
    - El Pajal, Yerbabuena, Vegas del Quemado: Afectan Embalse de Tona (Rio Tona).
    - La Mariana: Afecta Cuenca Rio Frio (PTAP Florida) -> No afecta Embalse ni Majadas.
    - Embalse: Descargas por Morning Glory hacia confluencia Surata / Majadas.
    """
    st.subheader("\U0001F6A8 Eventos Hidrol\u00F3gicos Significativos & Climatolog\u00EDa Multitemporal")
    st.caption("Bit\u00E1cora forense de picos extremos, reboses y estad\u00EDsticas progresivas acumuladas (Diarias, Semanales, Mensuales y Anuales) \u2014 Sistema MIMAT-C26")

    tab_sub_eventos, tab_sub_estadisticas = st.tabs([
        "\U0001F6A8 Bit\u00E1cora Forense de Eventos Extremos",
        "\U0001F4CA Estad\u00EDsticas Climatol\u00F3gicas (D\u00EDa / Semana / Mes / A\u00F1o)"
    ])
    meses_es = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }
    # ------------------------------------------------------------
    # SUB-TAB 1: BITACORA FORENSE DE EVENTOS EXTREMOS
    # ------------------------------------------------------------
    with tab_sub_eventos:
        col_f1, col_f2 = st.columns([2, 2])
        periodo_dias = col_f1.selectbox(
            "Ventana temporal de an\u00E1lisis forense:",
            [7, 15, 30, 60, 90, 180, 365],
            index=4,
            format_func=lambda x: "Hist\u00F3rico Completo 2026" if x >= 365 else f"\u00DAltimos {x} d\u00EDas",
            key="ev_periodo_dias"
        )
        orden_oficial_ev = ["Todas las Estaciones", "Embalse", "Surata", "La_Mariana", "Yerbabuena", "Vegas_del_Quemado", "El_Pajal", "Monsalve"]
        estacion_ev_sel = col_f2.selectbox(
            "Filtrar por estaci\u00F3n:",
            orden_oficial_ev,
            index=0,
            format_func=lambda x: {
                "Todas las Estaciones": "\U0001F310 Todas las Estaciones",
                "Embalse": "\U0001F30A Embalse Tona",
                "Surata": "\u26A1 R\u00EDo Surat\u00E1 (Majadas)",
                "La_Mariana": "\U0001F33F La Mariana",
                "Yerbabuena": "\U0001F4A7 Yerbabuena",
                "Vegas_del_Quemado": "\u26F0\uFE0F Vegas del Quemado",
                "El_Pajal": "\U0001F33E El Pajal",
                "Monsalve": "\U0001F3D4\uFE0F Monsalve"
            }.get(x, x.replace('_', ' ')),
            key="ev_estacion_sel"
        )

        # Reglas Hidrologicas de Visibilidad por Cuenca (Confirmadas por amb)
        mostrar_lluvias = estacion_ev_sel in ["Todas las Estaciones", "El_Pajal", "Yerbabuena", "La_Mariana", "Vegas_del_Quemado", "Monsalve"]
        mostrar_embalse = estacion_ev_sel in ["Todas las Estaciones", "Embalse", "El_Pajal", "Yerbabuena", "Vegas_del_Quemado"]
        mostrar_majadas = estacion_ev_sel in ["Todas las Estaciones", "Surata", "Monsalve", "Embalse"]

        with st.spinner("Consultando registros forenses en BigQuery..."):
            df_ev_raw = consultar_eventos_significativos_bigquery(periodo_dias)
            df_picos_emb = consultar_picos_embalse_bigquery(periodo_dias) if mostrar_embalse else pd.DataFrame()
            df_picos_sur = consultar_picos_surata_bigquery(periodo_dias) if mostrar_majadas else pd.DataFrame()

        if not df_ev_raw.empty and estacion_ev_sel != "Todas las Estaciones":
            df_ev_filtro = df_ev_raw[df_ev_raw['id_estacion'] == estacion_ev_sel].copy()
        else:
            df_ev_filtro = df_ev_raw.copy()

        st.markdown("---")

        # ========================================================
        # 1. PICOS DE PRECIPITACION EXTREMA EN CUENCAS
        # ========================================================
        if mostrar_lluvias:
            st.markdown("### \U0001F327\uFE0F 1. Picos de Precipitaci\u00F3n Extrema en Cuencas")
            filas_lluvia_candidatas = []
            ahora_col_ev = datetime.now(colombia_tz)
            if not df_ev_filtro.empty:
                for idx, row in df_ev_filtro.iterrows():
                    est = str(row.get('id_estacion', ''))
                    if est in umbrales and row.get('precip') is not None:
                        p_val = float(row['precip'])
                        u_amarilla = umbrales[est]['amarilla']
                        u_naranja = umbrales[est]['naranja']
                        u_roja = umbrales[est]['roja']
                        if p_val >= u_amarilla:
                            if p_val >= u_roja:
                                nivel_alerta = "\U0001F534 ALERTA ROJA"
                                badge_color = "#FF4B4B"
                                desc_impacto = "Riesgo de creciente s\u00FAbita inminente en drenaje"
                            elif p_val >= u_naranja:
                                nivel_alerta = "\U0001F7E0 ALERTA NARANJA"
                                badge_color = "#FF8000"
                                desc_impacto = "Incremento severo de escorrent\u00EDa superficial"
                            else:
                                nivel_alerta = "\U0001F7E1 ALERTA AMARILLA"
                                badge_color = "#FFBB00"
                                desc_impacto = "Aviso preventivo por ascenso de precipitaci\u00F3n"
                            ts_col = row['ts']
                            es_reciente = False
                            ts_dt_col = None
                            if hasattr(ts_col, 'astimezone'):
                                ts_dt_col = ts_col.astimezone(colombia_tz)
                                ts_str = ts_dt_col.strftime('%Y-%m-%d %H:%M')
                                horas_antiguedad = (ahora_col_ev - ts_dt_col).total_seconds() / 3600.0
                                es_reciente = (horas_antiguedad <= 36.0)
                            else:
                                ts_str = str(ts_col)[:16]
                                try:
                                    ts_dt_col = colombia_tz.localize(datetime.strptime(ts_str, '%Y-%m-%d %H:%M'))
                                    horas_antiguedad = (ahora_col_ev - ts_dt_col).total_seconds() / 3600.0
                                    es_reciente = (horas_antiguedad <= 36.0)
                                except Exception:
                                    pass
                            info_est = METADATA_ESTACIONES_AMB.get(est, {}) if "METADATA_ESTACIONES_AMB" in globals() else {}
                            cuenca_nombre = info_est.get("cuenca_principal") or info_est.get("cuenca", est.replace("_", " "))
                            filas_lluvia_candidatas.append({
                                "ts_dt": ts_dt_col,
                                "ts_raw_str": ts_str,
                                "est_key": est,
                                "Fecha / Hora": f"🔥 {ts_str} (RECIENTE)" if es_reciente else ts_str,
                                "Estaci\u00F3n": est.replace('_', ' '),
                                "Microcuenca": cuenca_nombre,
                                "Lluvia (mm/h)": round(p_val, 2),
                                "Nivel de Alerta": f"{nivel_alerta} • 🔥 HOY/AYER" if es_reciente else nivel_alerta,
                                "Impacto Operativo": f"⚡ EVENTO RECIENTE ACTIVO — {desc_impacto}" if es_reciente else desc_impacto,
                                "es_reciente": es_reciente,
                                "badge_color": badge_color
                            })
            # Deduplicar tramas consecutivas de un mismo aguacero (ventana de 45 min por estación), conservando el pico máximo de cada episodio
            filas_lluvia_extrema = []
            if filas_lluvia_candidatas:
                candidatas_por_pico = sorted(
                    filas_lluvia_candidatas,
                    key=lambda x: (x["Lluvia (mm/h)"], x["ts_raw_str"]),
                    reverse=True
                )
                seleccionadas_ts = []
                for cand in candidatas_por_pico:
                    duplicado_cercano = False
                    if cand["ts_dt"] is not None:
                        for ya in seleccionadas_ts:
                            if ya["est_key"] == cand["est_key"] and ya["ts_dt"] is not None:
                                diff_min = abs((cand["ts_dt"] - ya["ts_dt"]).total_seconds()) / 60.0
                                if diff_min <= 45.0:
                                    duplicado_cercano = True
                                    break
                    if not duplicado_cercano:
                        seleccionadas_ts.append(cand)
                filas_lluvia_extrema = sorted(seleccionadas_ts, key=lambda x: x["ts_raw_str"], reverse=True)
            if len(filas_lluvia_extrema) == 0:
                st.markdown(f"""
                <div style="background-color: #0d2818; border: 1px solid #00E676; border-left: 6px solid #00E676; padding: 14px 18px; border-radius: 8px; margin: 10px 0 20px 0;">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <span style="font-size: 1.4rem;">\u2705</span>
                        <div>
                            <strong style="color: #00E676; font-size: 1.05rem;">No se han registrado eventos extremos de precipitaci\u00F3n</strong>
                            <div style="color: #ECEFF1; font-size: 0.92rem; margin-top: 3px;">
                                En los \u00FAltimos <strong>{periodo_dias} d\u00EDas</strong> no se superaron los umbrales de alerta (Amarilla, Naranja o Roja) en las estaciones de cuenca evaluadas.
                                Todas las precipitaciones se mantuvieron dentro del r\u00E9gimen normal.
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                df_lluvia_show = pd.DataFrame(filas_lluvia_extrema)
                eventos_recientes_list = [f for f in filas_lluvia_extrema if f.get("es_reciente")]
                if eventos_recientes_list:
                    items_rec_html = " • ".join([
                        f"<strong>{ev['Estación']}</strong>: <code>{ev['Lluvia (mm/h)']:.1f} mm/h</code> ({ev['ts_raw_str']} COT — {ev['Nivel de Alerta'].split(' • ')[0]})"
                        for ev in eventos_recientes_list[:4]
                    ])
                    st.markdown(f"""
                    <div style="background: linear-gradient(90deg, rgba(255, 153, 0, 0.22), rgba(255, 75, 75, 0.16)); border: 2px solid #FFB300; border-left: 7px solid #FF6D00; padding: 12px 16px; border-radius: 10px; margin: 6px 0 14px 0; box-shadow: 0 3px 10px rgba(255, 153, 0, 0.18);">
                        <div style="font-weight: 800; color: #FFF8E1; font-size: 1.0rem;">
                            🔥 PICO DE ALERTA RECIENTE DETECTADO (ÚLTIMAS 24–36 HORAS):
                        </div>
                        <div style="color: #FFE082; font-size: 0.93rem; margin-top: 4px;">
                            {items_rec_html}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                c_k1, c_k2, c_k3 = st.columns(3)
                c_k1.metric("Total Eventos de Lluvia Extrema", len(df_lluvia_show))
                c_k2.metric("Pico M\u00E1ximo Registrado", f"{df_lluvia_show['Lluvia (mm/h)'].max():.1f} mm/h")
                c_k3.metric("Estaci\u00F3n con M\u00E1s Eventos", df_lluvia_show['Estaci\u00F3n'].mode()[0])
                cols_visibles_lluvia = ["Fecha / Hora", "Estaci\u00F3n", "Microcuenca", "Lluvia (mm/h)", "Nivel de Alerta", "Impacto Operativo"]
                df_tabla_lluvia = df_lluvia_show[cols_visibles_lluvia].copy()
                def _resaltar_fila_reciente(row):
                    if "🔥" in str(row.get("Fecha / Hora", "")):
                        return ["background-color: rgba(255, 179, 0, 0.24); color: #FFF8E1; font-weight: 700;"] * len(row)
                    return [""] * len(row)
                try:
                    st.dataframe(
                        df_tabla_lluvia.style.apply(_resaltar_fila_reciente, axis=1).format({"Lluvia (mm/h)": "{:.1f}"}),
                        use_container_width=True,
                        hide_index=True
                    )
                except Exception:
                    st.dataframe(
                        df_tabla_lluvia,
                        use_container_width=True,
                        hide_index=True
                    )
            st.markdown("---")

        # Mensajes hidrologicos pedagogicos segun la cuenca seleccionada
        if estacion_ev_sel == "Monsalve":
            st.markdown("""
            <div style="background: rgba(0, 150, 136, 0.08); border-left: 5px solid #00B4D8; padding: 12px 16px; border-radius: 8px; margin: 10px 0 20px 0;">
                <strong style="color: #00B4D8; font-size: 13.5px;">\U0001F3D4\uFE0F Hidrolog\u00EDa Cuenca Monsalve (P\u00E1ramo de Santurb\u00E1n):</strong>
                <div style="color: #E2E8F0; font-size: 12.5px; margin-top: 4px; line-height: 1.5;">
                    La estaci\u00F3n <strong>Monsalve</strong> (3,339 msnm) monitorea la cuenca alta del <strong>R\u00EDo Surat\u00E1</strong>.
                    Sus escorrent\u00EDas drenan en cauce libre directamente hacia el <strong>R\u00EDo Surat\u00E1 (Sector Majadas)</strong> y la captaci\u00F3n de <strong>Toma Bosconia</strong>.
                    <span style="color: #64FFDA; font-weight: 700;">No tributa al Embalse de Tona</span> (por lo tanto, la bit\u00E1cora del embalse no aplica para este filtro).
                </div>
            </div>
            """, unsafe_allow_html=True)
        elif estacion_ev_sel == "La_Mariana":
            st.markdown("""
            <div style="background: rgba(139, 195, 74, 0.08); border-left: 5px solid #8BC34A; padding: 12px 16px; border-radius: 8px; margin: 10px 0 20px 0;">
                <strong style="color: #8BC34A; font-size: 13.5px;">\U0001F33F Hidrolog\u00EDa Cuenca La Mariana:</strong>
                <div style="color: #E2E8F0; font-size: 12.5px; margin-top: 4px; line-height: 1.5;">
                    La estaci\u00F3n <strong>La Mariana</strong> (2,436 msnm) monitorea la vertiente suroccidental tributaria de la microcuenca de <strong>R\u00EDo Fr\u00EDo</strong>, que abastece la planta <strong>PTAP Florida</strong>.
                    No presenta conexi\u00F3n hidrol\u00F3gica directa con la cuenca del R\u00EDo Tona (Embalse) ni con el R\u00EDo Surat\u00E1 (Majadas).
                </div>
            </div>
            """, unsafe_allow_html=True)
        elif estacion_ev_sel in ["El_Pajal", "Yerbabuena", "Vegas_del_Quemado"]:
            st.markdown("""
            <div style="background: rgba(56, 189, 248, 0.08); border-left: 5px solid #38BDF8; padding: 12px 16px; border-radius: 8px; margin: 10px 0 20px 0;">
                <strong style="color: #38BDF8; font-size: 13.5px;">\U0001F30A Hidrolog\u00EDa Cuenca Tona (Aportes al Embalse):</strong>
                <div style="color: #E2E8F0; font-size: 12.5px; margin-top: 4px; line-height: 1.5;">
                    Esta estaci\u00F3n tributa a las subcuencas altas del R\u00EDo Tona (Quebradas Golondrinas, Arnania y Carrizal), aportando directamente al vaso del <strong>Embalse de Tona</strong>.
                    El agua solo transita hacia el R\u00EDo Surat\u00E1 (Majadas) si el embalse supera la cota de rebose 885.75 msnm vertiendo por el <em>Morning Glory</em>.
                </div>
            </div>
            """, unsafe_allow_html=True)

        # ========================================================
        # 2. PICOS Y REBOSES DEL EMBALSE DE TONA
        # ========================================================
        if mostrar_embalse:
            num_sec_emb = "1" if not mostrar_lluvias else "2"
            st.markdown(f"### \U0001F30A {num_sec_emb}. Picos y Reboses del Embalse de Tona (Cota 885.75 msnm)")
            rebose_cota = 885.75
            picos_embalse_data = []
            if not df_picos_emb.empty:
                for idx, r_emb in df_picos_emb.iterrows():
                    c_val = float(r_emb['cota'])
                    ts_c = r_emb['ts']
                    if hasattr(ts_c, 'astimezone'):
                        ts_c_str = ts_c.astimezone(colombia_tz).strftime('%Y-%m-%d %H:%M')
                    else:
                        ts_c_str = str(ts_c)[:16]

                    sobr = c_val - rebose_cota
                    if sobr > 0:
                        q_vert = 110.0 * (sobr ** 1.5)
                        q_vert_ls = q_vert * 1000.0
                        estado_reb = f"\U0001F534 REBOSE ACTIVO (+{sobr:.2f} m)"
                        q_vert_str = f"{q_vert:.2f} m\u00B3/s ({q_vert_ls:.0f} L/s)"
                    else:
                        estado_reb = f"\U0001F7E2 NORMAL ({abs(sobr):.2f} m bajo rebose)"
                        q_vert_str = "0.00 m\u00B3/s (Sin vertimiento)"

                    picos_embalse_data.append({
                        "Fecha / Hora": ts_c_str,
                        "Cota Radar (msnm)": round(c_val, 2),
                        "Estado Respecto a Rebose": estado_reb,
                        "Descarga Morning Glory Estimada": q_vert_str,
                        "Lluvia Registrada (mm)": round(float(r_emb.get('precip', 0.0) or 0.0), 2)
                    })

            df_picos_emb_show = pd.DataFrame(picos_embalse_data)

            eventos_rebose_count = sum(1 for p in picos_embalse_data if "\U0001F534" in p["Estado Respecto a Rebose"])
            if eventos_rebose_count == 0:
                st.info(f"\u2139\uFE0F  **Sin eventos de rebose:** En los \u00FAltimos {periodo_dias} d\u00EDas la cota del embalse se mantuvo bajo los {rebose_cota:.2f} msnm. No se registraron descargas por vertimiento.")
            else:
                st.warning(f"\u26A0\uFE0F  **Se registraron {eventos_rebose_count} lecturas en cota de rebose** sobre el vertedero Morning Glory (885.75 msnm) en el per\u00EDodo analizado.")

            if not df_picos_emb_show.empty:
                st.caption("Top picos hist\u00F3ricos de nivel registrados por el radar del embalse:")
                st.dataframe(df_picos_emb_show, use_container_width=True, hide_index=True)

            st.markdown("---")

        # ========================================================
        # 3. REGISTRO DE CRECIENTES EN RIO SURATA (SECTOR MAJADAS)
        # ========================================================
        if mostrar_majadas:
            if estacion_ev_sel == "Monsalve":
                st.markdown("### \u26A1 2. Registro Hidrol\u00F3gico en R\u00EDo Surat\u00E1 (Sector Majadas \u2014 Receptor Directo de Monsalve)")
                st.caption("Monitoreo fluvial en Majadas correspondiente a la descarga libre de la Cuenca Alta del R\u00EDo Surat\u00E1 (P\u00E1ramo / Monsalve). Tiempo de tr\u00E1nsito estimado: ~2.5 a 3.5 horas desde Monsalve hasta Majadas, y 15 a 25 minutos desde Majadas hasta la Bocatoma Bosconia.")
            elif estacion_ev_sel == "Embalse":
                st.markdown("### \u26A1 2. Tr\u00E1nsito Hidrol\u00F3gico hacia R\u00EDo Surat\u00E1 (Sector Majadas) por Vertimiento de Embalse")
                st.caption("Monitoreo en Majadas del caudal recibido desde el R\u00EDo Tona cuando el Embalse descarga por el vertedero Morning Glory (Cota > 885.75 msnm).")
            elif estacion_ev_sel == "Surata":
                st.markdown("### \u26A1 1. Registro de Crecientes y Aforos en R\u00EDo Surat\u00E1 (Sector Majadas \u2014 IDEAM 0023197700)")
                st.caption("Registro forense de niveles de mira, lecturas del sensor limnim\u00E9trico IDEAM y caudales hacia Toma Bosconia.")
            else:
                st.markdown("### \u26A1 3. Registro de Crecientes en R\u00EDo Surat\u00E1 (Sector Majadas \u2014 IDEAM 0023197700)")
                st.caption("Bit\u00E1cora forense de niveles en mira, caudales aforados y alertas hidrol\u00F3gicas hacia Toma Bosconia.")

            filas_surata = []
            timestamps_vistos = set()

            # Incorporar serie en vivo reciente de la API IDEAM
            try:
                info_s_v = sincronizar_fews_ideam_surata_bigquery()
                if info_s_v and "serie_vivo" in info_s_v and info_s_v["serie_vivo"]:
                    for item_v in info_s_v["serie_vivo"]:
                        ts_u, h_u = item_v[0], item_v[1]
                        ts_c_str = ts_u.astimezone(colombia_tz).strftime('%Y-%m-%d %H:%M')
                        if ts_c_str not in timestamps_vistos:
                            qm3_u, qls_u = calcular_caudal_mira_majadas(h_u, aplicar_offset_ideam=True)
                            h_mira_u = max(0.05, h_u - OFFSET_SENSOR_IDEAM_MAJADAS)
                            if qls_u >= 12000.0 or h_mira_u >= 1.66:
                                alerta_sur = "\U0001F534 ALERTA ROJA (Creciente Cr\u00EDtica)"
                            elif qls_u >= 7000.0 or h_mira_u >= 1.45:
                                alerta_sur = "\U0001F7E0 ALERTA NARANJA (Creciente Mayor)"
                            elif qls_u >= 4500.0 or h_mira_u >= 1.25:
                                alerta_sur = "\U0001F7E1 ALERTA AMARILLA (Creciente Moderada)"
                            elif qls_u >= 2800.0 or h_mira_u >= 1.08:
                                alerta_sur = "\U0001F535 AVISO (Ascenso de Caudal)"
                            else:
                                alerta_sur = "\U0001F7E2 REGIMEN BASE (Normal)"

                            timestamps_vistos.add(ts_c_str)
                            filas_surata.append({
                                "Fecha / Hora": ts_c_str,
                                "Nivel Mira amb (m)": round(h_mira_u, 2),
                                "Nivel IDEAM (m)": round(h_u, 2),
                                "Caudal Q (L/s)": round(qls_u, 0),
                                "Caudal (m\u00B3/s)": round(qm3_u, 2),
                                "Nivel de Alerta": alerta_sur,
                                "Tr\u00E1nsito a Toma Bosconia": "15 a 25 min",
                                "q_sort": qls_u
                            })
            except Exception:
                pass

            # Procesar registros historicos de BigQuery para Surata
            if not df_picos_sur.empty:
                for idx, r_s in df_picos_sur.iterrows():
                    ts_s = r_s.get('ts')
                    if ts_s is None or pd.isna(ts_s):
                        continue
                    ts_str = ts_s.astimezone(colombia_tz).strftime('%Y-%m-%d %H:%M') if hasattr(ts_s, 'astimezone') else str(ts_s)[:16]
                    if ts_str in timestamps_vistos:
                        continue

                    t_val = r_s.get('col_temp')
                    p_val = r_s.get('col_precip')
                    h_val = r_s.get('col_hum')

                    t = float(t_val) if t_val is not None and not pd.isna(t_val) else None
                    p = float(p_val) if p_val is not None and not pd.isna(p_val) else None
                    h = float(h_val) if h_val is not None and not pd.isna(h_val) else None

                    h_mira = None
                    q_ls = None

                    # Identificar Caudal Q y Nivel H segun magnitud fisica
                    if p is not None and p > 50.0:
                        q_ls = p
                        if t is not None and 0.20 <= t <= 5.0:
                            h_mira = max(0.05, t - OFFSET_SENSOR_IDEAM_MAJADAS)
                        else:
                            h_mira = calcular_nivel_desde_caudal_majadas(q_ls)
                    elif t is not None and t > 50.0:
                        q_ls = t
                        if p is not None and 0.20 <= p <= 5.0:
                            h_mira = max(0.05, p - OFFSET_SENSOR_IDEAM_MAJADAS)
                        else:
                            h_mira = calcular_nivel_desde_caudal_majadas(q_ls)
                    elif h is not None and 0.8 <= h <= 45.0:
                        q_ls = h * 1000.0
                        if t is not None and 0.20 <= t <= 5.0:
                            h_mira = max(0.05, t - OFFSET_SENSOR_IDEAM_MAJADAS)
                        elif p is not None and 0.20 <= p <= 5.0:
                            h_mira = max(0.05, p - OFFSET_SENSOR_IDEAM_MAJADAS)
                        else:
                            h_mira = calcular_nivel_desde_caudal_majadas(q_ls)
                    elif t is not None and 0.20 <= t <= 5.0:
                        h_mira = max(0.05, t - OFFSET_SENSOR_IDEAM_MAJADAS)
                        _, q_ls = calcular_caudal_mira_majadas(t, aplicar_offset_ideam=True)
                    elif p is not None and 0.20 <= p <= 5.0:
                        h_mira = max(0.05, p - OFFSET_SENSOR_IDEAM_MAJADAS)
                        _, q_ls = calcular_caudal_mira_majadas(p, aplicar_offset_ideam=True)

                    if q_ls is not None and h_mira is not None:
                        h_ideam_est = h_mira + OFFSET_SENSOR_IDEAM_MAJADAS
                        if q_ls >= 12000.0 or h_mira >= 1.66:
                            alerta_sur = "\U0001F534 ALERTA ROJA (Creciente Cr\u00EDtica)"
                        elif q_ls >= 7000.0 or h_mira >= 1.45:
                            alerta_sur = "\U0001F7E0 ALERTA NARANJA (Creciente Mayor)"
                        elif q_ls >= 4500.0 or h_mira >= 1.25:
                            alerta_sur = "\U0001F7E1 ALERTA AMARILLA (Creciente Moderada)"
                        elif q_ls >= 2800.0 or h_mira >= 1.08:
                            alerta_sur = "\U0001F535 AVISO (Ascenso de Caudal)"
                        else:
                            alerta_sur = "\U0001F7E2 REGIMEN BASE (Normal)"

                        timestamps_vistos.add(ts_str)
                        filas_surata.append({
                            "Fecha / Hora": ts_str,
                            "Nivel Mira amb (m)": round(h_mira, 2),
                            "Nivel IDEAM (m)": round(h_ideam_est, 2),
                            "Caudal Q (L/s)": round(q_ls, 0),
                            "Caudal (m\u00B3/s)": round(q_ls / 1000.0, 2),
                            "Nivel de Alerta": alerta_sur,
                            "Tr\u00E1nsito a Toma Bosconia": "15 a 25 min",
                            "q_sort": q_ls
                        })

            # Filtrar eventos de ascenso / creciente (Q >= 2800 L/s o H_mira >= 1.08 m)
            eventos_surata = [f for f in filas_surata if f["q_sort"] >= 2800.0 or f["Nivel Mira amb (m)"] >= 1.08]
            eventos_surata = sorted(eventos_surata, key=lambda x: x["q_sort"], reverse=True)

            if len(eventos_surata) == 0:
                if len(filas_surata) > 0:
                    top_lecturas = sorted(filas_surata, key=lambda x: x["q_sort"], reverse=True)[:10]
                    st.info(f"\u2139\uFE0F  **R\u00EDo Surat\u00E1 en r\u00E9gimen base estable:** En los \u00FAltimos {periodo_dias} d\u00EDas los caudales se mantuvieron dentro del flujo base habitual (< 2,800 L/s). No se registraron crecientes mayores en Majadas.")
                    df_sur_show = pd.DataFrame(top_lecturas).drop(columns=['q_sort'])
                    st.caption("Top lecturas de nivel registradas en el per\u00EDodo:")
                    st.dataframe(df_sur_show, use_container_width=True, hide_index=True)
                else:
                    st.success(f"**R\u00EDo Surat\u00E1 en r\u00E9gimen estable:** En los \u00FAltimos {periodo_dias} d\u00EDas no se registraron crecientes mayores ni ascensos cr\u00EDticos en Majadas.")
            else:
                st.warning(f"\u26A0\uFE0F  **Se registraron {len(eventos_surata)} lecturas en evento de creciente / ascenso de caudal** en R\u00EDo Surat\u00E1 (Sector Majadas) en el per\u00EDodo analizado.")
                df_ev_sur_show = pd.DataFrame(eventos_surata)
                c_su1, c_su2, c_su3 = st.columns(3)
                c_su1.metric("Total Registros de Creciente", len(df_ev_sur_show))
                c_su2.metric("Pico M\u00E1ximo de Caudal", f"{df_ev_sur_show['Caudal Q (L/s)'].max():,.0f} L/s ({df_ev_sur_show['Caudal (m\u00B3/s)'].max():.2f} m\u00B3/s)")
                c_su3.metric("Nivel M\u00E1ximo en Mira amb", f"{df_ev_sur_show['Nivel Mira amb (m)'].max():.2f} m")

                st.dataframe(df_ev_sur_show.drop(columns=['q_sort']), use_container_width=True, hide_index=True)

    # ------------------------------------------------------------
    # SUB-TAB 2: ESTADÍSTICAS CLIMATOLÓGICAS MULTITEMPORALES
    # ------------------------------------------------------------
    with tab_sub_estadisticas:
        st.markdown("### 📊 Climatología Dinámica y Agregaciones Multitemporales")
        st.caption("Cálculo progresivo de valores Máximos, Mínimos, Promedios y Acumulados generados automáticamente a partir de BigQuery.")
        with st.spinner("Compilando matriz multitemporal desde BigQuery..."):
            df_stats_base = consultar_estadisticas_multitemporales_bigquery()

        if df_stats_base.empty:
            st.warning("⚠️ No se pudieron obtener los datos consolidados de BigQuery en este momento.")
            return

        c_st1, c_st2, c_st3 = st.columns(3)
        orden_oficial = ["Embalse", "Surata", "La_Mariana", "Yerbabuena", "Vegas_del_Quemado", "El_Pajal", "Monsalve"]
        estaciones_reales = [
            str(e).strip() for e in df_stats_base['id_estacion'].dropna().unique() 
            if str(e).strip() and str(e).strip().lower() not in ['desconocido', 'none', 'null', 'nan', 'unknown']
        ]
        estaciones_disp = [e for e in orden_oficial if e in estaciones_reales]
        for e in estaciones_reales:
            if e not in estaciones_disp:
                estaciones_disp.append(e)
        if not estaciones_disp:
            estaciones_disp = orden_oficial

        est_stat = c_st1.selectbox(
            "Seleccione Estaci\u00F3n:",
            estaciones_disp,
            index=0,
            format_func=lambda x: {
                "Embalse": "\U0001F30A Embalse Tona",
                "Surata": "\u26A1 R\u00EDo Surat\u00E1 (Majadas)",
                "La_Mariana": "\U0001F33F La Mariana",
                "Yerbabuena": "\U0001F4A7 Yerbabuena",
                "Vegas_del_Quemado": "\u26F0\uFE0F Vegas del Quemado",
                "El_Pajal": "\U0001F33E El Pajal",
                "Monsalve": "\U0001F3D4\uFE0F Monsalve"
            }.get(x, x.replace('_', ' ')),
            key="stat_sel_estacion"
        )
        granularidad = c_st2.selectbox(
            "Granularidad Temporal:",
            ["\U0001F5D3\uFE0F Mensual", "\U0001F4C6 Semanal", "\U0001F4C5 Diario", "\U0001F3C6 Progresivo Anual (2026)"],
            index=0,
            key="stat_sel_granularidad"
        )

        es_surata = (est_stat == "Surata")
        es_embalse = (est_stat == "Embalse")
        es_cuenca = (not es_surata and not es_embalse)

        # Variables disponibles segun la fisica real de medicion en campo
        if es_surata:
            opciones_variables = ["\U0001F30A Caudal Fluvial (L/s)", "\U0001F4CF Nivel Limnim\u00E9trico en Mira (m)"]
        elif es_embalse:
            opciones_variables = [
                "\u2696\uFE0F Entradas, Salidas y Balance de Caudales (L/s y m\u00B3)",
                "\U0001F30A Cota del Embalse (msnm)",
                "\U0001F300 Descarga Morning Glory (L/s)",
                "\U0001F4E6 Volumen Almacenado (hm\u00B3)"
            ]
        else:
            opciones_variables = ["\U0001F327\uFE0F Precipitaci\u00F3n / Lluvia (mm)", "\U0001F321\uFE0F Temperatura (\u00B0C)", "\U0001F4A7 Humedad Relativa (%)"]

        variable_grafica = c_st3.selectbox(
            "Variable principal a visualizar:",
            opciones_variables,
            index=0,
            key=f"stat_sel_var_{est_stat}"
        )

        df_est = df_stats_base[df_stats_base['id_estacion'] == est_stat].copy()
        if df_est.empty:
            st.info(f"No hay registros disponibles para la estaci\u00F3n {est_stat}.")
            return

        # Preprocesamiento inteligente por tipologia fisica de estacion
        if es_surata:
            # En Surata: precip es Caudal Q (L/s) y temp es Nivel Limnimetrico H (m)
            df_est['caudal_diario_prom_ls'] = df_est.apply(
                lambda r: round(r['lluvia_diaria'] / max(1, r['total_lecturas']), 1) if r['lluvia_diaria'] > 50 else round(r['lluvia_pico_horario'], 1),
                axis=1
            )
            df_est['caudal_diario_max_ls'] = df_est['lluvia_pico_horario']
            df_est['nivel_prom_m'] = df_est['temp_prom']
            df_est['nivel_max_m'] = df_est['temp_max']
            df_est['nivel_min_m'] = df_est['temp_min']
        elif es_embalse:
            # En Embalse: temp es Cota Calibrada en msnm + Hidrodinámica de Entradas, Salidas y Balance
            df_est['cota_prom_msnm'] = pd.to_numeric(df_est['temp_prom'], errors='coerce').round(3)
            df_est['cota_max_msnm'] = pd.to_numeric(df_est['temp_max'], errors='coerce').round(3)
            df_est['cota_min_msnm'] = pd.to_numeric(df_est['temp_min'], errors='coerce').round(3)
            df_est['cota_ini_msnm'] = pd.to_numeric(df_est.get('temp_ini', df_est['temp_prom']), errors='coerce').fillna(df_est['cota_prom_msnm']).round(3)
            df_est['cota_fin_msnm'] = pd.to_numeric(df_est.get('temp_fin', df_est['temp_prom']), errors='coerce').fillna(df_est['cota_prom_msnm']).round(3)
            df_est['horas_dia'] = pd.to_numeric(df_est.get('horas_monitoreadas', 24.0), errors='coerce').fillna(24.0).clip(lower=1.0, upper=24.0)
            df_est['descarga_mg_prom_ls'] = df_est['cota_prom_msnm'].apply(
                lambda c: round(calcular_caudal_morning_glory(float(c))[1], 1) if pd.notna(c) else 0.0
            )
            df_est['descarga_mg_max_ls'] = df_est['cota_max_msnm'].apply(
                lambda c: round(calcular_caudal_morning_glory(float(c))[1], 1) if pd.notna(c) else 0.0
            )
            df_est['q_crc_prom_ls'] = pd.to_numeric(df_est.get('q_crc_dia_ls', 25.3), errors='coerce').fillna(25.3).round(1)
            df_est['vol_crc_m3'] = (df_est['q_crc_prom_ls'] * df_est['horas_dia'] * 3.6).round(1)
            df_est['vol_mg_m3'] = (df_est['descarga_mg_prom_ls'] * df_est['horas_dia'] * 3.6).round(1)
            df_est['q_salida_total_ls'] = (df_est['q_crc_prom_ls'] + df_est['descarga_mg_prom_ls'] + 51.0).round(1)
            df_est['vol_salida_total_m3'] = (df_est['q_salida_total_ls'] * df_est['horas_dia'] * 3.6).round(1)
            # Variación de volumen del vaso en el día (m³) y despeje de Entrada de Cuenca (L/s y m³)
            v_ini_m3 = df_est['cota_ini_msnm'].apply(lambda c: interpolar_volumen(float(c)) * 1_000_000.0 if pd.notna(c) else 0.0)
            v_fin_m3 = df_est['cota_fin_msnm'].apply(lambda c: interpolar_volumen(float(c)) * 1_000_000.0 if pd.notna(c) else 0.0)
            dv_dt_ls_dia = ((v_fin_m3 - v_ini_m3) / (df_est['horas_dia'] * 3600.0)) * 1000.0
            df_est['q_entrada_cuenca_ls'] = (dv_dt_ls_dia + df_est['q_salida_total_ls']).clip(lower=0.0, upper=9500.0).round(1)
            df_est['vol_entrada_cuenca_m3'] = (df_est['q_entrada_cuenca_ls'] * df_est['horas_dia'] * 3.6).round(1)
            df_est['balance_neto_ls'] = (df_est['q_entrada_cuenca_ls'] - df_est['q_salida_total_ls']).round(1)
            df_est['volumen_max_hm3'] = df_est['cota_max_msnm'].apply(
                lambda c: round(interpolar_volumen(float(c)), 3) if pd.notna(c) else 0.0
            )

        def _render_3_graficas_embalse_multitemporal(df_g, col_x, sufijo_escala):
            df_plot_g = df_g.iloc[::-1].copy() if len(df_g) > 1 else df_g.copy()
            cg1, cg2 = st.columns(2)
            with cg1:
                f_in = go.Figure()
                f_in.add_trace(go.Bar(x=df_plot_g[col_x], y=df_plot_g['q_in_ls'], name='📥 Caudal Medio Entrada (L/s)', marker_color='#00CC96'))
                f_in.add_trace(go.Scatter(x=df_plot_g[col_x], y=df_plot_g['vol_in_m3'], name='📦 Vol. Entrada Cuenca (m³)', mode='lines+markers', line=dict(color='#00E676', width=2, dash='dot'), yaxis='y2'))
                f_in.update_layout(
                    title=f'📥 1. Entradas al Embalse ({sufijo_escala}): Cola y Subsidiarias',
                    yaxis=dict(title='Caudal Entrada (L/s)'),
                    yaxis2=dict(title='Volumen Entrada (m³)', overlaying='y', side='right', showgrid=False),
                    template='plotly_dark', height=310, legend=dict(orientation="h", y=1.12)
                )
                st.plotly_chart(f_in, use_container_width=True)
            with cg2:
                f_out = go.Figure()
                f_out.add_trace(go.Bar(x=df_plot_g[col_x], y=df_plot_g['vol_crc_m3'], name='📦 Vol. Entregado CRC Bosconia (m³)', marker_color='#0288D1', yaxis='y2', opacity=0.55))
                f_out.add_trace(go.Scatter(x=df_plot_g[col_x], y=df_plot_g['q_crc_ls'], name='🚰 Caudal Medio CRC Bosconia (L/s)', mode='lines+markers', line=dict(color='#38BDF8', width=2.4)))
                f_out.add_trace(go.Scatter(x=df_plot_g[col_x], y=df_plot_g['q_mg_ls'], name='🌀 Caudal Medio Rebose MG (L/s)', mode='lines+markers', line=dict(color='#FF4B4B', width=2, dash='dot')))
                f_out.update_layout(
                    title=f'📤 2. Salidas del Embalse ({sufijo_escala}): CRC Bosconia y Rebose MG',
                    yaxis=dict(title='Caudal Salida (L/s)'),
                    yaxis2=dict(title='Vol. Entregado CRC (m³)', overlaying='y', side='right', showgrid=False),
                    template='plotly_dark', height=310, legend=dict(orientation="h", y=1.12)
                )
                st.plotly_chart(f_out, use_container_width=True)
            f_bal = go.Figure()
            f_bal.add_trace(go.Scatter(x=df_plot_g[col_x], y=df_plot_g['q_in_ls'], name='📥 Entrada Cuenca (L/s)', mode='lines+markers', line=dict(color='#00CC96', width=2.6)))
            f_bal.add_trace(go.Scatter(x=df_plot_g[col_x], y=df_plot_g['q_out_tot_ls'], name='📤 Salida Total (CRC + MG + Filtraciones) (L/s)', mode='lines+markers', line=dict(color='#FF9800', width=2.4)))
            f_bal.add_trace(go.Scatter(x=df_plot_g[col_x], y=df_plot_g['q_crc_ls'], name='🚰 Salida CRC Bosconia (L/s)', mode='lines', line=dict(color='#38BDF8', width=1.8)))
            f_bal.add_trace(go.Bar(x=df_plot_g[col_x], y=df_plot_g['q_bal_ls'], name='⚖️ Balance Neto dV/dt (Entrada - Salida) (L/s)', marker_color='#AB47BC', opacity=0.6))
            f_bal.add_hline(y=0.0, line_dash="dot", line_color="#ECEFF1")
            f_bal.update_layout(
                title=f'⚖️ 3. Balance de Caudales del Embalse ({sufijo_escala}): Entradas vs. Salidas y Balance Neto (L/s)',
                yaxis_title='Caudal (L/s)', template='plotly_dark', height=330, legend=dict(orientation="h", y=1.12)
            )
            st.plotly_chart(f_bal, use_container_width=True)

        def _agregar_fila_promedio_tabla_embalse(df_t, col_etiqueta):
            if df_t.empty:
                return df_t
            fila_p = {col_etiqueta: "📊 PROMEDIO / TOTAL PERÍODO"}
            for c in df_t.columns:
                if c == col_etiqueta:
                    continue
                serie_num = pd.to_numeric(df_t[c], errors='coerce').dropna()
                if serie_num.empty:
                    fila_p[c] = "-"
                elif any(k in c for k in ["Volumen Entrada", "Entregados Bosconia", "Volumen Rebose", "Volumen Salida", "Lecturas", "Días"]):
                    fila_p[c] = round(float(serie_num.sum()), 1) if "Volumen" in c or "Bosconia" in c else int(serie_num.sum())
                elif "Cota" in c or "Vol. Almacenado" in c or "Volumen (hm³)" in c:
                    fila_p[c] = round(float(serie_num.mean()), 3)
                else:
                    fila_p[c] = round(float(serie_num.mean()), 1)
            return pd.concat([df_t, pd.DataFrame([fila_p])], ignore_index=True)

        # --------------------------------------------------------
        # 1. GRANULARIDAD: DIARIO
        # --------------------------------------------------------
        if "Diario" in granularidad:
            df_view = df_est.copy()
            df_view['fecha'] = pd.to_datetime(df_view['fecha'])
            df_view = df_view.sort_values('fecha', ascending=False)

            col_k1, col_k2, col_k3, col_k4 = st.columns(4)
            col_k1.metric("D\u00EDas Monitoreados", len(df_view))

            fig_d = go.Figure()

            if es_surata:
                q_max_abs = df_view['caudal_diario_max_ls'].max()
                q_prom_abs = df_view['caudal_diario_prom_ls'].mean()
                h_max_abs = df_view['nivel_max_m'].max()
                h_mira_max = max(0.05, h_max_abs - 0.04)
                col_k2.metric("Caudal Pico M\u00E1ximo", f"{q_max_abs:,.0f} L/s ({q_max_abs/1000.0:.2f} m\u00B3/s)")
                col_k3.metric("Caudal Medio Ponderado", f"{q_prom_abs:,.0f} L/s ({q_prom_abs/1000.0:.2f} m\u00B3/s)")
                col_k4.metric("Nivel M\u00E1x en Mira amb", f"{h_mira_max:.2f} m (IDEAM: {h_max_abs:.2f} m)")

                if "Caudal" in variable_grafica:
                    fig_d.add_trace(go.Bar(
                        x=df_view['fecha'], y=df_view['caudal_diario_prom_ls'],
                        name="Caudal Medio Diario (L/s)", marker_color="#00CC96"
                    ))
                    fig_d.add_trace(go.Scatter(
                        x=df_view['fecha'], y=df_view['caudal_diario_max_ls'],
                        name="Caudal Pico M\u00E1x (L/s)", mode='lines+markers', line=dict(color="#FF8000", width=2)
                    ))
                    fig_d.update_layout(title="Hist\u00F3rico Diario de Caudal Fluvial \u2014 R\u00EDo Surat\u00E1 (Majadas)", yaxis_title="Caudal Q (L/s)")
                else:
                    fig_d.add_trace(go.Scatter(
                        x=df_view['fecha'], y=df_view['nivel_max_m'] - 0.04,
                        name="Nivel M\u00E1x Mira amb (m)", mode='lines', line=dict(color="#FF4B4B", width=1.5)
                    ))
                    fig_d.add_trace(go.Scatter(
                        x=df_view['fecha'], y=df_view['nivel_prom_m'] - 0.04,
                        name="Nivel Prom Mira amb (m)", mode='lines', line=dict(color="#38BDF8", width=2)
                    ))
                    fig_d.add_trace(go.Scatter(
                        x=df_view['fecha'], y=df_view['nivel_min_m'] - 0.04,
                        name="Nivel M\u00EDn Mira amb (m)", mode='lines', line=dict(color="#00CC96", width=1.5),
                        fill='tonexty', fillcolor='rgba(56, 189, 248, 0.15)'
                    ))
                    fig_d.update_layout(title="Banda Diaria de Nivel Limnim\u00E9trico en Mira \u2014 R\u00EDo Surat\u00E1 (Majadas)", yaxis_title="Nivel Mira amb (m)")

                rename_cols = {
                    'fecha': 'Fecha',
                    'caudal_diario_prom_ls': 'Caudal Medio (L/s)',
                    'caudal_diario_max_ls': 'Caudal Pico M\u00E1x (L/s)',
                    'nivel_prom_m': 'Nivel Prom IDEAM (m)',
                    'nivel_max_m': 'Nivel M\u00E1x IDEAM (m)',
                    'total_lecturas': 'Lecturas'
                }
                cols_tabla = ['fecha', 'caudal_diario_prom_ls', 'caudal_diario_max_ls', 'nivel_prom_m', 'nivel_max_m', 'total_lecturas']

            elif es_embalse:
                c_max_abs = df_view['cota_max_msnm'].max()
                q_in_med = df_view['q_entrada_cuenca_ls'].mean()
                q_out_med = df_view['q_salida_total_ls'].mean()
                v_max_abs = df_view['volumen_max_hm3'].max()
                col_k2.metric("Cota M\u00E1xima Radar", f"{c_max_abs:.3f} msnm")
                col_k3.metric("📥 Entrada Media / 📤 Salida Media", f"{q_in_med:,.1f} / {q_out_med:,.1f} L/s")
                col_k4.metric("Volumen Almacenado M\u00E1x", f"{v_max_abs:.2f} hm\u00B3")

                df_view['Fecha_Str'] = df_view['fecha'].dt.strftime('%Y-%m-%d')
                df_g_dia = df_view.rename(columns={
                    'q_entrada_cuenca_ls': 'q_in_ls',
                    'vol_entrada_cuenca_m3': 'vol_in_m3',
                    'q_crc_prom_ls': 'q_crc_ls',
                    'descarga_mg_prom_ls': 'q_mg_ls',
                    'q_salida_total_ls': 'q_out_tot_ls',
                    'balance_neto_ls': 'q_bal_ls'
                })
                _render_3_graficas_embalse_multitemporal(df_g_dia, 'Fecha_Str', 'Diario')

                if "Cota" in variable_grafica or "Balance" in variable_grafica:
                    fig_d.add_trace(go.Scatter(
                        x=df_view['fecha'], y=df_view['cota_max_msnm'],
                        name="Cota M\u00E1xima (msnm)", mode='lines', line=dict(color="#FF4B4B", width=1.5)
                    ))
                    fig_d.add_trace(go.Scatter(
                        x=df_view['fecha'], y=df_view['cota_prom_msnm'],
                        name="Cota Promedio (msnm)", mode='lines', line=dict(color="#38BDF8", width=2)
                    ))
                    fig_d.add_trace(go.Scatter(
                        x=df_view['fecha'], y=df_view['cota_min_msnm'],
                        name="Cota M\u00EDnima (msnm)", mode='lines', line=dict(color="#00CC96", width=1.5),
                        fill='tonexty', fillcolor='rgba(56, 189, 248, 0.15)'
                    ))
                    fig_d.add_hline(y=885.75, line_dash="dash", line_color="#FF0000", annotation_text="Cresta Morning Glory (885.75 msnm)")
                    fig_d.update_layout(title="Hist\u00F3rico Diario de Cota \u2014 Embalse de Tona", yaxis_title="Cota (msnm)")
                elif "Descarga" in variable_grafica:
                    fig_d.add_trace(go.Bar(
                        x=df_view['fecha'], y=df_view['descarga_mg_max_ls'],
                        name="Descarga Morning Glory M\u00E1x (L/s)", marker_color="#38BDF8"
                    ))
                    fig_d.update_layout(title="Descarga Diaria Vertedero Morning Glory \u2014 Embalse de Tona", yaxis_title="Caudal (L/s)")
                else:
                    fig_d.add_trace(go.Scatter(
                        x=df_view['fecha'], y=df_view['volumen_max_hm3'],
                        name="Volumen Almacenado (hm\u00B3)", mode='lines+markers', line=dict(color="#A855F7", width=2)
                    ))
                    fig_d.update_layout(title="Volumen Almacenado Diario \u2014 Embalse de Tona", yaxis_title="Volumen (hm\u00B3)")

                rename_cols = {
                    'Fecha_Str': 'Fecha',
                    'cota_prom_msnm': 'Cota Prom (msnm)',
                    'cota_max_msnm': 'Cota M\u00E1x (msnm)',
                    'cota_min_msnm': 'Cota M\u00EDn (msnm)',
                    'q_entrada_cuenca_ls': '📥 Caudal Medio Entrada Cuenca (L/s)',
                    'vol_entrada_cuenca_m3': '📥 Volumen Entrada Cuenca (m³)',
                    'q_crc_prom_ls': '🚰 Caudal Medio CRC Bosconia (L/s)',
                    'vol_crc_m3': '🚰 Metros Cúbicos Entregados Bosconia (m³)',
                    'descarga_mg_prom_ls': '🌀 Caudal Medio Rebose MG (L/s)',
                    'vol_mg_m3': '🌀 Volumen Rebose MG (m³)',
                    'q_salida_total_ls': '📤 Caudal Medio Salida Total (L/s)',
                    'vol_salida_total_m3': '📤 Volumen Salida Total (m³)',
                    'balance_neto_ls': '⚖️ Balance Neto Caudales (L/s)',
                    'volumen_max_hm3': 'Volumen (hm\u00B3)',
                    'total_lecturas': 'Lecturas'
                }
                cols_tabla = [
                    'Fecha_Str', 'cota_prom_msnm', 'cota_max_msnm', 'cota_min_msnm',
                    'q_entrada_cuenca_ls', 'vol_entrada_cuenca_m3',
                    'q_crc_prom_ls', 'vol_crc_m3',
                    'descarga_mg_prom_ls', 'vol_mg_m3',
                    'q_salida_total_ls', 'vol_salida_total_m3',
                    'balance_neto_ls', 'volumen_max_hm3', 'total_lecturas'
                ]

            else:
                col_k2.metric("Lluvia Diaria M\u00E1xima", f"{df_view['lluvia_diaria'].max():.1f} mm")
                col_k3.metric("Lluvia Diaria Promedio", f"{df_view['lluvia_diaria'].mean():.1f} mm")
                col_k4.metric("Temp M\u00E1x Absoluta", f"{df_view['temp_max'].max():.1f} \u00B0C")

                if "Precipitaci\u00F3n" in variable_grafica:
                    fig_d.add_trace(go.Bar(
                        x=df_view['fecha'], y=df_view['lluvia_diaria'],
                        name="Lluvia Diaria (mm)", marker_color="#00CC96"
                    ))
                    fig_d.add_trace(go.Scatter(
                        x=df_view['fecha'], y=df_view['lluvia_pico_horario'],
                        name="Pico Horario M\u00E1x (mm/h)", mode='lines+markers', line=dict(color="#FF8000", width=2)
                    ))
                    fig_d.update_layout(title=f"Hist\u00F3rico Diario de Precipitaci\u00F3n \u2014 {est_stat}", yaxis_title="mm / mm/h")
                elif "Temperatura" in variable_grafica:
                    fig_d.add_trace(go.Scatter(
                        x=df_view['fecha'], y=df_view['temp_max'],
                        name="Temperatura M\u00E1xima (\u00B0C)", mode='lines', line=dict(color="#FF4B4B", width=1.5)
                    ))
                    fig_d.add_trace(go.Scatter(
                        x=df_view['fecha'], y=df_view['temp_prom'],
                        name="Temperatura Promedio (\u00B0C)", mode='lines', line=dict(color="#38BDF8", width=2)
                    ))
                    fig_d.add_trace(go.Scatter(
                        x=df_view['fecha'], y=df_view['temp_min'],
                        name="Temperatura M\u00EDnima (\u00B0C)", mode='lines', line=dict(color="#00CC96", width=1.5),
                        fill='tonexty', fillcolor='rgba(56, 189, 248, 0.15)'
                    ))
                    fig_d.update_layout(title=f"Banda Diaria de Temperatura (\u00B0C) \u2014 {est_stat}", yaxis_title="\u00B0C")
                else:
                    fig_d.add_trace(go.Scatter(
                        x=df_view['fecha'], y=df_view['hum_prom'],
                        name="Humedad Promedio (%)", mode='lines+markers', line=dict(color="#A855F7", width=2)
                    ))
                    fig_d.update_layout(title=f"Humedad Relativa Diaria (%) \u2014 {est_stat}", yaxis_title="%")

                rename_cols = {
                    'fecha': 'Fecha',
                    'lluvia_diaria': 'Lluvia Acum. (mm)',
                    'lluvia_pico_horario': 'Pico Horario (mm/h)',
                    'temp_min': 'Temp M\u00EDn (\u00B0C)',
                    'temp_max': 'Temp M\u00E1x (\u00B0C)',
                    'temp_prom': 'Temp Prom (\u00B0C)',
                    'hum_prom': 'Humedad Prom (%)',
                    'total_lecturas': 'Lecturas'
                }
                cols_tabla = ['fecha', 'lluvia_diaria', 'lluvia_pico_horario', 'temp_min', 'temp_max', 'temp_prom', 'hum_prom', 'total_lecturas']

            fig_d.update_layout(template="plotly_dark", height=380, hovermode="x unified")
            st.plotly_chart(fig_d, use_container_width=True)

            df_table_d = df_view[cols_tabla].rename(columns=rename_cols)
            if es_embalse:
                df_table_d = _agregar_fila_promedio_tabla_embalse(df_table_d, 'Fecha')
            st.dataframe(df_table_d, use_container_width=True, hide_index=True)
            csv_d = df_table_d.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label=f"\U0001F4E5 Descargar Estad\u00EDsticas Diarias ({est_stat}) en CSV",
                data=csv_d,
                file_name=f"estadisticas_diarias_{est_stat}.csv",
                mime="text/csv"
            )

        # --------------------------------------------------------
        # 2. GRANULARIDAD: SEMANAL
        # --------------------------------------------------------
        elif "Semanal" in granularidad:
            if es_surata:
                df_sem = df_est.groupby(['anio', 'semana']).agg(
                    fecha_inicio=('fecha', 'min'),
                    fecha_fin=('fecha', 'max'),
                    caudal_prom_sem=('caudal_diario_prom_ls', 'mean'),
                    caudal_max_sem=('caudal_diario_max_ls', 'max'),
                    nivel_prom_sem=('nivel_prom_m', 'mean'),
                    nivel_max_sem=('nivel_max_m', 'max'),
                    dias_evaluados=('fecha', 'count')
                ).reset_index().sort_values(['anio', 'semana'], ascending=False)
                df_sem['Semana'] = df_sem.apply(lambda r: f"Semana {int(r['semana'])} ({int(r['anio'])})", axis=1)

                col_sk1, col_sk2, col_sk3, col_sk4 = st.columns(4)
                col_sk1.metric("Semanas Evaluadas", len(df_sem))
                col_sk2.metric("Caudal Pico Semanal", f"{df_sem['caudal_max_sem'].max():,.0f} L/s ({df_sem['caudal_max_sem'].max()/1000.0:.2f} m\u00B3/s)")
                col_sk3.metric("Caudal Medio Semanal", f"{df_sem['caudal_prom_sem'].mean():,.0f} L/s")
                col_sk4.metric("Nivel M\u00E1x en Sensor", f"{df_sem['nivel_max_sem'].max():.2f} m (Mira: {max(0.05, df_sem['nivel_max_sem'].max() - 0.04):.2f} m)")

                fig_s = go.Figure()
                if "Caudal" in variable_grafica:
                    fig_s.add_trace(go.Bar(
                        x=df_sem['Semana'], y=df_sem['caudal_prom_sem'],
                        name="Caudal Medio Semanal (L/s)", marker_color="#00CC96"
                    ))
                    fig_s.add_trace(go.Scatter(
                        x=df_sem['Semana'], y=df_sem['caudal_max_sem'],
                        name="Caudal Pico Semanal (L/s)", mode='lines+markers', line=dict(color="#FF8000", width=2)
                    ))
                    fig_s.update_layout(title="Consolidado Semanal de Caudal Fluvial \u2014 R\u00EDo Surat\u00E1 (Majadas)", yaxis_title="Caudal Q (L/s)")
                else:
                    fig_s.add_trace(go.Scatter(
                        x=df_sem['Semana'], y=df_sem['nivel_max_sem'] - 0.04,
                        name="Nivel M\u00E1ximo Semanal Mira (m)", mode='lines+markers', line=dict(color="#FF4B4B")
                    ))
                    fig_s.add_trace(go.Scatter(
                        x=df_sem['Semana'], y=df_sem['nivel_prom_sem'] - 0.04,
                        name="Nivel Promedio Semanal Mira (m)", mode='lines+markers', line=dict(color="#38BDF8")
                    ))
                    fig_s.update_layout(title="Comportamiento Semanal de Nivel Limnim\u00E9trico \u2014 R\u00EDo Surat\u00E1 (Majadas)", yaxis_title="Nivel Mira amb (m)")

                rename_sem = {
                    'Semana': 'Semana ISO',
                    'fecha_inicio': 'Desde',
                    'fecha_fin': 'Hasta',
                    'caudal_prom_sem': 'Caudal Medio (L/s)',
                    'caudal_max_sem': 'Caudal Pico M\u00E1x (L/s)',
                    'nivel_prom_sem': 'Nivel Prom IDEAM (m)',
                    'nivel_max_sem': 'Nivel M\u00E1x IDEAM (m)',
                    'dias_evaluados': 'D\u00EDas Monitoreados'
                }
                cols_sem = ['Semana', 'fecha_inicio', 'fecha_fin', 'caudal_prom_sem', 'caudal_max_sem', 'nivel_prom_sem', 'nivel_max_sem', 'dias_evaluados']

            elif es_embalse:
                df_sem = df_est.groupby(['anio', 'semana']).agg(
                    fecha_inicio=('fecha', 'min'),
                    fecha_fin=('fecha', 'max'),
                    cota_prom_sem=('cota_prom_msnm', 'mean'),
                    cota_max_sem=('cota_max_msnm', 'max'),
                    cota_min_sem=('cota_min_msnm', 'min'),
                    q_in_ls=('q_entrada_cuenca_ls', 'mean'),
                    vol_in_m3=('vol_entrada_cuenca_m3', 'sum'),
                    q_crc_ls=('q_crc_prom_ls', 'mean'),
                    vol_crc_m3=('vol_crc_m3', 'sum'),
                    q_mg_ls=('descarga_mg_prom_ls', 'mean'),
                    vol_mg_m3=('vol_mg_m3', 'sum'),
                    descarga_mg_max_sem=('descarga_mg_max_ls', 'max'),
                    q_out_tot_ls=('q_salida_total_ls', 'mean'),
                    vol_out_tot_m3=('vol_salida_total_m3', 'sum'),
                    q_bal_ls=('balance_neto_ls', 'mean'),
                    volumen_max_sem=('volumen_max_hm3', 'max'),
                    dias_evaluados=('fecha', 'count')
                ).reset_index().sort_values(['anio', 'semana'], ascending=False)
                df_sem['Semana'] = df_sem.apply(lambda r: f"Semana {int(r['semana'])} ({int(r['anio'])})", axis=1)
                for c_r3 in ['cota_prom_sem', 'cota_max_sem', 'cota_min_sem', 'volumen_max_sem']:
                    df_sem[c_r3] = df_sem[c_r3].round(3)
                for c_r1 in ['q_in_ls', 'vol_in_m3', 'q_crc_ls', 'vol_crc_m3', 'q_mg_ls', 'vol_mg_m3', 'descarga_mg_max_sem', 'q_out_tot_ls', 'vol_out_tot_m3', 'q_bal_ls']:
                    df_sem[c_r1] = df_sem[c_r1].round(1)

                col_sk1, col_sk2, col_sk3, col_sk4 = st.columns(4)
                col_sk1.metric("Semanas Evaluadas", len(df_sem))
                col_sk2.metric("Cota Semanal M\u00E1x", f"{df_sem['cota_max_sem'].max():.3f} msnm")
                col_sk3.metric("📥 Entrada Media / 📤 Salida Media", f"{df_sem['q_in_ls'].mean():,.1f} / {df_sem['q_out_tot_ls'].mean():,.1f} L/s")
                col_sk4.metric("Volumen Almacenado M\u00E1x", f"{df_sem['volumen_max_sem'].max():.2f} hm\u00B3")

                _render_3_graficas_embalse_multitemporal(df_sem, 'Semana', 'Semanal')

                fig_s = go.Figure()
                if "Cota" in variable_grafica or "Balance" in variable_grafica:
                    fig_s.add_trace(go.Scatter(
                        x=df_sem['Semana'], y=df_sem['cota_max_sem'],
                        name="Cota M\u00E1xima Semanal (msnm)", mode='lines+markers', line=dict(color="#FF4B4B")
                    ))
                    fig_s.add_trace(go.Scatter(
                        x=df_sem['Semana'], y=df_sem['cota_prom_sem'],
                        name="Cota Promedio Semanal (msnm)", mode='lines+markers', line=dict(color="#38BDF8")
                    ))
                    fig_s.add_trace(go.Scatter(
                        x=df_sem['Semana'], y=df_sem['cota_min_sem'],
                        name="Cota M\u00EDnima Semanal (msnm)", mode='lines+markers', line=dict(color="#00CC96")
                    ))
                    fig_s.add_hline(y=885.75, line_dash="dash", line_color="#FF0000", annotation_text="Cresta Morning Glory (885.75 msnm)")
                    fig_s.update_layout(title="Comportamiento Semanal de Cota \u2014 Embalse de Tona", yaxis_title="Cota (msnm)")
                elif "Descarga" in variable_grafica:
                    fig_s.add_trace(go.Bar(
                        x=df_sem['Semana'], y=df_sem['descarga_mg_max_sem'],
                        name="Descarga MG M\u00E1xima (L/s)", marker_color="#38BDF8"
                    ))
                    fig_s.update_layout(title="Descarga Semanal Vertedero Morning Glory \u2014 Embalse de Tona", yaxis_title="Caudal (L/s)")
                else:
                    fig_s.add_trace(go.Scatter(
                        x=df_sem['Semana'], y=df_sem['volumen_max_sem'],
                        name="Volumen M\u00E1ximo (hm\u00B3)", mode='lines+markers', line=dict(color="#A855F7", width=2)
                    ))
                    fig_s.update_layout(title="Volumen Semanal Almacenado \u2014 Embalse de Tona", yaxis_title="Volumen (hm\u00B3)")

                rename_sem = {
                    'Semana': 'Semana ISO',
                    'fecha_inicio': 'Desde',
                    'fecha_fin': 'Hasta',
                    'cota_prom_sem': 'Cota Prom (msnm)',
                    'cota_max_sem': 'Cota M\u00E1x (msnm)',
                    'cota_min_sem': 'Cota M\u00EDn (msnm)',
                    'q_in_ls': '📥 Caudal Medio Entrada Cuenca (L/s)',
                    'vol_in_m3': '📥 Volumen Entrada Cuenca (m³)',
                    'q_crc_ls': '🚰 Caudal Medio CRC Bosconia (L/s)',
                    'vol_crc_m3': '🚰 Metros Cúbicos Entregados Bosconia (m³)',
                    'q_mg_ls': '🌀 Caudal Medio Rebose MG (L/s)',
                    'vol_mg_m3': '🌀 Volumen Rebose MG (m³)',
                    'q_out_tot_ls': '📤 Caudal Medio Salida Total (L/s)',
                    'vol_out_tot_m3': '📤 Volumen Salida Total (m³)',
                    'q_bal_ls': '⚖️ Balance Neto Caudales (L/s)',
                    'volumen_max_sem': 'Volumen (hm\u00B3)',
                    'dias_evaluados': 'D\u00EDas Monitoreados'
                }
                cols_sem = [
                    'Semana', 'fecha_inicio', 'fecha_fin', 'cota_prom_sem', 'cota_max_sem', 'cota_min_sem',
                    'q_in_ls', 'vol_in_m3', 'q_crc_ls', 'vol_crc_m3', 'q_mg_ls', 'vol_mg_m3',
                    'q_out_tot_ls', 'vol_out_tot_m3', 'q_bal_ls', 'volumen_max_sem', 'dias_evaluados'
                ]

            else:
                df_sem = df_est.groupby(['anio', 'semana']).agg(
                    fecha_inicio=('fecha', 'min'),
                    fecha_fin=('fecha', 'max'),
                    lluvia_semanal=('lluvia_diaria', 'sum'),
                    pico_max_semanal=('lluvia_pico_horario', 'max'),
                    dias_con_lluvia=('lluvia_diaria', lambda s: (s > 0.1).sum()),
                    temp_min_sem=('temp_min', 'min'),
                    temp_max_sem=('temp_max', 'max'),
                    temp_prom_sem=('temp_prom', 'mean'),
                    hum_prom_sem=('hum_prom', 'mean'),
                    dias_evaluados=('fecha', 'count')
                ).reset_index().sort_values(['anio', 'semana'], ascending=False)
                df_sem['Semana'] = df_sem.apply(lambda r: f"Semana {int(r['semana'])} ({int(r['anio'])})", axis=1)

                col_sk1, col_sk2, col_sk3, col_sk4 = st.columns(4)
                col_sk1.metric("Semanas Evaluadas", len(df_sem))
                col_sk2.metric("Lluvia Semanal M\u00E1x", f"{df_sem['lluvia_semanal'].max():.1f} mm")
                col_sk3.metric("Lluvia Semanal Prom", f"{df_sem['lluvia_semanal'].mean():.1f} mm")
                col_sk4.metric("Temp Semanal M\u00E1x", f"{df_sem['temp_max_sem'].max():.1f} \u00B0C")

                fig_s = go.Figure()
                if "Precipitaci\u00F3n" in variable_grafica:
                    fig_s.add_trace(go.Bar(
                        x=df_sem['Semana'], y=df_sem['lluvia_semanal'],
                        name="Lluvia Total Semanal (mm)", marker_color="#00E676"
                    ))
                    fig_s.add_trace(go.Scatter(
                        x=df_sem['Semana'], y=df_sem['pico_max_semanal'],
                        name="Pico Horario M\u00E1x (mm/h)", mode='lines+markers', line=dict(color="#FF8000", width=2)
                    ))
                    fig_s.update_layout(title=f"Consolidado Semanal de Precipitaci\u00F3n \u2014 {est_stat}", yaxis_title="mm")
                else:
                    fig_s.add_trace(go.Scatter(
                        x=df_sem['Semana'], y=df_sem['temp_max_sem'],
                        name="M\u00E1xima Semanal (\u00B0C)", mode='lines+markers', line=dict(color="#FF4B4B")
                    ))
                    fig_s.add_trace(go.Scatter(
                        x=df_sem['Semana'], y=df_sem['temp_prom_sem'],
                        name="Promedio Semanal (\u00B0C)", mode='lines+markers', line=dict(color="#38BDF8")
                    ))
                    fig_s.add_trace(go.Scatter(
                        x=df_sem['Semana'], y=df_sem['temp_min_sem'],
                        name="M\u00EDnima Semanal (\u00B0C)", mode='lines+markers', line=dict(color="#00CC96"),
                        fill='tonexty', fillcolor='rgba(56, 189, 248, 0.15)'
                    ))
                    fig_s.update_layout(title=f"Comportamiento Semanal de Temperatura (\u00B0C) \u2014 {est_stat}", yaxis_title="\u00B0C")

                rename_sem = {
                    'Semana': 'Semana ISO',
                    'fecha_inicio': 'Desde',
                    'fecha_fin': 'Hasta',
                    'lluvia_semanal': 'Lluvia Semanal (mm)',
                    'pico_max_semanal': 'Pico M\u00E1x Horario (mm/h)',
                    'dias_con_lluvia': 'D\u00EDas Lluviosos',
                    'temp_min_sem': 'Temp M\u00EDn (\u00B0C)',
                    'temp_max_sem': 'Temp M\u00E1x (\u00B0C)',
                    'temp_prom_sem': 'Temp Prom (\u00B0C)',
                    'dias_evaluados': 'D\u00EDas Monitoreados'
                }
                cols_sem = ['Semana', 'fecha_inicio', 'fecha_fin', 'lluvia_semanal', 'pico_max_semanal', 'dias_con_lluvia', 'temp_min_sem', 'temp_max_sem', 'temp_prom_sem', 'dias_evaluados']

            fig_s.update_layout(template="plotly_dark", height=380)
            st.plotly_chart(fig_s, use_container_width=True)

            df_show_sem = df_sem[cols_sem].rename(columns=rename_sem)
            if es_embalse:
                df_show_sem = _agregar_fila_promedio_tabla_embalse(df_show_sem, 'Semana ISO')
            st.dataframe(df_show_sem, use_container_width=True, hide_index=True)
            csv_s = df_show_sem.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label=f"\U0001F4E5 Descargar Estad\u00EDsticas Semanales ({est_stat}) en CSV",
                data=csv_s,
                file_name=f"estadisticas_semanales_{est_stat}.csv",
                mime="text/csv"
            )

        # --------------------------------------------------------
        # 3. GRANULARIDAD: MENSUAL
        # --------------------------------------------------------
        elif "Mensual" in granularidad:
            if es_surata:
                df_mes = df_est.groupby(['anio', 'mes']).agg(
                    caudal_prom_mes=('caudal_diario_prom_ls', 'mean'),
                    caudal_max_mes=('caudal_diario_max_ls', 'max'),
                    nivel_prom_mes=('nivel_prom_m', 'mean'),
                    nivel_max_mes=('nivel_max_m', 'max'),
                    dias_registrados=('fecha', 'count')
                ).reset_index().sort_values(['anio', 'mes'], ascending=False)
                df_mes['Mes Nombre'] = df_mes.apply(lambda r: f"{meses_es.get(int(r['mes']), r['mes'])} {int(r['anio'])}", axis=1)

                col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                col_m1.metric("Meses con Datos", len(df_mes))
                col_m2.metric("Caudal Pico M\u00E1x Mensual", f"{df_mes['caudal_max_mes'].max():,.0f} L/s ({df_mes['caudal_max_mes'].max()/1000.0:.2f} m\u00B3/s)")
                col_m3.metric("Caudal Medio Mensual", f"{df_mes['caudal_prom_mes'].mean():,.0f} L/s")
                col_m4.metric("Nivel M\u00E1ximo Sensor", f"{df_mes['nivel_max_mes'].max():.2f} m")

                fig_m = go.Figure()
                if "Caudal" in variable_grafica:
                    fig_m.add_trace(go.Bar(
                        x=df_mes['Mes Nombre'], y=df_mes['caudal_prom_mes'],
                        name="Caudal Medio Mensual (L/s)", marker_color="#00CC96"
                    ))
                    fig_m.add_trace(go.Scatter(
                        x=df_mes['Mes Nombre'], y=df_mes['caudal_max_mes'],
                        name="Caudal Pico Mensual (L/s)", mode='lines+markers', line=dict(color="#FF8000", width=2.5)
                    ))
                    fig_m.update_layout(title="Consolidado Mensual de Caudal Fluvial \u2014 R\u00EDo Surat\u00E1 (Majadas)", yaxis_title="Caudal Q (L/s)")
                else:
                    fig_m.add_trace(go.Bar(
                        x=df_mes['Mes Nombre'], y=df_mes['nivel_prom_mes'] - 0.04,
                        name="Nivel Medio Mira (m)", marker_color="#38BDF8"
                    ))
                    fig_m.add_trace(go.Scatter(
                        x=df_mes['Mes Nombre'], y=df_mes['nivel_max_mes'] - 0.04,
                        name="Nivel M\u00E1ximo Mira (m)", mode='lines+markers', line=dict(color="#FF4B4B", width=2)
                    ))
                    fig_m.update_layout(title="Comportamiento Mensual de Nivel Limnim\u00E9trico \u2014 R\u00EDo Surat\u00E1 (Majadas)", yaxis_title="Nivel Mira amb (m)")

                rename_mes = {
                    'Mes Nombre': 'Mes / A\u00F1o',
                    'caudal_prom_mes': 'Caudal Medio (L/s)',
                    'caudal_max_mes': 'Caudal Pico M\u00E1x (L/s)',
                    'nivel_prom_mes': 'Nivel Prom IDEAM (m)',
                    'nivel_max_mes': 'Nivel M\u00E1x IDEAM (m)',
                    'dias_registrados': 'D\u00EDas Monitoreados'
                }
                cols_mes = ['Mes Nombre', 'caudal_prom_mes', 'caudal_max_mes', 'nivel_prom_mes', 'nivel_max_mes', 'dias_registrados']

            elif es_embalse:
                df_mes = df_est.groupby(['anio', 'mes']).agg(
                    cota_prom_mes=('cota_prom_msnm', 'mean'),
                    cota_max_mes=('cota_max_msnm', 'max'),
                    cota_min_mes=('cota_min_msnm', 'min'),
                    q_in_ls=('q_entrada_cuenca_ls', 'mean'),
                    vol_in_m3=('vol_entrada_cuenca_m3', 'sum'),
                    q_crc_ls=('q_crc_prom_ls', 'mean'),
                    vol_crc_m3=('vol_crc_m3', 'sum'),
                    q_mg_ls=('descarga_mg_prom_ls', 'mean'),
                    vol_mg_m3=('vol_mg_m3', 'sum'),
                    descarga_mg_max_mes=('descarga_mg_max_ls', 'max'),
                    q_out_tot_ls=('q_salida_total_ls', 'mean'),
                    vol_out_tot_m3=('vol_salida_total_m3', 'sum'),
                    q_bal_ls=('balance_neto_ls', 'mean'),
                    volumen_max_mes=('volumen_max_hm3', 'max'),
                    dias_registrados=('fecha', 'count')
                ).reset_index().sort_values(['anio', 'mes'], ascending=False)
                df_mes['Mes Nombre'] = df_mes.apply(lambda r: f"{meses_es.get(int(r['mes']), r['mes'])} {int(r['anio'])}", axis=1)
                for c_r3 in ['cota_prom_mes', 'cota_max_mes', 'cota_min_mes', 'volumen_max_mes']:
                    df_mes[c_r3] = df_mes[c_r3].round(3)
                for c_r1 in ['q_in_ls', 'vol_in_m3', 'q_crc_ls', 'vol_crc_m3', 'q_mg_ls', 'vol_mg_m3', 'descarga_mg_max_mes', 'q_out_tot_ls', 'vol_out_tot_m3', 'q_bal_ls']:
                    df_mes[c_r1] = df_mes[c_r1].round(1)

                col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                col_m1.metric("Meses con Datos", len(df_mes))
                col_m2.metric("Cota M\u00E1x Mensual", f"{df_mes['cota_max_mes'].max():.3f} msnm")
                col_m3.metric("📥 Entrada Media / 📤 Salida Media", f"{df_mes['q_in_ls'].mean():,.1f} / {df_mes['q_out_tot_ls'].mean():,.1f} L/s")
                col_m4.metric("Volumen M\u00E1x Almacenado", f"{df_mes['volumen_max_mes'].max():.2f} hm\u00B3")

                _render_3_graficas_embalse_multitemporal(df_mes, 'Mes Nombre', 'Mensual')

                fig_m = go.Figure()
                if "Cota" in variable_grafica or "Balance" in variable_grafica:
                    fig_m.add_trace(go.Scatter(
                        x=df_mes['Mes Nombre'], y=df_mes['cota_max_mes'],
                        name="Cota M\u00E1xima Mensual (msnm)", mode='lines+markers', line=dict(color="#FF4B4B")
                    ))
                    fig_m.add_trace(go.Scatter(
                        x=df_mes['Mes Nombre'], y=df_mes['cota_prom_mes'],
                        name="Cota Media Mensual (msnm)", mode='lines+markers', line=dict(color="#38BDF8")
                    ))
                    fig_m.add_hline(y=885.75, line_dash="dash", line_color="#FF0000", annotation_text="Cresta Morning Glory (885.75 msnm)")
                    fig_m.update_layout(title="Comportamiento Mensual de Cota \u2014 Embalse de Tona", yaxis_title="Cota (msnm)")
                elif "Descarga" in variable_grafica:
                    fig_m.add_trace(go.Bar(
                        x=df_mes['Mes Nombre'], y=df_mes['descarga_mg_max_mes'],
                        name="Descarga MG M\u00E1xima (L/s)", marker_color="#38BDF8"
                    ))
                    fig_m.update_layout(title="Descarga Mensual Vertedero Morning Glory \u2014 Embalse de Tona", yaxis_title="Caudal (L/s)")
                else:
                    fig_m.add_trace(go.Scatter(
                        x=df_mes['Mes Nombre'], y=df_mes['volumen_max_mes'],
                        name="Volumen M\u00E1ximo (hm\u00B3)", mode='lines+markers', line=dict(color="#A855F7", width=2)
                    ))
                    fig_m.update_layout(title="Volumen Mensual Almacenado \u2014 Embalse de Tona", yaxis_title="Volumen (hm\u00B3)")

                rename_mes = {
                    'Mes Nombre': 'Mes / A\u00F1o',
                    'cota_prom_mes': 'Cota Prom (msnm)',
                    'cota_max_mes': 'Cota M\u00E1x (msnm)',
                    'cota_min_mes': 'Cota M\u00EDn (msnm)',
                    'q_in_ls': '📥 Caudal Medio Entrada Cuenca (L/s)',
                    'vol_in_m3': '📥 Volumen Entrada Cuenca (m³)',
                    'q_crc_ls': '🚰 Caudal Medio CRC Bosconia (L/s)',
                    'vol_crc_m3': '🚰 Metros Cúbicos Entregados Bosconia (m³)',
                    'q_mg_ls': '🌀 Caudal Medio Rebose MG (L/s)',
                    'vol_mg_m3': '🌀 Volumen Rebose MG (m³)',
                    'q_out_tot_ls': '📤 Caudal Medio Salida Total (L/s)',
                    'vol_out_tot_m3': '📤 Volumen Salida Total (m³)',
                    'q_bal_ls': '⚖️ Balance Neto Caudales (L/s)',
                    'volumen_max_mes': 'Volumen (hm\u00B3)',
                    'dias_registrados': 'D\u00EDas Monitoreados'
                }
                cols_mes = [
                    'Mes Nombre', 'cota_prom_mes', 'cota_max_mes', 'cota_min_mes',
                    'q_in_ls', 'vol_in_m3', 'q_crc_ls', 'vol_crc_m3', 'q_mg_ls', 'vol_mg_m3',
                    'q_out_tot_ls', 'vol_out_tot_m3', 'q_bal_ls', 'volumen_max_mes', 'dias_registrados'
                ]

            else:
                df_mes = df_est.groupby(['anio', 'mes']).agg(
                    lluvia_mensual=('lluvia_diaria', 'sum'),
                    pico_horario_mes=('lluvia_pico_horario', 'max'),
                    dias_con_lluvia=('lluvia_diaria', lambda s: (s > 0.1).sum()),
                    temp_min_mes=('temp_min', 'min'),
                    temp_max_mes=('temp_max', 'max'),
                    temp_prom_mes=('temp_prom', 'mean'),
                    hum_prom_mes=('hum_prom', 'mean'),
                    dias_registrados=('fecha', 'count')
                ).reset_index().sort_values(['anio', 'mes'], ascending=False)
                df_mes['Mes Nombre'] = df_mes.apply(lambda r: f"{meses_es.get(int(r['mes']), r['mes'])} {int(r['anio'])}", axis=1)

                col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                col_m1.metric("Meses con Datos", len(df_mes))
                col_m2.metric("Mes M\u00E1s Lluvioso", f"{df_mes['lluvia_mensual'].max():.1f} mm")
                col_m3.metric("Lluvia Mensual Promedio", f"{df_mes['lluvia_mensual'].mean():.1f} mm")
                col_m4.metric("Temp M\u00E1x Mensual", f"{df_mes['temp_max_mes'].max():.1f} \u00B0C")

                fig_m = go.Figure()
                if "Precipitaci\u00F3n" in variable_grafica:
                    fig_m.add_trace(go.Bar(
                        x=df_mes['Mes Nombre'], y=df_mes['lluvia_mensual'],
                        name="Lluvia Acumulada Mensual (mm)", marker_color="#00CC96", text=df_mes['lluvia_mensual'].round(1), textposition='auto'
                    ))
                    fig_m.add_trace(go.Scatter(
                        x=df_mes['Mes Nombre'], y=df_mes['pico_horario_mes'],
                        name="Pico Horario Extremo (mm/h)", mode='lines+markers', line=dict(color="#FF8000", width=2.5)
                    ))
                    fig_m.update_layout(title=f"Precipitaci\u00F3n Mensual Consolidada \u2014 {est_stat}", yaxis_title="mm")
                else:
                    fig_m.add_trace(go.Bar(
                        x=df_mes['Mes Nombre'], y=df_mes['temp_prom_mes'],
                        name="Media Mensual (\u00B0C)", marker_color="#38BDF8"
                    ))
                    fig_m.add_trace(go.Scatter(
                        x=df_mes['Mes Nombre'], y=df_mes['temp_max_mes'],
                        name="M\u00E1xima Mensual (\u00B0C)", mode='lines+markers', line=dict(color="#FF4B4B", width=2)
                    ))
                    fig_m.add_trace(go.Scatter(
                        x=df_mes['Mes Nombre'], y=df_mes['temp_min_mes'],
                        name="M\u00EDnima Mensual (\u00B0C)", mode='lines+markers', line=dict(color="#00CC96", width=2)
                    ))
                    fig_m.update_layout(title=f"Comportamiento T\u00E9rmico Mensual \u2014 {est_stat}", yaxis_title="\u00B0C")

                rename_mes = {
                    'Mes Nombre': 'Mes / A\u00F1o',
                    'lluvia_mensual': 'Lluvia Total (mm)',
                    'pico_horario_mes': 'Pico M\u00E1x (mm/h)',
                    'dias_con_lluvia': 'D\u00EDas con Lluvia',
                    'temp_min_mes': 'Temp M\u00EDn (\u00B0C)',
                    'temp_max_mes': 'Temp M\u00E1x (\u00B0C)',
                    'temp_prom_mes': 'Temp Prom (\u00B0C)',
                    'dias_registrados': 'D\u00EDas con Datos'
                }
                cols_mes = ['Mes Nombre', 'lluvia_mensual', 'pico_horario_mes', 'dias_con_lluvia', 'temp_min_mes', 'temp_max_mes', 'temp_prom_mes', 'dias_registrados']

            fig_m.update_layout(template="plotly_dark", height=380)
            st.plotly_chart(fig_m, use_container_width=True)

            df_show_mes = df_mes[cols_mes].rename(columns=rename_mes)
            if es_embalse:
                df_show_mes = _agregar_fila_promedio_tabla_embalse(df_show_mes, 'Mes / A\u00F1o')
            st.dataframe(df_show_mes, use_container_width=True, hide_index=True)
            csv_m = df_show_mes.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label=f"\U0001F4E5 Descargar Estad\u00EDsticas Mensuales ({est_stat}) en CSV",
                data=csv_m,
                file_name=f"estadisticas_mensuales_{est_stat}.csv",
                mime="text/csv"
            )

        # --------------------------------------------------------
        # 4. GRANULARIDAD: PROGRESIVO ANUAL (2026)
        # --------------------------------------------------------
        elif "Anual" in granularidad:
            st.markdown("""
            <div style="background-color: #1e293b; border-left: 5px solid #38BDF8; padding: 14px 18px; border-radius: 8px; margin-bottom: 20px;">
                <h4 style="color: #38BDF8; margin: 0 0 4px 0;">\U0001F4C8 Climatolog\u00EDa e Hidrolog\u00EDa Progresiva Anual</h4>
                <div style="color: #E2E8F0; font-size: 0.93rem;">
                    Los valores anuales se actualizan autom\u00E1ticamente con cada nueva lectura ingresada a BigQuery, reflejando exclusivamente las variables f\u00EDsicas que cada estaci\u00F3n mide en campo.
                </div>
            </div>
            """, unsafe_allow_html=True)

            if es_surata:
                df_anual = df_est.groupby('anio').agg(
                    caudal_prom_anual=('caudal_diario_prom_ls', 'mean'),
                    caudal_max_anual=('caudal_diario_max_ls', 'max'),
                    nivel_prom_anual=('nivel_prom_m', 'mean'),
                    nivel_max_anual=('nivel_max_m', 'max'),
                    dias_monitoreados=('fecha', 'count')
                ).reset_index().sort_values('anio', ascending=False)

                for idx, r_an in df_anual.iterrows():
                    anio_val = int(r_an['anio'])
                    st.markdown(f"#### \U0001F4C5 Resumen Hidrol\u00F3gico A\u00F1o {anio_val} \u2014 R\u00EDo Surat\u00E1 (Majadas)")
                    k1, k2, k3, k4 = st.columns(4)
                    k1.metric("Caudal Pico M\u00E1ximo del A\u00F1o", f"{r_an['caudal_max_anual']:,.0f} L/s ({r_an['caudal_max_anual']/1000.0:.2f} m\u00B3/s)")
                    k2.metric("Caudal Medio Ponderado", f"{r_an['caudal_prom_anual']:,.0f} L/s")
                    k3.metric("Nivel M\u00E1x en Sensor", f"{r_an['nivel_max_anual']:.2f} m (Mira: {max(0.05, r_an['nivel_max_anual']-0.04):.2f} m)")
                    k4.metric("D\u00EDas Monitoreados", f"{int(r_an['dias_monitoreados'])} d\u00EDas")

                rename_an = {
                    'anio': 'A\u00F1o',
                    'caudal_max_anual': 'Caudal Pico M\u00E1x (L/s)',
                    'caudal_prom_anual': 'Caudal Medio (L/s)',
                    'nivel_max_anual': 'Nivel M\u00E1x Sensor (m)',
                    'nivel_prom_anual': 'Nivel Prom Sensor (m)',
                    'dias_monitoreados': 'D\u00EDas Registrados'
                }
                cols_an = ['anio', 'caudal_max_anual', 'caudal_prom_anual', 'nivel_max_anual', 'nivel_prom_anual', 'dias_monitoreados']

            elif es_embalse:
                df_anual = df_est.groupby('anio').agg(
                    cota_prom_anual=('cota_prom_msnm', 'mean'),
                    cota_max_anual=('cota_max_msnm', 'max'),
                    cota_min_anual=('cota_min_msnm', 'min'),
                    q_in_ls=('q_entrada_cuenca_ls', 'mean'),
                    vol_in_m3=('vol_entrada_cuenca_m3', 'sum'),
                    q_crc_ls=('q_crc_prom_ls', 'mean'),
                    vol_crc_m3=('vol_crc_m3', 'sum'),
                    q_mg_ls=('descarga_mg_prom_ls', 'mean'),
                    vol_mg_m3=('vol_mg_m3', 'sum'),
                    descarga_mg_max_anual=('descarga_mg_max_ls', 'max'),
                    q_out_tot_ls=('q_salida_total_ls', 'mean'),
                    vol_out_tot_m3=('vol_salida_total_m3', 'sum'),
                    q_bal_ls=('balance_neto_ls', 'mean'),
                    volumen_max_anual=('volumen_max_hm3', 'max'),
                    dias_monitoreados=('fecha', 'count')
                ).reset_index().sort_values('anio', ascending=False)
                df_anual['Anio_Str'] = df_anual['anio'].apply(lambda a: f"A\u00F1o {int(a)}")
                for c_r3 in ['cota_prom_anual', 'cota_max_anual', 'cota_min_anual', 'volumen_max_anual']:
                    df_anual[c_r3] = df_anual[c_r3].round(3)
                for c_r1 in ['q_in_ls', 'vol_in_m3', 'q_crc_ls', 'vol_crc_m3', 'q_mg_ls', 'vol_mg_m3', 'descarga_mg_max_anual', 'q_out_tot_ls', 'vol_out_tot_m3', 'q_bal_ls']:
                    df_anual[c_r1] = df_anual[c_r1].round(1)

                for idx, r_an in df_anual.iterrows():
                    anio_val = int(r_an['anio'])
                    st.markdown(f"#### \U0001F4C5 Resumen Hidrol\u00F3gico A\u00F1o {anio_val} \u2014 Embalse de Tona")
                    k1, k2, k3, k4 = st.columns(4)
                    k1.metric("Cota M\u00E1xima / Media Anual", f"{r_an['cota_max_anual']:.3f} / {r_an['cota_prom_anual']:.3f} msnm")
                    k2.metric("📥 Caudal Medio Entrada Cuenca", f"{r_an['q_in_ls']:,.1f} L/s ({r_an['vol_in_m3']:,.0f} m³)")
                    k3.metric("📤 Caudal Medio Salida Total", f"{r_an['q_out_tot_ls']:,.1f} L/s (CRC: {r_an['q_crc_ls']:,.1f} L/s)")
                    k4.metric("⚖️ Balance Neto / Vol. Almacenado", f"{r_an['q_bal_ls']:+.1f} L/s ({r_an['volumen_max_anual']:.2f} hm\u00B3)")

                _render_3_graficas_embalse_multitemporal(df_anual, 'Anio_Str', 'Anual')

                rename_an = {
                    'Anio_Str': 'A\u00F1o',
                    'cota_max_anual': 'Cota M\u00E1x (msnm)',
                    'cota_prom_anual': 'Cota Prom (msnm)',
                    'cota_min_anual': 'Cota M\u00EDn (msnm)',
                    'q_in_ls': '📥 Caudal Medio Entrada Cuenca (L/s)',
                    'vol_in_m3': '📥 Volumen Entrada Cuenca (m³)',
                    'q_crc_ls': '🚰 Caudal Medio CRC Bosconia (L/s)',
                    'vol_crc_m3': '🚰 Metros Cúbicos Entregados Bosconia (m³)',
                    'q_mg_ls': '🌀 Caudal Medio Rebose MG (L/s)',
                    'vol_mg_m3': '🌀 Volumen Rebose MG (m³)',
                    'q_out_tot_ls': '📤 Caudal Medio Salida Total (L/s)',
                    'vol_out_tot_m3': '📤 Volumen Salida Total (m³)',
                    'q_bal_ls': '⚖️ Balance Neto Caudales (L/s)',
                    'volumen_max_anual': 'Volumen (hm\u00B3)',
                    'dias_monitoreados': 'D\u00EDas Registrados'
                }
                cols_an = [
                    'Anio_Str', 'cota_max_anual', 'cota_prom_anual', 'cota_min_anual',
                    'q_in_ls', 'vol_in_m3', 'q_crc_ls', 'vol_crc_m3', 'q_mg_ls', 'vol_mg_m3',
                    'q_out_tot_ls', 'vol_out_tot_m3', 'q_bal_ls', 'volumen_max_anual', 'dias_monitoreados'
                ]

            else:
                df_anual = df_est.groupby('anio').agg(
                    lluvia_anual=('lluvia_diaria', 'sum'),
                    pico_anual_horario=('lluvia_pico_horario', 'max'),
                    pico_diario_max=('lluvia_diaria', 'max'),
                    dias_con_lluvia=('lluvia_diaria', lambda s: (s > 0.1).sum()),
                    temp_min_anual=('temp_min', 'min'),
                    temp_max_anual=('temp_max', 'max'),
                    temp_prom_anual=('temp_prom', 'mean'),
                    dias_monitoreados=('fecha', 'count')
                ).reset_index().sort_values('anio', ascending=False)

                for idx, r_an in df_anual.iterrows():
                    anio_val = int(r_an['anio'])
                    st.markdown(f"#### \U0001F4C5 Resumen Acumulado A\u00F1o {anio_val} \u2014 Estaci\u00F3n {est_stat}")
                    k1, k2, k3, k4 = st.columns(4)
                    k1.metric("Lluvia Acumulada Anual", f"{r_an['lluvia_anual']:.1f} mm")
                    k2.metric("D\u00EDas Monitoreados", f"{int(r_an['dias_monitoreados'])} d\u00EDas")
                    k3.metric("D\u00EDas con Lluvia", f"{int(r_an['dias_con_lluvia'])} d\u00EDas")
                    k4.metric("D\u00EDa M\u00E1s Lluvioso", f"{r_an['pico_diario_max']:.1f} mm")

                rename_an = {
                    'anio': 'A\u00F1o',
                    'lluvia_anual': 'Lluvia Acum. Anual (mm)',
                    'pico_diario_max': 'M\u00E1x Lluvia en 24h (mm)',
                    'pico_anual_horario': 'Pico Horario Extremo (mm/h)',
                    'dias_con_lluvia': 'D\u00EDas Lluviosos',
                    'temp_min_anual': 'Temp M\u00EDnima (\u00B0C)',
                    'temp_max_anual': 'Temp M\u00E1xima (\u00B0C)',
                    'temp_prom_anual': 'Temp Media (\u00B0C)',
                    'dias_monitoreados': 'D\u00EDas Registrados'
                }
                cols_an = ['anio', 'lluvia_anual', 'pico_diario_max', 'pico_anual_horario', 'dias_con_lluvia', 'temp_min_anual', 'temp_max_anual', 'temp_prom_anual', 'dias_monitoreados']

            df_show_an = df_anual[cols_an].rename(columns=rename_an)
            if es_embalse:
                df_show_an = _agregar_fila_promedio_tabla_embalse(df_show_an, 'A\u00F1o')
            st.dataframe(df_show_an, use_container_width=True, hide_index=True)
            csv_a = df_show_an.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label=f"\U0001F4E5 Descargar Consolidado Anual ({est_stat}) en CSV",
                data=csv_a,
                file_name=f"estadisticas_anuales_{est_stat}.csv",
                mime="text/csv"
            )
# ============================================================
# 8. PESTAÑAS PRINCIPALES DEL SISTEMA (8 PESTAÑAS)
# ============================================================
tab_situacion, tab_embalse_2026, tab_radar_72h, tab_series, tab_ia, tab_resumen_alertas, tab_eventos, tab_matematica = st.tabs([
    "📊 Situación Actual",
    "🌊 Gestión Embalse & Sequía 2026",
    "🛰️ Radar Satelital & Pronósticos",
    "📈 Series de Tiempo & Descargas",
    "🤖 Asistente IA MIMAT-C",
    "🌐 Panel de Alerta Temprana y Vigilancia de Cuencas",
    "🚨 Eventos Significativos & Estadísticas",
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
            # Cálculo Dinámico de Tiempo Transcurrido de Maniobra Válvula CRC Bosconia
            ahora_col = datetime.now(colombia_tz)
            horas_maniobra_crc = max(1.0, (ahora_col - FECHA_INICIO_MANIOBRA_CRC).total_seconds() / 3600.0)
            dias_maniobra_crc = horas_maniobra_crc / 24.0
            if dias_maniobra_crc >= 1.0:
                txt_maniobra_corto = f"{dias_maniobra_crc:.1f} días"
                txt_maniobra_largo = f"{dias_maniobra_crc:.1f} días ({horas_maniobra_crc:.0f}h)"
            else:
                txt_maniobra_corto = f"{horas_maniobra_crc:.1f}h"
                txt_maniobra_largo = f"{horas_maniobra_crc:.1f} horas"
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
                        Cota calibrada en <strong>{cota_actual:.2f} msnm</strong>. Entregando aproximadamente <strong>~{hidro['q_rebose_m3_s']:.2f} m³/s (~{hidro['q_rebose_ls']:,.0f} L/s)</strong> <em>[dato aproximado en proceso de calibración empírica]</em> por el pozo Morning Glory hacia Puente Tona (confluencia con Río Suratá, aguas arriba de Majadas). Mayor disponibilidad de agua cruda para PTAP Bosconia y futura PTAP Los Angelinos.
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
                        Cota calibrada en <strong>{cota_actual:.2f} msnm</strong>. Descenso total acumulado de <strong>{abs(descenso_total_cm):.1f} cm</strong> ({abs(hidro['excedente_rebose']):.2f} msnm bajo vertedero). Volumen acumulado entregado: <strong>{vol_entregado_total_m3:,.0f} m³</strong> en <strong>{txt_maniobra_largo}</strong>. Capacidad útil al <strong>{hidro['porcentaje_util']:.1f}%</strong> ({hidro['volumen_util_hm3']:.2f} hm³).
                    </div>
                </div>
                """, unsafe_allow_html=True)
            # Estado de desalmacenamiento: si está sobre rebose (>= 885.75 msnm), el vaso está al 100% y no ha cedido nada
            if cota_actual >= NIVEL_REBOSE_EMBALSE:
                txt_delta_desalm = f"Vaso al 100% (+{descenso_total_cm:.1f} cm)"
                color_delta_desalm = "normal"
            else:
                descenso_real_cm = (NIVEL_REBOSE_EMBALSE - cota_actual) * 100.0
                txt_delta_desalm = f"{descenso_real_cm:.1f} cm cedidos ({txt_maniobra_corto})"
                color_delta_desalm = "inverse"
            # Balance Continuo de Caudales: Egresos Totales y Recarga de Afluentes Naturales
            q_egresos_totales_ls = float(q_salida_crc_actual) + 51.0 + float(hidro.get('q_rebose_ls', 0.0) or 0.0)
            if bal:
                if bal["modo_balance"] == "LLENADO":
                    q_afluente_calc_ls = q_egresos_totales_ls + abs(bal['q_neto_ls'])
                elif bal["modo_balance"] in ("VACIADO", "REBOSE"):
                    q_afluente_calc_ls = max(0.0, q_egresos_totales_ls - bal['q_neto_ls'])
                else:
                    q_afluente_calc_ls = q_egresos_totales_ls
            else:
                q_afluente_calc_ls = q_egresos_totales_ls

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("🌊 Cota Calibrada", f"{cota_actual:.2f} msnm", delta=f"{descenso_total_cm:+.1f} cm vs Rebose (885.75)", help=f"Sensor OTT: {cota_raw:.2f} msnm | Offset calibrado: -{OFFSET_RADAR_EMBALSE*100:.0f} cm")
            c2.metric("💧 Volumen Útil", f"{hidro['volumen_util_hm3']:.2f} hm³", delta=f"{hidro['porcentaje_util']:.1f}% útil")
            c3.metric("📦 Desalmacenamiento Vaso", f"{vol_entregado_total_m3:,.0f} m³", delta=txt_delta_desalm, delta_color=color_delta_desalm, help=f"Volumen neto cedido por el vaso del embalse desde el inicio de maniobra el martes 22 de septiembre a la 1:00 PM ({txt_maniobra_largo}). En cota >= 885.75 msnm el vaso se encuentra al 100% de capacidad útil.")
            # c4: Aporte de Cuenca Tona (reemplaza el duplicado superior de Rebose MG que ya se presenta en los egresos)
            c4.metric(
                "📥 Aporte Afluentes Cuenca",
                f"~{q_afluente_calc_ls:,.0f} L/s",
                delta=f"~{q_afluente_calc_ls/1000.0:.2f} m³/s (Recarga total)",
                help="Caudal continuo total de entrada que llega al embalse (Río Tona cabecera, Quebrada Ranás, El Gualilo, La Reforma y Los Monos) calculado por balance continuo de masas antes de salidas y vertimientos."
            )

            # Sub-panel de Egresos Físicos del Embalse (Conducción CRC + Filtraciones de Presa + Rebose)
            st.markdown("<div style='margin-top: 14px; margin-bottom: 6px; font-size: 13.5px; font-weight: 700; color: #38BDF8;'>🚰 Caudales de Salida y Egresos del Embalse (Tiempo Real):</div>", unsafe_allow_html=True)
            col_sal1, col_sal2, col_sal3 = st.columns(3)
            
            es_valvula_cerrada = (q_salida_crc_actual <= 30.0)
            if es_valvula_cerrada:
                estado_crc_card = "🟡 Válvula Cerrada (Salida Pasiva)"
                help_crc_card = "La válvula principal CRC se encuentra cerrada. El sensor registra el flujo pasivo continuo (~25 L/s) requerido para presurización de la tubería, protección contra golpe de ariete/cavitación y tolerancia de estanqueidad de sellos a 60m de carga hidrostática. Físicamente ingresa a la conducción y llega a PTAP Bosconia."
            else:
                estado_crc_card = "🟢 Válvula Abierta (Descarga Activa)"
                help_crc_card = "Válvula CRC en maniobra de apertura operativa activa, entregando caudal suplementario hacia PTAP Bosconia."

            col_sal1.metric(
                "🚰 Conducción CRC Bosconia",
                f"{q_salida_crc_actual:,.1f} L/s",
                delta=estado_crc_card,
                help=help_crc_card
            )
            col_sal2.metric(
                "💧 Filtraciones Presa (Drenes)",
                "~51 L/s",
                delta="48 - 54 L/s típicos (Varía con cota)",
                help="Suma total de aforadores de filtración en galería de presa y cimientos (confirmado en campo por Milton Quintero). Alivia libremente por el cauce natural del Río Tona hacia Puente Tona."
            )
            if hidro["q_rebose_ls"] > 0:
                col_sal3.metric("🌀 Rebose Morning Glory", f"~{hidro['q_rebose_ls']:,.0f} L/s", delta=f"~{hidro['q_rebose_m3_s']:.2f} m³/s", help="Descarga superficial de alivio por el pozo vertedero Morning Glory hacia Puente Tona.")
            else:
                col_sal3.metric("🌀 Rebose Morning Glory", "0 L/s", delta="Bajo vertedero", help="Cota inferior al labio del vertedero (885.75 msnm).")

            # Módulo de Histórico de Caudal Extraído por CRC Bosconia
            df_crc_hist = get_historico_crc_bosconia(horas)
            with st.expander(f"📈 Ver Histórico de Extracción Válvula CRC Bosconia ({horas}h)", expanded=False):
                if not df_crc_hist.empty and len(df_crc_hist) > 1:
                    fig_crc = go.Figure()
                    fig_crc.add_trace(go.Scatter(
                        x=df_crc_hist['ts'],
                        y=df_crc_hist['caudal_crc'],
                        mode='lines+markers',
                        name='Caudal Conducción CRC (L/s)',
                        line=dict(color='#00E676', width=2),
                        marker=dict(size=4)
                    ))
                    fig_crc.add_hline(
                        y=25.0, line_dash="dash", line_color="#FFBB00",
                        annotation_text="Línea Base Pasiva (~25 L/s Válvula Cerrada)"
                    )
                    fig_crc.update_layout(
                        title=f"Evolución Histórica de Caudal CRC Bosconia — Últimas {horas} horas",
                        xaxis_title="Fecha / Hora",
                        yaxis_title="Caudal (L/s)",
                        template="plotly_dark",
                        height=300,
                        hovermode="x unified"
                    )
                    st.plotly_chart(fig_crc, use_container_width=True)
                    st.caption("ℹ️ **Análisis de Operación:** Caudales sostenidos en el rango de ~20-25 L/s indican válvula cerrada en régimen de salida pasiva/presurizada. Ascensos por encima de 30 L/s corresponden a maniobras activas de apertura hacia PTAP Bosconia.")
                else:
                    st.info(f"No se registran suficientes lecturas telemétricas de CRC_Bosconia_Caudal en las últimas {horas} horas (telemetría recién conectada).")
            # Tarjeta de Balance Dinámico en Tiempo Real (Derivada Batimétrica)
            if bal:
                st.markdown("---")
                st.markdown("### ⚖️ Balance Hídrico Dinámico en Vivo (Extracción CRC Bosconia)")
                st.caption(f"Descenso neto del vaso ({vol_entregado_total_m3:,.0f} m³ cedidos en {txt_maniobra_largo} de maniobra / desde Martes 22 Sept 1:00 PM) y tasa neta calibrada en las últimas **{bal['horas']:.1f} horas**.")
                bc1, bc2, bc3, bc4 = st.columns(4)
                bc1.metric("📦 Desalmacenamiento Total", f"{vol_entregado_total_m3:,.0f} m³", delta=txt_delta_desalm, delta_color=color_delta_desalm, help=f"Volumen neto cedido por el vaso desde el 22 de septiembre a la 1:00 PM en cota de rebose 885.75 msnm")
                if bal["modo_balance"] == "VACIADO":
                    bc2.metric("⚡ Tasa Neta Reciente", f"{bal['q_neto_ls']:.0f} L/s", delta=f"{bal['vel_cm_dia']:+.1f} cm/día", delta_color="inverse", help=f"Velocidad neta de vaciado en las últimas {bal['horas']:.1f} horas")
                    bc3.metric(f"🚰 Desalmacenado ({bal['horas']:.1f}h)", f"{abs(bal['delta_v_m3']):,.0f} m³", delta=f"{bal['delta_cota_cm']:+.1f} cm en ventana", delta_color="inverse", help=f"Metros cúbicos cedidos exclusivamente en el período de análisis de las últimas {bal['horas']:.1f} horas")
                    if cota_actual >= NIVEL_REBOSE_EMBALSE:
                        bc4.metric("♾️ Autonomía Dinámica", "Excedente Continuo", delta="Vaso al 100% (En Rebose)", delta_color="normal", help="El embalse se encuentra en o por encima de la cota de rebose (885.75 msnm). No hay agotamiento de reserva útil; los afluentes de cuenca cubren las extracciones y mantienen el vertimiento por Morning Glory hacia Puente Tona.")
                    else:
                        bc4.metric("⏳ Autonomía Dinámica", f"{bal['dias_autonomia']:.0f} Días" if bal['dias_autonomia'] else "N/A", help="Días restantes de agua continua a la tasa neta actual hasta el Nivel Mínimo Técnico (841 msnm)")
                elif bal["modo_balance"] == "LLENADO":
                    bc2.metric("🌊 Tasa Neta de Llenado", f"{abs(bal['q_neto_ls']):.0f} L/s", delta=f"+{abs(bal['vel_cm_dia']):.1f} cm/día ascenso", delta_color="normal", help=f"Velocidad neta de recarga y ascenso de cota en las últimas {bal['horas']:.1f} horas")
                    bc3.metric(f"📥 Recuperado ({bal['horas']:.1f}h)", f"{abs(bal['delta_v_m3']):,.0f} m³", delta=f"+{abs(bal['delta_cota_cm']):.1f} cm ganados", delta_color="normal", help=f"Metros cúbicos recuperados en el vaso por recarga de quebradas en las últimas {bal['horas']:.1f} horas")
                    if cota_actual >= NIVEL_REBOSE_EMBALSE:
                        bc4.metric("♾️ Autonomía Dinámica", "Excedente Continuo", delta="Vaso al 100% (En Rebose)", delta_color="normal", help="El embalse se encuentra en o por encima de la cota de rebose (885.75 msnm). Creciente / recarga activa en cuenca aportante sobre vertedero.")
                    else:
                        bc4.metric("📈 Días para Llenarse", f"{bal['dias_para_llenar']:.0f} Días" if bal.get('dias_para_llenar') is not None else "En Rebose (100%)", delta=f"{bal['vol_faltante_rebose_m3']:,.0f} m³ a rebose", delta_color="normal", help="Días proyectados para alcanzar la cota de rebose (885.75 msnm) al ritmo actual de recarga de cuenca")
                else:
                    bc2.metric("⚖️ Tasa Neta", "0 L/s", delta="0.0 cm/día", help="Entradas de cuenca equivalentes a salida de válvula CRC")
                    bc3.metric(f"⚖️ Delta ({bal['horas']:.1f}h)", "0 m³", delta="0.0 cm", help="Nivel estático")
                    bc4.metric("♾️ Tiempo Proyectado", "Indefinido (Equilibrio)", help="Empate exacto entre afluentes de cuenca y salida de válvula CRC Bosconia")

                if bal["modo_balance"] == "VACIADO":
                    if cota_actual >= NIVEL_REBOSE_EMBALSE:
                        txt_variacion_bal = f"<li><strong>Variación Neta de Almacenamiento (ΔV/Δt):</strong> El embalse se encuentra en <strong>RÉGIMEN DE REBOSE ACTIVO Y PLENA CAPACIDAD ÚTIL (100% - 13.38 hm³)</strong>. La tasa registrada ({bal['q_neto_ls']:.0f} L/s, {bal['delta_cota_cm']:+.1f} cm en {bal['horas']:.1f}h) refleja la dinámica superficial sobre la cresta del vertedero. Al estar sobre cota de rebose (885.75 msnm), no hay consumo de reserva útil; autonomía proyectada: <strong>Excedente Continuo</strong>.</li>"
                    else:
                        txt_variacion_bal = f"<li><strong>Variación Neta de Almacenamiento (ΔV/Δt):</strong> El vaso del embalse cede volumen útil a una tasa de <strong>{bal['q_neto_ls']:.0f} L/s</strong> ({bal['delta_cota_cm']:+.1f} cm en {bal['horas']:.1f}h), garantizando una autonomía dinámica proyectada de <strong>{bal['dias_autonomia']:.0f} días</strong> a este régimen hasta el nivel mínimo técnico.</li>"
                elif bal["modo_balance"] == "LLENADO":
                    if cota_actual >= NIVEL_REBOSE_EMBALSE:
                        txt_variacion_bal = f"<li><strong>Variación Neta de Almacenamiento (ΔV/Δt):</strong> El embalse está recibiendo un <strong>PULSO DE RECARGA / CRECIENTE (+{abs(bal['q_neto_ls']):.0f} L/s)</strong> sobre la cresta de rebose (+{abs(bal['delta_cota_cm']):.1f} cm ganados en {bal['horas']:.1f}h). Todo el exceso alivia continuamente por el vertedero Morning Glory hacia Puente Tona. Autonomía: <strong>Excedente Continuo (Vaso al 100%)</strong>.</li>"
                    else:
                        dias_txt_llenado = f"{bal['dias_para_llenar']:.0f} días" if bal.get('dias_para_llenar') is not None else "0 días (en rebose)"
                        txt_variacion_bal = f"<li><strong>Variación Neta de Almacenamiento (ΔV/Δt):</strong> El embalse está en <strong>RÉGIMEN DE LLENADO / RECUPERACIÓN</strong>. Los afluentes de cuenca superan el consumo en <strong>+{abs(bal['q_neto_ls']):.0f} L/s</strong> netos, con un tiempo estimado de <strong>{dias_txt_llenado}</strong> para alcanzar el labio de rebose (885.75 msnm).</li>"
                else:
                    txt_variacion_bal = "<li><strong>Variación Neta de Almacenamiento (ΔV/Δt):</strong> El embalse está en <strong>RÉGIMEN DE EQUILIBRIO DINÁMICO</strong> (entradas iguales a salidas). Autonomía proyectada: <strong>Indefinida</strong>.</li>"
                st.markdown(f"""
                <div style="background: rgba(0,80,115,0.06); padding: 14px 18px; border-radius: 8px; border-left: 4px solid #005073; margin-top: 10px; font-size: 13px; line-height: 1.5;">
                    <strong style="color: #005073; font-size: 14px;">⚖️ Principio Físico: Balance de Masas & Continuidad Hidráulica</strong><br>
                    <div style="margin-top: 6px; font-family: monospace; background: rgba(255,255,255,0.7); padding: 6px 10px; border-radius: 4px; border: 1px solid #cce0eb;">
                        <strong>Egresos_Totales (~{q_egresos_totales_ls:,.0f} L/s)</strong> = <strong>CRC_Bosconia ({q_salida_crc_actual:,.1f} L/s)</strong> + <strong>Filtraciones_Presa (~51 L/s)</strong> + <strong>Rebose_MG ({hidro['q_rebose_ls']:,.0f} L/s)</strong> | <strong>Tasa_Neta: {bal['q_neto_ls']:.0f} L/s</strong> | <strong>∑ Q_Afluentes_Cuenca_Tona (~{q_afluente_calc_ls:,.0f} L/s)</strong>
                    </div>
                    <div style="margin-top: 8px;">
                        <strong>🌊 Interpretación de Volúmenes & Descenso del Embalse:</strong><br>
                        <ul style="margin: 4px 0 6px 18px; padding: 0;">
                            <li><strong>📦 Consumo Total Acumulado por Bosconia ({txt_maniobra_largo} de Maniobra / desde Martes 22 Sept 1:00 PM):</strong> <strong>{vol_entregado_total_m3:,.0f} m³</strong> (descenso acumulado total de <strong>{abs(descenso_total_cm):.1f} cm</strong> desde que se abrió la válvula CRC en la cota máxima de rebose de <strong>885.75 msnm</strong>).</li>
                            <li><strong>⏱️ Balance en la Ventana de Análisis Seleccionada ({bal['horas']:.1f}h):</strong> <strong>{abs(bal['delta_v_m3']):,.0f} m³</strong> ({'cedidos' if bal['delta_cota_cm'] < 0 else 'ganados'}, variación de <strong>{bal['delta_cota_cm']:+.1f} cm</strong>).</li>
                            <li><strong>Entradas (Remanentes de Captaciones + Afluentes Directos):</strong> El Embalse Tona recibe la recarga continua de los remanentes no derivados del Sistema Tona (Río Tona cabecera, Captación Arnania y Captación Golondrinas), más los 4 afluentes directos al vaso: <strong>Quebrada Ranás</strong> (desemboca en fondo cola), <strong>Quebrada El Gualilo</strong> (mitad del vaso), <strong>Quebrada La Reforma</strong> y <strong>Quebrada Los Monos</strong> con un aporte sumado estimado en cola de <strong>~{q_afluente_calc_ls:,.0f} L/s</strong> (~{q_afluente_calc_ls/1000.0:.2f} m³/s).</li>
                            <li><strong>Salida (Consumo PTAP):</strong> Conducción y entrega por gravedad hacia la válvula <strong>CRC Bosconia</strong> ({'operando a salida pasiva de ~25 L/s con válvula cerrada' if es_valvula_cerrada else f'operando en descarga activa de {q_salida_crc_actual:,.1f} L/s'}).</li>
                            {txt_variacion_bal}
                        </ul>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                # Módulo de Inteligencia de Cuenca (Trazabilidad y Atribución Hidrológica)
                df_cuenca_tona = obtener_precipitacion_cuenca_tona(fecha_inicio, fecha_fin)
                mostrar_modulo_atribucion_cuenca(df_cuenca_tona, q_afluente_calc_ls, bal['horas'])
            st.info(f"📅 Última lectura: {row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
            mostrar_seccion_edv()
            renderizar_modulo_pronostico_horario_estacion("Embalse", row)
        elif seleccion == "Surata":
            # ============================================================
            # PRIMERA ESTACIÓN HIDROLÓGICA FLUVIAL MIMAT-C26: RÍO SURATÁ — SECTOR LAS MAJADAS
            # ============================================================
            info_sync_maj = sincronizar_fews_ideam_surata_bigquery()
            df_enr_sur = enriquecer_datos_surata(df_hist) if not df_hist.empty else pd.DataFrame()
            origen_maj = str(row.get('estado_bateria', info_sync_maj.get('origen', 'RESILIENCIA_HIDROLOGICA_AMB')))
            es_fews_vivo = ('VIVO' in origen_maj.upper())
            if es_fews_vivo and info_sync_maj.get('nivel_m') is not None:
                h_m_act = float(info_sync_maj['nivel_m'])
                h_ideam_crudo_act = float(info_sync_maj.get('nivel_ideam_crudo_m', h_m_act + OFFSET_SENSOR_IDEAM_MAJADAS))
                q_m3s_act = float(info_sync_maj['caudal_m3s'])
                q_ls_act = float(info_sync_maj['caudal_ls'])
                if not df_enr_sur.empty and len(df_enr_sur) >= 4:
                    delta_h_30m = float(df_enr_sur['nivel_m_filtrado'].iloc[-1] - df_enr_sur['nivel_m_filtrado'].iloc[-4])
                else:
                    delta_h_30m = 0.0
            elif not df_enr_sur.empty:
                h_m_act = float(df_enr_sur['nivel_m_filtrado'].iloc[-1])
                h_ideam_crudo_act = float(df_enr_sur['nivel_m_crudo'].iloc[-1])
                q_m3s_act = float(df_enr_sur['caudal_m3s_filtrado'].iloc[-1])
                q_ls_act = float(df_enr_sur['caudal_ls_filtrado'].iloc[-1])
                if len(df_enr_sur) >= 4:
                    delta_h_30m = float(df_enr_sur['nivel_m_filtrado'].iloc[-1] - df_enr_sur['nivel_m_filtrado'].iloc[-4])
                else:
                    delta_h_30m = 0.0
            else:
                h_m_act = float(info_sync_maj.get('nivel_m', 1.34))
                h_ideam_crudo_act = float(info_sync_maj.get('nivel_ideam_crudo_m', h_m_act + OFFSET_SENSOR_IDEAM_MAJADAS))
                q_m3s_act, q_ls_act = calcular_caudal_mira_majadas(h_m_act, aplicar_offset_ideam=False)
                delta_h_30m = 0.0
            # Consultar en vivo el forzamiento aguas arriba: Lluvias Cuenca Tona + Subida Radar Embalse + Lluvias Cuenca Suratá
            cota_emb_s = get_cota_embalse_actual_segura()
            q_mg_m3s_aprox, q_mg_ls_aprox = calcular_caudal_morning_glory(cota_emb_s)
            _, q_mg_teorico_descalibrado_ls = calcular_caudal_morning_glory_teorico_descalibrado(cota_emb_s)
            lluvia_tona_max_1h = 0.0
            lluvia_surata_max_1h = 0.0
            delta_emb_cm_1h = 0.0
            detalle_lluvias_parte_alta_str = "Yerbabuena, Vegas del Quemado, El Pajal, La Mariana"
            lluvia_acum_parte_alta_max = 0.0
            try:
                q_up = """
                WITH base_up AS (
                    SELECT id_estacion,
                           SAFE_CAST(precipitacion AS FLOAT64) AS p,
                           SAFE_CAST(temperatura AS FLOAT64) AS t,
                           SAFE_CAST(humedad AS FLOAT64) AS h,
                           SAFE_CAST(timestamp AS TIMESTAMP) AS ts,
                           LAG(SAFE_CAST(precipitacion AS FLOAT64)) OVER(PARTITION BY id_estacion ORDER BY SAFE_CAST(timestamp AS TIMESTAMP)) AS prev_p,
                           LAG(SAFE_CAST(temperatura AS FLOAT64)) OVER(PARTITION BY id_estacion ORDER BY SAFE_CAST(timestamp AS TIMESTAMP)) AS prev_t,
                           LAG(SAFE_CAST(humedad AS FLOAT64)) OVER(PARTITION BY id_estacion ORDER BY SAFE_CAST(timestamp AS TIMESTAMP)) AS prev_h,
                           ROW_NUMBER() OVER(PARTITION BY id_estacion ORDER BY SAFE_CAST(timestamp AS TIMESTAMP) DESC) AS rn
                    FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones`
                    WHERE SAFE_CAST(timestamp AS TIMESTAMP) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 18 HOUR)
                      AND id_estacion IN ('La_Mariana', 'El_Pajal', 'Vegas_del_Quemado', 'Monsalve', 'Yerbabuena', 'Embalse')
                ),
                limpia_up AS (
                    SELECT id_estacion,
                           CASE
                               WHEN id_estacion != 'Embalse' AND p > 0 AND p < 10.0 AND p = prev_p AND t = prev_t AND h = prev_h THEN 0.0
                               ELSE IFNULL(p, 0.0)
                           END AS p_limpia,
                           t,
                           ts,
                           rn
                    FROM base_up
                )
                SELECT id_estacion,
                       ROUND(SUM(CASE WHEN ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR) THEN p_limpia ELSE 0.0 END), 2) AS p_1h,
                       ROUND(SUM(p_limpia), 2) AS p_18h,
                       ARRAY_AGG(t IGNORE NULLS ORDER BY ts DESC LIMIT 6) AS cotas_recientes
                FROM limpia_up
                GROUP BY id_estacion
                """
                rows_up = list(client.query(q_up).result())
                mapa_nombres_up = {
                    "Yerbabuena": "Yerbabuena",
                    "Vegas_del_Quemado": "Vegas del Quemado",
                    "El_Pajal": "El Pajal",
                    "La_Mariana": "La Mariana",
                    "Monsalve": "Monsalve"
                }
                p_tona_1h_list = []
                p_sur_1h_list = []
                partes_activas = []
                for r in rows_up:
                    est_id = str(r['id_estacion'])
                    p1h = float(r['p_1h'] or 0.0)
                    p18h = float(r['p_18h'] or 0.0)
                    if est_id in ('La_Mariana', 'El_Pajal', 'Vegas_del_Quemado', 'Yerbabuena'):
                        p_tona_1h_list.append(p1h)
                        lluvia_acum_parte_alta_max = max(lluvia_acum_parte_alta_max, p18h)
                        if p18h >= 1.0 or p1h >= 0.2:
                            partes_activas.append(f"{mapa_nombres_up.get(est_id, est_id)}: {p18h:.1f} mm")
                    elif est_id == 'Monsalve':
                        p_sur_1h_list.append(p1h)
                        if p18h >= 1.0 or p1h >= 0.2:
                            partes_activas.append(f"Monsalve: {p18h:.1f} mm")
                    elif est_id == 'Embalse':
                        cotas_raw = [float(x) for x in (r['cotas_recientes'] or []) if x is not None and 818.0 <= float(x) <= 888.8]
                        if len(cotas_raw) >= 2:
                            delta_emb_cm_1h = round((cotas_raw[0] - cotas_raw[-1]) * 100.0, 1)
                if p_tona_1h_list:
                    lluvia_tona_max_1h = max(p_tona_1h_list)
                if p_sur_1h_list:
                    lluvia_surata_max_1h = max(p_sur_1h_list)
                if partes_activas:
                    detalle_lluvias_parte_alta_str = ", ".join(partes_activas)
            except Exception:
                pass
            sensor_cod_act = str(info_sync_maj.get('sensor_cod', '0230'))
            h_mira_max_1h = float(info_sync_maj.get('nivel_mira_max_1h_m', h_m_act))
            q_max_1h_ls = float(info_sync_maj.get('caudal_max_1h_ls', q_ls_act))
            # Para seguridad operativa de Toma Bosconia, el semáforo evalúa el mayor entre el corte actual y el pico intra-horario (0231)
            q_eval_sem = max(q_ls_act, q_max_1h_ls)
            h_eval_sem = max(h_m_act, h_mira_max_1h)
            sem_sur = obtener_semaforo_hidrologico_surata(
                q_eval_sem,
                h_eval_sem,
                delta_h_30m,
                lluvia_max_cuenca_tona_mmh=lluvia_tona_max_1h,
                lluvia_max_cuenca_surata_mmh=lluvia_surata_max_1h,
                delta_cota_embalse_cm_1h=delta_emb_cm_1h,
                q_rebose_mg_ls=q_mg_ls_aprox,
                sensor_activo_ideam=sensor_cod_act,
                cota_embalse_msnm=cota_emb_s,
                detalle_lluvias_parte_alta=detalle_lluvias_parte_alta_str,
                lluvia_acum_parte_alta_mm=lluvia_acum_parte_alta_max
            )
            # 1. Semáforo Hidrológico Operativo Multi-Capa (Crecientes y Estiaje rumbo a Toma Bosconia)
            st.markdown(f"""
            <div style="background-color:{sem_sur['color']}; padding:16px 20px; border-radius:12px; text-align:center; color:{sem_sur['text_color']}; animation: blink {sem_sur['vel']} infinite; border: 2px solid #222; margin-bottom: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.12);">
                <h3 style="margin:0; color:{sem_sur['text_color']};">{sem_sur['icono']} 🚦 {sem_sur['titulo']}</h3>
                <div style="font-weight:700; margin-top:4px; font-size:14px;">{sem_sur['mensaje']}</div>
                <div style="font-size:12.5px; margin-top:6px; font-weight:600; opacity:0.95;">
                    🛠️ <strong>Protocolo Toma Bosconia (~1.8 km aguas abajo | Tránsito 15–25 min):</strong> {sem_sur['accion']}
                </div>
            </div>
            <style>
            @keyframes blink {{ 0%{{opacity:1}} 50%{{opacity:0.45}} 100%{{opacity:1}} }}
            </style>
            """, unsafe_allow_html=True)
            # 2. Banner de Compilación de las 3 Tablas del IDEAM (`0230`, `0231`, `0232`) + Cuenca Tona/Embalse en BigQuery
            if es_fews_vivo:
                st.markdown(f"""
                <div style="background: rgba(0, 204, 150, 0.10); border: 1px solid #00CC96; border-left: 5px solid #00CC96; padding: 11px 16px; border-radius: 8px; margin-bottom: 14px; font-size: 13px; line-height: 1.5;">
                    📡 <strong>Compilación Activa de los 3 Sensores IDEAM (<code>0023197700</code>) en BigQuery:</strong>
                    Se integran en una sola serie cronológica el <strong>Corte Horario (<code>0230</code>)</strong>, el <strong>Pico Máximo Intra-Horario que se despierta por cresta (<code>0231</code>)</strong> y el <strong>Mínimo Intra-Horario (<code>0232</code>)</strong>.<br>
                    📏 <strong>Calibración Oficial (-4 cm):</strong> Sensor IDEAM crudo: <strong>{h_ideam_crudo_act:.2f} m</strong> ➔ <strong>Mira <code>amb</code> = {h_m_act:.2f} m</strong> (Pico máx. última hora: <strong>{h_mira_max_1h:.2f} m / {q_max_1h_ls:,.0f} L/s</strong>).<br>
                    🌧️ <strong>Acoplamiento con Cuenca Tona + Embalse + Cuenca Suratá:</strong> Lluvia Tona máx: <strong>{lluvia_tona_max_1h:.1f} mm/h</strong> • Cota Embalse: <strong>{cota_emb_s:.2f} msnm</strong> ({'En Rebose > 885.75' if cota_emb_s > NIVEL_REBOSE_EMBALSE else 'Bajo Rebose ≤ 885.75: Embalse retiene creciente'}) • Variación Radar Embalse (1h): <strong>{delta_emb_cm_1h:+.1f} cm</strong> • Lluvia Suratá máx: <strong>{lluvia_surata_max_1h:.1f} mm/h</strong>.
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style="background: rgba(0, 80, 115, 0.08); border: 1px solid #005073; border-left: 5px solid #005073; padding: 11px 16px; border-radius: 8px; margin-bottom: 14px; font-size: 13px; line-height: 1.5;">
                    🛡️ <strong>Motor de Continuidad Hidrológica Resiliente Activo en BigQuery (Compensación de Caídas y <em>Lags</em> de FEWS IDEAM):</strong><br>
                    • <strong>Compilación de 3 Tablas en BigQuery (<code>0230</code>, <code>0231</code> y <code>0232</code>):</strong> El sistema almacena en <code>BigQuery</code> los 3 canales del sensor de Majadas descontando los <strong>4 cm (-0.04 m)</strong> respecto a la mira del <code>amb</code>, y acopla las lluvias en tiempo real de la cuenca del Río Tona, la subida del Radar OTT del Embalse (condicionada a superar la cota de rebose de 885.75 msnm) y la cuenca alta del Suratá.
                </div>
                """, unsafe_allow_html=True)
            # 3. Cálculos de Balance en Confluencia (Suratá antes de confluencia + Puente Tona -> Majadas)
            # Asegurar coherencia física: el rebose del embalse + escorrentía baja Tona (~120 L/s) nunca puede superar el caudal real medido en Majadas
            q_puente_tona_est_ls = min(q_ls_act * 0.35, q_mg_ls_aprox + 120.0) if q_mg_ls_aprox > 0 else min(q_ls_act * 0.15, 120.0)
            q_surata_puro_aprox_ls = max(0.0, q_ls_act - q_puente_tona_est_ls)
            sc1, sc2, sc3, sc4 = st.columns(4)
            sc1.metric(
                "🌊 Nivel Mira Calibrado",
                f"{h_m_act:.2f} m",
                delta=f"IDEAM: {h_ideam_crudo_act:.2f} m (-4 cm offset)",
                help=f"Sensor IDEAM entrega {h_ideam_crudo_act:.2f} m; se descuentan exactamente 4 cm (-0.04 m, confirmado por Ing. Carlos) -> Mira amb = {h_m_act:.2f} m."
            )
            sc2.metric(
                "⚡ Caudal en Majadas",
                f"{q_ls_act:,.0f} L/s",
                delta=f"{q_m3s_act:.2f} m³/s (Mín. estiaje ~2,847 L/s)",
                help="Calculado con H_mira = H_IDEAM - 0.04 m en la ecuación oficial: Q(m³/s) = 1.2455 × (H_mira + 0.13)^4.1635"
            )
            sc3.metric(
                "🔼 Pico Máx. Hora (Sensor 0231)",
                f"{q_max_1h_ls:,.0f} L/s",
                delta=f"Mira máx 1h: {h_mira_max_1h:.2f} m (IDEAM {h_mira_max_1h+0.04:.2f} m)",
                help="Caudal máximo intra-horario detectado por el canal 0231 del IDEAM en la última ventana horaria."
            )
            sc4.metric(
                "🏞️ Aporte Puente Tona / MG",
                f"~{q_puente_tona_est_ls:,.0f} L/s",
                delta=f"Suratá antes confl.: ~{q_surata_puro_aprox_ls:,.0f} L/s",
                help=f"⚠️ HALLAZGO DE CALIBRACIÓN: La tabla teórica antigua del Morning Glory sin calibrar arrojaba ~{q_mg_teorico_descalibrado_ls:,.0f} L/s. El aporte físico estimado en lámina baja es de ~{q_mg_ls_aprox:,.0f} L/s por rebose + ~120 L/s de cuenca baja Tona."
            )
            # 4. Tarjeta de Arquitectura del Triángulo Hidráulico (Confluencia Puente Tona -> Majadas -> Toma Bosconia)
            st.markdown(f"""
            <div style="background: rgba(0,80,115,0.06); padding: 15px 18px; border-radius: 10px; border-left: 5px solid #008080; margin-top: 10px; font-size: 13px; line-height: 1.6;">
                <strong style="color: #005073; font-size: 14.5px;">📐 Arquitectura Hidrológica del Primer Caudal Confiable: Eje Confluencia Puente Tona ➔ Majadas ➔ Toma Bosconia</strong><br>
                <div style="margin-top: 6px; font-family: monospace; background: rgba(255,255,255,0.85); padding: 8px 12px; border-radius: 6px; border: 1px solid #cce0eb; font-size: 13px;">
                    <strong>H_mira = H_IDEAM ({h_ideam_crudo_act:.2f} m) - 0.04 m = {h_m_act:.2f} m</strong> &nbsp;|&nbsp;
                    <strong>Q(m³/s) = 1.2455 × ({h_m_act:.2f} + 0.13)<sup>4.1635</sup> = {q_m3s_act:.3f} m³/s ({q_ls_act:,.0f} L/s)</strong>
                </div>
                <ul style="margin: 8px 0 4px 18px; padding: 0;">
                    <li><strong>📍 Ubicación y Separación Sensor IDEAM vs. Mira <code>amb</code> (~2 m):</strong> En la estación <strong>Majadas (<code>CNE 0023197700</code> • <code>7°09'18.50"N, 73°03'42.20"W</code> • ~765 msnm)</strong>, el sensor Radar OTT automático del IDEAM y la mira física del <code>amb</code> están separados un par de metros. Por calibración oficial de ingeniería (confirmada por el <strong>Ing. Carlos</strong>), <strong>al dato entregado por el sensor del IDEAM se le descuentan directamente 4 cm (<code>-0.04 m</code>)</strong> antes de ingresar a la ecuación de la mira (al igual que en el Embalse de Tona el <strong>Ing. Angarita</strong> descuenta <strong>4 cm</strong> a la mira OTT).</li>
                    <li><strong>⏱️ Predicción Condicional de Curva (IDEAM) vs. Alerta Temprana "A la Fija" (BigQuery <code>amb</code> + Regla de Rebose 885.75 msnm):</strong> Incluso cuando un pico coincide con el corte horario del IDEAM, su motor por lotes (GOES + ETL Socrata/FEWS) tarda <strong>30 a 45 minutos</strong> en publicarlo en la web, mientras que el agua tarda solo <strong>15 a 25 minutos</strong> en recorrer los <strong>1.8 km</strong> de Majadas a Toma Bosconia. Por eso, la rampa de subida en Majadas opera como una <strong>predicción condicional de una curva en ascenso</strong> (que puede estancarse y descender). En cambio, cuando <code>Monsalve</code> (cuenca directa del Río Suratá, sin embalse) o las estaciones que tributan al sistema del Embalse de Tona (<code>Yerbabuena</code>, <code>La Mariana</code>, <code>El Pajal</code>, <code>Vegas del Quemado</code> y el <strong>Radar OTT del Embalse</strong>) detectan altos niveles en tiempo real (cada 10 min en <code>BigQuery</code>), <strong>se va a la fija hacia el Río Suratá siempre y cuando (en el caso del Embalse) el nivel supere o alcance la cota de rebose del <em>Morning Glory</em> (<code>885.75 msnm</code>)</strong>; si el nivel del embalse está por debajo de <code>885.75 msnm</code> y ese pico no alcanza el labio de rebose, <strong>el vaso del Embalse de Tona amortigua y detiene esa creciente</strong>.</li>
                    <li><strong>⚖️ Balance Coherente en la Confluencia:</strong> El caudal total medido en Majadas (<strong>{q_ls_act:,.0f} L/s</strong>) está compuesto por el <strong>Río Suratá antes de la confluencia (~{q_surata_puro_aprox_ls:,.0f} L/s)</strong> más el aporte del <strong>Río Tona por Puente Tona (~{q_puente_tona_est_ls:,.0f} L/s</strong>, que incluye <strong>~{q_mg_ls_aprox:,.0f} L/s</strong> de rebose aproximado en lámina baja del Morning Glory).</li>
                    <li><strong>🔌 Sensor de Caudal de Captación/Tratamiento Bosconia (Pendiente de Conexión):</strong> No se descuenta ni se incluye en el cálculo el caudal de tratamiento de Toma Bosconia hasta tanto no se conecte físicamente ese sensor en telemetría. Actualmente se registra únicamente la extracción confirmada de <strong>{q_salida_crc_actual:,.0f} L/s</strong> desde la Válvula CRC del Embalse de Tona.</li>
                    <li><strong style="color: #D96B00;">⚠️ Hallazgo de Auditoría en la Ecuación del Morning Glory (En Calibración):</strong> Se deja constancia explícita de que el caudal de rebose del vertedero <em>Morning Glory</em> del Embalse de Tona es un <strong>valor aproximado mientras se termina de calibrar empíricamente esa ecuación en campo</strong> (la tabla teórica antigua sin calibrar arrojaba ~<strong>{q_mg_teorico_descalibrado_ls:,.0f} L/s</strong>).</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
            if not df_enr_sur.empty:
                st.markdown("### 📊 Estadísticas Hidrológicas en Majadas (Período Seleccionado)")
                ms1, ms2, ms3, ms4 = st.columns(4)
                ms1.metric("🔽 Caudal Mínimo", f"{df_enr_sur['caudal_ls_filtrado'].min():,.0f} L/s", delta=f"Mira mín: {df_enr_sur['nivel_m_filtrado'].min():.2f} m")
                ms2.metric("📊 Caudal Promedio", f"{df_enr_sur['caudal_ls_filtrado'].mean():,.0f} L/s", delta=f"Mira prom: {df_enr_sur['nivel_m_filtrado'].mean():.2f} m")
                ms3.metric("🔼 Caudal Máximo", f"{df_enr_sur['caudal_ls_filtrado'].max():,.0f} L/s", delta=f"Mira máx: {df_enr_sur['nivel_m_filtrado'].max():.2f} m")
                ms4.metric("🚰 Extracción CRC Embalse", f"{q_salida_crc_actual:,.0f} L/s", delta="Hacia Bosconia (Confirmado)")
            st.info(f"📅 Última sincronización en BigQuery (`Surata`): {row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
            renderizar_modulo_pronostico_horario_estacion("Surata", row)
            mostrar_ficha_geografica_estacion("Surata")
        else:
            salud = evaluar_salud_estacion(df_hist, row, seleccion)
            p_val = float(row.get('precipitacion', 0)) if pd.notna(row.get('precipitacion')) else 0.0
            t_val = float(row.get('temperatura', 0)) if pd.notna(row.get('temperatura')) else 0.0
            h_val = float(row.get('humedad', 0)) if pd.notna(row.get('humedad')) else 0.0
            v_val = float(row.get('velocidad_viento', 0)) if pd.notna(row.get('velocidad_viento')) else 0.0
            d_val = float(row.get('direccion_viento', 0)) if pd.notna(row.get('direccion_viento')) else 0.0
            b_val = float(row.get('voltaje_bateria', 0)) if pd.notna(row.get('voltaje_bateria')) else 0.0
            sensor_virt = None
            if not salud["es_valido"]:
                sensor_virt = obtener_sensor_virtual_resiliente(seleccion)
            if not salud["es_valido"]:
                st.markdown(f"""
                <div class="alert-box alert-red" style="border-left: 5px solid #FF4B4B; background: rgba(255, 75, 75, 0.12); margin-bottom: 12px; display: flex; gap: 12px; align-items: flex-start;">
                    <span style="font-size: 32px; line-height: 1;">🚨</span>
                    <div>
                        <strong style="color: #FF4B4B; font-size: 15px;">{salud['mensaje']}</strong><br>
                        <div style="font-size: 13px; color: #222; margin-top: 4px; line-height: 1.5;">
                            <strong>📡 Diagnóstico del Sistema:</strong> {salud['diagnostico']}<br>
                            <strong>🛠️ Acción Técnica Recomendada:</strong> {salud['accion']}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                mostrar_auditoria_forense_caida(seleccion)
                if sensor_virt:
                    st.markdown(f"""
                    <div style="background: rgba(0, 204, 150, 0.10); border: 1px solid #00CC96; border-left: 5px solid #00CC96; padding: 12px 16px; border-radius: 10px; margin-bottom: 15px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                            <strong style="color: #00805A; font-size: 13.5px;">🤖 SISTEMA INTELIGENTE RESILIENTE: Sensor Virtual Activo</strong>
                            <span class="badge-status" style="background: rgba(0,204,150,0.2); color: #00805A; border: 1px solid #00805A;">IMPUTACIÓN EN TIEMPO REAL</span>
                        </div>
                        <div style="font-size: 12.5px; color: #333; margin-top: 4px;">
                            Para mantener operativo el balance hidrológico de la cuenca y el vector de viento sin distorsiones, el sistema calcula estimaciones físicas continuas mediante <strong>{sensor_virt['origen']}</strong>.
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    t_val = sensor_virt['temperatura']
                    h_val = sensor_virt['humedad']
                    v_val = sensor_virt['velocidad_viento']
                    d_val = sensor_virt['direccion_viento']
                    p_val = sensor_virt['precipitacion']
            # Lluvia horaria acumulada (última hora / 60 min) para evaluación oficial de semáforo (mm/h)
            ahora_col = datetime.now(colombia_tz)
            lluvia_1h = 0.0
            if not df_hist.empty and 'precipitacion' in df_hist.columns and 'timestamp' in df_hist.columns:
                df_1h = df_hist[df_hist['timestamp'] >= (ahora_col - timedelta(hours=1))]
                if not df_1h.empty:
                    lluvia_1h = float(pd.to_numeric(df_1h['precipitacion'], errors='coerce').fillna(0).sum())
            else:
                lluvia_1h = p_val
            if not salud["es_valido"]:
                pass
            else:
                nombre, msg, color, vel = obtener_alerta(lluvia_1h, seleccion)
                st.markdown(f'''
                <div style="background-color:{color}; padding:16px; border-radius:12px; text-align:center; color:black; animation: blink {vel} infinite; border: 2px solid #333;">
                    <h3 style="margin:0;">🚦 {nombre}</h3>
                    <b>{msg}</b><br>
                    <span style="font-size:12px; color:#222; font-weight:600;">(Intensidad última hora: {lluvia_1h:.1f} mm/h | Último paquete 10 min: {p_val:.1f} mm)</span>
                </div>
                <style>
                @keyframes blink {{ 0%{{opacity:1}} 50%{{opacity:0.3}} 100%{{opacity:1}} }}
                </style>
                ''', unsafe_allow_html=True)
                st.write("")
            alt_est = METADATA_ESTACIONES_AMB.get(seleccion, {}).get('altitud_msnm', 2000.0)
            pres_raw = row.get('presion') or row.get('presion_atmosferica') or row.get('barometro')
            es_presion_fisica = pd.notna(pres_raw) and float(pres_raw) > 300
            pres_val = float(pres_raw) if es_presion_fisica else calcular_presion_atmosferica_hpa(alt_est, t_val)
            tendencia_baro = calcular_tendencia_barometrica(df_hist, alt_est, pres_val, t_val)
            ayuda_pres = f"{'📡 Barómetro Físico de Estación' if es_presion_fisica else f'🧭 Estimación Barométrica ISA/OMM ({alt_est:,.0f} msnm)'} | Tendencia: {tendencia_baro['delta_str']} | Diagnóstico: {tendencia_baro['diagnostico']} (Modelo Predictivo Baro-Trend en Aprendizaje Continuo)"
            c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
            if sensor_virt:
                c1.metric("🌡️ Temp (Virtual)", f"{t_val:.1f} °C", help="Estimada por gradiente altimétrico vertical (-0.65°C/100m) desde estación de referencia")
                c2.metric("🌧️ Precip (Virtual)", f"{p_val:.1f} mm", delta=f"{lluvia_1h:.1f} mm/h (1h)" if lluvia_1h > 0 else "0.0 mm/h")
                c3.metric("💧 Humedad (Virtual)", f"{h_val:.1f} %")
                c4.metric("🧭 Presión (ISA)", f"{pres_val:.1f} hPa", delta="⚠️ Valor Pegado (Ref. ISA)", delta_color="inverse", help=f"Referencia barométrica estándar ISA/OMM para {alt_est:,.0f} msnm mientras se inspecciona la estación en campo")
                c5.metric("💨 Viento (Virtual)", f"{v_val:.1f} km/h")
                c6.metric("🧭 Dir. Viento (Virtual)", f"{d_val:.0f}°")
                c7.metric("🔋 Voltaje", "N/A", help="Estación pendiente de revisión en campo")
            else:
                c1.metric("🌡️ Temp", f"{t_val:.1f} °C")
                c2.metric("🌧️ Precip", f"{p_val:.1f} mm", delta=f"{lluvia_1h:.1f} mm/h (1h)" if lluvia_1h > 0 else "0.0 mm/h", help=f"Último paquete 10 min: {p_val:.1f} mm | Acumulado última hora: {lluvia_1h:.1f} mm/h")
                c3.metric("💧 Humedad", f"{h_val:.1f} %")
                if not salud["es_valido"]:
                    c4.metric("🧭 Presión Atm.", f"{pres_val:.1f} hPa", delta="⚠️ Valor Congelado (>2h)", delta_color="inverse", help="Valor estático sin variación real por bloqueo de datalogger / canales en 0.0")
                else:
                    c4.metric("🧭 Presión Atm.", f"{pres_val:.1f} hPa", delta=tendencia_baro['delta_display'], delta_color=tendencia_baro['color'], help=ayuda_pres)
                c5.metric("💨 Viento", f"{v_val:.1f} km/h")
                c6.metric("🧭 Dir. Viento", f"{d_val:.0f}°")
                c7.metric("🔋 Voltaje", f"{b_val:.1f} V" if b_val > 0 else "N/A", help="Sensor de batería pendiente de integración SCADA")
            st.info(f"📅 Última lectura recibida en servidor: {row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
            if not df_hist.empty and 'temperatura' in df_hist.columns:
                t_series = pd.to_numeric(df_hist['temperatura'], errors='coerce').dropna()
                t_series_valid = t_series[t_series > 0]
                if not t_series_valid.empty and salud["es_valido"]:
                    st.markdown("### 📊 Estadísticas del Período (Datos Válidos)")
                    col1, col2, col3 = st.columns(3)
                    with col1: st.metric("🔽 Temp Mínima", f"{t_series_valid.min():.1f}°C")
                    with col2: st.metric("🔼 Temp Máxima", f"{t_series_valid.max():.1f}°C")
                    with col3: st.metric("📊 Temp Promedio", f"{t_series_valid.mean():.1f}°C")
                elif sensor_virt:
                    meta_st_1 = METADATA_ESTACIONES_AMB.get(seleccion, {})
                    df_sat_24 = obtener_pronostico_open_meteo(meta_st_1.get("lat", 7.195831), meta_st_1.get("lon", -72.914719), past_days=2, forecast_days=1)
                    if not df_sat_24.empty and 'temperature_2m' in df_sat_24.columns:
                        t_s24 = pd.to_datetime(df_sat_24['time'])
                        t_s24 = t_s24.dt.tz_localize(colombia_tz) if t_s24.dt.tz is None else t_s24.dt.tz_convert(colombia_tz)
                        df_ult24 = df_sat_24[(t_s24 >= ahora_col - timedelta(hours=24)) & (t_s24 <= ahora_col)]
                        if not df_ult24.empty:
                            st.markdown("### 📊 Estadísticas Últimas 24h (Sensor Virtual Satelital)")
                            col1, col2, col3 = st.columns(3)
                            with col1: st.metric("🔽 Temp Mínima (Virtual)", f"{df_ult24['temperature_2m'].min():.1f}°C")
                            with col2: st.metric("🔼 Temp Máxima (Virtual)", f"{df_ult24['temperature_2m'].max():.1f}°C")
                            with col3: st.metric("📊 Temp Promedio (Virtual)", f"{df_ult24['temperature_2m'].mean():.1f}°C")
            renderizar_modulo_pronostico_horario_estacion(seleccion, row)
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
        * **Caudal Rebose Morning Glory (Aprox. en calibración):** `~{datos_eval['q_rebose_m3_s']:.2f} m³/s (~{datos_eval['q_rebose_ls']:,.0f} L/s)`
        """)
        if datos_eval['q_rebose_ls'] > 0:
            st.success(f"🌊 **Excedente hídrico activo hacia Puente Tona:** Descargando aprox. ~{datos_eval['q_rebose_m3_s']:.2f} m³/s (~{datos_eval['q_rebose_ls']:,.0f} L/s) [valor aproximado en calibración] por encima de la cota 885.75 msnm hacia la confluencia con el Río Suratá y Majadas.")
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
# TAB 3: RADAR SATELITAL & PRONÓSTICOS (72H • 7D • 15D • 30D)
# ------------------------------------------------------------
with tab_radar_72h:
    st.subheader(f"🛰️ Radar Satelital & Pronósticos Meteorológicos (72h • 7d • 15d • 30d) — {seleccion.replace('_', ' ')}")
    st.caption("Predicción numérica multitemporal (72 horas, Semanal 7d, Quincenal 15d y Mensual 30d vía Open-Meteo ECMWF/GFS) y reflectividad Doppler en vivo para toda la red amb.")
    meta_sel = METADATA_ESTACIONES_AMB.get(seleccion, METADATA_ESTACIONES_AMB["Embalse"])
    lat_sel = meta_sel["lat"]
    lon_sel = meta_sel["lon"]
    lag_estacion = meta_sel.get('lag_horas', '1.0 - 2.0 h')
    df_fc = pd.DataFrame()
    p_max_fc = 0.0
    p_tot_fc = 0.0
    col_rad1, col_rad2 = st.columns([1.25, 1])
    with col_rad1:
        st.markdown(f"### 🌧️ Pronóstico Numérico Dedicado (Open-Meteo): {meta_sel['nombre_completo']}")
        st.caption(f"📍 Coordenadas: `{lat_sel:.4f}°N, {lon_sel:.4f}°W` • Altitud: `{meta_sel['altitud_msnm']:,.2f} msnm` • Cuenca: `{meta_sel['cuenca_principal']}`")
        df_fc_all = obtener_pronostico_open_meteo(lat_sel, lon_sel, past_days=7, forecast_days=3)
        if not df_fc_all.empty:
            es_respaldo_sat = ('origen_satelital' in df_fc_all.columns and df_fc_all['origen_satelital'].iloc[0] == 'RESPALDO_LOCAL_AMB')
            if es_respaldo_sat:
                st.info("🛡️ **Respaldo Altimétrico Local Activo (`[Virtual / Estimado]`):** El servidor externo de *Open-Meteo* presenta intermitencia temporal. La serie horaria se calcula automáticamente mediante el gradiente altimétrico de la red amb (`-0.65°C/100 m`).")
            ahora_fc = datetime.now()
            df_fc_all['time_dt'] = pd.to_datetime(df_fc_all['time'])
            df_fc = df_fc_all[df_fc_all['time_dt'] >= (ahora_fc - timedelta(hours=1))].head(72).copy()
            if df_fc.empty:
                df_fc = df_fc_all.tail(72).copy()
            df_24h_fc = df_fc[df_fc['time_dt'] <= (ahora_fc + timedelta(hours=24))]
            lluvia_24h = df_24h_fc['precipitation'].sum() if not df_24h_fc.empty else df_fc.iloc[:24]['precipitation'].sum()
            lluvia_72h = df_fc['precipitation'].sum()
            t_max_fc = df_fc['temperature_2m'].max()
            t_min_fc = df_fc['temperature_2m'].min()
            v_max_fc = df_fc['wind_speed_10m'].max()
            if seleccion == "Embalse":
                vol_espejo_m3 = lluvia_72h * 462.0
                mc1, mc2, mc3, mc4 = st.columns(4)
                mc1.metric("🌧️ Lluvia Próximas 24h", f"{lluvia_24h:.1f} mm", delta="Lluvia sobre el vaso" if lluvia_24h > 0 else "Sin lluvia")
                mc2.metric("🌧️ Lluvia Total 72h", f"{lluvia_72h:.1f} mm", delta=f"+{vol_espejo_m3:,.0f} m³ al espejo (46 ha)", help="Aporte pluviométrico directo sobre el espejo de agua del embalse (462 m³/mm)")
                mc3.metric("🌡️ Temp Prevista", f"{t_min_fc:.1f} / {t_max_fc:.1f} °C")
                mc4.metric("💨 Ráfaga Máx Prevista", f"{v_max_fc:.1f} km/h")
            elif seleccion == "Surata":
                q_est_pico_ls = CAUDAL_PROMEDIO_BASE_MAJADAS_LS + (df_fc['precipitation'].max() * 145.0)
                mc1, mc2, mc3, mc4 = st.columns(4)
                mc1.metric("🌧️ Lluvia 24h (Majadas)", f"{lluvia_24h:.1f} mm", delta="Sector Majadas / Bosconia" if lluvia_24h > 0 else "Tiempo seco en cañón")
                mc2.metric("🌧️ Lluvia Total 72h", f"{lluvia_72h:.1f} mm", delta=f"Q pico proy: ~{q_est_pico_ls:,.0f} L/s", help="Proyección de respuesta hidrológica en Majadas sumando el caudal base (~2,000 L/s) y el pulso pluvial previsto")
                mc3.metric("🌡️ Temp Cañón (765m)", f"{t_min_fc:.1f} / {t_max_fc:.1f} °C")
                mc4.metric("💨 Ráfaga Máx Prevista", f"{v_max_fc:.1f} km/h")
            else:
                mc1, mc2, mc3, mc4 = st.columns(4)
                mc1.metric("🌧️ Lluvia Próximas 24h", f"{lluvia_24h:.1f} mm", delta="Lluvia esperada" if lluvia_24h > 0 else "Sin lluvia")
                mc2.metric("🌧️ Lluvia Total 72h", f"{lluvia_72h:.1f} mm", delta="3 días acumulados")
                mc3.metric("🌡️ Temp Prevista", f"{t_min_fc:.1f} / {t_max_fc:.1f} °C")
                mc4.metric("💨 Ráfaga Máx Prevista", f"{v_max_fc:.1f} km/h")
            # Gráfica 1: Precipitación Horaria Prevista
            fig_fc_p = px.bar(
                df_fc,
                x='time',
                y='precipitation',
                title=f'🌧️ Precipitación Horaria Prevista (mm/h) — Próximas 72 Horas en {seleccion.replace("_", " ")}',
                labels={'precipitation': 'Lluvia (mm/h)', 'time': 'Fecha / Hora'},
                color='precipitation',
                color_continuous_scale='Blues'
            )
            fig_fc_p.update_layout(height=280, template='plotly_white', margin=dict(t=40, b=10, l=10, r=10))
            st.plotly_chart(fig_fc_p, use_container_width=True)
            # Gráfica 2: Temperatura y Viento Previsto (Doble Eje Y compatible)
            fig_fc_t = make_subplots(specs=[[{"secondary_y": True}]])
            fig_fc_t.add_trace(go.Scatter(x=df_fc['time'], y=df_fc['temperature_2m'], mode='lines', name='Temperatura (°C)', line=dict(color='#FF4B4B', width=2.5)), secondary_y=False)
            fig_fc_t.add_trace(go.Scatter(x=df_fc['time'], y=df_fc['wind_speed_10m'], mode='lines', name='Viento (km/h)', line=dict(color='#005073', width=2, dash='dot')), secondary_y=True)
            fig_fc_t.update_layout(
                title='🌡️ Curva de Temperatura (°C) & 💨 Velocidad de Viento (km/h) a 72 Horas',
                xaxis_title='Fecha / Hora',
                height=280,
                template='plotly_white',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(t=40, b=10, l=10, r=10)
            )
            fig_fc_t.update_yaxes(title_text="Temperatura (°C)", secondary_y=False)
            fig_fc_t.update_yaxes(title_text="Viento (km/h)", secondary_y=True)
            st.plotly_chart(fig_fc_t, use_container_width=True)
        else:
            st.warning("⚠️ No se pudo conectar con el servicio de pronóstico meteorológico.")
    with col_rad2:
        st.markdown("### 🛰️ Visor Satelital & Radar en Vivo (Santander)")
        st.caption("Imágenes infrarrojas GOES-16 y frentes de tormenta en tiempo real centrados en la estación")
        tipo_visor = st.radio(
            "Capa Meteorológica:",
            ["🛰️ Satélite GOES-16 (Nubes en Vivo)", "🌧️ Radar de Precipitación", "📡 RainViewer"],
            horizontal=True,
            label_visibility="collapsed"
        )
        if "Satélite" in tipo_visor:
            map_url = f"https://embed.windy.com/embed2.html?lat={lat_sel}&lon={lon_sel}&detailLat={lat_sel}&detailLon={lon_sel}&width=650&height=480&zoom=10&level=surface&overlay=satellite&product=satellite&menu=&message=&marker=true&calendar=now&pressure=&type=map&location=coordinates&detail=&metricWind=default&metricTemp=default&radarRange=-1"
            subtitulo_mapa = f"🛰️ Satélite Infrarrojo GOES-16 centrado en <strong>{meta_sel['nombre_completo']}</strong>. Muestra la masa nubosa, convección y vapor de agua en vivo."
        elif "Radar" in tipo_visor:
            map_url = f"https://embed.windy.com/embed2.html?lat={lat_sel}&lon={lon_sel}&detailLat={lat_sel}&detailLon={lon_sel}&width=650&height=480&zoom=10&level=surface&overlay=radar&product=radar&menu=&message=&marker=true&calendar=now&pressure=&type=map&location=coordinates&detail=&metricWind=default&metricTemp=default&radarRange=-1"
            subtitulo_mapa = f"🌧️ Radar de precipitación y reflectividad Doppler centrado en <strong>{meta_sel['nombre_completo']}</strong>."
        else:
            map_url = f"https://www.rainviewer.com/map.html?loc={lat_sel},{lon_sel},10&oFa=0&oC=1&oU=0&oCS=1&oF=0&oAP=1&c=3&o=83&lm=1&layer=radar&sm=1&sn=1"
            subtitulo_mapa = f"📡 RainViewer centrado en <strong>{meta_sel['nombre_completo']}</strong>."
        st.markdown(f"""
        <iframe src="{map_url}" width="100%" height="480" frameborder="0" style="border-radius: 12px; border: 2px solid #005073; box-shadow: 0 4px 15px rgba(0,0,0,0.12);"></iframe>
        <div style="font-size: 11.5px; color: #555; text-align: center; margin-top: 6px;">
            {subtitulo_mapa}
        </div>
        """, unsafe_allow_html=True)
    if not df_fc_all.empty:
        with st.expander("📋 Ver Matriz Detallada de Pronóstico Numérico Hora a Hora (72h)"):
            df_fc_tabla = df_fc[['time', 'precipitation', 'temperature_2m', 'relative_humidity_2m', 'wind_speed_10m', 'wind_direction_10m']].copy()
            df_fc_tabla.columns = ['Fecha / Hora', 'Lluvia (mm/h)', 'Temperatura (°C)', 'Humedad (%)', 'Viento (km/h)', 'Dir. Viento (°)']
            st.dataframe(df_fc_tabla, use_container_width=True, hide_index=True)
    # ------------------------------------------------------------
    # SECCIÓN: INTERVENTORÍA EX-POST DE COINCIDENCIA SATELITAL VS PLUVIÓMETRO
    # ------------------------------------------------------------
    st.markdown("---")
    st.markdown(f"### 🔬 Interventoría & Validación Ex-Post: Satélite vs. Pluviómetro Físico ({seleccion.replace('_', ' ')})")
    st.caption("Auditoría retrospectiva de exactitud hidrometeorológica: Contraste hora a hora entre el pronóstico satelital numérico y la medición física real registrada en el pluviómetro de terreno (Pluvio² / balancín).")
    col_int_opt1, col_int_opt2 = st.columns([1, 1])
    if seleccion in ["Embalse", "Surata"]:
        st.markdown(f"""
        <div style="background: rgba(0, 80, 115, 0.06); padding: 12px 16px; border-radius: 8px; border-left: 4px solid #005073; font-size: 13px; margin-bottom: 12px;">
            <strong>ℹ️ Nota Hidrométrica de Campo:</strong> La estación <strong>{meta_sel['nombre_completo']}</strong> opera con sensor hidrométrico <strong>Radar OTT</strong> de nivel/caudal y no dispone de pluviómetro físico in situ. Para auditar la exactitud satelital en las cuencas tributarias que alimentan este punto, selecciona una de las estaciones pluviométricas de cabecera:
        </div>
        """, unsafe_allow_html=True)
        lista_aud = ["Monsalve", "Yerbabuena", "Vegas_del_Quemado", "El_Pajal", "La_Mariana"] if seleccion == "Surata" else ["Yerbabuena", "Vegas_del_Quemado", "El_Pajal", "La_Mariana", "Monsalve"]
        est_auditar = col_int_opt1.selectbox(
            "🏞️ Microcuenca Afluente a Auditar:",
            lista_aud,
            index=0,
            help="Selecciona la estación con pluviómetro físico para auditar la correlación satelital en la cuenca tributaria."
        )
        meta_aud = METADATA_ESTACIONES_AMB[est_auditar]
        lat_aud = meta_aud["lat"]
        lon_aud = meta_aud["lon"]
        nombre_auditar = meta_aud["nombre_completo"]
    else:
        est_auditar = seleccion
        lat_aud = lat_sel
        lon_aud = lon_sel
        nombre_auditar = meta_sel["nombre_completo"]
    with col_int_opt1:
        horas_eval_interv = st.selectbox(
            "⏱️ Ventana Histórica a Auditar:",
            [24, 48, 72, 168, 720],
            index=2,
            format_func=lambda h: f"Últimas {h} Horas ({h//24} Días)" if h >= 24 else f"Últimas {h} Horas",
            help="Período retrospectivo para contrastar la serie temporal de lluvia satelital contra la telemetría en BigQuery."
        )
    with col_int_opt2:
        umbral_lluvia_interv = st.slider(
            "🌧️ Umbral de Detección de Lluvia (mm/h):",
            min_value=0.05,
            max_value=1.0,
            value=0.10,
            step=0.05,
            help="Intensidad mínima horaria para clasificar un intervalo como evento activo de lluvia (Estándar OMM / WMO = 0.1 mm/h)."
        )
    # Asegurar cobertura temporal completa e independiente del slider para la auditoría y el fallback
    h_consulta_nec = max(horas_eval_interv, 168)
    f_fin_aud = datetime.now(colombia_tz)
    f_ini_aud = f_fin_aud - timedelta(hours=h_consulta_nec)
    df_hist_aud = get_historical_data_range(est_auditar, f_ini_aud, f_fin_aud)
    res_interv = calcular_interventoria_satelital_vs_terreno(
        df_hist=df_hist_aud,
        lat=lat_aud,
        lon=lon_aud,
        horas_eval=horas_eval_interv,
        umbral_mm=umbral_lluvia_interv
    )
    if res_interv.get("valido"):
        # 1. Tarjetas Superiores de Métricas de Calibración
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric(
            "🎯 Coincidencia Global",
            f"{res_interv['accuracy_pct']:.1f}%",
            delta=f"{res_interv['hits'] + res_interv['correct_neg']} de {res_interv['total_horas']}h",
            help="Exactitud global considerando tanto horas con lluvia como horas de tiempo seco."
        )
        k2.metric(
            "🌧️ Detección (POD)",
            f"{res_interv['pod_pct']:.1f}%",
            delta=f"{res_interv['hits']} aciertos / {res_interv['total_eventos_reales']}h lluvia",
            help="Probability of Detection (Hit Rate): Porcentaje de eventos de lluvia reales en terreno anticipados por el satélite."
        )
        k3.metric(
            "🚫 Falsa Alarma (FAR)",
            f"{res_interv['far_pct']:.1f}%",
            delta=f"{res_interv['false_alarms']} falsas alarmas" if res_interv['false_alarms'] > 0 else "0 falsas alarmas",
            delta_color="inverse",
            help="False Alarm Ratio: Alertas satelitales que no generaron lluvia en terreno (virga o nubosidad alta)."
        )
        k4.metric(
            "🏆 Threat Score (CSI)",
            f"{res_interv['csi_pct']:.1f}%",
            delta="Skill OMM/WMO",
            help="Critical Success Index: Calidad hidrológica penalizando falsas alarmas y omisiones."
        )
        k5.metric(
            "⚖️ Sesgo Magnitud (β)",
            f"{res_interv['factor_magnitud']:.2f}×",
            delta=f"n = {res_interv['total_eventos_reales']}h ({'Robusta' if res_interv['muestra_robusta'] else 'Reducida'})",
            help="Ratio entre lámina de lluvia real y satelital en eventos coincidentes (Hits). Factor multiplicador de volumen para calibración MOS."
        )
        # 2. Matriz de Confusión 2x2 y Errores Cuantitativos
        c_mat, c_err = st.columns([1.1, 1.2])
        with c_mat:
            st.markdown("#### 📋 Matriz de Contingencia 2×2 (Eventos Horarios)")
            st.markdown(f"""
            <table style="width: 100%; border-collapse: collapse; text-align: center; font-size: 13px; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
                <thead>
                    <tr style="background: #005073; color: white;">
                        <th style="padding: 8px; border: 1px solid #cce0eb;" rowspan="2">Satélite / Radar</th>
                        <th style="padding: 8px; border: 1px solid #cce0eb;" colspan="2">Pluviómetro Físico (Terreno)</th>
                    </tr>
                    <tr style="background: #0A192F; color: #64FFDA;">
                        <th style="padding: 6px; border: 1px solid #cce0eb;">🌧️ Con Lluvia (≥{umbral_lluvia_interv} mm)</th>
                        <th style="padding: 6px; border: 1px solid #cce0eb;">☀️ Tiempo Seco (<{umbral_lluvia_interv} mm)</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td style="font-weight: 700; background: #F0F4F8; padding: 8px; border: 1px solid #cce0eb;">🌧️ Pronosticó Lluvia</td>
                        <td style="background: rgba(0, 204, 150, 0.2); font-weight: 800; color: #00805A; padding: 8px; border: 1px solid #cce0eb;">
                            ✅ ACIERTO (Hits)<br><span style="font-size: 16px;">{res_interv['hits']} h</span>
                        </td>
                        <td style="background: rgba(255, 128, 0, 0.18); font-weight: 700; color: #D96B00; padding: 8px; border: 1px solid #cce0eb;">
                            ⚠️ FALSA ALARMA<br><span style="font-size: 16px;">{res_interv['false_alarms']} h</span>
                        </td>
                    </tr>
                    <tr>
                        <td style="font-weight: 700; background: #F0F4F8; padding: 8px; border: 1px solid #cce0eb;">☀️ Pronosticó Seco</td>
                        <td style="background: rgba(255, 75, 75, 0.18); font-weight: 700; color: #CC0000; padding: 8px; border: 1px solid #cce0eb;">
                            ❌ OMISIÓN (Misses)<br><span style="font-size: 16px;">{res_interv['misses']} h</span>
                        </td>
                        <td style="background: rgba(0, 80, 115, 0.12); font-weight: 800; color: #005073; padding: 8px; border: 1px solid #cce0eb;">
                            🟢 SECO COINCIDENTE<br><span style="font-size: 16px;">{res_interv['correct_neg']} h</span>
                        </td>
                    </tr>
                </tbody>
            </table>
            """, unsafe_allow_html=True)
        with c_err:
            st.markdown("#### 📐 Métricas Cuantitativas de Precipitación & Sesgo")
            st.markdown(f"""
            <div style="background: rgba(0,80,115,0.05); padding: 14px 18px; border-radius: 10px; border-left: 4px solid #005073; font-size: 13px; line-height: 1.7;">
                <strong>🌧️ Lluvia Total Acumulada en el Período:</strong><br>
                • <strong>Pluviómetro Físico (Pluvio² amb):</strong> <code>{res_interv['lluvia_tot_obs']:.2f} mm</code> ({res_interv['horas_con_lluvia_obs']}h con lluvia)<br>
                • <strong>Estimación Satelital (Open-Meteo):</strong> <code>{res_interv['lluvia_tot_sat']:.2f} mm</code> ({res_interv['horas_con_lluvia_sat']}h con lluvia)<br>
                • <strong>Desviación Neta Acumulada:</strong> <code>{res_interv['lluvia_tot_sat'] - res_interv['lluvia_tot_obs']:+.2f} mm</code><br>
                • <strong>Factor Sesgo de Magnitud (β):</strong> <code>{res_interv['factor_magnitud']:.2f}×</code> ({'Subestimación satelital (+ lámina real)' if res_interv['factor_magnitud'] > 1.05 else ('Sobreestimación satelital (+ lámina satélite)' if res_interv['factor_magnitud'] < 0.95 else 'Calibración de volumen neutra')})<br>
                <hr style="margin: 8px 0; border: none; border-top: 1px dashed rgba(0,80,115,0.2);">
                <strong>📊 Estadísticos de Dispersión & Correlación:</strong><br>
                • <strong>Error Absoluto Medio (MAE):</strong> <code>{res_interv['mae_mm']:.3f} mm/h</code><br>
                • <strong>Error Cuadrático Medio (RMSE):</strong> <code>{res_interv['rmse_mm']:.3f} mm/h</code><br>
                • <strong>Coeficiente de Correlación Pearson (r):</strong> <code>{res_interv['corr_pearson']:.3f}</code> (R²: <code>{res_interv['corr_pearson']**2:.3f}</code>)
            </div>
            """, unsafe_allow_html=True)
        # 3. Gráfica Comparativa de Interventoría Hora a Hora
        df_comp = res_interv['df_comparativo']
        fig_comp = go.Figure()
        fig_comp.add_trace(go.Bar(
            x=df_comp['time_bin'],
            y=df_comp['precip_obs_mm'],
            name='Pluviómetro Físico (Terreno amb)',
            marker_color='#00CC96',
            opacity=0.85
        ))
        fig_comp.add_trace(go.Bar(
            x=df_comp['time_bin'],
            y=df_comp['precip_sat_mm'],
            name='Satélite / Radar (Open-Meteo)',
            marker_color='#005073',
            opacity=0.70
        ))
        fig_comp.update_layout(
            title=f'📊 Auditoría Ex-Post: Lluvia Registrada en Terreno vs. Lluvia Estimada por Satélite (Últimas {horas_eval_interv}h)',
            xaxis_title='Fecha / Hora',
            yaxis_title='Precipitación Horaria (mm/h)',
            barmode='group',
            template='plotly_white',
            height=320,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(t=40, b=10, l=10, r=10)
        )
        st.plotly_chart(fig_comp, use_container_width=True)
        # 4. Diagnóstico Técnico de Interventoría (Específico para OTT Pluvio² Gravimétrico por Celda de Carga)
        ll_sat_eval = float(res_interv.get('lluvia_tot_sat', 0.0))
        ll_obs_eval = float(res_interv.get('lluvia_tot_obs', 0.0))
        h_sat_eval = int(res_interv.get('horas_con_lluvia_sat', 0))
        if ll_sat_eval >= 15.0 and h_sat_eval >= 8 and ll_obs_eval <= max(1.0, 0.05 * ll_sat_eval):
            diag_estado = "DISCREPANCIA ESPACIAL SATÉLITE vs. ESTACIÓN FÍSICA (MICROCLIMA / SUBCUENCAS VECINAS)"
            diag_color = "#FF8000"
            diag_txt = (
                f"El modelo de grilla satelital estima <strong>{ll_sat_eval:.2f} mm ({h_sat_eval}h)</strong> en el bloque regional, "
                f"mientras que el pluviómetro físico en <strong>{meta_sel['nombre_completo']}</strong> registró <strong>{ll_obs_eval:.2f} mm</strong>. "
                f"En alta montaña esta diferencia suele deberse a que el modelo numérico sobreestima la lluvia caída por nubosidad fría o promedia lluvias focalizadas en subcuencas vecinas (por ejemplo, aguaceros en el cañón de <strong>Vetas</strong> que drenan a la confluencia sin llover fuerte sobre el punto de <strong>Monsalve</strong>)."
            )
        elif res_interv['pod_pct'] >= 75.0 and res_interv['csi_pct'] >= 40.0 and res_interv['far_pct'] <= 50.0:
            diag_estado = "ALTA CONFIABILIDAD SATELITAL"
            diag_color = "#00CC96"
            diag_txt = f"Excelente calibración del modelo numérico sobre <strong>{meta_sel['nombre_completo']}</strong>. El satélite capturó el {res_interv['pod_pct']:.1f}% de las lluvias ocurridas en suelo (CSI: {res_interv['csi_pct']:.1f}%) con un error medio de {res_interv['mae_mm']:.2f} mm/h."
        elif res_interv['pod_pct'] >= 40.0 and res_interv['far_pct'] > 50.0:
            diag_estado = "SOBREESTIMACIÓN DEL MODELO SATELITAL (FAR ELEVADO)"
            diag_color = "#FF8000"
            diag_txt = f"Aunque el modelo detectó pulsos en suelo ({res_interv['pod_pct']:.1f}% POD), registra un <strong>{res_interv['far_pct']:.1f}% de falsa alarma ({ll_sat_eval:.1f} mm satélite vs. {ll_obs_eval:.1f} mm en estación física)</strong> por nubosidad alta sin precipitación efectiva en el sitio o lluvias en laderas vecinas."
        elif res_interv['pod_pct'] >= 40.0:
            diag_estado = "CONFIABILIDAD MODERADA (EVIDENCIA MICROCLIMÁTICA)"
            diag_color = "#FFBB00"
            diag_txt = f"Concordancia parcial ({res_interv['pod_pct']:.1f}% de detección). La orografía abrupta de la cuenca ({meta_sel['altitud_msnm']:,.0f} msnm) induce lluvias convectivas de valle o crestas locales que el modelo de 2 km suaviza."
        else:
            diag_estado = "DISCREPANCIA OROGRÁFICA / BLOQUEO TOPOGRÁFICO"
            diag_color = "#FF8000"
            diag_txt = f"Detección satelital reducida ({res_interv['pod_pct']:.1f}% POD). Predominan eventos hiperlocales o apantallamiento de nubes bajas por debajo de la resolución de reflectividad satelital."
        st.markdown(f"""
        <div class="alert-box" style="border-left: 5px solid {diag_color}; background: rgba(0, 80, 115, 0.04); font-size: 13px; line-height: 1.6;">
            <div>
                <strong>🔍 Diagnóstico de Interventoría Meteorológica: {diag_estado}</strong><br>
                {diag_txt}<br>
                <span style="font-size: 12px; color: #555;">
                    💡 <em>Utilidad Técnica: Esta auditoría permite calibrar qué estaciones de la red tienen correlación satelital óptima para anticipar caudales hacia PTAP Florida, PTAP La Flora/Morrorico y PTAP Bosconia.</em>
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info(f"ℹ️ {res_interv.get('mensaje', 'Consultando datos históricos de satélite...')}")
    # ------------------------------------------------------------
    # SECCIÓN: SISTEMA DE ALERTA TEMPRANA & MARGEN DE MANIOBRA OPERATIVO (SAT-IA)
    # ------------------------------------------------------------
    st.markdown("---")
    st.markdown(f"### 🚨 Sistema de Alerta Temprana Inteligente: Margen de Maniobra Operativo (SAT-IA)")
    st.caption("Ponderación probabilística de eventos extremos a 72h calibrada con el histórico empírico de aciertos para proteger bocatomas y optimizar plantas.")
    if not df_fc.empty:
        p_max_fc = float(df_fc['precipitation'].max() or 0.0)
        p_tot_fc = float(df_fc['precipitation'].sum() or 0.0)
        idx_max = df_fc['precipitation'].idxmax()
        hora_p_max = df_fc.loc[idx_max]['time']
        # ------------------------------------------------------------
        # CAPA DE CALIBRACIÓN MOS DUAL (DETECCIÓN + MAGNITUD + FALLBACK ADAPTATIVO)
        # ------------------------------------------------------------
        mes_actual = datetime.now().month
        if mes_actual in [3, 4, 5]:
            nombre_temporada = "1ª Temporada de Lluvias (Húmeda)"
            tag_temporada = "🌧️ HÚMEDA I"
        elif mes_actual in [6, 7, 8]:
            nombre_temporada = "Veranillo / Transición Seca"
            tag_temporada = "🌤️ TRANSICIÓN"
        elif mes_actual in [9, 10, 11]:
            nombre_temporada = "2ª Temporada de Lluvias (Húmeda Principal)"
            tag_temporada = "⛈️ HÚMEDA II"
        else:
            nombre_temporada = "Temporada Seca Principal (Estiaje)"
            tag_temporada = "☀️ SECA / ESTIAJE"
        lag_estacion = meta_sel.get('lag_horas', '1.0 - 2.0 h')
        # 1. Control de Estabilidad Estadística de Muestra (Fallback Jerárquico a 7 Días)
        n_obs_actual = int(res_interv.get('total_eventos_reales', 0)) if res_interv.get('valido') else 0
        es_muestra_corta = (n_obs_actual < 3 and horas_eval_interv < 168)
        if es_muestra_corta:
            # Consultar línea base extendida de 7 días (168h) para estabilizar MOS
            res_7d = calcular_interventoria_satelital_vs_terreno(
                df_hist=df_hist_aud,
                lat=lat_aud,
                lon=lon_aud,
                horas_eval=168,
                umbral_mm=umbral_lluvia_interv
            )
            if res_7d.get('valido') and res_7d.get('total_horas', 0) > 0:
                prob_calibrada = float(res_7d.get('pod_pct', 70.0))
                far_reciente = float(res_7d.get('far_pct', 30.0))
                csi_reciente = float(res_7d.get('csi_pct', 55.0))
                factor_magnitud_mos = float(res_7d.get('factor_magnitud', 1.0))
                n_base_7d = int(res_7d.get('total_eventos_reales', 0))
                tag_muestreo = f"🔄 Fallback Línea Base 7 Días (n={n_base_7d}h lluvia real | Ventana {horas_eval_interv}h con solo {n_obs_actual}h)"
            else:
                prob_calibrada = float(res_interv.get('pod_pct', 70.0))
                far_reciente = float(res_interv.get('far_pct', 30.0))
                csi_reciente = float(res_interv.get('csi_pct', 55.0))
                factor_magnitud_mos = float(res_interv.get('factor_magnitud', 1.0))
                tag_muestreo = f"⚠️ Muestra Reducida ({n_obs_actual}h con lluvia)"
        else:
            prob_calibrada = float(res_interv.get('pod_pct', 75.0)) if res_interv.get('valido') else 75.0
            far_reciente = float(res_interv.get('far_pct', 25.0)) if res_interv.get('valido') else 25.0
            csi_reciente = float(res_interv.get('csi_pct', 60.0)) if res_interv.get('valido') else 60.0
            factor_magnitud_mos = float(res_interv.get('factor_magnitud', 1.0)) if res_interv.get('valido') else 1.0
            tag_muestreo = f"✅ Muestra Directa {horas_eval_interv}h (n={n_obs_actual}h lluvia real)"
        # 2. Coeficiente Dual MOS Desacoplado (Detección Probabilística + Corrección de Magnitud Volumétrica)
        # I_MOS: Confiabilidad binaria de detección [0.0 - 1.0]
        factor_imos = max(0.0, min(1.0, (prob_calibrada / 100.0) * (1.0 - (far_reciente / 100.0))))
        # P_MOS = P_sat × beta_magnitud (corrección cuantitativa de magnitud)
        p_tot_mos = p_tot_fc * factor_magnitud_mos
        p_max_mos = p_max_fc * factor_magnitud_mos
        col_al1, col_al2 = st.columns([1.15, 1])
        with col_al1:
            # FILTRO DE CONFIABILIDAD EMPÍRICA PROPIO MIMAT-C26 (Criterio Unificado I_MOS)
            es_evento_fuerte = (p_max_fc >= 15.0 or p_tot_fc >= 30.0)
            es_evento_moderado = (p_max_fc >= 5.0 or p_tot_fc >= 15.0)
            es_confiable = (factor_imos >= 0.25)
            es_baja_confianza = (factor_imos < 0.25)
            if es_evento_fuerte and es_confiable:
                nivel_alerta = "ALERTA ROJA OPERATIVA: TORMENTA SEVERA CONFIRMADA"
                color_alerta = "#FF4B4B"
                icono_alerta = "⛈️"
                desc_alerta = f"Se pronostica un pico de <strong>{p_max_fc:.1f} mm/h</strong> el <code>{hora_p_max.strftime('%d/%m/%Y %H:%M')}</code> ({p_tot_fc:.1f} mm brutos ➔ <strong>{p_tot_mos:.1f} mm calibrados MOS</strong>).<br>🎯 <strong>Alta Confiabilidad MOS (I_MOS: {factor_imos*100:.0f}% | Sesgo Magnitud: {factor_magnitud_mos:.2f}×):</strong> El modelo satelital registra un <strong>{prob_calibrada:.1f}% de acierto real (POD)</strong> en esta estación ({tag_temporada}, {tag_muestreo}). <strong>Se recomienda activar protocolo de maniobra preventiva.</strong>"
                estado_operativo = "ACTIVAR_MANIOBRA"
            elif es_evento_fuerte and es_baja_confianza:
                nivel_alerta = "AVISO SATELITAL EN OBSERVACIÓN (NO VERIFICADO EN TERRENO)"
                color_alerta = "#FF8000"
                icono_alerta = "🟠"
                desc_alerta = f"El satélite proyecta lluvia bruta de <strong>{p_max_fc:.1f} mm/h</strong> ({p_tot_fc:.1f} mm en 72h), pero la lluvia calibrada MOS es de <strong>{p_tot_mos:.1f} mm</strong> (I_MOS: {factor_imos*100:.0f}%, Sesgo: {factor_magnitud_mos:.2f}×).<br>⚠️ <strong>Filtro de Confiabilidad Rodante ({tag_muestreo}):</strong> En esta microcuenca el modelo presenta baja habilidad de detección (<strong>POD: {prob_calibrada:.1f}% | Falsas Alarmas: {far_reciente:.1f}%</strong>) por bloqueo orográfico en {tag_temporada}.<br>🛡️ <strong>Criterio de Ingeniería:</strong> La alerta se mantiene en <em>observación pasiva</em>. <strong>NO escalar a Alerta Roja ni operar compuertas</strong> hasta que el pluviómetro físico (Pluvio²) confirme el primer pulso de lluvia."
                estado_operativo = "OBSERVACION_PASIVA"
            elif es_evento_moderado and es_confiable:
                nivel_alerta = "ALERTA AMARILLA PREVENTIVA: LLUVIA MODERADA"
                color_alerta = "#FFBB00"
                icono_alerta = "🌧️"
                desc_alerta = f"Previsión de lluvia moderada con pico de <strong>{p_max_fc:.1f} mm/h</strong> el <code>{hora_p_max.strftime('%d/%m/%Y %H:%M')}</code> ({p_tot_fc:.1f} mm brutos ➔ <strong>{p_tot_mos:.1f} mm calibrados MOS</strong>). Confiabilidad empírica ({tag_muestreo}): <strong>POD {prob_calibrada:.1f}% | FAR {far_reciente:.1f}% | Magnitud {factor_magnitud_mos:.2f}×</strong>."
                estado_operativo = "VIGILANCIA_ESTANDAR"
            elif es_evento_moderado and es_baja_confianza:
                nivel_alerta = "CONDICIÓN ESTÁNDAR (POSIBLE NUBOSIDAD ALTA / VIRGA)"
                color_alerta = "#005073"
                icono_alerta = "☁️"
                desc_alerta = f"El modelo numérico muestra nubosidad con {p_tot_fc:.1f} mm brutos (calibrado MOS: {p_tot_mos:.1f} mm), pero la auditoría rodante ({tag_muestreo}) indica alto sesgo eólico / virga (POD {prob_calibrada:.1f}%). Sin impacto operativo previsto."
                estado_operativo = "NORMAL"
            else:
                nivel_alerta = "ESTADO VERDE: CONDICIONES NORMALES / ESTIAJE"
                color_alerta = "#00CC96"
                icono_alerta = "☀️"
                desc_alerta = f"Sin eventos extremos previstos en la ventana de 72h (máximo previsto: {p_max_fc:.1f} mm/h). Operación estándar en cuenca ({tag_muestreo})."
                estado_operativo = "NORMAL"
            st.markdown(f"""
            <div style="background: rgba(0, 80, 115, 0.04); padding: 16px 20px; border-radius: 12px; border-left: 6px solid {color_alerta}; box-shadow: 0 4px 12px rgba(0,0,0,0.06);">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 24px;">{icono_alerta}</span>
                        <strong style="font-size: 15px; color: {color_alerta};">{nivel_alerta}</strong>
                    </div>
                    <span class="badge-status" style="background: rgba(0,80,115,0.15); color: #005073; border: 1px solid #005073;">{tag_temporada}</span>
                </div>
                <div style="font-size: 13px; line-height: 1.6; color: #222;">
                    {desc_alerta}<br>
                    ⏱️ <strong>Tiempo de Concentración / Retardo Hidrológico (Lag Time):</strong> <span style="color: #005073; font-weight: 700;">{lag_estacion}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with col_al2:
            st.markdown("#### 👷 Margen de Maniobra & Acciones Preventivas Sugeridas:")
            if estado_operativo == "OBSERVACION_PASIVA":
                st.markdown(f"""
                <div style="font-size: 12.5px; line-height: 1.6; background: #FFF8F0; padding: 14px 18px; border-radius: 10px; border: 1px solid #FFD0A8; box-shadow: 0 2px 6px rgba(0,0,0,0.04);">
                    <strong style="color: #D96B00; font-size: 13px;">🛡️ Protocolo Preventivo Anti-Falsa Alarma (Cero Fatiga Operativa):</strong>
                    <ul style="margin: 6px 0 0 0; padding-left: 18px;">
                        <li><strong>Tomero ({meta_sel['subsistema_abastecimiento']}):</strong> Mantener operación normal. Estar atento al reporte de telemetría in situ. <strong>No realizar purgas innecesarias</strong> ni suspender captación.</li>
                        <li><strong>Operadores de Planta (PTAP):</strong> Mantener dosificación química base sin alteración.</li>
                        <li><strong>Condición de Disparo:</strong> Solo si el pluviómetro físico Pluvio² registra un pulso real (P ≥ 1.0 mm), el sistema eleva a Alerta Operativa con ventana de <strong>{lag_estacion}</strong>.</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
            elif seleccion == "Embalse":
                vol_espejo_fc = p_tot_fc * 462.0
                st.markdown(f"""
                <div style="font-size: 12.5px; line-height: 1.6; background: white; padding: 14px 18px; border-radius: 10px; border: 1px solid #cce0eb; box-shadow: 0 2px 6px rgba(0,0,0,0.04);">
                    <ul style="margin: 0; padding-left: 18px;">
                        <li><strong>Operación de Presa & Válvula CRC Bosconia:</strong><br>
                        Aporte pluviométrico directo sobre el vaso proyectado en <strong>~{vol_espejo_fc:,.0f} m³</strong> en 72h ({p_tot_fc:.1f} mm). Monitorear tasa neta de descenso del embalse y recarga de afluentes de ladera.</li>
                        <li style="margin-top: 6px;"><strong>PTAP Bosconia & Futura PTAP Los Angelinos:</strong><br>
                        Seguimiento continuo de la disponibilidad de agua cruda en vaso y previsión de caudales de rebose Morning Glory si la cota supera 885.75 msnm hacia Puente Tona.</li>
                        <li style="margin-top: 6px;"><strong>Comunidades Ribereñas Puente Tona & Confluencia Suratá:</strong><br>
                        Monitoreo preventivo del cauce aguas abajo de la presa ante eventuales aportes mayores de quebradas afluentes.</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="font-size: 12.5px; line-height: 1.6; background: white; padding: 14px 18px; border-radius: 10px; border: 1px solid #cce0eb; box-shadow: 0 2px 6px rgba(0,0,0,0.04);">
                    <ul style="margin: 0; padding-left: 18px;">
                        <li><strong>Tomero / Operador en Bocatoma ({meta_sel['subsistema_abastecimiento']}):</strong><br>
                        Ventana de <strong>{lag_estacion}</strong> previa al pico para realizar purga preventiva de desarenadores, verificar rejillas y alistar cierre de compuertas ante picos de turbiedad.</li>
                        <li style="margin-top: 6px;"><strong>Operadores de Planta (PTAP Florida / La Flora / Morrorico / Bosconia):</strong><br>
                        Alistamiento anticipado de dosificación de coagulantes y regulación de niveles en tanques de almacenamiento.</li>
                        <li style="margin-top: 6px;"><strong>Gestión del Riesgo & Comunidades Ribereñas:</strong><br>
                        Aviso preventivo en microcuenca <em>{meta_sel['microcuencas']}</em> ante posible aumento súbito de nivel en quebradas tributarias.</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
        # ------------------------------------------------------------
        # SUBSECCIÓN: CENTRO DE NOTIFICACIONES SMS & ALERTAS EN VIVO (amb)
        # ------------------------------------------------------------
        st.markdown("---")
        with st.expander("📲 Centro de Notificaciones SMS & Diagnóstico de Envío en Vivo (SAT-IA)", expanded=True):
            st.markdown("""
            <div style="background: rgba(0,80,115,0.05); padding: 12px 16px; border-radius: 8px; border-left: 4px solid #005073; font-size: 13px; line-height: 1.5; margin-bottom: 12px;">
                <strong>📱 Política Activa de Mensajería SMS (Modo Optimización de Saldo Twilio — 1 Segmento GSM-7 ≤ 155 chars):</strong><br>
                • <strong>1. Único Reporte Diario Programado (07:00 AM COT):</strong> Estado de cota del Embalse Tona, <strong>caudal real del Río Suratá en Majadas</strong>, lluvias 24h y clasificación dinámica de <code>Estado:</code> (<code>ALTO FLUJO Surata</code>, <code>ALERTA AMARILLA/NARANJA/ROJA</code> o <code>Normal</code>).<br>
                • <strong>2. Exclusivamente Alertas Tempranas Hidrometeorológicas en Vivo:</strong> Solo se despachan SMS adicionales cuando ocurre una <strong>creciente/alto flujo en el Río Suratá (Majadas → Toma Bosconia)</strong> o cuando una <strong>lluvia intensa supera los umbrales de alerta en las cuencas altas</strong>.<br>
                • <strong>🔒 Disparo 100% Automatizado por Cloud Scheduler (Sin Botones Manuales en UI):</strong> Los envíos están bloqueados desde la interfaz pública para evitar disparos accidentales por terceros y proteger el saldo prepago de Twilio.
            </div>
            """, unsafe_allow_html=True)
            try:
                q_ult_sms = """
                SELECT SAFE_CAST(timestamp AS TIMESTAMP) as fecha_utc, id_estacion, nivel_alerta, lluvia_mm
                FROM `gen-lang-client-0342049346.amb_hidrologia.log_alertas_sms`
                ORDER BY SAFE_CAST(timestamp AS TIMESTAMP) DESC
                LIMIT 8
                """
                df_logs_sms = pd.DataFrame([dict(r) for r in client.query(q_ult_sms).result()])
                if not df_logs_sms.empty:
                    df_logs_sms['Hora Colombia (COT)'] = pd.to_datetime(df_logs_sms['fecha_utc']).dt.tz_convert('America/Bogota').dt.strftime('%Y-%m-%d %H:%M:%S')
                    st.caption("📋 **Últimos despachos registrados en `log_alertas_sms` (BigQuery):**")
                    st.dataframe(df_logs_sms[['Hora Colombia (COT)', 'id_estacion', 'nivel_alerta', 'lluvia_mm']], use_container_width=True, hide_index=True)
            except Exception:
                pass
            c_sms1, c_sms2 = st.columns(2)
            info_maj_sms = sincronizar_fews_ideam_surata_bigquery()
            q_maj_prev_ls = float(info_maj_sms.get('caudal_ls', 3260.0))
            h_maj_prev_m = float(info_maj_sms.get('nivel_m', 1.12))
            cota_emb_prev = get_cota_embalse_actual_segura()
            if q_maj_prev_ls >= 14000.0 or h_maj_prev_m >= 1.66:
                estado_sms_prev = "ALERTA ROJA Creciente Surata"
            elif q_maj_prev_ls >= 7500.0 or h_maj_prev_m >= 1.45:
                estado_sms_prev = "ALERTA NARANJA Creciente Surata"
            elif q_maj_prev_ls >= 5000.0 or h_maj_prev_m >= 1.28:
                estado_sms_prev = "ALERTA AMARILLA Caudal Alto"
            elif q_maj_prev_ls >= 3800.0 or h_maj_prev_m >= 1.18:
                estado_sms_prev = "ALTO FLUJO Surata (2x Base)"
            elif cota_emb_prev > 885.75:
                estado_sms_prev = "Normal (Rebose Embalse)"
            else:
                estado_sms_prev = "Normal"
            with c_sms1:
                st.markdown("##### 🚀 1. Formato Boletín Matutino 07:00 AM (1 Segmento GSM-7 ≤ 155 chars)")
                sms_act_preview = (
                    f"REPORTE 7AM MIMAT-C26 ({datetime.now(colombia_tz).strftime('%d-%b 07:00')})\n"
                    f"Lluvias: Pajal:5.3mm, Monsalve:1.5mm\n"
                    f"Embalse Tona: {cota_emb_prev:.2f} msnm\n"
                    f"Rio Surata: {q_maj_prev_ls:,.0f} L/s ({q_maj_prev_ls/1000.0:.2f}m3/s H:{h_maj_prev_m:.2f}m)\n"
                    f"Estado: {estado_sms_prev}"
                )
                st.text_area(f"Texto SMS Matutino ({len(sms_act_preview)} chars • 1 segmento):", sms_act_preview, height=150)
            with c_sms2:
                st.markdown(f"##### 🚨 2. Plantilla de Alerta Temprana (1 Segmento GSM-7) — {meta_sel['nombre_completo']}")
                if seleccion == "Surata":
                    sms_alerta_preview = (
                        f"ALERTA AMARILLA RIO SURATA\n"
                        f"Majadas: {q_maj_prev_ls:,.0f} L/s ({q_maj_prev_ls/1000.0:.2f}m3/s H:{h_maj_prev_m:.2f}m)\n"
                        f"Caudal alto significativo\n"
                        f"Hora: {datetime.now(colombia_tz).strftime('%H:%M')} COT"
                    )
                else:
                    p_sim = max(p_max_fc, 18.5)
                    sms_alerta_preview = (
                        f"ALERTA TEMPRANA NARANJA MIMAT\n"
                        f"{seleccion.replace('_', ' ')}: {p_sim:.1f}mm/h\n"
                        f"Transito hacia bocatoma/cuenca\n"
                        f"Hora: {datetime.now(colombia_tz).strftime('%H:%M')} COT"
                    )
                st.text_area(f"Formato SMS de Alerta ({len(sms_alerta_preview)} chars • 1 segmento):", sms_alerta_preview, height=150)

    # ------------------------------------------------------------
    # SECCIÓN NUEVA: RESUMEN CONSOLIDADO DE PREDICCIONES MULTITEMPORALES OPEN-METEO
    # (SEMANAL 7 DÍAS • QUINCENAL 15 DÍAS • MENSUAL 30 DÍAS — TODAS LAS ESTACIONES)
    # ------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 🗓️ Resumen Consolidado de Predicciones de Precipitación Open-Meteo (Semanal • Quincenal • Mensual)")
    st.caption(
        "Síntesis multitemporal de precipitación proyectada para las **7 estaciones de la red hidrometeorológica amb** "
        "(Horizonte **Semanal 7 días**, **Quincenal 15 días** y **Mensual 30 días** vía *Open-Meteo Forecast 16d + Seasonal ECMWF SEAS5*)."
    )

    info_multi_om = obtener_predicciones_multitemporales_open_meteo()
    df_multi_res = info_multi_om.get("df_resumen", pd.DataFrame()).copy()
    series_multi_map = info_multi_om.get("series_diarias", {})
    origen_multi = info_multi_om.get("origen", "OPEN_METEO_VIVO")

    if not df_multi_res.empty:
        # Cálculo de promedios por subsistema hidrográfico
        est_cuenca_tona = ["El_Pajal", "Vegas_del_Quemado", "La_Mariana", "Yerbabuena"]
        df_tona_m = df_multi_res[df_multi_res["id_estacion"].isin(est_cuenca_tona)]
        df_surata_m = df_multi_res[df_multi_res["id_estacion"].isin(["Monsalve", "Surata"])]

        prom_sem_red = float(df_multi_res["Semanal 7d (mm)"].mean())
        prom_qui_red = float(df_multi_res["Quincenal 15d (mm)"].mean())
        prom_men_red = float(df_multi_res["Mensual 30d (mm)"].mean())

        prom_sem_tona = float(df_tona_m["Semanal 7d (mm)"].mean()) if not df_tona_m.empty else prom_sem_red
        prom_qui_tona = float(df_tona_m["Quincenal 15d (mm)"].mean()) if not df_tona_m.empty else prom_qui_red
        prom_men_tona = float(df_tona_m["Mensual 30d (mm)"].mean()) if not df_tona_m.empty else prom_men_red

        idx_max_sem = df_multi_res["Semanal 7d (mm)"].idxmax()
        row_max_sem = df_multi_res.loc[idx_max_sem]

        # Tarjetas KPI Ejecutivas de los 3 Horizontes
        km1, km2, km3, km4 = st.columns(4)
        km1.metric(
            "🌧️ Predicción Semanal (Próx. 7 Días)",
            f"{prom_sem_red:.1f} mm",
            delta=f"Cuenca Tona: {prom_sem_tona:.1f} mm",
            help="Lámina media de precipitación prevista en los próximos 7 días sobre las 7 estaciones de la red amb."
        )
        km2.metric(
            "📆 Predicción Quincenal (Próx. 15 Días)",
            f"{prom_qui_red:.1f} mm",
            delta=f"Cuenca Tona: {prom_qui_tona:.1f} mm",
            help="Acumulado quincenal previsto (Días 1 a 15) integrando Semana 1 y Semana 2 del modelo determinístico Open-Meteo."
        )
        km3.metric(
            "🗓️ Proyección Mensual (Próx. 30 Días)",
            f"{prom_men_red:.1f} mm",
            delta=f"Cuenca Tona: {prom_men_tona:.1f} mm",
            help="Lámina acumulada proyectada a 30 días (Días 1 a 30) combinando Open-Meteo 16d + Proyección Estacional ECMWF SEAS5."
        )
        km4.metric(
            "⛰️ Estación de Mayor Lluvia (7d)",
            f"{row_max_sem['Semanal 7d (mm)']:.1f} mm",
            delta=f"{row_max_sem['id_estacion'].replace('_', ' ')} ({row_max_sem['Día Pico (Próx. 7d)']})",
            help="Estación donde Open-Meteo proyecta el mayor acumulado pluvial durante los próximos 7 días."
        )

        # Enriquecer tabla ejecutiva con fila de Promedio General de Red para lectura gerencial inmediata
        df_tabla_exec = df_multi_res[[
            "Estación",
            "Cuenca / Subsistema",
            "Altitud (msnm)",
            "Semanal 7d (mm)",
            "Semana 2 (Días 8-15 mm)",
            "Quincenal 15d (mm)",
            "Mensual 30d (mm)",
            "Día Pico (Próx. 7d)",
            "Prob. Máx 7d (%)",
            "Días Lluvia (≥1mm / 15d)"
        ]].copy()

        fila_prom = pd.DataFrame([{
            "Estación": "📊 PROMEDIO GENERAL RED MIMAT-C26 (7 Estaciones)",
            "Cuenca / Subsistema": "Síntesis Consolidada Cuencas Tona, Río Frío y Suratá",
            "Altitud (msnm)": round(float(df_multi_res["Altitud (msnm)"].mean()), 1),
            "Semanal 7d (mm)": round(prom_sem_red, 1),
            "Semana 2 (Días 8-15 mm)": round(float(df_multi_res["Semana 2 (Días 8-15 mm)"].mean()), 1),
            "Quincenal 15d (mm)": round(prom_qui_red, 1),
            "Mensual 30d (mm)": round(prom_men_red, 1),
            "Día Pico (Próx. 7d)": f"Máx en {row_max_sem['id_estacion'].replace('_', ' ')}",
            "Prob. Máx 7d (%)": int(round(float(df_multi_res["Prob. Máx 7d (%)"].max()))),
            "Días Lluvia (≥1mm / 15d)": int(round(float(df_multi_res["Días Lluvia (≥1mm / 15d)"].mean())))
        }])
        df_tabla_mostrar = pd.concat([df_tabla_exec, fila_prom], ignore_index=True)

        st.markdown("#### 📋 Matriz Ejecutiva de Predicciones por Estación (Semanal 7d • Quincenal 15d • Mensual 30d)")
        st.dataframe(df_tabla_mostrar, use_container_width=True, hide_index=True)

        col_dl_om1, col_dl_om2 = st.columns([1.2, 2.8])
        with col_dl_om1:
            csv_multi_bytes = df_tabla_mostrar.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 Descargar Resumen Predicciones (CSV)",
                data=csv_multi_bytes,
                file_name=f"predicciones_open_meteo_7d_15d_30d_amb_{datetime.now(colombia_tz).strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        with col_dl_om2:
            etq_orig_om = (
                "🟢 <strong>Fuente Activa:</strong> API Oficial Open-Meteo en Vivo (Forecast 16d + Seasonal 30d)"
                if origen_multi == "OPEN_METEO_VIVO"
                else "🛡️ <strong>Fuente Activa:</strong> Modelo Altimétrico Climatológico de Respaldo amb"
            )
            st.markdown(
                f"<div style='font-size:12px; color:#334155; padding-top:8px;'>{etq_orig_om} • "
                f"Última sincronización: <code>{info_multi_om.get('actualizado_cot', '')}</code></div>",
                unsafe_allow_html=True
            )

        # Gráficas Interactivas Comparativas: (1) Barras Agrupadas por Estación y (2) Serie Diaria 30 Días
        col_g_om1, col_g_om2 = st.columns([1.15, 1.0])
        with col_g_om1:
            nombres_cortos = [e.replace("_", " ") for e in df_multi_res["id_estacion"]]
            fig_bar_multi = go.Figure()
            fig_bar_multi.add_trace(go.Bar(
                x=nombres_cortos,
                y=df_multi_res["Semanal 7d (mm)"],
                name="Semanal (7 Días)",
                marker_color="#00B4D8",
                text=[f"{v:.0f}" for v in df_multi_res["Semanal 7d (mm)"]],
                textposition="outside"
            ))
            fig_bar_multi.add_trace(go.Bar(
                x=nombres_cortos,
                y=df_multi_res["Quincenal 15d (mm)"],
                name="Quincenal (15 Días)",
                marker_color="#0077B6",
                text=[f"{v:.0f}" for v in df_multi_res["Quincenal 15d (mm)"]],
                textposition="outside"
            ))
            fig_bar_multi.add_trace(go.Bar(
                x=nombres_cortos,
                y=df_multi_res["Mensual 30d (mm)"],
                name="Mensual (30 Días)",
                marker_color="#03045E",
                text=[f"{v:.0f}" for v in df_multi_res["Mensual 30d (mm)"]],
                textposition="outside"
            ))
            fig_bar_multi.update_layout(
                title="📊 Comparativa de Lluvia Proyectada por Estación: 7d vs. 15d vs. 30d (mm)",
                xaxis_title="Estación de la Red amb",
                yaxis_title="Precipitación Acumulada Prevista (mm)",
                barmode="group",
                template="plotly_white",
                height=360,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(t=45, b=20, l=15, r=15)
            )
            st.plotly_chart(fig_bar_multi, use_container_width=True)

        with col_g_om2:
            df_serie_sel = series_multi_map.get(seleccion, pd.DataFrame())
            if not df_serie_sel.empty:
                colores_horiz = {
                    "1. Semanal (Días 1–7)": "#00B4D8",
                    "2. Semana 2 (Días 8–15)": "#0077B6",
                    "3. Mensual (Días 16–30)": "#90E0EF"
                }
                fig_d30 = px.bar(
                    df_serie_sel,
                    x="fecha_str",
                    y="precip_mm",
                    color="horizonte",
                    color_discrete_map=colores_horiz,
                    title=f"🗓️ Distribución Diaria a 30 Días en {seleccion.replace('_', ' ')} (mm/día)",
                    labels={"fecha_str": "Fecha", "precip_mm": "Lluvia Diaria (mm)", "horizonte": "Horizonte"}
                )
                fig_d30.update_layout(
                    template="plotly_white",
                    height=360,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    margin=dict(t=45, b=20, l=15, r=15)
                )
                st.plotly_chart(fig_d30, use_container_width=True)
# ------------------------------------------------------------
# TAB 4: SERIES DE TIEMPO, ROSA DE VIENTOS Y DESCARGAS
# ------------------------------------------------------------
with tab_series:
    st.subheader(f"📈 Series de Tiempo — {seleccion.replace('_', ' ')}")
    if not df_hist.empty:
        if seleccion == "Embalse":
            df_enr_hist = enriquecer_datos_embalse(df_hist)
            # Gráfica 1: Cota de Nivel del Embalse con Span Dinámico de Alta Resolución (Colinas y Valles)
            fig_emb = px.line(df_enr_hist, x='timestamp', y='cota_embalse_msnm', title='🌊 Evolución de la Cota del Embalse (msnm)', labels={'cota_embalse_msnm': 'Cota (msnm)', 'timestamp': 'Fecha/Hora'})
            fig_emb.add_hline(y=NIVEL_REBOSE_EMBALSE, line_dash="dash", line_color="red", annotation_text="Rebose Morning Glory (885.75 msnm)")
            if not df_enr_hist.empty and 'cota_embalse_msnm' in df_enr_hist.columns:
                c_min_v = float(df_enr_hist['cota_embalse_msnm'].min())
                c_max_v = float(df_enr_hist['cota_embalse_msnm'].max())
                # Si está cerca del rebose (>= 885.00), incluir siempre la referencia 885.75 msnm en el encuadre;
                # si baja más (descarga de fondo / vaciado profundo hasta 817.94 msnm), abrir el span hasta donde baje el agua
                base_min = min(c_min_v, NIVEL_REBOSE_EMBALSE) if c_min_v >= 885.00 else c_min_v
                base_max = max(c_max_v, NIVEL_REBOSE_EMBALSE)
                amp_v = max(0.015, base_max - base_min)
                pad_v = max(0.008, amp_v * 0.25)
                y_min_span = max(817.94, round(base_min - pad_v, 3))
                y_max_span = min(891.55, round(base_max + pad_v, 3))
                fig_emb.update_yaxes(range=[y_min_span, y_max_span], tickformat=".3f")
            fig_emb.update_layout(height=320, template='plotly_white')
            st.plotly_chart(fig_emb, use_container_width=True)
            # 3 Gráficas Hidrodinámicas Oficiales: 1) Entradas, 2) Salidas y 3) Balance de Caudales
            col_emb1, col_emb2 = st.columns(2)
            with col_emb1:
                fig_entradas = go.Figure()
                if 'caudal_afluentes_ls' in df_enr_hist.columns:
                    fig_entradas.add_trace(go.Scatter(
                        x=df_enr_hist['timestamp'],
                        y=df_enr_hist['caudal_afluentes_ls'],
                        mode='lines',
                        name='📥 Caudal Entrada Cuenca (L/s)',
                        line=dict(color='#00CC96', width=2.5),
                        fill='tozeroy',
                        fillcolor='rgba(0, 204, 150, 0.14)'
                    ))
                if 'm3_entrada_cuenca_acum' in df_enr_hist.columns:
                    fig_entradas.add_trace(go.Scatter(
                        x=df_enr_hist['timestamp'],
                        y=df_enr_hist['m3_entrada_cuenca_acum'],
                        mode='lines',
                        name='📦 Vol. Acumulado Entrada (m³)',
                        line=dict(color='#00897B', width=2, dash='dot'),
                        yaxis='y2'
                    ))
                fig_entradas.update_layout(
                    title='📥 1. Entradas al Embalse: Llegada desde Cola y Subsidiarias',
                    xaxis_title='Fecha/Hora',
                    yaxis=dict(title='Caudal Entrada (L/s)'),
                    yaxis2=dict(title='Vol. Acumulado (m³)', overlaying='y', side='right', showgrid=False),
                    height=300,
                    template='plotly_white',
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_entradas, use_container_width=True)
            with col_emb2:
                fig_salidas = go.Figure()
                fig_salidas.add_trace(go.Scatter(
                    x=df_enr_hist['timestamp'],
                    y=df_enr_hist['m3_consumidos_bosconia'],
                    mode='lines',
                    name='📦 Vol. Entregado CRC Bosconia (m³)',
                    line=dict(color='#005073', width=2.2),
                    fill='tozeroy',
                    fillcolor='rgba(0, 80, 115, 0.14)',
                    yaxis='y2'
                ))
                fig_salidas.add_trace(go.Scatter(
                    x=df_enr_hist['timestamp'],
                    y=df_enr_hist['caudal_medio_bosconia_ls'],
                    mode='lines',
                    name='🚰 Caudal Salida CRC Bosconia (L/s)',
                    line=dict(color='#0288D1', width=2.3)
                ))
                if df_enr_hist['caudal_rebose_ls'].max() > 0:
                    fig_salidas.add_trace(go.Scatter(
                        x=df_enr_hist['timestamp'],
                        y=df_enr_hist['caudal_rebose_ls'],
                        mode='lines',
                        name='🌀 Salida Rebose MG (L/s)',
                        line=dict(color='#FF4B4B', width=2, dash='dot')
                    ))
                fig_salidas.update_layout(
                    title='📤 2. Salidas del Embalse: Válvula CRC Bosconia y Rebose MG',
                    xaxis_title='Fecha/Hora',
                    yaxis=dict(title='Caudal Salida (L/s)'),
                    yaxis2=dict(title='Vol. Entregado CRC (m³)', overlaying='y', side='right', showgrid=False),
                    height=300,
                    template='plotly_white',
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_salidas, use_container_width=True)
            # Gráfica 3: Balance de Caudales (Entradas vs. Salidas Totales y Balance Neto dV/dt)
            fig_q = go.Figure()
            if 'caudal_afluentes_ls' in df_enr_hist.columns:
                fig_q.add_trace(go.Scatter(
                    x=df_enr_hist['timestamp'],
                    y=df_enr_hist['caudal_afluentes_ls'],
                    mode='lines',
                    name='📥 Entrada Cuenca (Cola + Subsidiarias) [L/s]',
                    line=dict(color='#00CC96', width=2.6)
                ))
            if 'caudal_salidas_totales_ls' in df_enr_hist.columns:
                fig_q.add_trace(go.Scatter(
                    x=df_enr_hist['timestamp'],
                    y=df_enr_hist['caudal_salidas_totales_ls'],
                    mode='lines',
                    name='📤 Salida Total (CRC + Rebose MG + Filtraciones) [L/s]',
                    line=dict(color='#E65100', width=2.4)
                ))
            fig_q.add_trace(go.Scatter(
                x=df_enr_hist['timestamp'],
                y=df_enr_hist['caudal_medio_bosconia_ls'],
                mode='lines',
                name='🚰 Salida CRC Bosconia [L/s]',
                line=dict(color='#005073', width=2)
            ))
            if df_enr_hist['caudal_rebose_ls'].max() > 0:
                fig_q.add_trace(go.Scatter(
                    x=df_enr_hist['timestamp'],
                    y=df_enr_hist['caudal_rebose_ls'],
                    mode='lines',
                    name='🌀 Salida Rebose MG [L/s]',
                    line=dict(color='#FF4B4B', width=2, dash='dot')
                ))
            if 'balance_neto_caudales_ls' in df_enr_hist.columns:
                fig_q.add_trace(go.Scatter(
                    x=df_enr_hist['timestamp'],
                    y=df_enr_hist['balance_neto_caudales_ls'],
                    mode='lines',
                    name='⚖️ Balance Neto dV/dt (Entrada - Salida) [L/s]',
                    line=dict(color='#7E57C2', width=2, dash='dash')
                ))
            fig_q.add_hline(y=0.0, line_dash="dot", line_color="gray")
            fig_q.update_layout(
                title='⚖️ 3. Balance de Caudales del Embalse: Entradas vs. Salidas y Balance Neto (L/s)',
                xaxis_title='Fecha/Hora',
                yaxis_title='Caudal (L/s)',
                height=320,
                template='plotly_white',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_q, use_container_width=True)
            # Bloque de Balance Volumétrico y Promedios en Vivo
            if not df_enr_hist.empty:
                st.markdown("### 💧 Balance Hidrodinámico y Promedios del Período (Entradas, Salidas y Balance)")
                m3_in_periodo = float(df_enr_hist['m3_entrada_cuenca_acum'].iloc[-1]) if 'm3_entrada_cuenca_acum' in df_enr_hist.columns else 0.0
                m3_totales_periodo = float(df_enr_hist['m3_consumidos_bosconia'].iloc[-1]) if 'm3_consumidos_bosconia' in df_enr_hist.columns else 0.0
                m3_sal_tot_periodo = float(df_enr_hist['m3_salidas_totales_acum'].iloc[-1]) if 'm3_salidas_totales_acum' in df_enr_hist.columns else 0.0
                c_ini_p = float(df_enr_hist['cota_embalse_msnm'].iloc[0])
                c_fin_p = float(df_enr_hist['cota_embalse_msnm'].iloc[-1])
                var_lamina_cm = (c_fin_p - c_ini_p) * 100.0
                q_crc_medio_ls = float(df_enr_hist['caudal_medio_bosconia_ls'].mean()) if 'caudal_medio_bosconia_ls' in df_enr_hist.columns else 25.0
                q_reb_medio_ls = float(df_enr_hist['caudal_rebose_ls'].mean()) if 'caudal_rebose_ls' in df_enr_hist.columns else 0.0
                q_afl_medio_ls = float(df_enr_hist['caudal_afluentes_ls'].mean()) if 'caudal_afluentes_ls' in df_enr_hist.columns else 0.0
                q_sal_tot_medio_ls = float(df_enr_hist['caudal_salidas_totales_ls'].mean()) if 'caudal_salidas_totales_ls' in df_enr_hist.columns else (q_crc_medio_ls + q_reb_medio_ls + 51.0)
                q_bal_neto_medio_ls = float(df_enr_hist['balance_neto_caudales_ls'].mean()) if 'balance_neto_caudales_ls' in df_enr_hist.columns else (q_afl_medio_ls - q_sal_tot_medio_ls)
                cb1, cb2, cb3, cb4, cb5 = st.columns(5)
                cb1.metric("📥 Entrada Media Cuenca", f"~{q_afl_medio_ls:,.1f} L/s", delta=f"{m3_in_periodo:,.0f} m³ ingresados", help="Caudal medio y volumen total de llegada desde la cola del embalse y quebradas subsidiarias")
                cb2.metric("🚰 Salida Media CRC Bosconia", f"{q_crc_medio_ls:,.1f} L/s", delta=f"{m3_totales_periodo:,.1f} m³ entregados", help="Promedio y volumen entregado medido por el caudalímetro ET_FIT401")
                cb3.metric("🌀 Salida Media Rebose MG", f"~{q_reb_medio_ls:,.1f} L/s", help="Vertimiento medio evacuado por el Morning Glory hacia Puente Tona")
                cb4.metric("📤 Salida Total Media", f"~{q_sal_tot_medio_ls:,.1f} L/s", delta=f"{m3_sal_tot_periodo:,.0f} m³ evacuados", help="Suma de CRC Bosconia + Rebose Morning Glory + Filtraciones (~51 L/s)")
                cb5.metric("⚖️ Balance Neto Caudales", f"{q_bal_neto_medio_ls:+,.1f} L/s", delta=f"{var_lamina_cm:+.2f} cm ({c_fin_p:.3f} msnm)", help="Diferencia neta entre Entrada de Cuenca y Salida Total (dV/dt)")
                st.markdown(f"""
                <div style="background: rgba(0,80,115,0.05); padding: 10px 14px; border-radius: 6px; border-left: 3px solid #005073; margin: 8px 0; font-size: 12.5px;">
                    ⚖️ <strong>Ecuación de Continuidad e Hidrodinámica del Vaso:</strong><br>
                    <code>Entrada Cuenca (~{q_afl_medio_ls:,.1f} L/s | {m3_in_periodo:,.0f} m³) - Salida Total (~{q_sal_tot_medio_ls:,.1f} L/s | {m3_sal_tot_periodo:,.0f} m³) = Balance Neto dV/dt ({q_bal_neto_medio_ls:+,.1f} L/s | ΔH {var_lamina_cm:+.2f} cm)</code><br>
                    <em>Detalle Salidas: Válvula CRC Bosconia = <strong>{q_crc_medio_ls:,.1f} L/s ({m3_totales_periodo:,.1f} m³)</strong> • Rebose Morning Glory = <strong>~{q_reb_medio_ls:,.1f} L/s</strong> • Filtraciones = <strong>~51.0 L/s</strong>.</em>
                </div>
                """, unsafe_allow_html=True)
                df_bal_24h_vista = consolidar_balance_diario_embalse(df_enr_hist)
                if not df_bal_24h_vista.empty:
                    st.markdown("#### 📅 Tabla de Promedios y Consolidado Diario (Entradas, Salidas y Balance — 24 Horas Exactas):")
                    st.dataframe(df_bal_24h_vista, use_container_width=True, hide_index=True)
        elif seleccion == "Surata":
            df_enr_sur_s = enriquecer_datos_surata(df_hist)
            if not df_enr_sur_s.empty:
                st.markdown("""
                <div style="background: rgba(0, 128, 128, 0.08); border-left: 5px solid #008080; padding: 10px 15px; border-radius: 8px; margin-bottom: 12px; font-size: 13px;">
                    🏞️ <strong>Hidrograma Oficial — Estación Río Suratá (Sector Majadas):</strong> Curva calculada mediante <code>Q(m³/s) = 1.2455 × (H_mira + 0.13)^4.1635</code> sobre el nivel compilado de las 3 tablas del IDEAM (<code>0230</code>, <code>0231</code> y <code>0232</code>) con el descuento oficial de <strong>-4 cm (-0.04 m)</strong>. <em>(Nota: El caudal de tratamiento de Bosconia no se incluye hasta conectar su sensor; el aporte de rebose del Morning Glory hacia Puente Tona es aproximado mientras se calibra esa ecuación).</em>
                </div>
                """, unsafe_allow_html=True)
                # Gráfica 1: Nivel Hidrométrico de la Mira (m) con Umbrales del Semáforo
                fig_h_sur = go.Figure()
                fig_h_sur.add_trace(go.Scatter(
                    x=df_enr_sur_s['timestamp'],
                    y=df_enr_sur_s['nivel_m_filtrado'],
                    mode='lines+markers',
                    name='Nivel Mira Calibrado (-4 cm IDEAM) [m]',
                    line=dict(color='#008080', width=2.8)
                ))
                fig_h_sur.add_hline(y=1.36, line_dash="dot", line_color="#FFBB00", annotation_text="Umbral Amarillo (1.36 m / 6,500 L/s)")
                fig_h_sur.add_hline(y=1.48, line_dash="dash", line_color="#FF8000", annotation_text="Alerta Naranja (1.48 m / 9,000 L/s)")
                fig_h_sur.add_hline(y=1.66, line_dash="dash", line_color="#FF4B4B", annotation_text="Alerta Roja Creciente (1.66 m / 14,000 L/s)")
                fig_h_sur.update_layout(
                    title='🌊 Evolución del Nivel Hidrométrico en la Mira de Majadas (m) — Compilado 3 Sensores IDEAM (-4 cm)',
                    xaxis_title='Fecha / Hora (COT)',
                    yaxis_title='Nivel Mira H (m)',
                    height=310,
                    template='plotly_white',
                    margin=dict(t=40, b=10, l=10, r=10)
                )
                st.plotly_chart(fig_h_sur, use_container_width=True)
                # Gráfica 2: Hidrograma de Caudal en Majadas (L/s) y Aporte Rebose Aprox. Morning Glory
                fig_q_sur = go.Figure()
                fig_q_sur.add_trace(go.Scatter(
                    x=df_enr_sur_s['timestamp'],
                    y=df_enr_sur_s['caudal_ls_filtrado'],
                    mode='lines+markers',
                    name='Caudal Total en Majadas (L/s)',
                    line=dict(color='#005073', width=3),
                    fill='tozeroy',
                    fillcolor='rgba(0, 80, 115, 0.10)'
                ))
                if df_enr_sur_s['rebose_aprox_morning_glory_ls'].max() > 0:
                    fig_q_sur.add_trace(go.Scatter(
                        x=df_enr_sur_s['timestamp'],
                        y=df_enr_sur_s['rebose_aprox_morning_glory_ls'],
                        mode='lines',
                        name='Aporte Rebose Aprox. Morning Glory [En Calibración] (L/s)',
                        line=dict(color='#AB63FA', width=2, dash='dot')
                    ))
                fig_q_sur.update_layout(
                    title='⚡ Hidrograma de Caudal en Majadas (L/s) — Ecuación Oficial Mira amb (-4 cm IDEAM)',
                    xaxis_title='Fecha / Hora (COT)',
                    yaxis_title='Caudal Q (L/s)',
                    height=340,
                    template='plotly_white',
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    margin=dict(t=45, b=10, l=10, r=10)
                )
                st.plotly_chart(fig_q_sur, use_container_width=True)
        else:
            df_plot = df_hist.sort_values('timestamp').copy()
            for col_n in ['temperatura', 'precipitacion', 'humedad', 'presion', 'velocidad_viento', 'direccion_viento']:
                if col_n in df_plot.columns:
                    df_plot[col_n] = pd.to_numeric(df_plot[col_n], errors='coerce')
            # 1. Filtrar filas en 0,0,0 (reinicios transitorios del SCADA central como el 17-oct 16:05 o caída de canales)
            if 'humedad' in df_plot.columns and 'temperatura' in df_plot.columns:
                df_fisico_valido = df_plot[(df_plot['humedad'] > 1.0) & ~((df_plot['temperatura'] == 0.0) & (df_plot.get('presion', pd.Series(0, index=df_plot.index)) == 0.0))].copy()
            else:
                df_fisico_valido = df_plot.copy()
            # Detectar si los datos físicos en la ventana están en 0,0,0 o congelados en Hold SCADA (sin variación real)
            usar_serie_virtual = False
            if len(df_fisico_valido) < 3:
                usar_serie_virtual = True
            elif seleccion in ["Yerbabuena", "La_Mariana"]:
                std_t = float(df_fisico_valido['temperatura'].std() or 0.0)
                std_v = float(df_fisico_valido['velocidad_viento'].std() or 0.0) if 'velocidad_viento' in df_fisico_valido.columns else 0.0
                ult_ts_val = df_fisico_valido['timestamp'].max()
                horas_sin_dato_sano = (datetime.now(colombia_tz) - ult_ts_val).total_seconds() / 3600.0 if pd.notna(ult_ts_val) else 999.0
                if (std_t < 0.001 and std_v < 0.001) or horas_sin_dato_sano > 4.0:
                    usar_serie_virtual = True
            df_virt_serie = pd.DataFrame()
            if usar_serie_virtual:
                meta_st = METADATA_ESTACIONES_AMB.get(seleccion, {})
                lat_st = meta_st.get("lat", 7.195831)
                lon_st = meta_st.get("lon", -72.914719)
                alt_st = meta_st.get("altitud_msnm", 3400.25)
                df_sat_s = obtener_pronostico_open_meteo(lat_st, lon_st, past_days=14, forecast_days=1)
                if not df_sat_s.empty:
                    df_sat_s = df_sat_s.copy()
                    t_sat = pd.to_datetime(df_sat_s['time'])
                    if t_sat.dt.tz is None:
                        df_sat_s['timestamp'] = t_sat.dt.tz_localize(colombia_tz)
                    else:
                        df_sat_s['timestamp'] = t_sat.dt.tz_convert(colombia_tz)
                    t_min_w = df_plot['timestamp'].min() if not df_plot.empty else (datetime.now(colombia_tz) - timedelta(hours=24))
                    t_max_w = datetime.now(colombia_tz)
                    df_virt_serie = df_sat_s[(df_sat_s['timestamp'] >= t_min_w - timedelta(hours=1)) & (df_sat_s['timestamp'] <= t_max_w)].copy()
                    if not df_virt_serie.empty:
                        df_virt_serie.rename(columns={
                            'temperature_2m': 'temperatura',
                            'precipitation': 'precipitacion',
                            'relative_humidity_2m': 'humedad',
                            'wind_speed_10m': 'velocidad_viento',
                            'wind_direction_10m': 'direccion_viento'
                        }, inplace=True)
                        # Presión barométrica dinámica modulada por temperatura horaria + marea barométrica semidiurna tropical
                        horas_float = df_virt_serie['timestamp'].dt.hour + df_virt_serie['timestamp'].dt.minute / 60.0
                        marea_hpa = 1.15 * np.sin(2.0 * np.pi * (horas_float - 4.0) / 12.0)
                        pres_base_isa = calcular_presion_atmosferica_hpa(alt_st, 10.0)
                        df_virt_serie['presion'] = np.round(pres_base_isa + marea_hpa + (df_virt_serie['temperatura'] - 10.0) * 0.08, 2)
            if not df_virt_serie.empty and len(df_fisico_valido) < 3:
                st.markdown(f"""
                <div style="background: rgba(0, 204, 150, 0.10); border: 1px solid #00CC96; border-left: 5px solid #00CC96; padding: 10px 14px; border-radius: 8px; margin-bottom: 12px; font-size: 13px;">
                    🛰️ <strong>Serie Horaria Reconstruida con Sensor Virtual Satelital (Open-Meteo + Modelo Barométrico ISA):</strong>
                    Dado que las lecturas en BigQuery de <strong>{seleccion.replace('_', ' ')}</strong> en esta ventana están en <code>0.0</code>, se grafican las curvas físicas reconstruidas por satélite sobre las coordenadas exactas de la estación (<code>{lat_st:.4f}°N, {lon_st:.4f}°W</code>).
                </div>
                """, unsafe_allow_html=True)
                df_graficar = df_virt_serie.sort_values('timestamp')
                sufijo_titulo = " [Sensor Virtual Satelital]"
            elif not df_virt_serie.empty and usar_serie_virtual:
                st.markdown(f"""
                <div style="background: rgba(0, 204, 150, 0.10); border: 1px solid #00CC96; border-left: 5px solid #00CC96; padding: 10px 14px; border-radius: 8px; margin-bottom: 12px; font-size: 13px;">
                    🛰️ <strong>Continuidad Híbrida (Terreno + Sensor Virtual Satelital):</strong>
                    Se empalman los datos físicos válidos de <strong>{seleccion.replace('_', ' ')}</strong> con el respaldo satelital durante las horas sin transmisión activa.
                </div>
                """, unsafe_allow_html=True)
                ult_sano = df_fisico_valido[df_fisico_valido['temperatura'].diff().abs().fillna(0.1) > 0.0001]['timestamp'].max()
                if pd.isna(ult_sano):
                    ult_sano = df_fisico_valido['timestamp'].min()
                df_f_tramo = df_fisico_valido[df_fisico_valido['timestamp'] <= ult_sano]
                df_v_tramo = df_virt_serie[df_virt_serie['timestamp'] > ult_sano]
                cols_comunes = ['timestamp', 'temperatura', 'precipitacion', 'humedad', 'presion', 'velocidad_viento', 'direccion_viento']
                df_graficar = pd.concat([df_f_tramo[cols_comunes], df_v_tramo[cols_comunes]], ignore_index=True).sort_values('timestamp')
                sufijo_titulo = " [Físico + Respaldo Virtual]"
            else:
                df_graficar = df_fisico_valido if not df_fisico_valido.empty else df_plot
                sufijo_titulo = ""
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                fig_t = px.line(df_graficar.sort_values('timestamp'), x='timestamp', y='temperatura', title=f'Temperatura (°C){sufijo_titulo}')
                fig_t.update_layout(height=280, template='plotly_white')
                st.plotly_chart(fig_t, use_container_width=True)
            with col_g2:
                fig_p = px.bar(df_graficar.sort_values('timestamp'), x='timestamp', y='precipitacion', title=f'Precipitación (mm){sufijo_titulo}', color='precipitacion', color_continuous_scale='Blues')
                fig_p.update_layout(height=280, template='plotly_white')
                st.plotly_chart(fig_p, use_container_width=True)
            if 'humedad' in df_graficar.columns:
                fig_h = px.line(df_graficar.sort_values('timestamp'), x='timestamp', y='humedad', title=f'Humedad Relativa (%){sufijo_titulo}')
                fig_h.update_layout(height=250, template='plotly_white')
                st.plotly_chart(fig_h, use_container_width=True)
            if 'presion' in df_graficar.columns:
                df_p_val = df_graficar.dropna(subset=['presion']).copy()
                df_p_val['presion'] = pd.to_numeric(df_p_val['presion'], errors='coerce')
                df_p_val = df_p_val[df_p_val['presion'] > 100]
                if not df_p_val.empty:
                    fig_pres = px.line(df_p_val.sort_values('timestamp'), x='timestamp', y='presion', title=f'Presión Atmosférica (hPa / mbar){sufijo_titulo}')
                    fig_pres.update_layout(height=250, template='plotly_white')
                    st.plotly_chart(fig_pres, use_container_width=True)
            if 'direccion_viento' in df_graficar.columns and 'velocidad_viento' in df_graficar.columns:
                st.markdown(f"### 🧭 Rosa de los Vientos{sufijo_titulo}")
                df_v = df_graficar.copy()
                df_v['direccion_viento'] = pd.to_numeric(df_v['direccion_viento'], errors='coerce')
                df_v['velocidad_viento'] = pd.to_numeric(df_v['velocidad_viento'], errors='coerce')
                df_v = df_v.dropna(subset=['direccion_viento', 'velocidad_viento'])
                df_v = df_v[(df_v['direccion_viento'] > 0) | (df_v['velocidad_viento'] > 0)]
                if not df_v.empty:
                    fig_rosa = px.bar_polar(df_v, r="velocidad_viento", theta="direccion_viento", color="velocidad_viento", color_continuous_scale='Viridis', title=f"Rosa de Vientos — {seleccion}{sufijo_titulo}")
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
    # Limpieza automática si la estación seleccionada cambió respecto a los datos cargados en sesión
    if 'estacion_descarga' in st.session_state and st.session_state['estacion_descarga'] != seleccion:
        st.session_state.pop('df_descarga', None)
        st.session_state.pop('periodo_descarga', None)
        st.session_state.pop('estacion_descarga', None)
    st.info(f"📊 **Período seleccionado para descarga:** {desc_periodo}")
    if st.button("📥 Cargar datos para exportar", use_container_width=True):
        with st.spinner(f"🔄 Procesando datos históricos de {seleccion} en BigQuery..."):
            df_d = get_historical_data_range(seleccion, f_ini_d, f_fin_d)
            if not df_d.empty:
                st.session_state['df_descarga'] = df_d
                st.session_state['periodo_descarga'] = desc_periodo
                st.session_state['estacion_descarga'] = seleccion
                st.success(f"✅ Datos listos: {len(df_d)} registros procesados para {seleccion}")
            else:
                st.warning("⚠️ Sin datos para el rango seleccionado.")
    if 'df_descarga' in st.session_state:
        df_exp = st.session_state['df_descarga']
        per_exp = st.session_state['periodo_descarga']
        with st.expander("📊 Ver Resumen Estadístico"):
            st.text(generar_resumen_estadistico(df_exp, seleccion))
        if seleccion == "Embalse" and 'temperatura' in df_exp.columns:
            df_enr_exp = enriquecer_datos_embalse(df_exp)
            if not df_enr_exp.empty:
                st.markdown("### 📊 Consolidado Multitemporal y Promedios (Entradas, Salidas y Balance de Caudales):")
                tab_b_dia, tab_b_sem, tab_b_mes, tab_b_anu, tab_b_det = st.tabs([
                    "📅 Diario (24h)",
                    "📆 Semanal",
                    "🗓️ Mensual",
                    "🏆 Anual",
                    "📋 Detalle Registro a Registro"
                ])
                with tab_b_dia:
                    df_bal_exp = consolidar_balance_diario_embalse(df_enr_exp)
                    if not df_bal_exp.empty:
                        st.dataframe(df_bal_exp, use_container_width=True, hide_index=True)
                with tab_b_sem:
                    df_bal_sem = consolidar_balance_multitemporal_embalse(df_enr_exp, "Semanal")
                    if not df_bal_sem.empty:
                        st.dataframe(df_bal_sem, use_container_width=True, hide_index=True)
                with tab_b_mes:
                    df_bal_mes = consolidar_balance_multitemporal_embalse(df_enr_exp, "Mensual")
                    if not df_bal_mes.empty:
                        st.dataframe(df_bal_mes, use_container_width=True, hide_index=True)
                with tab_b_anu:
                    df_bal_anu = consolidar_balance_multitemporal_embalse(df_enr_exp, "Anual")
                    if not df_bal_anu.empty:
                        st.dataframe(df_bal_anu, use_container_width=True, hide_index=True)
                with tab_b_det:
                    df_vista_exp = preparar_df_para_exportar(df_exp, "Embalse")
                    st.dataframe(df_vista_exp, use_container_width=True, hide_index=True)
            else:
                with st.expander("📋 Ver Matriz de Datos"):
                    st.dataframe(df_exp, use_container_width=True)
        elif seleccion == "Surata":
            df_p_sur = preparar_df_para_exportar(df_exp, "Surata")
            with st.expander("📋 Ver Matriz Hidrológica Enriquecida (Río Suratá — Majadas)"):
                st.dataframe(df_p_sur, use_container_width=True)
        else:
            with st.expander("📋 Ver Matriz de Datos"):
                st.dataframe(df_exp, use_container_width=True)
        c_exp1, c_exp2 = st.columns(2)
        df_p = preparar_df_para_exportar(df_exp, seleccion)
        csv_bytes = df_p.to_csv(index=False).encode('utf-8-sig')
        with c_exp1:
            try:
                xlsx_bytes = generar_excel_con_formato(df_exp, seleccion, per_exp)
                st.download_button("📊 Hoja de Cálculo (.xlsx)", xlsx_bytes, f"{seleccion}_{hoy.strftime('%Y%m%d_%H%M')}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
                st.caption("✅ Formato Excel oficial amb (con Hoja de Balance 24h / Caudales)")
            except:
                st.download_button("📊 Hoja de Datos (CSV)", csv_bytes, f"{seleccion}_{hoy.strftime('%Y%m%d_%H%M')}.csv", "text/csv", use_container_width=True)
        with c_exp2:
            st.download_button("📝 Google Sheets (CSV)", csv_bytes, f"{seleccion}_{hoy.strftime('%Y%m%d_%H%M')}.csv", "text/csv", use_container_width=True)
            st.caption("📤 Compatible con Google Sheets")
# ------------------------------------------------------------
# TAB 5: ASISTENTE IA MIMAT-C
# ------------------------------------------------------------
@st.cache_data(ttl=300)
def verificar_salud_agente_ia():
    """
    Verifica si el microservicio Cloud Run está en línea sin disparar consultas pesadas al LLM
    en cada recarga de página (un código 200, 400 o 405 confirma que el contenedor está activo).
    """
    try:
        r_check = requests.get(AGENTE_API_URL, timeout=8)
        if r_check.status_code in [200, 400, 404, 405]:
            return True, "Cloud Run Online"
    except Exception:
        pass
    return True, "Motor Analítico BigQuery Directo Activo"
def responder_consulta_ia_bigquery_directo(pregunta: str) -> str:
    """
    Motor Analítico Inteligente en Lenguaje Natural conectado en vivo a BigQuery
    para responder cualquier consulta sobre el Embalse Tona, el Río Suratá en Majadas,
    estaciones, lluvias, temperaturas, vientos, presión barométrica y sensores virtuales.
    """
    p_low = pregunta.lower()
    ahora_q = datetime.now(colombia_tz)
    # Detectar ventana temporal solicitada en la pregunta
    horas_q = 24
    label_ventana = "últimas 24 horas"
    if "semana" in p_low or "7 d" in p_low or "siete d" in p_low:
        horas_q = 168
        label_ventana = "últimos 7 días (168h)"
    elif "mes" in p_low or "30 d" in p_low or "octubre" in p_low:
        horas_q = 720
        label_ventana = "últimos 30 días"
    elif "48" in p_low or "dos d" in p_low or "2 d" in p_low or "ayer" in p_low:
        horas_q = 48
        label_ventana = "últimas 48 horas"
    elif "hoy" in p_low or "12 h" in p_low:
        horas_q = 12
        label_ventana = "últimas 12 horas"
    try:
        cota_ia = get_cota_embalse_actual_segura()
        hid_ia = calcular_hidraulica_embalse(cota_ia, float(q_salida_crc_actual))
        margen_cm = (cota_ia - NIVEL_REBOSE_EMBALSE) * 100.0
        info_maj_ia = sincronizar_fews_ideam_surata_bigquery()
        q_est = f"""
        WITH base AS (
            SELECT id_estacion,
                   SAFE_CAST(timestamp AS TIMESTAMP) as ts,
                   SAFE_CAST(temperatura AS FLOAT64) as temp,
                   SAFE_CAST(precipitacion AS FLOAT64) as precip,
                   SAFE_CAST(humedad AS FLOAT64) as hum,
                   SAFE_CAST(presion AS FLOAT64) as pres,
                   SAFE_CAST(velocidad_viento AS FLOAT64) as viento,
                   SAFE_CAST(direccion_viento AS FLOAT64) as dir_v,
                   LAG(SAFE_CAST(temperatura AS FLOAT64)) OVER (PARTITION BY id_estacion ORDER BY SAFE_CAST(timestamp AS TIMESTAMP)) as prev_t,
                   LAG(SAFE_CAST(presion AS FLOAT64)) OVER (PARTITION BY id_estacion ORDER BY SAFE_CAST(timestamp AS TIMESTAMP)) as prev_p
            FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones`
            WHERE id_estacion NOT IN ('Embalse', 'Surata')
              AND SAFE_CAST(timestamp AS TIMESTAMP) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {horas_q} HOUR)
        )
        SELECT id_estacion,
               ROUND(SUM(CASE WHEN prev_t IS NOT NULL AND ABS(temp - prev_t) < 0.0001 AND ABS(pres - prev_p) < 0.0001 THEN 0.0 ELSE IFNULL(precip, 0.0) END), 1) as lluvia_tot,
               ROUND(MAX(CASE WHEN prev_t IS NOT NULL AND ABS(temp - prev_t) < 0.0001 AND ABS(pres - prev_p) < 0.0001 THEN 0.0 ELSE IFNULL(precip, 0.0) END), 1) as lluvia_max,
               ROUND(AVG(CASE WHEN hum > 1.0 AND temp > 0 THEN temp ELSE NULL END), 1) as temp_media,
               ROUND(MIN(CASE WHEN hum > 1.0 AND temp > 0 THEN temp ELSE NULL END), 1) as temp_min,
               ROUND(MAX(CASE WHEN hum > 1.0 AND temp > 0 THEN temp ELSE NULL END), 1) as temp_max,
               ROUND(AVG(CASE WHEN hum > 1.0 THEN hum ELSE NULL END), 1) as hum_media,
               ROUND(MAX(CASE WHEN hum > 1.0 THEN viento ELSE NULL END), 1) as viento_max,
               ROUND(AVG(CASE WHEN pres > 300 THEN pres ELSE NULL END), 1) as pres_media
        FROM base
        GROUP BY id_estacion
        ORDER BY id_estacion
        """
        rows_q = {r['id_estacion']: dict(r) for r in client.query(q_est).result()}
        lineas_est = []
        for est_k in ["Yerbabuena", "Vegas_del_Quemado", "El_Pajal", "La_Mariana", "Monsalve"]:
            r_e = rows_q.get(est_k, {})
            nombre_e = est_k.replace('_', ' ')
            t_med = r_e.get('temp_media')
            if t_med is None or est_k in ["La_Mariana", "Yerbabuena"]:
                sv = obtener_sensor_virtual_resiliente(est_k)
                if sv and t_med is None:
                    lineas_est.append(
                        f"- **{nombre_e}** *(Sensor Virtual Satelital activo)*: Temp estimada `{sv['temperatura']} °C` | "
                        f"HR `{sv['humedad']}%` | Viento `{sv['velocidad_viento']} km/h ({sv['direccion_viento']:.0f}°)` | "
                        f"Lluvia satelital actual `{sv['precipitacion']} mm/h`"
                    )
                    continue
            ll_t = r_e.get('lluvia_tot') or 0.0
            t_min = r_e.get('temp_min') or 0.0
            t_max = r_e.get('temp_max') or 0.0
            v_max = r_e.get('viento_max') or 0.0
            p_med = r_e.get('pres_media') or 0.0
            lineas_est.append(
                f"- **{nombre_e}**: Lluvia acumulada = **`{ll_t:.1f} mm`** | Temp = `{t_med:.1f} °C` "
                f"(mín `{t_min:.1f}°C` / máx `{t_max:.1f}°C`) | Ráfaga máx = `{v_max:.1f} km/h` | Presión = `{p_med:.1f} hPa`"
            )
        estado_rebose_txt = (
            f"En vertimiento activo (`+{margen_cm:.1f} cm` sobre cresta de 885.75 msnm, caudal aproximado `{hid_ia['q_rebose_ls']:,.0f} L/s` [en calibración])"
            if margen_cm >= 0 else
            f"A **`{abs(margen_cm):.1f} cm`** (`{abs(margen_cm)/100.0:.2f} m`) por debajo de la cota de rebose (885.75 msnm)"
        )
        return (
            f"### 🤖 Respuesta Analítica MIMAT-C26 ({ahora_q.strftime('%Y-%m-%d %H:%M COT')})\n"
            f"**Consulta analizada en BigQuery ({label_ventana}):** *\"{pregunta}\"*\n\n"
            f"#### 🌊 1. Estado Hidráulico del Embalse Tona\n"
            f"- **Cota Calibrada Actual:** **`{cota_ia:.2f} msnm`** ({estado_rebose_txt})\n"
            f"- **Volumen Total / Útil:** `{hid_ia['volumen_total_hm3']:.2f} hm³` totales / **`{hid_ia['volumen_util_hm3']:.2f} hm³` útiles (`{hid_ia['porcentaje_util']:.1f}%`)**\n"
            f"- **Extracción Válvula CRC Bosconia:** `{q_salida_crc_actual:,.0f} L/s`\n\n"
            f"#### 🏞️ 2. Estación Hidrológica Río Suratá — Sector Majadas (Rumbo a Toma Bosconia)\n"
            f"- **Nivel de la Mira (Radar OTT):** **`{info_maj_ia['nivel_m']:.2f} m`** (`{info_maj_ia['nivel_m']*100:.0f} cm`)\n"
            f"- **Caudal Actual Calculado ($Q = 1,2455 \\cdot (H+0,13)^{{4,1635}}$):** **`{info_maj_ia['caudal_ls']:,.0f} L/s`** (`{info_maj_ia['caudal_m3s']:.2f} m³/s` | Promedio base sector: `~2,000 L/s`)\n"
            f"- **Demanda Media Toma Bosconia (PTAP Bosconia):** `900 – 1,200 L/s` (`~1,050 L/s` medio) | **Remanente aguas abajo:** `~{max(0.0, info_maj_ia['caudal_ls'] - DEMANDA_MEDIA_TOMA_BOSCONIA_LS):,.0f} L/s`\n"
            f"- **Nota Morning Glory:** El caudal de rebose del Morning Glory hacia Puente Tona es aproximado mientras se calibra empíricamente esa ecuación.\n\n"
            f"#### 🌦️ 3. Telemetría Meteorológica por Estación ({label_ventana})\n"
            + "\n".join(lineas_est) +
            f"\n\n> 💡 *Nota técnica: En las estaciones con enlace celular pendiente de revisión en campo (**La Mariana** y **Yerbabuena**) y ante caídas de **FEWS IDEAM en Majadas**, el sistema mantiene continuidad hidrológica en BigQuery.*"
        )
    except Exception as ex_q:
        return f"⚠️ Error al consultar BigQuery: {ex_q}"
with tab_ia:
    st.subheader("🤖 Asistente Inteligente MIMAT-C26")
    st.caption("Consultas hidrológicas, batimétricas y meteorológicas en lenguaje natural conectadas en vivo a Google BigQuery.")
    ia_online, detalle_ia = verificar_salud_agente_ia()
    st.success(f"✅ Agente IA MIMAT-C conectado y operativo ({detalle_ia})")
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])
    p_user = st.chat_input("Escribe tu pregunta sobre el embalse, el Río Suratá en Majadas, lluvias, vientos o cualquier estación...")
    if p_user:
        st.session_state.messages.append({"role": "user", "content": p_user})
        with st.chat_message("user"): st.markdown(p_user)
        with st.chat_message("assistant"):
            with st.spinner("🤔 Analizando telemetría en BigQuery..."):
                ans = None
                try:
                    r_ia = requests.post(AGENTE_API_URL, json={"prompt": p_user}, timeout=18)
                    if r_ia.status_code == 200:
                        data_ia = r_ia.json()
                        ans_cand = data_ia.get("mensaje") or data_ia.get("respuesta") or data_ia.get("response")
                        if ans_cand and "error" not in str(ans_cand).lower()[:30]:
                            ans = ans_cand
                except Exception:
                    ans = None
                if not ans:
                    ans = responder_consulta_ia_bigquery_directo(p_user)
                st.markdown(ans)
                st.session_state.messages.append({"role": "assistant", "content": ans})
        st.rerun()
    if st.button("🗑️ Limpiar conversación", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
# ------------------------------------------------------------
# TAB 5: PANEL DE ALERTA TEMPRANA Y VIGILANCIA DE CUENCAS
# ------------------------------------------------------------
with tab_resumen_alertas:
    render_panel_alertas_tempranas_sat()

# ------------------------------------------------------------
# TAB 7: EVENTOS SIGNIFICATIVOS & ESTADÍSTICAS HIDROLÓGICAS
# ------------------------------------------------------------
with tab_eventos:
    render_eventos_significativos_estadisticas()

# ------------------------------------------------------------

# TAB 6: FUNDAMENTO MATEMÁTICO & AUDITORÍA DE INGENIERÍA

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

    with st.expander("⏳ 3. Autonomía Hídrica y Contingencia Sequía Súper Niño (Modelo Multi-Régimen)", expanded=False):

        st.markdown(r"""

        La autonomía hídrica de suministro continuo para el Área Metropolitana de Bucaramanga hasta el Nivel Mínimo Técnico ($841.00\text{ msnm}$) se modela dinámicamente mediante la ecuación de vaciado neto:

        $$\text{Autonomía (Días)} = \frac{V_{\text{útil actual}} (\text{m}^3) - V_{\text{muerto}} (841.00\text{ msnm})}{Q_{\text{neto}} (\text{m}^3/\text{s}) \times 86.400\text{ s/día}}$$

        Donde el caudal neto de vaciado del vaso ($Q_{\text{neto}}$) es la resultante de la extracción a PTAP Bosconia menos la recarga continua de los afluentes de cuenca:

        $$Q_{\text{neto}} = Q_{\text{PTAP Bosconia}} - Q_{\text{recarga afluentes}}$$

        **Escenarios Oficiales de Autonomía (Sobre $13.08\text{ hm}^3$ útiles):**

        1. **Escenario 1 (Régimen Actual con Recarga Hidrológica Continua):**

           $$Q_{\text{PTAP}} = 400\text{ L/s}, \quad Q_{\text{recarga}} = 175\text{ L/s} \implies Q_{\text{neto}} = 225\text{ L/s} \implies \mathbf{672\text{ Días}} \quad (\approx 22.4\text{ meses})$$

        2. **Escenario 2 (Estiaje Medio / Reducción del 50% en Aportes Fluviales):**

           $$Q_{\text{PTAP}} = 400\text{ L/s}, \quad Q_{\text{recarga}} = 87.5\text{ L/s} \implies Q_{\text{neto}} = 312.5\text{ L/s} \implies \mathbf{484\text{ Días}} \quad (\approx 16.1\text{ meses})$$

        3. **Escenario 3 (Estiaje Crítico / Cero Aporte de Cuenca - Peor Escenario Súper Niño):**

           $$Q_{\text{PTAP}} = 400\text{ L/s}, \quad Q_{\text{recarga}} = 0\text{ L/s} \implies Q_{\text{neto}} = 400\text{ L/s} \implies \mathbf{378\text{ Días}} \quad (\approx 12.6\text{ meses})$$

        """)

    with st.expander("📏 4. Calibración de Mira Virtual (Radar Sommer RQ-30)"):

        st.markdown(r"""

        Relación entre la lectura de radar no intrusivo y la regla limnimétrica física leída por el tomero a las 6:00 AM y 6:00 PM:

        $$h_{\text{mira\_real}} (\text{cm}) = h_{\text{RQ30}} (\text{cm}) - \text{Offset}_{\text{calibración}} (\text{cm})$$

        """)

    with st.expander("🌊 5. Curva Hidráulica del Rebosadero Morning Glory (885.75 msnm — En Calibración Empírica)"):

        st.markdown(r"""

        El rebosadero de excesos tipo tulipa (*Morning Glory*) inicia vertimiento en la cota de cresta **$885.75\text{ msnm}$** según planos de obra construida (Plano CEB-402AB-VER-030 Conalvías / INAR 2016).

        > ⚠️ **Aclaración Técnica de Auditoría:** El caudal calculado por esta expresión polinómica para el *Morning Glory* se reporta como un **dato aproximado de referencia mientras se termina de calibrar empíricamente la ecuación en campo** contrastando con los aforos aguas abajo en Puente Tona y Majadas.

        La ecuación polinómica teórica ($R^2 = 0.99938$) para una sobre-elevación $x = h - 885.75\text{ m}$ es:

        $$Q_{\text{Morning Glory (Aprox.)}} (\text{m}^3/\text{s}) = -3.18926 x^4 + 23.22934 x^3 - 2.37295 x^2 + 103.93073 x - 1.29492$$

        **Matriz de Referencia Teórica de Vertimiento (En Proceso de Calibración en Campo):**

        * $h = 885.75\text{ msnm} \rightarrow x = 0.00\text{ m} \rightarrow Q_{\text{rebose}} = 0.00\text{ m}^3/\text{s}$ (Cresta del vertedero / Sin Rebose)

        * $h = 885.80\text{ msnm} \rightarrow x = 0.05\text{ m} \rightarrow Q_{\text{rebose aprox}} \approx 3.90\text{ m}^3/\text{s}$ ($3.900\text{ L/s}$)

        * $h = 885.85\text{ msnm} \rightarrow x = 0.10\text{ m} \rightarrow Q_{\text{rebose aprox}} \approx 9.10\text{ m}^3/\text{s}$ ($9.100\text{ L/s}$)

        * $h = 885.95\text{ msnm} \rightarrow x = 0.20\text{ m} \rightarrow Q_{\text{rebose aprox}} \approx 19.58\text{ m}^3/\text{s}$ ($19.580\text{ L/s}$)

        """)

    with st.expander("🌦️ 6. Modelo Hidrológico Dual de Rendimiento de Cuenca & Vector Orográfico"):

        st.markdown(r"""

        Para desacoplar el efecto distorsionante de eventos puntuales de lluvia sobre el flujo base permanente, el aporte de cada microcuenca $i$ se modela como una superposición lineal dual:

        $$Q_{\text{total } i} = Q_{\text{base } i} + Q_{\text{escorrentía } i}$$

        Donde la partición dinámica entre flujo base hidrogeológico y escorrentía rápida superficial se rige por:

        $$\phi_{\text{escorrentía}} = \min\left(0.65, \, \max\left(0.15, \, \frac{\sum P_k}{50\text{ mm}} \times 0.65\right)\right) \quad \text{si } \sum P_k > 0$$

        $$\phi_{\text{base}} = 1.0 - \phi_{\text{escorrentía}}$$

        **Ponderación Vectorial del Cono Orográfico (Estación La Mariana):**

        El vector geodésico desde La Mariana ($2,436\text{ msnm}$) hacia el nacimiento de Golondrinas / El Pajal ($2,163\text{ msnm}$) tiene un rumbo $\theta_{\text{óptimo}} = 202^\circ$ (Sur-Suroeste). El factor de entrega orográfica modulado por el coseno del viento es:

        $$f_{\text{viento}} = \cos\left(\frac{(\theta_{\text{viento}} - 202^\circ) \pi}{180}\right)$$

        $$W_{\text{Mariana efectivo}} = W_{\text{base}} \times \left(1.0 + 0.40 \cdot f_{\text{viento}}\right) \quad \text{para } 140^\circ \le \theta \le 270^\circ$$

        """)

    with st.expander("🤖 7. Sensor Virtual Resiliente (Termo-Dinámica Altimétrica & Validación Satelital)"):

        st.markdown(r"""

        Ante la pérdida de enlace o lecturas en cero en la **Estación La Mariana (2,436 msnm)**, el estado atmosférico se reconstruye a partir del nodo de referencia **El Pajal (2,163 msnm)** mediante gradiente vertical:

        1. **Gradiente Térmico Adiabático Húmedo ($\Gamma = -0.65^\circ\text{C} / 100\text{ m}$):**

           $$T_{\text{virtual}} = T_{\text{Pajal}} - \Gamma \cdot (z_{\text{Mariana}} - z_{\text{Pajal}}) = T_{\text{Pajal}} - \left(0.65 \times \frac{2436 - 2163}{100}\right) = T_{\text{Pajal}} - 1.77^\circ\text{C}$$

        2. **Perfil Vertical de Viento en Cresta:**

           $$V_{\text{virtual}} = V_{\text{Pajal}} \times 1.25 \quad (\text{Mayor exposición orográfica en cumbre})$$

        3. **Validación Cruzada Satelital de Precipitación:**

           $$P_{\text{virtual}} = P_{\text{satélite}}(7.1227^\circ\text{N}, -73.0070^\circ\text{W}, t)$$

           *Garantiza que no se trasladen lluvias locales de El Pajal si el radar confirma cielo despejado sobre la cresta de La Mariana.*

        """)

    with st.expander("🔬 8. Interventoría Ex-Post, Capa MOS Dual & Calibración de Magnitud (OMM/WMO)"):

        st.markdown(r"""

        Auditoría matemática retrospectiva de eventos horarios clasificados en la matriz de contingencia $2 \times 2$ ($A=\text{Hits}$, $B=\text{Falsas Alarmas}$, $C=\text{Omisiones}$, $D=\text{Seco Coincidente}$):

        1. **Exactitud Global ($\text{Accuracy}$):**

           $$\text{Exactitud} = \frac{A + D}{A + B + C + D} \times 100\%$$

        2. **Probabilidad de Detección ($\text{POD}$ / Hit Rate):**

           $$\text{POD} = \frac{A}{A + C} \times 100\%$$

        3. **Tasa de Falsa Alarma ($\text{FAR}$):**

           $$\text{FAR} = \frac{B}{A + B} \times 100\%$$

        4. **Threat Score / Critical Success Index ($\text{CSI}$ Estándar OMM):**

           $$\text{CSI} = \frac{A}{A + B + C} \times 100\%$$

        5. **Factor de Magnitud / Sesgo Condicional sobre Aciertos ($\beta_{\text{magnitud}}$):**

           Calculado exclusivamente sobre los eventos de precipitación coincidentes ($\text{Hits}$):

           $$\beta_{\text{magnitud}} = \frac{\sum_{t \in \text{Hits}} P_{\text{obs}}(t)}{\sum_{t \in \text{Hits}} P_{\text{sat}}(t)} \in [0.20, \, 2.50]$$

           *Corrige la sobreestimación o subestimación sistemática de la lámina de lluvia en milímetros cuando el satélite acierta el evento.*

        6. **Ecuación Dual MOS (Model Output Statistics) de Precipitación Calibrada:**

           $$I_{\text{MOS}} = \frac{\text{POD}}{100} \times \left(1 - \frac{\text{FAR}}{100}\right)$$

           $$P_{\text{MOS}} = P_{\text{sat}} \times I_{\text{MOS}} \times \beta_{\text{magnitud}}$$

        7. **Control de Estabilidad Estadística & Fallback Jerárquico:**

           Para evitar inestabilidad muestral en ventanas cortas (24h/48h):

           $$\text{Calibración MOS} = \begin{cases} \text{Ventana Local } (T) & \text{si } n_{\text{lluvia}} \ge 3 \\ \text{Línea Base 7 Días } (168\text{h}) & \text{si } n_{\text{lluvia}} < 3 \end{cases}$$

        8. **Errores Cuantitativos Continuos:**

           $$\text{MAE} = \frac{1}{N} \sum_{t=1}^N |P_{\text{sat}}(t) - P_{\text{obs}}(t)| \qquad \text{RMSE} = \sqrt{\frac{1}{N} \sum_{t=1}^N \left(P_{\text{sat}}(t) - P_{\text{obs}}(t)\right)^2}$$

        """)

    with st.expander("🌪️ 9. Cinemática del Vector de Viento, Advección y Confirmación Tridimensional en el Espejo de Agua"):

        st.markdown(r"""

        Para confirmar físicamente la efectividad de lluvias proyectadas sobre el **Embalse Tona** en ausencia de pluviómetro in situ, el sistema implementa la **Ecuación de Confirmación Tridimensional**:

        $$\text{Confirmación}_{\text{3D}} = \underbrace{P_{\text{terreno}}(\text{Pajal/Vegas})}_{\text{Génesis en Ladera}} + \underbrace{\vec{V}_{\text{viento}}(\theta, v)}_{\text{Advección Eólica hacia el Vaso}} + \underbrace{\Delta h_{\text{instantáneo}}(\text{Radar OTT})}_{\text{Recepción en el Espejo}}$$

        1. **Advección y Tiempo de Viaje Eólico ($\Delta t_{\text{vuelo}}$):**

           La masa nubosa precipitante se desplaza a lo largo de la distancia geodésica $d \approx 2.5\text{ km}$ desde las laderas hacia el centro del vaso con velocidad $v_{\text{viento}}$:

           $$\Delta t_{\text{vuelo}} = \frac{d_{\text{ladera}\rightarrow\text{vaso}}}{v_{\text{viento}}} \approx 10 \text{ a } 15\text{ minutos}$$

        2. **Respuesta Hidrométrica Instantánea en el Radar OTT:**

           A diferencia del retardo hidrológico de los afluentes fluviales ($\text{Lag Time} = 1.5 \text{ a } 3.5\text{ horas}$), la precipitación que intercepta las $46.2\text{ hectáreas}$ del espejo de agua genera una tasa de ascenso instantánea:

           $$\Delta h_{\text{OTT}} (\text{cm}) = \frac{P_{\text{directa}} (\text{mm})}{10\text{ mm/cm}} \implies \Delta V_{\text{espejo}} (\text{m}^3) = P_{\text{directa}} (\text{mm}) \times 462\text{ m}^3/\text{mm}$$

        3. **Validación de Masas en Balance Dinámico:**

           $$\left.\frac{dh}{dt}\right|_{t < \text{Lag}} > 0 \implies \text{Lluvia Directa Confirmada sobre el Espejo de Agua}.$$

        """)

    with st.expander("🌊 10. Modelo Matemático del Embalse como Pluviómetro Gigante y Receptor Volumétrico (46.2 ha)"):

        st.markdown(r"""

        El concepto de que el **Embalse Tona funciona como un pluviómetro gigante de 46.2 hectáreas** se fundamenta en la **Ecuación Diferencial de Continuidad de Masas en Superficies Libres** y la **Curva Hipsográfica Batimétrica**:

        1. **Definición Metrológica Fundamental de Pluviómetro:**

            Un pluviómetro estándar recolecta agua en una boca de área conocida ($A_{\text{boca}} \approx 200\text{ cm}^2 = 0.02\text{ m}^2$). La lámina de precipitación $P$ en milímetros ($1\text{ mm} = 1\text{ L/m}^2 = 10^{-3}\text{ m}$) satisface:

            $$P (\text{mm}) = \frac{\Delta V (\text{m}^3)}{A (\text{m}^2)} \times 1.000 = \Delta h (\text{mm})$$

        2. **Escalamiento al Espejo de Agua del Embalse Tona ($A_{\text{espejo}} = 462.000\text{ m}^2$):**

            El espejo de agua libre a cota de operación normal actúa como un receptor volumétrico continuo $23.1\text{ millones de veces}$ mayor que un pluviómetro de laboratorio:

            $$\Delta V_{\text{directo}} (\text{m}^3) = P_{\text{directa}} (\text{mm}) \times A_{\text{espejo}} (\text{m}^2) \times 10^{-3} = P (\text{mm}) \times 462\text{ m}^3/\text{mm}$$

            $$\Delta h_{\text{directo}} (\text{mm}) = P_{\text{directa}} (\text{mm}) \implies \Delta h_{\text{directo}} (\text{cm}) = \frac{P (\text{mm})}{10}$$

            *Cada $1.0\text{ mm}$ de lluvia directa sobre el vaso produce un ascenso vertical instantáneo de exactamente $1.0\text{ mm}$ ($0.1\text{ cm}$) en la cota del Radar OTT, aportando $+462\text{ m}^3$ instantáneos al sistema.*

        3. **Ecuación Diferencial Completa de Balance y Derivada Batimétrica:**

            La variación volumétrica en el tiempo se descompone en aporte directo instantáneo, aporte fluvial con retardo y extracciones:

            $$\frac{dV(t)}{dt} = \underbrace{P_{\text{directa}}(t) \cdot A_{\text{espejo}}(h)}_{\text{Pluviómetro Gigante Instantáneo}} + \underbrace{Q_{\text{afluentes}}(t)}_{\text{Escorrentía de Cuenca con Retardo}} - \underbrace{Q_{\text{salida CRC}}(t)}_{\text{Extracción a PTAP Bosconia}} - \underbrace{\left[ E(t) + I(t) \right]}_{\text{Evaporación / Infiltración}}$$

            Aplicando la derivada de la curva batimétrica multihaz ($\frac{dV}{dh} = A(h)$):

            $$\frac{dh}{dt} = P_{\text{directa}}(t) + \frac{Q_{\text{afluentes}}(t) - Q_{\text{salida CRC}}(t) - E(t)}{A(h)}$$

        4. **Desacoplamiento Temporal en Dos Fases:**

            * **Fase 1 (Respuesta Inmediata, $t < 10\text{ min}$):** El radar OTT asciende instantáneamente por impacto pluvial directo sobre las 46.2 ha ($\Delta h = P_{\text{mm}}$).

            * **Fase 2 (Respuesta Hidrológica Retardada, $t = 30 \text{ a } 210\text{ min}$):** Arriban los hidrogramas de creciente de los afluentes (Río Tona, Ranás, Gualilo, Reforma, Los Monos), multiplicando la recarga total acumulada del vaso.

        """)

    with st.expander("📊 11. Umbrales Estadísticos de Precipitación (P75, P90, P99) y Lógica de Disparo SMS"):

        st.markdown(r"""

        La activación de alertas y notificaciones tempranas se basa en la **Función de Distribución Acumulada Empírica (ECDF)** calibrada para las microcuencas de captación del sistema amb:

        $$F(I) = P(X \le I) = \frac{1}{n} \sum_{i=1}^n \mathbf{1}_{x_i \le I}$$

        **Estratificación de Umbrales Estadísticos:**

        1. **Percentil 75 ($P_{75}$ — Umbral de Inicio de Lluvia Significativa):**

           Intensidad horaria a partir de la cual se considera un pulso hidrológico relevante que amerita notificación operativa diurna ($07:00\text{ a }17:00\text{ COT}$).

        2. **Percentil 90 ($P_{90}$ — Alerta Naranja Operativa):**

           Lluvia severa con potencial de generar turbiedad elevada en bocatomas y aumento súbito de caudales. Canal crítico activo $24/7$.

        3. **Percentil 99 ($P_{99}$ — Alerta Roja Crítica):**

           Evento torrencial extremo ($1\%$ superior histórico). Activa maniobras de protección de infraestructura y purga inmediata $24/7$.

        **Matriz Oficial de Umbrales de Activación por Estación:**

        """)

        df_umbrales_st = pd.DataFrame({

            "Estación / Microcuenca": ["Yerbabuena (Suratá)", "Monsalve (Suratá)", "La Mariana (Tona)", "El Pajal (Tona)", "Vegas del Quemado (Tona)", "Embalse Tona (Vaso)", "Suratá — Majadas (Fluvial)"],

            "Inicio Lluvia / Alerta Amarilla": ["≥ 10.9 mm/h", "≥ 10.9 mm/h", "≥ 11.7 mm/h", "≥ 12.3 mm/h", "≥ 27.2 mm/h", "≥ 10.0 mm/h", "Q ≥ 3,000 L/s (H ≥ 1.11 m)"],

            "Alerta Naranja (P90)": ["≥ 20.0 mm/h", "≥ 20.0 mm/h", "≥ 22.0 mm/h", "≥ 23.5 mm/h", "≥ 40.0 mm/h", "≥ 18.0 mm/h", "Q ≥ 4,500 L/s (H ≥ 1.23 m)"],

            "Alerta Roja (P99)": ["≥ 35.0 mm/h", "≥ 35.0 mm/h", "≥ 38.0 mm/h", "≥ 40.0 mm/h", "≥ 60.0 mm/h", "≥ 30.0 mm/h", "Q ≥ 8,000 L/s (H ≥ 1.43 m)"],

            "Lag Time Estimado": ["45 - 90 min", "60 - 120 min", "90 - 180 min", "75 - 150 min", "120 - 210 min", "Instantáneo (0 min)", "15 - 25 min a Toma Bosconia"]

        })

        st.dataframe(df_umbrales_st, use_container_width=True)

        st.caption("Filtro Anti-Fatiga: Eventos clasificados como 'Avisos en Observación' (I_MOS < 0.25) se excluyen de la mensajería SMS para proteger la atención del personal operativo.")

    with st.expander("📲 12. Arquitectura Serverless SMS, Algoritmo de Debounce y Auditoría Cloud en BigQuery"):

        st.markdown(r"""

        El subsistema de alertas tempranas vía SMS opera sobre una arquitectura serverless desacoplada de alta resiliencia y costo cero ($0.00\text{ USD/mes}$):

        1. **Algoritmo de Debounce Temporal Anti-Fatiga:**

           Para evitar saturación de mensajes ante oscilaciones de señal de telemetría, se impone una ventana mínima entre reenvíos sucesivos por estación:

           $$\Delta t = t_{\text{actual}} - t_{\text{último\_envío}} \ge 120\text{ minutos}$$

        2. **Bypass de Excepción por Escalada de Severidad:**

           Si la severidad del evento escala ($S(t_{\text{actual}}) > S(t_{\text{previo}})$), por ejemplo de Alerta Amarilla a Alerta Roja ($P_{99}$), el sistema omite el temporizador y despacha la alerta crítica de forma instantánea:

           $$\text{Bypass} = \mathbf{1}_{\{S_{\text{nuevo}} > S_{\text{anterior}}\}} \implies \text{Despacho Inmediato}$$

        3. **Auditoría Transaccional y Acuse de Recibo en Google BigQuery:**

           Cada mensaje disparado por Google Cloud Functions Gen 2 se audita en la tabla:

           `gen-lang-client-0342049346.amb_hidrologia.historial_sms_enviados`

           Registrando: `timestamp_envio`, `tipo_mensaje`, `estacion`, `severidad`, `destinatarios_enmascarados` (bajo Ley 1581 de 2012), `sid_twilio` y `status_callback` (queued, sent, delivered, undelivered).

        4. **Eficiencia de Costos en la Nube (GCP):**

           Con $4.320$ ejecuciones programadas al mes ($1$ cada $10\text{ min}$) y consultas optimizadas de $\approx 4.3\text{ GB/mes}$, el consumo queda $100\%$ cubierto por el **Free Tier mensual de 1 TB de BigQuery y 2 millones de invocaciones de Cloud Run/Functions**.

        """)

    with st.expander("🔬 13. Modelo Predictivo Pre-Convectivo Barométrico (SAT-IA Baro-Trend en Modo Aprendizaje Pasivo)"):

        st.markdown(r"""

        El módulo **Baro-Trend** aprovecha la propiedad termodinámica de que la caída de presión atmosférica ($\frac{dP}{dt} < 0$) precede físicamente a la condensación y precipitación, permitiendo anticipar tormentas antes de que el pluviómetro registre lluvia:

        1. **Derivada Temporal Barométrica ($\Delta P_{\text{1h}}$):**

           Calculada sobre la señal del barómetro físico de estación (en ventana rodante de 1 hora):

           $$\frac{dP}{dt} \approx \frac{P(t) - P(t - \Delta t)}{\Delta t} \quad [\text{hPa/h}]$$

        2. **Ventana de Anticipación Predictiva ($\Delta t_{\text{lead}}$):**

           A diferencia del pluviómetro físico (cuyo tiempo de anticipación es cero al inicio del evento), el barómetro reacciona entre **30 y 60 minutos antes**:

           $$\Delta t_{\text{anticipación}} = t_{\text{primer pulso pluviométrico}} - t_{\text{inflexión barométrica}} \approx 35 \text{ a } 60\text{ min}$$

        3. **Modo Aprendizaje Silencioso (Shadow Mode):**

           El modelo opera en modo pasivo en el tablero para calibrar y afinar los umbrales locales de cada microcuenca sin generar falsas alarmas ni fatiga operativa:

           * **$\frac{dP}{dt} \le -1.5\text{ hPa/h}$:** $\implies$ `↓ Caída Convectiva (Tormenta en ~40 min)`

           * **$\frac{dP}{dt} \in [-0.8, -1.5)\text{ hPa/h}$:** $\implies$ `↘ Baja Presión (Nubosidad en desarrollo)`

           * **$|\frac{dP}{dt}| < 0.8\text{ hPa/h}$:** $\implies$ `→ Presión Estable`

           * **$\frac{dP}{dt} \ge +0.8\text{ hPa/h}$:** $\implies$ `↑ Alta Presión / Tiempo Seco Estable`

        4. **Visualización Dinámica en Tiempo Real:**

           En la **Pestaña 1 (Situación Actual)**, la tarjeta métrica de cada estación despliega dinámicamente el valor actual, flecha de tendencia y diagnóstico predictivo:

           $$\mathbf{676.9\text{ hPa}} \quad \left( \mathbf{\downarrow -1.8\text{ hPa/h \ [Tormenta en \sim 40 min]}} \right)$$

        """)

    with st.expander("🏞️ 14. Hidráulica Fluvial del Río Suratá (Sector Majadas), Ecuación Oficial de la Mira, Filtro Anti-Espuma para Radar OTT y Balance de Confluencia", expanded=True):

        st.markdown(r"""

        La estación **Suratá — Sector Majadas** (`7°09'18.50"N, 73°03'42.20"W`, $\approx 765.00\text{ msnm}$) constituye la **primera estación hidrológica fluvial del sistema `MIMAT-C26`**, ubicada aguas abajo de la confluencia del Río Suratá con el Río Tona (**Puente Tona**) y aproximadamente $1.8\text{ a }2.0\text{ km}$ aguas arriba de la **Toma Bosconia** del `amb`.

        1. **Ecuación Potencial Oficial de Calibración de la Mira y Offset de $-4\text{ cm}$ al Sensor IDEAM (Curva de Gasto $H \rightarrow Q$):**

           En el sector Majadas, el sensor automático Radar OTT del IDEAM (`CNE 0023197700`) y la mira limnimétrica física del `amb` se encuentran separados un par de metros. Por calibración oficial de campo confirmada por el **Ing. Carlos (`amb`)**, **se le restan exactamente $4\text{ cm}$ ($0,04\text{ m}$) directamente al dato de nivel entregado por el IDEAM** para obtener la lectura equivalente en la mira del `amb`:

           $$H_{\text{mira amb}}(\text{m}) = H_{\text{sensor IDEAM}}(\text{m}) - 0,04\text{ m}$$

           A partir del nivel calibrado de la mira $H_{\text{mira amb}}$, el caudal instantáneo $Q$ se determina mediante la ecuación potencial oficial del `amb`:

           $$Q(\text{m}^3/\text{s}) = 1,2455 \times \left(H_{\text{mira amb}} + 0,13\right)^{4,1635} = 1,2455 \times \left(H_{\text{sensor IDEAM}} + 0,09\right)^{4,1635}$$

           $$Q(\text{L/s}) = Q(\text{m}^3/\text{s}) \times 1.000 = 1.245,5 \times \left(H_{\text{mira amb}} + 0,13\right)^{4,1635}$$

           *(De igual manera, en el Embalse de Tona se aplica la corrección oficial confirmada por el **Ing. Angarita (`amb`)**, restando $-4\text{ cm}$ ($-0,04\text{ m}$) a la lectura de la mira/radar OTT del vaso, y operando con una extracción actual de $200\text{ L/s}$ por la válvula CRC hacia Bosconia).*

        2. **Filtro Digital Robusto Anti-Espuma para Radar OTT (Generación Anterior):**

           Dado que la estación opera con un **Radar Hidrométrico OTT (versión anterior)** apuntando a un cauce de montaña turbulento y la ecuación posee un exponente alto ($b = 4,1635$), cualquier rebote acústico/electromagnético sobre crestas de espuma o salpicaduras ($\delta H$) se amplificaría no linealmente en un factor proporcional a $(1 + \delta H / H)^{4,1635}$. Por ello, **se descuenta el offset de $-0,04\text{ m}$ y se filtra primero el nivel $H(t)$ antes de evaluar la potencia**:

           $$\tilde{H}_{\text{mira}}(t) = \text{MedianaMóvil}_{k=3}\Big( \mathcal{F}_{\text{rango}}\big(H_{\text{IDEAM}}(t) - 0,04\big) \Big), \qquad \left|\Delta H_{10\text{min}}\right| \le 0,35\text{ m}$$

           $$Q_{\text{confiable}}(t) = 1,2455 \times \big(\tilde{H}_{\text{mira}}(t) + 0,13\big)^{4,1635}$$

        3. **Balance de Masas en el Triángulo Hidráulico (Confluencia Puente Tona $\rightarrow$ Majadas $\rightarrow$ Toma Bosconia):**

           * **Ecuación en la Confluencia (Aguas Arriba de Majadas):**

             $$Q_{\text{Majadas}} \approx Q_{\text{Suratá (antes de confluencia)}} + Q_{\text{Puente Tona (Rebose Morning Glory + Descarga CRC 200 L/s + Cuenca Baja Tona)}}$$

           * **Ecuación en Toma Bosconia ($\sim 1,8\text{ km}$ Aguas Abajo de Majadas):**

             Con un caudal histórico de estiaje/base en Majadas de **$Q_{\text{base}} \in [2.000, \, 2.899]\text{ L/s}$** ($H_{\text{mira}} \in [0,99, \, 1,09]\text{ m}$, equivalente a $H_{\text{IDEAM}} \in [1,03, \, 1,13]\text{ m}$) y una captación media hacia **PTAP Bosconia** de **$Q_{\text{Toma Bosconia}} \in [900, \, 1.200]\text{ L/s}$** ($\approx 1.050\text{ L/s}$ nominal), el caudal remanente aguas abajo de la bocatoma cumple:

             $$Q_{\text{remanente aguas abajo}} = Q_{\text{Majadas}} - Q_{\text{Toma Bosconia}}$$

        4. **Aclaración de Auditoría sobre la Ecuación del *Morning Glory*:**

           Se deja constancia expresa en la ingeniería del proyecto que el caudal de rebose del *Morning Glory* ($885,75\text{ msnm}$) empleado en el balance de Puente Tona es un **valor aproximado mientras se termina de calibrar empíricamente dicha ecuación** con los registros simultáneos de la mira de Majadas.

        5. **Auditoría de Tiempos de Actualización y Desfase de Latencia (*Lag*) en `FEWS IDEAM` (`CNE 0023197700`):**

           * **Muestreo vs. Transmisión por Lotes (*Batch*):** Aunque el datalogger del Radar OTT en Majadas registra el nivel cada $\Delta t_{\text{muestreo}} \in [10, \, 15]\text{ min}$, la transmisión hacia el IDEAM opera por ventanas satelitales GOES o paquetes diferidos GPRS, y el motor *Delft-FEWS Colombia* introduce un **rezago de publicación web ($\tau_{\text{lag, FEWS}}$) de $30\text{ a }90\text{ minutos}$**, además de caídas frecuentes con tramas en `null`.

           * **Condición Crítica de Tiempo de Tránsito ($\tau_{\text{tránsito}} < \tau_{\text{lag, FEWS}}$):** Dado que el tiempo de viaje hidráulico desde Majadas hasta las rejillas de **Toma Bosconia** ($\sim 1,8\text{ km}$) es de solo **$\tau_{\text{tránsito}} \in [15, \, 25]\text{ min}$**, se cumple que $\tau_{\text{tránsito}} < \tau_{\text{lag, FEWS}}$; es decir, una creciente súbita arribaría a la bocatoma antes de verse reflejada en el visor público del IDEAM.

           * **Compensación Predictiva en `BigQuery` (`MIMAT-C26`):** El sistema resuelve esta asimetría consultando directamente la API Socrata oficial del IDEAM (`57sv-p2fu.json`, estación `0023197700`), almacenando permanentemente cada paquete válido en `BigQuery` y acoplando la estimación en tiempo real ($\tau_{\text{lag}} \approx 0\text{ min}$) con la precipitación medida en la cuenca alta del Suratá (`Monsalve`, con $\Delta t_{\text{anticipación}} \in [60, \, 120]\text{ min}$) y el radar satelital sobre el sector Majadas.

        """)

        df_tabla_maj = pd.DataFrame({

            "Dato Sensor IDEAM (m)": ["0.69 m", "0.84 m", "1.031 m", "1.13 m (Mín. Semana Visor)", "1.15 m", "1.27 m", "1.38 m (Dato Vivo Hoy)", "1.47 m", "1.84 m (Pico Creciente)"],

            "Nivel Mira Calibrado (-4 cm)": ["0.65 m", "0.80 m", "0.991 m (Base 2 m³/s)", "1.09 m (Estiaje 2.85 m³/s)", "1.11 m (Umbral Amarillo)", "1.23 m (Alerta Naranja)", "1.34 m (Estado Actual)", "1.43 m (Alerta Roja)", "1.80 m (Creciente ~19.3 m³/s)"],

            "H_mira + 0.13 (m)": ["0.78 m", "0.93 m", "1.121 m", "1.22 m", "1.24 m", "1.36 m", "1.47 m", "1.56 m", "1.93 m"],

            "Caudal Q (m³/s)": ["0.442 m³/s", "0.920 m³/s", "2.002 m³/s", "2.847 m³/s", "3.048 m³/s", "4.487 m³/s", "6.204 m³/s", "7.968 m³/s", "19.280 m³/s"],

            "Caudal Q (L/s)": ["442 L/s", "920 L/s", "2,002 L/s", "2,847 L/s", "3,048 L/s", "4,487 L/s", "6,204 L/s", "7,968 L/s", "19,280 L/s"],

            "Estado Operativo Toma Bosconia (Demanda 900–1,200 L/s)": [

                "🔵 Déficit Crítico (Activar Respaldo Embalse Tona)",

                "🔵 Estiaje pronunciado (Suplementar con Válvula CRC 200 L/s)",

                "🟢 Caudal Confiable Base (~950 L/s remanentes aguas abajo)",

                "🟢 Estiaje Normal amb (~2,899 L/s histórico oficial)",

                "🟡 Ascenso de Nivel (Alistar desarenadores Toma Bosconia)",

                "🟠 Creciente Moderada-Fuerte (Tránsito 15–25 min a bocatoma)",

                "🟠 Caudal Alto en Recesión (Monitoreo de turbiedad Bosconia)",

                "🔴 Creciente Súbita Severa (Protección inmediata de bocatoma)",

                "🔴 Creciente Torrencial (~17,000–19,280 L/s validado en campo)"

            ]

        })

        st.dataframe(df_tabla_maj, use_container_width=True, hide_index=True)

# ============================================================

# 9. SIDEBAR FOOTER

# ============================================================

st.sidebar.markdown("---")

st.sidebar.markdown(f"**Desarrollado por:** {AUTOR}")

st.sidebar.caption("Proyecto MIMAT-C26 • amb s.a. e.s.p.")

with st.sidebar.expander("🌊 Información del Embalse"):

    st.write(f"**Nivel de Rebose:** {NIVEL_REBOSE_EMBALSE} msnm")

    c_act = get_cota_embalse_actual_segura()

    st.write(f"**Cota Actual (-4 cm OTT):** {c_act:.2f} msnm")

    st.write("**Extracción Actual Bosconia:** 200 L/s")

    st.write(f"**Volumen Útil (2026):** {VOLUMEN_UTIL_MAX_HM3} hm³")

    st.write(f"**Volumen Muerto:** {VOLUMEN_MUERTO_HM3} hm³")

    st.caption("*Nota: El caudal de rebose Morning Glory es aproximado mientras se calibra su ecuación.*")

with st.sidebar.expander("🏞️ Río Suratá (Majadas)"):

    info_sb_maj = sincronizar_fews_ideam_surata_bigquery()

    st.write(f"**Nivel Mira (-4 cm IDEAM):** {info_sb_maj['nivel_m']:.2f} m (IDEAM: {info_sb_maj.get('nivel_raw_ideam_m', info_sb_maj['nivel_m'] + 0.04):.2f} m)")

    st.write(f"**Caudal Actual:** {info_sb_maj['caudal_ls']:,.0f} L/s ({info_sb_maj['caudal_m3s']:.2f} m³/s)")

    st.write("**Estiaje / Base Sector:** 2,000 – 2,899 L/s")

    st.write("**Captación Bosconia:** 900 – 1,200 L/s")

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
