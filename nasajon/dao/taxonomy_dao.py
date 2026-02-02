import logging
import json
from typing import List, Dict, Optional
from sqlalchemy import text
from nasajon.db_pool_config import db_pool

logger = logging.getLogger(__name__)

class TaxonomyDAO:
    def __init__(self):
        # Inicializa com Self-Healing
        self._init_db()

    def _init_db(self):
        """
        Cria a tabela unificada 'taxonomy_nodes' com suporte a hierarquia e metadados JSONB.
        """
        ddl = """
        CREATE TABLE IF NOT EXISTS taxonomy_nodes (
            id SERIAL PRIMARY KEY,
            type VARCHAR(50) NOT NULL, -- Ex: 'sintoma', 'recurso', 'erro', 'causa', 'solucao'
            name VARCHAR(255) NOT NULL,
            description TEXT,
            parent_id INTEGER REFERENCES taxonomy_nodes(id) ON DELETE SET NULL, -- Permite aninhamento infinito
            metadata JSONB DEFAULT '{}', -- Guarda campos específicos (ex: responsabilidade, exemplos, variacoes)
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(type, name, parent_id)
        );
        """
        try:
            with db_pool.begin() as conn:
                conn.execute(text(ddl))
        except Exception as e:
            logger.error(f"Erro init taxonomy: {e}")

    def get_nodes(self, taxonomy_type: str) -> List[Dict]:
        """
        Retorna todos os nós de um tipo específico.
        """
        query = text("""
            SELECT id, type, name, description, parent_id, metadata, active 
            FROM taxonomy_nodes 
            WHERE type = :type AND active = TRUE
            ORDER BY parent_id NULLS FIRST, name ASC
        """)
        with db_pool.connect() as conn:
            rows = conn.execute(query, {"type": taxonomy_type}).mappings().all()
            return [dict(row) for row in rows]

    def create_node(self, taxonomy_type: str, name: str, description: str, 
                   parent_id: Optional[int] = None, metadata: Dict = None) -> Optional[int]:
        """
        Cria um nó e RETORNA O ID gerado (ou None se falhar).
        """
        # Adicionamos 'RETURNING id' ao final da query
        query = text("""
            INSERT INTO taxonomy_nodes (type, name, description, parent_id, metadata)
            VALUES (:type, :name, :desc, :parent, :meta)
            RETURNING id
        """)
        
        if metadata is None: metadata = {}
        
        try:
            with db_pool.begin() as conn:
                # Usamos .scalar() para pegar o primeiro valor da primeira linha (o ID)
                new_id = conn.execute(query, {
                    "type": taxonomy_type, "name": name, 
                    "desc": description, "parent": parent_id,
                    "meta": json.dumps(metadata)
                }).scalar()
            return new_id
        except Exception as e:
            logger.error(f"Erro create taxonomy: {e}")
            return None

    def update_node(self, node_id: int, name: str, description: str, 
                    parent_id: Optional[int], metadata: Dict = None) -> bool:
        """
        Atualiza nó, incluindo movimentação de pai e metadados.
        """
        # Constroi query dinâmica para update apenas do que for passado? 
        # Não, update completo é mais seguro para garantir estado.
        query = text("""
            UPDATE taxonomy_nodes 
            SET name = :name, description = :desc, parent_id = :parent, metadata = :meta
            WHERE id = :id
        """)
        
        if metadata is None: metadata = {}

        try:
            with db_pool.begin() as conn:
                conn.execute(query, {
                    "id": node_id, "name": name, 
                    "desc": description, "parent": parent_id,
                    "meta": json.dumps(metadata)
                })
            return True
        except Exception as e:
            logger.error(f"Erro update taxonomy: {e}")
            return False

    def delete_node(self, node_id: int) -> bool:
        """Soft delete (apenas desativa)."""
        query = text("UPDATE taxonomy_nodes SET active = FALSE WHERE id = :id")
        try:
            with db_pool.begin() as conn:
                conn.execute(query, {"id": node_id})
            return True
        except Exception as e:
            logger.error(f"Erro delete taxonomy: {e}")
            return False