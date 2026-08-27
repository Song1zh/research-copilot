from openai import OpenAI
from core.config import settings


class LLMClient:
    def __init__(self, model: str | None = None):
        self.api_key = settings.CHAT_API_KEY
        self.base_url = settings.CHAT_BASE_URL
        self.model = model or settings.OPENAI_MODEL

        if not self.api_key:
            raise ValueError(
                "CHAT_API_KEY/OPENAI_API_KEY 未设置，请检查 .env 文件。"
            )

        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        self.client = OpenAI(**client_kwargs)

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        if not user_prompt.strip():
            raise ValueError("user_prompt 不能为空。")

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )

        content = response.choices[0].message.content
        if content is None:
            raise ValueError("模型返回内容为空。")

        return content
