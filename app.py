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
            raw_data = json.load(uploaded_file)
            st.info(f"📂 {len(raw_data)} tickets detectados.")
            
            if st.button("🔥 Iniciar Pipeline"):
                # O processamento agora chama a rota /ingest via API
                with st.spinner("Processando via Microserviço..."):
                    INGEST_URL = "https://api.nasajon.app/nsj-ia-suporte/ingest"
                    response = requests.post(INGEST_URL, json={"tickets": raw_data})
                    if response.status_code == 200:
                        st.success("Ingestão concluída!")
                    else:
                        st.error(f"Erro: {response.text}")
        except Exception as e:
            st.error(f"Erro ao ler arquivo: {e}")
