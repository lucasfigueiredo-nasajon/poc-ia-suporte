import logging
import os
from functools import wraps
from flask import request, g

# --- CÓDIGO ORIGINAL (Mantido comentado para referência futura em PROD) ---
# from nsj_flask_auth import Auth, Scope, ProfileVendor
# from nasajon.settings import INTROSPECT_TOKEN, INTROSPECT_URL, DIRETORIO_URL
#
# auth = Auth(
#     scope=Scope.GRUPO_EMPRESARIAL,
#     profile_vendor=ProfileVendor.NSJ_AUTH_API,
#     introspect_token=INTROSPECT_TOKEN,
#     introspect_url=INTROSPECT_URL,
#     diretorio_base_uri=DIRETORIO_URL,
# )
# --------------------------------------------------------------------------

logger = logging.getLogger(__name__)

def requires_api_key_or_access_token():
    """
    [MOCK DE DESENVOLVIMENTO]
    Este decorador simula a autenticação da Nasajon.
    
    Motivo: Permitir testar o Agente (Runtime) sem precisar conectar
    no servidor de identidade (Introspect) neste momento.
    
    Comportamento:
    1. Loga a tentativa de acesso.
    2. Pega o Tenant do Header (X-Tenant-ID) e injeta no contexto.
    3. Permite a execução da rota.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 1. Auditoria Simples
            tenant_id = request.headers.get('X-Tenant-ID')
            logger.info(f"🔓 [AUTH BYPASS] Rota: {request.path} | Tenant: {tenant_id}")

            # 2. Injeção de Dependência (Simulando o que a lib faria)
            if tenant_id:
                # Garante que o Controller consiga ler g.tenant
                g.tenant = tenant_id
                
                # Se a aplicação esperar o tenant como int, já converte
                try:
                    g.tenant_id = int(tenant_id)
                except ValueError:
                    pass
            else:
                logger.warning("⚠️ [AUTH BYPASS] Requisição sem X-Tenant-ID!")

            # 3. Executa a função original (O Controller)
            return f(*args, **kwargs)
        return decorated_function
    return decorator