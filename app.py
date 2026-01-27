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

# --- ESTADO DA SESSÃO ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())

# --- CABEÇALHO ---
col1, col2 = st.columns([1, 5])
with col1:
    st.image("https://nasajon.com.br/wp-content/uploads/2020/12/logo-nasajon.png", width=80)
with col2:
    st.title("Nasajon IA - Suporte")
    st.caption("Painel de Atendimento e Ingestão de Conhecimento")

# --- SIDEBAR (RESTAURADA) ---
with st.sidebar:
    st.header("⚙️ Contexto do Cliente")
    tenant_id = st.text_input("Tenant ID", value="1")
    
    sistema = st.selectbox(
        "Sistema em Uso", 
        ["Persona SQL", "Contábil SQL", "Scritta SQL", "Estoque SQL", "Finanças SQL", "Meu RH"]
    )
    
    st.markdown("---")
    if st.button("🗑️ Nova Conversa (Limpar)"):
        st.session_state.messages = []
        st.session_state.conversation_id = str(uuid.uuid4())
        st.rerun()

# --- DEFINIÇÃO DAS ABAS ---
tab_chat, tab_admin = st.tabs(["💬 Chat de Suporte", "⚙️ Gestão de Conhecimento"])

# ---------------------------------------------------------
# ABA 2: INGESTÃO E VISUALIZAÇÃO (VERSÃO FINAL)
# ---------------------------------------------------------
with tab_admin:
    st.header("🚀 Ingestão de Base de Conhecimento")

    # --- SELEÇÃO DE FONTE ---
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

    # --- PROCESSAMENTO (SE HOUVER DADOS) ---
    if raw_data:
        total_disponivel = len(raw_data)
        st.success(f"📂 {total_disponivel} tickets carregados prontos para análise.")

        # --- NOVO: PRÉ-VISUALIZAÇÃO RICA ---
        with st.expander("🔍 Pré-visualizar Tickets (Clique para ver detalhes)", expanded=False):
            st.caption("Mostrando os 3 primeiros tickets do lote para validação:")
            
            # Função de renderização (inline para facilitar o copy-paste)
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

            # Renderiza apenas os 3 primeiros para não travar a tela
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
            
            # Container de Status Rico (Real-Time)
            status_container = st.status("🚀 Inicializando conexão...", expanded=True)
            progress_bar = status_container.progress(0)
            current_action = status_container.empty()
            
            try:
                # URL PROD
                INGEST_URL = "https://api.nasajon.app/nsj-ia-suporte/ingest-pipeline"
                
                payload_ingesta = {
                    "tickets": data_to_send,
                    "clear_db": clean_start
                }
                
                # Garante que tenant_id venha do sidebar (escopo global do script)
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
                    
                    if final_stats and 'stats' in final_stats:
                        st.divider()
                        st.markdown("### 📊 Relatório de Ingestão")
                        
                        s = final_stats['stats'] # Pega o dicionário novo do backend
                        
                        # Linha 1: Visão Geral do Funil
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric("1. Total Recebido", s['total_recebido'])
                        
                        with col2:
                            # Tickets que já existiam (Duplicados)
                            st.metric("2. Já Existiam", s['ja_existia'], 
                                     delta=f"{s['ja_existia']} ignorados", delta_color="off")
                        
                        with col3:
                            # Tickets Úteis (Passaram pela IA)
                            st.metric("3. Classificados Úteis", s['classificado_util'], 
                                     delta=f"{s['classificado_util']} aprovados")
                            
                        with col4:
                            # Tickets Efetivamente Salvos no Neo4j
                            st.metric("4. Gravados no Neo4j", s['salvo_sucesso'], 
                                     delta=f"+{s['salvo_sucesso']}", delta_color="normal")
                        
                        # Linha 2: Detalhe dos Descartados
                        st.caption("Detalhes dos tickets descartados ou com erro:")
                        d1, d2, d3 = st.columns(3)
                        d1.metric("Filtro Sistema (Não Persona)", s['filtrado_sistema'])
                        d2.metric("IA Rejeitou (Inútil/Incompleto)", s['classificado_inutil'])
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
