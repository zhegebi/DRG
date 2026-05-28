"""docgen_agent task API."""

import asyncio
import json
import re
import shutil
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from loguru import logger
from pydantic import BaseModel, Field
from sqlmodel import delete, select
from sqlmodel.ext.asyncio.session import AsyncSession

import server.db
from server.db.utils import get_async_session
from server.knowledge_base.table import Category, Document
from server.user.auth import get_current_user
from server.user.table import User

from .table import DocgenTask
from .tools import OUTPUT_DIR, client
from .workflow import (
    GenerationTerminated,
    DEFAULT_GENERATION_MODE,
    GenerationMode,
    get_generation_trace,
    normalize_generation_mode,
    request_generation_terminate,
    run_agent,
    start_generation_trace,
)

router = APIRouter(prefix="/api/docgen_agent")

DocType = Literal["需求规格说明书", "架构设计文档", "测试文档"]

UPLOAD_DIR = Path(tempfile.gettempdir()) / "drg_docgen_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".txt", ".md"}
_TERMINAL_STATUSES = {"completed", "failed", "terminated"}


class StartDocgenTaskResponse(BaseModel):
    status: str
    task_id: str
    doc_type: str
    task_title: str = ""
    generation_mode: str = DEFAULT_GENERATION_MODE


class DocgenTaskStatusResponse(BaseModel):
    task_id: str
    task_status: str


class DocgenTaskTraceResponse(BaseModel):
    task_id: str
    status: str
    doc_type: str = ""
    task_title: str = ""
    generation_mode: str = DEFAULT_GENERATION_MODE
    document_id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    output_path: Optional[str] = None
    pdf_path: Optional[str] = None
    error: Optional[str] = None
    terminated: bool = False
    events: list[dict[str, Any]] = Field(default_factory=list)


class TerminateResponse(BaseModel):
    status: str
    task_id: str


def _normalize_trace_payload(
    task_id: str,
    trace: dict[str, Any],
    row: Optional[DocgenTask] = None,
) -> dict[str, Any]:
    payload = dict(trace)
    payload.pop("run_id", None)
    payload["task_id"] = task_id
    if row is not None:
        payload.setdefault("doc_type", row.doc_type)
        payload.setdefault("task_title", row.name)
        payload.setdefault("generation_mode", DEFAULT_GENERATION_MODE)
        payload.setdefault("document_id", row.document_id)
        payload.setdefault("created_at", row.created_at.isoformat(timespec="seconds"))
        payload.setdefault("updated_at", row.updated_at.isoformat(timespec="seconds"))
        if not payload.get("output_path"):
            payload["output_path"] = row.output_path
        if not payload.get("pdf_path"):
            payload["pdf_path"] = row.pdf_path
        if not payload.get("error"):
            payload["error"] = row.error
    payload["terminated"] = payload.get("status") in {"terminate_requested", "terminated"}
    payload["generation_mode"] = normalize_generation_mode(str(payload.get("generation_mode") or DEFAULT_GENERATION_MODE))
    payload.setdefault("events", [])
    return payload


def _trace_payload_from_db(row: DocgenTask) -> dict[str, Any]:
    trace = row.trace if isinstance(row.trace, dict) else {}
    return _normalize_trace_payload(
        row.task_id,
        {
            "status": row.status,
            "doc_type": row.doc_type,
            "task_title": row.name,
            "generation_mode": trace.get("generation_mode", DEFAULT_GENERATION_MODE),
            "document_id": row.document_id,
            "created_at": row.created_at.isoformat(timespec="seconds"),
            "updated_at": row.updated_at.isoformat(timespec="seconds"),
            "output_path": row.output_path or trace.get("output_path"),
            "pdf_path": row.pdf_path or trace.get("pdf_path"),
            "error": row.error or trace.get("error"),
            "events": trace.get("events", []),
        },
        row,
    )


async def _create_docgen_task_record(
    db_client: AsyncSession,
    *,
    task_id: str,
    user_id: Optional[int],
    doc_type: str,
    prompt: str,
    source_paths: list[str],
    task_title: str,
    initial_trace: dict[str, Any],
) -> None:
    row = DocgenTask(
        task_id=task_id,
        user_id=user_id,
        name=task_title,
        doc_type=doc_type,
        user_input=prompt,
        source_files=[Path(path).name for path in source_paths],
        status="running",
        trace=_normalize_trace_payload(task_id, initial_trace),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_client.add(row)
    await db_client.commit()


def _generated_markdown_path(path_text: Optional[str]) -> Optional[Path]:
    if not path_text:
        return None
    path = Path(path_text)
    if not path.is_absolute():
        path = Path.cwd() / path
    try:
        path = path.resolve()
        path.relative_to(OUTPUT_DIR.resolve())
    except (OSError, ValueError):
        logger.warning(f"Skip storing generated document outside output dir: {path_text}")
        return None
    if path.suffix.lower() == ".pdf":
        path = path.with_suffix(".md")
    if path.suffix.lower() != ".md" or not path.exists() or not path.is_file():
        logger.warning(f"Skip storing missing generated markdown: {path}")
        return None
    return path


def _generated_document_payload(row: DocgenTask) -> Optional[tuple[str, str, Category]]:
    title = (row.name or row.doc_type or row.task_id).strip()
    category = _doc_type_to_category(row.doc_type)
    trace = row.trace if isinstance(row.trace, dict) else {}
    content = trace.get("document_content")
    if isinstance(content, str) and content.strip():
        return title, content.strip(), category
    path = _generated_markdown_path(row.output_path)
    if path is None:
        return None
    content = path.read_text(encoding="utf-8")
    if not content.strip():
        logger.warning(f"Skip storing empty generated markdown: {path}")
        return None
    return title, content, category


async def _store_generated_document_async(db_client: AsyncSession, task_id: str) -> None:
    try:
        row = await db_client.get(DocgenTask, task_id)
        if row is None or row.status != "completed":
            return
        payload = _generated_document_payload(row)
        if payload is None:
            return
        title, content, category = payload
        document = await db_client.get(Document, row.document_id) if row.document_id else None
        if document is None:
            document = Document(title=title, content=content, category=category)
            db_client.add(document)
            await db_client.flush()
            row.document_id = document.id
        else:
            document.title = title
            document.content = content
            document.category = category
        row.updated_at = datetime.now()
        db_client.add(document)
        db_client.add(row)
        await db_client.commit()
    except Exception as exc:
        await db_client.rollback()
        logger.exception(f"cannot add docgen document, error: {exc}")


def _store_generated_document_sync(session, task_id: str) -> None:
    try:
        row = session.get(DocgenTask, task_id)
        if row is None or row.status != "completed":
            return
        payload = _generated_document_payload(row)
        if payload is None:
            return
        title, content, category = payload
        document = session.get(Document, row.document_id) if row.document_id else None
        if document is None:
            document = Document(title=title, content=content, category=category)
            session.add(document)
            session.flush()
            row.document_id = document.id
        else:
            document.title = title
            document.content = content
            document.category = category
        row.updated_at = datetime.now()
        session.add(document)
        session.add(row)
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.exception(f"cannot add docgen document, error: {exc}")


async def _persist_trace_async(db_client: AsyncSession, task_id: str) -> None:
    trace = get_generation_trace(task_id)
    if trace is None:
        return
    row = await db_client.get(DocgenTask, task_id)
    if row is None:
        return
    payload = _normalize_trace_payload(task_id, trace, row)
    row.status = str(payload.get("status") or row.status)
    row.name = str(payload.get("task_title") or row.name)
    row.output_path = payload.get("output_path") or row.output_path
    row.pdf_path = payload.get("pdf_path") or row.pdf_path
    row.error = payload.get("error") or None
    row.trace = payload
    row.updated_at = datetime.now()
    db_client.add(row)
    await db_client.commit()
    await _store_generated_document_async(db_client, task_id)


def _persist_trace_sync(task_id: str) -> None:
    trace = get_generation_trace(task_id)
    if trace is None or server.db.sync_engine is None:
        return
    from sqlmodel import Session

    with Session(server.db.sync_engine) as session:
        row = session.get(DocgenTask, task_id)
        if row is None:
            return
        payload = _normalize_trace_payload(task_id, trace, row)
        row.status = str(payload.get("status") or row.status)
        row.name = str(payload.get("task_title") or row.name)
        row.output_path = payload.get("output_path") or row.output_path
        row.pdf_path = payload.get("pdf_path") or row.pdf_path
        row.error = payload.get("error") or None
        row.trace = payload
        row.updated_at = datetime.now()
        session.add(row)
        session.commit()
        _store_generated_document_sync(session, task_id)


def _display_title(title: str) -> str:
    title = re.sub(r"[#*_`\"'“”‘’《》]+", "", title).strip()
    title = re.sub(r"\s+", "", title)
    return title or "文档生成任务"


def _fallback_task_title(doc_type: str, prompt: str, source_paths: list[str]) -> str:
    if prompt.strip():
        words = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]+", prompt)
        title = "".join(words)[:16]
        return _display_title(title)
    if source_paths:
        return _display_title(Path(source_paths[0]).stem.split("_", 2)[-1])
    return _display_title(doc_type)


def _generate_task_title(doc_type: str, prompt: str, source_paths: list[str]) -> str:
    fallback = _fallback_task_title(doc_type, prompt, source_paths)
    try:
        file_names = "、".join(Path(path).name for path in source_paths[:3]) or "无"
        resp = client.chat.completions.create(
            model="deepseek-v4-pro",
            messages=[
                {
                    "role": "system",
                    "content": "你是任务命名助手。为文档生成任务生成一个中文短标题，只输出标题本身，不要解释，不要标点，尽量不超过10个汉字。",
                },
                {
                    "role": "user",
                    "content": f"文档类型：{doc_type}\n用户提示：{prompt[:300] or '无'}\n上传文件：{file_names}",
                },
            ],
            temperature=0.2,
        )
        title = _display_title(resp.choices[0].message.content or "")
        return title or fallback
    except Exception as exc:
        logger.warning(f"生成任务标题失败，使用兜底标题: {exc}")
        return fallback


def _doc_type_to_category(doc_type: str) -> Category:
    mapping = {
        "需求规格说明书": Category.REQUIREMENT,
        "架构设计文档": Category.ARC,
        "测试文档": Category.TEST_CASE_DOC,
    }
    return mapping.get(doc_type, Category.ANY)


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


def _save_one_uploaded_source_file(source_file: UploadFile) -> str:
    original_name = Path(source_file.filename or "uploaded.md").name
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {ext}，仅支持 {', '.join(ALLOWED_EXTENSIONS)}",
        )

    safe_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{original_name}"
    dest = UPLOAD_DIR / safe_name
    with open(dest, "wb") as f:
        shutil.copyfileobj(source_file.file, f)
    logger.info(f"收到上传文件: {dest}")
    return str(dest)


def _save_uploaded_source_files(
    source_file: Optional[UploadFile] = None,
    source_files: Optional[list[UploadFile]] = None,
) -> list[str]:
    saved: list[str] = []
    if source_file is not None and source_file.filename:
        saved.append(_save_one_uploaded_source_file(source_file))
    for file in source_files or []:
        if file is not None and file.filename:
            saved.append(_save_one_uploaded_source_file(file))
    return saved


def _run_agent_background(
    task_id: str,
    doc_type: DocType,
    prompt: str,
    source_paths: list[str],
    generation_mode: GenerationMode = DEFAULT_GENERATION_MODE,
) -> None:
    try:
        run_agent(
            doc_type=doc_type,
            user_hint=prompt,
            source_files=source_paths,
            run_id=task_id,
            generation_mode=generation_mode,
        )
    except GenerationTerminated:
        logger.info(f"后台文档生成已终止: {task_id}")
    except Exception as e:
        logger.exception(f"后台文档生成失败: {task_id}: {e}")
    finally:
        _persist_trace_sync(task_id)


@router.post("/task/create", response_model=StartDocgenTaskResponse)
async def create_task(
    background_tasks: BackgroundTasks,
    prompt: str = Form(default="", description="前端用户的提示词"),
    doc_type: DocType = Form(default="需求规格说明书", description="目标文档类型"),
    generation_mode: GenerationMode = Form(default=DEFAULT_GENERATION_MODE, description="生成模式"),
    source_file: Optional[UploadFile] = File(default=None, description="需求文件（txt/md），兼容旧字段"),
    source_files: Optional[list[UploadFile]] = File(default=None, description="需求/依赖文件列表（txt/md）"),
    task_id: Optional[str] = Form(default=None, description="任务 ID；不传则后端生成"),
    current_user: User = Depends(get_current_user),
    db_client: AsyncSession = Depends(get_async_session),
) -> StartDocgenTaskResponse:
    """创建后台文档生成任务，立即返回 task_id。"""
    source_paths = _save_uploaded_source_files(source_file, source_files)
    task_id = task_id or uuid.uuid4().hex
    task_title = _generate_task_title(doc_type, prompt, source_paths)
    assert current_user.id is not None, "current_user.id is None"
    generation_mode = normalize_generation_mode(generation_mode)
    initial_trace = start_generation_trace(
        task_id,
        doc_type=doc_type,
        user_hint=prompt,
        task_title=task_title,
        generation_mode=generation_mode,
        reset=True,
    )
    await _create_docgen_task_record(
        db_client,
        task_id=task_id,
        user_id=current_user.id,
        doc_type=doc_type,
        prompt=prompt,
        source_paths=source_paths,
        task_title=task_title,
        initial_trace=initial_trace,
    )
    background_tasks.add_task(_run_agent_background, task_id, doc_type, prompt, source_paths, generation_mode)
    return StartDocgenTaskResponse(
        status="started",
        task_id=task_id,
        doc_type=doc_type,
        task_title=task_title,
        generation_mode=generation_mode,
    )


@router.get("/task/list", response_model=list[DocgenTaskTraceResponse])
async def get_task_list(
    current_user: User = Depends(get_current_user),
    db_client: AsyncSession = Depends(get_async_session),
) -> list[DocgenTaskTraceResponse]:
    """读取当前用户的文档生成任务列表。"""
    stmt = (
        select(DocgenTask)
        .where(DocgenTask.user_id == current_user.id)
        .order_by(DocgenTask.created_at.desc())  # type: ignore
    )
    result = await db_client.exec(stmt)
    return [DocgenTaskTraceResponse(**_trace_payload_from_db(row)) for row in result.all()]


@router.get("/task/status", response_model=list[DocgenTaskStatusResponse])
async def get_task_status(
    task_ids: list[str] = Query(..., description="The task ids to get status"),
    db_client: AsyncSession = Depends(get_async_session),
) -> list[DocgenTaskStatusResponse]:
    query_result = await db_client.exec(
        select(DocgenTask.task_id, DocgenTask.status).where(DocgenTask.task_id.in_(task_ids))  # type: ignore
    )
    return [DocgenTaskStatusResponse(task_id=row[0], task_status=row[1]) for row in query_result.all()]


@router.get("/task/{task_id}/trace", response_model=DocgenTaskTraceResponse)
async def read_task_trace(
    task_id: str,
    db_client: AsyncSession = Depends(get_async_session),
) -> DocgenTaskTraceResponse:
    """读取文档生成任务过程，包含阶段、模型输出、工具调用和工具结果摘要。"""
    trace = get_generation_trace(task_id)
    row = await db_client.get(DocgenTask, task_id)
    if trace is None and row is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    if trace is not None:
        if row is not None:
            await _persist_trace_async(db_client, task_id)
            row = await db_client.get(DocgenTask, task_id)
        return DocgenTaskTraceResponse(**_normalize_trace_payload(task_id, trace, row))
    if row is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    return DocgenTaskTraceResponse(**_trace_payload_from_db(row))


@router.get("/task/{task_id}/trace/stream")
async def stream_task_trace(
    task_id: str,
    db_client: AsyncSession = Depends(get_async_session),
) -> StreamingResponse:
    """以 SSE 方式持续推送 trace 快照，用于前端即时显示思考和工具调用。"""
    if get_generation_trace(task_id) is None and await db_client.get(DocgenTask, task_id) is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

    async def event_generator():
        last_signature = ""
        while True:
            trace = get_generation_trace(task_id)
            if trace is None:
                row = await db_client.get(DocgenTask, task_id)
                if row is None:
                    yield 'data: {"error":"任务不存在"}\n\n'
                    yield "data: [END]\n\n"
                    return
                yield f"data: {json.dumps(_trace_payload_from_db(row), ensure_ascii=False)}\n\n"
                yield "data: [END]\n\n"
                return

            payload = _normalize_trace_payload(task_id, trace)
            signature = json.dumps(
                {
                    "status": payload.get("status"),
                    "updated_at": payload.get("updated_at"),
                    "event_count": len(payload.get("events", [])),
                    "last_event": payload.get("events", [])[-1] if payload.get("events") else None,
                    "output_path": payload.get("output_path"),
                    "pdf_path": payload.get("pdf_path"),
                    "error": payload.get("error"),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            if signature != last_signature:
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                last_signature = signature

            if payload.get("status") in _TERMINAL_STATUSES:
                yield "data: [END]\n\n"
                return

            await asyncio.sleep(0.2)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/task/{task_id}/terminate", response_model=TerminateResponse)
async def terminate_task(
    task_id: str,
    db_client: AsyncSession = Depends(get_async_session),
) -> TerminateResponse:
    """请求协作式终止指定文档生成任务。"""
    row = await db_client.get(DocgenTask, task_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    ok = request_generation_terminate(task_id)
    if not ok:
        if row.status in _TERMINAL_STATUSES:
            return TerminateResponse(status=row.status, task_id=task_id)
        raise HTTPException(status_code=409, detail="任务不在当前进程中运行，无法终止")
    await _persist_trace_async(db_client, task_id)
    return TerminateResponse(status="terminate_requested", task_id=task_id)


@router.get("/task/{task_id}/download")
async def download_task_result(
    task_id: str,
    db_client: AsyncSession = Depends(get_async_session),
) -> FileResponse:
    """下载指定任务最终生成的 Markdown 文档。"""
    trace = get_generation_trace(task_id)
    row = await db_client.get(DocgenTask, task_id)
    payload = _normalize_trace_payload(task_id, trace, row) if trace else (_trace_payload_from_db(row) if row else None)
    if payload is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    output_path = payload.get("output_path")
    if not output_path:
        raise HTTPException(status_code=409, detail="文档尚未生成完成")
    path = _safe_output_path(str(output_path))
    if path.suffix.lower() == ".pdf":
        path = _safe_output_path(str(path.with_suffix(".md")))
    return FileResponse(
        path,
        filename=path.name,
        media_type="text/markdown; charset=utf-8",
    )


@router.get("/task/{task_id}/download/pdf")
async def download_task_pdf(
    task_id: str,
    db_client: AsyncSession = Depends(get_async_session),
) -> FileResponse:
    """下载指定任务生成的 PDF 文档。"""
    trace = get_generation_trace(task_id)
    row = await db_client.get(DocgenTask, task_id)
    payload = _normalize_trace_payload(task_id, trace, row) if trace else (_trace_payload_from_db(row) if row else None)
    if payload is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    pdf_path = payload.get("pdf_path")
    md_path = payload.get("output_path")
    if not pdf_path and not md_path:
        raise HTTPException(status_code=409, detail="文档尚未生成完成")
    path = _safe_output_path(str(pdf_path or Path(str(md_path)).with_suffix(".pdf")))
    if path.suffix.lower() != ".pdf":
        raise HTTPException(status_code=404, detail="PDF 文件不存在，请确认转换已完成")
    return FileResponse(
        path,
        filename=path.name,
        media_type="application/pdf",
    )


@router.delete("/task/{task_id}")
async def delete_task(
    task_id: str,
    db_client: AsyncSession = Depends(get_async_session),
) -> bool:
    """删除已结束的文档生成任务。运行中的任务不能删除。"""
    row = await db_client.get(DocgenTask, task_id)
    if row is None:
        return True
    if row.status not in _TERMINAL_STATUSES:
        return False
    await db_client.exec(delete(DocgenTask).where(DocgenTask.task_id == task_id))  # type: ignore
    await db_client.commit()
    return True


@router.get("/documents/{file_name:path}/download")
async def download_document(file_name: str) -> FileResponse:
    """按文件名下载 output_docs 目录中的文档或图片。支持子目录路径，如 diagrams/xxx.png。"""
    path = _safe_output_path(str(OUTPUT_DIR / file_name))
    return FileResponse(
        path,
        filename=path.name,
        media_type="application/octet-stream",
    )


@router.get("/doc-types")
async def list_doc_types() -> list[str]:
    """返回支持的文档类型。"""
    return ["需求规格说明书", "架构设计文档", "测试文档"]
