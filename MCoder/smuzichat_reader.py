import argparse
import os


def read_file_lines(filepath):
    """Читает файл построчно с номерами строк."""
    with open(filepath, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            yield i, line.rstrip('\n')

def search_in_file(filepath, keyword):
    """Ищет строки, содержащие ключевое слово."""
    results = []
    for i, line in read_file_lines(filepath):
        if keyword.lower() in line.lower():
            results.append((i, line))
    return results

def export_fragments(fragments, out_path):
    """Экспортирует найденные фрагменты в файл."""
    with open(out_path, 'w', encoding='utf-8') as f:
        for i, line in fragments:
            f.write(f"{i}: {line}\n")
    print(f"Экспортировано {len(fragments)} строк в {out_path}")

def tag_lines(filepath, keyword, tag):
    """Помечает строки с ключевым словом тегом (выводит на экран)."""
    for i, line in read_file_lines(filepath):
        if keyword.lower() in line.lower():
            print(f"{i}: [{tag}] {line}")

def main():
    parser = argparse.ArgumentParser(description='Читатель и анализатор архива обсуждений.')
    parser.add_argument('filepath', help='Путь к архивному файлу')
    parser.add_argument('--search', help='Ключевое слово для поиска')
    parser.add_argument('--export', help='Путь для экспорта найденных фрагментов')
    parser.add_argument('--tag', help='Тег для пометки найденных строк')
    args = parser.parse_args()

    if not os.path.exists(args.filepath):
        print('Файл не найден!')
        return

    if args.search:
        results = search_in_file(args.filepath, args.search)
        for i, line in results:
            print(f"{i}: {line}")
        print(f"Найдено {len(results)} строк.")
        if args.export:
            export_fragments(results, args.export)
        if args.tag:
            tag_lines(args.filepath, args.search, args.tag)
    else:
        # Просто выводим первые 20 строк для примера
        for i, line in read_file_lines(args.filepath):
            print(f"{i}: {line}")
            if i >= 20:
                break

if __name__ == '__main__':
    main() 