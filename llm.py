from typing import Protocol
import os, time
from dotenv import load_dotenv
load_dotenv()

class LLM(Protocol):
    def complete(self, system, messages):
        pass


_last_gemini_call = 0.0
_GEMINI_MIN_INTERVAL = 4.5  # free tier: 15 requests/minute per model

class GeminiLLM:
    def __init__(self, model = "gemini-3.5-flash-lite"):
        from google import genai
        self.client = genai.Client(api_key = os.getenv("GEMINI_API_KEY"))
        self.model = model

    def complete(self, system, messages):
        global _last_gemini_call
        wait = _GEMINI_MIN_INTERVAL - (time.time() - _last_gemini_call)
        if wait > 0:
            time.sleep(wait)
        _last_gemini_call = time.time()

        transcript = '\n'.join(f"{m['role']}: {m['content']}" for m in messages)
        response = self.client.models.generate_content(
            model=self.model,
            contents = transcript,
            config = {"system_instruction": system},
        )
        return response.text

class AnthropicLLM:
    def __init__(self, model="claude-sonnet-5"):
        from anthropic import Anthropic
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = model

    def complete(self, system, messages):
        response = self.client.messages.create(
            model = self.model,
            system = system,
            messages = messages,
            max_tokens = 1024
        )
        return response.content[0].text

def get_llm():
    if os.getenv("GEMINI_API_KEY"):
        return GeminiLLM()
    if os.getenv("ANTHROPIC_API_KEY"):
        return AnthropicLLM()
    raise RuntimeError("Set API Key for Model")