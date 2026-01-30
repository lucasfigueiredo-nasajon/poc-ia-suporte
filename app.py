import streamlit as st
import requests
import uuid
import json
import pandas as pd
import random
import altair as alt

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Nasajon IA Suporte", 
    page_icon="🤖", 
    layout="wide"
)

# --- CONSTANTES GLOBAIS ---
BASE_URL = "https://api.nasajon.app/nsj-ia-suporte"
# BASE_URL = "http://localhost:5000/nsj-ia-suporte" # Para teste local

# Rotas do Sistema
STATS_URL = f"{BASE_URL}/stats" # <--- CORREÇÃO APLICADA
CHAT_URL = f"{BASE_URL}/queries"
INGEST_URL = f"{BASE_URL}/ingest-pipeline"
PROMPTS_URL = f"{BASE_URL}/prompts"
TAXONOMY_URL = f"{BASE_URL}/taxonomies/nodes"

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
# ---------------------------------------------------------
# ABA 1: CHAT DE SUPORTE (CORRIGIDO: BOTÃO + SISTEMA FIXO)
# ---------------------------------------------------------
with tab_chat:
    # --- 1. BOTÃO DE LIMPEZA (RESTAURADO) ---
    col_btn, _ = st.columns([2, 8])
    with col_btn:
        if st.button("🗑️ Limpar Conversa / Reiniciar", type="secondary"):
            st.session_state.messages = []
            st.session_state.conversation_id = str(uuid.uuid4())
            st.rerun()
    
    st.divider()

    # --- 2. CONFIGURAÇÕES FIXAS (HARDCODED) ---
    sistema = "Persona SQL"

    # --- 3. CONTAINER DE MENSAGENS ---
    chat_container = st.container()

    # --- 4. INPUT DE TEXTO ---
    prompt = st.chat_input("Olá! Em que posso ajudar?")

    # --- 5. RENDERIZAÇÃO DO HISTÓRICO ---
    with chat_container:
        def get_avatar(role, metadata=None):
            if role == "user": return "👤"
            if metadata:
                agent = metadata.get("agent", "")
                if "receptionist" in agent: return "💁‍♀️"
                if "specialist" in agent: return "👷‍♂️"
                if "ticket" in agent: return "🎫"
            return "🤖"

        for message in st.session_state.messages:
            avatar = get_avatar(message["role"], message.get("debug"))
            with st.chat_message(message["role"], avatar=avatar):
                st.markdown(message["content"])
                if "debug" in message:
                    with st.expander("ℹ️ Bastidores"):
                        st.json(message["debug"])

    # --- 6. PROCESSAMENTO DO PROMPT ---
    if prompt:
        with chat_container:
            st.chat_message("user", avatar="👤").markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})

            with st.chat_message("assistant", avatar="🤖"):
                message_placeholder = st.empty()
                message_placeholder.markdown("🧠 *Analisando solicitação...*")
                
                try:
                    # Prepara histórico
                    historico_para_enviar = []
                    for msg in st.session_state.messages[:-1]:
                        msg_payload = {"role": msg["role"], "content": msg["content"]}
                        if "agent" in msg: msg_payload["agent"] = msg["agent"]
                        historico_para_enviar.append(msg_payload)

                    payload = {
                        "conversation_id": st.session_state.conversation_id,
                        "message": prompt,
                        "history": historico_para_enviar,
                        # Aqui usamos a variável 'sistema' que definimos fixa no topo
                        "context": {"sistema": sistema} 
                    }
                    
                    headers = {
                        "X-Tenant-ID": tenant_id,
                        "Content-Type": "application/json"
                    }
                    
                    # Chama API
                    response = requests.post(CHAT_URL, json=payload, headers=headers, timeout=60)
                    
                    if response.status_code == 200:
                        data = response.json()
                        bot_response = data.get("response") or data.get("answer") or "⚠️ Resposta vazia."
                        metadata = data.get("metadata", {})
                        
                        message_placeholder.markdown(bot_response)
                        
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": bot_response, 
                            "debug": metadata,
                            "agent": metadata.get("agent")
                        })
                        st.rerun()
                    else:
                        message_placeholder.error(f"❌ Erro {response.status_code}: {response.text}")
                
                except requests.exceptions.ConnectionError:
                    message_placeholder.error(f"🔌 Não foi possível conectar em: {CHAT_URL}")
                except Exception as e:
                    message_placeholder.error(f"🔌 Erro inesperado: {str(e)}")
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

    API_URL = PROMPTS_URL
    
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
import altair as alt
import random

# =========================================================
# ABA 5: GESTÃO DE TICKETS (COM DETALHES E CHAT)
# =========================================================
with tab_tickets:
    st.header("📊 Análise de Tickets (Protótipo Visual)")
    st.info("Visualização baseada em dados mockados do Persona SQL para validação de layout.")

    # --- 1. CONFIGURAÇÃO DAS TAXONOMIAS ---
    TAXONOMIA_PERSONA = {
        "Arquivos Oficiais": ["Geral"],
        "Cadastros e Configurações": ["Geral"],
        "Cálculos e Rotinas": ["Folha", "Férias", "Rescisão", "13º Salário"],
        "eSocial": [
            "DCTFWeb", "Eventos Iniciais", "Eventos Não Periódicos", 
            "Eventos Periódicos", "FGTS Digital", "Outro", "Painel eSocial", "SST"
        ]
    }
    
    CATEGORIAS_SINTOMA = [
        "Bug de Funcionalidade / Erro de Tela", "Dúvida de Cadastro / Configuração",
        "Dúvida de Processo / \"Como Fazer\"", "Dúvida sobre Relatório / Visualização",
        "Erro de Cálculo / Divergência de Valor", "Erro de Transmissão (Governo)",
        "Indisponibilidade / Falha de Acesso", "Interesse Comercial / Aquisição",
        "Outro", "Risco de Churn / Insatisfação", "Solicitação Administrativa (Financeiro)",
        "Solicitação de Serviço Interno / Infra"
    ]
    
    CATEGORIAS_CAUSA = [
        "Defeito de Software / Bug", "Dúvida / Negócio (Não Técnico)",
        "Erro Operacional / Parametrização", "Falha de Ambiente / Infraestrutura",
        "Fator Externo / Terceiros", "Gestão de Acesso / Identidade",
        "Inconsistência de Dados / Banco", "Limitação do Sistema / By Design", "Outro"
    ]
    
    CATEGORIAS_SOLUCAO = [
        "Configuração e Parametrização", "Correção de Dados / Saneamento",
        "Escalonamento / Correção de Bug", "Intervenção Técnica / Infraestrutura",
        "Orientação e Educação (Procedimental)", "Outro", "Serviço Administrativo / Comercial"
    ]
    
    EVENTOS_ESOCIAL = ["S-1000", "S-1005", "S-1010", "S-2200", "S-2299", "S-1200", "S-1210", "S-1299"]
    CODIGOS_ERRO = ["105", "106", "1728", "536", "588", "Access violation", "Violação de PK"]

    # --- 2. GERADOR DE DADOS MOCKADOS (ENRIQUECIDO) ---
    @st.cache_data
    def load_mock_data(qtd=60):
        data = []
        for i in range(1, qtd + 1):
            nivel_2 = random.choice(list(TAXONOMIA_PERSONA.keys()))
            nivel_3 = random.choice(TAXONOMIA_PERSONA[nivel_2])
            cat_sintoma = random.choice(CATEGORIAS_SINTOMA)
            cat_causa = random.choice(CATEGORIAS_CAUSA)
            cat_solucao = random.choice(CATEGORIAS_SOLUCAO)
            
            evento = None
            erro = None
            detalhe_extra = ""

            # Lógica simples para contexto
            if nivel_2 == "eSocial":
                evento = random.choice(EVENTOS_ESOCIAL)
                if cat_sintoma == "Erro de Transmissão (Governo)":
                    erro = random.choice(CODIGOS_ERRO)
                    detalhe_extra = f"retornando erro {erro}."
                else:
                    detalhe_extra = "com status aguardando retorno."
            elif cat_sintoma == "Erro de Cálculo / Divergência de Valor":
                 detalhe_extra = "com diferença de centavos no líquido."
            elif cat_sintoma == "Bug de Funcionalidade / Erro de Tela":
                 erro = random.choice(["Access violation", "Violação de PK"]) if random.random() > 0.5 else None
                 detalhe_extra = f"apresentando mensagem {erro}." if erro else "travando a tela."

            # Detalhes Gerados
            detalhe_sintoma = random.choice([
                f"Cliente relata problema no {nivel_3} {detalhe_extra}",
                f"Dificuldade em processar {nivel_3}, sistema {detalhe_extra}",
                f"Ao tentar gerar {nivel_2}, ocorre inconsistência {detalhe_extra}",
            ])

            detalhe_causa = random.choice([
                f"Identificado que o cadastro em {nivel_3} estava incompleto.",
                f"O ambiente do cliente estava sem permissão de escrita na pasta do sistema.",
                f"Falha na comunicação com o webservice do governo (instabilidade).",
                f"Bug na versão atual relacionado ao cálculo de {nivel_3}.",
                f"Usuário desconhecia o parâmetro X na configuração global."
            ])

            detalhe_solucao = random.choice([
                f"Orientado cliente a preencher o campo obrigatório em {nivel_3}.",
                f"Realizado script de correção no banco de dados para ajustar a referência.",
                f"Aberto chamado para o desenvolvimento (Issue #1234).",
                f"Atualizado sistema para a versão mais recente (Patch de correção).",
                f"Reiniciado serviços do Persona e liberado permissões de rede."
            ])

            # Conversa Simulada
            conversa = [
                {"role": "user", "author": "Cliente", "text": f"Olá, estou com problemas no {nivel_2}. {detalhe_sintoma}"},
                {"role": "assistant", "author": "Agente IA", "text": f"Olá! Entendo. Parece ser um caso de {cat_sintoma}. Poderia me enviar um print?"},
                {"role": "user", "author": "Cliente", "text": "Segue em anexo. O erro acontece sempre que tento salvar."},
                {"role": "assistant", "author": "Agente IA", "text": f"Analisando o log, parece que a causa é: {cat_causa}. Sugiro: {detalhe_solucao}"},
                {"role": "user", "author": "Cliente", "text": "Funcionou! Obrigado."}
            ]

            ticket = {
                "id": f"T{i:03d}",
                "recurso_nivel_1": "Persona SQL",
                "recurso_nivel_2": nivel_2,
                "recurso_nivel_3": nivel_3,
                "sintoma_categoria": cat_sintoma,
                "sintoma_detalhe": detalhe_sintoma,
                "causa_categoria": cat_causa,
                "causa_detalhe": detalhe_causa,
                "solucao_categoria": cat_solucao,
                "solucao_detalhe": detalhe_solucao,
                "evento_esocial": evento if evento else "-",
                "codigo_erro": erro if erro else "-",
                "conversa_completa": conversa
            }
            data.append(ticket)
        return pd.DataFrame(data)

    df_tickets = load_mock_data(qtd=60)

    # --- 3. SELETORES E GRÁFICO ---
    st.markdown("### 🔍 Visão Geral")
    opcoes_visao = {
        "Por Causa Raiz": "causa_categoria",
        "Por Categoria de Sintoma": "sintoma_categoria",
        "Por Solução Aplicada": "solucao_categoria",
        "Por Módulo": "recurso_nivel_2",
        "Por Evento eSocial": "evento_esocial"
    }
    
    col_sel, col_metrics = st.columns([1, 2])
    with col_sel:
        visao_selecionada = st.selectbox("Selecione a Taxonomia:", list(opcoes_visao.keys()))
        coluna_analise = opcoes_visao[visao_selecionada]

    df_chart = df_tickets[df_tickets[coluna_analise] != "-"][coluna_analise].value_counts().reset_index()
    df_chart.columns = ["Categoria", "Quantidade"]

    with col_metrics:
        total = len(df_tickets)
        if not df_chart.empty:
            top_item = df_chart.iloc[0]["Categoria"]
            st.metric("Total de Tickets", total, delta=f"Top ofensor: {top_item}", delta_color="inverse")

    st.subheader(f"Distribuição: {visao_selecionada}")
    
    if not df_chart.empty:
        chart = alt.Chart(df_chart).mark_bar(color="#FF4B4B").encode(
            x=alt.X('Quantidade', title='Qtd Tickets'), 
            y=alt.Y('Categoria', sort='-x', title=None, axis=alt.Axis(labelLimit=300)),
            tooltip=['Categoria', 'Quantidade']
        ).properties(height=350)
        
        text = chart.mark_text(align='left', baseline='middle', dx=3).encode(text='Quantidade')
        st.altair_chart(chart + text, use_container_width=True)
    else:
        st.warning("Nenhum dado para esta visão.")

    st.divider()

    # --- 4. DETALHAMENTO DA CATEGORIA ---
    st.markdown(f"### 🔬 Detalhar Categoria: {visao_selecionada}")
    
    if not df_chart.empty:
        col_drill1, col_drill2 = st.columns([1, 3])
        with col_drill1:
            categorias = df_chart["Categoria"].tolist()
            cat_foco = st.radio("Selecione o grupo:", options=categorias)

        with col_drill2:
            df_filtro = df_tickets[df_tickets[coluna_analise] == cat_foco]
            st.write(f"**{len(df_filtro)} Tickets em:** `{cat_foco}`")
            st.dataframe(
                df_filtro[["id", "recurso_nivel_2", "recurso_nivel_3", "sintoma_detalhe"]], 
                use_container_width=True, hide_index=True,
                column_config={"id": "ID", "sintoma_detalhe": st.column_config.TextColumn("Resumo", width="large")}
            )
    
    st.divider()

    # --- 5. FICHA TÉCNICA DO TICKET (ATUALIZADA) ---
    st.markdown("### 🎫 Ficha Técnica do Ticket")
    st.caption("Pesquise pelo ID para ver a classificação completa e o histórico.")

    col_search, col_card = st.columns([1, 3])

    with col_search:
        search_id = st.text_input("Digite o ID do Ticket:", placeholder="Ex: T015").upper()
        if not df_tickets.empty:
            sample_id = df_tickets.iloc[0]['id']
            st.caption(f"Tente: {sample_id}")

    with col_card:
        if search_id:
            ticket_found = df_tickets[df_tickets["id"] == search_id]
            
            if not ticket_found.empty:
                t = ticket_found.iloc[0]
                
                # CARD PRINCIPAL
                with st.container(border=True):
                    # Cabeçalho
                    c1, c2 = st.columns([3, 1])
                    c1.markdown(f"### 📂 {t['recurso_nivel_1']}")
                    c1.caption(f"{t['recurso_nivel_2']} > {t['recurso_nivel_3']}")
                    c2.metric("ID", t['id'])
                    
                    st.divider()

                    # BLOCO DE CLASSIFICAÇÃO DETALHADA
                    # Sintoma
                    st.info(f"**Sintoma ({t['sintoma_categoria']})**")
                    st.write(f"> {t['sintoma_detalhe']}")
                    
                    # Causa
                    st.warning(f"**Causa ({t['causa_categoria']})**")
                    st.write(f"> {t['causa_detalhe']}")
                    
                    # Solução
                    st.success(f"**Solução ({t['solucao_categoria']})**")
                    st.write(f"> {t['solucao_detalhe']}")
                    
                    # Dados Técnicos
                    if t['evento_esocial'] != "-" or t['codigo_erro'] != "-":
                        st.markdown("---")
                        t1, t2 = st.columns(2)
                        if t['evento_esocial'] != "-": t1.metric("Evento eSocial", t['evento_esocial'])
                        if t['codigo_erro'] != "-": t2.metric("Código de Erro", t['codigo_erro'])

                    # CHAT / CONVERSA COMPLETA
                    st.markdown("---")
                    with st.expander("💬 Histórico da Conversa", expanded=False):
                        for msg in t['conversa_completa']:
                            avatar = "👤" if msg['role'] == "user" else "🤖"
                            with st.chat_message(msg['role'], avatar=avatar):
                                st.write(f"**{msg['author']}:** {msg['text']}")

            else:
                st.error(f"Ticket **{search_id}** não encontrado.")
        else:
            st.info("👈 Digite um ID ao lado para carregar os detalhes.")
