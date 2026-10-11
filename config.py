import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").strip().lower()  # ollama یا openai

# OpenAI settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

# Ollama settingsP
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b").strip()

DATABASE_PATH = os.getenv("DATABASE_PATH", "reports.db")
WEEK_START_DAY = os.getenv("WEEK_START_DAY", "MONDAY").upper()
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
