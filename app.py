import functions_framework
import json
import logging
from datetime import datetime, timedelta
from google.cloud import bigquery
from flask import Flask, request, jsonify
import os
import re
import unicodedata
import calendar
import pandas as pd

# ============================================================
# CONFIGURACIÓN BIGQUERY
# ============================================================
client = bigquery.Client()
TABLE_SCADA = "gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones"
TABLE_HISTORICA = "gen-lang-client-0342049346.amb_hidrologia.vista_unificada_agente"

# ============================================================
# MAPEO DE ESTACIONES
# ============================================================
MAPEO_HISTORICO = {
    "El_Pajal": "EL_PAJAL",
    "La_Mariana": "LA_MARIANA",
    "Yerbabuena": "TONA_IDEAM",
    "Vegas_del_Quemado": "MARTIN_GIL",
    "Monsalve": None,
    "Embalse": None
}

ESTACIONES_IMPACTO_EMBALSE = ["El_Pajal", "Yerbabuena", "Vegas_del_Quemado"]

ENTIDADES = {
    "la mariana": {
        "canonico": "La_Mariana",
        "tags": ["la mariana", "la_mariana", "mariana"],
        "cuenca": "Río Frío",
        "afecta": "Río Frío"
    },
    "el pajal": {
        "canonico": "El_Pajal",
        "tags": ["el pajal", "el_pajal", "pajal"],
        "cuenca": "Golondrinas",
        "afecta": "Río Tona"
    },
    "yerbabuena": {
        "canonico": "Yerbabuena",
        "tags": ["yerbabuena", "yerba buena"],
        "cuenca": "Carrizal",
        "afecta": "Río Tona"
    },
    "vegas": {
        "canonico": "Vegas_del_Quemado",
        "tags": ["vegas", "vegas del quemado", "vegas_del_quemado", "quemado"],
        "cuenca": "Arnania",
        "afecta": "Río Tona"
    },
    "monsalve": {
        "canonico": "Monsalve",
        "tags": ["monsalve"],
        "cuenca": "Suratá",
        "afecta": "Río Suratá (nacimiento)"
    },
    "embalse": {
        "canonico": "Embalse",
        "tags": ["embalse", "represa"],
        "cuenca": "Embalse",
        "afecta": "Río Suratá (Puente Tona)"
    }
}

# ============================================================
# FUNCIONES PARA INGESTA (TUS FUNCIONES EXISTENTES)
# ============================================================
def safe_float(val):
    try:
        if val is None or val == "": 
            return 0.0
        return float(val)
    except:
        return 0.0

# ============================================================
# FUNCIONES PARA AGENTE IA
# ============================================================
def normalizar(texto):
    if not texto:
        return ""
    texto = texto.lower()
    texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('ascii')
    return texto

def encontrar_estacion_inteligente(prompt):
    prompt_norm = normalizar(prompt)
    
    for key, entidad in ENTIDADES.items():
        if key in prompt_norm:
            return entidad["canonico"], entidad
    
    for key, entidad in ENTIDADES.items():
        tags = entidad.get("tags", [])
        for tag in tags:
            if tag in prompt_norm:
                return entidad["canonico"], entidad
    
    return None, None

def extraer_fechas_avanzado(prompt):
    prompt_lower = prompt.lower()
    hoy = datetime.now()
    
    meses = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
        'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
        'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
    }
    
    def validar_fecha(año, mes, dia):
        if año < 2004 or año > 2025:
            return "fuera_rango"
        if mes < 1 or mes > 12:
            return None
        ultimo_dia = calendar.monthrange(año, mes)[1]
        if dia < 1 or dia > ultimo_dia:
            return None
        return f"{año:04d}-{mes:02d}-{dia:02d}"
    
    for mes_nombre, mes_num in meses.items():
        patron_con_año = r'\b(\d{1,2})\s+(?:de\s+)?' + mes_nombre + r'\s+(?:de\s+)?(20\d{2})\b'
        match = re.search(patron_con_año, prompt_lower)
        if match:
            dia = int(match.group(1))
            año = int(match.group(2))
            fecha = validar_fecha(año, mes_num, dia)
            if fecha and fecha != "fuera_rango":
                return {"tipo": "fecha_especifica", "fecha_inicio": fecha, "fecha_fin": fecha}
        
        patron_sin_año = r'\b(\d{1,2})\s+(?:de\s+)?' + mes_nombre + r'\b'
        if not re.search(patron_con_año, prompt_lower):
            match = re.search(patron_sin_año, prompt_lower)
            if match:
                dia = int(match.group(1))
                año = hoy.year
                fecha = validar_fecha(año, mes_num, dia)
                if fecha and fecha != "fuera_rango":
                    return {"tipo": "fecha_especifica", "fecha_inicio": fecha, "fecha_fin": fecha}
    
    if "hoy" in prompt_lower:
        fecha = hoy.strftime('%Y-%m-%d')
        return {"tipo": "hoy", "fecha_inicio": fecha, "fecha_fin": fecha}
    
    if "ayer" in prompt_lower:
        fecha = (hoy - timedelta(days=1)).strftime('%Y-%m-%d')
        return {"tipo": "ayer", "fecha_inicio": fecha, "fecha_fin": fecha}
    
    match_dias = re.search(r'últimos?\s+(\d+)\s+días?', prompt_lower)
    if match_dias:
        n = int(match_dias.group(1))
        fecha_fin = hoy.strftime('%Y-%m-%d')
        fecha_inicio = (hoy - timedelta(days=n)).strftime('%Y-%m-%d')
        return {"tipo": "dias", "cantidad": n, "fecha_inicio": fecha_inicio, "fecha_fin": fecha_fin}
    
    return {"tipo": "default", "cantidad": 30, 
            "fecha_inicio": (hoy - timedelta(days=30)).strftime('%Y-%m-%d'), 
            "fecha_fin": hoy.strftime('%Y-%m-%d')}

def get_nivel_embalse_actual():
    sql = f"""
        SELECT temperatura as nivel, timestamp
        FROM `{TABLE_SCADA}`
        WHERE id_estacion = 'Embalse'
        ORDER BY timestamp DESC
        LIMIT 1
    """
    try:
        query_job = client.query(sql)
        rows = [{"nivel": row.nivel, "timestamp": str(row.timestamp)} for row in query_job.result()]
        return rows[0] if rows else None
    except Exception as e:
        print(f"Error consultando embalse: {e}")
        return None

def get_nivel_embalse_anterior(horas=24):
    sql = f"""
        SELECT temperatura as nivel, timestamp
        FROM `{TABLE_SCADA}`
        WHERE id_estacion = 'Embalse'
          AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {horas} HOUR)
        ORDER BY timestamp ASC
        LIMIT 1
    """
    try:
        query_job = client.query(sql)
        rows = [{"nivel": row.nivel, "timestamp": str(row.timestamp)} for row in query_job.result()]
        return rows[0] if rows else None
    except Exception as e:
        print(f"Error consultando embalse anterior: {e}")
        return None

def get_lluvia_estacion(estacion, horas=24):
    sql = f"""
        SELECT AVG(precipitacion) as promedio, COUNT(*) as lecturas
        FROM `{TABLE_SCADA}`
        WHERE id_estacion = @estacion
          AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {horas} HOUR)
          AND precipitacion > 0
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("estacion", "STRING", estacion)
        ]
    )
    try:
        query_job = client.query(sql, job_config=job_config)
        rows = [{"promedio": row.promedio, "lecturas": row.lecturas} for row in query_job.result()]
        if rows and rows[0].promedio:
            return {"promedio": round(rows[0].promedio, 4), "lecturas": rows[0].lecturas}
    except Exception as e:
        print(f"Error consultando lluvia en {estacion}: {e}")
    return None

def analizar_impacto_embalse():
    nivel_actual = get_nivel_embalse_actual()
    if not nivel_actual:
        return {"error": "No se pudo obtener el nivel actual del embalse"}
    
    nivel_anterior = get_nivel_embalse_anterior(24)
    if not nivel_anterior:
        return {"error": "No se pudo obtener el nivel anterior del embalse"}
    
    delta = nivel_actual["nivel"] - nivel_anterior["nivel"]
    
    lluvias = {}
    for estacion in ESTACIONES_IMPACTO_EMBALSE:
        lluvia = get_lluvia_estacion(estacion, 24)
        if lluvia and lluvia["promedio"] > 0:
            lluvias[estacion] = lluvia
    
    if delta > 0:
        tendencia = "SUBIDA"
        if lluvias:
            mensaje = f"✅ El nivel subió {delta:.2f} msnm. Lluvias detectadas en: {', '.join(lluvias.keys())}"
        else:
            mensaje = f"⚠️ El nivel subió {delta:.2f} msnm pero no se detectaron lluvias directas."
    elif delta < 0:
        tendencia = "BAJADA"
        mensaje = f"📉 El nivel bajó {abs(delta):.2f} msnm."
    else:
        tendencia = "ESTABLE"
        mensaje = f"➡️ El nivel se mantiene estable en {nivel_actual['nivel']:.2f} msnm."
    
    return {
        "nivel_actual": nivel_actual,
        "nivel_anterior": nivel_anterior,
        "delta": delta,
        "tendencia": tendencia,
        "lluvias": lluvias,
        "mensaje": mensaje
    }

def procesar_consulta_agente(prompt):
    prompt_lower = prompt.lower()
    
    # DETECTAR CONSULTA DE EMBALSE
    if any(word in prompt_lower for word in ["embalse", "nivel del embalse", "rebose", "por qué subió", "por qué bajó"]):
        if "embalse" in prompt_lower or "nivel" in prompt_lower:
            analisis = analizar_impacto_embalse()
            
            if "error" in analisis:
                return {
                    "status": "error",
                    "mensaje": analisis["error"]
                }
            
            mensaje = f"""🌊 ANÁLISIS DE IMPACTO EN EL EMBALSE

📊 Nivel actual: {analisis['nivel_actual']['nivel']:.2f} msnm
📊 Nivel anterior: {analisis['nivel_anterior']['nivel']:.2f} msnm
📈 Diferencia: {analisis['delta']:+.2f} msnm ({analisis['tendencia']})

🌧️ LLUVIAS DETECTADAS (últimas 24h):"""
            
            if analisis["lluvias"]:
                for estacion, datos in analisis["lluvias"].items():
                    mensaje += f"\n✅ {estacion}: {datos['promedio']:.4f} mm ({datos['lecturas']} lecturas) → IMPACTO DIRECTO"
            else:
                mensaje += "\n❌ No se detectaron lluvias en las estaciones de impacto directo."
            
            mensaje += f"""

💡 {analisis['mensaje']}

📍 Estaciones que afectan directamente el embalse:
- El_Pajal (Golondrinas → Río Tona)
- Yerbabuena (Carrizal → Río Tona)  
- Vegas_del_Quemado (Arnania → Río Tona)

📍 Contexto:
- Embalse ubicado en Puente Tona (Río Suratá)
- Estas estaciones aportan al Río Tona que desemboca en el embalse"""
            
            return {
                "status": "ok",
                "estacion": "Embalse",
                "mensaje": mensaje,
                "analisis": analisis
            }
    
    # CONSULTA NORMAL SOBRE ESTACIONES
    variable_deseada = None
    if "caudal" in prompt_lower:
        variable_deseada = "caudal"
    elif "nivel" in prompt_lower:
        variable_deseada = "nivel"
    elif "lluvia" in prompt_lower or "precipitacion" in prompt_lower:
        variable_deseada = "precipitacion"
    elif "temperatura" in prompt_lower or "temp" in prompt_lower:
        variable_deseada = "temperatura"
    elif "humedad" in prompt_lower:
        variable_deseada = "humedad"
    
    estacion, entidad = encontrar_estacion_inteligente(prompt)
    
    if not estacion:
        return {
            "status": "error",
            "mensaje": f"No reconocí la estación en tu consulta. Estaciones disponibles: El_Pajal, La_Mariana, Yerbabuena, Vegas_del_Quemado, Monsalve, Embalse"
        }
    
    if not variable_deseada:
        return {
            "status": "error",
            "mensaje": f"No entendí qué variable quieres consultar. Pregunta por: temperatura, precipitación, humedad o nivel."
        }
    
    periodo = extraer_fechas_avanzado(prompt)
    fecha_inicio = periodo["fecha_inicio"]
    fecha_fin = periodo["fecha_fin"]
    
    columna_map = {
        "temperatura": "temperatura",
        "precipitacion": "precipitacion",
        "humedad": "humedad",
        "nivel": "precipitacion",
        "caudal": "precipitacion"
    }
    columna = columna_map.get(variable_deseada, "precipitacion")
    
    sql_scada = f"""
        SELECT 
            DATE(timestamp) as fecha,
            AVG({columna}) as valor,
            COUNT(*) as lecturas
        FROM `{TABLE_SCADA}`
        WHERE id_estacion = @estacion
          AND DATE(timestamp) BETWEEN @fecha_inicio AND @fecha_fin
        GROUP BY DATE(timestamp)
        ORDER BY fecha DESC
        LIMIT 100
    """
    
    try:
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("estacion", "STRING", estacion),
                bigquery.ScalarQueryParameter("fecha_inicio", "DATE", fecha_inicio),
                bigquery.ScalarQueryParameter("fecha_fin", "DATE", fecha_fin)
            ]
        )
        query_job = client.query(sql_scada, job_config=job_config)
        rows = [{"fecha": str(row.fecha), "valor": row.valor, "lecturas": row.lecturas} for row in query_job.result()]
        
        if rows:
            avg_valor = sum(r["valor"] for r in rows) / len(rows) if rows else 0
            mensaje = f"""📊 **{estacion}** - {variable_deseada.capitalize()}

📅 Período: {fecha_inicio} al {fecha_fin}
📊 Promedio: {avg_valor:.2f}
📋 Registros: {len(rows)}

📈 Datos por fecha:"""
            for row in rows[:10]:
                mensaje += f"\n- {row['fecha']}: {row['valor']:.2f} ({row['lecturas']} lecturas)"
            if len(rows) > 10:
                mensaje += f"\n... y {len(rows) - 10} fechas más"
            
            if entidad:
                if entidad.get("cuenca"):
                    mensaje += f"\n\n📍 Cuenca: {entidad['cuenca']}"
                if entidad.get("afecta"):
                    mensaje += f"\n📍 Afecta: {entidad['afecta']}"
            
            return {
                "status": "ok",
                "estacion": estacion,
                "variable": variable_deseada,
                "mensaje": mensaje,
                "datos": rows
            }
    except Exception as e:
        print(f"Error en consulta SCADA: {e}")
    
    estacion_historica = MAPEO_HISTORICO.get(estacion)
    if estacion_historica:
        sql_historico = f"""
            SELECT 
                DATE(fecha) as fecha,
                AVG(valor) as valor
            FROM `{TABLE_HISTORICA}`
            WHERE estacion = @estacion_historica
              AND variable = @variable
              AND DATE(fecha) BETWEEN @fecha_inicio AND @fecha_fin
            GROUP BY DATE(fecha)
            ORDER BY fecha DESC
            LIMIT 100
        """
        try:
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("estacion_historica", "STRING", estacion_historica),
                    bigquery.ScalarQueryParameter("variable", "STRING", variable_deseada),
                    bigquery.ScalarQueryParameter("fecha_inicio", "DATE", fecha_inicio),
                    bigquery.ScalarQueryParameter("fecha_fin", "DATE", fecha_fin)
                ]
            )
            query_job = client.query(sql_historico, job_config=job_config)
            rows = [{"fecha": str(row.fecha), "valor": row.valor} for row in query_job.result()]
            
            if rows:
                avg_valor = sum(r["valor"] for r in rows) / len(rows) if rows else 0
                mensaje = f"""📜 **{estacion}** - {variable_deseada.capitalize()} (Datos Históricos)

📅 Período: {fecha_inicio} al {fecha_fin}
📊 Promedio histórico: {avg_valor:.2f}
📋 Registros: {len(rows)}

📈 Datos históricos:"""
                for row in rows[:10]:
                    mensaje += f"\n- {row['fecha']}: {row['valor']:.2f}"
                if len(rows) > 10:
                    mensaje += f"\n... y {len(rows) - 10} fechas más"
                
                if entidad:
                    if entidad.get("cuenca"):
                        mensaje += f"\n\n📍 Cuenca: {entidad['cuenca']}"
                    if entidad.get("afecta"):
                        mensaje += f"\n📍 Afecta: {entidad['afecta']}"
                
                return {
                    "status": "ok",
                    "estacion": estacion,
                    "variable": variable_deseada,
                    "fuente": "Históricos",
                    "mensaje": mensaje,
                    "datos": rows
                }
        except Exception as e:
            print(f"Error en consulta histórica: {e}")
    
    return {
        "status": "sin_datos",
        "mensaje": f"No hay datos de {variable_deseada} para {estacion} en el período consultado."
    }

# ============================================================
# CREAR LA APLICACIÓN FLASK
# ============================================================
app = Flask(__name__)

# ============================================================
# ENDPOINT 1: INGESTA DE DATOS (TU CÓDIGO EXISTENTE)
# ============================================================
@app.route('/', methods=['POST'])
def ingestar_estacion():
    if request.method != 'POST':
        return 'Método no permitido', 405

    datos = request.get_json(silent=True)
    if not datos:
        return jsonify({"error": "No se recibió un JSON válido"}), 400

    id_estacion = datos.get('id_estacion', 'DESCONOCIDA')
    
    print(f"DEBUG - Recibido de {id_estacion}: {datos}")

    # FILTRO DE SEGURIDAD (ANTI-DUPLICADOS)
    query_verificar = f"""
        SELECT timestamp FROM `{TABLE_SCADA}`
        WHERE id_estacion = '{id_estacion}'
        ORDER BY timestamp DESC LIMIT 1
    """
    try:
        results = list(client.query(query_verificar).result())
        if len(results) > 0:
            ultimo_ts = datetime.fromisoformat(str(results[0].timestamp))
            if (datetime.utcnow() - ultimo_ts) < timedelta(minutes=9):
                return jsonify({"status": "ignorado", "mensaje": "Frecuencia alta"}), 200
    except Exception as e:
        print(f"Error en filtro de seguridad: {e}")

    # PROCESAMIENTO DE DATOS
    try:
        temp = safe_float(datos.get('temperatura'))
        lluvia = safe_float(datos.get('precipitacion'))
        humedad = safe_float(datos.get('humedad'))
        presion = safe_float(datos.get('presion'))
        viento = safe_float(datos.get('velocidad_viento'))
        bateria = safe_float(datos.get('voltaje_bateria'))
    except Exception as e:
        return jsonify({"error": f"Error de conversión: {str(e)}"}), 400

    estado_bateria = "OK"
    if bateria > 0 and bateria < 11.5:
        estado_bateria = "CRITICO"
    elif bateria > 0 and bateria < 12.0:
        estado_bateria = "ADVERTENCIA"

    fila = [{
        "timestamp": datetime.utcnow().isoformat(),
        "id_estacion": id_estacion,
        "temperatura": temp,
        "precipitacion": lluvia,
        "humedad": humedad,
        "presion": presion,
        "velocidad_viento": viento,
        "voltaje_bateria": bateria,
        "estado_bateria": estado_bateria
    }]

    # INSERCIÓN
    try:
        errores = client.insert_rows_json(TABLE_SCADA, fila)
        if errores == []:
            return jsonify({"status": "exito"}), 200
        else:
            return jsonify({"status": "error", "detalle": str(errores)}), 500
    except Exception as e:
        return jsonify({"status": "error", "detalle": str(e)}), 500

# ============================================================
# ENDPOINT 2: WEBHOOK PARA AGENTE IA
# ============================================================
@app.route('/webhook', methods=['POST'])
def webhook_ia():
    try:
        datos = request.get_json(silent=True)
        if not datos:
            return jsonify({"status": "error", "mensaje": "No se recibieron datos"}), 400
        
        prompt = datos.get('prompt', '')
        if not prompt:
            return jsonify({"status": "error", "mensaje": "No se recibió 'prompt'"}), 400
        
        resultado = procesar_consulta_agente(prompt)
        return jsonify(resultado), 200
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "mensaje": f"Error en el webhook: {str(e)}"
        }), 500

# ============================================================
# ENDPOINT 3: HEALTH CHECK
# ============================================================
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "ok",
        "service": "ingesta-amb-oficial",
        "version": "1.2.0",
        "timestamp": datetime.utcnow().isoformat()
    }), 200

# ============================================================
# ENDPOINT 4: RAIZ (GET) - INFORMACIÓN DEL SERVICIO
# ============================================================
@app.route('/', methods=['GET'])
def root():
    return jsonify({
        "service": "ingesta-amb-oficial",
        "status": "running",
        "endpoints": {
            "POST /": "Ingesta de datos meteorológicos",
            "POST /webhook": "Agente IA para consultas",
            "GET /health": "Health check",
            "GET /": "Información del servicio"
        },
        "version": "1.2.0"
    }), 200

# ============================================================
# PARA EJECUCIÓN LOCAL Y CLOUD RUN
# ============================================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
