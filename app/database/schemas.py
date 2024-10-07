from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional

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

class EventCreate(BaseModel):
    name: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: str
    
class EventOut(BaseModel):
    id: int
    name: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: str
    
    class Config:
        from_attributes = True
    
# telegram bot
class CCCDInfo(BaseModel):
    identityCode: str
    name: str
    dob: str
    gender: str

class ContactCreate(BaseModel):
    isAppointment: bool
    appointmentTime: str
    department: str
    phoneNumber: str
    note: str
    cccdInfo: CCCDInfo