import pandas as pd
from datetime import datetime
import time
import os 
import sqlite3

def get_conn():
    return sqlite3.connect(os.path.join(os.getcwd(), "app", "database", "kiosk.db"))

xls = pd.ExcelFile("./test3.xlsx")

cates = {
    "Mã môn học": "ma_hoc_phan",
    "Tên môn học/ học phần": "ten_hoc_phan",
    "Nhóm": "thu_tu_lop",
    "Nhóm": "thu_tu_nhom",
    "": "thu",
    5: "tiet_bat_dau",
    6: "so_tiet",
    7: "phong",
    8: "ma_can_bo",
}

for i in range(len(xls.sheet_names)):
    sheetname = xls.sheet_names[i]
    df = pd.read_excel(xls, sheetname, dtype = str)
    df = df.iloc[3:, :-15]

    headers = []
    cols_to_drop = []

    for i in range(len(df.columns)):
        col = df.columns[i]
        header = df[col].iloc[0]
        
        if header in ("TT", "Tổ hợp", "Kíp", "Nhà", "Ghi chú", "Tháng", "Hệ", "Khoa", "Bộ môn"):
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
    df = df.iloc[3:]
    for index, row in df.iterrows():
        id = 0
        for col in df.columns:
            value = row[col]
            if pd.isna(value):
                continue
            ca = headers[id]
            id += 1
            print({ca: value})
        print()
        time.sleep(0.5)
    
