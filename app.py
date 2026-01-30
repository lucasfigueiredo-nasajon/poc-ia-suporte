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
tab_chat, tab_admin, tab_prompts, tab_taxonomy, tab_tickets = st.tabs([
    "💬 Chat de Suporte", 
    "⚙️ Ingestão de Dados", 
    "📝 Gestão de Prompts",
    "🗂️ Gestão de Taxonomias",
    "📊 Gestão de Tickets" # <--- NOVA ABA
])

# ---------------------------------------------------------
# ABA 1: CHAT DE SUPORTE
# ---------------------------------------------------------
# --- CONSTANTES & DEFAULTS ---
BASE_URL = "https://api.nasajon.app/nsj-ia-suporte"
# BASE_URL = "http://localhost:5000/nsj-ia-suporte" # Dev Local

INGEST_URL = f"{BASE_URL}/ingest-pipeline"
PROMPTS_URL = f"{BASE_URL}/prompts"
QUERY_URL = f"{BASE_URL}/query" # <--- ADICIONE ESSA CONSTANTE

# ... (Resto das configurações iniciais mantém igual) ...

# ---------------------------------------------------------
# ABA 1: CHAT DE SUPORTE
# ---------------------------------------------------------
with tab_chat:
    # Botão de Limpeza
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
        # 1. Adiciona msg do usuário ao histórico visual
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # 2. Chama a API do Backend
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            with st.spinner("🧠 Analisando base de conhecimento..."):
                try:
                    # Payload para o Orchestrator
                    payload = {
                        "user_id": "streamlit_user", 
                        "conversation_id": st.session_state.conversation_id,
                        "message": prompt
                    }
                    
                    headers = {
                        "X-Tenant-ID": tenant_id,
                        "Content-Type": "application/json"
                    }
                    
                    # Chamada POST para a API
                    response = requests.post(QUERY_URL, json=payload, headers=headers, timeout=60)
                    
                    if response.status_code == 200:
                        data = response.json()
                        # Assume que o backend devolve {"answer": "texto..."}
                        # Ajuste a chave 'answer' se seu backend retornar outro nome (ex: 'response')
                        full_response = data.get("answer", "⚠️ O backend respondeu, mas sem conteúdo de texto.")
                        
                        message_placeholder.markdown(full_response)
                        
                        # Salva resposta no histórico
                        st.session_state.messages.append({"role": "assistant", "content": full_response})
                    else:
                        error_msg = f"❌ Erro {response.status_code}: {response.text}"
                        message_placeholder.error(error_msg)
                        
                except requests.exceptions.ConnectionError:
                    message_placeholder.error("🚨 Não foi possível conectar ao servidor. Verifique se o Backend está rodando.")
                except Exception as e:
                    message_placeholder.error(f"🚨 Erro inesperado: {str(e)}")
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

# ... (código anterior mantido) ...

    # ... (código anterior da aba taxonomy) ...

    # --- ÁREA DE IMPORTAÇÃO EM LOTE ---
    

    
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

#=========================================================
# ABA 5: GESTÃO DE TICKETS (NEO4J)
# =========================================================
with tab_tickets:
    st.header("📊 Análise do Knowledge Graph (Neo4j)")
    st.info("Visualização em tempo real dos tickets processados e armazenados no grafo.")

    col_kpi1, col_kpi2, col_refresh = st.columns([2, 2, 1])
    
    # Botão de Atualizar
    if col_refresh.button("🔄 Atualizar Dados"):
        st.rerun()

    # --- 1. BUSCA DADOS DE CLASSIFICAÇÃO (UTIL / INUTIL) ---
    try:
        resp_class = requests.get(f"{STATS_URL}/tickets/classification", headers={"X-Tenant-ID": tenant_id})
        if resp_class.status_code == 200:
            data_class = resp_class.json()
            
            # KPI: Total de Tickets
            total_tickets = sum([item['value'] for item in data_class])
            col_kpi1.metric("Total de Tickets Ingeridos", total_tickets)
            
            # KPI: Taxa de Utilidade
            util_tickets = next((item['value'] for item in data_class if item['label'] == 'UTIL'), 0)
            taxa_util = (util_tickets / total_tickets * 100) if total_tickets > 0 else 0
            col_kpi2.metric("Taxa de Tickets Úteis", f"{taxa_util:.1f}%")

            st.divider()

            # GRÁFICO 1: Distribuição de Utilidade
            c_chart1, c_chart2 = st.columns(2)
            with c_chart1:
                st.subheader("Classificação (IA)")
                if data_class:
                    df_class = pd.DataFrame(data_class)
                    st.bar_chart(df_class.set_index("label"))
                else:
                    st.warning("Sem dados de classificação.")

    except Exception as e:
        st.error(f"Erro ao conectar com Neo4j Stats: {e}")

    # --- 2. BUSCA DADOS DE SINTOMAS MAIS COMUNS ---
    try:
        resp_sint = requests.get(f"{STATS_URL}/tickets/sintomas", headers={"X-Tenant-ID": tenant_id})
        if resp_sint.status_code == 200:
            data_sint = resp_sint.json()
            
            with c_chart2:
                st.subheader("Top Sintomas Recorrentes")
                if data_sint:
                    df_sint = pd.DataFrame(data_sint)
                    # Gráfico de barras horizontal para sintomas (melhor leitura)
                    st.bar_chart(df_sint.set_index("label"), horizontal=True)
                else:
                    st.warning("Sem dados de sintomas.")
                    
            # Tabela Detalhada
            with st.expander("📋 Ver Tabela de Sintomas Completa"):
                if data_sint:
                    st.dataframe(pd.DataFrame(data_sint), use_container_width=True)
                    
    except Exception as e:
        st.error(f"Erro ao buscar sintomas: {e}")
