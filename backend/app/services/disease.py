"""病害记录业务规则：状态流转、字段校验与筛选口径都收在这里。

关键约束：
- 严重等级、处置方案、病害状态分别落在每条病害编号自己的记录上，
  任何保存动作只按 id 定位并写当前这一条，不允许跨编号带值；
- 实施处置后状态同步为「处置中」，闭合后状态必须同步为「已闭合」；
- 所在位置为空不允许闭合，由后端拦下并返回可读的原因；
- 已闭合的病害只能查看，等级、方案、状态一律不能再改。
"""
from __future__ import annotations

from typing import Any

from app.store import store

MODULE = "disease"
REQUIRED_FIELDS = ["病害编号", "所属设施", "病害类型"]
OPTIONAL_FIELDS = ["发现时间", "所在位置"]
STATUS_ORDER = ["待处置", "处置中", "已闭合"]
PROCESSING_STATUS = "处置中"
CLOSED_STATUS = "已闭合"
SEVERITY_LEVELS = ["轻微", "一般", "严重"]


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
            rows = [row for row in rows if row.get("status") == status]
        total = len(rows)
        start = max(page - 1, 0) * size
        page_rows = [self._present(row) for row in rows[start:start + size]]
        return page_rows, total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        entry = store.find(MODULE, entry_id)
        return self._present(entry) if entry is not None else None

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        errors: list[str] = []
        missing = [
            field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()
        ]
        if missing:
            errors.append(f"缺少必填字段：{'、'.join(missing)}")
        code = str(values.get("病害编号") or "").strip()
        if code and any(str(row.get("病害编号") or "") == code for row in store.rows(MODULE)):
            errors.append(f"病害编号 {code} 已存在，每条病害编号的等级与方案只能登记在自己那条上")
        if errors:
            return None, errors

        rows = store.rows(MODULE)
        entry: dict[str, Any] = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        for field in REQUIRED_FIELDS + OPTIONAL_FIELDS:
            value = values.get(field)
            entry[field] = str(value).strip() if value is not None else ""
        # 新病害尚未定级、尚未给方案，三者分开保存，互不串值
        entry["严重等级"] = ""
        entry["处置方案"] = ""
        entry["status"] = STATUS_ORDER[0]
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)
        return self._present(entry), []

    def save_disposal(
        self, entry_id: int, values: dict[str, Any]
    ) -> tuple[dict[str, Any] | None, str]:
        """实施处置：只把严重等级、处置方案（可补录所在位置）写回该 id 的记录。"""
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"病害 {entry_id} 不存在或已归档"
        if entry.get("status") == CLOSED_STATUS:
            return None, f"病害 {entry.get('病害编号', entry_id)} 已闭合，只能查看，不能再修改等级或处置方案"

        severity = str(values.get("严重等级") or "").strip()
        plan = str(values.get("处置方案") or "").strip()
        location = str(values.get("所在位置") or "").strip()
        if severity not in SEVERITY_LEVELS:
            return None, f"请选择该条病害的严重等级（{'、'.join(SEVERITY_LEVELS)}）"
        if not plan:
            return None, "处置方案不能为空，请先填写该条病害编号下的处置方案"

        # 只更新当前记录自身的字段，不碰其他病害编号
        entry["严重等级"] = severity
        entry["处置方案"] = plan
        if location:
            entry["所在位置"] = location
        entry["status"] = PROCESSING_STATUS
        entry["pending"] = True
        entry["abnormal"] = severity == "严重"
        return self._present(entry), (
            f"病害 {entry.get('病害编号')} 已实施处置，严重等级与处置方案已保存在本编号下"
        )

    def close_entry(self, entry_id: int) -> tuple[dict[str, Any] | None, str]:
        """闭合病害：未处置或所在位置为空都拦下；成功后状态同步为已闭合。"""
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"病害 {entry_id} 不存在或已归档"
        status = entry.get("status")
        if status == CLOSED_STATUS:
            return None, f"病害 {entry.get('病害编号', entry_id)} 已闭合，不能重复闭合或改动"
        if status != PROCESSING_STATUS:
            return None, "该病害尚未实施处置，不能闭合；请先在处置弹窗中保存严重等级与处置方案"
        if not str(entry.get("所在位置") or "").strip():
            return None, (
                f"病害 {entry.get('病害编号')} 的所在位置为空，不允许闭合："
                "请先在处置弹窗中补录所在位置，再执行闭合"
            )

        entry["status"] = CLOSED_STATUS
        entry["pending"] = False
        return self._present(entry), f"病害 {entry.get('病害编号')} 已闭合，病害状态已同步为已闭合"

    def _present(self, entry: dict[str, Any]) -> dict[str, Any]:
        """统一对外口径：病害状态始终取真实 status，列表/详情/弹窗结论一致。"""
        shown = dict(entry)
        shown["病害状态"] = str(entry.get("status") or STATUS_ORDER[0])
        shown.setdefault("严重等级", "")
        shown.setdefault("处置方案", "")
        shown.setdefault("所在位置", "")
        shown.setdefault("发现时间", "")
        return shown
