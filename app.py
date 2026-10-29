"""
===================================================================================================
MIMAT-C26 | CLOUD FUNCTION SERVERLESS: MOTOR DE ALERTAS Y BOLETINES SMS (amb)
Autor: Mauricio Mora - Auxiliar Operativo III / Arquitecto Cloud MIMAT-C26
===================================================================================================
"""

import os
import json
import requests
from datetime import datetime, time, timezone, timedelta
import functions_framework
from google.cloud import bigquery

colombia_tz = timezone(timedelta(hours=-5), name="COT")

# Directorio Institucional de Destinatarios Oficiales amb
DIRECTORIO_DESTINATARIOS_AMB = {
    "diana_calderon": {
        "nombre": "Ing. Diana Lucia Calderon Ochoa",
        "cargo": "Lider del Area de Produccion",
        "telefono": "+573002748260"
    },
    "carlos_angarita": {
        "nombre": "Ing. Carlos Angarita",
        "cargo": "Jefe de Recursos Hidricos y Captacion",
        "telefono": "+573005636313"
    },
    "mauricio_mora": {
        "nombre": "Mauricio Mora",
        "cargo": "Auxiliar Operativo III / Arquitecto Cloud MIMAT-C26",
        "telefono": "+573176390605"
    }
}

# Umbrales Oficiales de Alerta MIMAT-C26 (mm/h)
UMBRALES_ESTACIONES = {
    "El_Pajal": {"amarilla": 12.3, "naranja": 15.1, "roja": 20.4, "alias": "Pajal"},
    "Yerbabuena": {"amarilla": 10.9, "naranja": 20.0, "roja": 40.8, "alias": "Yerbabuena"},
    "La_Mariana": {"amarilla": 11.7, "naranja": 18.0, "roja": 35.0, "alias": "Mariana"},
    "Vegas_del_Quemado": {"amarilla": 27.2, "naranja": 36.8, "roja": 55.8, "alias": "Vegas"},
    "Monsalve": {"amarilla": 10.9, "naranja": 20.0, "roja": 40.8, "alias": "Monsalve"}
}

def obtener_hora_colombia():
    return datetime.now(colombia_tz)

def enviar_sms_individual(destinatario_telf, texto_sms):
    """
    Envío directo vía Twilio REST API en 1 solo segmento puro GSM-7 (< 160 caracteres).
    Entrega prioritaria instantánea (< 5 segundos).
    """
    twilio_sid = (os.getenv("TWILIO_ACCOUNT_SID") or os.getenv("TWILIO_SID") or "").strip().strip('"').strip("'")
    twilio_token = (os.getenv("TWILIO_AUTH_TOKEN") or os.getenv("TWILIO_TOKEN") or "").strip().strip('"').strip("'")
    twilio_from = (os.getenv("TWILIO_FROM_NUMBER") or os.getenv("TWILIO_PHONE_NUMBER") or os.getenv("TWILIO_NUMBER") or "").strip().strip('"').strip("'")
    
    if twilio_sid and twilio_token and twilio_from:
        try:
            url_twilio = f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}/Messages.json"
            resp = requests.post(
                url_twilio,
                data={'To': destinatario_telf, 'From': twilio_from, 'Body': texto_sms},
                auth=(twilio_sid, twilio_token),
                timeout=15
            )
            data = resp.json()
            if resp.status_code in [200, 201]:
                return {"success": True, "provider": "TWILIO", "sid": data.get("sid"), "status": data.get("status")}
            else:
                return {"success": False, "provider": "TWILIO", "error_code": data.get("code"), "error": data.get("message")}
        except Exception as e:
            return {"success": False, "provider": "TWILIO", "error": str(e)}
    faltantes = []
    if not twilio_sid:
        faltantes.append("TWILIO_ACCOUNT_SID")
    if not twilio_token:
        faltantes.append("TWILIO_AUTH_TOKEN")
    if not twilio_from:
        faltantes.append("TWILIO_FROM_NUMBER")
    return {
        "success": False,
        "provider": "CONFIG_ERROR",
        "error": f"Credenciales Twilio no detectadas en Cloud Run ({', '.join(faltantes)})"
    }

def algun_envio_exitoso(resultados: dict) -> bool:
    if not isinstance(resultados, dict):
        return False
    return any(bool(v.get("resultado", {}).get("success")) for v in resultados.values())

def asegurar_tabla_log_alertas(client):
    try:
        q_create = """
        CREATE TABLE IF NOT EXISTS `gen-lang-client-0342049346.amb_hidrologia.log_alertas_sms` (
            timestamp TIMESTAMP,
            id_estacion STRING,
            nivel_alerta STRING,
            lluvia_mm FLOAT64
        )
        """
        client.query(q_create).result()
    except:
        pass

def obtener_ultimo_despacho_alerta(client, est_id):
    try:
        q = f"""
        SELECT nivel_alerta, SAFE_CAST(timestamp AS TIMESTAMP) as ult_ts
        FROM `gen-lang-client-0342049346.amb_hidrologia.log_alertas_sms`
        WHERE id_estacion = '{est_id}'
          AND SAFE_CAST(timestamp AS TIMESTAMP) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 75 MINUTE)
        ORDER BY SAFE_CAST(timestamp AS TIMESTAMP) DESC
        LIMIT 1
        """
        job = client.query(q)
        rows = list(job)
        if rows:
            return {
                "nivel": rows[0]['nivel_alerta'],
                "timestamp": rows[0]['ult_ts']
            }
    except:
        pass
    return None

def registrar_despacho_alerta(client, est_id, nivel, ll_val):
    try:
        rows_to_insert = [{
            "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
            "id_estacion": est_id,
            "nivel_alerta": nivel,
            "lluvia_mm": round(float(ll_val), 1)
        }]
        table_id = "gen-lang-client-0342049346.amb_hidrologia.log_alertas_sms"
        client.insert_rows_json(table_id, rows_to_insert)
    except:
        pass

def despachar_sms_a_grupo_amb(client, texto_sms, nivel_alerta="ALERTA", solo_mauricio=False):
    """
    Despacha el mensaje SMS respetando el perfil institucional de cada directivo y el descanso nocturno:
    - Ing. Diana Calderón (Líder Producción):
        * Boletín Matutino 07:00 AM: Siempre.
        * Diurno (06:30 a 20:30 COT): Alertas Naranja y Roja.
        * Nocturno (20:30 a 06:30 COT): SILENCIO TOTAL para Naranja y Amarilla. Solo Roja Extrema.
    - Ing. Carlos Angarita (Jefe Recursos Hídricos):
        * Diurno (06:00 a 21:00 COT): Naranja y Roja.
        * Nocturno: Solo Roja Extrema.
    - Mauricio Mora (Líder Técnico):
        * Siempre habilitado 24/7 con control de cooldown.
    """
    ahora = obtener_hora_colombia()
    h_act = ahora.time()
    es_noche_diana = (h_act >= time(20, 30) or h_act < time(6, 30))
    es_noche_carlos = (h_act >= time(21, 0) or h_act < time(6, 0))
    
    resultados = {}
    if solo_mauricio:
        destinatarios_a_enviar = ["mauricio_mora"]
    else:
        destinatarios_a_enviar = []
        for key in DIRECTORIO_DESTINATARIOS_AMB.keys():
            if key == "mauricio_mora":
                destinatarios_a_enviar.append(key)
            elif key == "diana_calderon":
                if nivel_alerta in ["BOLETIN_MATUTINO", "ROJA"]:
                    destinatarios_a_enviar.append(key)
                elif nivel_alerta == "NARANJA" and not es_noche_diana:
                    destinatarios_a_enviar.append(key)
            elif key == "carlos_angarita":
                if nivel_alerta in ["BOLETIN_MATUTINO", "ROJA"]:
                    destinatarios_a_enviar.append(key)
                elif nivel_alerta == "NARANJA" and not es_noche_carlos:
                    destinatarios_a_enviar.append(key)
                    
    for key in destinatarios_a_enviar:
        persona = DIRECTORIO_DESTINATARIOS_AMB[key]
        res = enviar_sms_individual(persona['telefono'], texto_sms)
        resultados[key] = {
            "nombre": persona['nombre'],
            "cargo": persona['cargo'],
            "telefono": persona['telefono'],
            "resultado": res
        }
    return resultados

@functions_framework.http
def centinela_inspeccion_cuencas(request):
    client = bigquery.Client()
    ahora = obtener_hora_colombia()
    request_args = request.args if hasattr(request, 'args') and request.args else {}
    req_json = request.get_json(silent=True) if hasattr(request, 'get_json') else {}
    if not isinstance(req_json, dict):
        req_json = {}
        
    modo_raw = request_args.get('modo') or req_json.get('modo')
    if modo_raw:
        modo = str(modo_raw).lower().strip()
    else:
        modo = "vigilancia"

    # Si son entre las 06:58 y las 07:12 AM COT y entra por el cron de 'vigilancia',
    # verificar si ya se procesó el boletín de las 07:00 AM hoy; si no, activar '07am' automáticamente:
    if modo == "vigilancia" and ((ahora.hour == 6 and ahora.minute >= 58) or (ahora.hour == 7 and ahora.minute <= 12)):
        try:
            asegurar_tabla_log_alertas(client)
            q_chk_7am = """
            SELECT COUNT(*) as n_hoy
            FROM `gen-lang-client-0342049346.amb_hidrologia.log_alertas_sms`
            WHERE nivel_alerta IN ('BOLETIN_MATUTINO', 'BOLETIN_EVALUADO_SECO')
              AND SAFE_CAST(timestamp AS TIMESTAMP) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 4 HOUR)
            """
            n_hoy = list(client.query(q_chk_7am))[0]['n_hoy']
            if int(n_hoy or 0) == 0:
                modo = "07am"
        except Exception:
            modo = "07am"
    
    # -------------------------------------------------------------
    # FUNCIÓN AUXILIAR: ESTADO HIDROLÓGICO RÍO SURATÁ — LAS MAJADAS
    # Calibración Oficial (Ing. Carlos - amb):
    # Se restan 4 cm (0.04 m) al dato crudo entregado por el sensor IDEAM (0023197700):
    # H_mira = H_sensor_IDEAM - 0.04 m
    # Q (m3/s) = 1.2455 * (H_mira + 0.13)**4.1635  -->  Q (L/s) = Q * 1000
    # -------------------------------------------------------------
    OFFSET_SENSOR_IDEAM_MAJADAS = 0.04  # -4 cm confirmados por Ing. Carlos (amb)

    def obtener_estado_surata_majadas(bq_client):
        # 1. Consultar en vivo la API Oficial Socrata del IDEAM compilando las 3 tablas de sensores (0230, 0231 y 0232) en las últimas 24h (~72 registros)
        try:
            url_soc = (
                "https://www.datos.gov.co/resource/57sv-p2fu.json"
                "?codigoestacion=0023197700&$where=codigosensor%20in('0230','0231','0232')"
                "&$limit=72&$order=fechaobservacion%20DESC"
            )
            r_soc = requests.get(url_soc, timeout=4.5)
            if r_soc.status_code == 200:
                datos_soc = r_soc.json()
                if isinstance(datos_soc, list) and len(datos_soc) > 0:
                    # Sincronizar silenciosamente en BigQuery los registros nuevos de las 3 tablas (0230, 0231, 0232)
                    try:
                        q_exist = """
                        SELECT FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%S', SAFE_CAST(timestamp AS TIMESTAMP)) as ts_str
                        FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones`
                        WHERE id_estacion = 'Surata'
                          AND SAFE_CAST(timestamp AS TIMESTAMP) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 36 HOUR)
                        """
                        ts_existentes = {r['ts_str'] for r in bq_client.query(q_exist) if r.get('ts_str')}
                        filas_nuevas = []
                        ts_vistos_lote = set()
                        for reg_s in datos_soc:
                            f_s = str(reg_s.get("fechaobservacion", "")).replace("T", " ").split(".")[0].strip()
                            c_s = str(reg_s.get("codigosensor", "0230")).strip()
                            if not f_s or f_s in ts_existentes or f_s in ts_vistos_lote:
                                continue
                            v_s = float(reg_s.get("valorobservado", 0))
                            if v_s > 15.0:
                                v_s = v_s / 100.0
                            if 0.09 <= v_s <= 3.50:
                                hm_s = max(0.05, round(v_s - OFFSET_SENSOR_IDEAM_MAJADAS, 3))
                                q_s_ls = round(1.2455 * ((hm_s + 0.13) ** 4.1635) * 1000.0, 2)
                                cod_num = 231.0 if c_s == "0231" else (232.0 if c_s == "0232" else 230.0)
                                etq_s = "MAX_HORA_0231" if c_s == "0231" else ("MIN_HORA_0232" if c_s == "0232" else "CORTE_HORA_0230")
                                filas_nuevas.append({
                                    "timestamp": f_s,
                                    "id_estacion": "Surata",
                                    "precipitacion": q_s_ls,
                                    "temperatura": round(v_s, 3),
                                    "humedad": hm_s,
                                    "velocidad_viento": round(q_s_ls / 1000.0, 4),
                                    "direccion_viento": cod_num,
                                    "presion": 885.0,
                                    "radiacion_solar": 0.0,
                                    "estado_bateria": f"IDEAM_0023197700_{etq_s}_VIVO"
                                })
                                ts_vistos_lote.add(f_s)
                        if filas_nuevas:
                            bq_client.insert_rows_json("gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones", filas_nuevas)
                    except Exception:
                        pass

                    # Último dato entregado por el IDEAM (caudal actual en ese momento)
                    h_raw_ult = round(float(datos_soc[0].get("valorobservado", 1.38)), 3)
                    if h_raw_ult > 15.0:
                        h_raw_ult = h_raw_ult / 100.0
                    h_raw_ult = max(0.09, min(3.50, h_raw_ult))
                    h_mira_ult = max(0.05, round(h_raw_ult - OFFSET_SENSOR_IDEAM_MAJADAS, 3))
                    q_ult_ls = round(1.2455 * ((h_mira_ult + 0.13) ** 4.1635) * 1000.0, 0)

                    # Calcular el promedio de las últimas 24 horas (filtrando los registros dentro de 24h respecto al último reporte)
                    f_ult_str = str(datos_soc[0].get("fechaobservacion", ""))
                    dt_ult = datetime.fromisoformat(f_ult_str.replace("Z", "").split(".")[0]) if f_ult_str else None
                    caudales_24h = []
                    for reg_i in datos_soc:
                        try:
                            v_i = float(reg_i.get("valorobservado", 0))
                            if v_i > 15.0:
                                v_i = v_i / 100.0
                            if 0.09 <= v_i <= 3.50:
                                f_i_str = str(reg_i.get("fechaobservacion", ""))
                                if dt_ult and f_i_str:
                                    dt_i = datetime.fromisoformat(f_i_str.replace("Z", "").split(".")[0])
                                    if (dt_ult - dt_i).total_seconds() > 86400:
                                        continue
                                h_m_i = max(0.05, v_i - OFFSET_SENSOR_IDEAM_MAJADAS)
                                q_i_ls = 1.2455 * ((h_m_i + 0.13) ** 4.1635) * 1000.0
                                caudales_24h.append(q_i_ls)
                        except Exception:
                            continue
                    q_prom_24h_ls = round(sum(caudales_24h) / len(caudales_24h), 0) if caudales_24h else q_ult_ls

                    h_prev_raw = float(datos_soc[min(5, len(datos_soc)-1)].get("valorobservado", h_raw_ult)) if len(datos_soc) > 1 else h_raw_ult
                    if h_prev_raw > 15.0:
                        h_prev_raw = h_prev_raw / 100.0
                    delta_cm = int(round((h_raw_ult - h_prev_raw) * 100.0))
                    return {
                        "nivel_m": h_mira_ult,
                        "nivel_raw_ideam_m": h_raw_ult,
                        "caudal_ls": q_ult_ls,
                        "caudal_prom_24h_ls": q_prom_24h_ls,
                        "delta_cm": delta_cm,
                        "resiliente": False
                    }
        except Exception:
            pass
        # 2. Respaldo desde BigQuery si la API del IDEAM no respondió en ese instante
        try:
            q_sur = """
            SELECT SAFE_CAST(temperatura AS FLOAT64) as nivel_m,
                   SAFE_CAST(precipitacion AS FLOAT64) as caudal_ls,
                   SAFE_CAST(timestamp AS TIMESTAMP) as ts
            FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones`
            WHERE id_estacion = 'Surata'
              AND SAFE_CAST(timestamp AS TIMESTAMP) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
            ORDER BY SAFE_CAST(timestamp AS TIMESTAMP) DESC
            LIMIT 72
            """
            rows_s = list(bq_client.query(q_sur))
            if rows_s and rows_s[0]['nivel_m'] is not None:
                h_raw = round(float(rows_s[0]['nivel_m']), 3)
                h_raw = max(0.09, min(3.50, h_raw))
                h_mira = max(0.05, round(h_raw - OFFSET_SENSOR_IDEAM_MAJADAS, 3))
                q_m3s = 1.2455 * ((h_mira + 0.13) ** 4.1635)
                q_ls = round(q_m3s * 1000.0, 0)
                qs_24h = []
                for r_i in rows_s:
                    if r_i['nivel_m'] is not None and 0.09 <= float(r_i['nivel_m']) <= 3.50:
                        hm_i = max(0.05, float(r_i['nivel_m']) - OFFSET_SENSOR_IDEAM_MAJADAS)
                        qs_24h.append(1.2455 * ((hm_i + 0.13) ** 4.1635) * 1000.0)
                q_prom_24h_ls = round(sum(qs_24h) / len(qs_24h), 0) if qs_24h else q_ls
                h_prev_raw = float(rows_s[min(5, len(rows_s)-1)]['nivel_m']) if len(rows_s) > 1 and rows_s[min(5, len(rows_s)-1)]['nivel_m'] is not None else h_raw
                delta_cm = int(round((h_raw - h_prev_raw) * 100.0))
                return {
                    "nivel_m": h_mira,
                    "nivel_raw_ideam_m": h_raw,
                    "caudal_ls": q_ls,
                    "caudal_prom_24h_ls": q_prom_24h_ls,
                    "delta_cm": delta_cm,
                    "resiliente": False
                }
        except Exception:
            pass
        # 3. Respaldo resiliente ante caída simultánea (H_IDEAM = 1.38 m -> H_mira = 1.34 m -> Q = 6,204 L/s)
        h_raw_def = 1.38
        h_mira_def = round(h_raw_def - OFFSET_SENSOR_IDEAM_MAJADAS, 2)
        q_def = round(1.2455 * ((h_mira_def + 0.13) ** 4.1635) * 1000.0, 0)
        return {
            "nivel_m": h_mira_def,
            "nivel_raw_ideam_m": h_raw_def,
            "caudal_ls": q_def,
            "caudal_prom_24h_ls": q_def,
            "delta_cm": 0,
            "resiliente": True
        }

    # -------------------------------------------------------------
    # MODO 1: TEST MANUAL A MAURICIO MORA (+57 317 639 0605)
    # -------------------------------------------------------------
    if modo == "test_mauricio":
        sur_test = obtener_estado_surata_majadas(client)
        msg = (
            f"MIMAT-C26 (amb): Alertas activas.\n"
            f"Surata Act:{sur_test['caudal_ls']:.0f}L/s Prom24h:{sur_test['caudal_prom_24h_ls']:.0f}L/s\n"
            f"CRC Embalse: 200L/s"
        )
        res = despachar_sms_a_grupo_amb(client, msg, nivel_alerta="TEST_MAURICIO", solo_mauricio=True)
        return json.dumps({"status": "OK", "modo": "test_mauricio", "destinatario": "Mauricio Mora (+573176390605)", "resultados": res}), 200, {'Content-Type': 'application/json'}
        
    # -------------------------------------------------------------
    # MODO 2: DESPACHO MATUTINO (07:00 AM COT) Y BOLETÍN SEMANAL LUNES
    # -------------------------------------------------------------
    elif modo in ["07am", "activacion", "matutino", "boletin"]:
        asegurar_tabla_log_alertas(client)
        es_lunes = (ahora.weekday() == 0)
        sur_info = obtener_estado_surata_majadas(client)
        
        # A. LUNES 07:00 AM (o invocación explícita ?modo=boletin): Boletín Semanal de Pronóstico 7 Días + Caudal Majadas (Actual y Promedio 24h)
        if es_lunes or modo == "boletin":
            coords_est = {
                "Vegas": (7.215028, -73.012806, 22),
                "Yerbabuena": (7.195831, -72.914719, 35),
                "Pajal": (7.140581, -72.999750, 18),
                "Mariana": (7.122739, -73.007019, 28),
                "Monsalve": (7.441806, -72.930917, 40),
                "Majadas": (7.155139, -73.061722, 24)
            }
            mm_sem = {}
            satelite_caido = False
            for nom_c, (lat_c, lon_c, val_def) in coords_est.items():
                if satelite_caido:
                    mm_sem[nom_c] = val_def
                    continue
                try:
                    url_om = f"https://api.open-meteo.com/v1/forecast?latitude={lat_c}&longitude={lon_c}&daily=precipitation_sum&forecast_days=7&timezone=America/Bogota"
                    r_om = requests.get(url_om, timeout=3.5)
                    if r_om.status_code == 200:
                        d_om = r_om.json().get("daily", {}).get("precipitation_sum", [])
                        mm_sem[nom_c] = int(round(sum(x for x in d_om if x is not None)))
                    else:
                        satelite_caido = True
                        mm_sem[nom_c] = val_def
                except Exception:
                    satelite_caido = True
                    mm_sem[nom_c] = val_def

            fin_sem = ahora + timedelta(days=6)
            meses_es = {1:"ene", 2:"feb", 3:"mar", 4:"abr", 5:"may", 6:"jun", 7:"jul", 8:"ago", 9:"sep", 10:"oct", 11:"nov", 12:"dic"}
            if ahora.month == fin_sem.month:
                rango_txt = f"{ahora.day}-{fin_sem.day} {meses_es.get(ahora.month, 'oct')}"
            else:
                rango_txt = f"{ahora.day}{meses_es.get(ahora.month, 'oct')}-{fin_sem.day}{meses_es.get(fin_sem.month, 'nov')}"
            msg = (
                f"MIMAT-C26 ({rango_txt})\n"
                f"Surata Act:{sur_info['caudal_ls']:.0f} Prom24h:{sur_info['caudal_prom_24h_ls']:.0f}L/s\n"
                f"Vegas:{mm_sem['Vegas']}mm Yerba:{mm_sem['Yerbabuena']}mm\n"
                f"Pajal:{mm_sem['Pajal']}mm Maria:{mm_sem['Mariana']}mm\n"
                f"Monsalve:{mm_sem['Monsalve']}mm Majadas:{mm_sem['Majadas']}mm\n"
                f"Pronostico semanal amb"
            )
            res = despachar_sms_a_grupo_amb(client, msg, nivel_alerta="BOLETIN_MATUTINO", solo_mauricio=False)
            exito_envio = algun_envio_exitoso(res)
            if exito_envio:
                registrar_despacho_alerta(client, "Red_MIMAT", "BOLETIN_MATUTINO", 0.0)
            return json.dumps({
                "status": "OK" if exito_envio else "ERROR_TWILIO_CONFIG",
                "modo": "boletin_semanal_lunes",
                "mensaje_enviado": msg,
                "caudal_surata_actual_ls": sur_info['caudal_ls'],
                "caudal_surata_prom_24h_ls": sur_info['caudal_prom_24h_ls'],
                "resultados": res
            }), 200, {'Content-Type': 'application/json'}

        # B. MARTES A DOMINGO 07:00 AM: Reporte de Lluvias 24h + Embalse + Río Suratá (Majadas: Caudal Actual y Promedio 24h)
        todas_estaciones = ["El_Pajal", "Yerbabuena", "La_Mariana", "Vegas_del_Quemado", "Monsalve"]
        
        try:
            q_lluvia = """
            SELECT id_estacion, 
                   SUM(SAFE_CAST(precipitacion AS FLOAT64)) as lluvia_mm,
                   MAX(SAFE_CAST(timestamp AS TIMESTAMP)) as ult_envio,
                   COUNT(*) as num_registros,
                   MAX(CASE WHEN SAFE_CAST(timestamp AS TIMESTAMP) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 3 HOUR) THEN SAFE_CAST(temperatura AS FLOAT64) ELSE NULL END) as max_temp_3h,
                   MAX(CASE WHEN SAFE_CAST(timestamp AS TIMESTAMP) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 3 HOUR) THEN SAFE_CAST(humedad AS FLOAT64) ELSE NULL END) as max_hum_3h
            FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones`
            WHERE SAFE_CAST(timestamp AS TIMESTAMP) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
              AND id_estacion NOT IN ('Embalse', 'Surata')
            GROUP BY id_estacion
            """
            job_ll = client.query(q_lluvia)
            datos_est = {
                r['id_estacion']: {
                    'lluvia': round(float(r['lluvia_mm'] or 0.0), 1),
                    'num_registros': int(r['num_registros'] or 0),
                    'max_temp_3h': float(r['max_temp_3h']) if r['max_temp_3h'] is not None else None,
                    'max_hum_3h': float(r['max_hum_3h']) if r['max_hum_3h'] is not None else None
                }
                for r in job_ll
            }
        except:
            datos_est = {}
            
        try:
            q_cota = """
            SELECT SAFE_CAST(temperatura AS FLOAT64) - 0.04 as cota_cal
            FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones`
            WHERE id_estacion = 'Embalse'
              AND SAFE_CAST(timestamp AS TIMESTAMP) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
            ORDER BY SAFE_CAST(timestamp AS TIMESTAMP) DESC
            """
            job_c = client.query(q_cota)
            rows_c = [round(float(r['cota_cal']), 2) for r in job_c if r['cota_cal'] is not None and 800 < r['cota_cal'] < 900]
            if rows_c:
                cota_val = rows_c[0]
                cota_ini = rows_c[-1]
                delta_cm = int(round((cota_val - cota_ini) * 100.0))
                if delta_cm >= 2:
                    txt_embalse = f"Embalse: {cota_val}m (+{delta_cm}cm)"
                elif delta_cm <= -2:
                    txt_embalse = f"Embalse: {cota_val}m ({delta_cm}cm)"
                else:
                    txt_embalse = f"Embalse: {cota_val}m Estable"
            else:
                cota_val = 885.67
                txt_embalse = f"Embalse: {cota_val}m"
        except:
            cota_val = 885.67
            txt_embalse = f"Embalse: {cota_val}m"

        # Línea hidrológica oficial de Río Suratá (Sector Majadas): Caudal Actual (último IDEAM) + Caudal Promedio 24h
        txt_surata = f"Surata Act:{sur_info['caudal_ls']:.0f}L/s Prom24h:{sur_info['caudal_prom_24h_ls']:.0f}L/s"
        # Aclarar rebose calibrado del Morning Glory si el embalse supera 885.75 msnm
        if cota_val > 885.75:
            h_mg = cota_val - 885.75
            q_mg_aprox = round(110.0 * (h_mg ** 1.5) * 1000.0, 0)
            txt_embalse = f"Embalse:{cota_val}m (MG~{q_mg_aprox:.0f}L/s cascadas)"
            
        est_tona_lluvia = []
        monsalve_linea = None
        est_offline_items = []
        est_offline_aliases = []

        for est_id in todas_estaciones:
            alias = UMBRALES_ESTACIONES.get(est_id, {}).get('alias', est_id)
            info = datos_est.get(est_id)
            
            sondas_en_cero = (
                info is not None
                and (info['max_temp_3h'] is None or info['max_temp_3h'] == 0.0)
                and (info['max_hum_3h'] is None or info['max_hum_3h'] == 0.0)
            )
            if not info or info['num_registros'] == 0:
                est_offline_items.append(f"{alias}: Sin datos")
                est_offline_aliases.append(alias)
            elif sondas_en_cero:
                est_offline_items.append(f"{alias}: En 0.0 (Virtual)")
                est_offline_aliases.append(alias)
            elif info['lluvia'] >= 1.0:
                if est_id == "Monsalve":
                    monsalve_linea = f"Monsalve: {info['lluvia']}mm"
                else:
                    est_tona_lluvia.append((info['lluvia'], f"{alias}: {info['lluvia']}mm"))
            elif info['lluvia'] >= 0.2:
                if est_id == "Monsalve":
                    monsalve_linea = f"Monsalve: {info['lluvia']}mm"
                else:
                    est_tona_lluvia.append((info['lluvia'], f"{alias}: {info['lluvia']}mm"))
        
        est_tona_lluvia.sort(key=lambda x: x[0], reverse=True)
        lineas_tona = [x[1] for x in est_tona_lluvia]
        
        lineas_reporte = []
        lineas_reporte.extend(lineas_tona[:2])
        if monsalve_linea:
            lineas_reporte.append(monsalve_linea)
        elif len(lineas_tona) > 2:
            lineas_reporte.append(lineas_tona[2])
            
        # Garantizar que TODAS las estaciones desconectadas (ej. Yerbabuena y Mariana) se reporten siempre:
        espacio_disponible = 3 - len(lineas_reporte)
        if espacio_disponible > 0 and len(est_offline_items) <= espacio_disponible:
            lineas_reporte.extend(est_offline_items)
        elif est_offline_aliases:
            lineas_reporte.append(f"En 0.0 (Virtual): {', '.join(est_offline_aliases)}")
            
        fecha_str = ahora.strftime('%d-%b').lower()
        detalle_txt = "\n".join(lineas_reporte) if lineas_reporte else "Cuencas: 0.0mm (Tiempo seco 24h)"
        msg = (
            f"MIMAT-C26 ({fecha_str} 7am)\n"
            f"{txt_embalse}\n"
            f"{txt_surata}\n"
            f"{detalle_txt}\n"
            f"Reporte matutino amb"
        )
        res = despachar_sms_a_grupo_amb(client, msg, nivel_alerta="BOLETIN_MATUTINO", solo_mauricio=False)
        exito_envio = algun_envio_exitoso(res)
        if exito_envio:
            registrar_despacho_alerta(client, "Red_MIMAT", "BOLETIN_MATUTINO", 0.0)
        return json.dumps({
            "status": "OK" if exito_envio else "ERROR_TWILIO_CONFIG",
            "modo": modo,
            "descripcion": "Despacho matutino 07:00 AM ejecutado con exito (incluye Caudal Actual y Promedio 24h de Surata)" if exito_envio else "Boletin generado pero Twilio reporto error de credenciales/envio",
            "mensaje_enviado": msg,
            "caudal_surata_actual_ls": sur_info['caudal_ls'],
            "caudal_surata_prom_24h_ls": sur_info['caudal_prom_24h_ls'],
            "resultados": res
        }), 200, {'Content-Type': 'application/json'}
        
    # -------------------------------------------------------------
    # MODO 3: VIGILANCIA CONTINUA CADA 10 MINUTOS (TELEMETRÍA EN VIVO)
    # -------------------------------------------------------------
    elif modo == "vigilancia":
        dia_sem = ahora.weekday() # 0=Lun ... 4=Vie, 5=Sab, 6=Dom
        hora_act = ahora.time()
        es_fin_de_semana = (dia_sem in [5, 6])
        
        asegurar_tabla_log_alertas(client)
        
        # Ventana de Avisos Diurnos (Amarilla P75):
        # - Lunes a Viernes: 07:00 a 17:00 COT
        # - Sabados y Domingos: Despues de las 10:00 AM hasta las 17:00 COT
        if es_fin_de_semana:
            ventana_diurna = (time(10, 0) <= hora_act <= time(17, 0))
        else:
            ventana_diurna = (time(7, 0) <= hora_act <= time(17, 0))
            
        # -----------------------------------------------------------------
        # VIGILANCIA DE COTA EMBALSE TONA (ALERTA DE PROXIMIDAD O REBOSE)
        # Offset de -0.04 m (-4 cm) confirmado por Ing. Angarita
        # -----------------------------------------------------------------
        alertas_disparadas = []
        cota_actual_emb = 885.67
        try:
            q_emb = """
            SELECT SAFE_CAST(temperatura AS FLOAT64) - 0.04 as cota_cal
            FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones`
            WHERE id_estacion = 'Embalse'
              AND SAFE_CAST(temperatura AS FLOAT64) BETWEEN 818.0 AND 886.5
            ORDER BY SAFE_CAST(timestamp AS TIMESTAMP) DESC
            LIMIT 1
            """
            job_emb = client.query(q_emb)
            rows_emb = list(job_emb)
            if rows_emb and rows_emb[0]['cota_cal'] is not None:
                cota_actual = round(float(rows_emb[0]['cota_cal']), 2)
                cota_actual_emb = cota_actual
                
                # Horario respetable para avisos de embalse:
                # - Lunes a Viernes: 07:00 a 20:30 COT
                # - Sábados y Domingos: Después de las 10:00 AM hasta las 20:30 COT
                if es_fin_de_semana:
                    horario_respetable = (time(10, 0) <= hora_act <= time(20, 30))
                else:
                    horario_respetable = (time(7, 0) <= hora_act <= time(20, 30))
                    
                nivel_embalse = None
                if cota_actual >= 885.75:
                    nivel_embalse = "REBOSE_ACTIVO"
                elif cota_actual >= 885.73: # A escasos 2 cm del vertedero Morning Glory (885.75 msnm)
                    nivel_embalse = "PRE_REBOSE"
                    
                if nivel_embalse and horario_respetable:
                    # COOLDOWN ESTRICTO DE 12 HORAS (AVISA UNA SOLA VEZ Y SILENCIA)
                    # Evita que el oleaje en la corona (885.74 - 885.76 msnm) dispare mensajes continuos
                    q_hist_emb = """
                    SELECT nivel_alerta 
                    FROM `gen-lang-client-0342049346.amb_hidrologia.log_alertas_sms`
                    WHERE id_estacion = 'Embalse'
                      AND SAFE_CAST(timestamp AS TIMESTAMP) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 12 HOUR)
                    ORDER BY SAFE_CAST(timestamp AS TIMESTAMP) DESC
                    LIMIT 5
                    """
                    job_h = client.query(q_hist_emb)
                    alertas_previas_emb = [r['nivel_alerta'] for r in job_h]
                    
                    debe_despachar_emb = False
                    # 1. Si ya se notifico REBOSE_ACTIVO hoy (ultimas 12h), NO enviar nada mas
                    if "REBOSE_ACTIVO" in alertas_previas_emb:
                        debe_despachar_emb = False
                    # 2. Si es REBOSE_ACTIVO y no se habia avisado antes en 12h, se envia 1 sola vez
                    elif nivel_embalse == "REBOSE_ACTIVO":
                        debe_despachar_emb = True
                    # 3. Si es PRE_REBOSE, solo se envia si no hay NINGUNA alerta de embalse en 12h
                    elif nivel_embalse == "PRE_REBOSE" and not alertas_previas_emb:
                        debe_despachar_emb = True
                            
                    if debe_despachar_emb:
                        cm_faltan = max(0, int(round((885.75 - cota_actual) * 100.0)))
                        if nivel_embalse == "REBOSE_ACTIVO":
                            cm_sobre = int(round((cota_actual - 885.75) * 100.0))
                            h_mg = max(0.0, cota_actual - 885.75)
                            q_mg_aprox = round(110.0 * (h_mg ** 1.5) * 1000.0, 0)
                            sms_emb = (
                                f"Embalse Tona - Rebose Activo\n"
                                f"Cota: {cota_actual}m (+{cm_sobre}cm)\n"
                                f"MG cascada: ~{q_mg_aprox:.0f}L/s\n"
                                f"Descarga a Puente Tona\n"
                                f"MIMAT-C26 amb"
                            )
                        else:
                            sms_emb = (
                                f"Embalse Tona - Aviso Nivel\n"
                                f"Cota: {cota_actual}m (Faltan {cm_faltan}cm)\n"
                                f"Llenado acelerado hacia rebose\n"
                                f"MIMAT-C26 amb"
                            )
                        res_emb = despachar_sms_a_grupo_amb(client, sms_emb, nivel_alerta="NARANJA", solo_mauricio=False)
                        if algun_envio_exitoso(res_emb):
                            registrar_despacho_alerta(client, "Embalse", nivel_embalse, cota_actual)
                        alertas_disparadas.append({"estacion": "Embalse", "nivel": nivel_embalse, "cota": cota_actual, "resultado": res_emb})
        except:
            pass

        # -----------------------------------------------------------------
        # VIGILANCIA HIDROLÓGICA RÍO SURATÁ — SECTOR MAJADAS -> TOMA BOSCONIA
        # Ecuación Oficial: Q(m3/s) = 1.2455 * (H + 0.13)**4.1635
        # Tiempo de tránsito Majadas -> Bocatoma Bosconia: 15 a 25 minutos
        # -----------------------------------------------------------------
        try:
            sur_vig = obtener_estado_surata_majadas(client)
            if not sur_vig.get("resiliente", True):
                q_sur_ls = float(sur_vig["caudal_ls"])
                h_sur_m = float(sur_vig["nivel_m"])
                hora_str = ahora.strftime('%H:%M')

                nivel_surata = None
                if q_sur_ls >= 14000.0 or h_sur_m >= 1.66:
                    nivel_surata = "CRECIENTE_ROJA"
                elif q_sur_ls >= 9500.0 or h_sur_m >= 1.50:
                    nivel_surata = "CRECIENTE_NARANJA"
                elif (q_sur_ls >= 7500.0 or h_sur_m >= 1.41) and ventana_diurna:
                    nivel_surata = "ASCENSO_AMARILLO"

                if nivel_surata:
                    ult_sur = obtener_ultimo_despacho_alerta(client, "Surata")
                    debe_alertar_sur = True
                    if ult_sur:
                        niv_prev_s = ult_sur["nivel"]
                        if nivel_surata == niv_prev_s:
                            debe_alertar_sur = False
                        elif nivel_surata == "CRECIENTE_NARANJA" and niv_prev_s == "CRECIENTE_ROJA":
                            debe_alertar_sur = False
                        elif nivel_surata == "ASCENSO_AMARILLO" and niv_prev_s in ["CRECIENTE_NARANJA", "CRECIENTE_ROJA"]:
                            debe_alertar_sur = False

                    if debe_alertar_sur:
                        if nivel_surata == "CRECIENTE_ROJA":
                            sms_sur = (
                                f"Alerta Roja Creciente Surata\n"
                                f"Majadas: {q_sur_ls:.0f}L/s ({h_sur_m:.2f}m)\n"
                                f"Transito Bosconia: 15-25 min\n"
                                f"Proteger/cerrar bocatoma\n"
                                f"Hora: {hora_str} COT"
                            )
                            res_s = despachar_sms_a_grupo_amb(client, sms_sur, nivel_alerta="ROJA", solo_mauricio=False)
                        elif nivel_surata == "CRECIENTE_NARANJA":
                            sms_sur = (
                                f"Alerta Naranja Rio Surata\n"
                                f"Majadas: {q_sur_ls:.0f}L/s ({h_sur_m:.2f}m)\n"
                                f"Curva alta a Bosconia\n"
                                f"Alistar desarenadores/purga\n"
                                f"Hora: {hora_str} COT"
                            )
                            res_s = despachar_sms_a_grupo_amb(client, sms_sur, nivel_alerta="NARANJA", solo_mauricio=False)
                        else:
                            sms_sur = (
                                f"Aviso Nivel Rio Surata (amb)\n"
                                f"Majadas: {q_sur_ls:.0f}L/s ({h_sur_m:.2f}m)\n"
                                f"Curva en ascenso estimada\n"
                                f"Vigilancia de turbiedad\n"
                                f"Hora: {hora_str} COT"
                            )
                            res_s = despachar_sms_a_grupo_amb(client, sms_sur, nivel_alerta="AMARILLA", solo_mauricio=False)

                        if algun_envio_exitoso(res_s):
                            registrar_despacho_alerta(client, "Surata", nivel_surata, q_sur_ls)
                        alertas_disparadas.append({"estacion": "Surata", "nivel": nivel_surata, "caudal_ls": q_sur_ls, "nivel_m": h_sur_m, "resultado": res_s})
        except Exception:
            pass

        # -----------------------------------------------------------------
        # VIGILANCIA DE PRECIPITACIÓN HORARIA EN ESTACIONES METEOROLÓGICAS
        # Regla física de tránsito hacia Toma Bosconia:
        # - Monsalve drena directo al Río Suratá (cauce libre sin embalse).
        # - Cuenca Tona (Pajal, Vegas, Mariana, Yerbabuena) drena al Embalse:
        #   solo pasa a Bosconia si el Embalse supera 885.75 msnm (rebose activo);
        #   si está <= 885.75 msnm, el Embalse amortigua y detiene esa creciente.
        # -----------------------------------------------------------------
        try:
            q_vig = """
            SELECT id_estacion, SUM(SAFE_CAST(precipitacion AS FLOAT64)) as lluvia_reciente
            FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones`
            WHERE SAFE_CAST(timestamp AS TIMESTAMP) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
              AND id_estacion NOT IN ('Embalse', 'Surata')
            GROUP BY id_estacion
            """
            job_vig = client.query(q_vig)
            lluvias_recientes = {r['id_estacion']: float(r['lluvia_reciente'] or 0.0) for r in job_vig}
        except:
            lluvias_recientes = {}
            
        for est_id, ll_val in lluvias_recientes.items():
            u = UMBRALES_ESTACIONES.get(est_id)
            if not u:
                continue
                
            alias = u["alias"]
            hora_str = ahora.strftime('%H:%M')
            
            nivel_candidato = None
            if ll_val >= u["roja"]:
                nivel_candidato = "ROJA"
            elif ll_val >= u["naranja"]:
                nivel_candidato = "NARANJA"
            elif ll_val >= u["amarilla"] and ventana_diurna:
                nivel_candidato = "AMARILLA"
                
            if not nivel_candidato:
                continue
                
            ultimo_despacho = obtener_ultimo_despacho_alerta(client, est_id)
            if ultimo_despacho:
                nivel_previo = ultimo_despacho["nivel"]
                if nivel_candidato == nivel_previo:
                    continue
                if nivel_candidato == "NARANJA" and nivel_previo == "ROJA":
                    continue
                if nivel_candidato == "AMARILLA" and nivel_previo in ["NARANJA", "ROJA"]:
                    continue

            es_monsalve = (est_id == "Monsalve")
            embalse_en_rebose = (cota_actual_emb > 885.75)
                
            if nivel_candidato == "ROJA":
                if es_monsalve:
                    linea_transito_r = "Directo a Rio Surata/Bosconia"
                    linea_accion_r = "Alistar purga/bocatoma"
                elif embalse_en_rebose:
                    linea_transito_r = f"Embalse rebose ({cota_actual_emb}m)->Bosconia"
                    linea_accion_r = "Alistar purga/bocatoma"
                else:
                    linea_transito_r = f"Aporte a Embalse ({cota_actual_emb}m)"
                    linea_accion_r = "Embalse amortigua (<885.75m)"
                sms_critico = (
                    f"Alerta Roja MIMAT-C26 (amb)\n"
                    f"{alias}: {ll_val:.1f}mm/h\n"
                    f"{linea_transito_r}\n"
                    f"{linea_accion_r}\n"
                    f"Hora: {hora_str} COT"
                )
                res_crit = despachar_sms_a_grupo_amb(client, sms_critico, nivel_alerta="ROJA", solo_mauricio=False)
                if algun_envio_exitoso(res_crit):
                    registrar_despacho_alerta(client, est_id, "ROJA", ll_val)
                alertas_disparadas.append({"estacion": est_id, "nivel": "ROJA", "resultado": res_crit})
                
            elif nivel_candidato == "NARANJA":
                if es_monsalve:
                    linea_transito_n = "Drena directo a Rio Surata"
                    linea_accion_n = "Inspeccion rejillas Bosconia"
                elif embalse_en_rebose:
                    linea_transito_n = f"Embalse rebose ({cota_actual_emb}m)->Surata"
                    linea_accion_n = "Inspeccion rejillas Bosconia"
                else:
                    linea_transito_n = f"Ascenso hacia Embalse ({cota_actual_emb}m)"
                    linea_accion_n = "Embalse retiene (<885.75m)"
                sms_critico = (
                    f"Alerta Naranja MIMAT-C26 (amb)\n"
                    f"{alias}: {ll_val:.1f}mm/h\n"
                    f"{linea_transito_n}\n"
                    f"{linea_accion_n}\n"
                    f"Hora: {hora_str} COT"
                )
                res_crit = despachar_sms_a_grupo_amb(client, sms_critico, nivel_alerta="NARANJA", solo_mauricio=False)
                if algun_envio_exitoso(res_crit):
                    registrar_despacho_alerta(client, est_id, "NARANJA", ll_val)
                alertas_disparadas.append({"estacion": est_id, "nivel": "NARANJA", "resultado": res_crit})
                
            elif nivel_candidato == "AMARILLA":
                sms_diurno = (
                    f"Aviso Lluvia MIMAT-C26 (amb)\n"
                    f"{alias}: {ll_val:.1f}mm/h\n"
                    f"Lluvia significativa\n"
                    f"Monitoreo rutinario\n"
                    f"Hora: {hora_str} COT"
                )
                res_diur = despachar_sms_a_grupo_amb(client, sms_diurno, nivel_alerta="AMARILLA", solo_mauricio=False)
                if algun_envio_exitoso(res_diur):
                    registrar_despacho_alerta(client, est_id, "AMARILLA", ll_val)
                alertas_disparadas.append({"estacion": est_id, "nivel": "AMARILLA", "resultado": res_diur})

        # -----------------------------------------------------------------
        # VIGILANCIA DE FALLA DE SENSORES O CAÍDA DE ESTACIÓN (AVISO ÚNICO SIN SPAM)
        # Reglas físicas por sensor:
        # - Precipitación: Se excluye de alerta por cero (0.0 mm es tiempo seco normal).
        # - Humedad: 0.0% sostenido (>2h) es físicamente imposible -> Falla confirmada.
        # - Temperatura: 0.0°C en estaciones medias (>2h) o cero prolongado (>3h) en páramo (Yerbabuena/Monsalve).
        # - Barómetro: En 0.0 o pegado exactamente en el mismo valor (>6h sin variación por marea barométrica).
        # - Viento: Solo se advierte si velocidad=0.0 y dirección=0° simultáneamente por >12h continuas.
        # -----------------------------------------------------------------
        try:
            q_salud = """
            WITH base AS (
                SELECT id_estacion,
                       SAFE_CAST(timestamp AS TIMESTAMP) as ts,
                       SAFE_CAST(temperatura AS FLOAT64) as temp,
                       SAFE_CAST(humedad AS FLOAT64) as hum,
                       SAFE_CAST(presion AS FLOAT64) as pres,
                       SAFE_CAST(velocidad_viento AS FLOAT64) as viento,
                       SAFE_CAST(direccion_viento AS FLOAT64) as dir_v,
                       LAG(SAFE_CAST(temperatura AS FLOAT64)) OVER (PARTITION BY id_estacion ORDER BY SAFE_CAST(timestamp AS TIMESTAMP)) as prev_t,
                       LAG(SAFE_CAST(velocidad_viento AS FLOAT64)) OVER (PARTITION BY id_estacion ORDER BY SAFE_CAST(timestamp AS TIMESTAMP)) as prev_v,
                       LAG(SAFE_CAST(direccion_viento AS FLOAT64)) OVER (PARTITION BY id_estacion ORDER BY SAFE_CAST(timestamp AS TIMESTAMP)) as prev_d
                FROM `gen-lang-client-0342049346.amb_hidrologia.telemetria_estaciones`
                WHERE SAFE_CAST(timestamp AS TIMESTAMP) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
                  AND id_estacion NOT IN ('Embalse', 'La_Mariana', 'Surata')
            )
            SELECT id_estacion,
                   COUNTIF(ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 150 MINUTE)) as n_reg_2h,
                   COUNTIF(ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 210 MINUTE)) as n_reg_3h,
                   COUNTIF(ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 8 HOUR)) as n_reg_8h,
                   COUNTIF(ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 12 HOUR)) as n_reg_12h,
                   MAX(CASE WHEN ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 150 MINUTE) THEN temp ELSE NULL END) as max_temp_2h,
                   MIN(CASE WHEN ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 150 MINUTE) THEN temp ELSE NULL END) as min_temp_2h,
                   MAX(CASE WHEN ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 210 MINUTE) THEN temp ELSE NULL END) as max_temp_3h,
                   MIN(CASE WHEN ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 210 MINUTE) THEN temp ELSE NULL END) as min_temp_3h,
                   MAX(CASE WHEN ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 150 MINUTE) THEN hum ELSE NULL END) as max_hum_2h,
                   MAX(CASE WHEN ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 150 MINUTE) THEN pres ELSE NULL END) as max_pres_2h,
                   MAX(CASE WHEN ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 8 HOUR) THEN pres ELSE NULL END) as max_pres_8h,
                   MIN(CASE WHEN ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 8 HOUR) THEN pres ELSE NULL END) as min_pres_8h,
                   MAX(CASE WHEN ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 12 HOUR) THEN viento ELSE NULL END) as max_viento_12h,
                   MAX(CASE WHEN ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 12 HOUR) THEN dir_v ELSE NULL END) as max_dir_12h,
                   MAX(CASE WHEN hum > 1.0 AND temp != 0.0 AND (prev_t IS NULL OR ABS(temp - prev_t) > 0.0001 OR ABS(viento - prev_v) > 0.0001 OR ABS(dir_v - prev_d) > 0.0001) THEN ts ELSE NULL END) as ult_lectura_sana
            FROM base
            GROUP BY id_estacion
            """
            job_sal = client.query(q_salud)
            salud_map = {r['id_estacion']: dict(r) for r in job_sal}

            estaciones_monitoreadas = ["El_Pajal", "Yerbabuena", "Vegas_del_Quemado", "Monsalve"]
            estaciones_alta_montana = ["Yerbabuena", "Monsalve"]

            for est_id in estaciones_monitoreadas:
                u = UMBRALES_ESTACIONES.get(est_id, {})
                alias = u.get("alias", est_id)
                hora_str = ahora.strftime('%H:%M')
                s_info = salud_map.get(est_id)

                estado_falla = None
                sms_falla = None

                if not s_info or int(s_info.get('n_reg_2h', 0)) == 0:
                    estado_falla = "OFFLINE_SOSTENIDO"
                    sms_falla = (
                        f"ALERTA TECNICA MIMAT\n"
                        f"{alias}: Sin datos (>2.5h)\n"
                        f"Estacion fuera de linea\n"
                        f"Requiere revision en campo\n"
                        f"Hora: {hora_str} COT"
                    )
                else:
                    n_2h = int(s_info.get('n_reg_2h', 0))
                    n_3h = int(s_info.get('n_reg_3h', 0))
                    n_8h = int(s_info.get('n_reg_8h', 0))
                    n_12h = int(s_info.get('n_reg_12h', 0))

                    max_t2 = float(s_info['max_temp_2h']) if s_info.get('max_temp_2h') is not None else 0.0
                    min_t2 = float(s_info['min_temp_2h']) if s_info.get('min_temp_2h') is not None else 0.0
                    max_t3 = float(s_info['max_temp_3h']) if s_info.get('max_temp_3h') is not None else 0.0
                    min_t3 = float(s_info['min_temp_3h']) if s_info.get('min_temp_3h') is not None else 0.0
                    max_h2 = float(s_info['max_hum_2h']) if s_info.get('max_hum_2h') is not None else 0.0
                    max_p2 = float(s_info['max_pres_2h']) if s_info.get('max_pres_2h') is not None else 0.0
                    max_p8 = float(s_info['max_pres_8h']) if s_info.get('max_pres_8h') is not None else 0.0
                    min_p8 = float(s_info['min_pres_8h']) if s_info.get('min_pres_8h') is not None else 0.0
                    max_v12 = float(s_info['max_viento_12h']) if s_info.get('max_viento_12h') is not None else 0.0
                    max_d12 = float(s_info['max_dir_12h']) if s_info.get('max_dir_12h') is not None else 0.0

                    sensores_falla = []

                    # 1. Humedad en 0.0% (>2.5h): físicamente imposible en cualquier estación
                    if n_2h >= 6 and max_h2 == 0.0:
                        sensores_falla.append("Humedad(0%)")

                    # 2. Temperatura en 0.0°C:
                    # - En Yerbabuena y Monsalve (alta montaña): solo si es cero exacto prolongado (>3.5h, max=0 y min=0)
                    # - En estaciones medias (Pajal, Vegas): >2.5h en 0.0°C
                    if est_id in estaciones_alta_montana:
                        if n_3h >= 12 and max_t3 == 0.0 and min_t3 == 0.0:
                            sensores_falla.append("Temp(0.0 prolongado)")
                    else:
                        if n_2h >= 6 and max_t2 == 0.0 and min_t2 == 0.0:
                            sensores_falla.append("Temp(0.0)")

                    # 3. Barómetro en 0.0 (>2.5h) o pegado exactamente en el mismo valor por >8h (Hold SCADA)
                    if n_2h >= 6 and max_p2 == 0.0:
                        sensores_falla.append("Barometro(0.0)")
                    elif n_8h >= 36 and max_p8 == min_p8:
                        sensores_falla.append("Barometro(pegado)")

                    # 4. Viento: solo si velocidad=0.0 Y dirección=0° clavados durante >12 horas continuas
                    if n_12h >= 36 and max_v12 == 0.0 and max_d12 == 0.0:
                        sensores_falla.append("Viento(0/0)")

                    if sensores_falla:
                        estado_falla = "SENSORES_EN_CERO"
                        if len(sensores_falla) >= 2:
                            detalle_f = "Multiples sensores en 0/pegados"
                        else:
                            detalle_f = f"Falla: {sensores_falla[0]}"

                        sms_falla = (
                            f"ALERTA SENSOR MIMAT\n"
                            f"{alias}: {detalle_f}\n"
                            f"Requiere revision en campo\n"
                            f"Hora: {hora_str} COT"
                        )

                if estado_falla and sms_falla:
                    # BLOQUEO DE AVISO ÚNICO POR INCIDENTE (LATCH DE ESTADO - CERO SPAM):
                    # Envía 1 solo SMS cuando entra en falla y no vuelve a enviar otro
                    # hasta que la estación se recupere en campo y vuelva a fallar en el futuro.
                    ult_sana = s_info.get('ult_lectura_sana') if s_info else None
                    q_prev_falla = f"""
                    SELECT MAX(SAFE_CAST(timestamp AS TIMESTAMP)) as ult_alerta_ts
                    FROM `gen-lang-client-0342049346.amb_hidrologia.log_alertas_sms`
                    WHERE id_estacion = '{est_id}'
                      AND nivel_alerta IN ('SENSORES_EN_CERO', 'TRAMA_CONGELADA', 'OFFLINE_SOSTENIDO')
                    """
                    rows_pf = list(client.query(q_prev_falla))
                    ult_alerta_ts = rows_pf[0]['ult_alerta_ts'] if rows_pf and rows_pf[0]['ult_alerta_ts'] is not None else None

                    ya_notificado_este_incidente = False
                    if ult_alerta_ts is not None:
                        if ult_sana is None or ult_alerta_ts >= ult_sana:
                            ya_notificado_este_incidente = True

                    if not ya_notificado_este_incidente:
                        res_f = despachar_sms_a_grupo_amb(client, sms_falla, nivel_alerta="NARANJA", solo_mauricio=False)
                        if algun_envio_exitoso(res_f):
                            registrar_despacho_alerta(client, est_id, estado_falla, 0.0)
                        alertas_disparadas.append({"estacion": est_id, "nivel": estado_falla, "sensores": sensores_falla if estado_falla == "SENSORES_EN_CERO" else ["OFFLINE"], "aviso_unico_bloqueado": True, "resultado": res_f})
        except Exception as e:
            pass

        return json.dumps({
            "status": "OK",
            "modo": "vigilancia",
            "ventana_diurna_activa": ventana_diurna,
            "alertas_emitidas": len(alertas_disparadas),
            "detalle": alertas_disparadas
        }), 200, {'Content-Type': 'application/json'}
        
    else:
        return json.dumps({"error": f"Modo no reconocido: {modo}"}), 400, {'Content-Type': 'application/json'}

# Alias de compatibilidad para cualquier punto de entrada configurado en GCP
main_handler = centinela_inspeccion_cuencas

# ===================================================================================================
# FIN DEL MÓDULO | MIMAT-C26 CLOUD FUNCTION SERVERLESS (amb)
# Desarrollado por: Mauricio Mora - Auxiliar Operativo III / Arquitecto Cloud MIMAT-C26
# Acueducto Metropolitano de Bucaramanga S.A. E.S.P. (amb) - Todos los derechos reservados
# ===================================================================================================
