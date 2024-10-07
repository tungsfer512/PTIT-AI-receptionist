import io
import os
import re
import cv2
import docx
import json
import pandas as pd
import base64
import codecs
import sqlite3
from sqlalchemy import text, func
import numpy as np
from PIL import Image
from collections import Counter

from insightface.app import FaceAnalysis
from insightface.data import get_image
from datetime import datetime
import re
from database import models
import datetime


# -------------------------------------SERVICES----------------------------------------------
def get_conn():
    conn = sqlite3.connect(os.path.join(os.getcwd(), "app", "database", "kiosk.db"))
    return conn

def import_model():
    model = FaceAnalysis(name = 'buffalo_l')
    model.prepare(ctx_id = 0, det_size = (640, 640))
    os.system('cls||clear')
    return model

def save_image(image_data, filename = './services/received_img.png'):
    temp = image_data.split(",")
    if len(temp) != 2:
        print("KO TACH DUOC ,")
    else:
        image_data = image_data.split(',')[1]
        image_binary = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_binary))
        image.save(filename)

def png_to_base64(png_file):
    with open(png_file, "rb") as file:
        return base64.b64encode(file.read()).decode('utf-8')

def import_data():
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute('''
                   SELECT cccd FROM sinhvien WHERE du_lieu IS NOT NULL
                   UNION
                   SELECT cccd FROM canbo WHERE du_lieu IS NOT NULL
                   UNION
                   SELECT cccd FROM khach WHERE du_lieu IS NOT NULL''')
    temp = cursor.fetchall()

    result = []
    for _ in temp:
        cccd = list(_)[0]
        path = os.path.join(os.getcwd(), "app", "data", "img", cccd, "data.json")
        with open(path, 'r') as file:
            result += json.load(file)
    return result
# --------------------------------------------------------FACE_RECOGNITION--------------------------------------------------

def get_face_embedding(img_path, model):
    img = cv2.imread(img_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    faces = model.get(img)
    
    if len(faces) == 0:
        return 
    face_embeddings = []
    for face in faces:
        face_embeddings.append(face.embedding)
    return face_embeddings

def save_personal_data(img_path, model, personal_data):
    cccd: str = None
    role: str = None
    name: str = None
    conn = get_conn()
    cursor = conn.cursor()
    exist_data = []
    for file in os.listdir(img_path):
        if file.endswith(".png"):
            path = os.path.join(img_path, file)
            print(path)
            print()
            embedding = get_face_embedding(path, model)[0]
            embed_path = os.path.join(img_path, f'{file[:len(file)-4:]}.txt')
            data = {'embedding': embed_path}
            np.savetxt(embed_path, embedding)
            
            for key, value in personal_data.items():
                if key == "Identity Code":
                    cccd = value
                if key == 'role':
                    role = value
                if key == 'Name':
                    name = value
                data.update({key: value})
            exist_data.append(data)

    data_path = os.path.join(os.getcwd(), "app", "data", "img", cccd, "data.json")
    with open(data_path, 'w', encoding = 'utf-8') as f:
        json.dump(exist_data, f)

    print(cccd, name)
    result = cursor.execute("SELECT * FROM sinhvien WHERE cccd = ?", (cccd,)).fetchone()
    if result:
        cursor.execute("UPDATE sinhvien SET du_lieu = True WHERE cccd = ?", (cccd,))
        conn.commit()
        conn.close()
        return "Đã cập nhật du_lieu trong bảng sinhvien"

    result = cursor.execute("SELECT * FROM canbo WHERE cccd = ?", (cccd,)).fetchone()
    if result:
        cursor.execute("UPDATE canbo SET du_lieu = True WHERE cccd = ?", (cccd,))
        conn.commit()
        conn.close()
        return "Đã cập nhật du_lieu trong bảng canbo"

    result = cursor.execute("SELECT * FROM khach WHERE cccd = ?", (cccd,)).fetchone()
    if result:
        cursor.execute("UPDATE khach SET du_lieu = True WHERE cccd = ?", (cccd,))
        conn.commit()
        conn.close()
        return "Đã cập nhật du_lieu trong bảng khach"
    
    cursor.execute('''INSERT INTO khach (cccd, ho_ten, du_lieu)
        VALUES (?, ?, True)''', (cccd, name))
    conn.commit()
    conn.close()
    return "Đã thêm dữ liệu mới vào bảng khach"

def detect_nums_of_people(img_path, model):
    img = cv2.imread(img_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    faces = model.get(img)
    print(f'Có {len(faces)} trong khung hình!')
    return len(faces)

def cosine_similarity(a, b):
    if a is None or b is None: return 0

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0: return 0

    return np.dot(a, b) / (norm_a * norm_b)


def calc_cosine_similarity(embedding, faces_data):
    res = []
    for _ in faces_data:
        person = {}
        for key in _.keys():
            if key == "embedding":
                face_embedding = np.loadtxt(_["embedding"], dtype = "float64")
                cosine_sim = cosine_similarity(embedding, face_embedding)
                person.update({"embedding": cosine_sim})
            else:
                person.update({key: _[key]})
        res.append(person)
    res = [ _ for _ in res if _["embedding"] > 0.35]
    return sorted(res, key = lambda x: x["embedding"], reverse = True)

def KNN(embedding, faces_data):
    sorted_distance = calc_cosine_similarity(embedding, faces_data)
    if len(sorted_distance) > 5:
        closest_5_embed = sorted_distance[0:5:1]
    else:
        closest_5_embed = sorted_distance
    names = [item["Name"] for item in closest_5_embed]
    name_counts = Counter(names)
    try:
        most_name = name_counts.most_common(1)[0][0]
        most_list = [ _ for _ in closest_5_embed if _["Name"] == most_name]
        most_list.sort(key = lambda x: x["embedding"], reverse = True)
        result = most_list[0]
        result = {
            "name": result["Name"],
            "role": result['role']
        }
        print(f'Tìm thấy: {result}')
        return result
    except:
        result = {
            "name": "Khách",
            "role": "GUEST"
        }
        print(f'Tìm thấy: {result}')
        return result

def face_recognition(img_path, model, faces_data):
    face_embeddings = get_face_embedding(img_path, model)
    res = []
    for face_embedding in face_embeddings:
        person = KNN(face_embedding, faces_data)
        res.append(person)
    return res

# -----------------------------------------DECODE_CCCD----------------------------------------

tagIndex = {
        "020101": "Identity Code",
        "020102": "Name",
        "020103": "DOB",
        "020104": "Gender",
        "020105": "Nationality",
        "020106": "Ethnic",
        "020107": "Religion",
        "020108": "Hometown",
        "020109": "Permanent Address",
        "02010A": "Identifying Features",
        "02010B": "Card Issuance Date",
        "02010C": "Expiration Date",
        "02010D": "Parents' Names"
    }

def extract_data(data):

    so_cccd = ""
    ten = ""
    data_extract = {
        "Identity Code" : "",
        "Name" : "",
        "DOB" : "",
        "Gender" : "",
        "Nationality" : "",
        "Ethnic" : "",
        "Religion" : "",
        "Hometown" : "",
        "Permanent Address" : "",
        "Identifying Features" : "",
        "Card Issuance Date" : "",
        "Expiration Date" : "",
    }



    data_all = ""
    for i in data:
        data_all = data_all + " " +  i
    # print(data_all)

    # hexBytes = bytes.fromhex(data_all)

    # print(hexBytes)

    offset = 0

    # while (offset < 2000):
    #     if (data_all):
    #         break
    #     offset +=1
    while (offset < 2000):

        # GET CCCD
        try:
            if not data_extract.get("Identity Code") and str(data[offset]) == "30" and  str(data[offset + 2]) == "02" and  str(data[offset + 3]) == "01" and  str(data[offset + 4]) == "01":
                data_tmp = ""
                for i in range(int(data[offset + 6], 16)):
                    data_tmp = data_tmp +  data[offset + 7 + i]
                data_tmp = str(codecs.decode(data_tmp, 'hex').decode('utf-8'))
                data_extract["Identity Code"] = data_tmp
        except:
            pass
        # GET Tên
        try:
            if not data_extract.get("Name") and str(data[offset]) == "30" and  str(data[offset + 2]) == "02" and  str(data[offset + 3]) == "01" and  str(data[offset + 4]) == "02":
                data_tmp = ""
                for i in range(int(data[offset + 6], 16)):
                    data_tmp = data_tmp +  data[offset + 7 + i]
                data_tmp = str(codecs.decode(data_tmp, 'hex').decode('utf-8'))
                data_extract["Name"] = data_tmp
        except:
            pass
        # GET DOB
        try:
            if not data_extract.get("DOB") and str(data[offset]) == "30" and  str(data[offset + 2]) == "02" and  str(data[offset + 3]) == "01" and  str(data[offset + 4]) == "03":
                data_tmp = ""
                for i in range(int(data[offset + 6], 16)):
                    data_tmp = data_tmp +  data[offset + 7 + i]
                data_tmp = str(codecs.decode(data_tmp, 'hex').decode('utf-8'))
                data_extract["DOB"] = data_tmp
        except:
            pass

        # GET Gender
        try:
            if not data_extract.get("Gender") and str(data[offset]) == "30" and  str(data[offset + 2]) == "02" and  str(data[offset + 3]) == "01" and  str(data[offset + 4]) == "04":
                data_tmp = ""
                for i in range(int(data[offset + 6], 16)):
                    data_tmp = data_tmp +  data[offset + 7 + i]
                data_tmp = str(codecs.decode(data_tmp, 'hex').decode('utf-8'))
                data_extract["Gender"] = data_tmp
        except:
            pass

        # GET Nationality
        try:
            if not data_extract.get("Nationality") and str(data[offset]) == "30" and  str(data[offset + 2]) == "02" and  str(data[offset + 3]) == "01" and  str(data[offset + 4]) == "05":
                data_tmp = ""
                for i in range(int(data[offset + 6], 16)):
                    data_tmp = data_tmp +  data[offset + 7 + i]
                data_tmp = str(codecs.decode(data_tmp, 'hex').decode('utf-8'))
                data_extract["Nationality"] = data_tmp
        except:
            pass

        # GET Ethnic
        try:
            if not data_extract.get("Ethnic") and str(data[offset]) == "30" and  str(data[offset + 2]) == "02" and  str(data[offset + 3]) == "01" and  str(data[offset + 4]) == "06":
                data_tmp = ""
                for i in range(int(data[offset + 6], 16)):
                    data_tmp = data_tmp +  data[offset + 7 + i]
                data_tmp = str(codecs.decode(data_tmp, 'hex').decode('utf-8'))
                data_extract["Ethnic"] = data_tmp
        except:
            pass

        # GET Religion
        try:
            if not data_extract.get("Religion") and str(data[offset]) == "30" and  str(data[offset + 2]) == "02" and  str(data[offset + 3]) == "01" and  str(data[offset + 4]) == "07":
                data_tmp = ""
                for i in range(int(data[offset + 6], 16)):
                    data_tmp = data_tmp +  data[offset + 7 + i]
                data_tmp = str(codecs.decode(data_tmp, 'hex').decode('utf-8'))
                data_extract["Religion"] = data_tmp
        except:
            pass

        # GET Hometown
        try:
            if not data_extract.get("Hometown") and str(data[offset]) == "30" and  str(data[offset + 2]) == "02" and  str(data[offset + 3]) == "01" and  str(data[offset + 4]) == "08":
                data_tmp = ""
                for i in range(int(data[offset + 6], 16)):
                    data_tmp = data_tmp +  data[offset + 7 + i]
                data_tmp = str(codecs.decode(data_tmp, 'hex').decode('utf-8'))
                data_extract["Hometown"] = data_tmp
        except:
            pass

        # GET Permanent Address
        try:
            if not data_extract.get("Permanent Address") and str(data[offset]) == "30" and  str(data[offset + 2]) == "02" and  str(data[offset + 3]) == "01" and  str(data[offset + 4]) == "09":
                data_tmp = ""
                for i in range(int(data[offset + 6], 16)):
                    data_tmp = data_tmp +  data[offset + 7 + i]
                data_tmp = str(codecs.decode(data_tmp, 'hex').decode('utf-8'))
                data_extract["Permanent Address"] = data_tmp
        except:
            pass

        # GET Identifying Features
        try:
            if not data_extract.get("Identifying Features") and str(data[offset]) == "30" and  str(data[offset + 2]) == "02" and  str(data[offset + 3]) == "01" and  str(data[offset + 4]) == "0A":
                data_tmp = ""
                for i in range(int(data[offset + 6], 16)):
                    data_tmp = data_tmp +  data[offset + 7 + i]
                data_tmp = str(codecs.decode(data_tmp, 'hex').decode('utf-8'))
                data_extract["Identifying Features"] = data_tmp
        except:
            pass


        # GET Card Issuance Date
        try:
            if not data_extract.get("Card Issuance Date") and str(data[offset]) == "30" and  str(data[offset + 2]) == "02" and  str(data[offset + 3]) == "01" and  str(data[offset + 4]) == "0B":
                data_tmp = ""
                for i in range(int(data[offset + 6], 16)):
                    data_tmp = data_tmp +  data[offset + 7 + i]
                data_tmp = str(codecs.decode(data_tmp, 'hex').decode('utf-8'))
                data_extract["Card Issuance Date"] = data_tmp
        except:
            pass

        # GET Card Expiration Date
        try:
            if not data_extract.get("Expiration Date") and str(data[offset]) == "30" and  str(data[offset + 2]) == "02" and  str(data[offset + 3]) == "01" and  str(data[offset + 4]) == "0C":
                data_tmp = ""
                for i in range(int(data[offset + 6], 16)):
                    data_tmp = data_tmp +  data[offset + 7 + i]
                data_tmp = str(codecs.decode(data_tmp, 'hex').decode('utf-8'))
                data_extract["Expiration Date"] = data_tmp
        except:
            pass
        
        offset +=1
    # result_string = hexBytes.decode("utf-8")
    return data_extract

# -----------------------------READ FILE DOCX----------------------------------
def save_to_json(data):
    with open(os.path.join(os.getcwd(), "app", "data", "lichTuan", "lichTuan.json"), 'w', encoding = 'utf-8') as file:
        json.dump(data, file, indent = 4)
        
def check(text):
    time_pattern = re.compile(r"\b\d{2}\.\d{2}\b")
    tp_pattern = re.compile(r"TP: [^\n]*")
    dd_pattern = re.compile(r"DD: [^\n]*")
    cb_pattern = re.compile(r"C/b: [^\n]*")
    
    if re.search(time_pattern, text):
        return "time"

    if re.search(tp_pattern, text):
        return "attendees"
    
    if re.search(dd_pattern, text):
            return "location"
        
    if re.search(cb_pattern, text):
            return "preparation"
    return ""

def extract_events_from_doc(file_path):
    date_pattern = re.compile(r"Thứ\s*[A-Za-zÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠàáâãèéêìíòóôõùúăđĩũơƯẮẠẢẤẦẨẪẬẮẰẲẴẶẸẺẼỀỀỂưắạảấầẩẫậắằẳẵặẹẻẽềềểỄỆỈỊỌỎỐỒỔỖỘỚỜỞỡợỤỦỨỪỬỮỰỲỴÝỶỸấầẩẫậắằẳẵặẹẻẽềểểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]+,\s*ngày\s*\d{1,2}/\d{1,2}")
    time_pattern = re.compile(r"\b\d{2}\.\d{2}\b")
    tp_pattern = re.compile(r"TP: [^\n]*")
    dd_pattern = re.compile(r"DD: [^\n]*")
    cb_pattern = re.compile(r"C/b: [^\n]*")
    
    events = []
    current_event = {}
    current_day: str = None
    document = docx.Document(file_path)
    for table in document.tables:
        rows = table.rows
        for row in rows:
            first_cell = row.cells[0].text.strip()
            second_cell = row.cells[1].text.strip()
            
            if re.search(date_pattern, first_cell):
                current_day = first_cell
        
                continue
            
            for line in first_cell.split("\n"):
                if check(line) == "location":
                    current_event.update({"location": line.split(": ")[1]})
                    current_event.update({"date": current_day})
                    events.append(current_event)
                    current_event = {}
                    continue

                if check(line) == "time":
                    temp = line.split(": ")
                    current_event.update({"time": temp[0]})
                    current_event.update({"name": temp[1]})
                    continue
            
                temp = line.split(": ")
                if len(temp) == 2:
                    current_event.update({check(line): temp[1]})
                    continue

            for line in second_cell.split("\n"):
                if check(line) == "location":
                    current_event.update({"location": line.split(": ")[1]})
                    current_event.update({"date": current_day})
                    events.append(current_event)
                    current_event = {}
            
            
            
                    continue

                if check(line) == "time":
                    temp = line.split(": ")
                    current_event.update({"time": temp[0]})
                    current_event.update({"name": temp[1]})
            
            
                    continue
            
                temp = line.split(": ")
                if len(temp) == 2:
                    current_event.update({check(line): temp[1]})
                    continue
    
    import_lichTuan_into_DB(events)
    return format_events(events)
    # save_to_json(format_events(events))  
    
def format_events(events):
    formatted_events = []
    current_year = datetime.now().year
    
    for event in events:
        formatted_event = event.copy()
        
        # Extract date
        date_match = re.search(r"Thứ [^,]+, ngày (\d{1,2})/(\d{1,2})", event['date'])
        if date_match:
            day, month = map(int, date_match.groups())
            
            # Extract time
            time_parts = event['time'].split('.')
            hour, minute = map(int, time_parts)
            
            # Create ISO datetime
            try:
                dt = datetime(current_year, month, day, hour, minute)
                formatted_event['iso_datetime'] = dt.isoformat()
                
                # Remove separate date and time fields if desired
                del formatted_event['date']
                del formatted_event['time']
                
            except ValueError as e:
                print(f"Error processing date/time for event: {e}")
                formatted_event['iso_datetime'] = None
        
        formatted_events.append(formatted_event)
    
    return formatted_events

def import_lichTuan_into_DB(datas):
    # pass
    with open(os.path.join(os.getcwd(), "app", "data", "lichTuan", "lichTuan.json"), 'r') as file:
        return json.load(file)

def get_lichTuan():
    # pass
    with open(os.path.join(os.getcwd(), "app", "data", "lichTuan", "lichTuan.json"), 'r') as file:
        return json.load(file)

# ----------------------------------------------------------------------------
def extract_lichHoc_from_xlsx(file_path):
    xls = pd.ExcelFile(file_path)
    results = []
    for sheetname in xls.sheet_names:
        dataframe = pd. read_excel(xls, sheetname)

        dataframe = dataframe.iloc[3:].drop(dataframe.columns[0], axis = 1)

        headers = []
        cols_to_drop = []

        for i in range(len(dataframe.columns)):
            col = dataframe.columns[i]
            header = dataframe[col].iloc[0]
            
            if header in ("Ghi chú", "Tháng", "Hệ"):
                cols_to_drop.append(col)

        dataframe = dataframe.drop(columns = cols_to_drop)


        current_month: str = None
        for col in dataframe.columns:
            col_3_row = dataframe[col].iloc[0:3]
            first_cell = col_3_row.iloc[0]
            second_cell =  col_3_row.iloc[1]
            third_cell = col_3_row.iloc[2]
            
            if not pd.isna(first_cell):
                current_month = first_cell
                if not pd.isna(second_cell) and second_cell != first_cell:
                    if not pd.isna(third_cell) and third_cell != second_cell:
                        headers.append("-".join([str(second_cell), str(third_cell), str(first_cell)]))
                    else:
                        headers.append("-".join([str(second_cell), str(first_cell)]))
                else:
                    headers.append(str(first_cell))
            else:
                first_cell = current_month
                if not pd.isna(second_cell) and second_cell != first_cell:
                    if not pd.isna(third_cell) and third_cell != second_cell:
                        headers.append("-".join([str(second_cell), str(third_cell), str(first_cell)]))
                    else:
                        headers.append("-".join([str(second_cell), str(first_cell)]))
                else:
                    headers.append("")
        result = []
        for index, row in dataframe.iterrows():
            _class = {}
            if index > 2:
                for i in range(len(dataframe.iloc[3:].columns)):
                    col = dataframe.columns[i]
                    
                    value = row.iloc[i]
                    if pd.isna(value):
                        continue
                        
                    
                    if headers[i] != "":
                        _class.update({headers[i]: value})
            result.append(_class)
        results += result[3:]
    
    import_lichHoc_into_DB(results)
    return results
    # with open(os.path.join(os.getcwd(), "app", "data", "lichThucHanh", "lichThucHanh.json"), 'w') as file:
    #     json.dump(results, file, ensure_ascii=False, indent = 4)
        
def import_lichHoc_into_DB(datas):
    pass
    # with open(os.path.join(os.getcwd(), "app", "data", "lichThucHanh", "lichThucHanh.json"), 'r') as file:
    #     return json.load(file)

def get_current_week_start_end():
    today = datetime.date.today()
    # Get the ISO week number and year
    iso_week = today.isocalendar()
    # Calculate the start of the week based on the ISO week
    week_start = today + datetime.timedelta(days=-iso_week[2] + 1)
    week_end = week_start + datetime.timedelta(days=6)    
    return week_start.strftime("%d/%m/%Y"), week_end.strftime("%d/%m/%Y")

def get_lichHoc(cccd, db):
    all_lichhocs = []
    sinhvien = db.query(models.SinhVien).filter(models.SinhVien.cccd == cccd).first()
    sinhvien_nhomtinchies = db.query(models.SinhVien_NhomTinChi).filter(models.SinhVien_NhomTinChi.ma_sinh_vien == sinhvien.ma_sinh_vien).all()
    week_start, week_end = get_current_week_start_end()
    for sinhvien_nhomtinchi in sinhvien_nhomtinchies:
        print(sinhvien_nhomtinchi.ma_sinh_vien, sinhvien_nhomtinchi.ma_nhom_tin_chi)
        lichhocs = db.query(models.LichHoc).filter(
            models.LichHoc.ma_nhom_tin_chi == sinhvien_nhomtinchi.ma_nhom_tin_chi
        ).all()
        for lichhoc in lichhocs:
            room = f"{lichhoc.phong}"
            if lichhoc.nha != None and lichhoc.nha != "":
                 room += f" - {lichhoc.nha}"
            data_tmp = {
                "eventType": "Lịch học",
                "creditClass": lichhoc.ma_nhom_tin_chi,
                "courseName": "Toán rời rạc 1",
                "ngay_hoc": lichhoc.ngay_hoc,
                "startTime": f"{lichhoc.gio_bat_dau.replace('.', ':')} {lichhoc.ngay_hoc}",
                "endTime": f"{lichhoc.gio_ket_thuc.replace('.', ':')} {lichhoc.ngay_hoc}",
                "room": room,
                "instructor": "Nguyễn Hồng Anh Tấn",
            }
            all_lichhocs.append(data_tmp)
    
    print(week_start, week_end)
    print(len(all_lichhocs))
    return sorted(all_lichhocs, key=lambda lichhoc: datetime.datetime.strptime(lichhoc["ngay_hoc"], "%d/%m/%Y"))

def convertDepartment(department: str):
    if department == "bld":
        return "Ban lãnh đạo"
    elif department == "phongTh":
        return "Phòng tổng hợp"
    elif department == "phongKhcnvkhkd":
        return "Phòng Khoa học công nghệ và Kế hoạch kinh doanh"
    elif department == "phongTvtk":
        return "Phòng tư vấn thiết kế"
    elif department == "phongNcktvdvvt":
        return "Phòng nghiên cứu kỹ thuật và dịch vụ viễn thông"
    elif department == "phongDlkdvtccl":
        return "Phòng đo lường kiểm định và tiêu chuẩn chất lượng"
    elif department == "phongUdvcgcns":
        return "Phòng ứng dụng và chuyển giao công nghệ số"
    elif department == "phongNcptcns":
        return "Phòng nghiên cứu phát triển công nghệ số"
    elif department == "cs2":
        return "Cơ sở 2 của Viện tại TP.Hồ Chí Minh"
    else:
        return "Không xác định"