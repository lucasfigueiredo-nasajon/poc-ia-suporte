import logging
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from nasajon.settings import OPENAI_API_KEY
from nasajon.dao.prompt_dao import PromptDAO
from nasajon.dao.taxonomy_dao import TaxonomyDAO  # <--- NOVA IMPORTAÇÃO

logger = logging.getLogger(__name__)

# Fallback caso o banco falhe, para o agente não parar
FALLBACK_PRODUTOS = """
- Persona SQL (RH, Folha, eSocial)
- Contábil SQL (Contabilidade)
- Scritta SQL (Fiscal)
- Finanças SQL (Financeiro)
"""

DEFAULT_RECEPTIONIST_PROMPT = """
Você é a Recepcionista da IA de Suporte da Nasajon.
Sua função é ler o HISTÓRICO e a NOVA MENSAGEM para direcionar o usuário. 
Você precisa identificar sobre qual PRODUTO o usuário está falando e direcionar o atendimento.

CATÁLOGO DE PRODUTOS NASAJON (VINDOS DO BANCO DE DADOS):
{{PRODUTOS}}

🕵️‍♂️ **ANÁLISE DE CONTINUIDADE (REGRA DE OURO):**
Antes de classificar, OLHE A ÚLTIMA MENSAGEM DO "BOT" NO HISTÓRICO.
- Se o BOT perguntou sobre detalhes de erro, códigos, eSocial ou pediu confirmação técnica:
  -> A resposta do usuário (mesmo que seja "não sei", "sim", "isso mesmo", "não") PERTENCE AO TEMA ANTERIOR.
  -> Se o tema anterior era Persona, CLASSIFIQUE COMO "SUPORTE_PERSONA".

SUA MISSÃO - CLASSIFIQUE A INTENÇÃO EM UMA DAS CATEGORIAS (JSON):

1. "SUPORTE_PERSONA":
   - O usuário menciona explicitamente: Persona SQL, eSocial, Folha, Meu RH, Ponto Web.
   - OU descreve problemas claros de RH (Férias, Rescisão, Rubrica, Admissão, DCTFWeb).
   - **CRUCIAL:** Se o HISTÓRICO mostra que o usuário já estava falando de Persona, MANTENHA nessa categoria.
   
2. "SUPORTE_OUTROS_PRODUTOS":
   - O usuário menciona produtos que NÃO são do RH (ex: Contábil, Scritta, Estoque, NFe, Finanças).
   - Indique qual produto foi detectado no campo "produto_detectado".

3. "SOLICITAR_ATENDENTE":
   - O usuário pede explicitamente: "Falar com humano", "Atendente", "Ticket", "Pessoa".
   - O usuário expressa frustração clara ("não resolveu", "desisto", "péssimo").

4. "INDETERMINADO":
   - O usuário relata um problema técnico ("Erro ao abrir", "Não conecta") MAS NÃO DISSE O SISTEMA.
   - Você precisa perguntar qual é o sistema.
   - ⛔ **PROIBIDO:** Não use esta categoria se o usuário estiver RESPONDENDO a uma pergunta do bot.
   
5. "SAUDACAO": Oi, Olá, Tudo bem, Quem é você.

6. "FORA_ESCOPO": Receitas, Futebol, Código, Política.

SAÍDA OBRIGATÓRIA (JSON):
{
    "categoria": "SUPORTE_PERSONA" | "SUPORTE_OUTROS_PRODUTOS" | "INDETERMINADO" | "SAUDACAO" | "FORA_ESCOPO",
    "produto_detectado": "Nome do produto (se houver) ou null",
    "resposta_imediata": "Texto da resposta (apenas para SAUDACAO, INDETERMINADO ou FORA_ESCOPO) ou null"
}
"""

class ReceptionistAgent:
    def __init__(self):
        # Modelo leve para triagem
        self.llm = ChatOpenAI(api_key=OPENAI_API_KEY, model="gpt-4o-mini", temperature=0)
        self.taxonomy_dao = TaxonomyDAO()
        
        # --- 1. CARREGAMENTO DO PROMPT (System) ---
        try:
            dao = PromptDAO()
            db_prompt = dao.get_prompt('receptionist_main')
        except Exception as e:
            logger.warning(f"Erro ao buscar prompt recepcionista: {e}")
            db_prompt = None
            
        raw_prompt = db_prompt if db_prompt else DEFAULT_RECEPTIONIST_PROMPT
        
        # --- 2. CARREGAMENTO DINÂMICO DE PRODUTOS (Postgres) ---
        produtos_str = self._load_products_from_db()
        
        # Injeção no Prompt
        self.system_prompt = raw_prompt.replace("{{PRODUTOS}}", produtos_str)

    def _load_products_from_db(self) -> str:
        """
        Busca os sistemas e módulos no Postgres para montar o catálogo dinâmico.
        """
        try:
            # Busca tudo que é 'recurso' ou 'recurso_n2'
            # No seu banco atual, tudo é 'recurso', então isso cobre tudo.
            raw_nodes = self.taxonomy_dao.get_nodes('recurso')
            if not raw_nodes:
                return FALLBACK_PRODUTOS

            # Organização simples para o Prompt
            # Ex: "- Persona SQL: Sistema de Folha..."
            lines = []
            for node in raw_nodes:
                name = node['name']
                desc = node.get('description') or ""
                # Filtra apenas sistemas principais ou módulos relevantes para não poluir o prompt
                # (Opcional: você pode filtrar por parent_id se quiser só os Nível 1)
                lines.append(f"- {name}: {desc[:100]}...") # Corta descrições gigantes
            
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Erro ao carregar produtos do banco: {e}")
            return FALLBACK_PRODUTOS

    def analyze_intent(self, text: str, chat_history_str: str) -> dict:
        """
        Classifica a intenção do usuário.
        """
        try:
            full_input = f"--- HISTÓRICO RECENTE ---\n{chat_history_str}\n\n--- NOVA MENSAGEM ---\n{text}"
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", self.system_prompt),
                ("user", full_input)
            ])
            
            # Chain simples: Prompt -> LLM -> JSON Parser
            chain = prompt | self.llm | JsonOutputParser()
            return chain.invoke({})
            
        except Exception as e:
            logger.error(f"Erro no Router (Recepcionista): {e}")
            # Fallback seguro: Assume Persona se der erro grave, para não travar o user
            return {"categoria": "SUPORTE_PERSONA", "resposta_imediata": None}