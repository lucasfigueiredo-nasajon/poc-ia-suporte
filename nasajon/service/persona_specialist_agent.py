import os
import logging
import random
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_neo4j import Neo4jGraph, Neo4jVector
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_core.messages import AIMessage, HumanMessage

from nasajon.dao.prompt_dao import PromptDAO
from nasajon.settings import OPENAI_API_KEY, OPENAI_MODEL, NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD

# Configs de Ambiente
os.environ["NEO4J_URI"] = NEO4J_URI
os.environ["NEO4J_USERNAME"] = NEO4J_USERNAME
os.environ["NEO4J_PASSWORD"] = NEO4J_PASSWORD

logger = logging.getLogger(__name__)

# --- SINGLETONS DE CONEXÃO ---
_GRAPH = None
_VECTOR = None

DEFAULT_SYSTEM_PROMPT = """
Você é um Especialista de Suporte Sênior da Nasajon ERP (Persona/eSocial).
Sua autoridade é baseada na PRECISÃO. Você nunca chuta uma resposta e nunca confunde o usuário com excesso de informação.

🧠 PROTOCOLO DE DECISÃO BLINDADO (Chain of Thought):

1. **COLETA DE DADOS:**
   - Analise a entrada do usuário e o Histórico da Conversa.
   - Use as ferramentas (`lookup_specific_data` ou `search_similar_solutions`) para buscar tickets na base.

2. **ANÁLISE DE RESULTADOS (O Grande Filtro):**
   Compare os campos 'passos_solucao' dos tickets retornados.

   ---
   🚦 **DECISÃO DE FLUXO (STOP & THINK):**

   **CENÁRIO A: MATCH PERFEITO / CONSENSO**
   - *Condição:* Encontrou apenas um ticket relevante OU vários tickets que dizem exatamente a mesma coisa.
   - *Ação:* ✅ Forneça a solução técnica passo a passo imediatamente.

   **CENÁRIO B: AMBIGUIDADE / CONFLITO (PERIGO ⚠️)**
   - *Condição:* Encontrou tickets com soluções DIFERENTES (ex: Ticket A manda "Configurar Rubrica", Ticket B manda "Alterar Matrícula").
   - *Regra de Bloqueio:* ⛔ **É ESTRITAMENTE PROIBIDO listar, resumir ou mencionar as soluções neste momento.** Oculte o conhecimento técnico temporariamente.
   - *Ação Tática:* Identifique a diferença de contexto entre os tickets (ex: Evento S-1200 vs S-2299) e faça **UMA ÚNICA PERGUNTA** de desambiguação para o usuário.

   **CENÁRIO C: VÁZIO / DESCONHECIDO**
   - *Condição:* Buscou um código específico (ex: "Erro 9999") e a tool retornou vazio/nulo.
   - *Ação:* 🚨 Use a tool `escalate_to_human` IMEDIATAMENTE. Não faça perguntas genéricas ("Acontece sempre?").

   ---

❌ **O QUE NUNCA FAZER (EXEMPLOS DE ERRO):**
- *Erro:* "Encontrei duas possibilidades. A opção 1 é X, a opção 2 é Y. Qual você quer?" (Isso é proibido).
- *Erro:* "Tente a solução A. Se não der certo, volte aqui." (Isso é suporte preguiçoso).

✅ **O QUE FAZER (EXEMPLO CORRETO - CENÁRIO B):**
- *Raciocínio Interno:* Vejo que o Erro 269 tem uma solução para cadastro geral e outra específica para o S-1200 com código 1099. Não posso dar a resposta ainda.
- *Resposta para o Usuário:* "Encontrei cenários distintos para o Erro 269. Para eu te passar o procedimento exato e não colocar seu cadastro em risco, preciso confirmar: Esse erro apareceu especificamente durante o envio do evento **S-1200** pedindo alteração de código?"

Lembre-se: O usuário confia em você. Se houver dúvida, PERGUNTE antes de instruir.
"""

DEFAULT_CYPHER_PROMPT = """
Você é um especialista em Neo4j. Gere uma query Cypher para responder: "{{QUERY}}"

Schema do Grafo: 
{{SCHEMA}}

REGRAS OBRIGATÓRIAS PARA A QUERY:
1. **LIMPEZA DE STRINGS (CRUCIAL):**
   - O banco contem APENAS CÓDIGOS NUMÉRICOS OU ALFANUMÉRICOS LIMPOS.
   - Se o usuário pedir "Erro 176", você DEVE buscar: WHERE e.codigo CONTAINS "176"
   - **PROIBIDO:** WHERE e.codigo CONTAINS "Erro 176" (Isso retorna zero resultados).
   - Se pedir "Evento S-1200", busque: WHERE ev.codigo CONTAINS "1200" ou "S-1200".

2. **NÃO concatene propriedades.** - ERRADO: (e:Erro {codigo: "269 S-1200"})
   - CORRETO: Encontre o erro "269" E o evento "S-1200" separadamente e conecte-os via Ticket.
   
3. **Estratégia de Interseção (AND):**
   - Se a busca tem um número de erro (ex: 269) E um evento (ex: S-1200):
     MATCH (t:Ticket)-[:GEROU_ERRO]->(e:Erro)
     MATCH (t)-[:ENVOLVE_EVENTO]->(ev:EventoEsocial)
     WHERE e.codigo CONTAINS "269" AND ev.codigo CONTAINS "1200"
     RETURN t.protocolo, t.titulo, t.passos_solucao
     
4. **Busca Flexível:** Use sempre `CONTAINS` para códigos.

Retorne APENAS a string da query Cypher, sem markdown.
"""

def get_components():
    global _GRAPH, _VECTOR
    
    if not _GRAPH:
        try: 
            _GRAPH = Neo4jGraph(refresh_schema=False)
        except Exception as e:
            logger.error(f"Erro ao conectar Grafo: {e}")

    if not _VECTOR:
        try:
            # --- ATUALIZAÇÃO PARA SCHEMA HIERÁRQUICO ---
            _VECTOR = Neo4jVector.from_existing_index(
                embedding=OpenAIEmbeddings(api_key=OPENAI_API_KEY, model="text-embedding-3-small"),
                url=NEO4J_URI, username=NEO4J_USERNAME, password=NEO4J_PASSWORD,
                index_name="sintoma_detalhe_vector", # <--- Nome atualizado
                text_node_property="descricao",      # <--- Propriedade do DetalheSintoma
                retrieval_query="""
                WITH node, score
                /* O nó recuperado pelo vetor é um DetalheSintoma */
                MATCH (node)<-[:APRESENTA_SINTOMA]-(t:Ticket)
                
                /* Buscamos o contexto das Categorias e Recursos */
                OPTIONAL MATCH (node)-[:DA_CATEGORIA]->(cat_s:CategoriaSintoma)
                OPTIONAL MATCH (t)-[:REFERENTE_A]->(r3:RecursoNivel3)
                OPTIONAL MATCH (t)-[:POSSUI_CAUSA]->(dc:DetalheCausa)-[:DA_CATEGORIA]->(cat_c:CategoriaCausa)
                OPTIONAL MATCH (t)-[:APLICOU_SOLUCAO]->(dsol:DetalheSolucao)-[:DA_CATEGORIA]->(cat_sol:CategoriaSolucao)

                RETURN node.descricao AS text, score, 
                {
                    ticket_id: t.id, 
                    titulo: t.titulo, 
                    modulo: coalesce(r3.nome, 'Geral'),
                    categoria_sintoma: coalesce(cat_s.nome, 'Geral'),
                    solucao: coalesce(dsol.descricao, t.passos_solucao, 'Solução não estruturada'),
                    causa: coalesce(dc.descricao, 'Não identificada'),
                    score: score
                } AS metadata
                """
            )
        except Exception as e:
            logger.warning(f"Erro ao conectar Vector Store: {e}")
            
    return _GRAPH, _VECTOR

# --- TOOLS (Copiadas e Mantidas Idênticas) ---

@tool
def lookup_specific_data(query: str) -> str:
    """
    Use APENAS para buscar dados EXATOS e ESTRUTURADOS.
    Ex: "Erro 269", "Protocolo 123", "Tickets do eSocial".
    """
    graph, _ = get_components()
    if not graph: return "Erro DB."
    
    try:
        # --- ATUALIZAÇÃO DO SCHEMA HINT ---
        schema_hint = """
        Nós Principais:
        (:Ticket) - Nó central.
        (:DetalheSintoma {descricao}) -> (:CategoriaSintoma {nome})
        (:DetalheCausa {descricao}) -> (:CategoriaCausa {nome})
        (:DetalheSolucao {descricao}) -> (:CategoriaSolucao {nome})
        
        Hierarquia de Sistema:
        (:RecursoNivel1 {nome}) <-[:PERTENCE_A]- (:RecursoNivel2 {nome}) <-[:PERTENCE_A]- (:RecursoNivel3 {nome})
        
        Listas Técnicas:
        (:Erro {codigo}) <-[:GEROU_ERRO]- (:Ticket)
        (:EventoEsocial {codigo}) <-[:ENVOLVE_EVENTO]- (:Ticket)
        
        Relacionamentos do Ticket:
        (:Ticket)-[:APRESENTA_SINTOMA]->(:DetalheSintoma)
        (:Ticket)-[:POSSUI_CAUSA]->(:DetalheCausa)
        (:Ticket)-[:REFERENTE_A]->(:RecursoNivel3)
        """
        
        try:
            dao = PromptDAO()
            db_prompt = dao.get_prompt('tool_lookup_cypher')
        except Exception:
            db_prompt = None

        raw_prompt = db_prompt if db_prompt else DEFAULT_CYPHER_PROMPT
        final_prompt = raw_prompt.replace("{{SCHEMA}}", schema_hint).replace("{{QUERY}}", query)
        
        llm = ChatOpenAI(api_key=OPENAI_API_KEY, model="gpt-4o", temperature=0)
        cypher_query = llm.invoke(final_prompt).content.strip().replace("```cypher","").replace("```","")
        
        logger.info(f"🔍 [Cypher Gerado]: {cypher_query}")
        
        try:
            result = graph.query(cypher_query)
            return str(result) if result else "Nenhum dado exato encontrado."
        except Exception as cypher_error:
            return f"Erro de sintaxe na query gerada: {cypher_error}"

    except Exception as e:
        return f"Erro técnico na busca estruturada: {e}"

@tool
def search_similar_solutions(problem_description: str) -> str:
    """
    Use para buscar soluções baseadas em sintomas ou descrições de problemas.
    Ex: "Sistema travando", "Cálculo errado", "Lentidão".
    """
    _, vector_store = get_components()
    if not vector_store: return "Erro: Busca vetorial indisponível."

    logger.info(f"🧠 [Vector]: Buscando por '{problem_description}'")
    
    try:
        results = vector_store.similarity_search_with_score(problem_description, k=3)
        
        formatted_results = []
        for doc, score in results:
            meta = doc.metadata
            if score < 0.70: continue

            # --- ATUALIZAÇÃO DA VISUALIZAÇÃO ---
            formatted_results.append(
                f"--- CASO RECUPERADO (Relevância: {score:.2f}) ---\n"
                f"Módulo: {meta.get('modulo')} | Categoria: {meta.get('categoria_sintoma')}\n"
                f"Sintoma Detalhado: {doc.page_content}\n"
                f"Causa Provável: {meta.get('causa')}\n"
                f"Solução: {meta.get('solucao')}\n"
                f"--------------------------------------------------\n"
            )
        
        if not formatted_results:
            return "Nenhum ticket similar encontrado com relevância suficiente."
            
        return "\n".join(formatted_results)
    except Exception as e:
        return f"Erro na busca: {e}"

@tool
def escalate_to_human(resumo_problema: str) -> str:
    """
    Use esta ferramenta APENAS quando:
    1. O usuário disser que nenhuma das soluções sugeridas funcionou ("Nenhum deles", "Não resolveu").
    2. O usuário pedir explicitamente para falar com um atendente/humano.
    
    A entrada deve ser um resumo curto do problema que não foi resolvido.
    """
    protocolo = random.randint(500000, 999999)
    logger.info(f"🚨 [ESCALONAMENTO] Abrindo chamado N3 para: {resumo_problema}")
    
    return (f"Solicitação enviada para a fila N3. "
            f"Protocolo de Atendimento gerado: #{protocolo}. "
            f"Um analista humano entrará em contacto em até 2 horas.")

# --- CLASSE DO AGENTE ---

class PersonaSpecialistAgent:
    def __init__(self):
        # Warmup das conexões
        get_components()
        
        self.llm = ChatOpenAI(api_key=OPENAI_API_KEY, model="gpt-4-turbo", temperature=0)
        self.tools = [lookup_specific_data, search_similar_solutions, escalate_to_human]
        
        # --- CARREGAMENTO DINÂMICO DO PROMPT ---
        try:
            dao = PromptDAO()
            # Tenta buscar no banco pela chave definida
            db_prompt = dao.get_prompt('persona_specialist')
        except Exception as e:
            logger.error(f"Falha ao conectar no banco para buscar prompt: {e}")
            db_prompt = None

        if db_prompt:
            logger.info("🤖 Prompt 'persona_specialist' carregado do Banco de Dados.")
            system_prompt = db_prompt
        else:
            logger.warning("⚠️ Prompt não encontrado no banco ou erro de conexão. Usando FALLBACK local.")
            system_prompt = DEFAULT_SYSTEM_PROMPT
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder("chat_history"),
            ("user", "{input}"),
            MessagesPlaceholder("agent_scratchpad")
        ])
        
        self.agent_executor = AgentExecutor(
            agent=create_openai_tools_agent(self.llm, self.tools, prompt), 
            tools=self.tools, 
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5
        )

    def run(self, input_text: str, chat_history: list) -> str:
        """Executa o agente com o input processado."""
        result = self.agent_executor.invoke({
            "input": input_text, 
            "chat_history": chat_history
        })
        return result['output']