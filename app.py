import streamlit as st
import requests
import uuid
import json

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Nasajon IA Suporte", 
    page_icon="🤖", 
    layout="wide" # Alterado para wide para facilitar a visualização de tabelas/logs
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

# --- DEFINIÇÃO DAS ABAS ---
tab_chat, tab_admin = st.tabs(["💬 Chat de Suporte", "⚙️ Gestão de Conhecimento (Ingestão)"])

# ---------------------------------------------------------
# ABA 1: CHAT (Seu código original adaptado)
# ---------------------------------------------------------
with tab_chat:
    # Mova aqui toda a sua lógica de visualização de mensagens, 
    # sidebar de contexto e o chat_input que você já usa.
    # [Omitido por brevidade, manter exatamente como seu original]
    st.info("Utilize a barra lateral para configurar o sistema de teste.")

# ---------------------------------------------------------
# ABA 2: INGESTÃO (A Nova Funcionalidade)
# ---------------------------------------------------------
with tab_admin:
    st.header("🚀 Ingestão de Base de Conhecimento")
    st.markdown("""
    Este módulo processa tickets crus, aplica visão computacional em prints, 
    classifica a utilidade e estrutura o conhecimento no **Neo4j GraphRAG**.
    """)

    uploaded_file = st.file_uploader("Arraste o arquivo 'tickets_for_llm.json'", type=['json'])

    if uploaded_file:
        try:
            raw_data = json.load(uploaded_file)
            st.info(f"📂 Arquivo carregado: {len(raw_data)} tickets detectados.")

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                clean_start = st.checkbox("Limpar banco antes de iniciar? (Reset Full)", value=False)
            
            if st.button("🔥 Iniciar Pipeline Completo"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                log_area = st.expander("📄 Logs de Processamento", expanded=True)

                # Aqui fazemos a chamada para a sua API Flask
                # Em vez de rodar o script local, chamamos a rota /ingest que você configurou
                with st.spinner("Processando..."):
                    try:
                        # Endpoint que você definiu no seu Blueprint bp_prod
                        INGEST_URL = "https://api.nasajon.app/nsj-ia-suporte/ingest" 
                        
                        response = requests.post(
                            INGEST_URL, 
                            json={"tickets": raw_data, "clear_db": clean_start},
                            timeout=600 # Timeout longo para processamento LLM
                        )
                        
                        if response.status_code == 200:
                            res = response.json()
                            st
