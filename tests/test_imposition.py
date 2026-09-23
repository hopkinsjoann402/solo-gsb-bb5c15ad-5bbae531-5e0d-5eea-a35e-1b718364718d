"""核心拼版逻辑 + HTTP 接口测试。"""

import pytest

from app.imposition import build_booklet, impose_signature, split_signatures


def _all_pages(booklet):
    """收集所有帖所有面的(左, 右)页码对。"""
    pairs = []
    for sig in booklet["signatures"]:
        for sheet in sig["pages"]:
            pairs.append((sheet["front"]["left"], sheet["front"]["right"]))
            pairs.append((sheet["back"]["left"], sheet["back"]["right"]))
    return pairs


# ---------- 分帖 ----------

def test_split_full_signatures_no_padding():
    sigs = split_signatures(16, 4)  # 每帖 16 页
    assert sigs == [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]]


def test_split_multiple_signatures():
    sigs = split_signatures(20, 4)  # 16 + 4
    assert len(sigs) == 2
    assert sigs[0] == list(range(1, 17))
    assert sigs[1] == [17, 18, 19, 20]  # 恰为 4 的倍数, 不补白


def test_split_last_signature_padded():
    sigs = split_signatures(18, 4)  # 16 + 2 -> 末帖补到 4
    assert len(sigs) == 2
    assert sigs[1] == [17, 18, None, None]


def test_split_small_padded():
    sigs = split_signatures(5, 2)  # 容量 8, 末帖补到 8
    assert sigs == [[1, 2, 3, 4, 5, None, None, None]]
    assert len(sigs[0]) == 8


def test_split_capacity_one_sheet():
    sigs = split_signatures(3, 1)
    assert sigs == [[1, 2, 3, None]]


def test_split_all_lengths_multiple_of_four():
    for total in range(1, 65):
        for cap in (1, 2, 3, 5):
            sigs = split_signatures(total, cap)
            assert all(len(s) % 4 == 0 for s in sigs)


# ---------- 左装订拼版 ----------

def test_left_binding_16_pages_4_sheets():
    booklet = build_booklet(16, 4, "left")
    pages = booklet["signatures"][0]["pages"]
    assert [s["sheet"] for s in pages] == [1, 2, 3, 4]
    # 最外张正面: 末页/首页; 背面: 次页/倒数第二页
    assert (pages[0]["front"]["left"], pages[0]["front"]["right"]) == (16, 1)
    assert (pages[0]["back"]["left"], pages[0]["back"]["right"]) == (2, 15)
    # 向内推进
    assert (pages[1]["front"]["left"], pages[1]["front"]["right"]) == (14, 3)
    assert (pages[1]["back"]["left"], pages[1]["back"]["right"]) == (4, 13)
    # 最内张
    assert (pages[3]["front"]["left"], pages[3]["front"]["right"]) == (10, 7)
    assert (pages[3]["back"]["left"], pages[3]["back"]["right"]) == (8, 9)


def test_left_binding_padded_outermost_sheet():
    # 1 页一本(1 张纸): 正面 null/1, 背面 2? -> 实际为 null/1 与 null/null
    booklet = build_booklet(1, 1, "left")
    pages = booklet["signatures"][0]["pages"][0]
    assert pages["front"] == {"left": None, "right": 1}
    assert pages["back"] == {"left": None, "right": None}


def test_every_page_appears_exactly_once():
    for total in (1, 4, 5, 8, 16, 17, 33, 100):
        booklet = build_booklet(total, 3, "left")
        flat = [p for pair in _all_pages(booklet) for p in pair if p is not None]
        assert sorted(flat) == list(range(1, total + 1))
        null_count = sum(p is None for pair in _all_pages(booklet) for p in pair)
        assert null_count == (-total) % 4


# ---------- 右装订镜像 ----------

def test_right_is_mirror_of_left():
    left = build_booklet(16, 4, "left")
    right = build_booklet(16, 4, "right")
    for sl, sr in zip(left["signatures"], right["signatures"]):
        for shl, shr in zip(sl["pages"], sr["pages"]):
            assert shr["front"] == {"left": shl["front"]["right"],
                                    "right": shl["front"]["left"]}
            assert shr["back"] == {"left": shl["back"]["right"],
                                   "right": shl["back"]["left"]}


def test_right_outermost_sheet():
    pages = build_booklet(16, 4, "right")["signatures"][0]["pages"]
    assert (pages[0]["front"]["left"], pages[0]["front"]["right"]) == (1, 16)
    assert (pages[0]["back"]["left"], pages[0]["back"]["right"]) == (15, 2)


# ---------- 非法参数 ----------

def test_core_invalid_args():
    with pytest.raises(ValueError):
        split_signatures(0, 4)
    with pytest.raises(ValueError):
        split_signatures(16, 0)
    with pytest.raises(ValueError):
        impose_signature([1, 2, 3, 4], "top")


# ---------- HTTP 层 ----------

def test_api_ok(client):
    r = client.get("/api/v1/impose", params={
        "total_pages": 16, "max_sheets": 4, "binding": "left"})
    assert r.status_code == 200
    data = r.json()
    assert data["signature_count"] == 1
    assert data["signatures"][0]["number"] == 1
    assert data["signatures"][0]["sheets"] == 4


@pytest.mark.parametrize("params", [
    {"total_pages": 0, "max_sheets": 4, "binding": "left"},
    {"total_pages": -3, "max_sheets": 4, "binding": "left"},
    {"total_pages": 16, "max_sheets": 0, "binding": "left"},
    {"total_pages": 1.5, "max_sheets": 4, "binding": "left"},
    {"total_pages": "abc", "max_sheets": 4, "binding": "left"},
    {"total_pages": 16, "max_sheets": 4, "binding": "right "},
    {"total_pages": 16, "max_sheets": 4},  # 缺 binding
    {"max_sheets": 4, "binding": "left"},  # 缺 total_pages
])
def test_api_invalid_params_4xx(client, params):
    r = client.get("/api/v1/impose", params=params)
    assert 400 <= r.status_code < 500


def test_api_over_limit_400(client, monkeypatch):
    monkeypatch.setattr("app.main.MAX_TOTAL_PAGES", 10)
    r = client.get("/api/v1/impose", params={
        "total_pages": 11, "max_sheets": 1, "binding": "left"})
    assert r.status_code == 400


def test_health_and_index(client):
    assert client.get("/healthz").status_code == 200
    body = client.get("/").json()
    assert "docs" in body
