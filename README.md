# 手绘图纸信息智能提取后端

按《手绘图纸信息提取功能及前后端接口规范-0825》实现的 FastAPI 后端首版。
详细的规范逐项对照和阶段性偏差见 `docs/interface-compliance.md`。

## 功能

- `POST /api/drawing-extraction/v1/extract`：上传 JPG/JPEG/PNG/PDF，同步完成分页、千问视觉分析、自动复核和 XLSX 生成。
- `GET /api/drawing-extraction/v1/files/{resultFileId}/download`：下载生成的 XLSX。
- 保存源文件、结构化中间结果、任务元数据和结果文件的关联。
- 支持多文件、多页 PDF 分析与来源追溯。
- 后端自动复核低置信度、空值和冲突结果，不伪造确定信息。
- 使用固定工作表输出全部分析信息和完整 JSON。

## 千问 GGUF 模型运行

### 1. 模型文件

本项目使用本地 Qwen3-VL GGUF 视觉模型。视觉推理需要同时提供两个文件：

```text
Qwen3VL-30B-A3B-Thinking-Q4_K_M.gguf
mmproj-Qwen3VL-30B-A3B-Thinking-Q8_0.gguf
```

- 主 GGUF 文件包含模型权重。
- `mmproj` 是与该模型配套的视觉投影模型；缺少它时无法分析图片。
- 模型文件不放入本工程，避免大文件参与百度网盘源码同步。

### 2. 安装推理运行时

GGUF 文件不能被 FastAPI 直接调用。测试机器需要安装支持 CUDA 和多模态的新版 `llama.cpp`，并使用其中的 `llama-server.exe` 加载模型。

Windows 环境建议下载 `llama.cpp` 的 CUDA 预编译版。确保解压目录中包含：

```text
llama-server.exe
llama-cli.exe
相应的 CUDA DLL
```

可先执行以下命令检查可执行文件：

```powershell
llama-server.exe --version
llama-server.exe --help
```

### 3. 启动千问视觉模型服务

以当前模型目录为例：

```powershell
llama-server.exe `
  --model "E:\QwenModels\Qwen3-VL-30B-A3B-Thinking-GGUF\Qwen3VL-30B-A3B-Thinking-Q4_K_M.gguf" `
  --mmproj "E:\QwenModels\Qwen3-VL-30B-A3B-Thinking-GGUF\mmproj-Qwen3VL-30B-A3B-Thinking-Q8_0.gguf" `
  --alias qwen3-vl-30b-a3b-thinking `
  --host 127.0.0.1 `
  --port 8080 `
  --ctx-size 8192 `
  --parallel 1 `
  --jinja `
  --reasoning on `
  --n-gpu-layers 20
```

参数说明：

- `--model`：主 GGUF 模型路径。
- `--mmproj`：与主模型配套的视觉投影文件。
- `--alias`：后端请求中使用的模型名称，必须与 `.env` 一致。
- `--ctx-size`：上下文长度。较大数值会增加内存和显存使用。
- `--parallel 1`：当前阶段串行处理，避免多并发占用过多内存。
- `--n-gpu-layers`：卸载到 GPU 的模型层数。显存不足时降低，有余量时可逐步提高。

RTX 3060 Ti 8 GB 显存无法完全装入约 18.6 GB 的主模型，因此需要 GPU 和系统内存混合运行。`20` 只是初始测试值；若出现 CUDA 显存不足，可依次尝试 `16`、`12`、`8` 或 `0`。

启动成功后，可访问：

```text
http://127.0.0.1:8080
http://127.0.0.1:8080/v1/models
```

### 4. 配置后端

复制配置样例：

```powershell
Copy-Item .env.example .env
```

`.env` 中的模型配置：

```env
DRAWING_OCR_BACKEND=qwen_vl
DRAWING_MODEL_BASE_URL=http://127.0.0.1:8080/v1
DRAWING_MODEL_NAME=qwen3-vl-30b-a3b-thinking
DRAWING_MODEL_API_KEY=local
DRAWING_MODEL_TIMEOUT_SECONDS=600
DRAWING_MODEL_MAX_TOKENS=8192
DRAWING_REVIEW_CONFIDENCE=0.70
```

`llama-server` 本地测试默认不需要真实 API Key，但 OpenAI 兼容客户端需要一个非空字符串，因此使用 `local`。

### 5. 启动后端

建议在本机非同步目录中使用已有 Python 环境，不要在本工程中创建 `.venv`。

```powershell
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

`requirements.txt` 包含全部运行时 Python 依赖。如果同时需要运行自动化测试，可安装完整开发环境：

```powershell
pip install -r requirements-all.txt
```

注意：需要先启动 `llama-server`，再启动 FastAPI 后端。

### 6. 接口测试

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/drawing-extraction/v1/extract" `
  -F "drawingFiles=@test-data\test-1.png" `
  -F "workbookName=手绘图纸信息表" `
  -F "extractionRequirements=提取图纸中的所有关键信息"
```

成功响应会返回 `resultFileId` 和 `downloadUrl`。然后可通过下载接口获取 XLSX。
工程已在 `test-data/test-1.png` 内附带一张《导管孔混凝土浇筑指示图》测试样本。

### 7. 常见问题

#### 后端连接被拒绝

检查 `llama-server` 是否已启动，以及 `.env` 中的端口是否与启动命令一致。

#### 提示不支持图片

检查启动命令是否包含 `--mmproj`，以及 `mmproj` 是否与主模型配套。

#### CUDA out of memory

降低 `--n-gpu-layers`、`--ctx-size` 或图片分辨率，关闭其他占用显存的程序。

#### 系统内存不足

关闭其他大型程序，确保 Windows 页面文件未被禁用。内存不足时可能加载失败或推理非常缓慢。

#### 返回内容不是标准 JSON

后端会尝试修复 JSON，并将不可靠内容加入自动复核结果。如果完全无法解析，应保留模型日志和输入样本进行调试。

## 测试

```powershell
pytest
```

## 目录

```text
app/
  api/          # HTTP 路由与响应契约
  core/         # 配置、异常、日志
  domain/       # 领域模型
  services/     # 分页、OCR、结构化、Excel、存储及流水线
tests/          # 契约与核心逻辑测试
runtime-data/   # 运行数据（已忽略，不同步）
```
