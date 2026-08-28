# 接口规范对照记录

对照文档：《手绘图纸信息提取功能及前后端接口规范-0825》。

## 已对应

- `POST /api/drawing-extraction/v1/extract`，请求类型 `multipart/form-data`。
- 请求字段：`drawingFiles`、`workbookName`、`language`、`extractionRequirements`。
- 输入格式：JPG/JPEG/PNG/PDF，支持多文件和多页 PDF。
- 同步完成分析、整理和 XLSX 生成。
- 成功响应包含 `resultFileId`、`resultFileName`、`downloadUrl`、`fileType`、
  `sourceFileCount`、`pageCount`、`extractedItemCount`、`reviewItemCount`、`createdAt`。
- 统一响应包含 `requestId`、`success`、`code`、`message`、`data`、`timestamp`。
- `GET /api/drawing-extraction/v1/files/{resultFileId}/download`返回 XLSX 文件流。
- 下载响应使用正确的 XLSX Content-Type 和文件名。
- 保存源文件、分析 JSON、任务元数据和结果 XLSX 之间的关联。
- 保留源文件、页码、来源位置和置信度等信息。
- 不覆盖原始上传文件；同名文件使用唯一前缀保存。
- 低置信度、空值和冲突信息由后端自动复核并保留说明。
- 实现 `DE0101`、`DE0102`、`DE0103`、`DE0201`、`DE0202`、`DE0203`、`DE0301`、`DE0302`、`DE0401`。
  当存在自动复核项时，接口仍返回可下载结果，同时使用 `DE0203` 作为完成但存在不完整内容的业务警告。
- 当前阶段不要求 Token 鉴权。

## 已确认的阶段性偏差

- 规范原则上要求工作表和字段根据图纸内容动态组织。当前按项目阶段要求，
  暂时使用固定工作表，并在「完整结果JSON」中保留全部模型信息，防止丢失。
- `language` 字段仍被接收，但当前阶段按要求固定使用中文。
- 本版使用导管孔混凝土浇筑图专用提示词，尚未扩展为所有图纸类型的动态提示词。

## 交付测试时必须验证

- 使用真实 Qwen3-VL GGUF 服务进行端到端请求。
- 使用 Microsoft Excel 打开、编辑生成的 XLSX。
- 校验模糊图像、旋转图像、多页 PDF、多文件和完全无法识别的输入。
- 核对提取数量、待复核数量、源文件和页码追溯信息。
