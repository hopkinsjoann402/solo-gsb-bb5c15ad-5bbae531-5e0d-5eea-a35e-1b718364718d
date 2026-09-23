"""离线小册子拼版核心逻辑。

基本概念
--------
一张纸对折后正反两面各承载 2 个页位, 因此 **1 张纸 = 4 个页位**。
- 帖(signature): 由若干张纸套叠成的一叠, ``sheets`` 张纸对应 ``4*sheets`` 个页位。
- 分帖: 按原书页码顺序切分; 每帖最多 ``max_sheets`` 张纸(即 ``4*max_sheets`` 页)。
  除最后一帖外每帖都是满帖; 仅最后一帖允许不足, 并在帖末补空白(``None``)到 4 的倍数。
- 页码: 全程使用全书统一的 1 基原页码; 空白页位用 ``None`` 表示。

拼版(以帖为单位, 纸张从外到内编号)
----------------------------------
设帖内页位为 p[0..n-1](n 为 4 的倍数), 左装订时第 k 张纸(k 从 0 起)::

    正面(front): 左 = p[n-1-2k], 右 = p[2k]
    背面(back) : 左 = p[2k+1],   右 = p[n-2-2k]

右装订为其镜像, 仅交换每个面的左、右页位。
"""

from typing import List, Optional

Binding = str  # "left" | "right"


def _pad_to_multiple_of_four(n: int) -> int:
    """把页数向上取整到 4 的倍数(每张纸 4 个页位)。"""
    return ((n + 3) // 4) * 4


def split_signatures(total_pages: int, max_sheets: int) -> List[List[Optional[int]]]:
    """按原页顺序把全书划分为若干帖。

    返回每帖的页位列表: 元素为 1..total_pages 的真实页码, 补白位置为 ``None``。
    除最后一帖外, 每帖长度恰为 ``4*max_sheets``; 最后一帖长度向上补齐到 4 的倍数。
    """
    if total_pages < 1:
        raise ValueError("total_pages 必须为正整数")
    if max_sheets < 1:
        raise ValueError("max_sheets 必须为正整数")

    capacity = 4 * max_sheets
    signatures: List[List[Optional[int]]] = []

    start = 1
    while start <= total_pages:
        real_pages = min(capacity, total_pages - start + 1)
        # 满帖(含总页数恰好是整帖容量的最后一帖)不补白; 否则只给末帖补白。
        size = capacity if real_pages == capacity else _pad_to_multiple_of_four(real_pages)

        pages: List[Optional[int]] = [
            page if page < start + real_pages else None
            for page in range(start, start + size)
        ]
        signatures.append(pages)
        start += size

    return signatures


def impose_signature(pages: List[Optional[int]], binding: Binding) -> List[dict]:
    """对单帖拼版, 按纸张从外到内返回各张纸正反面的左右页码。"""
    if binding not in ("left", "right"):
        raise ValueError("binding 必须为 'left' 或 'right'")
    if len(pages) % 4 != 0:
        raise ValueError("帖内页位数必须为 4 的倍数")

    n = len(pages)
    sheet_total = n // 4
    sheets: List[dict] = []

    for k in range(sheet_total):
        front_left = pages[n - 1 - 2 * k]
        front_right = pages[2 * k]
        back_left = pages[2 * k + 1]
        back_right = pages[n - 2 - 2 * k]

        if binding == "right":
            # 右装订: 镜像交换左右页位
            front_left, front_right = front_right, front_left
            back_left, back_right = back_right, back_left

        sheets.append(
            {
                "sheet": k + 1,
                "front": {"left": front_left, "right": front_right},
                "back": {"left": back_left, "right": back_right},
            }
        )

    return sheets


def build_booklet(total_pages: int, max_sheets: int, binding: Binding) -> dict:
    """生成整本书的拼版结果(分帖 + 每帖逐纸正反面页码)。"""
    signatures = []
    for index, pages in enumerate(split_signatures(total_pages, max_sheets), start=1):
        signatures.append(
            {
                "number": index,
                "sheets": len(pages) // 4,
                "blank_pages": sum(1 for p in pages if p is None),
                "pages": impose_signature(pages, binding),
            }
        )

    return {
        "total_pages": total_pages,
        "max_sheets_per_signature": max_sheets,
        "binding": binding,
        "signature_count": len(signatures),
        "signatures": signatures,
    }
