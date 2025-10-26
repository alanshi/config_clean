import json
from pydantic import BaseModel, field_validator
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

class BatchResponse(Batch):
    original_files: List[OriginalFile] = []
    cleaned_files_1: List[CleanedFile1] = []
    cleaned_files_2: List[CleanedFile2] = []
    keyword_matches: List[dict] = []


class BatchWithFiles(BatchResponse):
    pass

# 关键词组模型
class KeywordSetBase(BaseModel):
    name: str
    description: Optional[str] = None
    keywords: List[str]

class KeywordSetCreate(KeywordSetBase):
    pass

class KeywordSet(KeywordSetBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

# 匹配请求模型
class KeywordMatchRequest(BaseModel):
    batch_id: int
    keyword_set_id: int  # 关键词组ID

# 匹配结果模型
class KeywordMatchResultBase(BaseModel):
    batch_id: int
    file_id: int
    keyword_set_id: int
    match_data: dict
    filename: str
    file_path: str
    # 新增：自定义验证器，自动将JSON字符串转为字典
    @field_validator('match_data', mode='before')
    def parse_match_data(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)  # 字符串→字典
            except json.JSONDecodeError:
                return {"error": "Invalid JSON string"}
        elif not isinstance(v, dict):
            return {"error": f"Unexpected type: {type(v)}"}
        return v  # 已经是字典则直接返回

class KeywordMatchResultCreate(KeywordMatchResultBase):
    pass

class KeywordMatchResult(KeywordMatchResultBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True
        arbitrary_types_allowed = True