import base64
import httpx
import logging
from openai import OpenAI
import os
from nasajon.dao.prompt_dao import PromptDAO

# Importa logger central se disponível, ou usa o padrão
logger = logging.getLogger(__name__)

DEFAULT_VISION_PROMPT = """
Você é um Analista de Suporte N3 especialista em ERPs (Persona, Scritta, Estoque).
Analise esta captura de tela.

Sua missão:
1. Transcreva EXATAMENTE qualquer mensagem de erro, código ou pop-up.
2. Identifique o contexto da tela (ex: "Tela de Cálculo de Folha", "Grid de Notas").
3. Se não houver erro, descreva apenas os dados técnicos visíveis.

Saída: Apenas a descrição técnica das evidências visuais. Sem preâmbulos.
"""

class VisionService:
    def __init__(self):
        # Tenta pegar da configuração centralizada primeiro
        try:
            from nasajon.settings import OPENAI_API_KEY
            api_key = OPENAI_API_KEY
        except ImportError:
            api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise ValueError("❌ ERRO CRÍTICO: 'OPENAI_API_KEY' não encontrada no ambiente.")
        
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o" 

    def _call_openai_vision(self, base64_image: str) -> str:
        try:
            dao = PromptDAO()
            db_prompt = dao.get_prompt('vision_analysis')
        except Exception:
            db_prompt = None
        
        # 2. Seleciona: Banco ou Fallback
        final_prompt = db_prompt if db_prompt else DEFAULT_VISION_PROMPT
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": final_prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                            },
                        ],
                    }
                ],
                max_tokens=400,
                temperature=0,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Erro na API OpenAI Vision: {e}")
            return f"[ERRO NA API VISION: {str(e)}]"

    def analyze_image(self, image_url: str) -> str:
        """Processa link público com tratamento de erro robusto"""
        try:
            # Timeout de 10s para não travar o pipeline de ingestão
            response = httpx.get(image_url, timeout=10.0, follow_redirects=True)
            
            if response.status_code != 200:
                return f"[AVISO: Imagem inacessível - Status {response.status_code}]"
            
            base64_image = base64.b64encode(response.content).decode('utf-8')
            return self._call_openai_vision(base64_image)
        except httpx.ConnectError:
            return "[ERRO: Falha de conexão ao baixar imagem]"
        except Exception as e:
            return f"[ERRO AO PROCESSAR URL DA IMAGEM: {str(e)}]"

    def analyze_stream(self, file_buffer) -> str:
        """Processa arquivo vindo do Upload do Streamlit"""
        try:
            bytes_data = file_buffer.getvalue()
            base64_image = base64.b64encode(bytes_data).decode('utf-8')
            return self._call_openai_vision(base64_image)
        except Exception as e:
            return f"[ERRO AO PROCESSAR UPLOAD: {str(e)}]"