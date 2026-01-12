# agents/llms.py
from dotenv import load_dotenv
import os

load_dotenv()
openrouter_api_key = os.getenv("OPENROUTER_API_KEY")  # OPENROUTER_API_KEY

openrouter_model = os.getenv(
    "OPENROUTER_MODEL",
    "nex-agi/deepseek-v3.1-nex-n1:free"
)

from langchain.chat_models import init_chat_model

coordinator_brain_gemini = init_chat_model(
    "gemini-2.5-flash",
    model_provider="google_genai"
)

import os
from langchain_openai import ChatOpenAI  # or from langchain.chat_models import ChatOpenAI

coordinator_brain_openrouter = ChatOpenAI(
    model="xiaomi/mimo-v2-flash:free",  # qwen/Qwen3-4B:free,  # nex-agi/deepseek-v3.1-nex-n1:free
    temperature=0,
    openai_api_key=os.getenv("OPR1"),  # Change environment variable name
    openai_api_base="https://openrouter.ai/api/v1",  # This is the key change
    max_tokens=2048,
    timeout=None,
    max_retries=2,
)
context_retrieval_brain_openrouter = ChatOpenAI(
    model="arcee-ai/trinity-mini:free",  # nvidia/nemotron-3-nano-30b-a3b:free
    temperature=0,
    openai_api_key=os.getenv("OPR2"),  # Change environment variable name
    openai_api_base="https://openrouter.ai/api/v1",  # This is the key change
    max_tokens=2048,
    timeout=None,
    max_retries=2,
)
fix_proposal_brain_openrouter = ChatOpenAI(
    model="xiaomi/mimo-v2-flash:free",  # meta-llama/llama-3.2-3b-instruct:free
    temperature=0,
    openai_api_key=os.getenv("OPR3"),  # Change environment variable name
    openai_api_base="https://openrouter.ai/api/v1",  # This is the key change
    max_tokens=2048,
    timeout=None,
    max_retries=2,
)
judge_brain_openrouter = ChatOpenAI(
    model="meta-llama/llama-3.2-3b-instruct:free",  # mistralai/devstral-2512:free
    temperature=0,
    openai_api_key=os.getenv("OPR5"),  # Change environment variable name
    openai_api_base="https://openrouter.ai/api/v1",  # This is the key change
    max_tokens=2048,
    timeout=None,
    max_retries=2,
)
fix_application_brain_openrouter = ChatOpenAI(
    model="mistralai/devstral-2512:free",
    temperature=0,
    api_key=os.getenv("OPR4"),  # ✅ MUST be api_key
    base_url="https://openrouter.ai/api/v1",  # ✅ new name
    max_tokens=2048,
    timeout=None,
    max_retries=2,
)
