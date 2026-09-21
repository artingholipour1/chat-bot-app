from ollama import AsyncClient, ListResponse

class OllamaClient:
    def __init__(self, model: str = "gemma3:1b"):
        self.model = model
        self.client = AsyncClient()

    async def warm_up(self):
        """گرم‌کردن مدل و بارگذاری اولیه روی GPU"""
        await self.client.chat(
            model=self.model,
            messages=[{"role": "user", "content": "سلام"}],
            stream=False,
            keep_alive="1h",
            options={"num_gpu": 999}
        )

    async def stream_chat(self, messages: list[dict], options: dict = None):
        """ارسال تاریخچه و دریافت استریم توکن‌ها"""
        default_options = {
            "temperature": 0,
            "top_k": 1,
            "num_predict": 256,
            "num_ctx": 2048,
            "num_gpu": 999
        }
        if options:
            default_options.update(options)

        stream = await self.client.chat(
            model=self.model,
            messages=messages,
            stream=True,
            options=default_options,
            keep_alive="1h"
        )
        async for chunk in stream:
            yield chunk['message']['content']

    @staticmethod
    async def list_models() -> list[str]:
        """لیست مدل‌های نصب‌شده در Ollama"""
        client = AsyncClient()
        res: ListResponse = await client.list()
        return [m.model for m in res.models]
