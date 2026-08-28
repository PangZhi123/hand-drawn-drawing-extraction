from dataclasses import dataclass


@dataclass
class DrawingError(Exception):
    code: str
    message: str
    http_status: int = 400


FILE_MISSING = ("DE0101", "未上传任何图纸文件")
UNSUPPORTED_FORMAT = ("DE0102", "文件格式不支持")
LIMIT_EXCEEDED = ("DE0103", "文件过大或数量超限")
UNREADABLE_IMAGE = ("DE0201", "图像无法解析")
NO_INFORMATION = ("DE0202", "未提取到有效信息")
ANALYSIS_FAILED = ("DE0301", "分析模型失败")
EXCEL_FAILED = ("DE0302", "Excel生成失败")
RESULT_NOT_FOUND = ("DE0401", "结果文件不存在")
