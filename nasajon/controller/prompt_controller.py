from flask import request, jsonify
from nasajon.dao.prompt_dao import PromptDAO
import logging
import traceback  # <--- Faltava este import crucial para debug

logger = logging.getLogger(__name__)

def handle_prompt_api():
    try:
        # Instancia o DAO (o _init_db roda aqui e pode gerar erro se o banco falhar)
        dao = PromptDAO()

        # --- GET (Retorna tudo) ---
        if request.method == 'GET':
            key = request.args.get('key')
            if not key: return jsonify({"error": "Key obrigatoria"}), 400
            
            data = dao.get_prompt_data(key)
            if data:
                return jsonify({
                    "status": "success", 
                    "key": key, 
                    "prompt": data['prompt_text'],
                    "description": data['description'],
                    "target_entity": data['target_entity'],
                    "source_file": data['source_file']
                }), 200
            else:
                return jsonify({"status": "not_found"}), 404

        # --- POST (Grava tudo) ---
        elif request.method == 'POST':
            data = request.get_json()
            key = data.get('key')
            new_text = data.get('prompt')
            
            # Novos Campos Opcionais
            description = data.get('description')
            target = data.get('target_entity')
            source = data.get('source_file')
            
            if not key or not new_text:
                return jsonify({"error": "Campos 'key' e 'prompt' obrigatorios"}), 400
                
            success = dao.update_prompt(key, new_text, description, target, source)
            
            if success:
                return jsonify({"status": "success"}), 200
            else:
                return jsonify({"error": "Erro ao gravar no banco (ver logs)"}), 500

    except Exception as e:
        # --- CAPTURA DE ERRO DETALHADA ---
        # Isso permite que o Streamlit mostre exatamente qual foi o erro SQL/Python
        error_trace = traceback.format_exc()
        logger.error(f"Erro Crítico na API de Prompts: {error_trace}")
        return jsonify({
            "error": "Erro Interno no Servidor", 
            "details": str(e),
            "traceback": error_trace
        }), 500