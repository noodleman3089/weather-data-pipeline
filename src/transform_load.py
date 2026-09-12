# src/transform_load.py
# หน้าที่: อ่านไฟล์ JSON ดิบจาก data/raw/, แปลงข้อมูล (Transform) และโหลดเข้า SQLite (Load)

import json
import sqlite3
import logging
import os
import sys

# รองรับการ import config ทั้งเวลารันตรงและรันผ่าน main.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import CITIES, DB_PATH, SCHEMA_PATH, RAW_DATA_DIR


def init_database():
    """สร้างตารางใน Database ตามไฟล์ schema.sql หากยังไม่มี"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
    logging.info("[Transform/Load] ตรวจสอบและตั้งค่าโครงสร้าง Database เรียบร้อย")


def get_or_create_city(cursor, city_name, latitude, longitude):
    """บันทึกหรือดึง city_id ของเมืองนั้นๆ (INSERT OR IGNORE เพื่อป้องกันข้อมูลซ้ำ)"""
    cursor.execute("""
        INSERT OR IGNORE INTO cities (city_name, latitude, longitude)
        VALUES (?, ?, ?)
    """, (city_name, latitude, longitude))

    cursor.execute("SELECT city_id FROM cities WHERE city_name = ?", (city_name,))
    return cursor.fetchone()[0]


def transform_data(city_id, raw_json):
    """
    แปลงข้อมูลจาก JSON (Array แยกฟิลด์) ให้เป็น List of Tuples
    รูปแบบ: (city_id, forecast_time, temperature_2m, precipitation_probability)
    """
    hourly = raw_json.get("hourly", {})
    times = hourly.get("time", [])
    temperatures = hourly.get("temperature_2m", [])
    precipitations = hourly.get("precipitation_probability", [])

    rows = []
    for t, temp, precip in zip(times, temperatures, precipitations):
        rows.append((city_id, t, temp, precip))
    return rows


def transform_and_load():
    """
    อ่านไฟล์ raw JSON ของแต่ละเมือง แปลงข้อมูล และโหลดลง SQLite
    คืนค่า (total_cities_loaded, total_rows_loaded)
    """
    logging.info("--- [Transform/Load] เริ่มต้นกระบวนการแปลงและโหลดข้อมูลเข้า Database ---")
    init_database()

    total_cities_loaded = 0
    total_rows_loaded = 0

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        for city in CITIES:
            city_name = city["name"]
            lat = city["latitude"]
            lon = city["longitude"]

            filename = f"{city_name.lower().replace(' ', '_')}_raw.json"
            file_path = os.path.join(RAW_DATA_DIR, filename)

            if not os.path.exists(file_path):
                logging.warning(f"[Transform/Load] [WARNING] ไม่พบไฟล์ข้อมูลดิบสำหรับ {city_name} ที่ {file_path}")
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    raw_json = json.load(f)

                city_id = get_or_create_city(cursor, city_name, lat, lon)
                rows = transform_data(city_id, raw_json)

                # Upsert ข้อมูลล่าสุดโดยอาศัย UNIQUE(city_id, forecast_time) เพื่อไม่ให้เกิดข้อมูลซ้ำ
                cursor.executemany("""
                    INSERT OR REPLACE INTO weather_forecasts
                    (city_id, forecast_time, temperature_2m, precipitation_probability)
                    VALUES (?, ?, ?, ?)
                """, rows)

                conn.commit()

                total_cities_loaded += 1
                total_rows_loaded += len(rows)
                logging.info(f"[Transform/Load] [SUCCESS] โหลดข้อมูล {city_name} ลง DB สำเร็จ ({len(rows)} แถว)")

            except Exception as e:
                conn.rollback()
                logging.error(f"[Transform/Load] [ERROR] เกิดข้อผิดพลาดขณะโหลดข้อมูล {city_name}: {e}")

    finally:
        conn.close()

    logging.info(f"--- [Transform/Load] เสร็จสิ้น: โหลดสำเร็จ {total_cities_loaded} เมือง (รวม {total_rows_loaded} แถว) ---")
    return total_cities_loaded, total_rows_loaded


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    transform_and_load()
