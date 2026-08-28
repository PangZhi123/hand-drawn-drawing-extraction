from copy import deepcopy
from typing import Any


EMPTY_MARKERS = {None, "", "未知", "无法判断", "无法识别", "N/A", "null"}


def _is_empty(value: Any) -> bool:
    return value in EMPTY_MARKERS if not isinstance(value, (dict, list)) else not value


def normalize_and_review(data: dict, confidence_threshold: float) -> dict:
    """后端自动复核：保留原始信息，对低置信度、空值、冲突值和无证据结论降级。"""
    result = deepcopy(data)
    review_log: list[dict] = []

    fixed = result.get("fixed_key_data", [])
    values_by_field: dict[str, set[str]] = {}
    for item in fixed if isinstance(fixed, list) else []:
        if not isinstance(item, dict):
            continue
        field = str(item.get("field_name", "")).strip()
        value = item.get("field_value", "")
        confidence = _to_confidence(item.get("confidence"))
        reasons = []
        if _is_empty(value):
            reasons.append("未识别到可靠值")
        if confidence < confidence_threshold:
            reasons.append(f"置信度{confidence:.2f}低于阈值{confidence_threshold:.2f}")
        if field and not _is_empty(value):
            values_by_field.setdefault(field, set()).add(str(value).strip())
        item["confidence"] = confidence
        item["review_required"] = bool(reasons)
        item["review_status"] = "已自动复核"
        item["review_notes"] = "；".join(reasons) if reasons else "格式、置信度和证据检查通过"
        if reasons:
            review_log.append({"category": "fixed_key_data", "field": field, "value": value, "reasons": reasons})

    conflicts = {field for field, values in values_by_field.items() if len(values) > 1}
    for item in fixed if isinstance(fixed, list) else []:
        if isinstance(item, dict) and item.get("field_name") in conflicts:
            item["review_required"] = True
            item["review_notes"] = (item.get("review_notes", "") + "；同一字段存在多个冲突值").strip("；")

    result["automatic_review"] = {
        "completed": True,
        "confidence_threshold": confidence_threshold,
        "issue_count": len(review_log) + len(conflicts),
        "conflicting_fields": sorted(conflicts),
        "issues": review_log,
    }
    return result


def merge_page_results(results: list[dict]) -> dict:
    """合并多文件/多页结果；不丢弃冲突值，交由自动复核标记。"""
    merged = {
        "fixed_key_data": [],
        "process_analysis": {"导管分析": [], "时间方量分析": [], "关键线段数据": [], "曲线分析": []},
        "additional_observations": [],
        "uncertain_items": [],
        "page_results": results,
    }
    for page in results:
        source = page.get("_source", {})
        for item in page.get("fixed_key_data", []) or []:
            if isinstance(item, dict):
                row = deepcopy(item)
                row.setdefault("source_file", source.get("source_file", ""))
                row.setdefault("page_number", source.get("page_number", ""))
                merged["fixed_key_data"].append(row)
        process = page.get("process_analysis", {}) or {}
        for key in merged["process_analysis"]:
            value = process.get(key)
            if value not in (None, "", [], {}):
                merged["process_analysis"][key].append({"source": source, "content": value})
        merged["additional_observations"].extend(page.get("additional_observations", []) or [])
        merged["uncertain_items"].extend(page.get("uncertain_items", []) or [])
    return merged


def has_meaningful_information(data: dict) -> bool:
    if data.get("fixed_key_data") or data.get("additional_observations"):
        return True
    if data.get("uncertain_items"):
        return True
    return any(bool(value) for value in (data.get("process_analysis") or {}).values())


def count_information_items(data: dict) -> int:
    """统计所有可输出信息，而非只统计固定字段。"""
    count = len(data.get("fixed_key_data", []))
    count += len(data.get("additional_observations", []))
    count += len(data.get("uncertain_items", []))
    for records in (data.get("process_analysis") or {}).values():
        count += _count_leaves(records)
    return count


def _count_leaves(value: Any) -> int:
    if isinstance(value, dict):
        return sum(_count_leaves(child) for child in value.values())
    if isinstance(value, list):
        return sum(_count_leaves(child) for child in value)
    return 0 if _is_empty(value) else 1


def _to_confidence(value: Any) -> float:
    try:
        number = float(value)
        if number > 1:
            number /= 100
        return min(1.0, max(0.0, number))
    except (TypeError, ValueError):
        return 0.0
