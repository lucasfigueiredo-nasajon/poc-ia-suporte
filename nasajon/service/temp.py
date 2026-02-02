import os
import logging
import random
from typing import List, Dict, Any

# LangChain & Agente
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_neo4j import Neo4jGraph, Neo4jVector
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_core.messages import AIMessage, HumanMessage

from nasajon.dao.chat_dao import ChatDAO
from nasajon.settings import OPENAI_API_KEY, OPENAI_MODEL, NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD
from nasajon.service.receptionist_agent import ReceptionistService

# Configs de Ambiente para LangChain
os.environ["NEO4J_URI"] = NEO4J_URI
os.environ["NEO4J_USERNAME"] = NEO4J_USERNAME
os.environ["NEO4J_PASSWORD"] = NEO4J_PASSWORD

logger = logging.getLogger(__name__)

# Cache de conexão (Singletons)
_GRAPH = None
_VECTOR = None

# --- INICIALIZAÇÃO DE COMPONENTES ---
def get_components():
    global _GRAPH, _VECTOR
    
    # 1. Conexão Grafo (para queries estruturadas Cypher)
    if not _GRAPH:
        try: 
            # FIX: refresh_schema=False impede o erro "Could not use APOC procedures"
            # Como já passamos o schema manualmente na Tool, não precisamos que ele leia do banco.
            _GRAPH = Neo4jGraph(refresh_schema=False)
        except Exception as e:
            logger.error(f"Erro ao conectar Grafo: {e}")

    # 2. Conexão Vetorial (para queries semânticas no Schema Rico)
    if not _VECTOR:
        try:
            _VECTOR = Neo4jVector.from_existing_index(
                embedding=OpenAIEmbeddings(api_key=OPENAI_API_KEY, model="text-embedding-3-small"),
                url=NEO4J_URI, username=NEO4J_USERNAME, password=NEO4J_PASSWORD,
                index_name="sintoma_vector",
                text_node_property="descricao",
                # Query mantida igual
                retrieval_query="""
                WITH node, score
                MATCH (node)<-[:APRESENTA_SINTOMA]-(t:Ticket)
                OPTIONAL MATCH (t)-[:POSSUI_CAUSA]->(c:Causa)
                RETURN node.descricao AS text, score, 
                {
                    ticket_id: t.id, 
                    titulo: t.titulo, 
                    solucao: t.passos_solucao,
                    causa: coalesce(c.descricao, 'Não estruturada'),
                    score: score
                } AS metadata
                """
            )
        except Exception as e:
            logger.warning(f"Erro ao conectar Vector Store: {e}")
            
    return _GRAPH, _VECTOR

# --- TOOLS DO AGENTE (COM PROMPTS ORIGINAIS) ---

@tool
def lookup_specific_data(query: str) -> str:
    """
    Use APENAS para buscar dados EXATOS e ESTRUTURADOS.
    Ex: "Erro 269", "Protocolo 123", "Erro no evento S-1200".
    Retorna dados técnicos do grafo.
    """
    graph, _ = get_components()
    if not graph: return "Erro DB."
    
    try:
        # Schema Hint focado na estrutura rica que criamos
        schema_hint = """
        Nodes: (:Ticket), (:Sintoma), (:Causa), (:Erro {codigo}), (:EventoEsocial {codigo}), (:Modulo {nome})
        Rels: (:Ticket)-[:GEROU_ERRO]->(:Erro), (:Ticket)-[:ENVOLVE_EVENTO]->(:EventoEsocial), (:Ticket)-[:APRESENTA_SINTOMA]->(:Sintoma)
        """
        
        # Seu Prompt de Engenharia de Cypher Original (Adaptado ao Schema Rico)
        prompt = f"""
        Você é um especialista em Neo4j. Gere uma query Cypher para responder: "{query}"
        
        Schema do Grafo: {schema_hint}
        
        REGRAS OBRIGATÓRIAS PARA A QUERY:

        1. **LIMPEZA DE STRINGS (CRUCIAL):**
           - O banco contem APENAS CÓDIGOS NUMÉRICOS OU ALFANUMÉRICOS LIMPOS.
           - Se o usuário pedir "Erro 176", você DEVE buscar: WHERE e.codigo CONTAINS "176"
           - **PROIBIDO:** WHERE e.codigo CONTAINS "Erro 176" (Isso retorna zero resultados agora).
           - Se pedir "Evento S-1200", busque: WHERE ev.codigo CONTAINS "1200" ou "S-1200".


        2. **NÃO concatene propriedades.** - ERRADO: (e:Erro {{codigo: "269 S-1200"}})
           - CORRETO: Encontre o erro "269" E o evento "S-1200" separadamente e conecte-os via Ticket.
           
        3. **Estratégia de Interseção (AND):**
           - Se a busca tem um número de erro (ex: 269) E um evento (ex: S-1200):
             MATCH (t:Ticket)-[:GEROU_ERRO]->(e:Erro)
             MATCH (t)-[:ENVOLVE_EVENTO]->(ev:EventoEsocial)
             WHERE e.codigo CONTAINS "269" AND ev.codigo CONTAINS "1200"
             RETURN t.protocolo, t.titulo, t.passos_solucao
             
        4. **Busca Flexível:** Use sempre `CONTAINS` para códigos, pois o usuário pode digitar parcial.
        
        Retorne APENAS a string da query Cypher, sem markdown.
        """
        
        llm = ChatOpenAI(api_key=OPENAI_API_KEY, model=OPENAI_MODEL, temperature=0)
        cypher_query = llm.invoke(prompt).content.strip().replace("```cypher","").replace("```","")
        
        logger.info(f"🔍 [Cypher Gerado]: {cypher_query}")
        result = graph.query(cypher_query)
        
        if not result: 
            return "Nenhum dado exato encontrado com esses critérios combinados."
            
        return str(result)
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
        # Busca top 3
        results = vector_store.similarity_search_with_score(problem_description, k=3)
        
        formatted_results = []
        for doc, score in results:
            meta = doc.metadata
            # Filtro Rígido Original
            if score < 0.70: 
                continue

            formatted_results.append(
                f"--- CASO RECUPERADO (Relevância: {score:.2f}) ---\n"
                f"Sintoma no Banco: {doc.page_content}\n"
                f"Causa: {meta.get('causa', 'N/A')}\n"
                f"Solução: {meta.get('solucao', 'N/A')}\n"
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

# --- SERVIÇO PRINCIPAL ---
class ChatService:
    def __init__(self, dao: ChatDAO):
        self.dao = dao
        get_components() # Warmup das conexões
        
        self.llm = ChatOpenAI(api_key=OPENAI_API_KEY, model="gpt-4-turbo", temperature=0)
        self.tools = [lookup_specific_data, search_similar_solutions, escalate_to_human]
        
        # --- SEU PROMPT ORIGINAL BLINDADO (COPIADO DO agent_suport.py) ---
        system_prompt = """
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
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder("chat_history"),
            ("user", "{input}"),
            MessagesPlaceholder("agent_scratchpad")
        ])
        
        self.agent = AgentExecutor(
            agent=create_openai_tools_agent(self.llm, self.tools, prompt), 
            tools=self.tools, 
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5
        )

    def handle_query(self, id_conversa: str, contexto_cliente: dict, texto_usuario: str, tenant: int, historico_msgs: list, **kwargs) -> Dict[str, Any]:
        # Converter histórico para formato LangChain
        chat_history = []

        # --- DEBUG FORÇADO (PRINT VAI PRO LOG DO POD) ---
        print(f"\n🛑 [DEBUG RASTREIO] Tenant: {tenant} | Conversa: {id_conversa}")
        print(f"🛑 [DEBUG RASTREIO] Recebido do Front: {len(historico_msgs)} mensagens.")
        print(f"🛑 [DEBUG RASTREIO] Conteúdo Bruto: {historico_msgs}")
        # ------------------------------------------------

        # 🔍 DEBUG: Logando o que chegou BRUTO do Front-end
        logger.info(f"🔍 [DEBUG MEMORIA] Recebido {len(historico_msgs)} msgs do Front (antes do filtro).")

        # Processamento (Mantendo sua lógica de pegar os últimos 6)
        for msg in historico_msgs[-6:]:
            role = msg.get('role')
            content = msg.get('content', '')
            
            if role == 'user':
                chat_history.append(HumanMessage(content=content))
            else:
                chat_history.append(AIMessage(content=content))

        # 🔍 DEBUG: Logando o que vai para a IA (Após conversão)
        logger.info(f"🔍 [DEBUG MEMORIA] Enviando {len(chat_history)} mensagens de contexto para o Agente:")
        for i, m in enumerate(chat_history):
            tipo = "👤 USER" if isinstance(m, HumanMessage) else "🤖 BOT "
            # Loga os primeiros 100 caracteres para não poluir demais
            logger.info(f"   [{i}] {tipo}: {m.content[:100]}...")

        # Contexto + Input
        sistema_ctx = contexto_cliente.get('sistema', '')
        input_ctx = f"[Sistema: {sistema_ctx}] {texto_usuario}" if sistema_ctx else texto_usuario
        
        try:
            logger.info(f"🤖 Agente iniciado para: {input_ctx}")
            
            result = self.agent.invoke({
                "input": input_ctx, 
                "chat_history": chat_history
            })
            
            resposta_final = result['output']
            
            # Log Simplificado para Auditoria
            tier = 3 if "N3" in resposta_final or "protocolo" in resposta_final else 1
            if "não encontrei" in resposta_final.lower(): tier = 4
                
            self.dao.insert_interaction_log(tenant, contexto_cliente.get('email'), texto_usuario, tier, resposta_final, {})
            
            return {
                "response": resposta_final,
                "metadata": {"tier": tier, "agent": "react_v8_full"}
            }
            
        except Exception as e:
            logger.error(f"Erro Crítico no Agente: {e}")
            raise e

    def close(self):
        pass