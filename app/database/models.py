from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Date
from sqlalchemy.orm import relationship
from pydantic import BaseModel
from .database import Base  

class UserCreate(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)    

class Event(Base):
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    location = Column(String)

'''
--------------------------------------------------------------------------
Sinh viên bao gồm:
- Mã sinh viên
- Họ tên sinh viên
- giới tính
- Quốc tịch
- Dân tộc 
- Tôn giáo 
- Ngày sinh 
- CCCD
- Lớp hành chính 
'''

class SinhVien(Base):
    __tablename__ = "sinhvien"
    ma_sinh_vien = Column(String, primary_key = True, index = True)
    ho_ten = Column(String)
    lop_hanh_chinh = Column(String)
    dan_toc = Column(String)
    ton_giao = Column(String)
    cccd = Column(String, unique = True)
    ngay_sinh = Column(Date)
    gioi_tinh = Column(String)
    quoc_tich = Column(String)
    du_lieu = Column(Boolean)

class CanBo(Base):
    __tablename__ = "canbo"
    ma_can_bo = Column(String, primary_key = True, index = True)
    ho_ten = Column(String)
    loai_giao_vien = Column(String)
    cccd = Column(String, unique = True)
    ngay_sinh = Column(Date)
    gioi_tinh = Column(String)
    quoc_tich = Column(String)
    du_lieu = Column(Boolean)

class Khach(Base):
    __tablename__ = "khach"
    cccd = Column(String, primary_key = True, index = True)
    ho_ten = Column(String)
    du_lieu = Column(Boolean)
    
'''
--------------------------------------------------------------
Một lớp tín chỉ có một học phần
Một học phần có nhiều lớp tín chỉ
Lớp tín chỉ - Học phần: Một - Nhiều

==>
Lớp tín chỉ bao gồm:
- Mã lớp tín chỉ
- Mã học phần
- Thứ tự lớp   
- Học kỳ

Học phần bao gồm:
- Mã học phần
- Tên học phần
- Số tín chỉ
'''

class HocPhan(Base):
    __tablename__ = "hocphan"
    ma_hoc_phan = Column(String, primary_key = True, index = True)
    ten_hoc_phan = Column(String)
    so_tin_chi = Column(Integer)
    
class LopTinChi(Base):
    __tablename__ = "loptinchi"
    ma_lop_tin_chi = Column(String, primary_key = True, index = True)
    ma_hoc_phan = Column(String, ForeignKey(HocPhan.ma_hoc_phan), nullable = False)
    thu_tu_lop = Column(String)
    hoc_ky = Column(String)

'''
---------------------------------------------------------------
Một lớp tín chỉ gồm nhiều nhóm tín chỉ, có thể không có nhóm tín chỉ
Một nhóm tín chỉ chỉ thuộc một lớp tín chỉ

==> 
Nhóm tín chỉ bao gồm:
- Mã nhóm tín chỉ = Mã lớp tín chỉ + Thứ tự nhóm
- Mã lớp tín chỉ
- Thứ tự nhóm
- Lịch thực hành
'''

class NhomTinChi(Base):
    __tablename__ = "nhomtinchi"
    ma_nhom_tin_chi = Column(String, primary_key = True, index = True)
    ma_lop_tin_chi = Column(String, ForeignKey(LopTinChi.ma_lop_tin_chi), nullable = False)
    thu_tu_nhom = Column(String)
    

'''
----------------------------------------------------------------
Một sinh viên có thể tham gia nhiều nhóm tín chỉ
Một nhóm tín chỉ có nhiều sinh viên tham gia
Sinh viên - nhóm tín chỉ: Nhiều - Nhiều

==> 
Sinh viên - Nhóm tín chỉ bao gồm:
- Mã sinh viên
- Mã nhóm tín chỉ

'''

class SinhVien_NhomTinChi(Base):
    __tablename__ = "sinhvien_nhomtinchi"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ma_sinh_vien = Column(String, ForeignKey(SinhVien.ma_sinh_vien), nullable= False)
    ma_nhom_tin_chi = Column(String, ForeignKey(NhomTinChi.ma_nhom_tin_chi), nullable= False)

class CanBo_LopTinChi(Base):
    __tablename__ = "canbo_loptinchi"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ma_can_bo = Column(String, ForeignKey(CanBo.ma_can_bo), nullable= False)
    ma_lop_tin_chi = Column(String, ForeignKey(LopTinChi.ma_lop_tin_chi), nullable= False) 

class LichHoc(Base):
    __tablename__ = "lichhoc"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ma_nhom_tin_chi = Column(String, ForeignKey(NhomTinChi.ma_nhom_tin_chi), nullable= False)
    ngay_hoc = Column(String, nullable=False)
    gio_bat_dau = Column(String, nullable=False)
    gio_ket_thuc = Column(String, nullable=False)
    tiet_bat_dau = Column(Integer, nullable=False)
    so_tiet = Column(Integer, nullable=False)
    phong = Column(String, nullable=False)
    nha = Column(String, nullable=False)

hoc_phan = relationship("HocPhan", back_populates = "lop_tin_chi")
nhom_tin_chi = relationship("NhomTinChi", back_populates = "lop_tin_chi")
lop_tin_chi = relationship("LopTinChi", back_populates = "hoc_phan")
sinh_vien = relationship("SinhVien", back_populates = "nhom_tin_chi")
nhom_tin_chi = relationship("NhomTinChi", back_populates = "sinh_vien")
lop_tin_chi = relationship("LopTinChi", back_populates = "nhom_tin_chi")
sinh_vien = relationship("SinhVien_LopTinChi", back_populates = "nhom_tin_chi")

