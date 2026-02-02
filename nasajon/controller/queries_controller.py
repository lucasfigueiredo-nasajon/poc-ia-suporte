import logging
from flask import request, g, jsonify
from nsj_gcf_utils.json_util import json_dumps

# --- FIX DE COMPATIBILIDADE ---
try:
    from nsj_gcf_utils.rest_error_util import RestException
except ImportError:
    # ERPException antiga não aceita status_code no construtor
    from nsj_gcf_utils.rest_error_util import ERPException as RestException
# ------------------------------

from nasajon.injector_factory import InjectorFactory
from nasajon.auth import requires_api_key_or_access_token

logger = logging.getLogger(__name__)

def raise_rest_exception(msg, code=None):
    # Tenta assinatura nova, se falhar, usa a antiga (posicional)
    try:
        raise RestException(msg, status_code=code or 500)
    except TypeError:
        # Assinatura legada da Nasajon: ERPException(message, code, ...)
        raise RestException(msg, "ERROR_CODE")

@requires_api_key_or_access_token()
def handle_queries():
    """
    Endpoint principal para interação com o Agente de Suporte.
    """
    try:
        # 1. Extração de Dados
        # force=True garante parse mesmo se o Content-Type estiver errado
        data = request.get_json(force=True) 
        
        id_conversa = data.get('conversation_id')
        texto_usuario = data.get('message')
        historico = data.get('history', [])
        contexto = data.get('context', {})
        
        # 2. Segurança: Identificação do Tenant
        tenant = getattr(g, 'tenant', None)
        
        if not tenant:
            tenant = request.headers.get('X-Tenant-ID')
            
        if not tenant:
            raise_rest_exception("Tenant ID não identificado. Acesso negado.", 403)
            
        if not texto_usuario:
            raise_rest_exception("O campo 'message' é obrigatório.", 400)

        # 3. Instanciação via Factory
        with InjectorFactory() as factory:
            service = factory.chat_service()
            
            # 4. Execução da Lógica de Negócio
            response_data = service.handle_query(
                id_conversa=id_conversa,
                contexto_cliente=contexto,
                texto_usuario=texto_usuario,
                tenant=int(tenant),
                historico_msgs=historico
            )
            
            # 5. Resposta
            return json_dumps(response_data), 200

    except RestException as e:
        logger.warning(f"Erro REST controlado: {e}")
        raise e
    except Exception as e:
        logger.exception(f"Erro inesperado no QueriesController: {e}")
        # Usa a função segura para não causar TypeError
        raise_rest_exception(f"Erro interno: {str(e)}", 500)

# --- NOVA FUNÇÃO DE INGESTÃO (Sem decorator @app.route) ---
def ingest_knowledge_base():
    try:
        data = request.json
        if not isinstance(data, (list, dict)): 
             return jsonify({"error": "Formato inválido"}), 400
        
        # Lê o parâmetro da URL query string. Default é 'true' para manter comportamento seguro.
        # Ex: /ingest?clear=false
        clear_param = request.args.get('clear_db', 'true').lower() == 'true'

        logger.info(f"Ingestão iniciada via Controller. Clear DB? {clear_param}")

        with InjectorFactory() as factory:
            service = factory.knowledge_service()
            # Passa o parâmetro para o serviço
            result = service.repopulate_database(data, clear_db=clear_param)
        
        return jsonify(result), 200
    except Exception as e:
        logger.exception(f"Erro na ingestão: {e}")
        return jsonify({"error": str(e)}), 500
    
def debug_cypher_tool():
    """
    ENDPOINT DE DIAGNÓSTICO (USO INTERNO)
    Permite rodar queries Cypher arbitrárias para verificar o banco.
    POST /debug/cypher
    Body: { "query": "MATCH (n) RETURN count(n)" }
    """
    try:
        # Segurança básica: verificar tenant ou chave (opcional, mas recomendado)
        # tenant = request.headers.get('X-Tenant-ID')
        
        data = request.json
        cypher = data.get('query')
        
        if not cypher:
            return jsonify({"error": "Query vazia"}), 400

        # Usa o driver direto para raw query
        from nasajon.settings import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD
        from neo4j import GraphDatabase
        
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
        
        with driver.session() as session:
            result = session.run(cypher)
            # Converte o resultado para lista de dicts
            output = [dict(record) for record in result]
            
        driver.close()
        return jsonify({"count": len(output), "data": output}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500