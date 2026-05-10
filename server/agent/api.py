"""docgen_agent 前端接口。

POST /api/agent/generate-doc      — 生成文档（支持上传 txt/md 需求文件）
GET  /api/agent/doc-types         — 获取支持的文档类型列表
"""

import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from loguru import logger
from pydantic import BaseModel

from .docgen_agent.workflow import run_agent

router = APIRouter(prefix="/api/agent")

DocType = Literal["需求规格说明书", "架构设计文档", "测试文档"]

UPLOAD_DIR = Path(tempfile.gettempdir()) / "drg_docgen_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".txt", ".md"}


class GenerateDocResponse(BaseModel):
    status: str
    file_name: str
    file_path: str
    doc_type: str


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
) -> GenerateDocResponse:
    """生成技术文档。

    接收前端提示词 + 可选的需求文件，按 doc_type 生成 Markdown 文档。
    若未上传 source_file，默认使用 requirement.md。
    """
    # 处理上传文件
    source_path: Optional[str] = None
    if source_file is not None and source_file.filename:
        ext = Path(source_file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {ext}，仅支持 {', '.join(ALLOWED_EXTENSIONS)}",
            )

        safe_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{source_file.filename}"
        dest = UPLOAD_DIR / safe_name
        with open(dest, "wb") as f:
            shutil.copyfileobj(source_file.file, f)
        source_path = str(dest)
        logger.info(f"收到上传文件: {dest}")

    try:
        output_path = run_agent(
            doc_type=doc_type,
            user_hint=prompt,
            source_file=source_path,
        )
        return GenerateDocResponse(
            status="success",
            file_name=output_path.name,
            file_path=str(output_path),
            doc_type=doc_type,
        )
    except Exception as e:
        logger.exception(f"文档生成失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/doc-types")
async def list_doc_types() -> list[str]:
    """返回支持的文档类型。"""
    return ["需求规格说明书", "架构设计文档", "测试文档"]
