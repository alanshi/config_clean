from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ... import crud, schemas
from ...database import get_db
from ...services.file_service import perform_second_cleaning
from typing import List
from ...models import Batch, OriginalFile, CleanedFile1, CleanedFile2, KeywordMatchResult


router = APIRouter()

@router.get("/", response_model=List[schemas.BatchWithFiles])
def read_batches(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    batches = crud.get_batches(db, skip=skip, limit=limit)
    # 为每个批次补充关联数据
    result_batches = []
    for batch in batches:
        # 1. 查询该批次的原始文件
        original_files = db.query(OriginalFile).filter(
            OriginalFile.batch_id == batch.id
        ).all()

        # 2. 查询该批次的初次清洗文件
        cleaned_files_1 = db.query(CleanedFile1).filter(
            CleanedFile1.batch_id == batch.id
        ).all()

        # 3. 查询该批次的二次清洗文件（按需求保留，可能为空）
        cleaned_files_2 = db.query(CleanedFile2).filter(
            CleanedFile2.batch_id == batch.id
        ).all()

        # 4. 查询该批次的关键词匹配结果（关联原始文件名）
        keyword_matches = []
        if original_files:
            # 先获取该批次所有原始文件的id和文件名映射
            file_id_to_name = {f.id: f.filename for f in original_files}

            # 查询该批次的关键词结果
            matches = db.query(KeywordMatchResult).filter(
                KeywordMatchResult.batch_id == batch.id
            ).all()

            # 补充原始文件名（前端表格需要显示）
            for match in matches:
                keyword_matches.append({
                    "id": match.id,
                    "file_id": match.file_id,
                    "batch_id": batch.id,
                    "filename": match.filename,
                    "file_path": match.file_path[match.file_path.find("/static"):] if match.file_path else None,# 将/static字符前面路径部分删除
                    "keyword_set_id": match.keyword_set_id,
                    "created_at": match.created_at
                })

        # 组装批次数据（转换为Pydantic模型可识别的格式）
        result_batches.append({
            "id": batch.id,
            "timestamp": batch.timestamp,  # 假设批次模型用created_at存储创建时间
            "description": batch.description,
            "status": batch.status,
            "original_files": original_files,
            "cleaned_files_1": cleaned_files_1,
            "cleaned_files_2": cleaned_files_2,
            "keyword_matches": keyword_matches
        })

    return result_batches


@router.get("/{batch_id}", response_model=schemas.BatchResponse)
def read_batch(
    batch_id: int,
    db: Session = Depends(get_db)
):
    """获取单个批次的详细信息（包含关联文件）"""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="批次不存在")

    # 逻辑同列表接口，补充关联数据
    original_files = db.query(OriginalFile).filter(OriginalFile.batch_id == batch_id).all()
    cleaned_files_1 = db.query(CleanedFile1).filter(CleanedFile1.batch_id == batch_id).all()
    cleaned_files_2 = db.query(CleanedFile2).filter(CleanedFile2.batch_id == batch_id).all()

    # 关键词结果补充原始文件名
    #file_id_to_name = {f.id: f.filename for f in original_files} if original_files else {}
    matches = db.query(KeywordMatchResult).filter(KeywordMatchResult.batch_id == batch_id).all()

    keyword_matches = [{
        "id": m.id,
        "batch_id": batch_id,
        "file_id": m.file_id,
        "filename": m.filename,
        "file_path": m.file_path[m.file_path.find("/static"):] if m.file_path else None,# 将/static字符前面路径部分删除
        "keyword_set_id": m.keyword_set_id,
        "created_at": m.created_at
    } for m in matches]


    return {
        "id": batch.id,
        "timestamp": batch.created_at,
        "description": batch.description,
        "status": batch.status,
        "original_files": original_files,
        "cleaned_files_1": cleaned_files_1,
        "cleaned_files_2": cleaned_files_2,
        "keyword_matches": keyword_matches
    }

# @router.get("/{batch_id}", response_model=schemas.BatchWithFiles)
# def read_batch(batch_id: int, db: Session = Depends(get_db)):
#     batch = crud.get_batch(db, batch_id=batch_id)
#     if batch is None:
#         raise HTTPException(status_code=404, detail="Batch not found")
#     return batch

@router.post("/{batch_id}/clean2", response_model=schemas.BatchWithFiles)
def clean_batch_second_time(batch_id: int, db: Session = Depends(get_db)):
    batch = crud.get_batch(db, batch_id=batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found")

    # 执行二次清洗
    perform_second_cleaning(batch_id, db)
    return crud.get_batch(db, batch_id=batch_id)