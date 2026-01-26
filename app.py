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
# ABA 2: INGESTÃO
# ---------------------------------------------------------
with tab_admin:
    st.header("🚀 Ingestão de Base de Conhecimento")
    uploaded_file = st.file_uploader("Upload tickets_for_llm.json", type=['json'])

    if uploaded_file:
        try:
            # Carrega o JSON completo para contar o total disponível
            raw_data = json.load(uploaded_file)
            total_disponivel = len(raw_data)
            st.info(f"📂 {total_disponivel} tickets detectados no arquivo.")
            
            # --- NOVO SELETOR DE QUANTIDADE ---
            st.markdown("### ⚙️ Configuração do Lote")
            col_limit, col_mode = st.columns(2)
            
            with col_limit:
                quantidade = st.number_input(
                    "Quantidade de tickets para processar:",
                    min_value=1,
                    max_value=total_disponivel,
                    value=min(100, total_disponivel), # Valor padrão sugerido
                    step=1,
                    help="Define quantos tickets do início da lista serão enviados para o pipeline."
                )
            
            with col_mode:
                clean_start = st.checkbox(
                    "Reset Full (Limpar Neo4j)", 
                    value=False,
                    help="Se marcado, apaga todos os nós do grafo antes de iniciar a nova ingestão."
                )

            if st.button("🔥 Iniciar Pipeline"):
                # Realiza o fatiamento (slice) da lista com base na escolha do usuário
                data_to_send = raw_data[:int(quantidade)]
                
                with st.spinner(f"Processando lote de {quantidade} tickets via Microserviço..."):
                    try:
                        # Endpoint que chama a função ingest_knowledge_base no seu Flask
                        INGEST_URL = "https://api.nasajon.app/nsj-ia-suporte/ingest"
                        
                        payload_ingesta = {
                            "tickets": data_to_send,
                            "clear_db": clean_start
                        }
                        
                        # Timeout alto é importante pois o VisionService e LLMs são lentos
                        response = requests.post(
                            INGEST_URL, 
                            json=payload_ingesta,
                            timeout=900 
                        )
                        
                        if response.status_code == 200:
                            res_json = response.json()
                            st.success(f"✅ Sucesso! {res_json.get('imported', 0)} tickets processados.")
                            st.balloons()
                        else:
                            st.error(f"❌ Erro no processamento: {response.text}")
                    
                    except requests.exceptions.Timeout:
                        st.warning("⚠️ O processamento está demorando mais que o esperado, mas pode continuar rodando no servidor.")
                    except Exception as e:
                        st.error(f"🔌 Falha de conexão: {str(e)}")

        except Exception as e:
            st.error(f"❌ Erro ao ler arquivo JSON: {e}")
