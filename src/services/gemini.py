import asyncio

from google import genai
from google.genai import types

from src.config import Settings


class GeminiService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = None
        self._slots = asyncio.Semaphore(3)

    def start_chat(self):
        if not self.settings.gemini_api_key:
            raise ValueError("A IA está desativada. Configure GEMINI_API_KEY.")
        if self._client is None:
            self._client = genai.Client(
                api_key=self.settings.gemini_api_key,
                http_options=types.HttpOptions(timeout=self.settings.chat_request_timeout * 1000),
            )
        return self._client.aio.chats.create(
            model=self.settings.gemini_model,
            config=types.GenerateContentConfig(
                system_instruction="Você é o Vitola Bot, um bot de Discord criado por Victor de Souza. Responda em português.",
                max_output_tokens=2048,
                safety_settings=[
                    types.SafetySetting(
                        category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_LOW_AND_ABOVE"
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_LOW_AND_ABOVE"
                    ),
                ],
            ),
        )

    async def send(self, chat, prompt: str) -> str:
        async with asyncio.timeout(self.settings.chat_request_timeout):
            async with self._slots:
                response = await chat.send_message(prompt)
        return response.text or "Não consegui gerar uma resposta para essa mensagem."

    async def close(self):
        if self._client is not None:
            await self._client.aio.aclose()
            self._client.close()
            self._client = None
