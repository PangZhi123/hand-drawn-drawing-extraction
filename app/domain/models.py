from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class BoundingBox:
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class ExtractedItem:
    text: str
    confidence: float
    source_file: str
    page_number: int
    bbox: BoundingBox | None = None
    needs_review: bool = False

    def to_dict(self) -> dict:
        return asdict(self)
