"""utility_tools 的测试。

注意路径写法：
    WORKSPACE_DIRS[0] 是相对路径 "./workspace"，而测试运行前会
    chdir 到项目根目录，所以传给工具的 filepath 应当相对于
    workspace 目录本身（例如 "_test.txt"），而不是 "workspace/_test.txt"。

覆盖：
  1. 路径白名单 —— 绝对路径逃逸、..\\ 穿越，都必须被拒绝
  2. 编码探测   —— GBK 能读、二进制不抛异常
  3. 文件读写   —— 正常路径可用、非法模式被拒
  4. 代码执行   —— 正常执行、非零退出码、超时
"""

import os

import pytest

from utility_tools import (
    _safe_path,
    execute_python_code,
    list_files,
    read_workspace_file,
    write_workspace_file,
)

WORKSPACE = os.path.join(os.path.realpath("."), "workspace")


def _cleanup(name: str) -> None:
    p = os.path.join(WORKSPACE, name)
    if os.path.exists(p):
        os.remove(p)


# --------------------------------------------------------------------------
# 1. 路径白名单
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "evil_path",
    [
        r"..\..\Windows\win.ini",            # 相对路径穿越
        r"..\..\..\..\..\Windows\win.ini",   # 更深的穿越
        r"C:\Windows\win.ini",               # 绝对路径
        r"..\..\..\Users",                   # 穿越到 C:\Users
    ],
)
def test_dangerous_path_rejected(evil_path):
    """这些路径都必须被判为不安全。"""
    safe, _ = _safe_path(evil_path)
    assert safe is False, f"路径 {evil_path} 本应被拒绝，却通过了校验"


def test_safe_relative_path_accepted():
    """工作区内的相对路径应该通过。"""
    safe, target = _safe_path("test_note.txt")
    assert safe is True
    assert os.path.realpath(target).startswith(os.path.realpath("."))


def test_read_outside_workspace_returns_error():
    """读工作区外的文件，应返回错误信息而不是抛出异常。"""
    result = read_workspace_file(r"C:\Windows\win.ini")
    assert "不在允许范围内" in result


def test_write_outside_workspace_rejected():
    """写工作区外的文件必须被拒绝，且不能真的产生文件。"""
    target = r"C:\Windows\_should_not_exist_test.txt"
    result = write_workspace_file(target, "x")
    assert "不在允许范围内" in result
    assert not os.path.exists(target)


# --------------------------------------------------------------------------
# 2. 编码探测
# --------------------------------------------------------------------------

def test_read_gbk_file():
    """GBK 编码的文件应能读出（Windows 记事本默认编码）。"""
    name = "_test_gbk.txt"
    with open(os.path.join(WORKSPACE, name), "wb") as f:
        f.write("中文内容测试".encode("gbk"))
    try:
        result = read_workspace_file(name)
        assert "中文内容测试" in result
    finally:
        _cleanup(name)


def test_read_binary_file_returns_notice():
    """二进制文件不能抛异常，应返回明确提示。"""
    name = "_test_binary.bin"
    with open(os.path.join(WORKSPACE, name), "wb") as f:
        f.write(bytes(range(256)))
    try:
        result = read_workspace_file(name)
        assert isinstance(result, str)
        assert "二进制" in result or "未知编码" in result
    finally:
        _cleanup(name)


# --------------------------------------------------------------------------
# 3. 文件读写
# --------------------------------------------------------------------------

def test_write_then_read_roundtrip():
    """写入后应能读回相同内容；追加模式不应覆盖。"""
    name = "_test_roundtrip.txt"
    try:
        assert "成功写入" in write_workspace_file(name, "第一行\n", mode="w")
        assert "成功写入" in write_workspace_file(name, "第二行\n", mode="a")

        content = read_workspace_file(name)
        assert "第一行" in content
        assert "第二行" in content
    finally:
        _cleanup(name)


def test_invalid_mode_rejected():
    """非法的写入模式应被拒绝。"""
    result = write_workspace_file("_x.txt", "data", mode="x")
    assert "mode" in result


def test_read_missing_file():
    """读不存在的文件，返回提示而不是异常。"""
    result = read_workspace_file("_definitely_missing_file.txt")
    assert "不存在" in result


def test_list_files_default():
    """list_files() 不传参数时，应列出 workspace 目录内容。"""
    result = list_files()
    assert "文件列表" in result


def test_list_files_none_does_not_crash():
    """回归测试：list_files(None) 曾经因为 _safe_path(None) 抛 TypeError 而失败。"""
    result = list_files(None)
    assert isinstance(result, str)
    assert "不在允许范围内" not in result


# --------------------------------------------------------------------------
# 4. 代码执行
# --------------------------------------------------------------------------

def test_execute_prints_result():
    """正常执行应返回 stdout。"""
    result = execute_python_code("print(1 + 1)")
    assert "2" in result


def test_execute_nonzero_exit():
    """抛异常的代码应返回失败信息和错误内容。"""
    result = execute_python_code("raise ValueError('boom')")
    assert "失败" in result
    assert "boom" in result


def test_execute_timeout():
    """超时的代码应被强制终止。"""
    result = execute_python_code("import time; time.sleep(30)", timeout_seconds=1)
    assert "超时" in result
