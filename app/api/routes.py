from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse

from app.core.config import Settings, get_settings
from app.services.ocr import TesseractOCRBackend
from app.services.prompt import CONCRETE_POURING_PROMPT
from app.services.qwen_vl import QwenVLAnalyzer
from app.services.pipeline import ExtractionPipeline
from app.services.storage import FileStorage


router = APIRouter(prefix="/api/drawing-extraction/v1")


def get_pipeline(settings: Settings = Depends(get_settings)) -> ExtractionPipeline:
    storage = FileStorage(settings.data_dir)
    if settings.ocr_backend == "qwen_vl":
        analyzer = QwenVLAnalyzer(
            settings.model_base_url, settings.model_api_key, settings.model_name,
            settings.model_timeout_seconds, settings.model_max_tokens, CONCRETE_POURING_PROMPT,
        )
        return ExtractionPipeline(settings, storage, analyzer=analyzer)
    ocr = TesseractOCRBackend(settings.tesseract_cmd, settings.review_confidence)
    return ExtractionPipeline(settings, storage, ocr)


@router.post("/extract")
async def extract(
    drawingFiles: list[UploadFile] | None = File(None),
    workbookName: str | None = Form(None, max_length=128),
    language: str = Form("zh-CN", max_length=16),
    extractionRequirements: str | None = Form(None, max_length=1000),
    pipeline: ExtractionPipeline = Depends(get_pipeline),
):
    del language  # 当前阶段按要求固定为中文
    metadata = await pipeline.run(drawingFiles or [], workbookName, extractionRequirements)
    metadata["downloadUrl"] = f"/api/drawing-extraction/v1/files/{metadata['resultFileId']}/download"
    metadata["fileType"] = "XLSX"
    has_review_items = metadata["reviewItemCount"] > 0
    return {
        "requestId": f"req_{uuid4().hex}",
        "success": True,
        "code": "DE0203" if has_review_items else "0",
        "message": "分析已完成，部分内容已由后端标记自动复核信息" if has_review_items else "success",
        "data": metadata,
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
    }


@router.get("/files/{resultFileId}/download")
def download(resultFileId: str, settings: Settings = Depends(get_settings)):
    storage = FileStorage(settings.data_dir)
    path = storage.result_path(resultFileId)
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=_result_name(path),
    )


def _result_name(path: Path) -> str:
    import json

    metadata_path = path.parent / "metadata.json"
    if metadata_path.is_file():
        return json.loads(metadata_path.read_text(encoding="utf-8"))["resultFileName"]
    return "手绘图纸信息表.xlsx"
