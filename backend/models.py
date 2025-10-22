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