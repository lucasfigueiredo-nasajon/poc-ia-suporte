import os
import logging
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)

class Neo4jStatsDAO:
    def __init__(self):
        # Conecta usando o driver nativo, sem dependência do LangChain ou APOC
        uri = os.getenv("NEO4J_URI")
        username = os.getenv("NEO4J_USERNAME")
        password = os.getenv("NEO4J_PASSWORD")
        
        self.driver = GraphDatabase.driver(uri, auth=(username, password))

    def close(self):
        if self.driver:
            self.driver.close()

    def _execute_read(self, query, params=None):
        """Método auxiliar para executar queries de leitura com segurança"""
        if params is None:
            params = {}
            
        try:
            with self.driver.session() as session:
                result = session.run(query, params)
                # Converte o resultado (Result object) para uma lista de dicionários Python pura
                return [record.data() for record in result]
        except Exception as e:
            logger.error(f"Erro na query Neo4j: {e}")
            raise e

    def get_ticket_status_distribution(self):
        """Retorna contagem de tickets por classificação (UTIL vs INUTIL)."""
        query = """
        MATCH (t:Ticket)
        RETURN t.classificacao as label, count(t) as value
        ORDER BY value DESC
        """
        return self._execute_read(query)

    def get_top_sintomas(self, limit=10):
        """Retorna os sintomas mais frequentes vinculados a tickets."""
        # Se os sintomas forem nós conectados:
        # query = "MATCH (t:Ticket)-[:TEM_SINTOMA]->(s:Sintoma) RETURN s.nome as label, count(t) as value..."
        
        # Se o sintoma for apenas uma propriedade string no Ticket (como parece ser o caso agora):
        query = """
        MATCH (t:Ticket)
        WHERE t.sintoma IS NOT NULL AND t.sintoma <> ''
        RETURN t.sintoma as label, count(t) as value
        ORDER BY value DESC
        LIMIT $limit
        """
        return self._execute_read(query, {"limit": limit})
            
    def get_evolution_by_date(self):
        """Retorna tickets por data."""
        query = """
        MATCH (t:Ticket)
        WHERE t.datacriacao IS NOT NULL
        RETURN substring(t.datacriacao, 0, 10) as date, count(t) as count
        ORDER BY date ASC
        LIMIT 30
        """
        return self._execute_read(query)