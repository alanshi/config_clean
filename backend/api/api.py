from fastapi import APIRouter
from .endpoints import files, batches, keywords

api_router = APIRouter()
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(batches.router, prefix="/batches", tags=["batches"])
api_router.include_router(keywords.router, prefix="/keywords", tags=["keywords"])  # 新增
