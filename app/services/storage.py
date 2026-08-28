import json
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.errors import DrawingError, RESULT_NOT_FOUND


class FileStorage:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def create_result_id(self) -> str:
        return f"drawing_result_{uuid4().hex}"

    def create_job(self, result_id: str) -> Path:
        job = self.root / result_id
        (job / "source").mkdir(parents=True, exist_ok=False)
        return job

    async def save_upload(self, job: Path, upload: UploadFile, content: bytes) -> Path:
        safe_name = Path(upload.filename or "drawing").name
        target = job / "source" / safe_name
        if target.exists():
            target = job / "source" / f"{uuid4().hex[:8]}_{safe_name}"
        target.write_bytes(content)
        return target

    def save_json(self, job: Path, name: str, value: object) -> None:
        (job / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

    def result_path(self, result_id: str) -> Path:
        if not result_id.startswith("drawing_result_") or not result_id.removeprefix("drawing_result_").isalnum():
            raise DrawingError(*RESULT_NOT_FOUND, http_status=404)
        path = (self.root / result_id / "result.xlsx").resolve()
        if self.root not in path.parents or not path.is_file():
            raise DrawingError(*RESULT_NOT_FOUND, http_status=404)
        return path
