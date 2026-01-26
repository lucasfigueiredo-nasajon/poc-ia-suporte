import streamlit as st
import requests
import uuid

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Nasajon IA Suporte", 
    page_icon="🤖", 
    layout="centered"
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
    
    if metadata:
        agent = metadata.get("agent", "")
        if "receptionist" in agent: return "💁‍♀️"
        if "specialist" in agent: return "👷‍♂️"
        if "ticket" in agent: return "🎫"
        if "tier" in metadata and metadata["tier"] == 5: return "🚨"
        
    return "🤖"

###
def aba_ingestao(ingestion_service):
    st.header("🚀 Ingestão de Base de Conhecimento")
    uploaded_file = st.file_uploader("Upload tickets_for_llm.json", type=['json'])

    if uploaded_file:
        raw_data = json.load(uploaded_file)
        if st.button("Iniciar Processamento"):
            progress_bar = st.progress(0)
            status_text = st.empty()

            def update_ui(current, total):
                progress = current / total
                progress_bar.progress(progress)
                status_text.text(f"Processando ticket {current} de {total}...")

            result = ingestion_service.run_pipeline(raw_data, progress_callback=update_ui)
            st.success(f"Ingestão concluída! {result['imported']} tickets novos no Neo4j.")

# --- RENDERIZAÇÃO DO HISTÓRICO ---
for message in st.session_state.messages:
    avatar = get_avatar(message["role"], message.get("debug"))
    
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])
        
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
            # --- CRUCIAL: MONTAGEM DO HISTÓRICO COM 'AGENT' ---
            # Filtramos o session_state para criar um payload limpo,
            # mas incluímos o campo 'agent' se ele existir na mensagem anterior.
            # Isso ativa o Sticky Session no Backend.
            historico_para_enviar = []
            for msg in st.session_state.messages[:-1]: # Pega tudo menos a atual
                msg_payload = {
                    "role": msg["role"], 
                    "content": msg["content"]
                }
                # Se salvamos quem foi o agente na rodada anterior, mandamos de volta
                if "agent" in msg:
                    msg_payload["agent"] = msg["agent"]
                
                historico_para_enviar.append(msg_payload)
            # ---------------------------------------------------

            payload = {
                "conversation_id": st.session_state.conversation_id,
                "message": prompt,
                "history": historico_para_enviar,
                "context": {"sistema": sistema}
            }
            
            headers = {
                "Content-Type": "application/json",
                "X-Tenant-ID": tenant_id
            }
            
            response = requests.post(API_URL, json=payload, headers=headers, timeout=45)
            
            if response.status_code == 200:
                data = response.json()
                bot_response = data.get("response", "Não entendi.")
                metadata = data.get("metadata", {})
                
                # Extrai o nome do agente para salvar na sessão
                agent_used = metadata.get("agent") 

                message_placeholder.markdown(bot_response)
                
                # --- SALVAMENTO NO ESTADO ---
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": bot_response,
                    "debug": metadata,
                    "agent": agent_used # <--- Salvamos aqui para usar no loop acima na próxima vez
                })
                
                st.rerun()
                
            else:
                message_placeholder.error(f"❌ Erro {response.status_code}: {response.text}")
                
        except Exception as e:
            message_placeholder.error(f"🔌 Erro de conexão: {str(e)}")
