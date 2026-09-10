# agent项目复刻版 · v1.2 审查记录

> 审查时间：2026-09-09 16:30
> 审查对象：commit `71f1803` "v1.2"
> 方式：读源码 + 路径校验实机验证 + 检查字节码产物

---

## 一、状态确认

```
提交：71f1803  "v1.2
                 -安全路径拦截完善
                 -编码问题,不再写死utf-8
                 -检索代码兜底
                 -更新记忆工具字段修复
                 -exec工具调整为子进程实现
                 -检索阈值调整"
```

| 清单项 | 状态 |
|---|---|
| 1. 路径穿越 | ✅ 已修，且做得比我给的方案严谨 |
| 2. 编码兜底 | ✅ 已修（`_read_text` 三编码轮询） |
| 3. 检索崩溃 | ✅ 已修（try/except + recency=0.0） |
| 4. 字段名 | ✅ 已修（`last_mentioned_at`） |
| 5. exec 改造 | ⚠️ 改成了子进程，但**参数名拼错，目前必然失败** |
| 6. 阈值 | ⚠️ 1.5 → 0.8，方向对，但依据未记录 |
| 8. 死代码 | 🔶 部分清理，`file_str` 仍残留 |

**五条 P0 修对了四条。** 但引入了一个会让工具彻底失效的新问题。

---

## 二、🔴 P0：`execute_python_code` 目前 100% 失败

### 问题 1：关键字参数名拼错

```python
process = subprocess.run(
    [sys.executable, "-c", code],
    cwd=cwd_dir,
    capture_output=True,
    text=True,
    Timeout=timeout_seconds,     # ← 应该是 timeout（全小写）
    encoding="utf-8",
    errors="replace",
)
```

`subprocess.run()` 没有 `Timeout` 这个参数，只有 `timeout`。Python 关键字参数**区分大小写**。

**后果**：函数每次调用都在进入 try 之前就抛 `TypeError`，被外层 `except Exception` 捕获，返回"代码执行出错"。

### 问题 2：`_safe_path` 不接 `None`

`list_files()` 已经修好了（`if listpath is None: listpath = "."`），但 `_safe_path` 本身仍然会在收到 `None` 时抛 `TypeError`（`os.path.isabs(None)`）。

建议在 `_safe_path` 开头加一道防御：

```python
def _safe_path(filepath: str):
    if not filepath or not isinstance(filepath, str):
        return False, ""
    ...
```

这样任何调用方传空值都不会崩。

### 验证方法

修完后在项目根目录跑：

```bash
python -c "from utility_tools import execute_python_code; print(execute_python_code('print(1+1)'))"
```

预期输出：`执行输出：\n2`

---

## 三、🟠 P1：`__pycache__` 里是旧字节码

`__pycache__/` 下有：

```
memory_engine.cpython-314.pyc
tools_registry.cpython-314.pyc
utility_tools.cpython-314.pyc
```

`.pyc` 的时间戳是**改动前**的。如果你直接 `python agent_core.py` 而 Python 没有重新编译，可能会加载到旧版本。

**这不是 bug**（Python 会按 mtime 自动重编译），但说明**你还没实际运行过 `agent_core.py` 来验证改动**。改完代码不跑一遍，等于没改。

**做**：删掉 `__pycache__`，重新 `python agent_core.py` 跑一次对话，确认文件工具和记忆工具都正常。

---

## 四、🟠 P1：白名单仍然包含整个桌面

```python
WORKSPACE_DIRS = [".\\workspace", "C:\\Users\\21968\\Desktop"]
```

我实测过：`C:\Users\21968\Desktop\练习题.docx` **能读到**（只是编码报错），`副本茜草幼儿园2026年秋期新生分班幼儿信息表(1)(1).xlsx` 也在范围内。

**这是权限过宽，不是漏洞。** 但考虑到桌面上有真实幼儿信息，建议：

```python
WORKSPACE_DIRS = [".\\workspace"]
```

需要额外目录时再单独加，加之前问一句"Agent 真的需要吗"。

---

## 五、🟠 P1：`_safe_path` 的一个真实缺陷

```python
if os.path.isabs(filepath):
    target = os.path.realpath(filepath)
```

**绝对路径直接放行到 realpath**，只靠后面的 `commonpath` 拦。这在当前实现下是安全的（我实测 `C:\Windows\win.ini` 被拒）。

但有个边界情况：

```
os.path.commonpath([root, target])
```

当 `root` 和 `target` 分属不同盘符时，`commonpath` 会抛 `ValueError`。你已经用 `splitdrive` 提前拦了——**这一步是对的**。

不过 `commonpath` 抛异常的其他情况（比如路径含 null 字节）没有被 try 包住。建议：

```python
try:
    if os.path.commonpath([root, target]) == root:
        ...
except ValueError:
    continue
```

**低优先级**，但这是"防御性编程"该有的样子。

---

## 六、🔵 建议：把测出来的数字写进注释

`EDGE_THRESHOLD = 0.8` —— 这个数字怎么来的？

建议改成：

```python
# 阈值依据（bge-small-zh-v1.5，本机实测）：
#   相关样本 L2: 0.42 ~ 0.99
#   无关样本 L2: 1.21 ~ 1.60
#   取 0.8 作为分界
EDGE_THRESHOLD = 0.8
```

**面试官一定会问"为什么是 0.8"。** 有注释就是"我测过"，没注释就是"我猜的"。

---

## 七、待办（按优先级）

```
P0  1. Timeout -> timeout
    2. _safe_path 加 None 防御
    3. 删 __pycache__，实际跑一遍 agent_core.py 验证
    4. 提交

P1  5. WORKSPACE_DIRS 收窄为 [".\\workspace"]
    6. commonpath 包 try/except
    7. 阈值注释写明实测依据
    8. 清理 file_str 死变量

P1  9. 补 tests/（路径穿越、编码、list_files()、空库检索）
   10. 处理重复实体（两条 "Python编程语言"）
```

---

## 八、总评

**这一版的代码质量明显高于上一版。**

`_safe_path` 的多根白名单 + 盘符判断 + `realpath` + `commonpath`，四层防护，逻辑正确，实测有效。**这不是抄的，是读懂了才写得出来的。**

`_read_text` 的编码轮询顺序（`utf-8-sig` → `utf-8` → `gbk`）也对——先试带 BOM 的，避免 BOM 残留在字符串里。

**唯一的问题是 `Timeout` 那个拼写。** 这种错误很典型：改完代码没跑，直接提交。以后改完**先跑一遍**，再 commit。

---

*本记录所有验证结果均来自实机测试。*
