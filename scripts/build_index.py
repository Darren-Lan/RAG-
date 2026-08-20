"""
建立 / 增量更新知识库索引

用法:
    python build_index.py            # 全量重建
    python build_index.py --update   # 增量更新(只处理新增/修改的文档,速度快)
"""

import argparse
import os
import sys

import chromadb
from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
)
from llama_index.vector_stores.chroma import ChromaVectorStore

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import get_settings, DOCS_DIR, CHROMA_DIR, COLLECTION_NAME


def tag_category(documents):
    """把文档所在的一级子文件夹名当作分类标签,存进 metadata,方便以后按分类过滤检索"""
    for doc in documents:
        file_path = doc.metadata.get("file_path", "")
        rel_path = os.path.relpath(file_path, DOCS_DIR)
        parts = rel_path.split(os.sep)
        category = parts[0] if len(parts) > 1 else "未分类"
        doc.metadata["category"] = category
    return documents


def build_index(rebuild: bool = True):
    get_settings()

    if not os.path.exists(DOCS_DIR) or not os.listdir(DOCS_DIR):
        print(f"警告: {DOCS_DIR} 是空的,请先把文档放进去再运行。")
        return

    chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)

    if rebuild:
        # 全量重建: 先删掉旧 collection
        try:
            chroma_client.delete_collection(COLLECTION_NAME)
            print("已清空旧索引,开始全量重建...")
        except Exception:
            pass

    chroma_collection = chroma_client.get_or_create_collection(COLLECTION_NAME)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    print(f"正在读取 {DOCS_DIR} 下的文档...")
    documents = SimpleDirectoryReader(
        DOCS_DIR,
        recursive=True,
        filename_as_id=True,
    ).load_data()

    if not documents:
        print("没有读取到任何文档,请检查 docs/ 目录和文件格式。")
        return

    documents = tag_category(documents)

    print(f"共读取 {len(documents)} 份文档,正在向量化并写入索引(可能需要几分钟)...")
    VectorStoreIndex.from_documents(documents, storage_context=storage_context)

    print(f"索引构建完成! 共 {chroma_collection.count()} 个向量片段。")
    print(f"索引存储位置: {CHROMA_DIR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="构建/更新知识库索引")
    parser.add_argument(
        "--update",
        action="store_true",
        help="增量更新模式(不清空已有索引,直接追加新文档)。注意: 重复运行可能导致同一文档被重复索引,建议定期用全量重建清理。",
    )
    args = parser.parse_args()

    build_index(rebuild=not args.update)
