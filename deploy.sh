#!/bin/bash
# ==========================================================
# 知识库系统一键部署脚本
# 用法: bash deploy.sh
# 功能: 装 Ollama + 拉模型 + 建虚拟环境 + 装依赖 + 注册后台服务
# ==========================================================
set -e  # 出错立即停止

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/rag-env"
OLLAMA_MODEL="qwen2.5:7b"

# 你的 Ollama 是通过 1Panel 以 Docker 容器方式部署的(容器名: ollama,
# 端口映射 0.0.0.0:11434->11434/tcp)。脚本直接通过网络 API 判断服务可用性,
# 拉模型则通过 docker exec 进容器内执行,不依赖宿主机是否装了 ollama 命令。
OLLAMA_CONTAINER="${OLLAMA_CONTAINER:-ollama}"
OLLAMA_API="http://localhost:11434"

# ---------- 0. 禁止用 sudo 整体运行本脚本 ----------
if [ "$EUID" -eq 0 ] && [ -n "$SUDO_USER" ]; then
    echo "!! 检测到你在用 sudo 运行本脚本,请不要这样做。"
    echo "!! 直接运行: bash deploy.sh"
    echo "!! (脚本内部需要 root 权限的地方会自动弹出 sudo 密码提示)"
    exit 1
fi

echo "=================================================="
echo " 知识库系统部署开始"
echo " 项目目录: $PROJECT_DIR"
echo "=================================================="

# ---------- 1. 确认 Ollama 容器服务可用 ----------
echo ">> 检查 Ollama API ($OLLAMA_API) ..."
if curl -fsS --max-time 5 "$OLLAMA_API" > /dev/null 2>&1; then
    echo ">> Ollama 服务正常响应(容器: $OLLAMA_CONTAINER)。"
else
    echo "!! 无法连接到 $OLLAMA_API"
    echo "!! 请先在 1Panel 的「容器」页面确认 ollama 容器状态是「已启动」,"
    echo "!! 并且端口映射包含 11434,再重新运行本脚本。"
    exit 1
fi

# 用来在容器内执行 ollama 命令的小函数(自动尝试是否需要 sudo 调用 docker)
docker_ollama() {
    if docker exec "$OLLAMA_CONTAINER" ollama "$@" 2>/dev/null; then
        return 0
    else
        sudo docker exec "$OLLAMA_CONTAINER" ollama "$@"
    fi
}

# ---------- 2. 拉取模型(在容器内执行) ----------
echo ">> 检查模型 $OLLAMA_MODEL ..."
if docker_ollama list | grep -q "$OLLAMA_MODEL"; then
    echo ">> 模型 $OLLAMA_MODEL 已存在,跳过。"
else
    echo ">> 拉取模型 $OLLAMA_MODEL (可能需要几分钟)..."
    docker_ollama pull "$OLLAMA_MODEL"
fi

# ---------- 3. Python 虚拟环境 ----------
if [ ! -d "$VENV_DIR" ]; then
    echo ">> 创建 Python 虚拟环境..."
    python3 -m venv "$VENV_DIR"
else
    echo ">> 虚拟环境已存在,跳过创建。"
fi

PIP_INDEX="https://pypi.tuna.tsinghua.edu.cn/simple"

echo ">> 安装依赖（国内源）..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip --quiet -i "$PIP_INDEX"
pip install -r "$PROJECT_DIR/requirements.txt" --quiet -i "$PIP_INDEX"
deactivate

# ---------- 4. 建立必要目录并设置权限 ----------
mkdir -p "$PROJECT_DIR/docs" "$PROJECT_DIR/chroma_db" "$PROJECT_DIR/logs"
sudo chmod -R 777 "$PROJECT_DIR/docs"
echo ">> docs/ 目录权限已设为 777"

# ---------- 5. 若 docs/ 有文档则建索引 ----------
if [ -n "$(ls -A "$PROJECT_DIR/docs" 2>/dev/null)" ]; then
    echo ">> 检测到 docs/ 下有文档,正在建立索引..."
    source "$VENV_DIR/bin/activate"
    python "$PROJECT_DIR/scripts/build_index.py"
    deactivate
else
    echo ">> docs/ 目录为空,跳过建索引。请放入文档后手动运行:"
    echo "   source rag-env/bin/activate && python scripts/build_index.py"
fi

# ---------- 6. 注册 systemd 后台服务 ----------
echo ">> 正在注册 systemd 后台服务(需要 sudo 权限)..."
bash "$PROJECT_DIR/deploy/install_services.sh" "$PROJECT_DIR" "$VENV_DIR"

echo "=================================================="
echo " 部署完成!"
echo " 网页问答界面: http://<本机IP>:8501"
echo " 查看服务状态: sudo systemctl status aiask-app"
echo " 查看日志:     sudo journalctl -u aiask-app -f"
echo "=================================================="
