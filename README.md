# 雪乃 —— 本地文件与记忆助理 Agent

一个运行在本地的电脑助理 Agent。具备**跨会话长期记忆**与**受控的文件操作能力**，而不是一个只能聊天的 Chatbot。

**技术栈**：Python · LangChain 1.3 · LangGraph · ChromaDB · BAAI/bge-small-zh-v1.5 · DeepSeek API

---

## 为什么做这个项目

最初写过一个功能很杂的版本（情绪系统、好感度数值、人格阶段切换……）。做到一半发现：那些功能演示起来热闹，但既不是真实需求，也让系统变得难以调试——情绪数值写错了，你甚至很难发现。

于是重写时做了取舍：

| 保留 | 砍掉 | 理由 |
|---|---|---|
| 长期记忆（向量检索） | 情绪系统 | 记忆是刚需——一个记不住事的助理没有价值；情绪数值是"表演性"功能 |
| 文件读写工具 | 好感度/人格阶段 | 能操作文件才叫助理，否则只是聊天 |
| 路径安全校验 | 多角色切换 | 安全边界是工程问题，角色切换是产品问题 |

**这个取舍本身就是设计的一部分：知道什么不该做。**

---

## 功能

### 1. 长期记忆（RAG）

- 用 **ChromaDB + BGE 中文向量模型** 存储概念记忆，本地运行，无需外部服务
- 检索采用**三要素加权重排**（参考 Stanford Generative Agents 的记忆流思路）：

  | 维度 | 权重 | 计算方式 |
  |---|---|---|
  | 近因性（recency） | 0.30 | `exp(-ln2 · Δt_hours / 24)`，24 小时半衰期的指数衰减 |
  | 重要性（importance） | 0.25 | `log(1+mention_count) / log(1+100)` |
  | 相关性（relevance） | 0.45 | `max(0, 1 - L2_distance / 阈值)` |

- 写入采用 **Upsert 语义**：同名概念更新而非新建，`mention_count` 累加
- 检索结果取 **Top-3** 注入上下文

### 2. 文件工具

- `tool_read_file` / `tool_list_file` / `tool_write_file`
- 带**路径白名单校验**（见下方"安全设计"）
- 编码自动探测：UTF-8-SIG → UTF-8 → GBK，均失败时返回明确提示而非抛异常

### 3. 代码执行

- `tool_execute_python_code`：**子进程隔离 + 超时限制**（默认 10 秒）
- 超时或非零退出码都返回明确状态，不静默失败

### 4. 时间感知

用 LangChain 的 `@dynamic_prompt` 中间件，在**模型请求层**动态注入当前系统时间：

```python
@dynamic_prompt
def runtime_prompt(request) -> str:
    current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S %A")
    return f"{BASE_SYSTEM_PROMPT}\n[当前系统精确时间]: {current_time_str}"
```

**为什么不把时间拼进用户消息？** 因为那会污染 checkpoint——时间戳会被永久写进对话历史，每轮累积，且历史消息带着过时的时间。用中间件在请求层临时替换 system message，不写回状态。

### 5. 分层重试

重试按执行边界拆分，不对整个 `agent.invoke()` 重试，避免重复提交同一条 `HumanMessage`：

- `ModelRetryMiddleware`：只重试模型请求的临时错误（连接失败、超时、限流和部分 5xx）。
- `ToolRetryMiddleware`：只对只读工具重试一次，目前包括记忆查询、文件读取、文件列表和系统状态查询。
- 保存记忆、更新记忆、写文件和执行代码不自动重试，因为它们可能产生外部副作用。

工具只有抛出可重试异常时才会触发中间件。工具返回的业务失败字符串不会被当作临时异常重试。

### 6. 结构化响应契约（升级计划第 1 阶段）

`response_models.py` 定义了 Agent 输出的基础契约 `StructuredAgentResponse`：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `answer` | `str` | 是 | 展示给用户的最终回答，不能为空 |
| `intent` | `str` | 是 | 当前请求的意图，例如 `general`、`memory`、`file` 或 `code` |
| `memory_candidates` | `list[str]` | 否 | 相关记忆关键词，默认是空列表 |
| `need_tool` | `bool` | 是 | 是否需要调用工具 |

模型拒绝未声明的额外字段，并会拒绝空回答、缺少必填字段等无效结果。当前 `/chat` 仍保持原有文本响应兼容；结构化结果的 Agent 接入安排在下一天。

示例：

```json
{
  "answer": "已查询到相关记忆。",
  "intent": "memory",
  "memory_candidates": ["用户偏好"],
  "need_tool": true
}
```

---

## 快速开始

### 环境要求

- Python 3.10+
- 任意 OpenAI 兼容 API（默认 DeepSeek）

### 安装

```bash
git clone <repo-url>
cd agent项目复刻版

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

> ⚠️ 首次运行会下载 BGE 中文向量模型（约 130MB），之后从本地缓存加载。

### 配置

API Key 通过**环境变量**提供，不要写进代码：

```bash
# Windows PowerShell
$env:DEEPSEEK_API_KEY = "你的 Key"

# macOS / Linux
export DEEPSEEK_API_KEY="你的 Key"
```

模型和 `base_url` 在 `agent_core.py` 中配置。

### 运行

```bash
# 开发模式启动 API 服务
uvicorn api_server:app --reload
```

启动后可访问 `http://127.0.0.1:8000/docs` 查看 Swagger 文档。

### 接口示例

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

普通聊天：

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"thread_id":"demo-001","message":"你好"}'
```

流式聊天：

```bash
curl -N -X POST http://127.0.0.1:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"thread_id":"demo-stream-001","message":"请流式回复"}'
```

Windows PowerShell 中也可以把 JSON 保存到文件后使用：

```powershell
curl.exe -N -X POST "http://127.0.0.1:8000/chat/stream" `
  -H "Content-Type: application/json" `
  --data-binary "@stream_request.json"
```

---

## 架构

```
                        用户输入
                           │
                           ▼
        ┌──────────────────────────────────────┐
        │           agent_core.py              │
        │                                      │
        │  runtime_prompt  (dynamic_prompt)    │
        │  └─ 每轮在模型请求层注入当前时间        │
        │     不写回 checkpoint                 │
        └──────────────────┬───────────────────┘
                           │
                           ▼
        ┌──────────────────────────────────────┐
        │     create_agent  (LangChain 1.3)    │
        │  · system prompt                     │
        │  · 8 个工具                           │
        │  · SqliteSaver 持久化对话历史          │
        │  · SummarizationMiddleware           │
        └──────────────────┬───────────────────┘
                           │  LLM 决策要调用哪个工具
                           ▼
        ┌──────────────────────────────────────┐
        │          tools_registry.py           │
        │                                      │
        │  记忆 ×3 ──► memory_engine.py        │
        │              ChromaDB + BGE          │
        │                                      │
        │  文件 ×3 ──► utility_tools.py        │
        │              路径白名单 + 编码探测      │
        │                                      │
        │  执行 ×1 ──► subprocess + timeout    │
        │  系统 ×1                              │
        └──────────────────┬───────────────────┘
                           │
                           ▼
                   工具结果回填 → LLM → 回复
```

### 记忆检索流程

```
query
  │
  ├─ 1. ChromaDB 语义召回  Top-K = 8
  │
  ├─ 2. L2 距离过滤        阈值 0.8
  │      （超过阈值的直接丢弃）
  │
  ├─ 3. 三要素重排
  │      0.30 × 近因性
  │      0.25 × 重要性
  │      0.45 × 相关性
  │
  └─ 4. 返回 Top-3
```

---

## 安全设计

### 路径白名单校验

**问题**：最初只用 `os.path.join(WORKSPACE_DIR, filepath)` 拼接路径。

但 `os.path.join` 在遇到**绝对路径**时会直接丢弃前面的参数，也不拦截 `..\`。实测可逃逸：

| 输入 | 解析结果 | 是否逃逸 |
|---|---|---|
| `..\..\Windows\win.ini` | `C:\Users\Windows\...` | ❌ 逃逸 |
| `C:\Windows\win.ini` | `C:\Windows\win.ini` | ❌ 逃逸 |

也就是说，`read_file("C:\\Windows\\win.ini")` 能直接读出系统文件。

**修复**：三层校验。

```python
def _safe_path(filepath: str):
    for workspace_dir in WORKSPACE_DIRS:
        root = os.path.realpath(workspace_dir)
        target = os.path.realpath(filepath if os.path.isabs(filepath)
                                  else os.path.join(root, filepath))

        # 1. 跨盘符直接跳过（commonpath 在不同盘符下会抛 ValueError）
        if os.path.splitdrive(root)[0].lower() != os.path.splitdrive(target)[0].lower():
            continue

        # 2. realpath + commonpath 双重校验
        if os.path.commonpath([root, target]) == root:
            return True, target
    return False, ""
```

要点：`realpath` 会解析 `..` 和符号链接，`commonpath` 确保最终路径落在白名单根目录内。

**实测结果**：

```
read_file("..\\..\\Windows\\win.ini")  → 读取失败：路径不在允许范围内 ✅
read_file("C:\\Windows\\win.ini")      → 读取失败：路径不在允许范围内 ✅
read_file("test_note.txt")            → 正常返回内容 ✅
```

### 代码执行隔离

**问题**：最初用 `exec(code, {})`，注释写着"沙盒"。但 `exec` 只隔离了**全局命名空间**，没有任何权限隔离——实测可以通过 `import os` 直接写文件。

**修复**：改用 `subprocess.run()` 子进程执行，带超时控制：

```python
process = subprocess.run(
    [sys.executable, "-c", code],
    cwd=os.path.realpath(WORKSPACE_DIRS[0]),
    capture_output=True, text=True,
    timeout=timeout_seconds,
    encoding="utf-8", errors="replace",
)
```

**注意**：这不是真正的沙箱（子进程仍能访问文件系统和网络），只是把"命名空间隔离"升级为"进程边界 + 超时控制"。**不应把不可信代码交给它执行。**

---

## 我在这个项目里定位并修复的问题

以下每个问题都有可复现的验证方式。

### 1. 检索阈值形同虚设

`EDGE_THRESHOLD` 原为 `1.5`。但实测各 query 的 L2 距离：

| query | L2 距离 | 性质 |
|---|---|---|
| `Python编程语言` | 0.42 ~ 0.99 | 相关 |
| `量子力学` | 1.31 ~ 1.59 | 无关 |
| `完全不相关的内容zzzz` | 1.22 ~ 1.33 | 无关 |

**无关内容的距离也全部小于 1.5，等于完全不过滤。** 实测 `search("完全不相关的内容zzzz")` 会返回库中全部记忆。

修复：用正负样本重新标定阈值，改为 **0.8**。

### 2. 更新字段名与读取字段名不一致

`update_by_id` 写入的是 `last_created_at`，而 `search()` 读取的是 `last_mentioned_at`。

**后果**：所有被更新过的记忆，其"最近提及时间"永远停留在创建时间，近因性评分从原理上就是错的。

数据库中的实证：

```
1b5ad522  last_mentioned_at=2026-09-04T00:48:29   last_created_at=2026-09-05T02:10:15
                                                    ↑ 更新发生在 9/5，但检索看不到
```

修复：统一字段名为 `last_mentioned_at`。

### 3. 单条脏数据会导致整个检索崩溃

```python
last_time = datetime.fromisoformat(doc.metadata.get("last_mentioned_at", ""))
```

`fromisoformat("")` 抛 `ValueError`。只要库中有一条缺该字段的记录，**整个检索就挂掉**，而不是跳过那一条。

修复：包 `try/except`，解析失败时令 `recency = 0.0`（视为很久以前），不影响其余结果。

### 4. 读取文件硬编码 UTF-8

Windows 记事本默认保存为 GBK。读取这类文件时直接报错：

```
读取失败:'utf-8' codec can't decode byte 0xd6 in position 0
```

修复：改为二进制读取 + 编码轮询（`utf-8-sig` → `utf-8` → `gbk`），均失败时返回提示而非异常。

> 先试 `utf-8-sig` 是为了处理带 BOM 的文件，避免 BOM 字符残留在字符串开头。

### 5. 时间注入污染对话历史

最初实现是把时间拼进用户消息：`content = userinput + datetime.now().isoformat()`。

**后果**：时间戳被永久写入 checkpoint，历史消息累积大量过时时间，且用户原话与时间戳无分隔符、无法拆分。

修复：改用 `@dynamic_prompt` 中间件，在模型请求层临时替换 system message，不写回状态。

---

## 已知问题

诚实记录，未解决：

1. **`search()` 中每条结果都会额外查一次库**。为了拿 `concept_id`，每条结果都执行一次 `vector_db.get(where={'concept': ...})`。库大之后这是 O(n) 次额外查询。且当存在同名概念时，会返回重复 id。

2. **`WORKSPACE_DIRS` 目前包含整个用户桌面**。这是开发期为了方便调试留下的，生产使用应只保留 `./workspace`。

3. **去重依赖 `concept` 名称作为业务主键**。若概念改名，可能与已有条目撞名，产生重复实体。更稳妥的方案是使用稳定 id 作为主键、`concept` 仅作展示名。

4. **`SummarizationMiddleware` 的触发阈值设为 300000 tokens**，在实际使用中几乎不会触发，长对话压缩能力未经真实验证。

5. **测试覆盖仍不完整**。目前共有 43 个用例，覆盖文件工具、记忆引擎、API 层以及模型和工具重试边界，
   但 Agent 层的真实模型对话流程、长对话压缩和真实工具调用链尚无测试。

6. **客户端重复请求尚未去重**。当前重试已经下沉到模型和只读工具层，但如果客户端因网络原因没有收到响应并再次发送同一个请求，服务仍可能把它当作新的请求执行。
   后续需要为客户端提供幂等键，并保存请求状态和最终结果。

7. **工具错误类型仍需细化**。现有工具的一些失败会返回普通字符串，因此不会触发工具重试；后续需要区分可重试的临时错误和应直接展示的业务错误。

---

## 测试

```bash
pip install pytest
python -m pytest tests/ -v
```

当前共有 43 个用例：

| 文件 | 用例数 | 覆盖内容 |
|---|---|---|
| `tests/test_utility_tools.py` | 17 | 路径白名单（穿越 / 绝对路径）、GBK 与二进制读取、读写往返、非法模式、代码执行与超时 |
| `tests/test_memory_engine.py` | 8 | 空库检索、写入去重、更新字段一致性、mention_count 累加、阈值过滤、脏数据容错 |
| `tests/test_api_server.py` | 8 | 健康检查、参数校验、普通聊天成功/失败、SSE 正常/异常事件 |
| `tests/test_response_models.py` | 6 | 结构化模型原型的字段校验 |
| `tests/test_retry_policy.py` | 4 | 模型临时错误重试、只读工具重试和写工具不重试 |

其中若干用例是**回归测试**，专门锁住本项目修复过的 bug：

- `test_read_gbk_file` —— 曾经硬编码 UTF-8，导致读 GBK 文件直接报错
- `test_list_files_none_does_not_crash` —— 曾经 `list_files()` 无参数必崩
- `test_update_changes_last_mentioned_at` —— 曾经写错字段名，导致近因性永远算错
- `test_missing_timestamp_does_not_crash` —— 曾经一条脏数据搞崩整个检索

---

## 项目结构

```
agent项目复刻版/
├── agent_core.py          # 入口：LLM 配置、Agent 组装、动态时间注入、对话循环
├── memory_engine.py       # 记忆引擎：ChromaDB 读写、三要素重排检索
├── tools_registry.py      # 工具注册：8 个工具的 @tool 定义
├── utility_tools.py       # 文件与系统工具：路径校验、编码探测、子进程执行
├── requirements.txt       # 依赖清单
├── memory_db/             # ChromaDB 持久化目录（已 gitignore）
└── workspace/             # 文件工具的默认工作区
```

---

## 运行截图

建议补充以下截图：

- Swagger `/docs` 页面和 `/health` 响应；
- `curl -N` 收到的 SSE `token` / `done` 事件；
- 带 `request_id` 的请求日志；
- 记忆检索命中结果。

截图中不要包含 API Key、Cookie、完整本机路径或私人对话内容。

---

## 后续计划

按优先级：

- [x] 补充自动化测试（路径校验、编码兼容、检索过滤、执行超时）—— 共 25 个用例
- [ ] 长对话压缩阈值调优并实测触发效果
- [ ] 检索准确率实测：构造标注集，记录 Top-3 命中率
- [ ] 文件写入的确认机制（Human-in-the-loop）
- [x] 分层工具调用失败重试（模型层、只读工具层）
- [ ] 客户端请求幂等键与重复请求去重
- [ ] 记忆的遗忘机制（长期未提及的条目自动降权）
