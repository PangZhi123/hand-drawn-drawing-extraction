from datetime import datetime
from pathlib import Path

from fastapi import UploadFile

from app.core.config import Settings
from app.core.errors import (
    ANALYSIS_FAILED,
    DrawingError,
    FILE_MISSING,
    LIMIT_EXCEEDED,
    NO_INFORMATION,
    UNSUPPORTED_FORMAT,
    EXCEL_FAILED,
)
from app.services.excel import build_analysis_workbook, build_workbook
from app.services.ocr import OCRBackend
from app.services.pages import load_pages
from app.services.storage import FileStorage
from app.services.qwen_vl import QwenVLAnalyzer
from app.services.review import (
    count_information_items,
    has_meaningful_information,
    merge_page_results,
    normalize_and_review,
)


ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".pdf"}


class ExtractionPipeline:
    def __init__(self, settings: Settings, storage: FileStorage, ocr: OCRBackend | None = None,
                 analyzer: QwenVLAnalyzer | None = None):
        self.settings = settings
        self.storage = storage
        self.ocr = ocr
        self.analyzer = analyzer

    async def run(self, files: list[UploadFile], workbook_name: str | None,
                  extraction_requirements: str | None = None) -> dict:
        if not files:
            raise DrawingError(*FILE_MISSING)
        if len(files) > self.settings.max_file_count:
            raise DrawingError(*LIMIT_EXCEEDED)
        result_id = self.storage.create_result_id()
        job = self.storage.create_job(result_id)
        all_items = []
        page_results: list[dict] = []
        page_count = 0
        try:
            for upload in files:
                suffix = Path(upload.filename or "").suffix.lower()
                if suffix not in ALLOWED_SUFFIXES:
                    raise DrawingError(*UNSUPPORTED_FORMAT)
                content = await upload.read(self.settings.max_file_size_bytes + 1)
                if len(content) > self.settings.max_file_size_bytes:
                    raise DrawingError(*LIMIT_EXCEEDED)
                saved = await self.storage.save_upload(job, upload, content)
                pages = load_pages(content, suffix)
                page_count += len(pages)
                for number, page in enumerate(pages, 1):
                    if self.analyzer:
                        page_results.append(self.analyzer.analyze(
                            page, saved.name, number, extraction_requirements
                        ))
                    elif self.ocr:
                        all_items.extend(self.ocr.recognize(page, saved.name, number))
            if not all_items and not page_results:
                raise DrawingError(*NO_INFORMATION)
            title = (workbook_name or "手绘图纸信息表").removesuffix(".xlsx")
            if page_results:
                merged = merge_page_results(page_results)
                if not has_meaningful_information(merged):
                    raise DrawingError(*NO_INFORMATION)
                analysis = normalize_and_review(merged, self.settings.review_confidence)
                try:
                    build_analysis_workbook(analysis, job / "result.xlsx", title)
                except Exception as exc:
                    raise DrawingError(*EXCEL_FAILED, http_status=500) from exc
                self.storage.save_json(job, "extraction.json", analysis)
                extracted_count = count_information_items(analysis)
                review_count = analysis.get("automatic_review", {}).get("issue_count", 0)
            else:
                try:
                    build_workbook(all_items, job / "result.xlsx", title)
                except Exception as exc:
                    raise DrawingError(*EXCEL_FAILED, http_status=500) from exc
                self.storage.save_json(job, "extraction.json", [item.to_dict() for item in all_items])
                extracted_count = len(all_items)
                review_count = sum(item.needs_review for item in all_items)
            created_at = datetime.now().astimezone().isoformat(timespec="seconds")
            metadata = {
                "resultFileId": result_id,
                "resultFileName": f"{title}.xlsx",
                "sourceFileCount": len(files),
                "pageCount": page_count,
                "extractedItemCount": extracted_count,
                "reviewItemCount": review_count,
                "createdAt": created_at,
            }
            self.storage.save_json(job, "metadata.json", metadata)
            return metadata
        except DrawingError:
            raise
        except Exception as exc:
            raise DrawingError(*ANALYSIS_FAILED, http_status=500) from exc
