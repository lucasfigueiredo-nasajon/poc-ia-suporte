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
# ABA 1: CHAT FUNCIONAL
# ---------------------------------------------------------
with tab_chat:
    # Função auxiliar para ícones
    def get_avatar(role, metadata=None):
        if role == "user": return "👤"
        if metadata:
            agent = metadata.get("agent", "")
            if "receptionist" in agent: return "💁‍♀️"
            if "specialist" in agent: return "👷‍♂️"
            if "ticket" in agent: return "🎫"
        return "🤖"

    # RENDERIZAÇÃO DO HISTÓRICO
    for message in st.session_state.messages:
        avatar = get_avatar(message["role"], message.get("debug"))
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])
            if "debug" in message:
                with st.expander("ℹ️ Bastidores"):
                    st.json(message["debug"])

    # INPUT DO USUÁRIO
    if prompt := st.chat_input("Olá! Em que posso ajudar?"):
        st.chat_message("user", avatar="👤").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant", avatar="🤖"):
            message_placeholder = st.empty()
            message_placeholder.markdown("🧠 *Analisando solicitação...*")
            
            try:
                # Recuperar API_URL dos secrets ou padrão
                try:
                    API_URL = st.secrets["API_URL"]
                except:
                    API_URL = "https://api.nasajon.app/nsj-ia-suporte/queries"

                # Montagem do histórico para o backend
                historico_para_enviar = []
                for msg in st.session_state.messages[:-1]:
                    msg_payload = {"role": msg["role"], "content": msg["content"]}
                    if "agent" in msg: msg_payload["agent"] = msg["agent"]
                    historico_para_enviar.append(msg_payload)

                payload = {
                    "conversation_id": st.session_state.conversation_id,
                    "message": prompt,
                    "history": historico_para_enviar,
                    "context": {"sistema": sistema}
                }
                
                headers = {"Content-Type": "application/json", "X-Tenant-ID": tenant_id}
                
                response = requests.post(API_URL, json=payload, headers=headers, timeout=45)
                
                if response.status_code == 200:
                    data = response.json()
                    bot_response = data.get("response", "Não entendi.")
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
                    message_placeholder.error(f"❌ Erro {response.status_code}")
            except Exception as e:
                message_placeholder.error(f"🔌 Erro: {str(e)}")
# ---------------------------------------------------------
# ABA 2: INGESTÃO (AJUSTADA PARA PIPELINE PROFISSIONAL)
# ---------------------------------------------------------
with tab_admin:
    st.header("🚀 Ingestão de Base de Conhecimento")
    uploaded_file = st.file_uploader("Upload tickets_for_llm.json", type=['json'])

    if uploaded_file:
        try:
            raw_data = json.load(uploaded_file)
            total_disponivel = len(raw_data)
            st.info(f"📂 {total_disponivel} tickets detectados no arquivo.")

            st.markdown("### ⚙️ Configuração do Lote")
            col_limit, col_mode = st.columns(2)
            
            with col_limit:
                quantidade = st.number_input(
                    "Quantidade de tickets para processar:",
                    min_value=1,
                    max_value=total_disponivel,
                    value=min(100, total_disponivel),
                    step=1
                )
            
            with col_mode:
                clean_start = st.checkbox(
                    "Reset Full (Limpar Neo4j)", 
                    value=False,
                    help="⚠️ Se marcado, apaga TODO o banco antes de iniciar."
                )

            if st.button("🔥 Iniciar Pipeline IA"):
                data_to_send = raw_data[:int(quantidade)]
                
                # --- INÍCIO DA INTERFACE RICA ---
                # Cria um container expansível que mostra o log ao vivo
                status_container = st.status("🚀 Inicializando conexão...", expanded=True)
                progress_bar = status_container.progress(0)
                
                # Placeholder para mostrar a ação atual (ex: "Analisando Imagem...")
                current_action = status_container.empty()
                
                try:
                    INGEST_URL = "https://api.nasajon.app/nsj-ia-suporte/ingest-pipeline"
                    
                    payload_ingesta = {
                        "tickets": data_to_send,
                        "clear_db": clean_start
                    }
                    
                    headers = {"Content-Type": "application/json", "X-Tenant-ID": tenant_id}
                    
                    # stream=True é fundamental para receber os eventos um a um
                    response = requests.post(
                        INGEST_URL, 
                        json=payload_ingesta,
                        headers=headers,
                        timeout=900,
                        stream=True 
                    )
                    
                    final_stats = None
                    
                    if response.status_code == 200:
                        # Itera sobre cada linha de JSON enviada pelo Backend
                        for line in response.iter_lines():
                            if line:
                                try:
                                    event = json.loads(line.decode('utf-8'))
                                    step = event.get('step')
                                    msg = event.get('msg', '')
                                    
                                    # 1. Mensagens de Inicialização
                                    if step == 'init':
                                        status_container.write(f"ℹ️ {msg}")
                                    
                                    # 2. Barra de Progresso (Ticket a Ticket)
                                    elif step == 'progress':
                                        curr = event.get('current', 0)
                                        total = event.get('total', 1)
                                        # Atualiza a barra e o título da etapa
                                        progress_bar.progress(curr / total)
                                        current_action.markdown(f"**{msg}**")
                                    
                                    # 3. Logs Detalhados (Visão, Classificação, Grafo)
                                    elif step == 'log':
                                        # Escreve dentro do container (histórico)
                                        status_container.markdown(f"`{msg}`")
                                    
                                    # 4. Erros
                                    elif step == 'error':
                                        status_container.error(msg)
                                    
                                    # 5. Finalização
                                    elif step == 'final':
                                        final_stats = event
                                        
                                except json.JSONDecodeError:
                                    continue

                        # Atualiza o status final da caixa
                        status_container.update(label="✅ Processamento Concluído!", state="complete", expanded=False)
                        
                        # Exibe Métricas Finais
                        if final_stats:
                            imported = final_stats.get('imported', 0)
                            skipped = final_stats.get('skipped', 0)

                            st.divider()
                            st.markdown("### 📊 Resultado Final")
                            m_col1, m_col2, m_col3 = st.columns(3)
                            m_col1.metric("Enviados", len(data_to_send))
                            m_col2.metric("Novos Inseridos", imported, delta=f"+{imported}")
                            m_col3.metric("Pulados (Filtro/Duplicado)", skipped, delta=f"-{skipped}", delta_color="off")

                            if imported > 0:
                                st.balloons()
                            elif imported == 0 and skipped > 0:
                                st.warning("Nenhum dado novo inserido (todos já existiam ou foram filtrados).")
                                
                    else:
                        status_container.update(label="❌ Erro na API", state="error")
                        st.error(f"Erro HTTP {response.status_code}: {response.text}")
                        
                except Exception as e:
                    status_container.update(label="🔌 Erro de Conexão", state="error")
                    st.error(f"Detalhes: {str(e)}")

        except Exception as e:
            st.error(f"❌ Erro ao ler arquivo JSON: {e}")
