# run_queries.py
# สคริปต์สำหรับอ่านคำสั่ง SQL จาก sql/answers.sql และรันกับ data/weather.db
# พร้อมทั้งส่งออกผลลัพธ์ (Export) เป็นไฟล์ CSV เก็บไว้ใน data/processed/

import sqlite3
import pandas as pd
import re
import sys
import os

# ตั้งค่าการแสดงผล UTF-8 บน Windows console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# กำหนด Path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "weather.db")
SQL_PATH = os.path.join(BASE_DIR, "sql", "answers.sql")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")

# ตั้งค่าให้ Pandas แสดงผลให้เต็มหน้าจอ
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 1000)
pd.set_option("display.max_rows", 50)

# กำหนดชื่อไฟล์ CSV ปลายทางสำหรับแต่ละข้อ
CSV_FILENAMES = {
    1: "q1_daily_temperatures.csv",
    2: "q2_temperature_swing.csv",
    3: "q3_daily_rain_peaks.csv",
    4: "q4_temperature_diff.csv"
}


def extract_questions_and_queries(sql_content):
    """
    แยกข้อความใน answers.sql ออกเป็นแต่ละข้อตามหัวข้อ '-- ข้อที่ X:'
    """
    matches = list(re.finditer(r"--\s*(ข้อที่\s*\d+[^\n]*)", sql_content))
    
    sections = []
    for i, match in enumerate(matches):
        title = match.group(1).strip()
        start_pos = match.end()
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(sql_content)
        
        body = sql_content[start_pos:end_pos]
        
        # ตัด comment และบรรทัดว่างออก
        lines = []
        for line in body.splitlines():
            stripped = line.strip()
            if not stripped.startswith("--") and stripped != "":
                lines.append(line)
        query = "\n".join(lines).strip()
        sections.append((title, query))
        
    return sections


def main():
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] ไม่พบไฟล์ฐานข้อมูลที่: {DB_PATH}")
        return

    if not os.path.exists(SQL_PATH):
        print(f"[ERROR] ไม่พบไฟล์ SQL ที่: {SQL_PATH}")
        return

    # สร้างโฟลเดอร์ data/processed/ หากยังไม่มี
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    with open(SQL_PATH, "r", encoding="utf-8") as f:
        sql_content = f.read()

    sections = extract_questions_and_queries(sql_content)
    conn = sqlite3.connect(DB_PATH)

    print("================================================================================")
    print("ผลการทดสอบรันคำสั่ง SQL จากไฟล์ sql/answers.sql และส่งออกข้อมูลไปยัง data/processed/")
    print("================================================================================")

    target_q = None
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        target_q = int(sys.argv[1])

    for idx, (title, query) in enumerate(sections, 1):
        if target_q and idx != target_q:
            continue

        print(f"\n>>> {title}")
        print("-" * 80)

        if not query:
            print("[สถานะ] ยังไม่ได้เขียนคำสั่ง Query ในข้อนี้ (ว่างอยู่)")
            continue

        print("คำสั่ง SQL ที่รัน:")
        print(query)
        print("-" * 80)

        try:
            df = pd.read_sql_query(query, conn)
            print(f"[ผลลัพธ์] พบข้อมูลทั้งหมด {len(df)} แถว:")
            if len(df) > 0:
                print(df.to_string(index=False))

                # ส่งออกข้อมูลเป็นไฟล์ CSV ลง data/processed/
                csv_filename = CSV_FILENAMES.get(idx, f"q{idx}_result.csv")
                csv_path = os.path.join(PROCESSED_DIR, csv_filename)
                df.to_csv(csv_path, index=False, encoding="utf-8")
                print(f"[บันทึกไฟล์] บันทึกผลลัพธ์เรียบร้อย: {csv_path}")
            else:
                print("(ไม่มีข้อมูลส่งกลับมา)")
        except Exception as e:
            print(f"[SQL Error] เกิดข้อผิดพลาดทางไวยากรณ์ (Syntax / Operational Error):")
            print(f"-> {e}")

    conn.close()
    print("\n================================================================================")
    print("สิ้นสุดการตรวจสอบคำตอบและการบันทึกไฟล์")
    print("================================================================================")


if __name__ == "__main__":
    main()
