import logging
from typing import Optional, Dict
from sqlalchemy import text
from nasajon.db_pool_config import db_pool

logger = logging.getLogger(__name__)

class PromptDAO:
    def __init__(self):
        try:
            self._init_db()
        except Exception as e:
            logger.error(f"FALHA CRÍTICA NO SETUP DO BANCO (PROMPTS): {e}")

    def _init_db(self):
        """
        Cria tabela e seed inicial.
        Usa db_pool.begin() para transação automática (Commit no final do bloco).
        """
        ddl = """
        CREATE TABLE IF NOT EXISTS system_prompts (
            prompt_key VARCHAR(50) PRIMARY KEY,
            prompt_text TEXT NOT NULL,
            description VARCHAR(255),
            target_entity VARCHAR(100),
            source_file VARCHAR(255),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        """
        
        seed_sql = """
        INSERT INTO system_prompts (prompt_key, description, target_entity, source_file, prompt_text)
        VALUES (
            'persona_specialist', 
            'Prompt do Agente N2 (Persona/eSocial)',
            'PersonaSpecialistAgent',
            'nasajon/service/persona_specialist_agent.py',
            'Você é um Especialista de Suporte Sênior...'
        )
        ON CONFLICT (prompt_key) DO UPDATE SET
            target_entity = EXCLUDED.target_entity,
            source_file = EXCLUDED.source_file;
        """

        # FIX: Usa .begin() para gerenciar a transação automaticamente
        with db_pool.begin() as conn:
            conn.execute(text(ddl))
            
            try:
                # Tenta criar colunas se não existirem (Migration manual)
                conn.execute(text("ALTER TABLE system_prompts ADD COLUMN IF NOT EXISTS target_entity VARCHAR(100);"))
                conn.execute(text("ALTER TABLE system_prompts ADD COLUMN IF NOT EXISTS source_file VARCHAR(255);"))
            except Exception as e_mig:
                logger.warning(f"Migração ignorada: {e_mig}")

            conn.execute(text(seed_sql))
            # O commit acontece automaticamente aqui ao sair do 'with'

    def get_prompt_data(self, key: str) -> Optional[Dict]:
        query = text("""
            SELECT prompt_text, description, target_entity, source_file 
            FROM system_prompts 
            WHERE prompt_key = :key
        """)
        # Leitura não precisa de transação de escrita, .connect() serve
        with db_pool.connect() as conn:
            result = conn.execute(query, {"key": key}).mappings().fetchone()
            if result:
                return dict(result)
            return None

    def get_prompt(self, key: str) -> Optional[str]:
        data = self.get_prompt_data(key)
        return data['prompt_text'] if data else None

    def update_prompt(self, key: str, text_content: str, description: str = None, 
                      target_entity: str = None, source_file: str = None) -> bool:
        """
        Atualiza o prompt.
        Usa db_pool.begin() para evitar erro de 'conn.commit()'.
        """
        query = text("""
            INSERT INTO system_prompts (prompt_key, prompt_text, description, target_entity, source_file, updated_at)
            VALUES (:key, :text, :desc, :target, :source, NOW())
            ON CONFLICT (prompt_key) 
            DO UPDATE SET 
                prompt_text = :text, 
                description = COALESCE(:desc, system_prompts.description),
                target_entity = COALESCE(:target, system_prompts.target_entity),
                source_file = COALESCE(:source, system_prompts.source_file),
                updated_at = NOW()
        """)
        
        # FIX: Usa .begin() e remove o conn.commit() manual que estava falhando
        with db_pool.begin() as conn:
            conn.execute(query, {
                "key": key, "text": text_content, "desc": description,
                "target": target_entity, "source": source_file
            })
            # O commit é automático aqui
        
        return True