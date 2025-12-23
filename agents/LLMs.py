# agents/llms.py
from dotenv import load_dotenv
import os

load_dotenv()

# ===============================
# ENV VARIABLES
# ===============================
groq_api_key = os.getenv("GROQ_API_KEY")
openrouter_api_key = os.getenv("OPENROUTER_API_KEY") #OPENROUTER_API_KEY

model_name = os.getenv("MODEL_NAME")
llama_model = os.getenv("LLAMA_MODEL_NAME")
openrouter_model = os.getenv(
    "OPENROUTER_MODEL",
    "nex-agi/deepseek-v3.1-nex-n1:free"
)

# ===============================
# GROQ MODELS (FAST / FREE)
# ===============================
from langchain_groq import ChatGroq

model = ChatGroq(
    model=model_name,
    temperature=0,
    api_key=groq_api_key,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)

llama = ChatGroq(
    model=llama_model,
    temperature=0,
    api_key=groq_api_key,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)

# ===============================
# OPENROUTER MODELS (FREE MODELS)
# ===============================

# ===============================
# GEMINI (OPTIONAL)
# ===============================
from langchain.chat_models import init_chat_model

"""coordinator_brain = init_chat_model(
    "gemini-2.5-flash",
    model_provider="google_genai"
)"""


"""gemma = ChatOpenAI(
    model="gemma-7b",
    OPENROUTER_BASE_URL = openrouter.ai
    temperature=0,
    max_tokens=1024,
    client=None  # LangChain handles OpenRouter if OPENROUTER_API_KEY is set
)"""

"""coordinator_brain = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0,
    api_key=os.getenv("JB1"),
    max_tokens=None,
    timeout=None,
    max_retries=2,
)"""

import os
from langchain_openai import ChatOpenAI  # or from langchain.chat_models import ChatOpenAI

coordinator_brain_openrouter = ChatOpenAI(
    model="nex-agi/deepseek-v3.1-nex-n1:free",  # nex-agi/deepseek-v3.1-nex-n1:free
    temperature=0,
    openai_api_key=os.getenv("OPR1"),  # Change environment variable name
    openai_api_base="https://openrouter.ai/api/v1",  # This is the key change
    max_tokens=None,
    timeout=None,
    max_retries=2,
)
context_retrieval_brain_openrouter = ChatOpenAI(
    model="nvidia/nemotron-3-nano-30b-a3b:free",  # nvidia/nemotron-3-nano-30b-a3b:free
    temperature=0,
    openai_api_key=os.getenv("OPR2"),  # Change environment variable name
    openai_api_base="https://openrouter.ai/api/v1",  # This is the key change
    max_tokens=None,
    timeout=None,
    max_retries=2,
)
fix_proposal_brain_openrouter = ChatOpenAI(
    model="mistralai/devstral-2512:free",  # mistralai/devstral-2512:free
    temperature=0,
    openai_api_key=os.getenv("OPR3"),  # Change environment variable name
    openai_api_base="https://openrouter.ai/api/v1",  # This is the key change
    max_tokens=None,
    timeout=None,
    max_retries=2,
)
coordinator_brain_groq = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    api_key=os.getenv("JB2"),
    max_tokens=None,
    timeout=None,
    max_retries=2,
)

context_retrieval_brain_groq = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    api_key=os.getenv("JB2"),
    max_tokens=None,
    timeout=None,
    max_retries=2,
)

fix_proposal_brain_groq = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0,
    api_key=os.getenv("JB3"),
    max_tokens=None,
    timeout=None,
    max_retries=2,
)