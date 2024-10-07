# File struture
```bash
├── app                                 # "app" is a Python package
│   ├── __init__.py                     # this file makes "app" a "Python package"
│   ├── main.py                         # "main" module, e.g. import app.main
│   ├── .env                            # environment
│   ├── data                            # data folder for storing data and images
│   │   ├── img                         # images folder for storing images
│   │   │   │   personal data folder    
│   │   │   └── data.json               
│   │   └── lichTuan                    
│   │       └── lichTuan.docx           
│   ├── database                        # makes "routers" a "Python subpackage"
│   │   ├── __init__.py                 
│   │   ├── database.py                
│   │   └── user.db
│   ├── routers                         # makes "routers" a "Python subpackage"
│   │   ├── __init__.py                 # this file makes "routers" a "Python package"
│   │   ├── access_data.py              # submodule for accessing data
│   │   ├── auth.py                     # submodule for authorizing users
│   │   └── face_recognition.py         # submodule for face recognition
│   ├── internal                        # "internal" is a "Python subpackage"
│   │   ├── __init__.py                 
│   │   └── admin.py                    
│   ├── internal                        # makes "internal" a "Python subpackage"
│   │   ├── __init__.py
│   │   ├── base_model.py
│   │   ├── dependencies.py
│   │   └── received_img.png
├── README.md
├── .env
├── API_management.txt                       
└── requirement.txt                           
```

## Quản lý API/WebSocket

### Access Data API

#### `<GET/ WebSocket> /api/get-identity`
- Nhận thông tin được post từ máy đọc CCCD và đẩy thẳng sang máy khách thông qua WebSocket đã kết nối từ trước đó.
    - *Dữ liệu nhận:*
    ```json
    {
        "Identity Code": "",
        "Name": "",
        "DOB": "",
        "Gender": "",
        "Nationality": "",
        "Ethnic": "",
        "Religion": "",
        "Hometown": "",
        "Permanent Address": "",
        "Identifying Features": "",
        "Card Issuance Date": "",
        "Expiration Date": ""
    }
    ```
    - *Dữ liệu trả về:*
    ```json
    {
        "Identity Code": "",
        "Name": "",
        "DOB": "",
        "Gender": "",
        "Nationality": "",
        "Ethnic": "",
        "Religion": "",
        "Hometown": "",
        "Permanent Address": "",
        "Identifying Features": "",
        "Card Issuance Date": "",
        "Expiration Date": ""
    }
    ```

#### `<POST> /api/post-personal-img`
- Nhận thông tin của khách hàng nhằm đăng ký và lưu dữ liệu khách hàng cho mục đích nhận diện sau đó.
    - *Dữ liệu nhận:*
    ```json
    {
        "b64_img": ["b64", "b64"],
        "cccd": {
            "Identity Code": "",
            "Name": "",
            "DOB": "",
            "Gender": "",
            "Nationality": "",
            "Ethnic": "",
            "Religion": "",
            "Hometown": "",
            "Permanent Address": "",
            "Identifying Features": "",
            "Card Issuance Date": "",
            "Expiration Date": ""
        },
        "role": ""
    }
    ```
    - *Dữ liệu trả về:*
    ```json
    {
        "response": "Upload successfully!" 
    }
    {
        "response": "Thông tin của quý khách đã tồn tại"
    }
    {
        "response": "err"
    }
    ```

#### `<GET> /api/get-all-data`
- Trả về toàn bộ thông tin của khách hàng đã lưu.
    - *Dữ liệu trả về:*
    ```json
    [
        {
            "embedding": "đường dẫn đến file txt lưu embedding",
            "Identity Code": "",
            "Name": "",
            "DOB": "",
            "Gender": "",
            "Hometown": "",
            "role": ""
        }
    ]
    ```

### Face Recognition API

#### `<WebSocket> /ws`
- Trả liên tục thông tin của khách hàng xuất hiện trước camera.
    - *Dữ liệu nhận:* `b64`
    - *Dữ liệu trả về:*
        - *Số lượng người:*
        ```json
        {
            "nums_of_people": "nums_of_people"
        }
        ```
        - *Thông tin khách hàng:*
        ```json
        {
            "person_datas": [
                {
                    "name1": "name1",
                    "role1": "role1"
                },
                {
                    "name2": "name2",
                    "role2": "role2"
                }
            ]
        }
        ```