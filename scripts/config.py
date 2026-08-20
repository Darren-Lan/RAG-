"""
公共配置模块
所有脚本共用这里的设置,改配置只需要改这一个文件。
"""

import os

# ========== 网络配置 ==========
# HuggingFace 模型下载默认走 huggingface.co,国内访问经常很慢甚至连不上,
# 这里默认切换到国内镜像站,首次运行时下载 embedding 模型会快很多。
# 如果你的服务器本身能直连 huggingface.co,可以删掉这行或设成 ""。
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

# ========== 路径配置 ==========
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # data/aiask
DOCS_DIR = os.path.join(BASE_DIR, "docs")
CHROMA_DIR = os.path.join(BASE_DIR, "chroma_db")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

# ========== 向量库配置 ==========
COLLECTION_NAME = "my_knowledge_base"

# ========== 模型配置 ==========
# LLM: 通过 Ollama 本地跑,离线可用
# 如果 server 只有 CPU 且响应慢,把下面换成 "qwen2.5:3b"
OLLAMA_MODEL = "qwen2.5:3b"
OLLAMA_REQUEST_TIMEOUT = 120.0
# 你的 Ollama 跑在 1Panel 管理的 Docker 容器里,容器端口映射到了宿主机 11434,
# 所以这里直接用 localhost 就能访问,不需要额外配置。
OLLAMA_BASE_URL = "http://localhost:11434"

# Embedding: 中文场景用 bge,CPU 跑得动
EMBED_MODEL_NAME = "BAAI/bge-small-zh-v1.5"

# ========== 检索配置 ==========
SIMILARITY_TOP_K = 3  # 每次检索返回几个相关片段
CHUNK_SIZE = 512       # 文档切分大小(字符数)
CHUNK_OVERLAP = 50     # 切分片段之间的重叠,避免语义被切断


def get_settings():
    """初始化并返回全局 LlamaIndex 设置(LLM + Embedding)"""
    from llama_index.core import Settings
    from llama_index.llms.ollama import Ollama
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding

    Settings.llm = Ollama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        request_timeout=OLLAMA_REQUEST_TIMEOUT,
    )
    Settings.embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL_NAME)
    Settings.chunk_size = CHUNK_SIZE
    Settings.chunk_overlap = CHUNK_OVERLAP
    return Settings

