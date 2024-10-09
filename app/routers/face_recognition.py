import json
import os
import shutil
from typing import List, AnyStr
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, status
from typing import Dict, List, AnyStr
from collections import defaultdict
from services.dependencies import import_data
from services.dependencies import save_image, save_personal_data
from services.base_model import ConnectionManager
from services.dependencies import save_image, import_model, import_data, extract_data, get_conn
from services.dependencies import face_recognition, detect_nums_of_people

router = APIRouter()
model = import_model()
manager = ConnectionManager()
TARGET_WEBSOCKET = None
faces_data = import_data()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global TARGET_WEBSOCKET
    global manager
    await manager.connect(websocket)
    TARGET_WEBSOCKET = websocket
    img_path = os.path.join(os.getcwd(), "app", "services", "received_img.png")
    try:
        while True:
            data = await websocket.receive_text()
            save_image(data, img_path)
            nums_of_people = detect_nums_of_people(img_path, model)
            if nums_of_people != 0:
                names = face_recognition(img_path, model = model, faces_data = faces_data)
                await manager.send_response({
                    "key": "webcam", 
                    "value": {"nums_of_people": nums_of_people, "person_datas": names}}, websocket)
            else:
                await manager.send_response({
                    "key": "webcam", 
                    "value": {"nums_of_people": nums_of_people, "person_datas": []}}, websocket)
    except WebSocketDisconnect:
        TARGET_WEBSOCKET = None
    except Exception as err:
        # raise HTTPException(status_code = 502, detail = err)
        print(err)

@router.post("/api/get-identity")
async def get_identity(
    data: List[AnyStr]
    # DỮ LIỆU ĐƯỢC ĐỊNH DẠNG:
        # list(str)
):
    global TARGET_WEBSOCKET, manager
    if not TARGET_WEBSOCKET:
        raise HTTPException(status_code = 500, detail = "Chưa có ai kết nối đến máy chủ!")
    try:
        decoded_data = extract_data(data)
        await manager.send_response({
            "key": "cccd",
            "value": json.dumps(decoded_data)
        }, TARGET_WEBSOCKET)
    except Exception as err:
        raise HTTPException(status_code = 503, detail = err)

@router.post('/api/post-personal-img')
async def post_personal_img(
    data: Dict[AnyStr, List[AnyStr] | Dict[AnyStr, AnyStr] | AnyStr]
    # DỮ LIỆU ĐƯỢC ĐỊNH DẠNG:
        # Dict(str: dict(str: list) || list(str) || str)
):
    if not data:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = "Không có dữ liệu"
        )

    global faces_data
    b64_img = data['b64_img']
    personal_data = data['cccd']
    role =  data['role']
    personal_id = personal_data['Identity Code']
    personal_data.update({'role': role})    

    current_path = os.getcwd()
    save_img_path = os.path.join(current_path, "app", "data", "img", personal_id)
    if os.path.exists(save_img_path):
        shutil.rmtree(save_img_path)

    os.makedirs(save_img_path)
    try:
        id = 0 
        for img in b64_img:
            img_path = os.path.join(save_img_path, f'{personal_id}_{id}.png')
            save_image(img, img_path)

            print(f"Lưu thành công ảnh: {personal_id}_{id}.png")
            with open(os.path.join(save_img_path, f'{personal_id}_{id}_base64.txt'), 'w') as file:
                file.write(img)
            id += 1
        save_personal_data(save_img_path, model, personal_data)
        return {"response": "Request thành công"}
    except Exception as err:
        shutil.rmtree(save_img_path)
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail = f"ERROR: {err}"
        )
    finally:
        faces_data = import_data()

@router.get("/api/get-all-data")
async def get_all_data():
    normalized_data = defaultdict(lambda: {
        "embedding": [],
        "Identity Code": None,
        "Name": None,
        "DOB": None,
        "Gender": None,
        "role": None
    })

    for entry in faces_data:
        identity_code = entry["Identity Code"]
        normalized_data[identity_code]["identity_code"] = entry["Identity Code"]
        normalized_data[identity_code]["name"] = entry["Name"]
        normalized_data[identity_code]["dob"] = entry["DOB"]
        normalized_data[identity_code]["gender"] = entry["Gender"]
        normalized_data[identity_code]["role"] = entry["role"]

    final_data = list(normalized_data.values())

    for i in range(len(final_data)):
        person = final_data[i]
        identity = person["identity_code"]
        b64 = []
        path = os.path.join(os.getcwd(), "app", "data", "img", identity)
        for file in os.listdir(path):
            if file.endswith("base64.txt"):
                with open(os.path.join(path, file), 'r') as file:
                    b64.append(file.read())
        person["b64"] = b64
        final_data[i] = person
    return final_data