"""pytest 共享配置。

关键：把工作目录切到项目根目录。
因为 utility_tools.WORKSPACE_DIRS 里的 "./workspace" 是相对路径，
必须在项目根目录下运行，路径解析才正确。
"""

import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 让测试能 import 到项目根目录下的模块
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture(autouse=True)
def _chdir_to_project_root(monkeypatch):
    """每个测试前都切到项目根目录，测试后自动还原。"""
    monkeypatch.chdir(PROJECT_ROOT)
    yield
