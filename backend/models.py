from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Batch(Base):
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    description = Column(String, nullable=True)

    original_files = relationship("OriginalFile", back_populates="batch")
    cleaned_files_1 = relationship("CleanedFile1", back_populates="batch")
    cleaned_files_2 = relationship("CleanedFile2", back_populates="batch")

class OriginalFile(Base):
    __tablename__ = "original_files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    file_path = Column(String)
    upload_time = Column(DateTime, default=datetime.utcnow)
    batch_id = Column(Integer, ForeignKey("batches.id"))

    batch = relationship("Batch", back_populates="original_files")

class CleanedFile1(Base):
    __tablename__ = "cleaned_files_1"

    id = Column(Integer, primary_key=True, index=True)
    original_file_id = Column(Integer, ForeignKey("original_files.id"))
    filename = Column(String, index=True)
    file_path = Column(String)
    cleaned_time = Column(DateTime, default=datetime.utcnow)
    batch_id = Column(Integer, ForeignKey("batches.id"))

    batch = relationship("Batch", back_populates="cleaned_files_1")

class CleanedFile2(Base):
    __tablename__ = "cleaned_files_2"

    id = Column(Integer, primary_key=True, index=True)
    cleaned_file_1_id = Column(Integer, ForeignKey("cleaned_files_1.id"))
    filename = Column(String, index=True)
    file_path = Column(String)
    cleaned_time = Column(DateTime, default=datetime.utcnow)
    batch_id = Column(Integer, ForeignKey("batches.id"))

    batch = relationship("Batch", back_populates="cleaned_files_2")

# 在原有模型基础上添加
class KeywordSet(Base):
    __tablename__ = "keyword_sets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)  # 关键词组名称
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    keywords = Column(String)  # 存储逗号分隔的关键词

class KeywordMatchResult(Base):
    __tablename__ = "keyword_match_results"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("batches.id"))  # 关联批次
    file_id = Column(Integer, ForeignKey("cleaned_files_2.id"))  # 关联二次清洗文件
    keyword_set_id = Column(Integer, ForeignKey("keyword_sets.id"))  # 关联关键词组
    match_data = Column(String)  # 存储JSON格式的匹配结果
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关联关系
    batch = relationship("Batch")
    file = relationship("CleanedFile2")
    keyword_set = relationship("KeywordSet")