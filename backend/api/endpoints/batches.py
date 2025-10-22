from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ... import crud, schemas
from ...database import get_db
from ...services.file_service import perform_second_cleaning
from typing import List

router = APIRouter()

@router.get("/", response_model=List[schemas.BatchWithFiles])
def read_batches(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    batches = crud.get_batches(db, skip=skip, limit=limit)
    return batches

@router.get("/{batch_id}", response_model=schemas.BatchWithFiles)
def read_batch(batch_id: int, db: Session = Depends(get_db)):
    batch = crud.get_batch(db, batch_id=batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found")
    return batch

@router.post("/{batch_id}/clean2", response_model=schemas.BatchWithFiles)
def clean_batch_second_time(batch_id: int, db: Session = Depends(get_db)):
    batch = crud.get_batch(db, batch_id=batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found")

    # 执行二次清洗
    perform_second_cleaning(batch_id, db)
    return crud.get_batch(db, batch_id=batch_id)