import os
import logging
import logging_loki
import sys

from flask import Flask
from flask_cors import CORS

# ==============================================================================
# 1. VARIÁVEIS DE NEGÓCIO & AMBIENTE
# ==============================================================================
ENV = os.getenv("ENV", "dev")
APP_NAME = os.getenv("APP_NAME", "nsj-ia-suporte-api")
MOPE_CODE = os.getenv("MOPE_CODE", "1234")
LOG_DEBUG = os.getenv("LOG_DEBUG", "False").upper() == "TRUE"

# ==============================================================================
# 2. CONFIGURAÇÕES DE IA & GRAPH RAG (Adicionado na Migração)
# ==============================================================================
# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Neo4j (Graph Database)
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# ==============================================================================
# 3. BANCO DE DADOS RELACIONAL (POSTGRES)
# ==============================================================================
DATABASE_HOST = os.getenv("DATABASE_HOST", "localhost")
DATABASE_PORT = os.getenv("DATABASE_PORT", "5440")
DATABASE_NAME = os.getenv("DATABASE_NAME", "projeto")
DATABASE_USER = os.getenv("DATABASE_USER", "projeto")
DATABASE_PASS = os.getenv("DATABASE_PASS", "mysecretpassword")
DATABASE_DRIVER = os.getenv("DATABASE_DRIVER", "POSTGRES")

DEFAULT_PAGE_SIZE = int(os.getenv("DEFAULT_PAGE_SIZE", 20))

# ==============================================================================
# 4. INTEGRAÇÕES & UTILITÁRIOS (SRE/Auth)
# ==============================================================================
GRAFANA_URL = os.getenv("GRAFANA_URL")
INTROSPECT_TOKEN = os.getenv("INTROSPECT_TOKEN", "dummy_token")
INTROSPECT_URL = os.getenv("INTROSPECT_URL", "http://localhost:9999")
DIRETORIO_URL = os.getenv("DIRETORIO_URL", "")

# URLs para Jobs de Schema
BASE_API_URL = os.getenv("BASE_API_URL", "http://localhost:5000")
SCHEMAS_PATH = os.getenv("SCHEMAS_PATH", "/var/www/html/@schemas")
SCHEMAS_API_KEY = os.getenv("SCHEMAS_API_KEY", "")

# Workers Config
WORKER_COMPILACAO_TIMEOUT = int(os.getenv("WORKER_COMPILACAO_TIMEOUT", 5 * 60))
WORKER_COMPILACAO_TTL = int(os.getenv("WORKER_COMPILACAO_TTL", 3600 * 24 * 3))
WORKER_COMPILACAO_FAILURE_TTL = int(os.getenv("WORKER_COMPILACAO_FAILURE_TTL", 3600 * 24 * 7))
WORKER_COMPILACAO_RETRY_MAX = int(os.getenv("WORKER_COMPILACAO_RETRY_MAX", 15))
WORKER_COMPILACAO_RETRY_INTERVALS = [
    5**n * 60 for n in range(1, WORKER_COMPILACAO_RETRY_MAX + 1)
]

# ==============================================================================
# 5. CONFIGURAÇÃO DE LOGGING & FLASK (Mantido do original)
# ==============================================================================
logger = logging.getLogger(APP_NAME)
if LOG_DEBUG:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)

log_format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_format)
logger.addHandler(console_handler)

if GRAFANA_URL and GRAFANA_URL.strip() != "":
    try:
        loki_handler = logging_loki.LokiHandler(
            url=GRAFANA_URL,
            tags={ENV.upper() + "_flask_api_skeleton": ENV.lower() + "_log"},
            version="1",
        )
        loki_handler.setFormatter(log_format)
        logger.addHandler(loki_handler)
    except Exception as e:
        logger.warning(f"Erro ao configurar Loki: {e}")

# Instância Global do Flask (Legacy support)
application = Flask("app")
CORS(application, resources={r"/*": {"origins": "*"}})

# ==============================================================================
# 6. CONFIGURAÇÃO DO SENTRY
# ==============================================================================
try:
    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration

    SENTRY_DSN = os.getenv("SENTRY_DSN")

    if SENTRY_DSN and SENTRY_DSN.strip() != "":
        sentry_logging = LoggingIntegration(
            level=logging.INFO,
            event_level=logging.ERROR,
        )
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[sentry_logging],
            traces_sample_rate=1.0,
        )
        logger.info("SENTRY CARREGADO")
except ImportError:
    pass # Sentry não instalado no ambiente dev
except Exception as e:
    logger.exception(f"Erro configurando o Sentry: {e}")