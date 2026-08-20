"""
命令行问答工具

用法:
    python query.py                    # 进入交互式问答
    python query.py "你的问题"          # 单次提问
"""

import os
import sys
import json
import datetime

import chromadb
from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.chroma import ChromaVectorStore

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import get_settings, CHROMA_DIR, LOGS_DIR, COLLECTION_NAME, SIMILARITY_TOP_K


def load_index():
    get_settings()
    chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)

    try:
        chroma_collection = chroma_client.get_collection(COLLECTION_NAME)
    except Exception:
        print("找不到索引,请先运行 python build_index.py 建立知识库索引。")
        sys.exit(1)

    if chroma_collection.count() == 0:
        print("索引是空的,请先运行 python build_index.py 建立知识库索引。")
        sys.exit(1)

    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    index = VectorStoreIndex.from_vector_store(vector_store)
    return index


def log_qa(question, answer, sources):
    """把每次问答记录写入 logs/,方便日后回顾"""
    os.makedirs(LOGS_DIR, exist_ok=True)
    log_file = os.path.join(LOGS_DIR, f"{datetime.date.today().isoformat()}.jsonl")
    entry = {
        "time": datetime.datetime.now().isoformat(),
        "question": question,
        "answer": str(answer),
        "sources": sources,
    }
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def ask(index, question: str):
    query_engine = index.as_query_engine(similarity_top_k=SIMILARITY_TOP_K)
    response = query_engine.query(question)

    sources = []
    print("\n答案:", response)
    print("\n--- 参考来源 ---")
    for node in response.source_nodes:
        fname = node.node.metadata.get("file_name", "未知来源")
        category = node.node.metadata.get("category", "未分类")
        score = round(node.score, 3) if node.score is not None else None
        print(f"[{category}] {fname}  (相似度: {score})")
        sources.append({"file": fname, "category": category, "score": score})

    log_qa(question, response, sources)
    return response


if __name__ == "__main__":
    index = load_index()

    if len(sys.argv) > 1:
        # 单次提问模式: python query.py "问题"
        question = " ".join(sys.argv[1:])
        ask(index, question)
    else:
        # 交互式模式
        print("知识库已就绪,输入问题开始提问(输入 exit 退出)\n")
        while True:
            q = input("你的问题: ").strip()
            if q.lower() in ("exit", "quit", "q"):
                break
            if not q:
                continue
            ask(index, q)
