import logging
from flask import Blueprint, jsonify
from nsj_rest_lib.healthcheck_config import HealthCheckConfig
from nsj_rest_lib2.controller.dynamic_controller import setup_dynamic_routes

# 1. Imports da Aplicação
from nasajon.settings import application
from nasajon.injector_factory_multibanco import InjectorFactoryMultibanco
from nasajon.injector_factory import InjectorFactory

# 2. Import dos Controllers
from nasajon.controller.queries_controller import handle_queries, ingest_knowledge_base, debug_cypher_tool
from nasajon.controller.taxonomy_controller import bp_taxonomy
from nasajon.controller.ingestion_controller import handle_ingestion
from nasajon.controller.prompt_controller import handle_prompt_api
from nasajon.controller.stats_controller import bp_stats

# --- CONFIGURAÇÃO DE HEALTHCHECK ---
HealthCheckConfig(
    flask_application=application, 
    injector_factory_class=InjectorFactory
).config(True, False)

# --- CONFIGURAÇÃO DE ROTAS (BLUEPRINT PRINCIPAL) ---
# Define o prefixo global /nsj-ia-suporte
bp_prod = Blueprint('nsj_ia_suporte_prod', __name__, url_prefix='/nsj-ia-suporte')

# Rota 1: Chat Principal (/nsj-ia-suporte/queries)
bp_prod.add_url_rule('/queries', view_func=handle_queries, methods=['POST'])

# Rota 2: Ingestão de Dados (/nsj-ia-suporte/ingest)
bp_prod.add_url_rule('/ingest', view_func=ingest_knowledge_base, methods=['POST'])

# Rota 3: Debug Cypher
bp_prod.add_url_rule('/debug/cypher', view_func=debug_cypher_tool, methods=['POST'])

# Rota 4: Ingestão Profissional com Pipeline de IA (/nsj-ia-suporte/ingest-pipeline)
bp_prod.add_url_rule('/ingest-pipeline', view_func=handle_ingestion, methods=['POST'])

# Rota 5: Gestão de Prompts via Banco de Dados (/nsj-ia-suporte/prompts)
bp_prod.add_url_rule('/prompts', view_func=handle_prompt_api, methods=['GET', 'POST'])


# Rota de Debug
@bp_prod.route('/ping', methods=['GET'])
def ping():
    return jsonify({"status": "pong", "env": "production_ingest_ready"}), 200

# Registra o Blueprint Principal
application.register_blueprint(bp_prod)

# --- [NOVO] REGISTRO DO BLUEPRINT DE TAXONOMIA ---
# Registramos com o prefixo completo para ficar organizado e compatível com o script de upload
# A URL final será: /nsj-ia-suporte/taxonomies/sintomas, etc.
application.register_blueprint(bp_taxonomy, url_prefix='/nsj-ia-suporte/taxonomies')

application.register_blueprint(bp_stats, url_prefix='/nsj-ia-suporte/stats')

# --- ROTAS DINÂMICAS (LEGADO) ---
setup_dynamic_routes(
    application, 
    injector_factory=InjectorFactoryMultibanco, 
    escopo_in_url=True
)

if __name__ == "__main__":
    application.run(port=5000)