from datetime import datetime
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from app.api.routes import router
from app.core.config import get_settings
from app.core.errors import DrawingError


app = FastAPI(title=get_settings().app_name, version="0.1.1")
app.include_router(router)


@app.exception_handler(DrawingError)
async def drawing_error_handler(request: Request, exc: DrawingError):
    del request
    return JSONResponse(
        status_code=exc.http_status,
        content={
            "requestId": f"req_{uuid4().hex}",
            "success": False,
            "code": exc.code,
            "message": exc.message,
            "data": None,
            "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    del request
    details = exc.errors()
    return JSONResponse(
        status_code=400,
        content={
            "requestId": f"req_{uuid4().hex}",
            "success": False,
            "code": "DE0103",
            "message": "请求字段长度、格式或数量不符合要求",
            "data": {"validationErrors": jsonable_encoder(details)},
            "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        },
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
