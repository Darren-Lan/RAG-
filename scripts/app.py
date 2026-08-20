"""
Streamlit 网页问答界面

用法:
    streamlit run app.py
    然后浏览器打开 http://<你的server IP>:8501
"""

import os
import sys
import subprocess

import streamlit as st
import chromadb
from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.chroma import ChromaVectorStore

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import get_settings, DOCS_DIR, CHROMA_DIR, COLLECTION_NAME, SIMILARITY_TOP_K

get_settings()

st.set_page_config(page_title="小木呱知识库", page_icon="📚", layout="centered")

st.title("📚 小木呱知识库")

@st.cache_resource
def load_index():
    chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
    chroma_collection = chroma_client.get_or_create_collection(COLLECTION_NAME)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    return VectorStoreIndex.from_vector_store(vector_store), chroma_collection

index, collection = load_index()

if collection.count() == 0:
    st.warning("索引是空的。请先在服务器上运行 `python build_index.py` 建立索引,然后刷新本页。")
    st.stop()

with st.sidebar:
    st.header("管理")
    st.caption(f"当前索引片段数: {collection.count()}")
    st.divider()
    
    if st.button("🔄 重建索引"):
        with st.spinner("正在重建索引..."):
            result = subprocess.run(
                [sys.executable, os.path.join(os.path.dirname(__file__), "build_index.py")],
                capture_output=True, text=True
            )
        if result.returncode == 0:
            st.success("索引重建完成！请刷新页面。")
        else:
            st.error(f"重建失败：{result.stderr}")
    
    if st.button("🗑️ 全量重建"):
        with st.spinner("正在全量重建..."):
            result = subprocess.run(
                [sys.executable, os.path.join(os.path.dirname(__file__), "build_index.py"), "--full"],
                capture_output=True, text=True
            )
        if result.returncode == 0:
            st.success("全量重建完成！请刷新页面。")
        else:
            st.error(f"重建失败：{result.stderr}")

if "history" not in st.session_state:
    st.session_state.history = []

question = st.chat_input("问点什么...")

for q, a, sources in st.session_state.history:
    with st.chat_message("user"):
        st.write(q)
    with st.chat_message("assistant"):
        st.write(a)
        with st.expander("参考来源"):
            for s in sources:
                st.write(f"[{s['category']}] {s['file']} (相似度: {s['score']})")

if question:
    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        with st.spinner("检索并生成答案中..."):
            query_engine = index.as_query_engine(similarity_top_k=SIMILARITY_TOP_K)
            response = query_engine.query(question)

            sources = []
            for node in response.source_nodes:
                sources.append({
                    "file": node.node.metadata.get("file_name", "未知来源"),
                    "category": node.node.metadata.get("category", "未分类"),
                    "score": round(node.score, 3) if node.score is not None else None,
                })

            st.write(str(response))
            with st.expander("参考来源"):
                for s in sources:
                    st.write(f"[{s['category']}] {s['file']} (相似度: {s['score']})")

    st.session_state.history.append((question, str(response), sources))
