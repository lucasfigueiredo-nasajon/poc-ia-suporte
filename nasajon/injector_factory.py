from sqlalchemy.engine.base import Connection
from nasajon.dao.chat_dao import ChatDAO
from nasajon.service.chat_service import ChatService
from nasajon.dao.config_dao import ConfigDAO
from nasajon.service.config_service import ConfigService
from nasajon.service.knowledge_service import KnowledgeService
from nasajon.dao.taxonomy_dao import TaxonomyDAO
from nasajon.service.vision_service import VisionService
from nasajon.service.ingestion_service import IngestionService
from nasajon.dao.neo4j_stats_dao import Neo4jStatsDAO

# Adicionei imports de tipagem para o VSCode/PyCharm ajudarem no autocomplete
from nsj_gcf_utils.db_adapter2 import DBAdapter2

class InjectorFactory:
    _db_connection: Connection

    def __enter__(self):
        from nasajon.db_pool_config import db_pool
        self._db_connection = db_pool.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._db_connection:
            self._db_connection.close()

    def db_adapter(self) -> DBAdapter2:
        """Cria o adaptador de banco usando a conexão do pool atual"""
        return DBAdapter2(self._db_connection)

    # --- DAOs ---
    
    def chat_dao(self) -> ChatDAO:
        """Factory method para o DAO, injetando o adapter"""
        return ChatDAO(self.db_adapter())

    # --- SERVICES ---

    def chat_service(self) -> ChatService:
        """
        Instancia o ChatService injetando o DAO já configurado.
        Correção: Agora chama self.chat_dao() em vez de criar manualmente.
        """
        return ChatService(self.chat_dao())
    
    def knowledge_service(self):
        return KnowledgeService()
    
    def taxonomy_dao(self) -> TaxonomyDAO:
        """Factory para o DAO de Taxonomia"""
        return TaxonomyDAO(self.db_adapter())
    
    def neo4j_stats_dao(self) -> Neo4jStatsDAO:
        """Factory para o DAO de Estatísticas do Neo4j"""
        # Como o Neo4jStatsDAO usa variáveis de ambiente e não o adaptador SQL,
        # instanciamos diretamente.
        return Neo4jStatsDAO()
    
    def config_service(self) -> ConfigService: # Adicionado para consistência
        return ConfigService(ConfigDAO(self.db_adapter()))
    
    def vision_service(self) -> VisionService:
        """Instancia o serviço de visão computacional"""
        return VisionService()
    
    def ingestion_service(self) -> IngestionService:
        """
        [NOVO] Instancia o pipeline de ingestão injetando 
        as dependências de banco e IA.
        """
        return IngestionService(
            knowledge_service=self.knowledge_service(),
            vision_service=self.vision_service()
        )