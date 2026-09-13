"""memory_engine 的测试。

注意：MemoryEngine 初始化时会加载 BGE 向量模型（约 130MB），
所以整个模块共用一个实例（scope="module"），避免重复加载。

测试用例的执行顺序有意义：
  空库检索 → 写入 → 更新 → 脏数据容错
"""

import time

import pytest
from langchain_core.documents import Document

from memory_engine import EDGE_THRESHOLD, MemoryEngine


@pytest.fixture(scope="module")
def engine(tmp_path_factory):
    """独立临时库，不污染开发用的 memory_db。"""
    persist_dir = tmp_path_factory.mktemp("chroma_test")
    return MemoryEngine(persist_dir=str(persist_dir))


# --------------------------------------------------------------------------
# 1. 空库
# --------------------------------------------------------------------------

def test_search_empty_db_returns_empty(engine):
    """空库检索应返回空列表，而不是抛异常。"""
    result = engine.search("任何东西")
    assert result == []


# --------------------------------------------------------------------------
# 2. 写入与检索
# --------------------------------------------------------------------------

def test_save_then_search(engine):
    """写入后应能检索到。"""
    engine.save(
        concept="测试概念A",
        content="这是一条用于测试的记忆内容",
        tags=["测试", "自动化"],
    )
    result = engine.search("测试概念A")
    assert len(result) >= 1
    assert result[0]["concept"] == "测试概念A"


def test_save_same_concept_twice_does_not_duplicate(engine):
    """同名概念重复写入时应返回“已存在”，而不是新建。"""
    engine.save(concept="测试概念B", content="内容一", tags=["t"])
    msg = engine.save(concept="测试概念B", content="内容二", tags=["t"])
    assert "已存在" in msg

    ids = engine.vector_db.get(where={"concept": "测试概念B"})["ids"]
    assert len(ids) == 1, "同名概念不应产生重复条目"


# --------------------------------------------------------------------------
# 3. 更新
# --------------------------------------------------------------------------

def test_update_changes_last_mentioned_at(engine):
    """回归测试：update_by_id 曾经写错字段名（last_created_at），
    导致 last_mentioned_at 永远不变、近因性计算失效。
    """
    engine.save(concept="测试概念C", content="原始内容", tags=["t"])
    cid = engine.vector_db.get(where={"concept": "测试概念C"})["ids"][0]

    before = engine.vector_db.get(ids=[cid])["metadatas"][0]["last_mentioned_at"]

    time.sleep(0.05)  # 保证时间戳不同
    engine.update_by_id(concept_id=cid, new_content="更新后的内容")

    after_meta = engine.vector_db.get(ids=[cid])["metadatas"][0]

    assert after_meta["last_mentioned_at"] > before, (
        "更新后 last_mentioned_at 没有变化 —— 检查是否又写成了别的字段名"
    )
    assert "last_created_at" not in after_meta, (
        "出现了 last_created_at 字段，说明字段名又不一致了"
    )


def test_update_accumulates_mention_count(engine):
    """更新应让 mention_count 累加。"""
    engine.save(concept="测试概念D", content="内容", tags=["t"])
    cid = engine.vector_db.get(where={"concept": "测试概念D"})["ids"][0]

    engine.update_by_id(concept_id=cid, new_content="内容2")
    engine.update_by_id(concept_id=cid, new_content="内容3")

    meta = engine.vector_db.get(ids=[cid])["metadatas"][0]
    assert meta["mention_count"] >= 3


def test_update_missing_id_returns_error(engine):
    """更新不存在的 id 应返回失败信息。"""
    result = engine.update_by_id(concept_id="nonexistent-id-12345", new_content="x")
    assert "失败" in result


# --------------------------------------------------------------------------
# 4. 阈值过滤
# --------------------------------------------------------------------------

def test_irrelevant_query_is_filtered(engine):
    """无关 query 应被阈值过滤掉，不返回任何记忆。

    阈值依据（bge-small-zh-v1.5，实测）：
        相关记忆   L2 距离约 0.42 ~ 0.99
        无关记忆   L2 距离约 1.21 ~ 1.60
    当前 EDGE_THRESHOLD = 0.8 位于两者之间。

    如果这个测试失败，说明阈值需要基于新的样本重新标定。
    """
    engine.save(concept="咖啡", content="一种苦味热饮", tags=["饮品"])
    result = engine.search("量子纠缠的退相干时间尺度计算")
    assert result == [], (
        f"无关 query 竟返回了 {len(result)} 条结果 —— "
        f"当前阈值 {EDGE_THRESHOLD} 可能偏大"
    )


# --------------------------------------------------------------------------
# 5. 脏数据容错
# --------------------------------------------------------------------------

def test_missing_timestamp_does_not_crash(engine):
    """回归测试：缺少 last_mentioned_at 字段的记录，
    曾经导致 datetime.fromisoformat('') 抛出 ValueError，整个检索崩溃。
    """
    engine.vector_db.add_documents([
        Document(
            page_content="脏数据条目:故意不带时间戳",
            metadata={"concept": "脏数据条目", "mention_count": 1},
        )
    ])

    # 关键：不应抛出异常
    result = engine.search("脏数据条目")
    assert isinstance(result, list)
