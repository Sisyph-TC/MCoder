import sqlite3

DB_NAME = 'smuzichat.db'
TABLE_NAME = 'chat_lines'

conn = sqlite3.connect(DB_NAME)
c = conn.cursor()

c.execute(f'''
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    line_number INTEGER NOT NULL,
    content TEXT NOT NULL
)
''')

conn.commit()
conn.close()

print(f'База данных {DB_NAME} и таблица {TABLE_NAME} успешно созданы.') 