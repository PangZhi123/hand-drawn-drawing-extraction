from io import BytesIO

import pytest
from fastapi import UploadFile
from PIL import Image

from app.core.config import Settings
from app.domain.models import ExtractedItem
from app.services.ocr import OCRBackend
from app.services.pipeline import ExtractionPipeline
from app.services.storage import FileStorage


class FakeOCR(OCRBackend):
    def recognize(self, image, source_file, page_number):
        return [ExtractedItem("标注A", 0.95, source_file, page_number)]


@pytest.mark.asyncio
async def test_pipeline_generates_downloadable_xlsx(tmp_path):
    image = Image.new("RGB", (100, 80), "white")
    content = BytesIO()
    image.save(content, format="PNG")
    upload = UploadFile(filename="drawing.png", file=BytesIO(content.getvalue()))
    settings = Settings(data_dir=tmp_path)
    pipeline = ExtractionPipeline(settings, FileStorage(tmp_path), FakeOCR())

    result = await pipeline.run([upload], "测试结果")

    assert result["sourceFileCount"] == 1
    assert result["pageCount"] == 1
    assert result["extractedItemCount"] == 1
    assert (tmp_path / result["resultFileId"] / "result.xlsx").is_file()
