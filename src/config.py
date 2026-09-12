# src/config.py
# กำหนดค่าคงที่และ Path สำหรับใช้งานใน Data Pipeline สภาพอากาศ

import os

# ไดเรกทอรีหลักของโปรเจกต์ (weather-data-pipeline/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Path ไฟล์และโฟลเดอร์ต่างๆ
DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_DATA_DIR = os.path.join(DATA_DIR, "raw")
PROCESSED_DATA_DIR = os.path.join(DATA_DIR, "processed")
DB_PATH = os.path.join(DATA_DIR, "weather.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "sql", "schema.sql")
LOG_PATH = os.path.join(BASE_DIR, "pipeline.log")

# URL สำหรับ Open-Meteo API
API_URL = "https://api.open-meteo.com/v1/forecast"

# รายชื่อ 5 เมืองหลักในประเทศไทย พร้อมพิกัดละติจูด (Latitude) และลองจิจูด (Longitude)
CITIES = [
    {
        "name": "Bangkok",
        "latitude": 13.75,
        "longitude": 100.50,
    },
    {
        "name": "Chiang Mai",
        "latitude": 18.79,
        "longitude": 98.98,
    },
    {
        "name": "Khon Kaen",
        "latitude": 16.44,
        "longitude": 102.83,
    },
    {
        "name": "Chonburi",
        "latitude": 13.36,
        "longitude": 100.98,
    },
    {
        "name": "Songkhla",
        "latitude": 7.20,
        "longitude": 100.60,
    },
]
