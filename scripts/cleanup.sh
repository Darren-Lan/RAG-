#!/bin/bash
# ==========================================================
# 自动缓存清理脚本
# 由 systemd timer 每天定时触发,也可以手动运行: bash cleanup.sh
#
# 清理内容:
#   1. logs/ 下超过 LOG_RETENTION_DAYS 天的问答日志
#   2. huggingface / transformers 下载缓存中的临时文件(.tmp / 未完成下载)
#   3. Python __pycache__ 垃圾文件
#   4. (可选) chroma_db 里的过期 WAL/临时文件 -- 默认关闭,防止误删索引
# ==========================================================
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOGS_DIR="$PROJECT_DIR/logs"
LOG_RETENTION_DAYS=30   # 问答日志保留天数,超过就删

CLEAN_LOG="$LOGS_DIR/cleanup_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$LOGS_DIR"

echo "==== 缓存清理开始 $(date) ====" | tee -a "$CLEAN_LOG"

# ---------- 1. 清理过期问答日志 ----------
echo ">> 清理超过 ${LOG_RETENTION_DAYS} 天的问答日志..." | tee -a "$CLEAN_LOG"
find "$LOGS_DIR" -name "*.jsonl" -mtime +"$LOG_RETENTION_DAYS" -print -delete >> "$CLEAN_LOG" 2>&1 || true

# ---------- 2. 清理 HuggingFace / Ollama 未完成下载的临时文件 ----------
echo ">> 清理 HuggingFace 缓存中的临时/不完整文件..." | tee -a "$CLEAN_LOG"
HF_CACHE="$HOME/.cache/huggingface"
if [ -d "$HF_CACHE" ]; then
    find "$HF_CACHE" -name "*.incomplete" -print -delete >> "$CLEAN_LOG" 2>&1 || true
    find "$HF_CACHE" -name "*.lock" -print -delete >> "$CLEAN_LOG" 2>&1 || true
fi

# ---------- 3. 清理 Python 编译缓存 ----------
echo ">> 清理 __pycache__ ..." | tee -a "$CLEAN_LOG"
find "$PROJECT_DIR" -type d -name "__pycache__" -not -path "*/rag-env/*" -exec rm -rf {} + 2>/dev/null || true

# ---------- 4. 清理旧的清理日志本身(避免 logs 无限膨胀) ----------
find "$LOGS_DIR" -name "cleanup_*.log" -mtime +"$LOG_RETENTION_DAYS" -delete 2>/dev/null || true

# ---------- 5. 报告当前磁盘占用 ----------
echo ">> 当前项目磁盘占用:" | tee -a "$CLEAN_LOG"
du -sh "$PROJECT_DIR"/{docs,chroma_db,logs,models} 2>/dev/null | tee -a "$CLEAN_LOG" || true

echo "==== 缓存清理完成 $(date) ====" | tee -a "$CLEAN_LOG"
