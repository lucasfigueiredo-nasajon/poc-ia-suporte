import json
import logging
from typing import Dict, Any, Optional

# Utilitários do Framework
from nsj_gcf_utils.db_adapter2 import DBAdapter2

logger = logging.getLogger(__name__)

class ChatDAO:
    def __init__(self, db_adapter: DBAdapter2):
        """
        Recebe o adaptador de banco de dados injetado pela Factory.
        """
        self._db = db_adapter
        
        # --- AUTO-SETUP: Cria a tabela automaticamente no boot ---
        try:
            self._init_db()
        except Exception as e:
            # Apenas loga erro, não para a aplicação (pode ser falta de permissão DDL)
            logger.error(f"Erro no Auto-Setup do Banco: {e}")

    def _init_db(self):
        """
        Criação automática da estrutura relacional (Self-Healing).
        Isso resolve o erro 'relation does not exist'.
        """
        sql = """
        CREATE SCHEMA IF NOT EXISTS ia_suporte;
        
        CREATE TABLE IF NOT EXISTS ia_suporte.chat_interactions (
            id SERIAL PRIMARY KEY,
            tenant_id BIGINT,
            user_identifier VARCHAR(255),
            input_usuario TEXT,
            intent_detected VARCHAR(100),
            tier_final INT,
            debug_payload JSONB,
            response_text TEXT,
            data_hora TIMESTAMP DEFAULT NOW()
        );
        """
        # Executa sem parâmetros apenas para garantir a estrutura
        try:
            self._db.execute(sql)
        except Exception:
            # Ignora erros se a tabela já estiver sendo criada por outro processo concorrente
            pass

    def get_system_configs(self) -> Dict[str, Any]:
        """
        Recupera configurações dinâmicas (Thresholds, Feature Flags).
        """
        sql = """
        SELECT config_key, config_value 
        FROM ia_suporte.system_configs
        """
        
        configs = {}
        try:
            rows = self._db.execute(sql)
            for row in rows:
                key = row[0]
                value = row[1]
                
                if isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except:
                        pass
                
                configs[key] = value
                
            return configs
        except Exception as e:
            logger.error(f"Erro ao carregar configs do banco: {e}. Usando defaults.")
            return {}

    def insert_interaction_log(
        self, 
        tenant_id: int, 
        user_id: str, 
        input_text: str, 
        tier: int, 
        response_text: str, 
        debug_payload: Dict[str, Any]
    ):
        """
        Grava o rastro da interação para auditoria.
        """
        # SQL com parâmetros nomeados (:param) obrigatório para DBAdapter2 com kwargs
        sql = """
        INSERT INTO ia_suporte.chat_interactions (
            tenant_id, 
            user_identifier, 
            input_usuario, 
            intent_detected,
            tier_final, 
            debug_payload, 
            response_text
        ) VALUES (
            :tenant_id, :user_identifier, :input_usuario, :intent_detected,
            :tier_final, :debug_payload, :response_text
        )
        """
        
        try:
            # Serializa o payload de debug para JSONB
            payload_json = json.dumps(debug_payload, ensure_ascii=False)
            
            # Executa passando argumentos nomeados (kwargs)
            self._db.execute(
                sql, 
                tenant_id=tenant_id,
                user_identifier=user_id,
                input_usuario=input_text,
                intent_detected="BUSCAR", 
                tier_final=tier,
                debug_payload=payload_json,
                response_text=response_text
            )
        except Exception as e:
            logger.error(f"FALHA CRÍTICA AO GRAVAR LOG DE IA: {e}")

    def get_knowledge_base_article(self, embedding_id: str) -> Optional[Dict]:
        pass