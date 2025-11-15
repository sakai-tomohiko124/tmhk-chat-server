#!/usr/bin/env python3
# coding: utf-8
"""
鉄道運行情報スクレイピングスクリプト
Yahoo!路線情報から関東地方の運行情報を取得し、3日後に自動削除される
"""

import requests
import json
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from pathlib import Path
import logging

# 設定
URL = 'https://transit.yahoo.co.jp/diainfo/area/4'
OUTPUT_FILE = Path(__file__).resolve().parent / 'train_info.json'
ARCHIVE_DIR = Path(__file__).resolve().parent / 'archive' / 'train'
RETENTION_HOURS = 6  # 6時間後に自動削除

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def cleanup_old_archives():
    """6時間以上前のアーカイブファイルを削除"""
    if not ARCHIVE_DIR.exists():
        return
    
    cutoff_date = datetime.now() - timedelta(hours=RETENTION_HOURS)
    deleted_count = 0
    
    for file_path in ARCHIVE_DIR.glob("train_*.json"):
        try:
            # ファイル名から日時を抽出 (train_YYYYMMDD_HHMMSS.json)
            timestamp_str = file_path.stem.replace("train_", "")
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
        archive_path = ARCHIVE_DIR / f"train_{timestamp}.json"
        
        try:
            with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            with open(archive_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logging.info(f"アーカイブ保存: {archive_path.name}")
        except Exception as e:
            logging.error(f"アーカイブ保存エラー: {e}")


def main():
    """
    Yahoo!路線情報のHTMLテーブルを直接解析して運行情報を取得する。
    """
    logging.info("鉄道運行情報の取得を開始します")
    
    # 古いアーカイブを削除
    cleanup_old_archives()
    
    # 現在のデータをアーカイブ
    archive_current_data()
    
    lines_data = []
    try:
        response = requests.get(URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')

        # --- トラブル路線のテーブルを探す ---
        trouble_section = soup.find('div', id='mdStatusTroubleLine')
        trouble_lines = set()
        if trouble_section:
            rows = trouble_section.select('table tbody tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) == 3:
                    name = cells[0].get_text(strip=True)
                    status = cells[1].get_text(strip=True)
                    detail = cells[2].get_text(strip=True)
                    lines_data.append({'name': name, 'status': status, 'detail': detail})
                    trouble_lines.add(name)
        
        logging.info(f"{len(trouble_lines)}件のトラブル情報をHTMLテーブルから取得しました。")

        # --- 全路線のテーブルを探し、トラブルがなかった路線を追加 ---
        main_content = soup.find('div', id='main')
        if main_content:
            line_tables = main_content.select('.elmTblLstLine')
            for table in line_tables:
                rows = table.select('table tbody tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) == 3:
                        name = cells[0].get_text(strip=True)
                        if name not in trouble_lines:
                            status = cells[1].get_text(strip=True)
                            detail = cells[2].get_text(strip=True)
                            lines_data.append({'name': name, 'status': status, 'detail': detail})
        
        logging.info(f"鉄道運行情報を正常に取得しました (全 {len(lines_data)} 路線)")
        
    except requests.exceptions.RequestException as e:
        logging.error(f"HTTPリクエストエラーが発生しました: {e}")
    except Exception as e:
        logging.error(f"予期せぬエラーが発生しました: {e}")

    # 最終的なJSON構造を作成
    output_data = {
        "lastUpdated": datetime.now().isoformat(),
        "lines": lines_data
    }

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    logging.info(f"'{OUTPUT_FILE}' の生成が完了しました。全 {len(lines_data)} 件の路線情報を書き出しました。")


if __name__ == '__main__':
    main()
