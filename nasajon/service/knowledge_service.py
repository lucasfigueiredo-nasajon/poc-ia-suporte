import os
import logging
from typing import List, Dict, Any

# Drivers e AI
from neo4j import GraphDatabase
from langchain_openai import OpenAIEmbeddings

# Configs
from nasajon.settings import OPENAI_API_KEY, NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD

logger = logging.getLogger(__name__)

class KnowledgeService:
    def __init__(self):
        # Conexão dedicada para ingestão
        self.driver = GraphDatabase.driver(
            NEO4J_URI, 
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
            max_connection_lifetime=300
        )
        self.embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY, model="text-embedding-3-small")

    def _ensure_indexes(self):
        """Cria índices e constraints para o Novo Schema Hierárquico"""
        try:
            with self.driver.session() as session:
                # 1. Índice Vetorial no DETALHE do Sintoma (onde está a riqueza semântica)
                # Nota: Mudamos de (s:Sintoma) para (d:DetalheSintoma)
                session.run("""
                CREATE VECTOR INDEX sintoma_detalhe_vector IF NOT EXISTS
                FOR (d:DetalheSintoma) ON (d.embedding)
                OPTIONS {indexConfig: {
                  `vector.dimensions`: 1536,
                  `vector.similarity_function`: 'cosine'
                }}
                """)
                
                # 2. Constraints de Unicidade
                session.run("CREATE CONSTRAINT ticket_id IF NOT EXISTS FOR (t:Ticket) REQUIRE t.id IS UNIQUE")
                
                # 3. Índices de Performance (Lookups rápidos para o Dashboard)
                session.run("CREATE INDEX cat_sintoma_nome IF NOT EXISTS FOR (c:CategoriaSintoma) ON (c.nome)")
                session.run("CREATE INDEX cat_causa_nome IF NOT EXISTS FOR (c:CategoriaCausa) ON (c.nome)")
                session.run("CREATE INDEX recurso_n2_nome IF NOT EXISTS FOR (r:RecursoNivel2) ON (r.nome)")
                session.run("CREATE INDEX erro_codigo IF NOT EXISTS FOR (e:Erro) ON (e.codigo)")
                session.run("CREATE INDEX evento_codigo IF NOT EXISTS FOR (ev:EventoEsocial) ON (ev.codigo)")
                
            logger.info("✅ Índices hierárquicos verificados com sucesso.")
        except Exception as e:
            logger.warning(f"⚠️ Aviso ao criar índices: {e}")

    def get_all_existing_ticket_ids(self) -> set:
        """Retorna IDs já cadastrados."""
        try:
            with self.driver.session() as session:
                result = session.run("MATCH (t:Ticket) RETURN t.id AS id")
                return {str(record["id"]) for record in result}
        except Exception as e:
            logger.error(f"Erro ao buscar IDs: {e}")
            return set()

    def repopulate_database(self, data: Any, clear_db: bool = True) -> Dict[str, Any]:
        """
        Ingestão Híbrida v2: Grava estrutura Hierárquica (Categoria -> Detalhe) 
        baseada na taxonomia validada pelo Postgres.
        """
        tickets = data if isinstance(data, list) else data.get('tickets', [])
        
        if not tickets:
            return {"error": "Lista de tickets vazia."}
        
        count = 0
        errors = []
        mode_msg = "FULL RESET" if clear_db else "APPEND MODE"
        
        logger.info(f"🚀 [KnowledgeService] Iniciando ingestão hierárquica ({mode_msg}) de {len(tickets)} tickets...")
        
        with self.driver.session() as session:
            # 1. Limpeza
            if clear_db:
                session.run("MATCH (n) DETACH DELETE n")
                logger.info("🧹 Banco limpo.")
                self._ensure_indexes()
            
            # 2. Loop de Ingestão
            for item in tickets:
                try:
                    t_core = item.get('ticket', {})
                    t_id = t_core.get('ticket_id')
                    
                    # Fontes de Dados
                    enrich = item.get('graph_enrichment', {})
                    struct = item.get('structured_taxonomy', {}) # JSON Validado pelo Postgres
                    
                    # Se não tiver estrutura validada, tenta pegar do KB simples (fallback de segurança)
                    # Mas idealmente o IngestionService garante o 'structured_taxonomy'
                    if not struct:
                        logger.warning(f"Ticket {t_id} ignorado: Sem taxonomia estruturada.")
                        continue

                    # --- PREPARAÇÃO DOS TEXTOS RICOS (PARA OS NÓS DE DETALHE) ---
                    
                    # Sintoma: Combina descrição do usuário + técnica
                    sintoma_rico = enrich.get('analise_sintoma', {})
                    desc_user = sintoma_rico.get('descricao_usuario', '')
                    desc_tec = sintoma_rico.get('descricao_tecnica', '')
                    detalhe_sintoma_texto = f"{desc_user}\n\n[Análise Técnica]: {desc_tec}".strip()
                    
                    if not detalhe_sintoma_texto: detalhe_sintoma_texto = "Sem detalhes."

                    # Causa: Vem da solução atômica
                    detalhe_causa_texto = enrich.get('solucao_atomica', {}).get('causa_raiz_curta', 'Causa não identificada')
                    
                    # Solução: Passos ordenados
                    passos = enrich.get('solucao_atomica', {}).get('passos_ordenados', [])
                    detalhe_solucao_texto = "\n".join(passos) if passos else "Solução não estruturada."

                    # Vetorização (Crucial): Embedamos o TEXTO RICO do detalhe, não a categoria
                    vector = self.embeddings.embed_query(detalhe_sintoma_texto)

                    # --- PARÂMETROS PARA CYPHER ---
                    params = {
                        "tid": t_id,
                        "protocolo": str(t_core.get('numeroprotocolo', 'N/A')),
                        "titulo": t_core.get('resumo_admin', 'Sem título'),
                        "sistema": t_core.get('sistema', 'Persona SQL'), # Nível 1 Fixo
                        
                        # Hierarquia de Recursos (Vem do struct validado)
                        "rec_n2": struct.get('recurso_nivel_2', {}).get('nome_validado', 'Geral'),
                        "rec_n3": struct.get('recurso_nivel_3', {}).get('nome_validado', 'Outro'),

                        # Sintoma (Categoria + Detalhe)
                        "cat_sintoma": struct.get('categoria_sintoma', {}).get('nome_validado', 'Outro'),
                        "det_sintoma_desc": detalhe_sintoma_texto,
                        "vector": vector,

                        # Causa
                        "cat_causa": struct.get('categoria_causa', {}).get('nome_validado', 'Outro'),
                        "det_causa_desc": detalhe_causa_texto,

                        # Solução
                        "cat_solucao": struct.get('categoria_solucao', {}).get('nome_validado', 'Outro'),
                        "det_solucao_desc": detalhe_solucao_texto,

                        # Listas Técnicas (Validadas)
                        "erros": [e.get('nome_validado') for e in struct.get('codigos_erro', [])],
                        "eventos": [ev.get('nome_validado') for ev in struct.get('eventos_esocial', [])],
                        
                        # Tags extras (opcional, mantendo compatibilidade)
                        "tags": item.get('knowledge_base', {}).get('tags', [])
                    }

                    # --- QUERY HIERÁRQUICA ---
                    query = """
                    MERGE (t:Ticket {id: $tid})
                    SET t.protocolo = $protocolo, 
                        t.titulo = $titulo,
                        t.passos_solucao = $det_solucao_desc, /* Compatibilidade visual */
                        t.ingested_at = datetime()

                    /* 1. HIERARQUIA DE RECURSOS (Sistema <- Módulo <- Funcionalidade) */
                    MERGE (r1:RecursoNivel1 {nome: $sistema})
                    MERGE (r2:RecursoNivel2 {nome: $rec_n2})
                    MERGE (r3:RecursoNivel3 {nome: $rec_n3})
                    
                    MERGE (r3)-[:PERTENCE_A]->(r2)
                    MERGE (r2)-[:PERTENCE_A]->(r1)
                    
                    /* O Ticket se conecta ao nível mais específico (N3) */
                    MERGE (t)-[:REFERENTE_A]->(r3)

                    /* 2. SINTOMA (Ticket -> Detalhe -> Categoria) */
                    MERGE (cs:CategoriaSintoma {nome: $cat_sintoma})
                    
                    /* O Detalhe é único por Ticket, usamos o ID do ticket para amarrar */
                    MERGE (ds:DetalheSintoma {id_ticket: $tid}) 
                    SET ds.descricao = $det_sintoma_desc,
                        ds.embedding = $vector
                    
                    MERGE (ds)-[:DA_CATEGORIA]->(cs)
                    MERGE (t)-[:APRESENTA_SINTOMA]->(ds)

                    /* 3. CAUSA (Ticket -> Detalhe -> Categoria) */
                    MERGE (cc:CategoriaCausa {nome: $cat_causa})
                    MERGE (dc:DetalheCausa {id_ticket: $tid})
                    SET dc.descricao = $det_causa_desc
                    
                    MERGE (dc)-[:DA_CATEGORIA]->(cc)
                    MERGE (t)-[:POSSUI_CAUSA]->(dc)

                    /* 4. SOLUÇÃO (Ticket -> Detalhe -> Categoria) */
                    MERGE (csol:CategoriaSolucao {nome: $cat_solucao})
                    MERGE (dsol:DetalheSolucao {id_ticket: $tid})
                    SET dsol.descricao = $det_solucao_desc
                    
                    MERGE (dsol)-[:DA_CATEGORIA]->(csol)
                    MERGE (t)-[:APLICOU_SOLUCAO]->(dsol)

                    /* 5. ENTIDADES TÉCNICAS */
                    FOREACH (cod IN $erros | 
                        MERGE (e:Erro {codigo: cod}) 
                        MERGE (t)-[:GEROU_ERRO]->(e)
                    )
                    
                    FOREACH (ev IN $eventos | 
                        MERGE (evt:EventoEsocial {codigo: ev}) 
                        MERGE (t)-[:ENVOLVE_EVENTO]->(evt)
                    )
                    
                    FOREACH (tag IN $tags | 
                        MERGE (tg:Tag {nome: tag}) 
                        MERGE (t)-[:POSSUI_TAG]->(tg)
                    )
                    """
                    
                    session.run(query, params)
                    count += 1
                    
                except Exception as e:
                    logger.error(f"❌ Falha ao gravar ticket {item.get('ticket', {}).get('ticket_id')}: {e}")
                    errors.append(str(e))

        logger.info(f"✅ Ingestão finalizada. {count} importados com sucesso.")
        return {"status": "success", "imported": count, "skipped_errors": len(errors), "mode": mode_msg}

    def close(self):
        if self.driver:
            self.driver.close()