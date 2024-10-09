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
from datetime import datetime, date, timedelta
import re
from database import models


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
        if os.path.exists(path):
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
            "role": result['role'],
            "cccd": result['Identity Code'],
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
    
    save_to_json(format_events(events))  
    # import_lichTuan_into_DB(events)
    # return format_events(events)
    
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

def get_lichTuan(cccd=None):
    # pass
    with open(os.path.join(os.getcwd(), "app", "data", "lichTuan", "lichTuan.json"), 'r') as file:
        return json.load(file)

# ----------------------------------------------------------------------------
def extract_lichHoc_from_xlsx(file_path):
    conn = get_conn()
    cursor = conn.cursor()
    def exact_time(tiet_bat_dau: int, so_tiet: int):
        gio_hoc = {}
        tiet = 1
        start = 7
        while tiet <= 16:
            if tiet == 5:
                start = 12
            gio_bat_dau = f'{start}.00'
            gio_ket_thuc = f'{start}.50'
            gio_hoc.update({tiet: f'{gio_bat_dau} - {gio_ket_thuc}'})
            tiet += 1
            start += 1

        gio_bat_dau = gio_hoc[tiet_bat_dau].split(" - ")[0]
        gio_ket_thuc = gio_hoc[tiet_bat_dau + so_tiet].split(" - ")[1]
        return gio_bat_dau, gio_ket_thuc

    def exact_day(text: str, thu: int):
        ngay_bat_dau, ngay_ket_thuc = map(str, text.split(" - "))
        ngay_bat_dau = datetime.strptime(ngay_bat_dau, "%d/%m/%y")
        ngay_ket_thuc = datetime.strptime(ngay_ket_thuc, "%d/%m/%y")

        ngay_chinh_xac = ngay_bat_dau + timedelta(thu - 2)
        return ngay_chinh_xac.strftime("%d/%m/%Y")
    
    xls = pd.ExcelFile(file_path)
    cates = {
        "Mã môn học": "ma_hoc_phan",
        "Tên môn học/ học phần": "ten_hoc_phan",
        "Nhóm": "thu_tu_lop",
        "Tổ TH": "thu_tu_nhom",
        "Thứ": "thu",
        "Tiết BĐ": "tiet_bat_dau",
        "Số tiết": "so_tiet",
        "Phòng": "phong",
        "Mã giảng viên mới": "ma_can_bo",
        "Giảng viên giảng dạy": "ho_ten",
        "Nhà": "nha"
    }

    lich_hoc = []
    for i in range(len(xls.sheet_names)):
        sheetname = xls.sheet_names[i]
        df = pd.read_excel(xls, sheetname, dtype = str)
        df = df.iloc[8:, :-15]

        headers = []
        cols_to_drop = []

        for i in range(len(df.columns)):
            col = df.columns[i]
            header = df[col].iloc[0]
            
            if header in ("TT", "Tổ hợp", "Kíp", "Ghi chú", "Tháng", "Hệ", "Khoa", "Bộ môn", "Hình thức thi"):
                cols_to_drop.append(col)

        df = df.drop(columns = cols_to_drop)
        current_month: str = None
        for col in df.columns:
            col_3_row = df[col].iloc[0:3]
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

        for i in range(len(headers)):
            header = headers[i]
            if "-" not in header:
                continue
            header = header.split()[0]
            temp = header.split("-")
            try:
                if len(temp) != 3:
                    ngay_bat_dau, ngay_ket_thuc, nam, thang = temp[0], temp[1], temp[4], temp[3]
                else:    
                    ngay_bat_dau, ngay_ket_thuc, thang_nam = temp[0], temp[1], temp[2].split("/")
                    thang, nam = thang_nam[0], thang_nam[1]

                bat_dau  = f'{ngay_bat_dau}/{thang}/{nam}'
                if int(ngay_ket_thuc) < int(ngay_bat_dau):
                    if int(thang) + 1 > 12:
                        thang, nam = "1", f"{int(nam) + 1}" 
                    else:
                        thang = f"{int(thang) + 1}"
                ket_thuc = f'{ngay_ket_thuc}/{thang}/{nam}' 
                headers[i] = f'{bat_dau} - {ket_thuc}'
            except:
                print(header)
        df = df.iloc[4:]

        for index, row in df.iterrows():
            id = 0
            thu: int = None
            tiet_bat_dau: int = None
            so_tiet: int = None
            time: str = None
            startTime: str = None 
            endTime: str = None

            temp = {}
            lich = []
            for col in df.columns:
                value = row[col]
                ca = headers[id]
                if ca in cates.keys():
                    ca = cates[ca]
                    if ca == "thu_tu_nhom" and pd.isna(value):
                        value = "00"
                    if ca == "thu":
                        thu = int(value)
                        id += 1
                        continue
                    if ca == "tiet_bat_dau":
                        tiet_bat_dau = int(value)
                    if ca == "so_tiet":
                        so_tiet = int(value)
                    if tiet_bat_dau and so_tiet:
                        startTime, endTime = exact_time(tiet_bat_dau, so_tiet)
                        temp.update({"startTime": startTime})
                        temp.update({"endTime": endTime})
                    temp.update({ca: value})
                else:
                    if pd.isna(value):
                        id += 1
                        continue
                    day = exact_day(ca, thu)
                    lich.append(day)
                id += 1
            temp.update({"day": lich})
            lich_hoc.append(temp)

    cursor.execute(f"SELECT id FROM lichhoc")
    ids = cursor.fetchall()
    p = len(ids)
    conn = get_conn()
    cursor = conn.cursor()
    id = 0
    for i in range(len(lich_hoc)):
        temp = lich_hoc[i]
        ma_lop_tin_chi = f"{temp['ma_hoc_phan']}-{temp['thu_tu_lop']}"
        thu_tu_nhom = temp['thu_tu_nhom']
        if thu_tu_nhom == "00":
            ma_nhom_tin_chi = f"{ma_lop_tin_chi}"
        else:
            ma_nhom_tin_chi = f"{ma_lop_tin_chi}-{temp['thu_tu_nhom']}"
        hoc_phan = {
            "ma_hoc_phan": temp["ma_hoc_phan"],
            "ten_hoc_phan": temp["ten_hoc_phan"]
        }
        can_bo = {
            "ma_can_bo": temp['ma_can_bo'],
            "ho_ten": temp["ho_ten"]
        }
        cursor.execute(f'''INSERT OR IGNORE
                        INTO canbo ({", ".join([_ for _ in can_bo.keys()])}) VALUES
                        ({", ".join(["?" for _ in can_bo.keys()])})''', 
                        tuple(can_bo.values()))
        conn.commit()


        lop_tin_chi = {
            "ma_lop_tin_chi": ma_lop_tin_chi,
            "ma_hoc_phan": hoc_phan["ma_hoc_phan"],
            "thu_tu_lop": temp["thu_tu_lop"],
            "hoc_ky": "20241"
        }
        canbo_loptinchi = {
            "id": id,
            "ma_can_bo": can_bo["ma_can_bo"],
            "ma_lop_tin_chi": lop_tin_chi["ma_lop_tin_chi"],
        }

        cursor.execute(f"SELECT * FROM canbo_loptinchi WHERE ma_can_bo = ? AND ma_lop_tin_chi = ?", (canbo_loptinchi["ma_can_bo"], canbo_loptinchi["ma_lop_tin_chi"]))
        check = cursor.fetchone()
        if not check:
            cursor.execute(f'''INSERT
                            INTO canbo_loptinchi ({", ".join([_ for _ in canbo_loptinchi.keys()])}) VALUES
                            ({", ".join(["?" for _ in canbo_loptinchi.keys()])})''', 
                            tuple(canbo_loptinchi.values()))
            conn.commit()
            id += 1

        nhom_tin_chi = {
            "ma_nhom_tin_chi": ma_nhom_tin_chi,
            "ma_lop_tin_chi": lop_tin_chi["ma_lop_tin_chi"],
            "thu_tu_nhom": thu_tu_nhom
        }
        cursor.execute(f'''INSERT OR IGNORE
                        INTO nhomtinchi ({", ".join([_ for _ in nhom_tin_chi.keys()])}) VALUES
                        ({", ".join(["?" for _ in nhom_tin_chi.keys()])})''', 
                        tuple(nhom_tin_chi.values()))
        conn.commit()

        for lich in temp["day"]:
            thuc_hanh = {
                "id": p,
                "ma_nhom_tin_chi": nhom_tin_chi["ma_nhom_tin_chi"],
                "ngay_hoc": lich,
                "tiet_bat_dau": temp['tiet_bat_dau'],
                "so_tiet": temp['so_tiet'],
                "gio_bat_dau": temp['startTime'],
                "gio_ket_thuc": temp['endTime'],
                "phong": temp['phong'],
                "nha": temp['nha']
            }
            cursor.execute(f'''INSERT OR IGNORE
                        INTO lichhoc ({", ".join([_ for _ in thuc_hanh.keys()])}) VALUES
                        ({", ".join(["?" for _ in thuc_hanh.keys()])})''', 
                        tuple(thuc_hanh.values()))
            conn.commit()
            print(f'INSERT THANH CONG {thuc_hanh["ma_nhom_tin_chi"]}')
            p += 1
    conn.close()
    # with open(os.path.join(os.getcwd(), "app", "data", "lichThucHanh", "lichThucHanh.json"), 'w') as file:
    #     json.dump(results, file, ensure_ascii=False, indent = 4)
        
def import_lichHoc_into_DB(datas):
    pass
    # with open(os.path.join(os.getcwd(), "app", "data", "lichThucHanh", "lichThucHanh.json"), 'r') as file:
    #     return json.load(file)

def get_current_week_start_end(ngay=None):
    if ngay != None:
        today = datetime.strptime(ngay, "%d-%m-%Y")
    else:
        today = date.today()
    # Get the ISO week number and year
    iso_week = today.isocalendar()
    # Calculate the start of the week based on the ISO week
    week_start = today + timedelta(days=-iso_week[2] + 1)
    week_end = week_start + timedelta(days=6)    
    return week_start.strftime("%d/%m/%Y"), week_end.strftime("%d/%m/%Y")

def get_lichHoc (cccd, db, ngay=None):
    all_lichhocs = []
    sinhvien = db.query(models.SinhVien).filter(models.SinhVien.cccd == cccd).first()
    sinhvien_nhomtinchies = db.query(models.SinhVien_NhomTinChi).filter(models.SinhVien_NhomTinChi.ma_sinh_vien == sinhvien.ma_sinh_vien).all()
    week_start, week_end = get_current_week_start_end(ngay)
    for sinhvien_nhomtinchi in sinhvien_nhomtinchies:
        print(sinhvien_nhomtinchi.ma_sinh_vien, sinhvien_nhomtinchi.ma_nhom_tin_chi)
        lichhocs = db.query(models.LichHoc).filter(
            models.LichHoc.ma_nhom_tin_chi == sinhvien_nhomtinchi.ma_nhom_tin_chi
        ).all()
        nhomtinchi = db.query(models.NhomTinChi).filter(
            models.NhomTinChi.ma_nhom_tin_chi == sinhvien_nhomtinchi.ma_nhom_tin_chi
        ).first()
        loptinchi = db.query(models.LopTinChi).filter(
            models.LopTinChi.ma_lop_tin_chi == nhomtinchi.ma_lop_tin_chi
        ).first()
        hocphan = db.query(models.HocPhan).filter(
            models.HocPhan.ma_hoc_phan == loptinchi.ma_hoc_phan
        ).first()
        instructor = ""
        canbo_loptinchies = db.query(models.CanBo_LopTinChi).filter(
            models.CanBo_LopTinChi.ma_lop_tin_chi == loptinchi.ma_lop_tin_chi
        ).all()
        for canbo_loptinchi in canbo_loptinchies:
            canbo = db.query(models.CanBo).filter(
                models.CanBo.ma_can_bo == canbo_loptinchi.ma_can_bo
            ).first()
            instructor += f"{str(canbo.ho_ten).title()}, "
        if len(instructor) > 3:
            instructor = instructor[:-2]
        for lichhoc in lichhocs:
            room = f"{lichhoc.phong}"
            if lichhoc.nha != None and lichhoc.nha != "":
                 room += f" - {lichhoc.nha}"
            data_tmp = {
                "eventType": "Lịch học",
                "creditClass": lichhoc.ma_nhom_tin_chi,
                "courseName": hocphan.ten_hoc_phan,
                "ngay_hoc": lichhoc.ngay_hoc,
                "startTime": f"{lichhoc.gio_bat_dau.replace('.', ':')} {lichhoc.ngay_hoc}",
                "endTime": f"{lichhoc.gio_ket_thuc.replace('.', ':')} {lichhoc.ngay_hoc}",
                "room": room,
                "instructor": instructor,
            }
            if datetime.strptime(lichhoc.ngay_hoc, "%d/%m/%Y") >= datetime.strptime(week_start, "%d/%m/%Y") and datetime.strptime(lichhoc.ngay_hoc, "%d/%m/%Y") <= datetime.strptime(week_end, "%d/%m/%Y"):
                all_lichhocs.append(data_tmp)
    
    print(week_start, week_end)
    print(len(all_lichhocs))
    return sorted(all_lichhocs, key=lambda lichhoc: datetime.strptime(lichhoc["ngay_hoc"], "%d/%m/%Y"))

def get_lichGiangDay (cccd, db, ngay=None):
    all_lichgiangdays = []
    print(cccd)
    canbo = db.query(models.CanBo).filter(models.CanBo.cccd == cccd).first()
    canbo_loptinchies = db.query(models.CanBo_LopTinChi).filter(models.CanBo_LopTinChi.ma_can_bo == canbo.ma_can_bo).all()
    week_start, week_end = get_current_week_start_end(ngay)
    for canbo_loptinchi in canbo_loptinchies:
        loptinchi = db.query(models.LopTinChi).filter(
            models.LopTinChi.ma_lop_tin_chi == canbo_loptinchi.ma_lop_tin_chi
        ).first()
        hocphan = db.query(models.HocPhan).filter(
            models.HocPhan.ma_hoc_phan == loptinchi.ma_hoc_phan
        ).first()
        nhomtinchies = db.query(models.NhomTinChi).filter(
            models.NhomTinChi.ma_lop_tin_chi == loptinchi.ma_lop_tin_chi
        ).all()
        for nhomtinchi in nhomtinchies:
            lichgiangdays = db.query(models.LichHoc).filter(
                models.LichHoc.ma_nhom_tin_chi == nhomtinchi.ma_nhom_tin_chi
            ).all()
            instructor = ""
            tmp_canbo_loptinchies = db.query(models.CanBo_LopTinChi).filter(
                models.CanBo_LopTinChi.ma_lop_tin_chi == loptinchi.ma_lop_tin_chi
            ).all()
            for tmp_canbo_loptinchi in tmp_canbo_loptinchies:
                canbo = db.query(models.CanBo).filter(
                    models.CanBo.ma_can_bo == tmp_canbo_loptinchi.ma_can_bo
                ).first()
                instructor += f"{str(canbo.ho_ten).title()}, "
            if len(instructor) > 3:
                instructor = instructor[:-2]
            for lichgiangday in lichgiangdays:
                room = f"{lichgiangday.phong}"
                if lichgiangday.nha != None and lichgiangday.nha != "":
                    room += f" - {lichgiangday.nha}"
                data_tmp = {
                    "eventType": "Lịch giảng dạy",
                    "creditClass": lichgiangday.ma_nhom_tin_chi,
                    "courseName": hocphan.ten_hoc_phan,
                    "ngay_hoc": lichgiangday.ngay_hoc,
                    "startTime": f"{lichgiangday.gio_bat_dau.replace('.', ':')} {lichgiangday.ngay_hoc}",
                    "endTime": f"{lichgiangday.gio_ket_thuc.replace('.', ':')} {lichgiangday.ngay_hoc}",
                    "room": room,
                    "instructor": instructor,
                }
                if datetime.strptime(lichgiangday.ngay_hoc, "%d/%m/%Y") >= datetime.strptime(week_start, "%d/%m/%Y") and datetime.strptime(lichgiangday.ngay_hoc, "%d/%m/%Y") <= datetime.strptime(week_end, "%d/%m/%Y"):
                    all_lichgiangdays.append(data_tmp)
    
    print(week_start, week_end)
    print(len(all_lichgiangdays))
    return sorted(all_lichgiangdays, key=lambda lichgiangday: datetime.strptime(lichgiangday["ngay_hoc"], "%d/%m/%Y"))

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