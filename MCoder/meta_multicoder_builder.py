import os
import argparse
from smuzichat_reader import search_in_file
import logging

TEMPLATES = {
    "core": "# multicoder_core.py\n# Здесь будет ядро мультикодера\n\n",
    "gui": "# multicoder_gui.py\n# Здесь будет GUI мультикодера\n\n",
    "logger": "# multicoder_logger.py\n# Централизованное логирование\n\n",
    "ai": "# multicoder_ai.py\n# Интеграция с нейросетями\n\n"
}

KEYWORDS = [
    "ядро", "core", "GUI", "интерфейс", "логирование", "логгер", "TaskManager",
    "CoreCoordinator", "ParanoidTester", "API-ключ", "интеграция", "pipeline", "архитектура"
]

def setup_logging(log_path):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_path, mode='a', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def extract_fragments(archive_path, keywords):
    fragments = {k: [] for k in keywords}
    for k in keywords:
        results = search_in_file(archive_path, k)
        fragments[k].extend(results)
        logging.info(f"Извлечено {len(results)} фрагментов по ключу '{k}'")
    return fragments

def create_project_structure(output_dir):
    os.makedirs(output_dir, exist_ok=True)
    for fname, content in TEMPLATES.items():
        with open(os.path.join(output_dir, f"{fname}.py"), "w", encoding="utf-8") as f:
            f.write(content)
        logging.info(f"Создан файл: {fname}.py")

def insert_fragments(output_dir, fragments):
    for k, lines in fragments.items():
        for fname in TEMPLATES:
            if k.lower() in fname:
                path = os.path.join(output_dir, f"{fname}.py")
                with open(path, "a", encoding="utf-8") as f:
                    f.write(f"# --- Фрагменты по теме: {k} ---\n")
                    for i, line in lines:
                        f.write(f"# {i}: {line}\n")
                logging.info(f"Вставлено {len(lines)} фрагментов в {fname}.py по теме '{k}'")

def main():
    parser = argparse.ArgumentParser(description="Мета-скрипт для автоматической сборки мультикодера из архива идей.")
    parser.add_argument("archive", help="Путь к архиву обсуждений")
    parser.add_argument("output", help="Папка для нового мультикодера")
    parser.add_argument("--log", default="meta_multicoder_builder.log", help="Путь к лог-файлу")
    args = parser.parse_args()

    setup_logging(args.log)
    logging.info("=== Запуск автоматической сборки мультикодера ===")
    create_project_structure(args.output)
    fragments = extract_fragments(args.archive, KEYWORDS)
    insert_fragments(args.output, fragments)
    logging.info(f"Готово! Заготовки мультикодера созданы в папке {args.output}")

if __name__ == "__main__":
    main() 