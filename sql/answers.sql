-- ข้อที่ 1: หาอุณหภูมิเฉลี่ย, สูงสุด, และต่ำสุด ของแต่ละเมืองในแต่ละวัน

SELECT 
    c.city_name,
    DATE(wf.forecast_time) AS forecast_date,
    ROUND(AVG(wf.temperature_2m), 2) AS avg_temp,
    MAX(wf.temperature_2m) AS max_temp,
    MIN(wf.temperature_2m) AS min_temp
FROM cities c
JOIN weather_forecasts wf 
    ON c.city_id = wf.city_id
GROUP BY c.city_id, DATE(wf.forecast_time)
ORDER BY c.city_name, forecast_date;

-- ข้อที่ 2: หาเมืองที่อุณหภูมิแกว่งมากที่สุด (Max ลบ Min กว้างที่สุด) ในช่วง 7 วันนี้

SELECT 
    c.city_name,
    ROUND(MAX(wf.temperature_2m) - MIN(wf.temperature_2m), 2) AS temp_swing,
    MAX(wf.temperature_2m) AS max_temp,
    MIN(wf.temperature_2m) AS min_temp
FROM cities c
JOIN weather_forecasts wf 
    ON c.city_id = wf.city_id
GROUP BY c.city_id
ORDER BY temp_swing DESC
LIMIT 1;

-- ข้อที่ 3: หา "ชั่วโมง" ที่มีโอกาสฝนตกสูงสุดของแต่ละเมือง ในแต่ละวัน

WITH RankedData AS (
    SELECT
        c.city_name,
        wf.forecast_time,
        wf.precipitation_probability,
        ROW_NUMBER() OVER (
            PARTITION BY c.city_id, DATE(wf.forecast_time) 
            ORDER BY wf.precipitation_probability DESC
        ) AS rn
    FROM cities c
    JOIN weather_forecasts wf 
        ON c.city_id = wf.city_id
)
SELECT
    city_name,
    forecast_time,
    precipitation_probability
FROM RankedData
WHERE rn = 1
ORDER BY city_name, forecast_time;

-- ข้อที่ 4: หาความต่างของอุณหภูมิเฉลี่ยรายวันเทียบกับวันก่อนหน้าของแต่ละเมือง

WITH DailyAvg AS (
    SELECT 
        c.city_name,
        DATE(wf.forecast_time) AS forecast_date,
        ROUND(AVG(wf.temperature_2m), 2) AS avg_temp
    FROM cities c
    JOIN weather_forecasts wf 
        ON c.city_id = wf.city_id
    GROUP BY c.city_id, DATE(wf.forecast_time)
),
LaggedDaily AS (
    SELECT
        city_name,
        forecast_date,
        avg_temp,
        LAG(avg_temp, 1) OVER (
            PARTITION BY city_name 
            ORDER BY forecast_date
        ) AS prev_day_avg_temp
    FROM DailyAvg
)
SELECT 
    city_name,
    forecast_date,
    avg_temp,
    prev_day_avg_temp,
    ROUND(avg_temp - prev_day_avg_temp, 2) AS temp_diff
FROM LaggedDaily
ORDER BY city_name, forecast_date;
