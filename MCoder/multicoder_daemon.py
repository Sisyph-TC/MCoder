import time
import os
import subprocess
import logging

ARCHIVE = "smuzichat_5(хронология реальной попытки).txt"
OUTPUT = "MCoder_AutoBuild"
LOG = "meta_multicoder_builder.log"
CHECK_INTERVAL = 60  # секунд

def run_builder():
    cmd = [
        "python", "meta_multicoder_builder.py",
        ARCHIVE, OUTPUT, "--log", LOG
    ]
    subprocess.run(cmd)

def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.FileHandler("multicoder_daemon.log", encoding="utf-8"), logging.StreamHandler()]
    )
    last_mtime = None
    while True:
        try:
            mtime = os.path.getmtime(ARCHIVE)
            if last_mtime is None or mtime != last_mtime:
                logging.info("Обнаружено изменение архива, запускаю автоматическую сборку мультикодера.")
                run_builder()
                last_mtime = mtime
            time.sleep(CHECK_INTERVAL)
        except Exception as e:
            logging.error(f"Ошибка в демоне: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main() 