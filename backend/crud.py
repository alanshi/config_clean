from sqlalchemy.orm import Session
from . import models, schemas
from datetime import datetime

def create_batch(db: Session, batch: schemas.BatchCreate):
    db_batch = models.Batch(**batch.dict())
    db.add(db_batch)
    db.commit()
    db.refresh(db_batch)
    return db_batch

def get_batches(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Batch).offset(skip).limit(limit).all()

def get_batch(db: Session, batch_id: int):
    return db.query(models.Batch).filter(models.Batch.id == batch_id).first()

def create_original_file(db: Session, file: schemas.OriginalFileCreate):
    db_file = models.OriginalFile(** file.dict())
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    return db_file

def create_cleaned_file_1(db: Session, file: schemas.CleanedFile1Create):
    db_file = models.CleanedFile1(**file.dict())
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    return db_file

def create_cleaned_file_2(db: Session, file: schemas.CleanedFile2Create):
    db_file = models.CleanedFile2(** file.dict())
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    return db_file

def get_original_files_by_batch(db: Session, batch_id: int):
    return db.query(models.OriginalFile).filter(models.OriginalFile.batch_id == batch_id).all()

def get_cleaned_files_1_by_batch(db: Session, batch_id: int):
    return db.query(models.CleanedFile1).filter(models.CleanedFile1.batch_id == batch_id).all()

def get_cleaned_files_2_by_batch(db: Session, batch_id: int):
    return db.query(models.CleanedFile2).filter(models.CleanedFile2.batch_id == batch_id).all()