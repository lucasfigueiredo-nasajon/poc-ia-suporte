import logging
import json
from flask import request, Response, stream_with_context, jsonify
from nasajon.injector_factory import InjectorFactory
from nasajon.auth import requires_api_key_or_access_token

logger = logging.getLogger(__name__)

@requires_api_key_or_access_token()
def handle_ingestion():
    """
    Endpoint de Streaming para o Pipeline de Ingestão (NDJSON).
    A resposta é enviada linha a linha para permitir feedback visual no frontend.
    """
    try:
        # force=True garante leitura mesmo se o header Content-Type não for application/json exato
        data = request.get_json(force=True)
        tickets_brutos = data.get('tickets', [])
        clear_db = data.get('clear_db', False)

        if not tickets_brutos:
            return jsonify({"error": "Nenhum ticket enviado."}), 400

        def generate():
            """Função geradora que mantém o contexto da aplicação ativo durante o stream"""
            try:
                # O InjectorFactory deve ser usado dentro do gerador para manter a sessão de banco viva
                with InjectorFactory() as factory:
                    service = factory.ingestion_service()
                    
                    # Consome o generator do serviço e repassa para o cliente HTTP
                    # O serviço já cuida do filtro de persona e deduplicação interna
                    for event in service.run_pipeline_stream(tickets_brutos, clear_db=clear_db):
                        yield event

            except Exception as e:
                logger.exception(f"Erro durante o streaming no Controller: {e}")
                # Em caso de erro fatal no meio do stream, tentamos enviar um JSON de erro final
                yield json.dumps({"step": "error", "msg": f"🔥 Erro Interno no Servidor: {str(e)}"}) + "\n"

        # Retorna a resposta com mimetype específico para stream de JSON (New-Line Delimited JSON)
        response = Response(
            stream_with_context(generate()), 
            mimetype='application/x-ndjson'
        )
        
        # --- BLOCO CRÍTICO PARA NGINX/KUBERNETES ---
        # Desativa o buffer do Nginx para que o stream chegue em tempo real
        response.headers['X-Accel-Buffering'] = 'no'
        response.headers['Cache-Control'] = 'no-cache'
        
        return response

    except Exception as e:
        logger.exception(f"Erro ao iniciar IngestionController: {e}")
        return jsonify({"error": str(e)}), 500