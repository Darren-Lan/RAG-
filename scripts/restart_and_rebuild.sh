#!/bin/bash

# 1. 激活虚拟环境并执行重建索引脚本
source /data/aiask/rag-env/bin/activate
echo "正在重建索引..."
python3 /data/aiask/scripts/build_index.py

# 2. 退出虚拟环境
deactivate

# 3. 重启 AI 服务
echo "正在重启服务..."
sudo systemctl restart aiask-app

echo "✅ 全部完成！请强制刷新浏览器 (Ctrl+F5)"
sleep 3
