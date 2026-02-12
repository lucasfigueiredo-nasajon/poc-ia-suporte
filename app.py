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
if "vision_description" not in st.session_state:
    st.session_state.vision_description = None

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
    # --- NOVO: UPLOADER ACOPLADO AO INPUT ---
    with st.container():
        img_col1, img_col2 = st.columns([0.1, 0.9])
        with img_col1:
            # Botão visual para toggle ou apenas um label
            st.markdown("📎")
        with img_col2:
            img_file = st.file_uploader(
                "Anexar evidência visual para esta mensagem", 
                type=['png', 'jpg', 'jpeg'],
                label_visibility="collapsed"
            )

    # Processamento imediato da imagem se houver upload
    if img_file and (st.session_state.get("last_img_id") != img_file.name):
        with st.spinner("🔍 Analisando imagem..."):
            try:
                from nasajon.service.vision_service import VisionService
                vision = VisionService()
                st.session_state.vision_description = vision.analyze_stream(img_file)
                st.session_state.last_img_id = img_file.name
                st.toast("Imagem analisada com sucesso!", icon="✅")
            except Exception as e:
                st.error(f"Erro ao processar imagem: {e}")

    # --- 4. INPUT DE TEXTO (Seu código original continua aqui) ---
    prompt = st.chat_input("Olá! Em que posso ajudar?")
    # --- FIM DO NOVO: UPLOADER ACOPLADO AO INPUT ---
    #prompt = st.chat_input("Olá! Em que posso ajudar?")

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
            # 1. Recupera descrição da imagem se houver (Contexto Visual)
            contexto_visual = st.session_state.get("vision_description")
            
            # 2. Exibe apenas a mensagem do usuário (Visualmente Limpo)
            # Se houver imagem, mostramos um pequeno ícone indicativo
            display_text = prompt
            if contexto_visual:
                display_text = f"📎 *[Imagem Anexada]*\n\n{prompt}"
            
            st.chat_message("user", avatar="👤").markdown(display_text)
            
            # Salva no histórico visual (apenas o texto original para não poluir)
            st.session_state.messages.append({"role": "user", "content": display_text})

            with st.chat_message("assistant", avatar="🤖"):
                message_placeholder = st.empty()
                message_placeholder.markdown("🧠 *Analisando solicitação...*")
                
                try:
                    # 3. Prepara o Prompt Enriquecido para o Agente
                    prompt_final = prompt
                    if contexto_visual:
                        prompt_final = f" [EVIDÊNCIA VISUAL DA TELA]: {contexto_visual}\n\n[PERGUNTA]: {prompt}"

                    # 4. Prepara histórico (excluindo a mensagem atual que já vai no 'message')
                    historico_para_enviar = []
                    for msg in st.session_state.messages[:-1]:
                        # Limpa marcadores visuais do histórico para não confundir o modelo
                        content_clean = msg["content"].replace("📎 *[Imagem Anexada]*\n\n", "")
                        msg_payload = {"role": msg["role"], "content": content_clean}
                        if "agent" in msg: msg_payload["agent"] = msg["agent"]
                        historico_para_enviar.append(msg_payload)

                    payload = {
                        "conversation_id": st.session_state.conversation_id,
                        "message": prompt_final, # Enviamos o prompt com a descrição da imagem
                        "history": historico_para_enviar,
                        "context": {"sistema": sistema} 
                    }
                    
                    headers = {
                        "X-Tenant-ID": tenant_id,
                        "Content-Type": "application/json"
                    }
                    
                    # 5. Chama API
                    response = requests.post(CHAT_URL, json=payload, headers=headers, timeout=60)
                    
                    if response.status_code == 200:
                        # SUCESSO!
                        
                        # A. Limpa o buffer da imagem para não repetir na próxima
                        st.session_state.vision_description = None
                        st.session_state.last_img_id = None # Reseta ID para permitir re-upload se quiser
                        
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
                                # Se a mensagem já vier formatada como bloco de código (nosso JSON de debug), 
                                # não colocamos crases extras.
                                    if "```" in msg:
                                        status_container.markdown(msg) # Renderiza o bloco de código JSON bonito
                                    else:
                                        status_container.markdown(f"`{msg}`") # Mensagens normais ficam inline
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

# =========================================================
# ABA 5: GESTÃO DE TICKETS (VIA API)
# =========================================================
with tab_tickets:
    st.header("📊 Inteligência de Suporte (Real-Time)")
    
    # URL da nova rota que criamos no wsgi.py
    # BASE_URL já foi definido no início do seu app.py (https://api.nasajon.app/nsj-ia-suporte)
    ANALYTICS_URL = f"{BASE_URL}/tickets/analytics"
    
    # Função para buscar dados da API
    @st.cache_data(ttl=60)
    def fetch_tickets_api():
        try:
            # Consome a rota criada no Passo 2
            resp = requests.get(ANALYTICS_URL, params={"limit": 100}, headers={"X-Tenant-ID": tenant_id}, timeout=10)
            if resp.status_code == 200:
                return pd.DataFrame(resp.json())
            else:
                st.error(f"Erro API: {resp.text}")
                return pd.DataFrame()
        except Exception as e:
            st.error(f"Falha de conexão: {e}")
            return pd.DataFrame()

    # 1. CARREGAMENTO DE DADOS
    with st.spinner("Sincronizando com Knowledge Graph..."):
        df_tickets = fetch_tickets_api()

    if df_tickets.empty:
        st.warning("📭 Nenhum dado retornado pela API ou falha de conexão.")
    else:
        # Processamento de listas para exibição (String bonita)
        df_tickets['erros_str'] = df_tickets['lista_erros'].apply(lambda x: ", ".join(x) if isinstance(x, list) and x else "-")
        df_tickets['eventos_str'] = df_tickets['lista_eventos'].apply(lambda x: ", ".join(x) if isinstance(x, list) and x else "-")

        # --- KPIs ---
        col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
        with col_kpi1:
            st.metric("Total de Tickets (Amostra)", df_tickets['id'].nunique())
        with col_kpi2:
            if 'recurso_nivel_2' in df_tickets.columns and not df_tickets['recurso_nivel_2'].empty:
                top_modulo = df_tickets['recurso_nivel_2'].mode()[0]
            else:
                top_modulo = "N/A"
            st.metric("Módulo Mais Crítico", top_modulo)
        with col_kpi3:
            # Lógica para achar o erro mais comum (achatando as listas)
            todos_erros = []
            for lista in df_tickets['lista_erros']:
                if isinstance(lista, list): todos_erros.extend(lista)
            
            if todos_erros:
                from collections import Counter
                top_erro = Counter(todos_erros).most_common(1)[0][0]
            else:
                top_erro = "Nenhum"
            st.metric("Erro Mais Comum", top_erro)

        st.divider()

        # --- 2. GRÁFICOS E FILTROS ---
        st.markdown("### 🔍 Distribuição Taxonômica")
        
        # ADICIONADO: Opções de Erro e Evento no dicionário
        opcoes_visao = {
            "Por Categoria de Sintoma": "sintoma_categoria",
            "Por Causa Raiz": "causa_categoria",
            "Por Módulo (Recurso N2)": "recurso_nivel_2",
            "Por Solução Aplicada": "solucao_categoria",
            "Por Código de Erro": "lista_erros",   # <--- NOVO
            "Por Evento eSocial": "lista_eventos"  # <--- NOVO
        }
        
        c_sel, c_graph = st.columns([1, 3])
        
        with c_sel:
            visao_selecionada = st.radio("Agrupar por:", list(opcoes_visao.keys()))
            coluna_analise = opcoes_visao[visao_selecionada]

        # LÓGICA DE PREPARAÇÃO DO GRÁFICO
        if coluna_analise in df_tickets.columns:
            
            # Se for Erro ou Evento (Listas), precisamos usar EXPLODE para contar individualmente
            if coluna_analise in ["lista_erros", "lista_eventos"]:
                df_exploded = df_tickets.explode(coluna_analise)
                # Remove nulos e strings vazias geradas pelo explode
                df_exploded = df_exploded[df_exploded[coluna_analise].notna() & (df_exploded[coluna_analise] != "")]
                df_chart = df_exploded[coluna_analise].value_counts().reset_index()
            else:
                # Lógica padrão para colunas simples (Sintoma, Causa, Modulo)
                df_chart = df_tickets[coluna_analise].value_counts().reset_index()

            df_chart.columns = ["Categoria", "Quantidade"]

            with c_graph:
                if not df_chart.empty:
                    chart = alt.Chart(df_chart).mark_bar(color="#FF4B4B", cornerRadiusEnd=4).encode(
                        x=alt.X('Quantidade', title=None), 
                        y=alt.Y('Categoria', sort='-x', title=None),
                        tooltip=['Categoria', 'Quantidade']
                    ).properties(height=300)
                    
                    text = chart.mark_text(align='left', baseline='middle', dx=3).encode(text='Quantidade')
                    st.altair_chart(chart + text, use_container_width=True)
                else:
                    st.info("Sem dados suficientes para gerar gráfico desta categoria.")
        
        # --- 3. DRILL DOWN (TABELA DETALHADA) ---
        st.markdown(f"### 🔬 Detalhar: {visao_selecionada}")
        
        col_drill1, col_drill2 = st.columns([1, 3])
        with col_drill1:
            cats = df_chart["Categoria"].tolist() if not df_chart.empty else []
            if cats:
                cat_foco = st.selectbox(f"Filtrar {visao_selecionada}:", cats)
            else:
                cat_foco = None

        with col_drill2:
            if cat_foco and coluna_analise in df_tickets.columns:
                
                # LÓGICA DE FILTRAGEM (Simples vs Lista)
                if coluna_analise in ["lista_erros", "lista_eventos"]:
                    # Filtra verificando se o item selecionado está DENTRO da lista daquela linha
                    # Ex: Se selecionei "Erro 106", traz todas as linhas onde "Erro 106" está na lista_erros
                    mask = df_tickets[coluna_analise].apply(lambda x: cat_foco in x if isinstance(x, list) else False)
                    df_filtro = df_tickets[mask]
                else:
                    # Filtro exato padrão
                    df_filtro = df_tickets[df_tickets[coluna_analise] == cat_foco]

                # 1. Conta IDs únicos para o texto
                st.write(f"**{df_filtro['id'].nunique()} Tickets encontrados**")
                
                # 2. Remove duplicatas baseadas no ID antes de exibir a tabela
                df_exibicao = df_filtro[["id", "recurso_nivel_3", "sintoma_detalhe", "erros_str", "eventos_str"]].drop_duplicates(subset=['id'])

                st.dataframe(
                    df_exibicao, 
                    use_container_width=True, hide_index=True,
                    column_config={
                        "id": st.column_config.TextColumn("ID", width="small"),
                        "recurso_nivel_3": st.column_config.TextColumn("Funcionalidade", width="medium"),
                        "sintoma_detalhe": st.column_config.TextColumn("Resumo do Problema", width="large"),
                        "erros_str": st.column_config.TextColumn("Códigos de Erro", width="medium"),
                        "eventos_str": st.column_config.TextColumn("Eventos eSocial", width="medium")
                    }
                )

        st.divider()

        # --- 4. FICHA TÉCNICA (DETALHES DO TICKET) ---
        st.markdown("### 🎫 Ficha Técnica do Ticket (Knowledge Graph)")
        
        col_search, col_card = st.columns([1, 2])

        with col_search:
            ticket_options = df_tickets["id"].tolist()
            # Formata para mostrar ID e Titulo no dropdown
            format_func = lambda x: f"{x} - {str(df_tickets[df_tickets['id']==x]['titulo'].values[0])[:30]}..."
            
            selected_id = st.selectbox("Selecione um Ticket:", ticket_options, format_func=format_func)
            
            if selected_id:
                t = df_tickets[df_tickets["id"] == selected_id].iloc[0]
                
                st.info(f"**Protocolo:** {t.get('protocolo', 'N/A')}")
                st.caption(f"Ingerido em: {t.get('data_ingestao', 'N/A')}")
                
                # Destaque visual para Erros e Eventos
                if t['erros_str'] != "-": 
                    st.error(f"🛑 Erros: {t['erros_str']}")
                if t['eventos_str'] != "-": 
                    st.warning(f"📅 Eventos: {t['eventos_str']}")

        with col_card:
            if selected_id:
                with st.container(border=True):
                    # Header Hierárquico
                    st.markdown(f"#### 📂 {t.get('recurso_nivel_1', 'Geral')} > {t.get('recurso_nivel_2', 'Geral')}")
                    st.caption(f"Funcionalidade Específica: **{t.get('recurso_nivel_3', 'Não classificado')}**")
                    
                    st.divider()
                    
                    # Problema
                    st.markdown(f"**🔴 SINTOMA: {t.get('sintoma_categoria', 'N/A')}**")
                    st.write(t.get('sintoma_detalhe', 'Sem detalhes.')) 
                    
                    st.divider()
                    
                    # Causa
                    st.markdown(f"**🟡 CAUSA: {t.get('causa_categoria', 'N/A')}**")
                    st.write(t.get('causa_detalhe', 'Causa não identificada.'))
                    
                    st.divider()
                    
                    # Solução (Tutorial)
                    st.markdown(f"**🟢 SOLUÇÃO: {t.get('solucao_categoria', 'N/A')}**")
                    # Renderiza passos se houver quebras de linha
                    sol_text = t.get('solucao_detalhe', '')
                    if sol_text:
                        for line in sol_text.split('\n'):
                            st.write(line)
                    else:
                        st.write("Sem solução registrada.")
            else:
                st.info("Selecione um ticket para ver os detalhes extraídos pela IA.")
