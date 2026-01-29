import streamlit as st
import requests
import uuid
import json

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Nasajon IA Suporte", 
    page_icon="🤖", 
    layout="wide"
)

# --- CONSTANTES & DEFAULTS ---
BASE_URL = "https://api.nasajon.app/nsj-ia-suporte"
# BASE_URL = "http://localhost:5000/nsj-ia-suporte" # Dev Local

INGEST_URL = f"{BASE_URL}/ingest-pipeline"
PROMPTS_URL = f"{BASE_URL}/prompts"

# Define o Tenant ID fixo (já que removemos a seleção da sidebar)
tenant_id = "1" 

# --- ESTADO DA SESSÃO ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())

# --- CABEÇALHO ---
col1, col2 = st.columns([1, 6])
with col1:
    st.image("https://nasajon.com.br/wp-content/uploads/2020/12/logo-nasajon.png", width=80)
with col2:
    st.title("Nasajon IA - Suporte")
    st.caption(f"Painel de Atendimento Inteligente | Tenant: {tenant_id}")

# --- DEFINIÇÃO DAS ABAS ---
tab_chat, tab_admin, tab_prompts, tab_taxonomy = st.tabs([
    "💬 Chat de Suporte", 
    "⚙️ Ingestão de Dados", 
    "📝 Gestão de Prompts",
    "🗂️ Gestão de Taxonomias"
])

# ---------------------------------------------------------
# ABA 1: CHAT DE SUPORTE
# ---------------------------------------------------------
with tab_chat:
    # Botão de Limpeza (Agora no topo da aba)
    col_btn, _ = st.columns([2, 8])
    with col_btn:
        if st.button("🗑️ Limpar Conversa / Reiniciar", type="secondary"):
            st.session_state.messages = []
            st.session_state.conversation_id = str(uuid.uuid4())
            st.rerun()
    
    st.divider()

    # Histórico de Mensagens
    if not st.session_state.messages:
        st.info("👋 Olá! O assistente virtual está pronto. Digite sua dúvida abaixo.")
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Input do Chat
    if prompt := st.chat_input("Descreva seu problema ou dúvida..."):
        # 1. Adiciona msg do usuário
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # 2. Placeholder para resposta (Aqui entraria a integração com /queries)
        # with st.chat_message("assistant"):
        #     with st.spinner("Analisando base de conhecimento..."):
        #         response = requests.post(...) 
        #         st.markdown(response_text)
        #         st.session_state.messages.append({"role": "assistant", "content": response_text})

# ---------------------------------------------------------
# ABA 2: INGESTÃO E VISUALIZAÇÃO (VERSÃO FINAL)
# ---------------------------------------------------------
# ---------------------------------------------------------
# ABA 2: INGESTÃO E VISUALIZAÇÃO (VERSÃO FINAL + TEMPLATE)
# ---------------------------------------------------------
with tab_admin:
    st.header("🚀 Ingestão de Tickets")

    # --- 1. TEMPLATE VISUAL PARA O USUÁRIO ---
    # Define o modelo anonimizado
    TEMPLATE_JSON = [
      {
        "ticket": {
          "ticket_id": "uuid-gerado-automaticamente",
          "numeroprotocolo": 12345678,
          "sistema": "Persona SQL",
          "versao_sistema": "2.0.0",
          "tipo": "Dúvida",
          "situacao": 3,
          "prioridade": "Normal",
          "ocorrencias": "S2EDU006 - DÚVIDA SOBRE CÁLCULO",
          "canal_abertura": "portal",
          "resumo_admin": "Erro no cálculo de férias",
          "ultima_resposta_resumo": "Verificamos que a rubrica estava incorreta...",
          "atendimentosituacao": "uuid-situacao"
        },
        "datas": {
          "datacriacao": "2025-01-27 10:00:00+00",
          "data_ultima_resposta": "2025-01-27 12:00:00+00",
          "data_ultima_resposta_admin": "2025-01-27 11:30:00+00",
          "dataconclusao": "2025-01-27 14:00:00+00"
        },
        "cliente": {
          "id_cliente": "uuid-cliente",
          "codigo_cliente": "99999",
          "nome_cliente": "EMPRESA EXEMPLO LTDA",
          "nome_fantasia_cliente": "EMPRESA EXEMPLO",
          "cnpj_cliente": 12345678000199,
          "email_contato": "contato@empresa.com.br",
          "nome_contato": "FULANO DE TAL",
          "telefone_contato": "11-99999-9999"
        },
        "suporte": {
          "nome_equipe": "Suporte Persona",
          "responsavel_web": "analista@nasajon.com.br"
        },
        "conversa": [
          {
            "timestamp": "2025-01-27 10:00:00+00",
            "role": "analista",
            "author_name": "Analista Nasajon",
            "canal": "manual",
            "text": "Olá, qual seria sua dúvida?",
            "imagens": []
          },
          {
            "timestamp": "2025-01-27 10:05:00+00",
            "role": "cliente",
            "author_name": "Fulano de Tal",
            "canal": "portal",
            "text": "O cálculo do evento S-1200 está retornando erro de rubrica.",
            "imagens": ["https://exemplo.com/print_erro.png"]
          }
        ]
      }
    ]

    with st.expander("ℹ️ Ver Modelo de JSON Esperado (Template)", expanded=False):
        st.markdown("O sistema espera uma **Lista de Objetos** com a seguinte estrutura:")
        st.json(TEMPLATE_JSON)
        st.caption("Dica: Você pode copiar este JSON e alterar os valores para testar.")

    st.markdown("---")

    # --- 2. SELEÇÃO DE FONTE ---
    tipo_entrada = st.radio(
        "Como deseja inserir os tickets?", 
        ["📂 Upload de Arquivo JSON", "📝 Colar JSON Manualmente"], 
        horizontal=True
    )

    raw_data = []

    # --- LÓGICA DE CARREGAMENTO ---
    if tipo_entrada == "📂 Upload de Arquivo JSON":
        uploaded_file = st.file_uploader("Selecione o arquivo tickets.json", type=['json'])
        if uploaded_file:
            try:
                raw_data = json.load(uploaded_file)
            except Exception as e:
                st.error(f"Erro ao ler arquivo: {e}")

    else: # Colar Manualmente
        json_text = st.text_area(
            "Cole a lista de tickets aqui:", 
            height=200, 
            placeholder='[ {"ticket": {...}}, ... ]'
        )
        if json_text:
            try:
                loaded = json.loads(json_text)
                # Garante que seja lista mesmo se colar um único objeto
                raw_data = [loaded] if isinstance(loaded, dict) else loaded
            except json.JSONDecodeError:
                st.warning("Aguardando JSON válido...")
            except Exception as e:
                st.error(f"Erro: {e}")

    # --- 3. PROCESSAMENTO (SE HOUVER DADOS) ---
    if raw_data:
        total_disponivel = len(raw_data)
        st.success(f"📂 {total_disponivel} tickets carregados prontos para análise.")

        # --- PRÉ-VISUALIZAÇÃO RICA ---
        with st.expander("🔍 Pré-visualizar Tickets Carregados", expanded=False):
            st.caption("Mostrando os 3 primeiros tickets do lote para validação:")
            
            def _render_preview(t_data):
                t = t_data.get('ticket', {})
                msgs = t_data.get('conversa', [])
                
                # Cabeçalho Compacto
                c1, c2 = st.columns([3, 1])
                c1.markdown(f"**{t.get('sistema')}** | Protocolo: `{t.get('numeroprotocolo')}`")
                c1.caption(f"Resumo: {t.get('resumo_admin')}")
                c2.markdown(f"**ID:** `{t.get('ticket_id', '')[:8]}...`")
                
                # Chat Preview
                with st.container(border=True):
                    for m in msgs:
                        role = m.get('role', 'unknown')
                        avatar = "🎧" if role == 'analista' else "👤"
                        with st.chat_message(role, avatar=avatar):
                            st.markdown(f"**{m.get('author_name')}**: {m.get('text')}")
                            if m.get('imagens'):
                                st.image(m['imagens'][0], width=150, caption="Imagem Anexada")

            for item in raw_data[:3]:
                _render_preview(item)
                st.divider()

        st.markdown("---")

        # --- CONFIGURAÇÃO DO LOTE ---
        st.markdown("### ⚙️ Configuração do Pipeline")
        col_limit, col_mode = st.columns(2)
        
        with col_limit:
            quantidade = st.number_input(
                "Quantidade de tickets para processar:",
                min_value=1,
                max_value=total_disponivel,
                value=min(50, total_disponivel),
                step=1
            )
        
        with col_mode:
            clean_start = st.checkbox(
                "Reset Full (Limpar Neo4j)", 
                value=False,
                help="⚠️ Se marcado, apaga TODO o banco antes de iniciar."
            )

        # --- BOTÃO DE AÇÃO ---
        if st.button("🔥 Iniciar Pipeline IA", type="primary"):
            data_to_send = raw_data[:int(quantidade)]
            
            status_container = st.status("🚀 Inicializando conexão...", expanded=True)
            progress_bar = status_container.progress(0)
            current_action = status_container.empty()
            
            try:
                INGEST_URL = "https://api.nasajon.app/nsj-ia-suporte/ingest-pipeline"
                
                payload_ingesta = {
                    "tickets": data_to_send,
                    "clear_db": clean_start
                }
                
                headers = {"Content-Type": "application/json", "X-Tenant-ID": tenant_id}
                
                response = requests.post(
                    INGEST_URL, 
                    json=payload_ingesta,
                    headers=headers,
                    timeout=900,
                    stream=True 
                )
                
                final_stats = None
                
                if response.status_code == 200:
                    for line in response.iter_lines():
                        if line:
                            try:
                                event = json.loads(line.decode('utf-8'))
                                step = event.get('step')
                                msg = event.get('msg', '')
                                
                                if step == 'init':
                                    status_container.write(f"ℹ️ {msg}")
                                elif step == 'progress':
                                    curr = event.get('current', 0)
                                    total = event.get('total', 1)
                                    progress_bar.progress(curr / total)
                                    current_action.markdown(f"**{msg}**")
                                elif step == 'log':
                                    status_container.markdown(f"`{msg}`")
                                elif step == 'error':
                                    status_container.error(msg)
                                elif step == 'final':
                                    final_stats = event
                            except:
                                continue

                    status_container.update(label="✅ Processamento Concluído!", state="complete", expanded=False)
                    
                    # --- DASHBOARD DETALHADO (FUNIL) ---
                    if final_stats and 'stats' in final_stats:
                        st.divider()
                        st.markdown("### 📊 Relatório de Ingestão")
                        
                        s = final_stats['stats'] 
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("1. Total Recebido", s['total_recebido'])
                        with col2:
                            st.metric("2. Já Existiam", s['ja_existia'], 
                                     delta=f"{s['ja_existia']} ignorados", delta_color="off")
                        with col3:
                            st.metric("3. Classificados Úteis", s['classificado_util'], 
                                     delta=f"{s['classificado_util']} aprovados")
                        with col4:
                            st.metric("4. Gravados no Neo4j", s['salvo_sucesso'], 
                                     delta=f"+{s['salvo_sucesso']}", delta_color="normal")
                        
                        st.caption("Detalhes dos tickets descartados ou com erro:")
                        d1, d2, d3 = st.columns(3)
                        d1.metric("Filtro Sistema", s['filtrado_sistema'])
                        d2.metric("IA Rejeitou", s['classificado_inutil'])
                        d3.metric("Erros Técnicos", s['erro_processamento'])

                        if s['salvo_sucesso'] > 0:
                            st.balloons()
                        elif s['erro_processamento'] > 0:
                            st.error("Houve erros técnicos durante a gravação.")
                        elif s['ja_existia'] == s['total_recebido']:
                            st.warning("Nenhum dado novo: Todos os tickets já existiam no banco.")
                        elif s['classificado_inutil'] > 0:
                            st.warning("Os tickets foram processados, mas a IA considerou todos inúteis/incompletos.")
                else:
                    status_container.update(label="❌ Erro na API", state="error")
                    st.error(f"HTTP {response.status_code}: {response.text}")
                    
            except Exception as e:
                status_container.update(label="🔌 Erro de Conexão", state="error")
                st.error(f"Detalhes: {str(e)}")

# ---------------------------------------------------------
# ABA 3: GESTÃO DE PROMPTS (VIA API)
# ---------------------------------------------------------
with tab_prompts:
    st.header("📝 Editor de Prompts do Sistema")
    st.info("Gerencie os System Prompts, Agentes e Tools armazenados no banco.")

    API_URL = "https://api.nasajon.app/nsj-ia-suporte/prompts" 
    
    # Mapeamento do Sistema
    # Mapeamento do Sistema
    prompts_map = {
        "🛎️ Agente: Recepcionista (Triagem)": "receptionist_main",
        "🤖 Agente: Especialista (Persona)": "persona_specialist",
        "   ↳ 🛠️ Tool: Busca Técnica (Gerador Cypher)": "tool_lookup_cypher",
        "📥 Pipeline de Ingestão: (Visão Computacional OCR)": "vision_analysis",
        "📥 Pipeline de Ingestão (Classificador Tickets Úteis)": "ingestion_classification",
        "📥 Pipeline de Ingestão: (Enriquecimento GraphRAG)": "ingestion_graph_enrichment"# NOVO
    }
    
    selected_name = st.selectbox("Selecione o Componente:", list(prompts_map.keys()))
    selected_key = prompts_map[selected_name]

    # Estado Inicial
    if 'prompt_data' not in st.session_state:
        st.session_state['prompt_data'] = {}

    # --- 1. CARREGAR ---
    if st.button("🔄 Carregar Dados", key="btn_load"):
        try:
            resp = requests.get(API_URL, params={"key": selected_key}, headers={"X-Tenant-ID": tenant_id})
            if resp.status_code == 200:
                st.session_state['prompt_data'] = resp.json()
                st.success("Carregado!")
            elif resp.status_code == 404:
                st.warning("Prompt novo (ainda não existe no banco).")
                st.session_state['prompt_data'] = {"prompt": "", "description": "", "target_entity": "", "source_file": ""}
        except Exception as e:
            st.error(f"Erro: {e}")

    # Dados Atuais
    data = st.session_state.get('prompt_data', {})

    # --- 2. METADADOS (LINHAGEM) ---
    with st.container(border=True):
        st.markdown("#### 📍 Linhagem do Prompt")
        c1, c2 = st.columns(2)
        
        # Campos Editáveis
        target_val = st.text_input("Target Entity (Classe/Tool):", 
                                  value=data.get('target_entity', ''),
                                  placeholder="Ex: PersonaSpecialistAgent")
        
        source_val = st.text_input("Arquivo Fonte:", 
                                  value=data.get('source_file', ''),
                                  placeholder="Ex: nasajon/service/...")
        
        desc_val = st.text_input("Descrição:", 
                                value=data.get('description', ''),
                                placeholder="Resumo do objetivo deste prompt")

    # --- 3. EDITOR DE TEXTO ---
    new_prompt_text = st.text_area(
        "Conteúdo do System Prompt:", 
        value=data.get('prompt', ''),
        height=600,
        help="Edite o comportamento da IA aqui."
    )

    # --- 4. SALVAR ---
    if st.button("💾 Salvar Alterações", type="primary"):
        if len(new_prompt_text) < 5:
            st.error("Prompt inválido.")
        else:
            payload = {
                "key": selected_key,
                "prompt": new_prompt_text,
                "description": desc_val,
                "target_entity": target_val,
                "source_file": source_val
            }
            try:
                resp = requests.post(API_URL, json=payload, headers={"X-Tenant-ID": tenant_id})
                if resp.status_code == 200:
                    st.success("✅ Salvo com sucesso!")
                else:
                    st.error(f"Erro: {resp.text}")
            except Exception as e:
                st.error(f"Erro de conexão: {e}")

# ---------------------------------------------------------
# ABA 4: GESTÃO DE TAXONOMIAS
# ---------------------------------------------------------
with tab_taxonomy:
    st.header("🗂️ Gestão de Categorias e Recursos")
    st.info("Defina a estrutura de conhecimento. Use 'Recursos' para hierarquia (Sistema > Módulo > Funcionalidade).")

    # URL Específica desta aba
    TAXONOMY_URL = f"{BASE_URL}/taxonomies/nodes"

    tipos_taxonomia = {
        "Recursos (Sistemas/Módulos)": "recurso",
        "Sintomas": "sintoma",
        "Erros": "erro",
        "Eventos (eSocial)": "evento",
        "Causas": "causa",
        "Soluções": "solucao"
    }
    
    selected_label = st.selectbox("Selecione a Taxonomia:", list(tipos_taxonomia.keys()))
    selected_type = tipos_taxonomia[selected_label]

    # --- HELPER DE BUSCA ---
    def fetch_nodes(t_type):
        try:
            resp = requests.get(TAXONOMY_URL, params={"type": t_type}, headers={"X-Tenant-ID": tenant_id})
            return resp.json() if resp.status_code == 200 else []
        except: return []

    nodes = fetch_nodes(selected_type)
    
    # --- VISUALIZAÇÃO DE ÁRVORE ---
    node_map = {n['id']: n for n in nodes}
    tree_options = [] 
    
    def build_tree_list(parent_id, level=0):
        children = [n for n in nodes if n['parent_id'] == parent_id]
        for child in children:
            prefix = "└── " * level if level > 0 else "📦 "
            label = f"{prefix}{child['name']}"
            tree_options.append((child['id'], label))
            build_tree_list(child['id'], level + 1)

    build_tree_list(None)
    
    mapped_ids = {t[0] for t in tree_options}
    for n in nodes:
        if n['id'] not in mapped_ids:
            tree_options.append((n['id'], f"⚠️ [Orfão] {n['name']}"))

    # --- DIVISÃO DA TELA ---
    col_tree, col_edit = st.columns([1, 1])

    # ... (Lógica das colunas será renderizada abaixo da área de importação para facilitar acesso) ...

    # --- ÁREA DE IMPORTAÇÃO EM LOTE ---
    with st.expander("📦 Importação em Lote (Carga Inicial)", expanded=False):
        
        # 1. DADOS DE RECURSOS (SEUS DADOS ORIGINAIS)
        DATA_RECURSOS = [
          {
            "produto": "Reforma Tributária",
            "descricao": "Soluções e atualizações dedicadas à transição e conformidade com as novas normas tributárias brasileiras.",
            "modulos": [
              { "nome": "Reforma Tributária", "descricao": "Monitoramento de alíquotas, cálculos de IBS/CBS e adaptação de cadastros fiscais." }
            ]
          },
          {
            "produto": "Geral",
            "descricao": "Recursos transversais e conteúdos informativos aplicáveis a todo o ecossistema Nasajon.",
            "modulos": [
              { "nome": "Comum a todos os sistemas", "descricao": "Configurações globais de banco de dados, usuários e permissões de acesso." },
              { "nome": "Live - Assuntos Gerais", "descricao": "Acesso a transmissões ao vivo sobre atualizações de legislação e software." },
              { "nome": "Sprint Notes", "descricao": "Documentação técnica sobre as melhorias e correções implementadas em cada ciclo de desenvolvimento." }
            ]
          },
          {
            "produto": "Persona SQL",
            "descricao": "Sistema completo para gestão de Folha de Pagamento e Recursos Humanos.",
            "modulos": [
              { "nome": "eSocial", "descricao": "Gerenciamento e transmissão de eventos periódicos e não periódicos para o governo." },
              { "nome": "Cálculos e Rotinas", "descricao": "Processamento de folha, férias, 13º salário e rescisões contratuais." },
              { "nome": "Arquivos Oficiais", "descricao": "Geração de guias como FGTS, DARF e declarações anuais (DIRF/RAIS)." },
              { "nome": "Módulo de Ponto", "descricao": "Integração de batidas e tratamento de horas extras/faltas para a folha." },
              { "nome": "Listagens e Relatórios", "descricao": "Emissão de contracheques, fichas financeiras e relatórios gerenciais de RH." },
              { "nome": "Cadastros e Configurações", "descricao": "Manutenção de dados de funcionários, sindicatos e tabelas de incidência." },
              { "nome": "Integração", "descricao": "Conexão de dados contábeis e financeiros com outros sistemas SQL." }
            ]
          },
          {
            "produto": "Ponto Web",
            "descricao": "Solução em nuvem para controle de jornada e gestão de frequência.",
            "modulos": [
              { "nome": "Configuração", "descricao": "Definição de horários, escalas e regras de tolerância de atrasos." },
              { "nome": "Tratamento Ponto", "descricao": "Ajustes de marcações, justificativas de ausências e abonos." },
              { "nome": "Dúvidas Frequentes", "descricao": "Base de conhecimento interna para suporte ao usuário final." },
              { "nome": "Diversos", "descricao": "Funcionalidades auxiliares e manutenções técnicas do sistema web." }
            ]
          },
          {
            "produto": "Meu RH",
            "descricao": "Portal de autoatendimento para colaboradores e gestores de equipe.",
            "modulos": [
              { "nome": "Apontamento", "descricao": "Registro de presença via web ou aplicativo móvel." },
              { "nome": "Funcionário", "descricao": "Perfil pessoal com histórico de dados e documentos do colaborador." },
              { "nome": "Quadro de Horários", "descricao": "Visualização da jornada de trabalho e turnos alocados." },
              { "nome": "Cadastro", "descricao": "Atualização cadastral e envio de documentos pelo colaborador." },
              { "nome": "Solicitações", "descricao": "Fluxo de pedidos de reembolso, declarações e alterações." },
              { "nome": "Férias", "descricao": "Consulta de saldo de períodos aquisitivos e pedidos de gozo." },
              { "nome": "Relatórios", "descricao": "Extratos de horas, recibos e informes de rendimentos." },
              { "nome": "Configurações", "descricao": "Personalização de níveis de acesso e notificações do portal." },
              { "nome": "Organograma", "descricao": "Visualização hierárquica da estrutura da empresa." },
              { "nome": "Uso Interno", "descricao": "Área restrita para administração de RH e logs do sistema." },
              { "nome": "Simulações", "descricao": "Cálculos prévios de proventos e descontos para planejamento." },
              { "nome": "Movimentos", "descricao": "Registro de alterações de cargo, salário ou departamento." },
              { "nome": "Escala", "descricao": "Gestão de revezamentos e folgas para jornadas complexas." },
              { "nome": "Arquivos", "descricao": "Repositório de documentos digitais e GED (Gestão Eletrônica de Documentos)." },
              { "nome": "Colaboradores", "descricao": "Visão do gestor sobre sua equipe direta e subordinados." }
            ]
          },
          {
            "produto": "Scritta SQL",
            "descricao": "Software de escrita fiscal e apuração de impostos com foco em compliance.",
            "modulos": [
              { "nome": "Treinamento Completo", "descricao": "Guias de vídeo e textos para capacitação no uso das ferramentas fiscais." },
              { "nome": "Documentos Fiscais", "descricao": "Escrituração de entradas, saídas e serviços (NF-e, NFS-e, CT-e)." },
              { "nome": "Guias e Declarações", "descricao": "Geração automática de SPED Fiscal, EFD Contribuições e guias de recolhimento." },
              { "nome": "Impostos Federais", "descricao": "Cálculo de IRPJ, CSLL, PIS e COFINS nos regimes Lucro Real e Presumido." }
            ]
          },
          {
            "produto": "Contábil SQL",
            "descricao": "Gestão contábil robusta, integrando lançamentos financeiros à escrituração contábil.",
            "modulos": [
              { "nome": "BI Contábil", "descricao": "Business Intelligence para análise de indicadores e saúde financeira da empresa." },
              { "nome": "Obrigações Federais", "descricao": "Preparação e validação de arquivos para ECD e ECF." },
              { "nome": "Lotes", "descricao": "Processamento agrupado de lançamentos para agilizar o fechamento." }
            ]
          },
          {
            "produto": "Finanças SQL",
            "descricao": "Controle completo do fluxo de caixa, tesouraria e planejamento orçamentário.",
            "modulos": [
              { "nome": "Títulos a Receber", "descricao": "Gestão de cobranças, baixa de títulos e controle de inadimplência." },
              { "nome": "Fluxo de Caixa", "descricao": "Projeção de entradas e saídas para suporte à tomada de decisão financeira." },
              { "nome": "Orçamento", "descricao": "Criação de centros de custo e monitoramento do planejado vs realizado." }
            ]
          },
          {
            "produto": "Controller",
            "descricao": "Sistema ERP legado/estável voltado para gestão comercial e financeira integrada.",
            "modulos": [
              { "nome": "Cobrança Recorrente", "descricao": "Automação de faturamento para serviços de assinatura ou mensalidades." },
              { "nome": "Ped/Orç/Prop", "descricao": "Fluxo completo de vendas desde o orçamento até a proposta comercial." }
            ]
          },
          {
            "produto": "Estoque SQL",
            "descricao": "Controle de inventário, almoxarifado e movimentação de mercadorias.",
            "modulos": [
              { "nome": "Controle de Almoxarifado", "descricao": "Gerenciamento físico de itens e requisições internas de materiais." },
              { "nome": "Composição de Itens", "descricao": "Definição de 'Kits' ou estruturas de produtos para venda e produção." }
            ]
          },
          {
            "produto": "Painel do Cliente",
            "descricao": "Central de relacionamento entre o cliente e a Nasajon Sistemas.",
            "modulos": [
              { "nome": "Boletos & Faturas", "descricao": "Acesso à segunda via e histórico financeiro do contrato com a Nasajon." },
              { "nome": "Tíquetes", "descricao": "Abertura e acompanhamento de chamados de suporte técnico." },
              { "nome": "Base de Conhecimento", "descricao": "Repositório de artigos de ajuda para resolução de problemas comuns." }
            ]
          }
        ]

        # 2. DADOS DE CAUSAS
        DATA_CAUSAS = [
            {"nome": "Erro Operacional / Parametrização", "descricao": "O software funcionou conforme projetado, mas os dados inseridos, parâmetros ou processos executados pelo usuário estavam incorretos."},
            {"nome": "Defeito de Software / Bug", "descricao": "Falhas no código, erros de lógica, crashes, problemas visuais ou comportamentos inesperados do sistema."},
            {"nome": "Falha de Ambiente / Infraestrutura", "descricao": "Problemas relacionados à rede, sistema operacional, certificados digitais locais, instalação ou hardware do cliente."},
            {"nome": "Gestão de Acesso / Identidade", "descricao": "Bloqueios de senha, usuários inativos ou falta de permissão para rotinas específicas."},
            {"nome": "Limitação do Sistema / By Design", "descricao": "O sistema funciona conforme projetado, mas não atende a uma necessidade específica do cliente (Feature Request ou Restrição)."},
            {"nome": "Inconsistência de Dados / Banco", "descricao": "Dados corrompidos, registros órfãos ou necessidade de scripts de correção diretamente no banco de dados."},
            {"nome": "Fator Externo / Terceiros", "descricao": "Erros causados por instabilidade em portais do governo (eCac, eSocial) ou arquivos gerados por terceiros."},
            {"nome": "Dúvida / Negócio (Não Técnico)", "descricao": "Questões comerciais, dúvidas conceituais ou insatisfação com preço."},
            {"nome": "Outro", "descricao": "Causas que não se enquadram em nenhuma das categorias acima ou não puderam ser identificadas."}
        ]

        # 3. DADOS DE SINTOMAS
        DATA_SINTOMAS = [
            {"nome": "Erro de Transmissão (Governo)", "descricao": "Falhas na comunicação com eSocial, REINF ou DCTFWeb. Geralmente retornam códigos de erro ou XML inválido."},
            {"nome": "Erro de Cálculo / Divergência de Valor", "descricao": "O sistema funciona, mas o valor matemático final (imposto, salário, férias) não bate com o esperado pelo cliente."},
            {"nome": "Dúvida de Processo / \"Como Fazer\"", "descricao": "Solicitação de orientação sobre como realizar uma tarefa no sistema ou dúvida de legislação aplicada."},
            {"nome": "Dúvida de Cadastro / Configuração", "descricao": "Dificuldades em inserir dados cadastrais, vincular usuários ou parametrizar o sistema."},
            {"nome": "Bug de Funcionalidade / Erro de Tela", "descricao": "Erros técnicos de sistema, 'crashes', mensagens de erro de programação ou funcionalidades travadas."},
            {"nome": "Indisponibilidade / Falha de Acesso", "descricao": "Problemas de login, senha, queda de conexão ou servidor fora do ar."},
            {"nome": "Dúvida sobre Relatório / Visualização", "descricao": "Problemas na saída de dados: relatórios em branco, layout desconfigurado ou dados não visíveis na tela."},
            {"nome": "Solicitação de Serviço Interno / Infra", "descricao": "Demandas para a equipe interna de TI/Dados, Backups ou Atualizações de versão."},
            {"nome": "Solicitação Administrativa (Financeiro)", "descricao": "Pedidos relacionados a boletos, pagamentos e questões contratuais."},
            {"nome": "Interesse Comercial / Aquisição", "descricao": "Leads ou clientes querendo comprar novos módulos/sistemas."},
            {"nome": "Risco de Churn / Insatisfação", "descricao": "Reclamações sobre preço, qualidade do serviço ou ameaça de cancelamento."},
            {"nome": "Outro", "descricao": "Sintomas que não se enquadram em nenhuma das categorias acima."}
        ]

        # 4. DADOS DE SOLUÇÕES
        DATA_SOLUCOES = [
            {"nome": "Orientação e Educação (Procedimental)", "descricao": "O analista explicou como o sistema funciona ou indicou o caminho do menu. Nenhuma alteração técnica foi feita pelo analista, apenas instrução."},
            {"nome": "Correção de Dados / Saneamento", "descricao": "Ação focada em corrigir registros específicos que estavam errados, duplicados ou travados (muito comum no eSocial)."},
            {"nome": "Configuração e Parametrização", "descricao": "Alteração de configurações globais, cadastros de empresas ou regras de cálculo para mudar o comportamento do sistema."},
            {"nome": "Intervenção Técnica / Infraestrutura", "descricao": "Soluções que exigem privilégios administrativos, acesso ao banco de dados, infraestrutura de rede ou gestão de identidade."},
            {"nome": "Escalonamento / Correção de Bug", "descricao": "O problema não pôde ser resolvido pelo suporte e gerou uma tarefa de correção ou análise para o time de Desenvolvimento."},
            {"nome": "Serviço Administrativo / Comercial", "descricao": "Ações que não envolvem o software diretamente, mas a relação comercial/financeira com o cliente."},
            {"nome": "Outro", "descricao": "Soluções que não se enquadram em nenhuma das categorias acima ou não houve solução clara."}
        ]

        st.warning("⚠️ Atenção: A carga pode gerar duplicidade se os itens já existirem.")
        if st.button("🗑️ LIMPAR TODAS AS TAXONOMIAS (Zerar Banco)", type="primary"):
            st.error("Por segurança, a limpeza total deve ser feita no banco de dados com o comando: TRUNCATE TABLE taxonomy_nodes RESTART IDENTITY CASCADE;")

        c1, c2, c3, c4 = st.columns(4)
        
        headers = {"X-Tenant-ID": tenant_id}

        # --- BOTÃO 1: RECURSOS ---
        if c1.button("🚀 Carga: Recursos"):
            bar = st.progress(0); txt = st.empty()
            total = len(DATA_RECURSOS)
            for i, item in enumerate(DATA_RECURSOS):
                txt.text(f"Criando Produto: {item['produto']}...")
                try:
                    # Cria Pai
                    resp = requests.post(TAXONOMY_URL, json={
                        "type": "recurso", "name": item['produto'], "description": item['descricao'], "parent_id": None
                    }, headers=headers)
                    if resp.status_code == 201:
                        parent_id = resp.json().get('id')
                        # Cria Filhos
                        for mod in item.get('modulos', []):
                            requests.post(TAXONOMY_URL, json={
                                "type": "recurso", "name": mod['nome'], "description": mod['descricao'], "parent_id": parent_id
                            }, headers=headers)
                except Exception as e: st.error(e)
                bar.progress((i+1)/total)
            txt.success("Recursos importados!")
            st.rerun()

        # --- BOTÃO 2: CAUSAS ---
        if c2.button("🚀 Carga: Causas"):
            bar = st.progress(0); txt = st.empty()
            total = len(DATA_CAUSAS)
            for i, item in enumerate(DATA_CAUSAS):
                txt.text(f"Criando Causa: {item['nome']}...")
                requests.post(TAXONOMY_URL, json={
                    "type": "causa", "name": item['nome'], "description": item['descricao'], "parent_id": None
                }, headers=headers)
                bar.progress((i+1)/total)
            txt.success("Causas importadas!")
            st.rerun()

        # --- BOTÃO 3: SINTOMAS ---
        if c3.button("🚀 Carga: Sintomas"):
            bar = st.progress(0); txt = st.empty()
            total = len(DATA_SINTOMAS)
            for i, item in enumerate(DATA_SINTOMAS):
                txt.text(f"Criando Sintoma: {item['nome']}...")
                requests.post(TAXONOMY_URL, json={
                    "type": "sintoma", "name": item['nome'], "description": item['descricao'], "parent_id": None
                }, headers=headers)
                bar.progress((i+1)/total)
            txt.success("Sintomas importados!")
            st.rerun()

        # --- BOTÃO 4: SOLUÇÕES ---
        if c4.button("🚀 Carga: Soluções"):
            bar = st.progress(0); txt = st.empty()
            total = len(DATA_SOLUCOES)
            for i, item in enumerate(DATA_SOLUCOES):
                txt.text(f"Criando Solução: {item['nome']}...")
                requests.post(TAXONOMY_URL, json={
                    "type": "solucao", "name": item['nome'], "description": item['descricao'], "parent_id": None
                }, headers=headers)
                bar.progress((i+1)/total)
            txt.success("Soluções importadas!")
            st.rerun()

    # --- FIM DA ÁREA DE IMPORTAÇÃO ---

    with col_tree:
        st.subheader("Estrutura Atual")
        if tree_options:
            selected_node_tuple = st.radio(
                "Navegador:",
                options=tree_options,
                format_func=lambda x: x[1],
                label_visibility="collapsed"
            )
            selected_id = selected_node_tuple[0]
            selected_node_data = node_map.get(selected_id)
        else:
            st.warning("Lista vazia.")
            selected_node_data = None
            selected_id = None

    with col_edit:
        action = st.radio("Ação:", ["Editar Selecionado", "Criar Novo Item"], horizontal=True)
        st.divider()

        # CASO 1: CRIAÇÃO (Formulário Próprio)
        if action == "Criar Novo Item":
            st.markdown(f"#### Novo Item em: {selected_label}")
            
            # Form específico para criação
            with st.form("create_node_form"):
                form_name = st.text_input("Nome (Curto):")
                form_desc = st.text_area("Descrição:")
                
                # Hierarquia
                parent_opts = [(None, "Nenhum (Raiz)")] + tree_options
                form_parent = st.selectbox("Pai (Hierarquia):", options=parent_opts, format_func=lambda x: x[1])
                
                # METADADOS ESPECÍFICOS
                form_meta = {}
                if selected_type == 'causa':
                    form_meta['responsabilidade'] = st.selectbox("Responsabilidade:", ["Suporte", "Cliente", "Desenvolvimento", "Infra"])
                
                if selected_type in ['sintoma', 'erro', 'solucao']:
                    ex_text = st.text_area("Exemplos/Variações (separar por ;):", placeholder="Exemplo 1; Exemplo 2")
                    form_meta['exemplos'] = [x.strip() for x in ex_text.split(';') if x.strip()]

                submitted = st.form_submit_button("Salvar Novo")
                
                if submitted:
                    if not form_name:
                        st.error("Nome é obrigatório.")
                    else:
                        payload = {
                            "type": selected_type,
                            "name": form_name,
                            "description": form_desc,
                            "parent_id": form_parent[0],
                            "metadata": form_meta
                        }
                        try:
                            r = requests.post(TAXONOMY_URL, json=payload, headers={"X-Tenant-ID": tenant_id})
                            if r.status_code == 201:
                                st.success("Criado!")
                                st.rerun()
                            else: st.error(r.text)
                        except Exception as e: st.error(f"Erro: {e}")

        # CASO 2: EDIÇÃO (Só mostra o form SE tiver item selecionado)
        elif action == "Editar Selecionado":
            if selected_node_data:
                st.markdown(f"#### Editando: {selected_node_data['name']}")
                
                # Form específico para edição
                with st.form("edit_node_form"):
                    form_name = st.text_input("Nome:", value=selected_node_data['name'])
                    form_desc = st.text_area("Descrição:", value=selected_node_data.get('description', ''))
                    
                    # Hierarquia (evita ciclo removendo o próprio ID)
                    valid_parents = [(None, "Nenhum (Raiz)")] + [t for t in tree_options if t[0] != selected_id]
                    curr_pid = selected_node_data['parent_id']
                    def_idx = next((i for i, v in enumerate(valid_parents) if v[0] == curr_pid), 0)
                    
                    form_parent = st.selectbox("Pai:", options=valid_parents, index=def_idx, format_func=lambda x: x[1])
                    
                    # RECUPERA METADADOS
                    curr_meta = selected_node_data.get('metadata', {}) or {}
                    form_meta = {}
                    
                    if selected_type == 'causa':
                        opcoes_resp = ["Suporte", "Cliente", "Desenvolvimento", "Infra"]
                        val_atual = curr_meta.get('responsabilidade', 'Suporte')
                        idx_resp = opcoes_resp.index(val_atual) if val_atual in opcoes_resp else 0
                        form_meta['responsabilidade'] = st.selectbox("Responsabilidade:", opcoes_resp, index=idx_resp)
                    
                    if selected_type in ['sintoma', 'erro', 'solucao']:
                        curr_exs = "; ".join(curr_meta.get('exemplos', []))
                        ex_text = st.text_area("Exemplos (sep. por ;):", value=curr_exs)
                        form_meta['exemplos'] = [x.strip() for x in ex_text.split(';') if x.strip()]
                    
                    # Botões de Ação
                    c1, c2 = st.columns(2)
                    # Agora os botões estão garantidos dentro deste form
                    update_click = c1.form_submit_button("💾 Atualizar")
                    delete_click = c2.form_submit_button("🗑️ Deletar", type="primary")

                    if update_click:
                        payload = {
                            "name": form_name, "description": form_desc, 
                            "parent_id": form_parent[0], "metadata": form_meta
                        }
                        try:
                            r = requests.put(f"{TAXONOMY_URL}/{selected_id}", json=payload, headers={"X-Tenant-ID": tenant_id})
                            if r.status_code == 200:
                                st.success("Atualizado!")
                                st.rerun()
                            else: st.error(f"Erro: {r.text}")
                        except Exception as e: st.error(e)
                    
                    if delete_click:
                        try:
                            r = requests.delete(f"{TAXONOMY_URL}/{selected_id}", headers={"X-Tenant-ID": tenant_id})
                            if r.status_code == 200:
                                st.success("Deletado!")
                                st.rerun()
                            else: st.error(f"Erro: {r.text}")
                        except Exception as e: st.error(e)

            else:
                # CASO 3: NENHUM ITEM SELECIONADO
                # Aqui NÃO abrimos st.form nenhum, então não dá erro de "Missing Submit Button"
                st.info("👈 Selecione um item na lista à esquerda para editar.")
