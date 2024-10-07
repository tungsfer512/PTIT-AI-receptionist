import os
import time
import sqlite3
import pandas as pd
from datetime import datetime

def get_conn():
    conn = sqlite3.connect(os.path.join(os.getcwd(), "app", "database", "kiosk.db"))
    return conn
def insert_sinhvien():
    xls = pd.ExcelFile("./test.xlsx")
    conn = get_conn()
    cursor = conn.cursor()

    cate = {
        0: "ma_sinh_vien",
        1: "gioi_tinh",
        2: "quoc_tich",
        3: "dan_toc",
        4: "ton_giao",
        5: "ngay_sinh",
        6: "cccd"
    }

    sheetname = xls.sheet_names[1]
    df = pd.read_excel(xls, sheetname, dtype = str)
    for index, row in df.iterrows():
        id = 0
        sinh_vien = {}
        for col in df.columns:
            value = str(row[col])
            if value == "nan":
                id += 1
                continue
            ca = cate[id]
            if ca == "ngay_sinh":
                value = datetime.strptime(value, "%d/%m/%Y").date()
            sinh_vien.update({ca: value})
            id += 1
        cursor.execute(f'''INSERT OR IGNORE
                       INTO SinhVien ({", ".join([_ for _ in sinh_vien.keys()])}) VALUES
                       ({", ".join(["?" for _ in sinh_vien.keys()])})
                       ''', tuple(sinh_vien.values()))
        conn.commit()
        print(f"INSERT THANH CONG {sinh_vien['ma_sinh_vien']}")
        print()
        time.sleep(0.2)
    conn.close()

def insert():
    xls = pd.ExcelFile("./test.xlsx")
    du_lieu_lop_tin_chi = [0, 2, 3, 4, 5, 6, 7]
    conn = get_conn()
    cursor = conn.cursor()
    cate : dict = None
    id = 0
    for i in du_lieu_lop_tin_chi:
        if i == 0:
            cate = {
                0: ["SinhVien", "ma_sinh_vien"],
                1: ["SinhVien", "ho_ten"],
                2: ["SinhVien", "lop_hanh_chinh"],
                3: ["HocPhan", "ma_hoc_phan"],
                4: ["HocPhan", "ten_hoc_phan"],
                5: ["HocPhan", "so_tin_chi"],
                6: ["LopTinChi", "thu_tu_lop"],
                7: ['NhomTinChi', 'thu_tu_nhom'],
                8: ['LopTinChi', 'hoc_ky']
            }
        else:
            cate = {
                        0: ["SinhVien", "ma_sinh_vien"],
                        1: ["SinhVien", "ho_ten"],
                        2: ["SinhVien", "cccd"],
                        3: ["SinhVien", "lop_hanh_chinh"],
                        4: ["HocPhan", "ma_hoc_phan"],
                        5: ["HocPhan", "ten_hoc_phan"],
                        6: ["HocPhan", "so_tin_chi"],
                        7: ["LopTinChi", "thu_tu_lop"],
                        8: ['NhomTinChi', 'thu_tu_nhom'],
                        9: ['LopTinChi', 'hoc_ky']
                    }
        sheetname = xls.sheet_names[i]
        df = pd.read_excel(xls, sheetname, dtype = str)
        for index, row in df.iterrows():
            sinhvien = {}
            hocphan = {}
            loptinchi = {}
            nhomtinchi = {}
            sinhvien_nhomtinchi = {}
            for col in df.columns:
                check = cate[id]
                table = check[0]
                temp = check[1]
                value = str(row[col])
                if value == 'nan' or temp == 'cccd':
                    if id == len(list(cate)) - 1:
                        id = 0
                    else:
                        id += 1
                    continue
                
                if table == 'SinhVien':
                    sinhvien.update({temp: value})
                if table == 'HocPhan':
                    if temp == "ma_hoc_phan":
                        loptinchi.update({temp: value})    
                    hocphan.update({temp: value})
                if table == 'LopTinChi':
                    loptinchi.update({temp: value})
                if table == 'NhomTinChi':
                    nhomtinchi.update({temp: value})
                    
                if id == len(list(cate)) - 1:
                    id = 0
                else:
                    id += 1
            if "ma_hoc_phan" in loptinchi.keys() and "thu_tu_lop" in loptinchi.keys():
                ma_lop_tin_chi = f'{loptinchi["ma_hoc_phan"]}-{loptinchi["thu_tu_lop"]}'
                loptinchi.update({"ma_lop_tin_chi": ma_lop_tin_chi})
                nhomtinchi.update({"ma_lop_tin_chi": ma_lop_tin_chi})
            
            if 'ma_lop_tin_chi' in nhomtinchi.keys():
                if 'thu_tu_nhom' in nhomtinchi.keys():
                    ma_nhom_tin_chi = f"{nhomtinchi['ma_lop_tin_chi']}-{nhomtinchi['thu_tu_nhom']}"
                else:
                    nhomtinchi.update({"thu_tu_nhom": "00"})
                    ma_nhom_tin_chi = f"{nhomtinchi['ma_lop_tin_chi']}"
                nhomtinchi.update({'ma_nhom_tin_chi': ma_nhom_tin_chi})
                sinhvien_nhomtinchi.update({'ma_nhom_tin_chi': ma_nhom_tin_chi})
                sinhvien_nhomtinchi.update({'ma_sinh_vien': sinhvien['ma_sinh_vien']})
                        
            if sinhvien == {} or hocphan == {} or loptinchi == {} or nhomtinchi == {} or sinhvien_nhomtinchi == {}:
                id = 0
                sinhvien = {}
                hocphan = {}
                loptinchi = {}
                nhomtinchi = {}
                sinhvien_nhomtinchi = {}
                continue
            
            cursor.execute('UPDATE SinhVien SET ho_ten = ?, lop_hanh_chinh = ? WHERE ma_sinh_vien = ?', (sinhvien['ho_ten'], sinhvien['lop_hanh_chinh'], sinhvien['ma_sinh_vien']))
            conn.commit()
            print(f"Luu thanh cong sinh vien {sinhvien['ma_sinh_vien']}")
            
            cursor.execute(f'''INSERT OR IGNORE
                        INTO HocPhan ({", ".join([x for x in hocphan.keys()])}) VALUES 
                        ({", ".join(["?" for _ in hocphan.keys()])})''', 
                        tuple(hocphan.values()))
            conn.commit()
            print(f"Luu thanh cong hoc phan {hocphan['ten_hoc_phan']}")
            
            cursor.execute(f'''INSERT OR IGNORE
                        INTO LopTinChi ({", ".join([x for x in loptinchi.keys()])}) VALUES 
                        ({", ".join(["?" for _ in loptinchi.keys()])})''', 
                        tuple(loptinchi.values()))
            conn.commit()
            print(f"Luu thanh cong lop tin chi {loptinchi['ma_lop_tin_chi']}")
            
            cursor.execute(f'''INSERT OR IGNORE 
                        INTO NhomTinChi ({", ".join([x for x in nhomtinchi.keys()])}) VALUES 
                        ({", ".join(["?" for _ in nhomtinchi.keys()])})''', 
                        tuple(nhomtinchi.values()))
            conn.commit()
            print(f"Luu thanh cong nhom tin chi {nhomtinchi['ma_nhom_tin_chi']}")

            cursor.execute(f'''INSERT OR IGNORE 
                        INTO SinhVien_NhomTinChi ({", ".join([x for x in sinhvien_nhomtinchi.keys()])}) VALUES 
                        ({", ".join(["?" for _ in sinhvien_nhomtinchi.keys()])})''', 
                        tuple(sinhvien_nhomtinchi.values()))
            conn.commit()
            print(f"Luu thanh cong sinh vien - nhom tin chi")
            print()
            time.sleep(0.3)
    conn.close()

def inser_canbo():
    xls = pd.ExcelFile("./test2.xlsx")
    conn = get_conn()
    cursor = conn.cursor()
    cate = {
        1: "ma_hoc_phan",
        5: "thu_tu_lop",
        6: "thu_tu_nhom",
        7: "si_so_toi_da",
        9: "ma_can_bo",
        10: "ho_ten",
        11: "loai_giao_vien"
    }
    for i in range(2):
        sheetname = xls.sheet_names[i]
        df = pd.read_excel(xls, sheetname, dtype = str)
        for index, row in df.iterrows():
            id = 0
            loptinchi = {}
            canbo = {}
            nhomtinchi = {}
            for col in df.columns:
                if id not in cate.keys():
                    id += 1
                    continue
                value = str(row[col])
                if value == "nan":
                    id += 1
                    continue
                ca = cate[id]
                if id in (1, 5, 9):
                    loptinchi.update({ca: value})
                if id in (6, 7):
                    nhomtinchi.update({ca: value})
                if id in (9, 10, 11):
                    canbo.update({ca: value})
                id += 1

            cursor.execute(f'''INSERT OR IGNORE
                           INTO CanBo ({", ".join([_ for _ in canbo.keys()])}) VALUES
                            ({", ".join(["?" for _ in canbo.keys()])})''', tuple(canbo.values()))
            conn.commit()
            print(f"INSERT: {canbo['ho_ten']}")

            cursor.execute(f'''INSERT 
                           INTO CanBo_LopTinChi (ma_can_bo, ma_lop_tin_chi) VALUES
                           (?, ?)''',
                            (loptinchi["ma_can_bo"], f'{loptinchi["ma_hoc_phan"]}-{loptinchi["thu_tu_lop"]}'))
            conn.commit()
            print(f"UPDATE: {loptinchi['ma_hoc_phan']}")

            if "thu_tu_nhom" in nhomtinchi.keys():
                temp = nhomtinchi["thu_tu_nhom"]
            else:
                temp = "00"
            cursor.execute(f'''UPDATE NhomTinChi
                           SET si_so_toi_da = ?
                           WHERE ma_lop_tin_chi = ? AND thu_tu_nhom = ?''',
                           (nhomtinchi["si_so_toi_da"], f'{loptinchi["ma_hoc_phan"]}-{loptinchi["thu_tu_lop"]}', temp))
            conn.commit()
            print(f"UPDATE THANH CONG")
            time.sleep(0.1)
            print()
    conn.close()

inser_canbo()
insert()
insert_sinhvien()

