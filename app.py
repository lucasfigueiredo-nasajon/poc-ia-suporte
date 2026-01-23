import streamlit as st
import requests
import uuid

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Nasajon IA Suporte", 
    page_icon="🤖", 
    layout="centered" # Layout centralizado foca melhor no chat
)

# --- CABEÇALHO ---
col1, col2 = st.columns([1, 5])
with col1:
    st.image("https://nasajon.com.br/wp-content/uploads/2020/12/logo-nasajon.png", width=80)
with col2:
    st.title("Suporte Inteligente")
    st.caption("Arquitetura Híbrida: Router + Especialista Persona")

st.markdown("---")

# --- CONFIGURAÇÃO DE CONEXÃO ---
try:
    API_URL = st.secrets["API_URL"]
except:
    API_URL = "https://api.nasajon.app/nsj-ia-suporte/queries"

# --- SIDEBAR (CONTEXTO) ---
with st.sidebar:
    st.header("⚙️ Contexto do Cliente")
    tenant_id = st.text_input("Tenant ID", value="1")
    
    # Lista sincronizada com o ReceptionistAgent
    sistema = st.selectbox(
        "Sistema em Uso", 
        ["Persona SQL", "Contábil SQL", "Scritta SQL", "Estoque SQL", "Finanças SQL", "Meu RH"]
    )
    
    st.markdown("---")
    if st.button("🗑️ Nova Conversa (Limpar)"):
        st.session_state.messages = []
        st.session_state.conversation_id = str(uuid.uuid4())
        st.rerun()

# --- ESTADO DA SESSÃO ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())

# --- FUNÇÃO AUXILIAR PARA ÍCONES ---
def get_avatar(role, metadata=None):
    if role == "user":
        return "👤"
    
    # Se for o bot, decide o ícone pelo agente que respondeu
    if metadata:
        agent = metadata.get("agent", "")
        if "receptionist" in agent: return "💁‍♀️" # Recepcionista
        if "specialist" in agent: return "👷‍♂️"   # Especialista Técnico
        if "ticket" in agent: return "🎫"       # Automação de Ticket
        if "tier" in metadata and metadata["tier"] == 5: return "🚨" # Erro
        
    return "🤖"

# --- RENDERIZAÇÃO DO HISTÓRICO ---
for message in st.session_state.messages:
    # Define o avatar baseado nos metadados da mensagem
    avatar = get_avatar(message["role"], message.get("debug"))
    
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])
        
        # Detalhes Técnicos (Tier e Agente)
        if "debug" in message:
            meta = message["debug"]
            agent_name = meta.get("agent", "Desconhecido").replace("_", " ").title()
            tier = meta.get("tier", "?")
            
            with st.expander(f"ℹ️ Bastidores ({agent_name} - Tier {tier})"):
                st.json(meta)

# --- INPUT DO USUÁRIO ---
if prompt := st.chat_input("Olá! Em que posso ajudar?"):
    
    # 1. Exibe msg do usuário
    st.chat_message("user", avatar="👤").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2. Processamento do Bot
    with st.chat_message("assistant", avatar="🤖"):
        message_placeholder = st.empty()
        message_placeholder.markdown("🧠 *Analisando solicitação...*")
        
        try:
            # Prepara histórico (Excluindo a msg atual para não duplicar no backend se ele já tratar isso)
            historico_para_enviar = st.session_state.messages[:-1]

            payload = {
                "conversation_id": st.session_state.conversation_id,
                "message": prompt,
                "history": historico_para_enviar,
                "context": {"sistema": sistema} # Envia o sistema selecionado como dica
            }
            
            headers = {
                "Content-Type": "application/json",
                "X-Tenant-ID": tenant_id
            }
            
            # Chamada API
            response = requests.post(API_URL, json=payload, headers=headers, timeout=45) # Timeout maior para o Especialista
            
            if response.status_code == 200:
                data = response.json()
                bot_response = data.get("response", "Não entendi.")
                metadata = data.get("metadata", {})
                
                # Atualiza UI com a resposta final
                message_placeholder.markdown(bot_response)
                
                # Salva no estado
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": bot_response,
                    "debug": metadata
                })
                
                # Força refresh para atualizar o ícone do bot (de 🤖 para 💁‍♀️ ou 👷‍♂️)
                st.rerun()
                
            else:
                message_placeholder.error(f"❌ Erro {response.status_code}: {response.text}")
                
        except Exception as e:
            message_placeholder.error(f"🔌 Erro de conexão: {str(e)}")
