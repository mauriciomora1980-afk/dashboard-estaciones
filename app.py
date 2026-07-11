# ============================================================
# 2. CONEXIÓN A BIGQUERY (CORREGIDA)
# ============================================================
@st.cache_resource
def init_bigquery_client():
    try:
        # --- INTENTAR PRIMERO CON VARIABLE DE ENTORNO (CLOUD RUN) ---
        creds_json = os.environ.get("GCP_CREDENTIALS_JSON")
        
        if creds_json:
            st.info("🔐 Conectando con variable de entorno...")
            key_dict = json.loads(creds_json)
            st.success("✅ Conectado usando variable de entorno")
        
        # --- SI NO HAY VARIABLE DE ENTORNO, USAR SECRETS.TOML (LOCAL) ---
        else:
            st.info("🔐 Conectando con secrets.toml (modo local)...")
            # Intentar leer el archivo secrets.toml directamente
            import tomllib  # Python 3.11+
            # Para versiones anteriores, usar: import toml
            with open('.streamlit/secrets.toml', 'rb') as f:
                secrets = tomllib.load(f)
            
            b64_json = secrets["GCP_JSON_B64"]
            json_str = base64.b64decode(b64_json).decode('utf-8')
            key_dict = json.loads(json_str)
            st.success("✅ Conectado usando secrets.toml")
        
        # --- CREAR CREDENCIALES Y CLIENTE ---
        creds = service_account.Credentials.from_service_account_info(key_dict)
        client = bigquery.Client(credentials=creds, project=key_dict["project_id"])
        return client
        
    except Exception as e:
        st.error(f"❌ Error de conexión con BigQuery: {e}")
        st.stop()
