import json
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
    return db.query(models.Batch).order_by(models.Batch.id.desc()).offset(skip).limit(limit).all()

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


# 关键词组操作
def create_keyword_set(db: Session, keyword_set: schemas.KeywordSetCreate):
    # 将关键词列表转换为逗号分隔的字符串存储
    keywords_str = ",".join(keyword_set.keywords)
    db_set = models.KeywordSet(
        name=keyword_set.name,
        description=keyword_set.description,
        keywords=keywords_str
    )
    db.add(db_set)
    db.commit()
    db.refresh(db_set)
    return db_set

def get_keyword_sets(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.KeywordSet).offset(skip).limit(limit).all()

def get_keyword_set(db: Session, set_id: int):
    """根据ID查询关键词组"""
    return db.query(models.KeywordSet).filter(models.KeywordSet.id == set_id).first()


def update_keyword_match_result(
    db: Session,
    result_id: int,
    new_match_data: dict  # 传入的新匹配数据（字典）
):
    """更新关键词匹配结果（确保match_data序列化为JSON字符串）"""
    db_result = db.query(models.KeywordMatchResult).filter(
        models.KeywordMatchResult.id == result_id
    ).first()

    if not db_result:
        raise ValueError(f"匹配结果ID {result_id} 不存在")

    try:
        # 关键修复：将字典转换为JSON字符串后再更新
        db_result.match_data = json.dumps(new_match_data, ensure_ascii=False)
        db.commit()  # 提交更新
        db.refresh(db_result)

        # 返回时可转回字典（供前端使用）
        db_result.match_data = new_match_data
        return db_result
    except Exception as e:
        db.rollback()
        raise ValueError(f"更新匹配结果失败: {str(e)}")


def create_keyword_match_result(db: Session, result: schemas.KeywordMatchResultCreate):
    """
    创建关键词匹配结果并存储到数据库

    处理逻辑：
    1. 校验输入的 match_data 是否为可序列化的字典
    2. 将字典序列化为 JSON 字符串存储到数据库
    3. 返回时覆盖为原始字典，确保前端获取结构化数据
    """
    try:
        # 新增：校验 match_data 类型（必须是字典，否则无法序列化）
        if not isinstance(result.match_data, dict):
            raise TypeError(f"match_data 必须是字典类型，实际收到: {type(result.match_data)}")

        # 存储时序列化为 JSON 字符串（增强容错：确保非ASCII字符正确处理）
        try:
            match_data_str = json.dumps(
                result.match_data,
                ensure_ascii=False,  # 保留非ASCII字符（如中文）
                indent=None  # 不缩进，减少存储体积
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"match_data 序列化失败（JSON格式错误）: {str(e)}")
        except Exception as e:
            raise ValueError(f"match_data 序列化失败: {str(e)}")

        # 创建数据库记录（存储序列化后的字符串）
        db_result = models.KeywordMatchResult(
            batch_id=result.batch_id,
            file_id=result.file_id,
            keyword_set_id=result.keyword_set_id,
            match_data=match_data_str  # 数据库字段为字符串类型
        )
        db.add(db_result)
        db.commit()
        db.refresh(db_result)  # 从数据库刷新记录（此时 match_data 是字符串）

        # 关键：返回前覆盖为原始字典，确保前端拿到结构化数据
        # （覆盖后 ORM 对象的 match_data 变为字典，符合 Pydantic 模型要求）
        # db_result.match_data = result.match_data

        # 调试日志（生产环境可替换为 logging）
        print(f"[创建匹配结果] ID: {db_result.id}，match_data 类型: {type(db_result.match_data)}")
        return db_result

    except Exception as e:
        db.rollback()  # 出错时回滚事务，避免会话异常
        # 抛出包含上下文的错误信息，便于排查
        raise ValueError(f"保存关键词匹配结果失败（file_id: {result.file_id}）: {str(e)}")

def get_match_results_by_batch(db: Session, batch_id: int):
    """查询批次的匹配结果（强制解析为字典，添加日志验证）"""
    results = db.query(models.KeywordMatchResult).filter(
        models.KeywordMatchResult.batch_id == batch_id
    ).order_by(models.KeywordMatchResult.id.desc()).all()

    for res in results:
        # 打印原始类型，确认是否为字符串（调试用）
        # print(f"原始match_data类型: {type(res.match_data)}, 内容: {res.match_data[:50]}")

        # 强制解析：无论原始类型是什么，都尝试转为字典
        if isinstance(res.match_data, str):
            try:
                res.match_data = json.loads(res.match_data)
                # print(f"解析成功，类型变为: {type(res.match_data)}")  # 应输出dict
            except json.JSONDecodeError:
                res.match_data = {"error": "JSON解析失败"}
        elif not isinstance(res.match_data, dict):
            # 处理非字符串也非字典的异常情况
            res.match_data = {"error": f"非预期类型: {type(res.match_data)}"}

    return results

def get_cleaned_file_2(db: Session, file_id: int):
    return db.query(models.CleanedFile2).filter(models.CleanedFile2.id == file_id).first()