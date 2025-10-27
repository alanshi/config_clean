import os
import json
import shutil
from datetime import datetime
from fastapi import UploadFile
from sqlalchemy.orm import Session
from .. import crud, schemas, models
from .clean_1 import clean_multiple_configs
from .clean_2 import parse_config_file  # 导入二次清洗函数
from .keyword_service import perform_keyword_check

# 确保上传目录存在
UPLOAD_BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../static/uploads")
os.makedirs(UPLOAD_BASE_DIR, exist_ok=True)

async def process_uploaded_files(files: list[UploadFile], description: str, db: Session, keyword_set_id: int):
    # 创建新批次
    batch = crud.create_batch(db, schemas.BatchCreate(description=description))

    # 创建批次目录
    batch_timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    batch_dir = os.path.join(UPLOAD_BASE_DIR, f"batch_{batch.id}_{batch_timestamp}")
    original_dir = os.path.join(batch_dir, "original")
    cleaned1_dir = os.path.join(batch_dir, "cleaned_1")

    os.makedirs(original_dir, exist_ok=True)
    os.makedirs(cleaned1_dir, exist_ok=True)

    original_file_paths = []
    batch_id = batch.id
    # 保存原始文件
    for file in files:
        file_path = os.path.join(original_dir, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 保存文件信息到数据库
        crud.create_original_file(db, schemas.OriginalFileCreate(
            filename=file.filename,
            file_path=file_path,
            batch_id=batch_id
        ))

        original_file_paths.append(file_path)

    # 执行初次清洗
    clean_multiple_configs(original_file_paths, keep_bang_blocks=True)

    # 保存清洗后的文件信息
    for original_path in original_file_paths:
        # 找到清洗后的文件
        filename = os.path.basename(original_path)
        name, ext = os.path.splitext(filename)
        cleaned_filename = f"{name}{ext}_cleaned{ext}"
        cleaned_path = os.path.join(original_dir, cleaned_filename)

        # 如果清洗后的文件存在，移动到cleaned1_dir并更新数据库
        if os.path.exists(cleaned_path):
            new_cleaned_path = os.path.join(cleaned1_dir, cleaned_filename)
            shutil.move(cleaned_path, new_cleaned_path)

            # 获取原始文件ID
            original_file = db.query(models.OriginalFile).filter(
                models.OriginalFile.file_path == original_path
            ).first()

            # 创建清洗文件记录
            crud.create_cleaned_file_1(db, schemas.CleanedFile1Create(
                filename=cleaned_filename,
                file_path=new_cleaned_path,
                original_file_id=original_file.id,
                batch_id=batch.id
            ))

    # 步骤2：执行二次清洗，
    perform_second_cleaning(batch_id, db)

    # 步骤3: 执行关键词检测


    # 获取默认关键词组（或让用户提前选择，这里简化为取ID=1的组）
    # default_keyword_set = crud.get_default_keyword_set(db)  # 需实现：获取默认关键词组
    # if not default_keyword_set:
    #     raise ValueError("无可用关键词组，请先创建关键词组")
    # import pdb;pdb.set_trace()
    # 执行关键词检测（基于clean_1的结果）
    keyword_results = perform_keyword_check(
        db=db,
        batch_id=batch_id,
        # 传入clean_1文件的ID列表（替代原clean_2的file_ids）
        # file_ids=[f.id for f in original_file_paths],
        keyword_set_id=keyword_set_id
    )

    # 更新批次状态为“已完成”
    crud.update_batch_status(db, batch_id=batch_id, status="completed")
    return batch

def perform_second_cleaning(batch_id: int, db: Session):
    # 获取批次的初次清洗文件
    cleaned1_files = crud.get_cleaned_files_1_by_batch(db, batch_id)
    if not cleaned1_files:
        return

    # 创建二次清洗目录
    batch = crud.get_batch(db, batch_id)
    batch_dir = os.path.dirname(os.path.dirname(cleaned1_files[0].file_path))
    cleaned2_dir = os.path.join(batch_dir, "cleaned_2")
    match_dir = os.path.join(batch_dir, "match")
    os.makedirs(cleaned2_dir, exist_ok=True)
    os.makedirs(match_dir, exist_ok=True)

    # 执行二次清洗（使用新提供的代码）
    for file in cleaned1_files:
        try:
            # 调用二次清洗函数解析配置文件
            parsed_data = parse_config_file(file.file_path)

            # 生成二次清洗后的文件名
            filename = os.path.basename(file.file_path)
            name, ext = os.path.splitext(filename)
            cleaned2_filename = f"{name}_cleaned2.json"  # 保存为JSON格式
            cleaned2_path = os.path.join(cleaned2_dir, cleaned2_filename)

            # 写入JSON格式的清洗结果
            with open(cleaned2_path, 'w', encoding='utf-8') as f:
                json.dump(parsed_data, f, indent=4, ensure_ascii=False)

            # 保存到数据库
            crud.create_cleaned_file_2(db, schemas.CleanedFile2Create(
                filename=cleaned2_filename,
                file_path=cleaned2_path,
                cleaned_file_1_id=file.id,
                batch_id=batch_id
            ))
        except Exception as e:
            print(f"二次清洗文件 {file.filename} 失败: {str(e)}")

def get_file_content(file_path: str) -> str:
    if not os.path.exists(file_path):
        return "File not found"

    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()