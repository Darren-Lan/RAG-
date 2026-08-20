#!/bin/bash
# 把 .service/.timer 模板填充实际路径后安装到 systemd
# 用法: bash install_services.sh <PROJECT_DIR> <VENV_DIR>
set -e

PROJECT_DIR="$1"
VENV_DIR="$2"
CURRENT_USER="$(whoami)"
DEPLOY_DIR="$PROJECT_DIR/deploy"
SYSTEMD_DIR="/etc/systemd/system"

if [ -z "$PROJECT_DIR" ] || [ -z "$VENV_DIR" ]; then
    echo "用法: bash install_services.sh <PROJECT_DIR> <VENV_DIR>"
    exit 1
fi

render() {
    # $1 = 模板文件名  $2 = 输出文件名
    sed \
        -e "s|__PROJECT_DIR__|$PROJECT_DIR|g" \
        -e "s|__VENV_DIR__|$VENV_DIR|g" \
        -e "s|__USER__|$CURRENT_USER|g" \
        "$DEPLOY_DIR/$1" | sudo tee "$SYSTEMD_DIR/$2" > /dev/null
}

echo ">> 生成并安装 systemd 服务文件..."
render "aiask-app.service.template" "aiask-app.service"
render "aiask-cleanup.service.template" "aiask-cleanup.service"
render "aiask-cleanup.timer.template" "aiask-cleanup.timer"
render "aiask-watcher.service.template" "aiask-watcher.service"

echo ">> 重新加载 systemd 并启用服务..."
sudo systemctl daemon-reload
sudo systemctl enable --now aiask-app.service
sudo systemctl enable --now aiask-cleanup.timer
sudo systemctl enable --now aiask-watcher.service

echo ">> 完成。"
echo "   网页问答服务已在后台运行,开机自启,崩溃自动重启。"
echo "   文档监控服务已启动,放入新文件后自动建立索引。"
echo "   缓存清理已设为每天凌晨3点自动执行。"
