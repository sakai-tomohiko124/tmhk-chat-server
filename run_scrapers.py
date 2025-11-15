#!/usr/bin/env python3
# coding: utf-8
"""
scraper2.pyとscrape_train.pyを一括で実行するスクリプト
1日1回、午前0時（JST）に自動的に実行される
古いアーカイブファイルは3日後に自動削除される
"""

import argparse
import subprocess
import sys
import shutil
from pathlib import Path
from datetime import datetime
import logging
import tempfile

WORKDIR = Path(__file__).resolve().parent
SCRIPT_A = WORKDIR / "scraper2.py"
SCRIPT_B = WORKDIR / "scrape_train.py"
LOGDIR = WORKDIR / "logs"
LOGFILE = LOGDIR / "scraper.log"
CRON_MARKER = "# scrape_daily_job"


def ensure_logdir():
    LOGDIR.mkdir(parents=True, exist_ok=True)


def setup_logging():
    ensure_logdir()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(LOGFILE),
            logging.StreamHandler(sys.stdout),
        ],
    )


def run_script(path: Path) -> int:
    if not path.exists():
        logging.error("スクリプトが見つかりません: %s", path)
        return 2
    cmd = [sys.executable, str(path)]
    logging.info("実行: %s", " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    logging.info("終了コード: %s", proc.returncode)
    if proc.stdout:
        logging.info("stdout:\n%s", proc.stdout.strip())
    if proc.stderr:
        logging.error("stderr:\n%s", proc.stderr.strip())
    return proc.returncode


def run_once() -> int:
    logging.info("=" * 60)
    logging.info("開始: scraper2.py と scrape_train.py を順次実行します")
    logging.info("古いアーカイブファイル(6時間以前)は自動的に削除されます")
    logging.info("=" * 60)
    
    rc = run_script(SCRIPT_A)
    if rc != 0:
        logging.warning(" %s が非ゼロ終了コードを返しました: %s", SCRIPT_A.name, rc)
    
    rc2 = run_script(SCRIPT_B)
    if rc2 != 0:
        logging.warning(" %s が非ゼロ終了コードを返しました: %s", SCRIPT_B.name, rc2)
    
    final_rc = 0 if (rc == 0 and rc2 == 0) else 1
    logging.info("=" * 60)
    logging.info("完了 (終了コード=%s)", final_rc)
    logging.info("=" * 60)
    return final_rc


def install_cron():
    if shutil.which("crontab") is None:
        logging.error("crontab コマンドが見つかりません。devcontainerで利用可能か確認してください。")
        return 1
    
    # 毎日午前0時（JST）に実行
    cron_cmd = f'0 0 * * * cd {WORKDIR} && /usr/bin/env python3 {Path(__file__).resolve()} >> {LOGFILE} 2>&1 {CRON_MARKER}'
    
    try:
        existing = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        current = existing.stdout if existing.returncode == 0 else ""
        if CRON_MARKER in current:
            logging.info("既にcronエントリが存在します。")
            return 0
        new_cron = current.rstrip() + ("\n" if current and not current.endswith("\n") else "") + cron_cmd + "\n"
        with tempfile.NamedTemporaryFile("w+", delete=False) as tf:
            tf.write(new_cron)
            tf.flush()
            subprocess.check_call(["crontab", tf.name])
        logging.info("cron をインストールしました。毎日午前0時(JST)に実行されます。")
        logging.info("6時間以上前のアーカイブファイルは自動的に削除されます。")
        return 0
    except subprocess.CalledProcessError as e:
        logging.error("crontab のインストールに失敗しました: %s", e)
        return 2


def uninstall_cron():
    if shutil.which("crontab") is None:
        logging.error("crontab コマンドが見つかりません。")
        return 1
    try:
        existing = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        if existing.returncode != 0:
            logging.info("crontab が空または利用できません。")
            return 0
        lines = existing.stdout.splitlines()
        new_lines = [l for l in lines if CRON_MARKER not in l]
        if len(new_lines) == len(lines):
            logging.info("削除対象のcronエントリは見つかりませんでした。")
            return 0
        with tempfile.NamedTemporaryFile("w+", delete=False) as tf:
            tf.write("\n".join(new_lines) + "\n")
            tf.flush()
            subprocess.check_call(["crontab", tf.name])
        logging.info("cron エントリを削除しました。")
        return 0
    except subprocess.CalledProcessError as e:
        logging.error("crontab の削除に失敗しました: %s", e)
        return 2


def parse_args():
    p = argparse.ArgumentParser(
        description="scraper2.py と scrape_train.py をまとめて実行・cron登録するツール。6時間以上前のアーカイブは自動削除されます。"
    )
    p.add_argument("--install-cron", action="store_true", help="このスクリプトを毎日午前0時に実行するcronエントリを登録する")
    p.add_argument("--uninstall-cron", action="store_true", help="登録したcronエントリを削除する")
    p.add_argument("--run-once", action="store_true", help="1回だけ実行して終了する（デフォルト動作）")
    return p.parse_args()


def main():
    setup_logging()
    args = parse_args()
    if args.install_cron:
        rc = install_cron()
        sys.exit(rc)
    if args.uninstall_cron:
        rc = uninstall_cron()
        sys.exit(rc)
    # デフォルト: 1回実行
    rc = run_once()
    sys.exit(rc)


if __name__ == "__main__":
    main()
