import os
from datetime import datetime
import platform
import io
import contextlib

WORKSPACE_DIR="C:\\Users\\21968\\Desktop"

def read_workspace_file(filepath:str)->str:
    os.makedirs(WORKSPACE_DIR,exist_ok=True)
    file_path = os.path.join(WORKSPACE_DIR, filepath)
    file_str="文件内容"
    # 2. 检查文件存不存在
    if not os.path.exists(file_path):
        return f"读取失败：文件 [{filepath}] 不存在。"
    
    try:
        with open(file_path,'r',encoding="utf-8") as file:
            file_str=file.read()
    except Exception as e:
        file_str=f"读取失败:{e}"

    return file_str


def  write_workspace_file(filepath:str, content:str, mode: str ="w")->str:
    os.makedirs(WORKSPACE_DIR,exist_ok=True)
    file_path = os.path.join(WORKSPACE_DIR, filepath)
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
    os.makedirs(WORKSPACE_DIR,exist_ok=True)
    file_path=WORKSPACE_DIR
    if listpath is not None and listpath !=WORKSPACE_DIR:
        file_path=os.path.join(WORKSPACE_DIR,listpath)
    if not os.path.exists(file_path):
         return f"读取失败：文件夹 [{file_path}] 不存在。"
    files=os.listdir(file_path)
    if not files:
        return f"当前文件夹{file_path}为空，暂无任何文件。"
    return "当前工作区文件列表：\n" + "\n".join(f"- {f}" for f in files)


def get_system_status()->str:
    try:
        current_time = datetime.now().isoformat()
        os_name = platform.system()
        python_version = platform.python_version()
        return f"当前时间:{current_time}\n当前系统:{os_name}\n当前python版本:{python_version}"
    except Exception as e:
        return f"获取系统信息失败:{e}"


def execute_python_code(code:str) ->str:
    output_buffer = io.StringIO()

    try:
        with contextlib.redirect_stdout(output_buffer):
            exec_scope = {} #沙盒用于装接下来运行产生的变量函数,避免污染外部坏境
            exec(code,exec_scope)
        result = output_buffer.getvalue()
        if not result:
            return "代码执行成功，但没有产生任何标准输出（print）。"
        return f"执行输出:\n{result}"
    except Exception as e:
        return f"代码执行出错：{type(e).__name__}: {e}"

    


if __name__ == "__main__":
    print("🚀 测试文件工具集...")
    
    # 1. 测试新建写入与追加
    print(write_workspace_file("test_note.txt", "第一行：Agent 学习笔记。\n", mode="w"))
    print(write_workspace_file("test_note.txt", "第二行：今天完成了文件工具的编写。\n", mode="a"))
    
    # 2. 测试列出文件与读取
    print(list_files())
    print("--- 读取文件内容 ---")
    print(read_workspace_file("test_note.txt"))

    # 3. 测试系统状态
    print("\n--- 系统状态测试 ---")
    print(get_system_status())

    # 4. 测试 Python 代码执行沙盒
    print("\n--- Python 执行测试 ---")
    code_test = "total = sum(range(1, 101))\nprint(f'1到100求和: {total}')"
    print(execute_python_code(code_test))