"""病害记录业务规则：严重等级、处置方案与病害状态分开存放、分开口径修改。

关键约束：
- 每条病害编号的严重等级与处置方案只写进自己那条记录，不使用模块级共享状态；
- 实施处置只更新本记录的等级/位置/方案，第一次实施后状态由「待处置」转「处置中」；
- 闭合时所在位置不能为空，状态必须同步为「已闭合」；
- 已闭合病害可查不可改，任何修改/动作都会被拦下并说明原因。
"""
from __future__ import annotations

from typing import Any

from app.store import store

MODULE = "disease"

# 登记时必填；严重等级在登记环节就要落定，避免后续处置时被别的记录串掉。
REQUIRED_FIELDS = ["病害编号", "所属设施", "病害类型", "严重等级"]
EDITABLE_FIELDS = ["严重等级", "所在位置", "处置方案"]

# 病害状态只围绕「登记 -> 处置 -> 闭合」一条主线。
STATUS_PENDING = "待处置"
STATUS_PROCESSING = "处置中"
STATUS_CLOSED = "已闭合"
STATUS_ORDER = [STATUS_PENDING, STATUS_PROCESSING, STATUS_CLOSED]

# 严重等级限定枚举，不允许自由文本，防止列表、详情、弹窗三处口径不一。
SEVERITY_LEVELS = ["轻微", "中等", "严重"]


class DiseaseService:
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = store.rows(MODULE)
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("病害编号", ""))]
        if status:
            rows = [row for row in rows if row.get("病害状态") == status]
        total = len(rows)
        start = max(page - 1, 0) * size
        return rows[start:start + size], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        return store.find(MODULE, entry_id)

    def stats(self) -> dict[str, int]:
        """看板数字与列表同源，避免页面刷新前后对不上。"""
        rows = store.rows(MODULE)
        counts = {label: 0 for label in STATUS_ORDER}
        for row in rows:
            label = row.get("病害状态")
            if label in counts:
                counts[label] += 1
        return counts

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        clean = {field: str(values.get(field) or "").strip() for field in
                 ["病害编号", "所属设施", "病害类型", "严重等级", "发现时间", "所在位置", "处置方案"]}
        missing = [field for field in REQUIRED_FIELDS if not clean[field]]
        if missing:
            return None, missing
        if clean["严重等级"] not in SEVERITY_LEVELS:
            return None, [f"严重等级必须是：{'、'.join(SEVERITY_LEVELS)}"]

        rows = store.rows(MODULE)
        if any(str(row.get("病害编号", "")).strip() == clean["病害编号"] for row in rows):
            return None, [f"病害编号 {clean['病害编号']} 已存在"]

        entry: dict[str, Any] = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry["病害编号"] = clean["病害编号"]
        entry["所属设施"] = clean["所属设施"]
        entry["病害类型"] = clean["病害类型"]
        entry["严重等级"] = clean["严重等级"]
        entry["发现时间"] = clean["发现时间"]
        entry["所在位置"] = clean["所在位置"]
        # 处置方案与等级、状态分开保存：登记时默认空，由「实施处置」单独落值。
        entry["处置方案"] = clean["处置方案"]
        self._apply_status(entry, STATUS_PENDING)
        rows.append(entry)
        return entry, []

    def dispose(self, entry_id: int, values: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        """实施处置：只更新本记录的严重等级、所在位置与处置方案。

        等级与方案各自独立写回当前记录，绝不引用上一条病害的数据。
        """
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"病害 {entry_id} 不存在或已归档"
        closed_msg = self._guard_closed(entry)
        if closed_msg:
            return None, closed_msg

        severity = str(values.get("严重等级") or entry.get("严重等级") or "").strip()
        plan = str(values.get("处置方案") or "").strip()
        location = str(values.get("所在位置", entry.get("所在位置") or "")).strip()

        if severity not in SEVERITY_LEVELS:
            return None, f"严重等级必须是：{'、'.join(SEVERITY_LEVELS)}"
        if not plan:
            return None, "处置方案不能为空，请先填写本病害的处置方案"

        # 三个字段分别落到本条记录上，互不覆盖、不共享。
        entry["严重等级"] = severity
        entry["所在位置"] = location
        entry["处置方案"] = plan
        target = STATUS_PROCESSING if entry["病害状态"] == STATUS_PENDING else entry["病害状态"]
        self._apply_status(entry, target)
        return entry, "处置已实施，方案已保存到本病害记录"

    def close(self, entry_id: int) -> tuple[dict[str, Any] | None, str]:
        """闭合病害：所在位置必须有值，闭合后状态同步为「已闭合」。"""
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"病害 {entry_id} 不存在或已归档"
        closed_msg = self._guard_closed(entry)
        if closed_msg:
            return None, closed_msg
        if not str(entry.get("所在位置") or "").strip():
            return None, "所在位置为空，不允许闭合；请先在处置弹窗补全病害所在位置"

        self._apply_status(entry, STATUS_CLOSED)
        return entry, "病害已闭合，状态已同步为「已闭合」"

    def _guard_closed(self, entry: dict[str, Any]) -> str | None:
        if entry.get("病害状态") == STATUS_CLOSED:
            return "该病害已闭合，只可查看，不能再改动"
        return None

    def _apply_status(self, entry: dict[str, Any], status: str) -> None:
        """状态只允许从一个口径写入：病害状态字段与内部 status/pending 一起同步。"""
        entry["病害状态"] = status
        # status/pending/abnormal 供运营概览聚合使用，必须与业务字段保持一致。
        entry["status"] = status
        entry["pending"] = status != STATUS_CLOSED
        entry["abnormal"] = status != STATUS_CLOSED and entry.get("严重等级") == "严重"
