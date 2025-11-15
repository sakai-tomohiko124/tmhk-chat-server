#!/usr/bin/env python3
# coding: utf-8
"""
天気予報スクレイピングスクリプト
気象庁とウェザーニュースAPIから天気情報を取得し、3日後に自動削除される
"""

import requests
import json
from datetime import datetime, timedelta
from pathlib import Path
import logging

# 設定
JMA_API_URL = "https://www.jma.go.jp/bosai/forecast/data/forecast/130000.json"
WEATHERNEWS_API_URL = "https://site.weathernews.jp/lba/wxdata/api_data_ss1?lat=35.6812&lon=139.7671"
OUTPUT_FILE = Path(__file__).resolve().parent / "weather_info.json"
ARCHIVE_DIR = Path(__file__).resolve().parent / "archive" / "weather"
RETENTION_HOURS = 6  # 6時間後に自動削除
HOURLY_FORECAST_HOURS = 72

# 天気コードの対応表
WEATHERNEWS_CODE_MAP = {
    "100": "晴れ", "101": "晴れ時々くもり", "102": "晴れ一時雨", "103": "晴れ時々雨", "104": "晴れ一時雪",
    "105": "晴れ時々雪", "106": "晴れ一時雨か雪", "107": "晴れ時々雨か雪", "108": "晴れ一時雷雨",
    "110": "晴れ後くもり", "111": "晴れ後くもり", "112": "晴れ後雨", "113": "晴れ後時々雨", "114": "晴れ後雨",
    "115": "晴れ後雪", "116": "晴れ後時々雪", "117": "晴れ後雪", "118": "晴れ後雨か雪",
    "200": "くもり", "201": "くもり時々晴れ", "202": "くもり一時雨", "203": "くもり時々雨", "204": "くもり一時雪",
    "205": "くもり時々雪", "206": "くもり一時雨か雪", "207": "くもり時々雨か雪", "208": "くもり一時雷雨",
    "210": "くもり後晴れ", "211": "くもり後晴れ", "212": "くもり後雨", "213": "くもり後時々雨", "214": "くもり後雨",
    "215": "くもり後雪", "216": "くもり後時々雪", "217": "くもり後雪", "218": "くもり後雨か雪",
    "300": "雨", "301": "雨時々晴れ", "302": "雨時々止む", "303": "雨時々雪", "304": "雨か雪", "306": "大雨",
    "308": "雨で暴風を伴う", "309": "雨一時雪", "311": "雨後晴れ", "313": "雨後くもり", "314": "雨後雪",
    "315": "雨後雪", "321": "雨後くもり", "340": "雪か雨", "350": "雨で雷を伴う",
    "400": "雪", "401": "雪時々晴れ", "402": "雪時々止む", "403": "雪時々雨", "405": "大雪", "406": "風雪強い",
    "407": "暴風雪", "409": "雪一時雨", "411": "雪後晴れ", "413": "雪後くもり", "414": "雪後雨",
    "450": "雪で雷を伴う", "600": "晴れ", "800": "雷"
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def get_wni_weather_text(code):
    """ウェザーニュースの天気コードを日本語に変換"""
    return WEATHERNEWS_CODE_MAP.get(str(code), f"コード{code}")


def cleanup_old_archives():
    """6時間以上前のアーカイブファイルを削除"""
    if not ARCHIVE_DIR.exists():
        return
    
    cutoff_date = datetime.now() - timedelta(hours=RETENTION_HOURS)
    deleted_count = 0
    
    for file_path in ARCHIVE_DIR.glob("weather_*.json"):
        try:
            # ファイル名から日時を抽出 (weather_YYYYMMDD_HHMMSS.json)
            timestamp_str = file_path.stem.replace("weather_", "")
            file_datetime = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            
            if file_datetime < cutoff_date:
                file_path.unlink()
                deleted_count += 1
                logging.info(f"削除: {file_path.name} (作成日時: {file_datetime})")
        except (ValueError, OSError) as e:
            logging.warning(f"ファイル削除エラー {file_path.name}: {e}")
    
    if deleted_count > 0:
        logging.info(f"{RETENTION_HOURS}時間以前のアーカイブファイル {deleted_count}件を削除しました")


def archive_current_data():
    """現在のデータをアーカイブに保存"""
    if OUTPUT_FILE.exists():
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = ARCHIVE_DIR / f"weather_{timestamp}.json"
        
        try:
            with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            with open(archive_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logging.info(f"アーカイブ保存: {archive_path.name}")
        except Exception as e:
            logging.error(f"アーカイブ保存エラー: {e}")


def main():
    """メイン処理"""
    logging.info("天気予報の取得を開始します")
    
    # 古いアーカイブを削除
    cleanup_old_archives()
    
    # 現在のデータをアーカイブ
    archive_current_data()
    
    output_data = {}
    try:
        jma_resp = requests.get(JMA_API_URL, timeout=10)
        jma_resp.raise_for_status()
        jma_data = jma_resp.json()

        wni_resp = requests.get(WEATHERNEWS_API_URL, timeout=10)
        wni_resp.raise_for_status()
        wni_data = wni_resp.json()

        if not jma_data or not wni_data:
            raise ValueError("APIデータが空です。")

        # --- 1. 気象庁データから3日間予報を生成 ---
        short_forecast = jma_data[0] if len(jma_data) > 0 else {}
        weekly_forecast = jma_data[1] if len(jma_data) > 1 else {}

        publishing_office = short_forecast.get('publishingOffice', '気象庁')
        report_datetime = short_forecast.get('reportDatetime', datetime.now().isoformat())

        time_series = short_forecast.get('timeSeries', [])
        weather_ts = time_series[0] if len(time_series) > 0 else {}
        pops_ts = time_series[1] if len(time_series) > 1 else {}
        temp_ts_short = time_series[2] if len(time_series) > 2 else {}

        def find_area(ts, area_name):
            if not ts:
                return None
            for a in ts.get('areas', []):
                try:
                    if a.get('area', {}).get('name') == area_name:
                        return a
                except Exception:
                    continue
            return None

        tokyo_region_weather = find_area(weather_ts, '東京地方')
        tokyo_region_pops = find_area(pops_ts, '東京地方')
        tokyo_city_temp_short = find_area(temp_ts_short, '東京')

        forecast_dates = [d.split('T')[0] for d in weather_ts.get('timeDefines', [])]
        weathers = tokyo_region_weather.get('weathers', []) if tokyo_region_weather else []
        short_temps = tokyo_city_temp_short.get('temps', []) if tokyo_city_temp_short else []

        pops_by_datetime = {}
        pops_list = tokyo_region_pops.get('pops', []) if tokyo_region_pops else []
        pops_time_def = pops_ts.get('timeDefines', []) if isinstance(pops_ts, dict) else []
        for i, pop_val in enumerate(pops_list):
            if i < len(pops_time_def):
                dt_str = pops_time_def[i]
                pops_by_datetime[dt_str] = pop_val

        daily_forecasts = []
        for i in range(len(forecast_dates)):
            date = forecast_dates[i]
            temp_min, temp_max = "--", "--"

            chance_of_rain = [
                pops_by_datetime.get(f"{date}T00:00:00+09:00", '--'),
                pops_by_datetime.get(f"{date}T06:00:00+09:00", '--'),
                pops_by_datetime.get(f"{date}T12:00:00+09:00", '--'),
                pops_by_datetime.get(f"{date}T18:00:00+09:00", '--')
            ]

            weather_text = weathers[i] if i < len(weathers) else '--'

            if i == 0:  # 今日
                temp_max = short_temps[0] if len(short_temps) > 0 else '--'
                temp_min = short_temps[1] if len(short_temps) > 1 else '--'
            elif i == 1:  # 明日
                temp_min = short_temps[2] if len(short_temps) > 2 else '--'
                temp_max = short_temps[3] if len(short_temps) > 3 else '--'
            elif i == 2:  # 明後日
                weekly_ts_list = weekly_forecast.get('timeSeries', [])
                weekly_temp_ts = weekly_ts_list[1] if len(weekly_ts_list) > 1 else {}
                tokyo_city_temp_weekly = None
                if weekly_temp_ts:
                    for a in weekly_temp_ts.get('areas', []):
                        if a.get('area', {}).get('name') == '東京':
                            tokyo_city_temp_weekly = a
                            break
                if tokyo_city_temp_weekly:
                    weekly_dates = [d.split('T')[0] for d in weekly_temp_ts.get('timeDefines', [])]
                    try:
                        idx = weekly_dates.index(date)
                        temps_min = tokyo_city_temp_weekly.get('tempsMin', [])
                        temps_max = tokyo_city_temp_weekly.get('tempsMax', [])
                        if idx < len(temps_min):
                            temp_min = temps_min[idx]
                        if idx < len(temps_max):
                            temp_max = temps_max[idx]
                    except (ValueError, IndexError):
                        pass

            daily_forecasts.append({
                "date": date,
                "weather": weather_text,
                "temp_min": temp_min,
                "temp_max": temp_max,
                "chance_of_rain": chance_of_rain
            })

        # --- 2. ウェザーニュースデータから1時間ごと予報を生成 ---
        hourly_forecasts = []
        for hour_data in wni_data['srf'][:HOURLY_FORECAST_HOURS]:
            dt = datetime.fromtimestamp(int(hour_data['tm']))
            hourly_forecasts.append({
                "iso_time": dt.isoformat(),
                "time": dt.strftime('%H:%M'),
                "weather": get_wni_weather_text(hour_data['WX']),
                "temp": str(round(float(hour_data['AIRTMP']))),
                "precip": hour_data.get('PREC', '0')
            })

        output_data = {
            "publishingOffice": publishing_office,
            "reportDatetime": report_datetime,
            "forecasts": daily_forecasts,
            "hourly_forecast": hourly_forecasts
        }

        logging.info(f"天気予報データを正常に取得しました (3日間予報: {len(daily_forecasts)}件, 時間予報: {len(hourly_forecasts)}件)")

    except Exception as e:
        error_message = f"エラーが発生しました: {e}"
        logging.error(error_message)
        output_data = {"error": error_message}
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    if "error" not in output_data:
        logging.info(f"'{OUTPUT_FILE}' の生成が完了しました。")
    else:
        logging.error(f"'{OUTPUT_FILE}' にエラー情報を書き込みました。")
        exit(1)


if __name__ == '__main__':
    main()
