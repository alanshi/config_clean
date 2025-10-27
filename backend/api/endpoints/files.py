from fastapi import APIRouter, Form, UploadFile, File, Depends, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy.orm import Session
from ... import crud, schemas, models
from ...database import get_db
from ...services.file_service import process_uploaded_files, get_file_content
from typing import List, Optional

router = APIRouter()


@router.post("/upload/", response_model=schemas.Batch)
async def upload_files(
    files: List[UploadFile] = File(...),
    description: Optional[str] = None,
    keyword_set_id: int = Form(...),
    db: Session = Depends(get_db)
):
    batch = await process_uploaded_files(files, description, db, keyword_set_id)
    return batch

@router.get("/original/{file_id}/content", response_class=PlainTextResponse)
def get_original_file_content(file_id: int, db: Session = Depends(get_db)):
    file = db.query(models.OriginalFile).filter(models.OriginalFile.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    return get_file_content(file.file_path)

@router.get("/cleaned1/{file_id}/content", response_class=PlainTextResponse)
def get_cleaned1_file_content(file_id: int, db: Session = Depends(get_db)):
    file = db.query(models.CleanedFile1).filter(models.CleanedFile1.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    return get_file_content(file.file_path)

@router.get("/cleaned2/{file_id}/content", response_class=PlainTextResponse)
def get_cleaned2_file_content(file_id: int, db: Session = Depends(get_db)):
    file = db.query(models.CleanedFile2).filter(models.CleanedFile2.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    return get_file_content(file.file_path)