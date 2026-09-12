-- 1. ตารางเก็บข้อมูลเมือง (Master / Dimension Table)
CREATE TABLE IF NOT EXISTS cities (
    city_id INTEGER PRIMARY KEY AUTOINCREMENT,
    city_name TEXT UNIQUE NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL
);
-- 2. ตารางเก็บข้อมูลสภาพอากาศรายชั่วโมง (Fact Table)
CREATE TABLE IF NOT EXISTS weather_forecasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    city_id INTEGER NOT NULL,
    forecast_time TEXT NOT NULL,
    temperature_2m REAL,
    precipitation_probability REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (city_id) REFERENCES cities(city_id),
    UNIQUE(city_id, forecast_time)
);