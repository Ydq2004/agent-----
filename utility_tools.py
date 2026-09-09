import os
from datetime import datetime
import platform
import subprocess
import sys


WORKSPACE_DIRS=[".\\workspace","C:\\Users\\21968\\Desktop"]

def _safe_path(filepath:str):
    safe=False
    target_path=""
    for workspace_dir in WORKSPACE_DIRS:
        root=os.path.realpath(workspace_dir)
        if os.path.isabs(filepath):
            target = os.path.realpath(filepath)
        else:
            target = os.path.realpath(os.path.join(root, filepath))
            
        if os.path.splitdrive(root)[0].lower() != os.path.splitdrive(target)[0].lower():
            continue

        if os.path.commonpath([root,target])==root:
            safe=True
            target_path=target
            break

    return safe,target_path

def _read_text(path: str) -> str:
    """以二进制读取并自动探测 utf-8-sig / utf-8 / gbk 编码"""
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except Exception as e:
        return f"读取文件底层失败: {e}"
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return f"[二进制或未知编码文件，{len(raw)} 字节]"


def read_workspace_file(filepath:str)->str:
    safe,file_path = _safe_path(filepath)
    if not safe:
        return f"读取失败：路径 [{filepath}] 不在允许范围内。"
   
    # 2. 检查文件存不存在
    if not os.path.exists(file_path):
        return f"读取失败：文件 [{filepath}] 不存在。"
    
    file_str=_read_text(file_path)

    return file_str


def  write_workspace_file(filepath:str, content:str, mode: str ="w")->str:
    safe,file_path = _safe_path(filepath)
    if not safe:
        return f"写入失败：路径 [{filepath}] 不在允许范围内。"
    file_str="文件内容"
    if mode!="w" and mode!="a": 
        return "写入mode有误,修改为:覆盖w,追加a"

    try:
        with open(file_path,mode,encoding="utf-8") as f:
            number=f.write(content) 
        return f"成功写入文件{file_path}，共写入 {number} 个字符。"
    except Exception as e:
        file_str=f"写入失败:{e}"
        return file_str

def list_files(listpath:str = None,)->str:
    if listpath is None : 
        listpath = "."
    safe,list_path = _safe_path(listpath)
    if not safe:
        return f"读取文件表失败：路径 [{list_path}] 不在允许范围内。"
    if not os.path.exists(list_path):
         return f"读取失败：文件夹 [{list_path}] 不存在。"
    files=os.listdir(list_path)
    if not files:
        return f"当前路径文件表{list_path}为空，暂无任何文件。"
    return "当前工作区文件列表：\n" + "\n".join(f"- {f}" for f in files)


def get_system_status()->str:
    try:
        current_time = datetime.now().isoformat()
        os_name = platform.system()
        python_version = platform.python_version()
        return f"当前时间:{current_time}\n当前系统:{os_name}\n当前python版本:{python_version}"
    except Exception as e:
        return f"获取系统信息失败:{e}"


def execute_python_code(code:str,timeout_seconds:int=10) ->str:
    cwd_dir = os.path.realpath(WORKSPACE_DIRS[0])

    try:
       process=subprocess.run(
           [sys.executable,"-c",code],
           cwd=cwd_dir,
           capture_output=True,
           text=True,
           timeout=timeout_seconds,
           encoding="utf-8",
           errors="replace"
       )
       output = process.stdout
       error_output =process.stderr
       if process.returncode != 0:
            return f"代码执行失败（退出码 {process.returncode}）：\n{error_output.strip()}"
        
       if not output.strip() and not error_output.strip():
            return "代码执行成功，但没有产生任何标准输出（print）。"
       result=output.strip()
       if error_output.strip():
            result += f"\n[警告/标准错误输出]:\n{error_output.strip()}"
       return f"执行输出：\n{result}"
    except subprocess.TimeoutExpired:
        return f"代码执行超时：运行时间超过了 {timeout_seconds} 秒上限，已被系统强行终止。"

    except Exception as e:
        return f"代码执行出错：{type(e).__name__}: {e}"

    

