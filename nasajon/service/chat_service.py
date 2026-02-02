import logging
import random
from typing import Dict, Any, Optional
from langchain_core.messages import AIMessage, HumanMessage

from nasajon.dao.chat_dao import ChatDAO
from nasajon.service.receptionist_agent import ReceptionistAgent
from nasajon.service.persona_specialist_agent import PersonaSpecialistAgent

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self, dao: ChatDAO):
        self.dao = dao
        
        # 1. Instancia a Recepcionista (Router Inteligente)
        self.receptionist = ReceptionistAgent()
        
        # 2. Instancia o Especialista (Persona/Neo4j)
        self.persona_specialist = PersonaSpecialistAgent()

    def _generate_escalation_ticket(self, resumo_curto: str, detalhes_usuario: str = "") -> str:
        """
        Gera um ticket padronizado N3 (Simulação).
        """
        protocolo = random.randint(500000, 999999)
        
        mensagem = (
            f"Compreendo. Para esse caso, vou transferir para nossa equipe de especialistas humanos.\n\n"
            f"🎫 **Ticket Aberto: #{protocolo}**\n"
            f"📌 **Motivo:** {resumo_curto}\n"
        )
        
        if detalhes_usuario:
            mensagem += f"📝 **Relato:** \"{detalhes_usuario}\"\n"
            
        mensagem += "\nUm analista humano entrará em contato em até 2 horas."
        return mensagem

    def _run_persona_specialist(self, texto_usuario: str, historico_msgs: list, contexto_cliente: dict, tenant: int) -> Dict[str, Any]:
        """
        Método encapsulado para rodar o especialista.
        Usado tanto pelo Router (primeira vez) quanto pelo Sticky Session (vezes seguintes).
        """
        logger.info(f"🚀 [ESPECIALISTA] Executando lógica do Persona Specialist...")
        print(f"🚀 [DEBUG] Iniciando Persona Specialist para: '{texto_usuario}'", flush=True)


        # Prepara histórico LangChain (Janela de contexto segura)
        chat_history = []
        for msg in historico_msgs[-10:]: # Aumentei levemente para 10 para melhor contexto
            if msg.get('role') == 'user': 
                chat_history.append(HumanMessage(content=msg.get('content', '')))
            else: 
                chat_history.append(AIMessage(content=msg.get('content', '')))

        # Input limpo para o Agente (sem prefixos desnecessários)
        input_ctx = texto_usuario
        
        try:
            # O agente agora sabe lidar com o novo Schema do Neo4j
            resposta_final = self.persona_specialist.run(input_ctx, chat_history)
            
            # Análise de Tier (Lógica de Negócio - Atualizada)
            tier = 3 if "N3" in resposta_final or "protocolo" in resposta_final else 1
            
            # Melhora na detecção de falha de resposta
            if "não encontrei" in resposta_final.lower() or "não consegui" in resposta_final.lower(): 
                tier = 4
            
            self.dao.insert_interaction_log(tenant, contexto_cliente.get('email'), texto_usuario, tier, resposta_final, {})
            
            # --- PONTO CHAVE: MANTÉM O BASTÃO COM O ESPECIALISTA ---
            return {
                "response": resposta_final, 
                "metadata": {"tier": tier, "agent": "persona_specialist"}
            }
            
        except Exception as e:
            logger.error(f"Erro Crítico no Especialista: {e}")
            resp_erro = self._generate_escalation_ticket("Erro Técnico Interno na IA", str(e))
            self.dao.insert_interaction_log(tenant, contexto_cliente.get('email'), texto_usuario, 5, resp_erro, {"error": str(e)})
            
            # Em caso de erro, devolve o bastão para a recepcionista ("reset")
            return {"response": resp_erro, "metadata": {"tier": 5, "agent": "receptionist"}}

    def handle_query(self, id_conversa: str, contexto_cliente: dict, texto_usuario: str, tenant: int, historico_msgs: list, **kwargs) -> Dict[str, Any]:
        
        logger.info(f"📨 [CHAT] Nova mensagem: {texto_usuario}")

        # =========================================================================
        # 1. IDENTIFICAÇÃO DE SESSÃO ADESIVA (STICKY SESSION)
        # =========================================================================
        active_agent = "receptionist" # Padrão
        
        if historico_msgs:
            last_msg = historico_msgs[-1]
            # O front manda quem respondeu a última vez através do campo 'agent'
            if "agent" in last_msg and last_msg["agent"]:
                active_agent = last_msg["agent"]

        logger.info(f"🆔 [FLOW] Agente Ativo Anterior: {active_agent}")

        # 2. VERIFICAÇÃO DE SAÍDA (Obrigatoriedade)
        # Permite que o usuário quebre o loop do especialista
        termos_saida = ["sair", "voltar", "menu", "cancelar", "outro assunto", "tchau", "obrigado"]
        if any(term in texto_usuario.lower() for term in termos_saida):
            logger.info("👋 Usuário pediu para sair/resetar fluxo.")
            active_agent = "receptionist" # Força reset para a triagem

        # =========================================================================
        # ROTA A: FLUXO DIRETO (Via Sticky Session)
        # =========================================================================
        if active_agent == "persona_specialist":
            # Pula a recepcionista e vai direto para o técnico
            return self._run_persona_specialist(texto_usuario, historico_msgs, contexto_cliente, tenant)

        # =========================================================================
        # ROTA B: FLUXO PADRÃO (Via Recepcionista/Router)
        # =========================================================================
        
        # Prepara contexto para o Router (Amnésia)
        history_context = ""
        if historico_msgs:
            last_msgs = historico_msgs[-3:] 
            for m in last_msgs:
                role = "BOT" if m['role'] == 'assistant' else "USER"
                content = m.get('content', '')
                history_context += f"{role}: {content}\n"
        
        # Chama a Recepcionista
        decisao = self.receptionist.analyze_intent(texto_usuario, history_context)
        categoria = decisao.get('categoria')
        produto_detectado = decisao.get('produto_detectado')
        
        logger.info(f"🚦 [ROUTER] Decisão: {categoria} (Prod: {produto_detectado})")

        # CENA 1: SOLICITAÇÃO DE HUMANO
        if categoria == "SOLICITAR_ATENDENTE":
            resp = self._generate_escalation_ticket("Solicitação explícita de atendente", texto_usuario)
            self.dao.insert_interaction_log(tenant, contexto_cliente.get('email'), texto_usuario, 3, resp, {"router": categoria})
            # Devolve bastão para receptionist (reseta fluxo)
            return {"response": resp, "metadata": {"tier": 3, "agent": "receptionist"}}

        # CENA 2: RESPOSTA IMEDIATA (Saudação)
        if decisao.get("resposta_imediata"):
            resp = decisao["resposta_imediata"]
            self.dao.insert_interaction_log(tenant, contexto_cliente.get('email'), texto_usuario, 0, resp, {"router": categoria})
            return {"response": resp, "metadata": {"tier": 0, "agent": "receptionist"}}

        # CENA 3: OUTROS PRODUTOS (Ticket)
        if categoria == "SUPORTE_OUTROS_PRODUTOS":
            produto = produto_detectado if produto_detectado else "Produto Nasajon"
            resp = self._generate_escalation_ticket(f"Dúvida técnica sobre {produto}", texto_usuario)
            self.dao.insert_interaction_log(tenant, contexto_cliente.get('email'), texto_usuario, 3, resp, {"router": categoria})
            return {"response": resp, "metadata": {"tier": 3, "agent": "receptionist"}}

        # CENA 4: PERSONA (Inicia o fluxo do Especialista)
        if categoria == "SUPORTE_PERSONA":
            # Ao chamar aqui, o método retorna 'agent': 'persona_specialist' no metadata.
            # Isso ativa o Sticky Session para a próxima mensagem.
            return self._run_persona_specialist(texto_usuario, historico_msgs, contexto_cliente, tenant)
        
        # Fallback
        return {"response": "Não entendi sua solicitação. Poderia reformular?", "metadata": {"tier": 0, "agent": "receptionist"}}

    def close(self):
        pass