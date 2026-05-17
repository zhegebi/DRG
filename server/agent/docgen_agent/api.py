"""docgen_agent 前端接口。

POST /api/agent/generate-doc      — 生成文档（支持上传 txt/md 需求文件）
GET  /api/agent/doc-types         — 获取支持的文档类型列表
"""

import shutil
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from loguru import logger
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from .tools import OUTPUT_DIR
from .workflow import (
    GenerationInterrupted,
    GenerationTerminated,
    append_generation_hint,
    get_generation_trace,
    request_generation_interrupt,
    request_generation_terminate,
    run_agent,
    start_generation_trace,
)

router = APIRouter(prefix="/api/docgen_agent")

DocType = Literal["需求规格说明书", "架构设计文档", "测试文档"]

UPLOAD_DIR = Path(tempfile.gettempdir()) / "drg_docgen_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".txt", ".md"}


class GenerateDocResponse(BaseModel):
    status: str
    run_id: str
    file_name: str = ""
    file_path: str = ""
    doc_type: str


class StartGenerateDocResponse(BaseModel):
    status: str
    run_id: str
    doc_type: str


class AgentTraceResponse(BaseModel):
    run_id: str
    status: str
    doc_type: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    output_path: Optional[str] = None
    error: Optional[str] = None
    interrupted: bool = False
    terminated: bool = False
    events: list[dict[str, Any]] = Field(default_factory=list)


class InterruptResponse(BaseModel):
    status: str
    run_id: str


class TerminateResponse(BaseModel):
    status: str
    run_id: str


class AppendHintResponse(BaseModel):
    status: str
    run_id: str


def _safe_output_path(path_text: str) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = Path.cwd() / path
    path = path.resolve()
    try:
        path.relative_to(OUTPUT_DIR.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="文件不在文档输出目录内") from exc
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail=f"文件不存在: {path.name}")
    return path


def _save_uploaded_source_file(source_file: Optional[UploadFile]) -> Optional[str]:
    """保存前端上传的需求文件，返回本地路径。"""
    if source_file is None or not source_file.filename:
        return None

    original_name = Path(source_file.filename).name
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {ext}，仅支持 {', '.join(ALLOWED_EXTENSIONS)}",
        )

    safe_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{original_name}"
    dest = UPLOAD_DIR / safe_name
    with open(dest, "wb") as f:
        shutil.copyfileobj(source_file.file, f)
    logger.info(f"收到上传文件: {dest}")
    return str(dest)


def _run_agent_background(run_id: str, doc_type: DocType, prompt: str, source_path: Optional[str]) -> None:
    try:
        run_agent(
            doc_type=doc_type,
            user_hint=prompt,
            source_file=source_path,
            run_id=run_id,
        )
    except GenerationTerminated:
        logger.info(f"后台文档生成已终止: {run_id}")
    except GenerationInterrupted:
        logger.info(f"后台文档生成已中断: {run_id}")
    except Exception as e:
        logger.exception(f"后台文档生成失败: {run_id}: {e}")


@router.post(
    "/generate-doc",
    response_model=GenerateDocResponse,
    responses={
        200: {"description": "文档生成成功"},
        400: {"description": "参数错误"},
        500: {"description": "LLM 调用失败"},
    },
)
async def generate_doc(
    prompt: str = Form(default="", description="前端用户的提示词"),
    doc_type: DocType = Form(default="需求规格说明书", description="目标文档类型"),
    source_file: Optional[UploadFile] = File(default=None, description="需求文件（txt/md）"),
    run_id: Optional[str] = Form(default=None, description="运行 ID；前端可自生成后用于轮询 trace 或中断"),
) -> GenerateDocResponse:
    """生成技术文档。

    接收前端提示词 + 可选的需求文件，按 doc_type 生成 Markdown 文档。
    若未上传 source_file，默认使用 requirement.md。
    """
    source_path = _save_uploaded_source_file(source_file)
    run_id = run_id or uuid.uuid4().hex
    start_generation_trace(run_id, doc_type=doc_type, user_hint=prompt, reset=True)

    try:
        output_path = await run_in_threadpool(
            run_agent,
            doc_type=doc_type,
            user_hint=prompt,
            source_file=source_path,
            run_id=run_id,
        )
        return GenerateDocResponse(
            status="success",
            run_id=run_id,
            file_name=output_path.name,
            file_path=str(output_path),
            doc_type=doc_type,
        )
    except GenerationTerminated:
        return GenerateDocResponse(
            status="terminated",
            run_id=run_id,
            doc_type=doc_type,
        )
    except GenerationInterrupted:
        return GenerateDocResponse(
            status="interrupted",
            run_id=run_id,
            doc_type=doc_type,
        )
    except Exception as e:
        logger.exception(f"文档生成失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-doc/start", response_model=StartGenerateDocResponse)
async def start_generate_doc(
    background_tasks: BackgroundTasks,
    prompt: str = Form(default="", description="前端用户的提示词"),
    doc_type: DocType = Form(default="需求规格说明书", description="目标文档类型"),
    source_file: Optional[UploadFile] = File(default=None, description="需求文件（txt/md）"),
    run_id: Optional[str] = Form(default=None, description="运行 ID；不传则后端生成"),
) -> StartGenerateDocResponse:
    """启动后台生成任务，立即返回 run_id，前端可用 trace/interrupt 接口轮询和中断。"""
    source_path = _save_uploaded_source_file(source_file)
    run_id = run_id or uuid.uuid4().hex
    start_generation_trace(run_id, doc_type=doc_type, user_hint=prompt, reset=True)
    background_tasks.add_task(_run_agent_background, run_id, doc_type, prompt, source_path)
    return StartGenerateDocResponse(status="started", run_id=run_id, doc_type=doc_type)


@router.get("/runs/{run_id}/trace", response_model=AgentTraceResponse)
async def read_generation_trace(run_id: str) -> AgentTraceResponse:
    """读取智能体生成过程，包含阶段、模型输出、reasoning_content、工具调用和工具结果摘要。"""
    trace = get_generation_trace(run_id)
    if trace is None:
        raise HTTPException(status_code=404, detail=f"运行不存在: {run_id}")
    return AgentTraceResponse(**trace)


@router.post("/runs/{run_id}/interrupt", response_model=InterruptResponse)
async def interrupt_generation(run_id: str) -> InterruptResponse:
    """请求中断指定文档生成任务。"""
    ok = request_generation_interrupt(run_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"运行不存在: {run_id}")
    return InterruptResponse(status="interrupt_requested", run_id=run_id)


@router.post("/runs/{run_id}/terminate", response_model=TerminateResponse)
async def terminate_generation(run_id: str) -> TerminateResponse:
    """请求终止指定文档生成任务。"""
    ok = request_generation_terminate(run_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"运行不存在: {run_id}")
    return TerminateResponse(status="terminate_requested", run_id=run_id)


@router.get("/runs/{run_id}/download")
async def download_generation_result(run_id: str) -> FileResponse:
    """下载指定运行最终生成的 Markdown 文档。"""
    trace = get_generation_trace(run_id)
    if trace is None:
        raise HTTPException(status_code=404, detail=f"运行不存在: {run_id}")
    output_path = trace.get("output_path")
    if not output_path:
        raise HTTPException(status_code=409, detail="文档尚未生成完成")
    path = _safe_output_path(str(output_path))
    return FileResponse(
        path,
        filename=path.name,
        media_type="text/markdown; charset=utf-8",
    )


@router.get("/documents/{file_name}/download")
async def download_document(file_name: str) -> FileResponse:
    """按文件名下载 output_docs 目录中的文档。"""
    path = _safe_output_path(str(OUTPUT_DIR / Path(file_name).name))
    return FileResponse(
        path,
        filename=path.name,
        media_type="application/octet-stream",
    )


@router.post("/runs/{run_id}/hint", response_model=AppendHintResponse)
async def append_hint(
    run_id: str,
    hint: str = Form(..., description="追加的提示词或指导内容"),
    source_file: Optional[UploadFile] = File(default=None, description="追加的参考文件"),
) -> AppendHintResponse:
    """在文档生成运行中追加用户提示词，下一轮 LLM 调用时会作为 user 消息注入。"""
    if source_file and source_file.filename:
        source_path = _save_uploaded_source_file(source_file)
        with open(source_path, encoding="utf-8") as f:
            file_content = f.read()
        hint = f"{hint}\n\n[上传文件 {source_file.filename} 的内容]:\n{file_content[:3000]}"
    ok = append_generation_hint(run_id, hint)
    if not ok:
        raise HTTPException(status_code=404, detail=f"运行不存在或已结束: {run_id}")
    return AppendHintResponse(status="hint_appended", run_id=run_id)


@router.get("/runs/{run_id}/download/pdf")
async def download_generation_pdf(run_id: str) -> FileResponse:
    """下载指定运行生成的 PDF 文档。"""
    trace = get_generation_trace(run_id)
    if trace is None:
        raise HTTPException(status_code=404, detail=f"运行不存在: {run_id}")
    md_path = trace.get("output_path")
    if not md_path:
        raise HTTPException(status_code=409, detail="文档尚未生成完成")
    pdf_path = Path(str(md_path)).with_suffix(".pdf")
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF 文件不存在，请确认转换已完成")
    return FileResponse(
        pdf_path,
        filename=pdf_path.name,
        media_type="application/pdf",
    )


@router.get("/doc-types")
async def list_doc_types() -> list[str]:
    """返回支持的文档类型。"""
    return ["需求规格说明书", "架构设计文档", "测试文档"]
