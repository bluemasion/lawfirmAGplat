"""File upload/download API."""

import uuid
import os
from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.config import settings
from app.models.file import FileRecord
from app.utils.response import ok
from app.utils.errors import AppError

router = APIRouter()


@router.post("/upload")
async def upload_file(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """Upload a file."""
    if file.size and file.size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise AppError(f"文件大小超过 {settings.MAX_FILE_SIZE_MB}MB 限制")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename)[1]
    stored_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, stored_name)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    record = FileRecord(
        original_name=file.filename, stored_name=stored_name,
        file_path=file_path, file_type=ext.lstrip("."),
        file_size=len(content), uploader_id=1,  # TODO: from JWT
    )
    db.add(record)
    await db.flush()

    return ok(data={"id": record.id, "filename": file.filename, "size": len(content)})
