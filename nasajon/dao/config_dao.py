import json
import logging
from typing import Dict, Any
from sqlalchemy import text
from nasajon.db_pool_config import db_pool

logger = logging.getLogger(__name__)

class ConfigDAO:
    def get_config(self, key: str) -> Dict[str, Any]:
        """Recupera uma configuração pelo nome da chave."""
        query = text("SELECT config_value FROM system_configs WHERE config_key = :key")
        
        try:
            with db_pool.connect() as conn:
                result = conn.execute(query, {"key": key}).fetchone()
                if result:
                    # O driver pg8000 pode retornar string ou dict dependendo da versão
                    val = result[0]
                    if isinstance(val, str):
                        return json.loads(val)
                    return val
                return {}
        except Exception as e:
            logger.error(f"Erro ao ler config '{key}': {e}")
            return {}

    def update_config(self, key: str, value: Dict[str, Any]) -> bool:
        """Atualiza ou cria uma configuração."""
        query = text("""
            INSERT INTO system_configs (config_key, config_value, updated_at)
            VALUES (:key, :value, NOW())
            ON CONFLICT (config_key) 
            DO UPDATE SET config_value = :value, updated_at = NOW()
        """)
        
        # Garante que estamos salvando JSON válido stringificado para compatibilidade
        json_val = json.dumps(value) 
        
        try:
            with db_pool.connect() as conn:
                conn.execute(query, {"key": key, "value": json_val})
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Erro ao atualizar config '{key}': {e}")
            return False