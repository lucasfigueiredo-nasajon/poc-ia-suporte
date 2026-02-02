from flask import request, jsonify
from nasajon.injector_factory import InjectorFactory
from nasajon.auth import requires_api_key_or_access_token

@requires_api_key_or_access_token()
def get_thresholds():
    with InjectorFactory() as factory:
        service = factory.config_service()
        return jsonify(service.get_thresholds()), 200

@requires_api_key_or_access_token()
def update_thresholds():
    data = request.get_json() or {}
    
    try:
        # Usa valores padrão caso o JSON venha incompleto, mas ideal é vir tudo
        sniper = float(data.get('sniper', 0.88))
        high = float(data.get('high', 0.85))
        low = float(data.get('low', 0.60))
        
        with InjectorFactory() as factory:
            service = factory.config_service()
            service.update_thresholds(sniper, high, low)
            
        return jsonify({"status": "success", "message": "Thresholds atualizados com sucesso"}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Erro interno ao atualizar thresholds"}), 500