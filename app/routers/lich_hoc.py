from fastapi import APIRouter, HTTPException, status, UploadFile, File
from typing import AnyStr, Dict
import shutil
import json
import os
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, status, Query
from database.database import get_db

from services.dependencies import extract_lichHoc_from_xlsx, get_lichHoc, get_lichGiangDay

router = APIRouter()

@router.post("/api/post-lich-hoc")
def post_lich_hoc(file: UploadFile = File(...)):
    if not file:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST, 
            detail = "Không có dữ liệu"
        )
    if file.content_type != "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .xlsx")
    
    file_path = os.path.join(os.getcwd(), "app", "data", "lichThucHanh", "lichThucHanh.xlsx")
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        extract_lichHoc_from_xlsx(file_path)
        return {"response": "Upload file successfully"}
    except Exception as err:
        raise HTTPException(status_code = status.HTTP_500_INTERNAL_SERVER_ERROR, detail = err )

@router.get("/api/get-lich-hoc/{cccd}")
def get_lich_hoc(cccd: str, ngaybatdau: str = Query(None), db: Session = Depends(get_db)):
    return get_lichHoc(cccd, db, ngaybatdau)

@router.get("/api/get-lich-giang-day/{cccd}")
def get_lich_giang_day(cccd: str, ngaybatdau: str = Query(None), db: Session = Depends(get_db)):
    return get_lichGiangDay(cccd, db, ngaybatdau)