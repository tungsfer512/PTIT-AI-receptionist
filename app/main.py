import uvicorn
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from internal import admin 
from routers import face_recognition, lich_tuan, auth, event, telebot, lich_hoc
from database.database import engine, Base 

app = FastAPI()
Base.metadata.create_all(bind = engine)

app.include_router(face_recognition.router)
app.include_router(lich_tuan.router)
app.include_router(auth.router)
app.include_router(lich_hoc.router)
app.include_router(event.router)
app.include_router(telebot.router)

app.add_middleware(
    CORSMiddleware, 
    allow_origins = ['*'],
    allow_credentials = True,
    allow_methods = ['*'],
    allow_headers = ['*']
)

@app.get('/')
async def root():
    return {"message": "websocket server is running. Connect to /ws for websocket communication"}

if __name__ == "__main__":
    uvicorn.run("main:app", host = "0.0.0.0", port = 5050, log_level="debug", reload=True)