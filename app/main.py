"""离线小册子拼版 API (FastAPI)。

接口一览
--------
GET  /                    服务信息与文档链接
GET  /healthz             存活探针
GET  /api/v1/impose       拼版(总页数 / 每帖最多纸张数 / 装订方向)
"""

import os
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from .imposition import build_booklet

Binding = Literal["left", "right"]

# 防止误传巨大页数拖垮服务, 可通过环境变量调整。
MAX_TOTAL_PAGES = int(os.getenv("MAX_TOTAL_PAGES", "100000"))

app = FastAPI(
    title="离线小册子拼版 API",
    description="按帖装订的小册子拼版: 输入总页数、每帖最多纸张数和左/右装订方向, "
    "按纸张从外到内返回每帖各张正反面的左右页码(空白页为 null)。",
    version="1.0.0",
)


class Face(BaseModel):
    left: Optional[int] = Field(default=None, description="左页页码; 空白页为 null")
    right: Optional[int] = Field(default=None, description="右页页码; 空白页为 null")


class Sheet(BaseModel):
    sheet: int = Field(description="帖内纸张序号, 从外到内从 1 开始")
    front: Face = Field(description="正面(朝外的一面)左右页码")
    back: Face = Field(description="背面(朝里的一面)左右页码")


class Signature(BaseModel):
    number: int = Field(description="帖号, 从 1 开始")
    sheets: int = Field(description="该帖实际纸张数")
    blank_pages: int = Field(description="该帖补白页数")
    pages: list[Sheet] = Field(description="各张纸(从外到内)的正反面页码")


class ImpositionResult(BaseModel):
    total_pages: int
    max_sheets_per_signature: int
    binding: Binding
    signature_count: int
    signatures: list[Signature]


@app.get("/", tags=["meta"], summary="服务信息")
def index() -> dict:
    return {
        "service": "booklet-imposition-api",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "health": "/healthz",
        "impose": "/api/v1/impose?total_pages=16&max_sheets=4&binding=left",
    }


@app.get("/healthz", tags=["meta"], summary="健康检查")
def healthz() -> dict:
    return {"status": "ok"}


@app.get(
    "/api/v1/impose",
    tags=["imposition"],
    summary="小册子拼版",
    response_model=ImpositionResult,
)
def impose(
    total_pages: int = Query(
        ..., ge=1, description="全书总页数(正整数, 1 基页码)"
    ),
    max_sheets: int = Query(
        ...,
        ge=1,
        alias="max_sheets",
        description="每帖最多纸张数(正整数); 每帖最多容纳 4 倍纸张数个页位",
    ),
    binding: Binding = Query(
        ..., description="装订方向: left=左装订, right=右装订(左右页位镜像交换)"
    ),
) -> dict:
    if total_pages > MAX_TOTAL_PAGES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"total_pages={total_pages} 超过服务上限 {MAX_TOTAL_PAGES}; "
                "可通过环境变量 MAX_TOTAL_PAGES 调整"
            ),
        )
    return build_booklet(total_pages, max_sheets, binding)
