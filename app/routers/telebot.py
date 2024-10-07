import os
import httpx
from fastapi import APIRouter, HTTPException

from database.schemas import ContactCreate
from services.base_model import TelegramService
from services.dependencies import convertDepartment

router = APIRouter()

# API
@router.post("/api/contact")
async def create_contact(contact: ContactCreate):
    try:
        telegram_service = TelegramService(os.getenv("BOT_TOKEN"))

        message = f"""
🔔 *Thông báo có khách liên hệ*

👤 *Thông tin khách:*
- Họ tên: {contact.cccdInfo.name}
- CCCD: {contact.cccdInfo.identityCode}
- Ngày sinh: {contact.cccdInfo.dob}
- Giới tính: {contact.cccdInfo.gender}

📞 *Bên cần liên hệ:*
- Có lịch hẹn: {'Có' if contact.isAppointment else 'Không'}
- Thời gian hẹn: {contact.appointmentTime}
- Số điện thoại: {contact.phoneNumber}
- Phòng ban: {convertDepartment(contact.department)}


📝 *Ghi chú:* {contact.note}
        """

        await telegram_service.send_message(contact.phoneNumber, message)

        return {"status": "success", "message": "Đã gửi thông tin thành công"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))