# src/extract.py
# หน้าที่: ดึงข้อมูลสภาพอากาศจาก Open-Meteo API และบันทึกเป็นไฟล์ JSON ใน data/raw/

import requests
import json
import logging
import os
import sys

# รองรับการ import config ทั้งเวลารันตรงและรันผ่าน main.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import CITIES, API_URL, RAW_DATA_DIR


def save_raw_json(data, city_name):
    """บันทึกข้อมูลดิบเป็นไฟล์ JSON เก็บไว้ใน data/raw/"""
    os.makedirs(RAW_DATA_DIR, exist_ok=True)
    filename = f"{city_name.lower().replace(' ', '_')}_raw.json"
    file_path = os.path.join(RAW_DATA_DIR, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    return file_path


def extract_weather_data():
    """
    วนลูปดึงข้อมูลสภาพอากาศจาก API สำหรับทุกเมืองใน CITIES
    คืนค่าเป็น list ของ tuple (city_name, file_path) ที่ดึงสำเร็จ
    """
    logging.info("--- [Extract] เริ่มต้นกระบวนการดึงข้อมูลจาก API ---")
    successful_extractions = []

    for city in CITIES:
        city_name = city["name"]
        lat = city["latitude"]
        lon = city["longitude"]

        logging.info(f"[Extract] กำลังดึงข้อมูลเมือง: {city_name} (Lat: {lat}, Lon: {lon})")

        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": ["temperature_2m", "precipitation_probability"],
            "forecast_days": 7,
            "timezone": "Asia/Bangkok"
        }

        try:
            response = requests.get(API_URL, params=params, timeout=10)
            response.raise_for_status()
            raw_json = response.json()

            saved_path = save_raw_json(raw_json, city_name)
            successful_extractions.append((city_name, saved_path))
            logging.info(f"[Extract] [SUCCESS] บันทึกไฟล์ {city_name} เรียบร้อย: {saved_path}")

        except requests.exceptions.HTTPError as http_err:
            logging.error(f"[Extract] [HTTP Error] เมือง {city_name} ล้มเหลว: {http_err}")
        except requests.exceptions.ConnectionError as conn_err:
            logging.error(f"[Extract] [Connection Error] เมือง {city_name} ขัดข้อง: {conn_err}")
        except requests.exceptions.Timeout as timeout_err:
            logging.error(f"[Extract] [Timeout] เมือง {city_name} หมดเวลาเชื่อมต่อ: {timeout_err}")
        except Exception as e:
            logging.error(f"[Extract] [Unexpected Error] เมือง {city_name} เกิดข้อผิดพลาด: {e}")

    logging.info(f"--- [Extract] เสร็จสิ้น: ดึงข้อมูลสำเร็จ {len(successful_extractions)}/{len(CITIES)} เมือง ---")
    return successful_extractions


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    extract_weather_data()
