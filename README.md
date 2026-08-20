# 小木呱知识库(本地离线 RAG)

一套完全跑在自己 Ubuntu server 上的私有知识库系统。基于 RAG(检索增强生成)架构:
文档先向量化存入本地向量数据库,提问时先检索最相关的片段,再交给本地 LLM 生成答案,
全程不依赖任何外部 API,数据不出服务器。

## 架构

```
你的 PDF/MD/docx 文档
        │
        ▼
   切分成小片段(Chunking)
        │
        ▼
  Embedding 模型转成向量(BGE, 本地跑, CPU可用)
        │
        ▼
   存入 Chroma 向量数据库(本地持久化)
        │
        │  ← 提问时
        ▼
   检索最相关的几个片段
        │
        ▼
   拼接成 Prompt,交给本地 LLM(Ollama + Qwen2.5)
        │
        ▼
       生成答案 + 标注来源
```

## 目录结构

```
data/aiask/
├── docs/              # 原始文档,把你的 PDF/MD/docx 放这里(可分子文件夹)
├── chroma_db/         # 向量数据库文件,自动生成,不要手动改
├── scripts/
│   ├── config.py       # 统一配置(模型名、路径、检索参数)
│   ├── build_index.py  # 建立/更新索引
│   ├── query.py         # 命令行问答
│   ├── app.py            # 网页问答界面(Streamlit)
│   └── cleanup.sh        # 自动缓存清理脚本
├── deploy/              # 后台服务部署相关文件
│   ├── aiask-app.service.template       # 网页服务 systemd 模板
│   ├── aiask-cleanup.service.template   # 清理任务 systemd 模板
│   ├── aiask-cleanup.timer.template     # 清理任务定时器模板
│   └── install_services.sh               # 生成并注册 systemd 服务
├── models/             # (可选)本地模型缓存目录
├── logs/                # 问答历史记录 + 清理日志,按日期存
├── deploy.sh            # 一键自动部署脚本(装环境+建索引+注册后台服务)
├── requirements.txt
├── .gitignore
└── README.md
```

> **重要说明**: 你的 Ollama 是通过 1Panel 以 **Docker 容器**方式部署的(容器名 `ollama`,
> 端口已映射到宿主机 `11434`)。`deploy.sh` 和 `scripts/config.py` 都已按这个实际情况配置好,
> 直接用 `http://localhost:11434` 访问,不需要在宿主机上另外安装 Ollama 命令行工具。
> 如果你的容器名不是 `ollama`,跑脚本前先 `export OLLAMA_CONTAINER=你的容器名`。

## 一键自动部署(推荐)

把文档放进 `docs/` 后,一条命令搞定环境安装 + 建索引 + 后台服务注册:

```bash
cd data/aiask
bash deploy.sh
```

这个脚本会自动:

1. **检查 Ollama 容器 API 是否可访问**(`http://localhost:11434`),不可用会直接报错提醒你
   去 1Panel 确认容器状态,而不会尝试重新安装 Ollama(容器化部署不需要,也不应该在宿主机
   上另装一份,那样反而会造成冲突)
2. 通过 `docker exec` 进容器检查/拉取模型
3. 创建 Python 虚拟环境并安装依赖
4. 如果 `docs/` 有文档,自动建立索引
5. 注册两个 systemd 后台服务(见下方说明),完成后网页问答界面自动在后台常驻运行

跑的时候会要求 `sudo` 权限(注册系统服务、以及 `docker exec` 权限不够时会用到)。

**如果你的 Ollama 容器名不是 `ollama`**,跑之前指定一下实际容器名:

```bash
export OLLAMA_CONTAINER=你的实际容器名
bash deploy.sh
```

> 如果 `docs/` 此时还是空的也没关系,脚本会跳过建索引这步,你之后放好文档手动跑一次
> `source rag-env/bin/activate && python scripts/build_index.py` 即可。

### 部署后是什么状态

| 服务名                | 作用                  | 触发方式                |
| --------------------- | --------------------- | ----------------------- |
| `aiask-app.service`   | 网页问答界面,常驻后台 | 开机自启,崩溃自动重启   |
| `aiask-cleanup.timer` | 自动缓存清理          | 每天凌晨3点自动执行一次 |

常用管理命令:

```bash
# 查看网页服务状态 / 日志
sudo systemctl status aiask-app
sudo journalctl -u aiask-app -f

# 重启网页服务(比如改了 config.py 之后)
sudo systemctl restart aiask-app

# 手动触发一次缓存清理(不用等到凌晨3点)
sudo systemctl start aiask-cleanup.service

# 查看清理任务下次执行时间
systemctl list-timers aiask-cleanup.timer

# 停止/禁用服务
sudo systemctl disable --now aiask-app
sudo systemctl disable --now aiask-cleanup.timer
```

部署完成后浏览器访问 `http://<你的server内网IP>:8501` 就能问答,不需要手动开终端跑脚本。

---

## 手动部署(如果不想用 deploy.sh)

### 1. 安装 Ollama(本地跑 LLM)

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:3b #稍微会快一些
```

> CPU 机器如果觉得 7b 响应慢,换成更轻量的模型:
> `ollama pull qwen2.5:3b`,然后把 `scripts/config.py` 里的 `OLLAMA_MODEL` 改成 `"qwen2.5:3b"`

### 2. 创建 Python 虚拟环境并装依赖

```bash
cd data/aiask
python3 -m venv rag-env
source rag-env/bin/activate
pip install -r requirements.txt
```

### 3. 放文档

把你的 PDF、Markdown、Word 等文件放进 `docs/` 文件夹,可以按主题建子文件夹,例如:

```
docs/
├── 工作/
├── 学习/
└── 参考资料/
```

子文件夹名会自动被记录为文档的"分类"标签(存在 metadata 里)。

### 4. 建立索引

```bash
cd scripts
python build_index.py
```

首次运行会读取 `docs/` 下所有文档、切分、向量化、存入 `chroma_db/`。文档量大的话这一步会
花几分钟到几十分钟,取决于文档数量和 CPU 性能。

### 5. 提问

**命令行方式**:

```bash
python query.py                 # 交互式
python query.py "你的问题"       # 单次提问
```

**网页界面方式(前台运行,关终端就停)**:

```bash
streamlit run app.py --server.address 0.0.0.0
```

想要后台常驻不受终端关闭影响,建议还是用上面的 `deploy.sh` 走 systemd 服务方式。

## 自动缓存清理机制

`scripts/cleanup.sh` 由 `aiask-cleanup.timer` 每天凌晨3点自动触发,清理内容:

1. **问答日志**:`logs/` 下超过 30 天的 `.jsonl` 记录(天数可在 `cleanup.sh` 顶部的
   `LOG_RETENTION_DAYS` 修改)
2. **HuggingFace 缓存残留**:下载中断留下的 `.incomplete` / `.lock` 临时文件
3. **Python 编译缓存**:各处 `__pycache__`

> 出于安全考虑,**`chroma_db/`(你的知识库索引)默认不会被自动清理**,避免误删导致
> 知识库丢失。如果确实想清理旧索引,手动删除 `chroma_db/` 后重跑 `build_index.py` 即可。

每次清理会在 `logs/` 下生成一份 `cleanup_*.log` 记录做了什么、清理前后磁盘占用多少,
这份清理日志本身也会在过期后被自动删除。

## 配置调整

所有可调参数都在 `scripts/config.py` 里:

| 参数               | 说明                     | 默认值                   |
| ------------------ | ------------------------ | ------------------------ |
| `OLLAMA_MODEL`     | 使用的本地 LLM           | `qwen2.5:3b              |
| `EMBED_MODEL_NAME` | Embedding 模型           | `BAAI/bge-small-zh-v1.5` |
| `SIMILARITY_TOP_K` | 每次检索返回几个相关片段 | `3`                      |
| `CHUNK_SIZE`       | 文档切分粒度(字符数)     | `512`                    |
| `CHUNK_OVERLAP`    | 切分片段间的重叠         | `50`                     |

**调优建议**:

- 答案不够准确/跑题 → 尝试调大 `SIMILARITY_TOP_K`(比如5),让模型看到更多上下文
- 响应速度太慢 → 换更小的 LLM(`qwen2.5:3b`),或减小 `SIMILARITY_TOP_K`
- 文档里有大段连续内容(比如长合同、书籍) → 适当调大 `CHUNK_SIZE`,避免语义被切碎

## 常见问题

**Q: PDF 是扫描件/图片,读不出内容怎么办?**
`SimpleDirectoryReader` 只能读取有文字层的 PDF。扫描件需要先做 OCR(可以用 `pytesseract`
或其他 OCR 工具处理成文字后再放入 `docs/`)。

**Q: 想清空重建索引?**
直接删除 `chroma_db/` 文件夹,重新运行 `python build_index.py` 即可(或者不删,直接跑
`build_index.py`,脚本默认会先清空旧 collection 再全量重建)。

**Q: 想用更好的模型效果,但又不想放弃离线?**
可以尝试更大参数量的模型如 `qwen2.5:14b`,但 CPU 推理速度会明显变慢,建议先测试能否接受。

**Q: 想把这套系统开放给团队用?**
把 `streamlit run app.py --server.address 0.0.0.0` 跑起来后,同网段的人都能通过
`http://<server IP>:8501` 访问。如果要公网访问,建议加一层 Nginx 反向代理 + 简单的
密码认证,避免知识库暴露在公网。

## 后续可扩展方向

- 增量索引(只处理新增/修改的文档,而不是每次全量重建)
- 定时任务(cron)自动扫描 `docs/` 新文件并更新索引
- 更换向量数据库为 Qdrant(适合规模变大后需要更强性能的场景)
- 接入 OCR,支持扫描版 PDF
- 加权限控制,支持多用户/多知识库隔离
