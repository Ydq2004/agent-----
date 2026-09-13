from memory_engine import MemoryEngine
from langchain_core.tools import tool
import json
from utility_tools import (
    read_workspace_file,
    write_workspace_file,
    list_files,
    get_system_status,
    execute_python_code,
)

memory_engine=MemoryEngine()

@tool
def save_memory(
    concept:str,
    content:str,
    tags:list[str]
)->str:
    """
    调用此函数,可以保存训练数据以外的知识,概念,事件,偏好,值得记录的记忆点,:
    参数: 
    -concept: 将要保存的长期记忆概括.
    -content: 将要保存的长期记忆的详细内容.
    -tags:  将要保存的长期记忆的扁平化分类标签.
    """
    msg=memory_engine.save(concept=concept,content=content,tags=tags)
    return msg

@tool
def search_memory(
    query:str,
)->str:
    """
    查询储存的长期记忆时调用此函数.
    参数:query 将要查询的长期记忆内容,如"用户的偏好","难绷是什么意思".
    """
    results=memory_engine.search(query=query)

    json_result="\n".join(json.dumps(item,ensure_ascii=False)for item in results)
    return json_result

@tool
def update_memory_by_id(
    concept_id:str,
    new_content:str,
    new_concept_name:str|None=None,
    new_tags:list[str]|None=None,
    )->str:
    """
    需要通过记忆id来更新特定的记忆时请调用此工具.
    参数:
    -concept_id: 将要更新的记忆的id.
    -new_content: 更新记忆的详细内容.
    -new_concept_name: 更新记忆的concept内容概要,如果更新的详细记忆内容仍在就概要名称范围内,传入None,不更新.
    -new_tags: 如果记忆详细内容能提取的分类标签发生变化,就请传入新的分类标签,如果没有发生变化,传入None,不更新.
    """

    msg=memory_engine.update_by_id(concept_id=concept_id,new_content=new_content,new_concept_name=new_concept_name,new_tags=new_tags)
    return msg

@tool
def tool_read_file(filepath:str)->str:
    """文件阅读工具:filepath为需要阅读的文件地址,注意filepath只能在允许范围内,注意不用顾虑转义符,直接输入地址即可"""
    msg=read_workspace_file(filepath=filepath)
    return msg

@tool
def tool_list_file(listpath:str)->str:
    """查看特定地址下有哪些文件工具:listpath为需要查看文件夹的地址路径,注意listpath只能在允许范围内,注意不用顾虑转义符,直接输入地址即可"""
    msg=list_files(listpath=listpath)
    return msg

@tool
def tool_write_file(
    filepath:str,
    content:str,
    mode:str="w"
)->str:
    """
    写文件工具.
    参数:
    filepath将要写入的文件地址,只能在允许范围内,注意不用顾虑转义符,直接输入地址即可.
    content将要写入或追加的内容.
    mode写入模式,'w'是覆盖,'a'是追加.
    """
    msg=write_workspace_file(filepath=filepath,content=content,mode=mode)
    return msg

@tool
def tool_execute_python_code(code:str)->str:
    """运行Python代码脚本工具:参数code为将要执行的代码或者脚本"""
    msg=execute_python_code(code=code)
    return msg

@tool
def tool_get_system_status()->str:
    """获取系统信息:系统名称,python版本,当前系统时间等"""
    msg=get_system_status()
    return msg


ALL_TOOLS=[save_memory,search_memory,update_memory_by_id,tool_read_file,tool_list_file,tool_write_file,tool_execute_python_code,tool_get_system_status]

