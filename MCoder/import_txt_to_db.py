import sqlite3

DB_NAME = 'smuzichat.db'
TABLE_NAME = 'chat_lines'
TXT_FILE = 'smuzichat_5(хронология реальной попытки).txt'

conn = sqlite3.connect(DB_NAME)
c = conn.cursor()

with open(TXT_FILE, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f, 1):
        c.execute(f'INSERT INTO {TABLE_NAME} (line_number, content) VALUES (?, ?)', (i, line.rstrip('\n')))

conn.commit()
conn.close()

print(f'Импорт завершён: все строки из {TXT_FILE} добавлены в базу данных.') 