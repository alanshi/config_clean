from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class BatchBase(BaseModel):
    description: Optional[str] = None

class BatchCreate(BatchBase):
    pass

class Batch(BatchBase):
    id: int
    timestamp: datetime

    class Config:
        orm_mode = True

class FileBase(BaseModel):
    filename: str
    file_path: str

class OriginalFileCreate(FileBase):
    batch_id: int

class OriginalFile(FileBase):
    id: int
    upload_time: datetime
    batch_id: int

    class Config:
        orm_mode = True

class CleanedFile1Create(FileBase):
    original_file_id: int
    batch_id: int

class CleanedFile1(FileBase):
    id: int
    original_file_id: int
    cleaned_time: datetime
    batch_id: int

    class Config:
        orm_mode = True

class CleanedFile2Create(FileBase):
    cleaned_file_1_id: int
    batch_id: int

class CleanedFile2(FileBase):
    id: int
    cleaned_file_1_id: int
    cleaned_time: datetime
    batch_id: int

    class Config:
        orm_mode = True

class BatchWithFiles(Batch):
    original_files: List[OriginalFile] = []
    cleaned_files_1: List[CleanedFile1] = []
    cleaned_files_2: List[CleanedFile2] = []