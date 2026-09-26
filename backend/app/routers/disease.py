"""病害记录接口：覆盖登记、实施处置（保存等级与方案）、闭合等动作。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.disease import STATUS_ORDER, DiseaseService

router = APIRouter(prefix="/api/disease", tags=["病害记录"])

service = DiseaseService()

LIST_FIELDS = ["病害编号", "所属设施", "病害类型", "严重等级", "发现时间", "所在位置", "处置方案", "病害状态"]
STATUSES = STATUS_ORDER


@router.get("", response_model=PageResult[dict])
def list_entries(
    keyword: str | None = Query(default=None, description="按病害编号检索"),
    status: str | None = Query(default=None, description="待处置、处置中、已闭合"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按病害编号与状态过滤病害记录列表；没有数据时返回空页，不报错。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    if status and status not in STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"病害状态「{status}」不合法，可选：{'、'.join(STATUSES)}",
        )
    items, total = service.list_entries(keyword=keyword, status=status, page=page, size=size)
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/export")
def export_entries() -> dict[str, Any]:
    """导出病害记录清单：返回当前全量数据。"""
    items, total = service.list_entries(page=1, size=10000)
    return {"module": "disease", "total": total, "items": items}


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条病害明细；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"病害 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记一条病害，缺字段或编号重复时说明原因而不是静默丢弃。"""
    entry, errors = service.create_entry(payload.values)
    if errors:
        return ActionResult(ok=False, message="；".join(errors))
    return ActionResult(ok=True, message="病害已登记", entry=entry)


@router.post("/{entry_id}/disposal", response_model=ActionResult)
def save_disposal(entry_id: int, payload: EntryPayload) -> ActionResult:
    """实施处置：严重等级与处置方案只保存到该条病害编号下，并把状态带成处置中。"""
    entry, message = service.save_disposal(entry_id, payload.values)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)


@router.post("/{entry_id}/close", response_model=ActionResult)
def close_entry(entry_id: int) -> ActionResult:
    """闭合病害：所在位置为空会被拦下并说明原因；成功后状态同步为已闭合。"""
    entry, message = service.close_entry(entry_id)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)
