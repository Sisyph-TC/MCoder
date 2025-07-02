import sqlite3
import hashlib
import json
import os
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

class MultiCoderCore:
    def __init__(self, db_path: str = "multicoder.db"):
        self.db_path = db_path
        self.setup_database()
        self.setup_logging()
        self.security_level = "HIGH"
        self.memory_cache = {}
        self.active_projects = {}
        
    def setup_database(self):
        """Инициализация базы данных с бесконечной памятью"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Таблица проектов
        c.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active',
                security_level TEXT DEFAULT 'HIGH'
            )
        ''')
        
        # Таблица сообщений (бесконечная память)
        c.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                sender TEXT NOT NULL,
                content TEXT NOT NULL,
                message_type TEXT DEFAULT 'text',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                importance INTEGER DEFAULT 1,
                FOREIGN KEY (project_id) REFERENCES projects (id)
            )
        ''')
        
        # Таблица файлов
        c.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER,
                file_hash TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                security_scan TEXT DEFAULT 'pending',
                FOREIGN KEY (project_id) REFERENCES projects (id)
            )
        ''')
        
        # Таблица безопасности
        c.execute('''
            CREATE TABLE IF NOT EXISTS security_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                risk_level TEXT,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица кэша и векторов
        c.execute('''
            CREATE TABLE IF NOT EXISTS memory_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_hash TEXT UNIQUE NOT NULL,
                content TEXT NOT NULL,
                content_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица модулей проекта
        c.execute('''
            CREATE TABLE IF NOT EXISTS modules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                module_name TEXT NOT NULL,
                status TEXT DEFAULT 'not_started',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                log TEXT,
                FOREIGN KEY (project_id) REFERENCES projects (id)
            )
        ''')
        
        # Таблица статусов системных модулей мультикодера
        c.execute('''
            CREATE TABLE IF NOT EXISTS system_modules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module_name TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT 'unknown',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                log TEXT
            )
        ''')
        
        # Таблица истории изменений статусов
        c.execute('''
            CREATE TABLE IF NOT EXISTS system_status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module_name TEXT NOT NULL,
                status TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                log TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def setup_logging(self):
        """Настройка системы логирования"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('multicoder.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def security_check(self, content: str, content_type: str = "text") -> Dict:
        """Проверка безопасности контента"""
        risk_factors = []
        risk_level = "LOW"
        
        # Проверка на вредоносные паттерны
        dangerous_patterns = [
            "hack", "exploit", "virus", "malware", "backdoor", "keylogger",
            "password cracker", "ddos", "sql injection", "xss"
        ]
        
        content_lower = content.lower()
        for pattern in dangerous_patterns:
            if pattern in content_lower:
                risk_factors.append(f"Обнаружен опасный паттерн: {pattern}")
                risk_level = "HIGH"
                
        # Проверка размера (для файлов)
        if content_type == "file" and len(content) > 50 * 1024 * 1024:  # 50MB
            risk_factors.append("Файл превышает лимит 50MB")
            risk_level = "MEDIUM"
            
        # Логирование проверки
        self.log_security_action("security_check", risk_level, 
                               f"Content type: {content_type}, Risk factors: {risk_factors}")
        
        return {
            "safe": risk_level == "LOW",
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "recommendation": "APPROVE" if risk_level == "LOW" else "REVIEW"
        }
        
    def log_security_action(self, action: str, risk_level: str, details: str):
        """Логирование действий безопасности"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            INSERT INTO security_log (action, risk_level, details)
            VALUES (?, ?, ?)
        ''', (action, risk_level, details))
        conn.commit()
        conn.close()
        
    def create_project(self, name: str, description: str = "") -> int:
        """Создание нового проекта с проверкой безопасности"""
        try:
            security_check = self.security_check(f"{name} {description}")
            if not security_check["safe"]:
                self.logger.error(f"ОТКАЗАНО в создании проекта: {name}. Причина: {security_check['risk_factors']}")
                raise ValueError(f"Проект не прошёл проверку безопасности: {security_check['risk_factors']}")
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''
                INSERT INTO projects (name, description, security_level)
                VALUES (?, ?, ?)
            ''', (name, description, security_check["risk_level"]))
            project_id = c.lastrowid
            conn.commit()
            conn.close()
            if project_id is None:
                self.logger.error(f"Ошибка: не удалось получить ID нового проекта '{name}'")
                raise ValueError(f"Не удалось получить ID нового проекта '{name}'")
            self.logger.info(f"Создан проект: {name} (ID: {project_id})")
            return int(project_id)
        except Exception as e:
            self.logger.error(f"Ошибка при создании проекта '{name}': {str(e)}")
            raise
        
    def add_message(self, project_id: int, sender: str, content: str, 
                   message_type: str = "text", importance: int = 1):
        """Добавление сообщения в бесконечную память"""
        try:
            security_check = self.security_check(content, message_type)
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''
                INSERT INTO messages (project_id, sender, content, message_type, importance)
                VALUES (?, ?, ?, ?, ?)
            ''', (project_id, sender, content, message_type, importance))
            conn.commit()
            conn.close()
            cache_key = f"msg_{project_id}_{time.time()}"
            self.memory_cache[cache_key] = {
                "content": content,
                "sender": sender,
                "type": message_type,
                "timestamp": datetime.now()
            }
            self.logger.info(f"Добавлено сообщение в проект {project_id}: {sender}")
        except Exception as e:
            self.logger.error(f"Ошибка при добавлении сообщения в проект {project_id}: {str(e)}")
            raise
        
    def get_project_history(self, project_id: int, limit: int = 100) -> List[Dict]:
        """Получение истории проекта из бесконечной памяти"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''
                SELECT sender, content, message_type, created_at, importance
                FROM messages 
                WHERE project_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (project_id, limit))
            messages = []
            for row in c.fetchall():
                messages.append({
                    "sender": row[0],
                    "content": row[1],
                    "type": row[2],
                    "timestamp": row[3],
                    "importance": row[4]
                })
            conn.close()
            self.logger.info(f"Получена история проекта {project_id}, сообщений: {len(messages)}")
            return messages
        except Exception as e:
            self.logger.error(f"Ошибка при получении истории проекта {project_id}: {str(e)}")
            raise
        
    def search_memory(self, query: str, project_id: Optional[int] = None) -> List[Dict]:
        """Поиск в бесконечной памяти"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            if project_id:
                c.execute('''
                    SELECT sender, content, message_type, created_at, importance
                    FROM messages 
                    WHERE project_id = ? AND content LIKE ?
                    ORDER BY importance DESC, created_at DESC
                ''', (project_id, f"%{query}%"))
            else:
                c.execute('''
                    SELECT sender, content, message_type, created_at, importance
                    FROM messages 
                    WHERE content LIKE ?
                    ORDER BY importance DESC, created_at DESC
                ''', (f"%{query}%",))
            results = []
            for row in c.fetchall():
                results.append({
                    "sender": row[0],
                    "content": row[1],
                    "type": row[2],
                    "timestamp": row[3],
                    "importance": row[4]
                })
            conn.close()
            self.logger.info(f"Поиск в памяти: '{query}', найдено: {len(results)} записей")
            return results
        except Exception as e:
            self.logger.error(f"Ошибка при поиске в памяти: '{query}': {str(e)}")
            raise
        
    def add_file(self, project_id: int, file_path: str) -> bool:
        """Добавление файла с проверкой безопасности"""
        try:
            if not os.path.exists(file_path):
                self.logger.error(f"Файл не найден: {file_path}")
                return False
            file_size = os.path.getsize(file_path)
            if file_size > 50 * 1024 * 1024:  # 50MB
                self.logger.error(f"Файл превышает лимит 50MB: {file_path}")
                raise ValueError("Файл превышает лимит 50MB")
            with open(file_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            security_check = self.security_check(f"file:{file_path}", "file")
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''
                INSERT INTO files (project_id, filename, file_path, file_size, file_hash, security_scan)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (project_id, os.path.basename(file_path), file_path, file_size, file_hash, security_check["risk_level"]))
            conn.commit()
            conn.close()
            self.logger.info(f"Добавлен файл: {file_path} в проект {project_id}")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при добавлении файла в проект {project_id}: {str(e)}")
            raise
        
    def get_project_status(self, project_id: int) -> Dict:
        """Получение статуса проекта"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('SELECT name, description, status, created_at FROM projects WHERE id = ?', (project_id,))
            project_info = c.fetchone()
            c.execute('SELECT COUNT(*) FROM messages WHERE project_id = ?', (project_id,))
            message_count = c.fetchone()[0]
            c.execute('SELECT COUNT(*) FROM files WHERE project_id = ?', (project_id,))
            file_count = c.fetchone()[0]
            conn.close()
            if project_info:
                self.logger.info(f"Статус проекта {project_id} получен")
                return {
                    "id": project_id,
                    "name": project_info[0],
                    "description": project_info[1],
                    "status": project_info[2],
                    "created_at": project_info[3],
                    "message_count": message_count,
                    "file_count": file_count
                }
            self.logger.warning(f"Проект {project_id} не найден при запросе статуса")
            raise ValueError(f"Проект {project_id} не найден")
        except Exception as e:
            self.logger.error(f"Ошибка при получении статуса проекта {project_id}: {str(e)}")
            raise

    def export_project_report(self, project_id: int, filename_base: str = None) -> str:
        """Экспортирует отчёт по проекту в TXT и (если возможно) PDF. Возвращает путь к TXT-отчёту."""
        try:
            status = self.get_project_status(project_id)
            messages = self.get_project_history(project_id, limit=1000)
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('SELECT filename, file_path, file_size, uploaded_at FROM files WHERE project_id = ?', (project_id,))
            files = c.fetchall()
            c.execute('SELECT action, risk_level, details, timestamp FROM security_log ORDER BY timestamp DESC LIMIT 1000')
            security_events = c.fetchall()
            conn.close()
            if not filename_base:
                filename_base = f"project_report_{project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            txt_path = f"{filename_base}.txt"
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(f"=== ОТЧЁТ ПО ПРОЕКТУ #{project_id} ===\n")
                f.write(f"Имя: {status['name']}\nОписание: {status['description']}\nСтатус: {status['status']}\nСоздан: {status['created_at']}\n")
                f.write(f"\n--- СООБЩЕНИЯ ({len(messages)}) ---\n")
                for m in messages:
                    f.write(f"[{m['timestamp']}] {m['sender']} ({m['type']}): {m['content']}\n")
                f.write(f"\n--- ФАЙЛЫ ({len(files)}) ---\n")
                for file in files:
                    f.write(f"{file[0]} | {file[1]} | {file[2]} байт | {file[3]}\n")
                f.write(f"\n--- СОБЫТИЯ БЕЗОПАСНОСТИ ({len(security_events)}) ---\n")
                for ev in security_events:
                    f.write(f"[{ev[3]}] {ev[0]} | {ev[1]} | {ev[2]}\n")
            self.logger.info(f"Экспортирован TXT-отчёт по проекту {project_id}: {txt_path}")
            # PDF
            if REPORTLAB_AVAILABLE:
                pdf_path = f"{filename_base}.pdf"
                c = canvas.Canvas(pdf_path, pagesize=A4)
                width, height = A4
                y = height - 40
                c.setFont("Helvetica-Bold", 14)
                c.drawString(40, y, f"ОТЧЁТ ПО ПРОЕКТУ #{project_id}")
                y -= 30
                c.setFont("Helvetica", 10)
                c.drawString(40, y, f"Имя: {status['name']}")
                y -= 15
                c.drawString(40, y, f"Описание: {status['description']}")
                y -= 15
                c.drawString(40, y, f"Статус: {status['status']}")
                y -= 15
                c.drawString(40, y, f"Создан: {status['created_at']}")
                y -= 25
                c.setFont("Helvetica-Bold", 12)
                c.drawString(40, y, f"СООБЩЕНИЯ ({len(messages)})")
                y -= 18
                c.setFont("Helvetica", 8)
                for m in messages:
                    line = f"[{m['timestamp']}] {m['sender']} ({m['type']}): {m['content']}"
                    for l in self._split_line(line, 110):
                        if y < 40:
                            c.showPage(); y = height - 40; c.setFont("Helvetica", 8)
                        c.drawString(40, y, l)
                        y -= 10
                y -= 10
                c.setFont("Helvetica-Bold", 12)
                c.drawString(40, y, f"ФАЙЛЫ ({len(files)})")
                y -= 18
                c.setFont("Helvetica", 8)
                for file in files:
                    line = f"{file[0]} | {file[1]} | {file[2]} байт | {file[3]}"
                    for l in self._split_line(line, 110):
                        if y < 40:
                            c.showPage(); y = height - 40; c.setFont("Helvetica", 8)
                        c.drawString(40, y, l)
                        y -= 10
                y -= 10
                c.setFont("Helvetica-Bold", 12)
                c.drawString(40, y, f"СОБЫТИЯ БЕЗОПАСНОСТИ ({len(security_events)})")
                y -= 18
                c.setFont("Helvetica", 8)
                for ev in security_events:
                    line = f"[{ev[3]}] {ev[0]} | {ev[1]} | {ev[2]}"
                    for l in self._split_line(line, 110):
                        if y < 40:
                            c.showPage(); y = height - 40; c.setFont("Helvetica", 8)
                        c.drawString(40, y, l)
                        y -= 10
                c.save()
                self.logger.info(f"Экспортирован PDF-отчёт по проекту {project_id}: {pdf_path}")
            return txt_path
        except Exception as e:
            self.logger.error(f"Ошибка при экспорте отчёта по проекту {project_id}: {str(e)}")
            raise

    def _split_line(self, line, maxlen):
        """Вспомогательная функция для переноса длинных строк в PDF."""
        return [line[i:i+maxlen] for i in range(0, len(line), maxlen)]

    def add_or_update_module(self, project_id: int, module_name: str, status: str, log: str = None):
        """Добавляет или обновляет модуль проекта и его статус."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''
                SELECT id FROM modules WHERE project_id = ? AND module_name = ?
            ''', (project_id, module_name))
            row = c.fetchone()
            if row:
                c.execute('''
                    UPDATE modules SET status = ?, updated_at = CURRENT_TIMESTAMP, log = ? WHERE id = ?
                ''', (status, log, row[0]))
                self.logger.info(f"Обновлён модуль '{module_name}' проекта {project_id}: статус = {status}")
            else:
                c.execute('''
                    INSERT INTO modules (project_id, module_name, status, log)
                    VALUES (?, ?, ?, ?)
                ''', (project_id, module_name, status, log))
                self.logger.info(f"Добавлен модуль '{module_name}' в проект {project_id}: статус = {status}")
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Ошибка при добавлении/обновлении модуля '{module_name}' проекта {project_id}: {str(e)}")
            raise

    def get_modules(self, project_id: int):
        """Возвращает список модулей и их статусов для проекта."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''
                SELECT module_name, status, updated_at, log FROM modules WHERE project_id = ?
            ''', (project_id,))
            modules = [
                {"module_name": row[0], "status": row[1], "updated_at": row[2], "log": row[3]}
                for row in c.fetchall()
            ]
            conn.close()
            return modules
        except Exception as e:
            self.logger.error(f"Ошибка при получении модулей проекта {project_id}: {str(e)}")
            raise

    def get_build_progress(self, project_id: int) -> float:
        """Возвращает процент сборки модулей проекта (0-100)."""
        try:
            modules = self.get_modules(project_id)
            if not modules:
                return 0.0
            total = len(modules)
            done = sum(1 for m in modules if m["status"] == "done")
            percent = (done / total) * 100
            self.logger.info(f"Процент сборки проекта {project_id}: {percent:.1f}% ({done}/{total})")
            return percent
        except Exception as e:
            self.logger.error(f"Ошибка при расчёте процента сборки проекта {project_id}: {str(e)}")
            raise

    def update_system_module_status(self, module_name: str, status: str, log: str = None):
        """Обновляет статус системного модуля мультикодера и сохраняет в историю."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            # Обновление/добавление статуса
            c.execute('SELECT id FROM system_modules WHERE module_name = ?', (module_name,))
            row = c.fetchone()
            if row:
                c.execute('''
                    UPDATE system_modules SET status = ?, updated_at = CURRENT_TIMESTAMP, log = ? WHERE id = ?
                ''', (status, log, row[0]))
                self.logger.info(f"Обновлён статус системного модуля '{module_name}': {status}")
            else:
                c.execute('''
                    INSERT INTO system_modules (module_name, status, log)
                    VALUES (?, ?, ?)
                ''', (module_name, status, log))
                self.logger.info(f"Добавлен системный модуль '{module_name}' со статусом: {status}")
            # Запись в историю
            c.execute('''
                INSERT INTO system_status_history (module_name, status, log)
                VALUES (?, ?, ?)
            ''', (module_name, status, log))
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Ошибка при обновлении статуса системного модуля '{module_name}': {str(e)}")
            raise

    def get_system_status(self):
        """Возвращает текущий статус всех системных модулей мультикодера."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('SELECT module_name, status, updated_at, log FROM system_modules')
            modules = [
                {"module_name": row[0], "status": row[1], "updated_at": row[2], "log": row[3]}
                for row in c.fetchall()
            ]
            conn.close()
            return modules
        except Exception as e:
            self.logger.error(f"Ошибка при получении статусов системных модулей: {str(e)}")
            raise

    def get_system_status_history(self, module_name: str = None, limit: int = 100):
        """Возвращает историю изменений статусов системных модулей (по модулю или все)."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            if module_name:
                c.execute('''
                    SELECT status, updated_at, log FROM system_status_history WHERE module_name = ? ORDER BY updated_at DESC LIMIT ?
                ''', (module_name, limit))
            else:
                c.execute('''
                    SELECT module_name, status, updated_at, log FROM system_status_history ORDER BY updated_at DESC LIMIT ?
                ''', (limit,))
            history = c.fetchall()
            conn.close()
            return history
        except Exception as e:
            self.logger.error(f"Ошибка при получении истории статусов системных модулей: {str(e)}")
            raise

# Глобальный экземпляр ядра
multicoder_core = MultiCoderCore() 