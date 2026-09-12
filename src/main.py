# src/main.py
# ตัวควบคุมหลัก (Orchestrator): สั่งรันขั้นตอน Extract -> Transform & Load พร้อมบันทึก Log

import time
import logging
import sys
import os

# ตั้งค่าการแสดงผล console ให้รองรับ UTF-8
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# ไดเรกทอรีหลักของโปรเจกต์
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from src.config import LOG_PATH, CITIES
from src.extract import extract_weather_data
from src.transform_load import transform_and_load


def setup_logging():
    """กำหนดค่า Logging บันทึกลงทั้งไฟล์ pipeline.log และแสดงผลทางหน้าจอ Terminal"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(sys.stdout)
        ]
    )


def run_pipeline():
    """ฟังก์ชันควบคุมลำดับขั้นตอนทั้งหมดของ Weather Data Pipeline"""
    setup_logging()
    start_time = time.time()

    logging.info("============================================================")
    logging.info("เริ่มต้นกระบวนการ Weather Data Pipeline (ETL)")
    logging.info("============================================================")

    extractions = extract_weather_data()
    cities_loaded, rows_loaded = transform_and_load()

    elapsed_time = time.time() - start_time
    logging.info("============================================================")
    logging.info(f"สรุปผล Pipeline: ดึงข้อมูลสำเร็จ {len(extractions)}/{len(CITIES)} เมือง")
    logging.info(f"สรุปผล Database: บันทึกข้อมูลสำเร็จ {cities_loaded}/{len(CITIES)} เมือง")
    logging.info(f"จำนวนแถวทั้งหมดที่ประมวลผล: {rows_loaded} แถว")
    logging.info(f"เวลาที่ใช้ทั้งหมด: {elapsed_time:.2f} วินาที")
    logging.info("สิ้นสุดกระบวนการ Weather Data Pipeline อย่างสมบูรณ์")
    logging.info("============================================================")


if __name__ == "__main__":
    run_pipeline()
