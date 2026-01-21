import streamlit as st
import requests
import uuid

# Configuração da Página
st.set_page_config(page_title="Nasajon IA Suporte", page_icon="🤖", layout="wide")

# Título e Header
col1, col2 = st.columns([1, 5])
with col1:
    st.image("https://nasajon.com.br/wp-content/uploads/2020/12/logo-nasajon.png", width=100) # Logo opcional
with col2:
    st.title("Assistente de Suporte Inteligente - Nasajon")

st.markdown("---")

# --- CONFIGURAÇÃO (SECRETS) ---
# Tenta pegar dos secrets do Streamlit Cloud, senão usa default (para rodar local)
try:
    API_URL = st.secrets["API_URL"]
except:
    API_URL = "https://api.nasajon.app/nsj-ia-suporte/queries"

# Sidebar
with st.sidebar:
    st.header("⚙️ Contexto")
    # Se quiser esconder o Tenant ID também pode usar secrets
    tenant_id = st.text_input("Tenant ID", value="1")
    sistema = st.selectbox("Sistema", ["Persona SQL", "Scritta", "Contábil", "Geral"])
    
    if st.button("🗑️ Limpar Conversa"):
        st.session_state.messages = []
        st.session_state.conversation_id = str(uuid.uuid4())
        st.rerun()

# Estado da Sessão
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())

# Renderiza Chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "debug" in message:
            with st.expander("🛠️ Detalhes do Raciocínio (RAG)"):
                st.json(message["debug"])

# Input
if prompt := st.chat_input("Como posso te ajudar hoje?"):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("🧠 *Consultando base de conhecimento...*")
        
        try:
            payload = {
                "conversation_id": st.session_state.conversation_id,
                "message": prompt,
                "context": {"sistema": sistema}
            }
            
            headers = {
                "Content-Type": "application/json",
                "X-Tenant-ID": tenant_id
            }
            
            # Chama sua API de Produção
            response = requests.post(API_URL, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                bot_response = data.get("response", "Sem resposta.")
                metadata = data.get("metadata", {})
                
                message_placeholder.markdown(bot_response)
                
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": bot_response,
                    "debug": metadata
                })
            else:
                message_placeholder.error(f"Erro na API: {response.status_code}")
                
        except Exception as e:
            message_placeholder.error(f"Erro de conexão: {e}")
