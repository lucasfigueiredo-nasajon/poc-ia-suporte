import logging
import json
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, model_validator
import instructor
from openai import OpenAI
from nasajon.service.knowledge_service import KnowledgeService
from nasajon.service.vision_service import VisionService
from nasajon.settings import OPENAI_API_KEY
from flask import request, Response, stream_with_context
from nasajon.dao.prompt_dao import PromptDAO
from nasajon.dao.taxonomy_dao import TaxonomyDAO

logger = logging.getLogger(__name__)

DEFAULT_CLASSIFICATION_PROMPT = """
Você é um Engenheiro de Conhecimento criando um dataset para a Nasajon (Persona/SQL).
Analise o histórico e as descrições visuais para extrair conhecimento técnico.

CRITÉRIOS PARA "UTIL" (Prioridade Máxima):
1. O ticket contém uma **Solução Técnica Definitiva**.
2. Se a pergunta do cliente não estiver explícita, **INFIRA O SINTOMA** baseando-se na resposta técnica do analista.
3. Se houver prints de erro descritos pelo [Vision AI], use o texto do erro no campo 'sintoma'.

CRITÉRIOS PARA "INUTIL" (Descarte Imediato):
1. Problemas de infraestrutura (Internet caiu, computador travou).
2. Comercial/Financeiro (Boleto, Contrato, Licença expirada).
3. "Vou verificar internamente" (e o ticket acaba sem a resposta final).
4. Acessos remotos onde NÃO foi descrito o que foi feito (Ex: "Resolvido em acesso remoto").

No campo 'solucao', escreva como um tutorial instrucional: "Acesse menu X > Y e altere Z".
"""

DEFAULT_GRAPH_ENRICHMENT_PROMPT = """
Você é um Engenheiro de Dados Sênior especializado em estruturar logs de suporte técnico para sistemas de RAG e Knowledge Graphs.
Sua especialidade é o sistema 'Persona SQL' e o módulo 'eSocial'.

SEU OBJETIVO:
Analisar o histórico de conversa e o objeto 'knowledge_base' existente para extrair entidades e relacionamentos estruturados.

SAÍDA ESPERADA (JSON ESTRITO):
Você deve retornar APENAS um objeto JSON com a seguinte estrutura:
{
  "analise_sintoma": {
    "descricao_usuario": "Resumo curto de como o leigo descreveu (ex: 'botão cinza')",
    "descricao_tecnica": "Explicação técnica detalhada. Inclua nomes de tabelas, rotinas, códigos de erro e o fluxo da falha. Mínimo de 20 palavras.",
    "codigos_erro": ["Lista", "de", "codigos", "encontrados"]
  },
  "entidades_grafo": {
    "modulos": ["eSocial", "Folha", "Login", "Relatórios"],
    "eventos_esocial": ["S-1200", "S-2299", "S-1000"],
    "telas_menus": ["Cadastro de Funcionários", "Geração de Guias"]
  },
  "solucao_atomica": {
    "causa_raiz_curta": "Resumo de 1 linha da causa",
    "passos_ordenados": [
      "Passo 1: Ação...",
      "Passo 2: Ação..."
    ]
  },
  "grafo_metadata": {
    "pergunta_desambiguacao": "Uma pergunta chave para diferenciar este problema de outro similar",
    "complexidade": "Baixa"
  }
}
"""

# --- SCHEMAS ---
class AnaliseTicket(BaseModel):
    classificacao: Literal["UTIL", "INUTIL"]
    raciocinio_breve: str
    sintoma: Optional[str] = None
    causa: Optional[str] = None
    solucao: Optional[str] = None
    tags: Optional[List[str]] = []

    @model_validator(mode='after')
    def verificar_consistencia(self):
        # Se for útil, PRECISA ter sintoma e solução
        if self.classificacao == "UTIL" and (not self.solucao or not self.sintoma):
            self.classificacao = "INUTIL"
            self.raciocinio_breve += " [Reclassificado: Faltou sintoma ou solução]"
        return self

class ItemTaxonomia(BaseModel):
    id_banco: Optional[int] = Field(None, description="Ignorar.")
    nome_validado: str = Field(..., description="O nome exato escolhido da lista válida.")

class MapeamentoCompleto(BaseModel):
    # Hierarquia de Recurso
    recurso_nivel_2: ItemTaxonomia = Field(description="Módulo Macro (Ex: eSocial)")
    recurso_nivel_3: ItemTaxonomia = Field(description="Funcionalidade/Tela (Ex: Monitor de Eventos)")
    
    # Classificações
    categoria_sintoma: ItemTaxonomia
    categoria_causa: ItemTaxonomia
    categoria_solucao: ItemTaxonomia
    
    # Listas Validadas
    eventos_esocial: List[ItemTaxonomia]
    codigos_erro: List[ItemTaxonomia]


class IngestionService:
    def __init__(self, knowledge_service: KnowledgeService, vision_service: VisionService):
        self.knowledge = knowledge_service
        self.vision = vision_service
        self.taxonomy_dao = TaxonomyDAO()
        
        if not OPENAI_API_KEY:
             logger.error("OPENAI_API_KEY não configurada no settings.")
        
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.instructor_client = instructor.patch(self.client)
        self.keywords_persona = ["folha", "pagamento", "esocial", "ferias", "rescisao", "fgts", "inss", "salario"]

    def _is_persona(self, item: Dict) -> bool:
        ticket = item.get('ticket', {})
        # Verifica sistema explicitamente
        if ticket.get('sistema') == "Persona SQL": return True
        # Ou busca palavras-chave no resumo
        texto = f"{ticket.get('resumo_admin', '')} {ticket.get('ocorrencias', '')}".lower()
        return any(kw in texto for kw in self.keywords_persona)

    def _get_classification_prompt(self):
        """Helper para carregar o prompt do banco ou usar o fallback."""
        try:
            dao = PromptDAO()
            db_prompt = dao.get_prompt('ingestion_classification')
            return db_prompt if db_prompt else self.DEFAULT_CLASSIFICATION_PROMPT
        except Exception:
            return self.DEFAULT_CLASSIFICATION_PROMPT
    
    def run_pipeline_stream(self, raw_data: List[Dict], clear_db: bool = False):
        """
        Generator Verboso: Itera sobre TODOS os tickets e explica o motivo de sucesso ou falha.
        """
        try:
            system_prompt = self._get_classification_prompt()

            yield json.dumps({"step": "init", "msg": "🔄 Verificando banco de dados..."}) + "\n"
            
            try:
                existing_ids = self.knowledge.get_all_existing_ticket_ids()
            except Exception as e:
                logger.error(f"Falha ao recuperar IDs: {e}")
                existing_ids = []
            
            total = len(raw_data)
            yield json.dumps({"step": "init", "msg": f"📂 Analisando {total} tickets do arquivo..."}) + "\n"
            
            final_batch = []
            # --- NOVA ESTATÍSTICA GRANULAR ---
            stats = {
                "total_recebido": len(raw_data),
                "filtrado_sistema": 0,    # Não é Persona
                "ja_existia": 0,          # Já no Neo4j
                "classificado_inutil": 0, # IA rejeitou
                "classificado_util": 0,   # IA aprovou
                "salvo_sucesso": 0,       # Commit no Banco OK
                "erro_processamento": 0
            }

            # Loop Principal - Itera sobre TUDO para dar feedback de TUDO
            for i, ticket in enumerate(raw_data):
                t_id = str(ticket.get('ticket', {}).get('ticket_id', 'N/A'))
                
                # Feedback de Progresso
                yield json.dumps({
                    "step": "progress", 
                    "current": i + 1, 
                    "total": total, 
                    "msg": f"🎫 [{i+1}/{total}] Ticket {t_id[:8]}..."
                }) + "\n"

                # 1. Checagem de Domínio (Persona)
                if not self._is_persona(ticket):
                    yield json.dumps({"step": "log", "msg": "   🚫 Ignorado: Não é do sistema Persona/RH."}) + "\n"
                    stats["filtrado_sistema"] += 1  # <--- ALTERAR AQUI
                    continue

                # 2. Checagem de Duplicidade
                if t_id in existing_ids and not clear_db:
                    yield json.dumps({"step": "log", "msg": "   ⏭️ Ignorado: Já existe no Neo4j."}) + "\n"
                    stats["ja_existia"] += 1        # <--- ALTERAR AQUI
                    continue

                # Se passou pelos filtros, processa com IA
                try:
                    # A. Visão Computacional (Com Heartbeat)
                    imgs = []
                    for msg in ticket.get('conversa', []):
                        if msg.get('imagens'): imgs.extend(msg['imagens'])
                    
                    if imgs:
                        yield json.dumps({"step": "log", "msg": f"   👁️ Vision AI: Analisando {len(imgs)} imagens..."}) + "\n"
                        for idx, url in enumerate(imgs):
                            yield json.dumps({"step": "log", "msg": f"      📸 Imagem {idx+1}/{len(imgs)}..."}) + "\n"
                            analise_img = self.vision.analyze_image(url)
                            # Anexa a análise ao texto da mensagem para o GPT ler depois
                            for msg in ticket.get('conversa', []):
                                if url in msg.get('imagens', []):
                                    msg['text'] = (msg.get('text') or "") + f"\n\n[ANÁLISE DE IMAGEM]: {analise_img}"
                    
                    # B. Classificação e Estruturação (GPT-4o Mini)
                    yield json.dumps({"step": "log", "msg": "   🧠 IA: Analisando utilidade e extraindo dados..."}) + "\n"
                    
                    analise_ia = self.instructor_client.chat.completions.create(
                        model="gpt-4o-mini",
                        response_model=AnaliseTicket,
                        max_retries=2, 
                        messages=[
                            {
                                "role": "system", 
                                # AQUI: Usamos o prompt carregado
                                "content": system_prompt 
                            },
                            {"role": "user", "content": f"Analise este ticket JSON: {str(ticket)}"}
                        ]
                    )

                    if analise_ia.classificacao == "UTIL":
                        yield json.dumps({"step": "log", "msg": "   ✅ Aprovado. Gerando nós do grafo..."}) + "\n"
                        stats["classificado_util"] += 1

                        ticket['knowledge_base'] = {
                            "sintoma": analise_ia.sintoma,
                            "causa": analise_ia.causa,
                            "solucao": analise_ia.solucao,
                            "tags": analise_ia.tags
                        }
                        
                        # C. GraphRAG (GPT-4o)
                        ticket['graph_enrichment'] = self._enrich_for_graph(ticket)
                        # --- ADICIONE ESTE BLOCO NOVO ---
                        yield json.dumps({"step": "log", "msg": "   📚 Mapeando para Taxonomia (Postgres)..."}) + "\n"
                        ticket['structured_taxonomy'] = self._map_to_taxonomy(ticket, ticket['graph_enrichment'])
                        # --------------------------------

                        
                        final_batch.append(ticket)
                    else:
                        reason = analise_ia.raciocinio_breve
                        yield json.dumps({"step": "log", "msg": f"   🗑️ Rejeitado pela IA: {reason}"}) + "\n"
                        stats["classificado_inutil"] += 1 # <--- ALTERAR DE skipped_count PARA ISSO

                except Exception as e:
                    logger.error(f"Erro ticket {t_id}: {e}")
                    yield json.dumps({"step": "error", "msg": f"   ❌ Erro de Processamento: {str(e)}"}) + "\n"
                    stats["erro_processamento"] += 1      # <--- ALTERAR DE skipped_count PARA ISSO

            # 3. Ingestão Final
            if final_batch:
                # ==============================================================================
                # 🕵️ DEBUG VISUAL NO STREAMLIT
                # Isso vai mostrar o JSON direto na tela do usuário, dentro de um bloco de código
                # ==============================================================================
                try:
                    debug_json = json.dumps(final_batch[0], indent=2, ensure_ascii=False)
                    # Envia como mensagem de log formatada em Markdown para o Streamlit renderizar
                    yield json.dumps({
                        "step": "log", 
                        "msg": f"🔥🔥🔥 DEBUG JSON (Copie abaixo): \n```json\n{debug_json}\n```"
                    }) + "\n"
                except Exception as debug_err:
                    logger.error(f"Erro no debug: {debug_err}")
                # ==============================================================================
                yield json.dumps({"step": "log", "msg": f"💾 Gravando {len(final_batch)} tickets no banco..."}) + "\n"
                try:
                    res = self.knowledge.repopulate_database(final_batch, clear_db=clear_db)
                    
                    # Atualiza estatística de sucesso baseada no retorno do banco
                    saved = res.get('imported', 0)
                    stats["salvo_sucesso"] = saved
                    
                    # Se mandou salvar 10 e salvou 8, temos 2 erros de banco
                    if saved < len(final_batch):
                         stats["erro_processamento"] += (len(final_batch) - saved)
                         
                except Exception as db_err:
                    yield json.dumps({"step": "error", "msg": f"❌ Falha no Neo4j: {str(db_err)}"}) + "\n"
                    stats["erro_processamento"] += len(final_batch)
            
            # --- RETORNO FINAL COM O NOVO FORMATO ---
            yield json.dumps({
                "step": "final", 
                "stats": stats  # <--- Enviamos o objeto completo agora
            }) + "\n"
            
        except Exception as e:
            logger.critical(f"Erro pipeline: {e}")
            yield json.dumps({"step": "error", "msg": f"🚨 Erro Crítico: {str(e)}"}) + "\n"

    def _enrich_for_graph(self, ticket: Dict) -> Dict:
        """
        Extrai entidades ricas para o Knowledge Graph (Neo4j).
        """
        try:
            # 1. Prepara o contexto limpo (Melhor que enviar o JSON bruto)
            kb = ticket.get('knowledge_base', {})
            msgs = ticket.get('conversa', [])
            
            # Formata o chat para leitura humana/LLM (Remove ruído de JSON)
            chat_formatado = "\n".join([
                f"[{m.get('role', 'user').upper()}]: {m.get('text', '')}" 
                for m in msgs
            ])

            user_content = f"""
            === DADOS DO TICKET ===
            ID: {ticket.get('ticket', {}).get('ticket_id')}
            Resumo: {ticket.get('ticket', {}).get('resumo_admin')}
            
            === KNOWLEDGE BASE PRELIMINAR (GPT-Mini) ===
            Sintoma Detectado: {kb.get('sintoma')}
            Causa Detectada: {kb.get('causa')}
            Solução Sugerida: {kb.get('solucao')}
            
            === HISTÓRICO DA CONVERSA ===
            {chat_formatado}
            """

            try:
                dao = PromptDAO()
                db_prompt = dao.get_prompt('ingestion_graph_enrichment')
            except Exception:
                db_prompt = None
            
            final_system_prompt = db_prompt if db_prompt else DEFAULT_GRAPH_ENRICHMENT_PROMPT
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": final_system_prompt},
                    {"role": "user", "content": user_content}
                ]
            )
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Erro no enriquecimento de grafo: {e}")
            return {"analise_sintoma": {}, "entidades_grafo": {}, "solucao_atomica": {}}

    def _get_taxonomy_lists(self):
        """Busca listas do Postgres com inteligência para separar Módulos (N2) de Funcionalidades (N3)."""
        try:
            sintomas = [t['name'] for t in self.taxonomy_dao.get_nodes('sintoma')]
            causas = [t['name'] for t in self.taxonomy_dao.get_nodes('causa')]
            solucoes = [t['name'] for t in self.taxonomy_dao.get_nodes('solucao')]
            erros = [t['name'] for t in self.taxonomy_dao.get_nodes('erro')]
            eventos = [t['name'] for t in self.taxonomy_dao.get_nodes('evento')]

            # Lógica inteligente para Recursos (que estão misturados como 'recurso')
            all_recursos = self.taxonomy_dao.get_nodes('recurso')
            recursos_n2 = []
            recursos_n3 = []

            for r in all_recursos:
                # Se o pai for o Sistema Raiz (ID 21 = Persona SQL) ou NULL, é Módulo (N2)
                if r.get('parent_id') == 21 or r.get('parent_id') is None: 
                    recursos_n2.append(r['name'])
                else:
                    # Se tem pai e não é o Raiz, é Funcionalidade (N3)
                    recursos_n3.append(r['name'])
            
            # Fallback seguro se a lista N3 estiver vazia
            if not recursos_n3: recursos_n3 = ["Geral", "Outro"]

            return {
                "sintomas": sintomas, "causas": causas, "solucoes": solucoes,
                "recursos_n2": recursos_n2, "recursos_n3": recursos_n3,
                "erros": erros, "eventos": eventos
            }
        except Exception as e:
            logger.error(f"Erro carregando taxonomias: {e}")
            return {k: ["Outro"] for k in ["sintomas", "causas", "solucoes", "recursos_n2", "recursos_n3", "erros", "eventos"]}

    def _map_to_taxonomy(self, ticket_context: Dict, enrichment_data: Dict) -> Dict:
        """Classifica os dados ricos nas listas estritas do Postgres."""
        try:
            lists = self._get_taxonomy_lists()
            
            # Contexto Rico para a IA classificar
            sintoma_rico = enrichment_data.get('analise_sintoma', {})
            solucao_rica = enrichment_data.get('solucao_atomica', {})
            entidades = enrichment_data.get('entidades_grafo', {})
            
            prompt_input = f"""
            DADOS RICOS EXTRAÍDOS (Use isso para decidir):
            - Descrição Técnica: {sintoma_rico.get('descricao_tecnica')}
            - Erros Citados: {sintoma_rico.get('codigos_erro')}
            - Causa Raiz: {solucao_rica.get('causa_raiz_curta')}
            - Solução: {solucao_rica.get('passos_ordenados')}
            - Módulos/Telas: {entidades.get('modulos')} / {entidades.get('telas_menus')}

            SUA TAREFA:
            Para cada campo, escolha A MELHOR opção correspondente nas listas válidas abaixo.
            Se não houver match exato, escolha "Outro" ou a opção mais genérica.

            --- LISTAS VÁLIDAS (POSTGRES) ---
            [Sintomas]: {json.dumps(lists['sintomas'], ensure_ascii=False)}
            [Causas]: {json.dumps(lists['causas'], ensure_ascii=False)}
            [Solucoes]: {json.dumps(lists['solucoes'], ensure_ascii=False)}
            [Recurso N2 (Módulo)]: {json.dumps(lists['recursos_n2'], ensure_ascii=False)}
            [Recurso N3 (Funcionalidade)]: {json.dumps(lists['recursos_n3'], ensure_ascii=False)}
            [Códigos de Erro]: {json.dumps(lists['erros'], ensure_ascii=False)}
            [Eventos eSocial]: {json.dumps(lists['eventos'], ensure_ascii=False)}
            """

            response = self.instructor_client.chat.completions.create(
                model="gpt-4o-mini",
                response_model=MapeamentoCompleto,
                max_retries=2,
                messages=[
                    {"role": "system", "content": "Você é um classificador de taxonomias estrito. Use APENAS os valores das listas."},
                    {"role": "user", "content": prompt_input}
                ]
            )
            return response.model_dump()
        except Exception as e:
            logger.error(f"Erro no mapeamento taxonômico: {e}")
            return {}