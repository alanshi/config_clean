import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ... import schemas, crud
from ...database import get_db
from ...services.keyword_service import perform_keyword_check

router = APIRouter()


class KeywordCheckRequest(schemas.BaseModel):
    batch_id: int  # 批次ID
    keyword_set_id: int  # 关键词组ID

@router.get("/sets/{set_id}", response_model=schemas.KeywordSet)
def read_keyword_set(
    set_id: int,  # 路径参数：关键词组ID
    db: Session = Depends(get_db)
):
    """获取单个关键词组详情"""
    keyword_set = crud.get_keyword_set(db, set_id=set_id)
    if keyword_set is None:
        raise HTTPException(status_code=404, detail="关键词组不存在")

    # 将数据库中存储的逗号分隔字符串转换为列表（匹配前端预期）
    keyword_set.keywords = keyword_set.keywords.split(",")
    return keyword_set


# 关键词组管理
@router.post("/sets/", response_model=schemas.KeywordSet)
def create_keyword_set(
    keyword_set: schemas.KeywordSetCreate,
    db: Session = Depends(get_db)
):
    return crud.create_keyword_set(db=db, keyword_set=keyword_set)

@router.get("/sets/", response_model=List[schemas.KeywordSet])
def read_keyword_sets(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    sets = crud.get_keyword_sets(db, skip=skip, limit=limit)
    # 转换逗号分隔的关键词为列表
    for s in sets:
        s.keywords = s.keywords.split(",")
    return sets

# 关键词匹配
@router.post("/match/", response_model=List[schemas.KeywordMatchResult])
def match_keywords(
    request: schemas.KeywordMatchRequest,
    db: Session = Depends(get_db)
):
    try:
        results = perform_keyword_check(
            db=db,
            batch_id=request.batch_id,
            keyword_set_id=request.keyword_set_id
        )

        # # 接口层最后一次校验：确保所有match_data都是字典
        # for res in results:
        #     if isinstance(res.match_data, str):
        #         # 紧急解析：如果还是字符串，尝试最后一次解析
        #         res.match_data = json.loads(res.match_data)
        #     if not isinstance(res.match_data, dict):
        #         res.match_data = {"error": "接口层解析失败"}
        for res in results:
            if isinstance(res.match_data, str):
                res.match_data = json.loads(res.match_data)
        return results
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# 获取批次的匹配结果
@router.get("/match/batch/{batch_id}", response_model=List[schemas.KeywordMatchResult])
def get_batch_matches(batch_id: int, db: Session = Depends(get_db)):
    results = crud.get_match_results_by_batch(db, batch_id=batch_id)

    # 最后一次校验
    for res in results:
        if isinstance(res.match_data, str):
            res.match_data = json.loads(res.match_data)
        if not isinstance(res.match_data, dict):
            res.match_data = {"error": "查询接口解析失败"}

    return results