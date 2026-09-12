import sqlite3
import pandas as pd
import streamlit as st
import altair as alt
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "weather.db")

CITY_NAME_TH = {
    "Bangkok": "กรุงเทพมหานคร",
    "Chiang Mai": "เชียงใหม่",
    "Chonburi": "ชลบุรี",
    "Khon Kaen": "ขอนแก่น",
    "Songkhla": "สงขลา",
}

st.set_page_config(
    page_title="แดชบอร์ดวิเคราะห์สภาพอากาศ",
    layout="wide",
    initial_sidebar_state="expanded"
)


@st.cache_data(ttl=60)
def load_all_dashboard_data():
    """ดึงและคำนวณข้อมูลสภาพอากาศทั้งหมดจาก SQLite Database"""
    if not os.path.exists(DB_PATH):
        return None

    conn = sqlite3.connect(DB_PATH)

    query_daily = """
        SELECT 
            c.city_name AS city,
            DATE(wf.forecast_time) AS forecast_date,
            ROUND(AVG(wf.temperature_2m), 1) AS avg_temp,
            ROUND(MAX(wf.temperature_2m), 1) AS max_temp,
            ROUND(MIN(wf.temperature_2m), 1) AS min_temp,
            ROUND(MAX(wf.temperature_2m) - MIN(wf.temperature_2m), 1) AS temp_diff
        FROM cities c
        JOIN weather_forecasts wf ON c.city_id = wf.city_id
        GROUP BY c.city_name, DATE(wf.forecast_time)
        ORDER BY c.city_name, forecast_date ASC
    """
    df_daily = pd.read_sql_query(query_daily, conn)

    query_hourly = """
        SELECT 
            c.city_name AS city,
            wf.forecast_time AS forecast_time,
            DATE(wf.forecast_time) AS forecast_date,
            wf.temperature_2m AS temp,
            wf.precipitation_probability AS precip_prob
        FROM cities c
        JOIN weather_forecasts wf ON c.city_id = wf.city_id
        ORDER BY wf.forecast_time ASC
    """
    df_hourly = pd.read_sql_query(query_hourly, conn)

    query_rain_peaks = """
        WITH RankedData AS (
            SELECT
                c.city_name AS city,
                DATE(wf.forecast_time) AS forecast_date,
                TIME(wf.forecast_time) AS peak_time,
                wf.precipitation_probability AS max_precip_prob,
                ROW_NUMBER() OVER (
                    PARTITION BY c.city_id, DATE(wf.forecast_time) 
                    ORDER BY wf.precipitation_probability DESC
                ) AS rn
            FROM cities c
            JOIN weather_forecasts wf ON c.city_id = wf.city_id
        )
        SELECT city, forecast_date, peak_time, max_precip_prob
        FROM RankedData
        WHERE rn = 1
        ORDER BY city, forecast_date ASC
    """
    df_rain_peaks = pd.read_sql_query(query_rain_peaks, conn)

    query_cities = "SELECT city_name AS city FROM cities"
    df_cities = pd.read_sql_query(query_cities, conn)

    query_swings = """
        SELECT 
            c.city_name AS city,
            ROUND(MAX(wf.temperature_2m) - MIN(wf.temperature_2m), 1) AS temp_swing,
            ROUND(MAX(wf.temperature_2m), 1) AS max_temp,
            ROUND(MIN(wf.temperature_2m), 1) AS min_temp,
            ROUND(AVG(wf.temperature_2m), 1) AS avg_temp
        FROM cities c
        JOIN weather_forecasts wf ON c.city_id = wf.city_id
        GROUP BY c.city_id
        ORDER BY temp_swing DESC
    """
    df_swings = pd.read_sql_query(query_swings, conn)

    query_lag = """
        WITH DailyAvg AS (
            SELECT 
                c.city_name AS city,
                DATE(wf.forecast_time) AS forecast_date,
                ROUND(AVG(wf.temperature_2m), 1) AS avg_temp
            FROM cities c
            JOIN weather_forecasts wf ON c.city_id = wf.city_id
            GROUP BY c.city_id, DATE(wf.forecast_time)
        ),
        LaggedDaily AS (
            SELECT
                city,
                forecast_date,
                avg_temp,
                LAG(avg_temp, 1) OVER (
                    PARTITION BY city 
                    ORDER BY forecast_date
                ) AS prev_day_avg_temp
            FROM DailyAvg
        )
        SELECT 
            city,
            forecast_date,
            avg_temp,
            prev_day_avg_temp,
            ROUND(avg_temp - prev_day_avg_temp, 1) AS temp_diff
        FROM LaggedDaily
        ORDER BY city, forecast_date
    """
    df_lag = pd.read_sql_query(query_lag, conn)

    conn.close()

    for df in [df_daily, df_hourly, df_rain_peaks, df_cities, df_swings, df_lag]:
        if "city" in df.columns:
            df["city"] = df["city"].map(CITY_NAME_TH).fillna(df["city"])

    return {
        "daily": df_daily,
        "hourly": df_hourly,
        "rain_peaks": df_rain_peaks,
        "cities": df_cities,
        "swings": df_swings,
        "lag": df_lag
    }


THAI_MONTHS = [
    "", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
    "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."
]


def format_thai_date(date_str):
    """แปลงวันที่ YYYY-MM-DD เป็นรูปแบบไทย เช่น '12 ก.ย. 2569'"""
    try:
        dt = datetime.strptime(str(date_str), "%Y-%m-%d")
        thai_year = dt.year + 543
        return f"{dt.day} {THAI_MONTHS[dt.month]} {thai_year}"
    except (ValueError, IndexError):
        return str(date_str)


def format_thai_date_short(date_str):
    """รูปแบบสั้นสำหรับแกนกราฟ เช่น '12 ก.ย.'"""
    try:
        dt = datetime.strptime(str(date_str), "%Y-%m-%d")
        return f"{dt.day} {THAI_MONTHS[dt.month]}"
    except (ValueError, IndexError):
        return str(date_str)


def render_day_card(date_str, avg_val, max_val, min_val, diff_val):
    """เรนเดอร์การ์ดแสดงผลอุณหภูมิประจำวันแบบกะทัดรัด"""
    with st.container(border=True):
        st.markdown(f"**{format_thai_date_short(date_str)}**")
        st.metric(label="เฉลี่ย", value=f"{avg_val} °C")
        st.caption(f"ช่วง: {min_val} - {max_val} °C")
        st.caption(f"ต่าง: {diff_val} °C")


def render_rain_card(date_str, peak_time, prob_val):
    """เรนเดอร์การ์ดแสดงผลชั่วโมงฝนตกสูงสุดประจำวันแบบกะทัดรัด"""
    with st.container(border=True):
        st.markdown(f"**{format_thai_date_short(date_str)}**")
        st.metric(label="โอกาสฝน", value=f"{prob_val:.0f}%")
        st.caption(f"เวลาพีค: {peak_time} น.")
        if prob_val >= 80:
            st.caption("เสี่ยง: สูงมาก")
        elif prob_val >= 50:
            st.caption("เสี่ยง: ปานกลาง")
        else:
            st.caption("เสี่ยง: ต่ำ")


def main():
    st.markdown("""
    <style>
        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 2rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }
        h1 {
            font-size: 1.6rem !important;
            margin-bottom: 0.1rem !important;
            padding-bottom: 0 !important;
        }
        h2, h3 {
            font-size: 1.15rem !important;
            margin-top: 0.4rem !important;
            margin-bottom: 0.3rem !important;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.35rem !important;
            font-weight: 600 !important;
        }
        [data-testid="stMetricLabel"] {
            font-size: 0.8rem !important;
            color: #64748b !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] {
            padding: 0 !important;
            margin-bottom: 0.2rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            padding: 0.5rem 0.7rem !important;
            border-radius: 8px !important;
        }
        hr {
            margin-top: 0.5rem !important;
            margin-bottom: 0.6rem !important;
        }
        button[data-baseweb="tab"] {
            padding: 0.3rem 0.9rem !important;
            font-size: 0.9rem !important;
        }
    </style>
    """, unsafe_allow_html=True)

    st.title("แดชบอร์ดวิเคราะห์สภาพอากาศ")
    st.caption("ระบบวิเคราะห์และพยากรณ์สภาพอากาศล่วงหน้า 7 วัน สำหรับ 5 จังหวัดหลัก")
    st.markdown("---")

    data = load_all_dashboard_data()

    if data is None or data["daily"].empty:
        st.error("[ERROR] ไม่พบข้อมูลในฐานข้อมูล กรุณารันคำสั่ง 'python src/main.py' ก่อน")
        return

    # -------------------------------------------------------------
    # ตัวกรองข้อมูลด้านข้าง (Sidebar Filters)
    # -------------------------------------------------------------
    st.sidebar.header("ตัวกรองข้อมูล")

    city_list = ["ทั้งหมด"] + sorted(data["daily"]["city"].unique().tolist())
    selected_city = st.sidebar.selectbox("เลือกจังหวัดที่ต้องการดูข้อมูล:", city_list)

    # -------------------------------------------------------------
    # แบ่งหน้าแสดงผลเป็น 3 แท็บ
    # -------------------------------------------------------------
    tab1, tab2, tab3 = st.tabs([
        "สรุปอุณหภูมิรายวัน",
        "เฝ้าระวังฝนตกหนัก",
        "วิเคราะห์เชิงลึก"
    ])

    # =============================================================
    # แท็บที่ 1: สรุปอุณหภูมิรายวัน (Daily Temperature Summary)
    # =============================================================
    with tab1:
        if selected_city != "ทั้งหมด":
            filtered_daily = data["daily"][data["daily"]["city"] == selected_city].copy()
            filtered_hourly = data["hourly"][data["hourly"]["city"] == selected_city].copy()
        else:
            filtered_daily = data["daily"].copy()
            filtered_hourly = data["hourly"].copy()

        # ตัวเลขสรุปภาพรวมด้านบน
        st.subheader(f"ภาพรวมอุณหภูมิ: {selected_city}")
        col1, col2, col3, col4 = st.columns(4)
        avg_t = filtered_daily["avg_temp"].mean()
        max_t = filtered_daily["max_temp"].max()
        min_t = filtered_daily["min_temp"].min()
        max_diff_t = filtered_daily["temp_diff"].max()

        col1.metric(label="อุณหภูมิเฉลี่ย", value=f"{avg_t:.1f} °C")
        col2.metric(label="สูงสุดที่พบ", value=f"{max_t:.1f} °C")
        col3.metric(label="ต่ำสุดที่พบ", value=f"{min_t:.1f} °C")
        col4.metric(label="ความต่างกลางวัน-กลางคืนสูงสุด", value=f"{max_diff_t:.1f} °C")

        st.markdown("---")

        # แสดงการ์ด
        if selected_city != "ทั้งหมด":
            st.subheader(f"พยากรณ์อุณหภูมิ 7 วัน ({selected_city})")
            rows_list = list(filtered_daily.itertuples())
            cols_7 = st.columns(len(rows_list))
            for i, r in enumerate(rows_list):
                with cols_7[i]:
                    render_day_card(r.forecast_date, r.avg_temp, r.max_temp, r.min_temp, r.temp_diff)
        else:
            st.subheader("สรุปอุณหภูมิ 5 จังหวัด (เฉลี่ย 7 วัน)")
            cols_5 = st.columns(5)
            swing_rows = list(data["swings"].iterrows())
            for i, (idx, r) in enumerate(swing_rows):
                with cols_5[i]:
                    with st.container(border=True):
                        st.markdown(f"**{r['city']}**")
                        st.metric(label="เฉลี่ย 7 วัน", value=f"{r['avg_temp']} °C")
                        st.caption(f"ช่วง: {r['min_temp']} - {r['max_temp']} °C")
                        st.caption(f"แกว่ง: {r['temp_swing']} °C")

        st.subheader("กราฟแนวโน้มการเปลี่ยนแปลงอุณหภูมิ")
        if selected_city != "ทั้งหมด":
            st.caption(f"อุณหภูมิรายชั่วโมงตลอดทั้ง 7 วัน ({selected_city})")
            chart_t = filtered_hourly.set_index("forecast_time")[["temp"]]
            chart_t.columns = ["อุณหภูมิ (°C)"]
            st.line_chart(chart_t, height=240)
        else:
            st.caption("เปรียบเทียบอุณหภูมิเฉลี่ยรายวันของทั้ง 5 จังหวัด")
            chart_daily = filtered_daily.copy()
            chart_daily["วันที่"] = chart_daily["forecast_date"].apply(format_thai_date_short)
            date_order = chart_daily["วันที่"].unique().tolist()
            melted = chart_daily.melt(id_vars=["วันที่", "city"], value_vars=["avg_temp"], value_name="อุณหภูมิเฉลี่ย (°C)")
            chart = alt.Chart(melted).mark_line(point=True).encode(
                x=alt.X("วันที่:N", sort=date_order, axis=alt.Axis(labelAngle=0)),
                y=alt.Y("อุณหภูมิเฉลี่ย (°C):Q"),
                color=alt.Color("city:N", title="จังหวัด")
            ).properties(height=240)
            st.altair_chart(chart, use_container_width=True)


    # =============================================================
    # แท็บที่ 2: เฝ้าระวังฝนตกหนัก (Rain Forecast & Risk Alert)
    # =============================================================
    with tab2:
        st.subheader(f"การเฝ้าระวังและพยากรณ์โอกาสเกิดฝน: {selected_city}")
        st.caption("วิเคราะห์จากข้อมูลชั่วโมงที่มีความเสี่ยงฝนตกสูงสุดของแต่ละวัน")

        if selected_city != "ทั้งหมด":
            filtered_rain = data["rain_peaks"][data["rain_peaks"]["city"] == selected_city].copy()
            filtered_hourly_rain = data["hourly"][data["hourly"]["city"] == selected_city].copy()
        else:
            filtered_rain = data["rain_peaks"].copy()
            filtered_hourly_rain = data["hourly"].copy()

        # ตัวเลขสรุปฝน
        col_r1, col_r2, col_r3 = st.columns(3)
        max_rain_prob = filtered_rain["max_precip_prob"].max()
        avg_rain_prob = filtered_rain["max_precip_prob"].mean()
        high_risk_days = len(filtered_rain[filtered_rain["max_precip_prob"] >= 80])

        col_r1.metric(label="โอกาสฝนตกสูงสุดที่พบ", value=f"{max_rain_prob:.0f} %")
        col_r2.metric(label="ค่าเฉลี่ยความเสี่ยงฝนรายวัน", value=f"{avg_rain_prob:.1f} %")
        col_r3.metric(label="จำนวนวันที่มีความเสี่ยงสูง (>=80%)", value=f"{high_risk_days} วัน")

        st.markdown("---")

        if selected_city != "ทั้งหมด":
            st.subheader(f"ช่วงเวลาที่ฝนตกหนักที่สุดของแต่ละวัน ({selected_city})")
            st.caption("ระบุเวลาที่ควรพกร่มหรือหลีกเลี่ยงการเดินทางกลางแจ้ง")

            rain_rows = list(filtered_rain.itertuples())
            cols_r = st.columns(len(rain_rows))
            for i, r in enumerate(rain_rows):
                with cols_r[i]:
                    render_rain_card(r.forecast_date, r.peak_time, r.max_precip_prob)

            st.markdown("---")
            st.subheader(f"กราฟเปอร์เซ็นต์โอกาสเกิดฝนรายชั่วโมง ({selected_city})")
            chart_r = filtered_hourly_rain.set_index("forecast_time")[["precip_prob"]]
            chart_r.columns = ["โอกาสเกิดฝน (%)"]
            st.bar_chart(chart_r)
        else:
            st.subheader("ตารางเปรียบเทียบชั่วโมงฝนตกสูงสุดของทั้ง 5 จังหวัด")
            pivot_rain = data["rain_peaks"].copy()
            pivot_rain["forecast_date"] = pivot_rain["forecast_date"].apply(format_thai_date)
            pivot_rain = pivot_rain.pivot(
                index="forecast_date", 
                columns="city", 
                values="max_precip_prob"
            )
            st.dataframe(pivot_rain, use_container_width=True)
            st.caption("กราฟเปรียบเทียบโอกาสเกิดฝนสูงสุดในแต่ละวันของทั้ง 5 จังหวัด")
            rain_chart_data = data["rain_peaks"].copy()
            rain_chart_data["วันที่"] = rain_chart_data["forecast_date"].apply(format_thai_date_short)
            date_order_r = rain_chart_data["วันที่"].unique().tolist()
            chart_rain = alt.Chart(rain_chart_data).mark_line(point=True).encode(
                x=alt.X("วันที่:N", sort=date_order_r, axis=alt.Axis(labelAngle=0)),
                y=alt.Y("max_precip_prob:Q", title="โอกาสฝนสูงสุด (%)"),
                color=alt.Color("city:N", title="จังหวัด")
            ).properties(height=350)
            st.altair_chart(chart_rain, use_container_width=True)

    # =============================================================
    # แท็บที่ 3: วิเคราะห์เชิงลึก (Deep Analysis)
    # =============================================================
    with tab3:
        st.subheader("ความผันผวนของอุณหภูมิ: จังหวัดไหนอากาศแปรปรวนที่สุด?")
        st.caption("เปรียบเทียบความต่างระหว่างอุณหภูมิสูงสุด-ต่ำสุดตลอด 7 วัน เรียงจากแกว่งมากที่สุด")

        col_ins1, col_ins2 = st.columns(2)

        with col_ins1:
            top_swing = data["swings"].iloc[0]
            with st.container(border=True):
                st.markdown(f"### {top_swing['city']}")
                st.metric(label="ช่วงอุณหภูมิแกว่งกว้างที่สุด", value=f"{top_swing['temp_swing']} °C")
                st.write(f"อุณหภูมิสูงสุด: {top_swing['max_temp']} °C")
                st.write(f"อุณหภูมิต่ำสุด: {top_swing['min_temp']} °C")
                st.caption("จังหวัดที่มีความแตกต่างของอุณหภูมิกลางวัน-กลางคืนกว้างที่สุดใน 7 วัน")

        with col_ins2:
            st.markdown("#### อันดับความผันผวนของอุณหภูมิทั้ง 5 จังหวัด")
            st.dataframe(
                data["swings"].rename(columns={
                    "city": "จังหวัด",
                    "temp_swing": "อุณหภูมิแกว่ง (°C)",
                    "max_temp": "สูงสุด (°C)",
                    "min_temp": "ต่ำสุด (°C)",
                    "avg_temp": "เฉลี่ย (°C)"
                }),
                use_container_width=True,
                hide_index=True
            )

        st.markdown("---")
        st.subheader("แนวโน้มอุณหภูมิเทียบกับวันก่อนหน้า")
        st.caption("แสดงว่าแต่ละวันร้อนขึ้น (+) หรือเย็นลง (-) กว่าวันก่อนหน้ากี่องศา")

        if selected_city != "ทั้งหมด":
            lag_filtered = data["lag"][data["lag"]["city"] == selected_city].copy()
        else:
            lag_filtered = data["lag"].copy()

        lag_display = lag_filtered.copy()
        lag_display["forecast_date"] = lag_display["forecast_date"].apply(format_thai_date)

        st.dataframe(
            lag_display.rename(columns={
                "city": "จังหวัด",
                "forecast_date": "วันที่",
                "avg_temp": "อุณหภูมิเฉลี่ยวันนี้ (°C)",
                "prev_day_avg_temp": "อุณหภูมิเมื่อวาน (°C)",
                "temp_diff": "ผลต่างเทียบเมื่อวาน (°C)"
            }),
            use_container_width=True,
            hide_index=True
        )

        # กราฟแสดง temp_diff ทั้ง 5 จังหวัด
        if selected_city == "ทั้งหมด":
            st.markdown("---")
            st.subheader("กราฟผลต่างอุณหภูมิเทียบวันก่อนหน้า")
            st.caption("บวก = ร้อนขึ้น, ลบ = เย็นลง")
            lag_chart = data["lag"].dropna(subset=["temp_diff"]).copy()
            lag_chart["วันที่"] = lag_chart["forecast_date"].apply(format_thai_date_short)
            date_order_l = lag_chart["วันที่"].unique().tolist()
            chart_lag = alt.Chart(lag_chart).mark_bar().encode(
                x=alt.X("วันที่:N", sort=date_order_l, axis=alt.Axis(labelAngle=0)),
                y=alt.Y("temp_diff:Q", title="ผลต่าง (°C)"),
                color=alt.Color("city:N", title="จังหวัด"),
                xOffset="city:N"
            ).properties(height=350)
            st.altair_chart(chart_lag, use_container_width=True)


if __name__ == "__main__":
    main()

