import os
from dotenv import load_dotenv
from pathlib import Path
from pydantic.v1 import BaseSettings


def _default_rerank_base_url() -> str:
    base_url = os.getenv(
        "OPENAI_BASE_URL",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    return base_url.replace("/compatible-mode/v1", "/compatible-api/v1")

# 把环境变量从代码中分离,用于加载 .env 环境变量
load_dotenv()

class Settings:
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_NAME: str = os.getenv("APP_NAME", "ai-app-engineer-roadmap")

    OPENAI_API_KEY: str | None = os.getenv("DASHSCOPE_API_KEY")
    OPENAI_BASE_URL: str | None = os.getenv("OPENAI_BASE_URL")
    CHAT_API_KEY: str | None = (
        os.getenv("CHAT_API_KEY")
        or os.getenv("DASHSCOPE_API_KEY")
        or os.getenv("MOONSHOT_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    )
    CHAT_BASE_URL: str | None = os.getenv("CHAT_BASE_URL") or os.getenv(
        "OPENAI_BASE_URL"
    )
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "qwen3.7-plus-2026-05-26")
    GROUNDEDNESS_MODEL: str = os.getenv(
        "GROUNDEDNESS_MODEL", "qwen3.7-plus-2026-05-26"
    )
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "local_hash")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-v4")
    EMBEDDING_DIMENSIONS: int = int(os.getenv("EMBEDDING_DIMENSIONS", "1024"))
    EMBEDDING_BATCH_SIZE: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "10"))
    LOCAL_HASH_DIMENSIONS: int = int(os.getenv("LOCAL_HASH_DIMENSIONS", "64"))
    RERANKER_PROVIDER: str = os.getenv("RERANKER_PROVIDER", "dashscope")
    RERANK_MODEL: str = os.getenv("RERANK_MODEL", "qwen3-rerank")
    RERANK_BASE_URL: str = os.getenv(
        "DASHSCOPE_RERANK_BASE_URL", _default_rerank_base_url()
    )
    RERANK_CANDIDATE_K: int = int(os.getenv("RERANK_CANDIDATE_K", "30"))
    RERANK_TIMEOUT_SECONDS: float = float(
        os.getenv("RERANK_TIMEOUT_SECONDS", "30")
    )
    RERANK_MAX_DOCUMENTS: int = int(os.getenv("RERANK_MAX_DOCUMENTS", "500"))
    RERANK_MAX_DOCUMENT_CHARS: int = int(
        os.getenv("RERANK_MAX_DOCUMENT_CHARS", "8000")
    )
    RERANK_INSTRUCT: str = os.getenv(
        "RERANK_INSTRUCT",
        "Given a scientific literature question, retrieve passages that directly "
        "answer the question with methods, conditions, results, or conclusions.",
    )
    KG_PROVIDER: str = os.getenv("KG_PROVIDER", "neo4j")


settings = Settings()

# 用于统一项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent

CHROMA_DB_PATH = PROJECT_ROOT  / "chroma_db"
UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DB_PATH.mkdir(parents=True, exist_ok=True)

APP_DATA_DIR = PROJECT_ROOT / "app_data"
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_DB_PATH = APP_DATA_DIR / "history.db"

LITERATURE_CORPUS_DIR = PROJECT_ROOT / "data" / "literature_corpus"
LITERATURE_CHROMA_COLLECTION = os.getenv(
    "LITERATURE_CHROMA_COLLECTION",
    "energetic_materials_literature",
)

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

