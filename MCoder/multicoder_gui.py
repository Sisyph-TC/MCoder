import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel, QScrollArea, QSizePolicy, QFrame, QFileDialog, QProgressBar
)
from PyQt5.QtGui import QIcon, QFont, QTextCursor
from PyQt5.QtCore import Qt, QMimeData
import os
from multicoder_core import multicoder_core
from multicoder_ai import ai_integration
import threading

class ChatMessage(QFrame):
    def __init__(self, text, is_user):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{
                background: {'#f4f6fa' if is_user else '#e6e8ec'};
                border-radius: 12px;
                margin: 4px 0;
                padding: 12px 16px;
            }}
            QLabel {{
                font-size: 1.1em;
                color: #222;
            }}
        """)
        layout = QVBoxLayout(self)
        label = QLabel(text)
        label.setWordWrap(True)
        layout.addWidget(label)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

class ChatArea(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignTop)
        self.layout.setSpacing(8)
        self.layout.setContentsMargins(16, 16, 16, 16)

    def add_message(self, text, is_user):
        msg = ChatMessage(text, is_user)
        self.layout.addWidget(msg)
        self.layout.update()

class FileDropArea(QFrame):
    def __init__(self, on_file_selected):
        super().__init__()
        self.on_file_selected = on_file_selected
        self.setAcceptDrops(True)
        self.setStyleSheet("""
            QFrame {
                border: 2px dashed #10a37f;
                border-radius: 12px;
                background: #f4f6fa;
                min-height: 60px;
            }
            QLabel {
                color: #888;
                font-size: 1em;
            }
        """)
        layout = QVBoxLayout(self)
        self.label = QLabel("Перетащите файл сюда или кликните для выбора (до 50 МБ)")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        fname, _ = QFileDialog.getOpenFileName(self, "Выберите файл", "", "Все файлы (*)")
        if fname:
            self.on_file_selected(fname)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            fname = urls[0].toLocalFile()
            self.on_file_selected(fname)

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MultiCoder")
        self.setWindowIcon(QIcon("MultiCoder.ico"))
        self.setMinimumSize(600, 500)
        self.setStyleSheet("background: #fff;")
        self.current_project_id = None
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Chat scroll area
        self.chat_area_widget = ChatArea()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.chat_area_widget)
        scroll.setStyleSheet("border: none;")
        main_layout.addWidget(scroll, 1)

        # File drop area
        self.file_drop = FileDropArea(self.handle_file_selected)
        main_layout.addWidget(self.file_drop, 0)

        # Progress bar (скрыт по умолчанию)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar, 0)

        # Input area
        input_frame = QFrame()
        input_frame.setStyleSheet("background: #f7f7f8; border-top: 1px solid #e6e8ec;")
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(16, 8, 16, 8)
        input_layout.setSpacing(8)

        self.input_box = QTextEdit()
        self.input_box.setPlaceholderText("Введите сообщение...")
        self.input_box.setFixedHeight(40)
        self.input_box.setFont(QFont("Segoe UI", 11))
        self.input_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.input_box.setStyleSheet("background: #fff; border-radius: 8px; padding: 8px;")
        self.input_box.textChanged.connect(self.adjust_input_height)
        self.input_box.installEventFilter(self)
        input_layout.addWidget(self.input_box, 1)

        self.send_btn = QPushButton()
        self.send_btn.setText("→")
        self.send_btn.setFont(QFont("Arial", 16, QFont.Bold))
        self.send_btn.setFixedSize(40, 40)
        self.send_btn.setStyleSheet("background: #10a37f; color: #fff; border-radius: 8px;")
        self.send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_btn)

        main_layout.addWidget(input_frame, 0)

    def adjust_input_height(self):
        doc_height = self.input_box.document().size().height()
        new_height = max(40, min(120, int(doc_height) + 16))
        self.input_box.setFixedHeight(new_height)

    def send_message(self):
        text = self.input_box.toPlainText().strip()
        if not text:
            return
            
        # Создаём проект, если его нет
        if not self.current_project_id:
            try:
                self.current_project_id = multicoder_core.create_project(
                    "Новый проект",
                    f"Создан для задачи: {text[:50]}..."
                )
            except ValueError as e:
                self.chat_area_widget.add_message(f"Ошибка безопасности: {str(e)}", is_user=False)
                self.input_box.clear()
                return
                
        # Добавляем сообщение пользователя
        self.chat_area_widget.add_message(text, is_user=True)
        multicoder_core.add_message(self.current_project_id, "user", text)
        self.input_box.clear()
        
        # Обрабатываем сообщение в отдельном потоке
        threading.Thread(target=self.process_message, args=(text,), daemon=True).start()
        
    def process_message(self, text: str):
        """Обработка сообщения пользователя"""
        try:
            # Проверяем, не является ли это поисковым запросом
            if text.lower().startswith(('найди', 'поиск', 'ищи', 'search')):
                self.handle_search_request(text)
            else:
                self.handle_code_generation_request(text)
        except Exception as e:
            self.chat_area_widget.add_message(f"Ошибка обработки: {str(e)}", is_user=False)
            
    def handle_search_request(self, query: str):
        """Обработка поискового запроса"""
        self.chat_area_widget.add_message("🔍 Ищу информацию в интернете...", is_user=False)
        
        results = ai_integration.search_internet(query)
        
        if results:
            response = "Найдены следующие результаты:\n\n"
            for i, result in enumerate(results[:5], 1):  # Показываем первые 5 результатов
                response += f"{i}. **{result['title']}**\n"
                response += f"   {result['description']}\n"
                response += f"   Ссылка: {result['url']}\n\n"
                
            response += "Хотите использовать какой-то из этих результатов? Напишите номер или 'нет'."
        else:
            response = "К сожалению, ничего не найдено. Попробуйте изменить запрос."
            
        self.chat_area_widget.add_message(response, is_user=False)
        multicoder_core.add_message(self.current_project_id, "assistant", response)
        
    def handle_code_generation_request(self, prompt: str):
        """Обработка запроса на генерацию кода"""
        self.chat_area_widget.add_message("🤖 Анализирую задачу и генерирую код...", is_user=False)
        
        # Генерируем код через несколько нейросетей
        generation_result = ai_integration.generate_code_multi(prompt)
        
        if generation_result['success']:
            # Берём первый успешный результат
            service_name = list(generation_result['results'].keys())[0]
            code = generation_result['results'][service_name]['code']
            
            # Анализируем безопасность
            security_analysis = ai_integration.analyze_security(code)
            
            if security_analysis['safe']:
                response = f"✅ Код сгенерирован через {service_name.upper()}:\n\n```\n{code}\n```\n\nХотите собрать exe-файл? (да/нет)"
            else:
                response = f"⚠️ Код сгенерирован, но обнаружены проблемы безопасности:\n\n"
                for issue in security_analysis['issues']:
                    response += f"• {issue}\n"
                response += f"\n```\n{code}\n```\n\nРекомендация: {security_analysis['recommendation']}"
        else:
            response = f"❌ Ошибка генерации кода:\n"
            for error in generation_result['errors']:
                response += f"• {error}\n"
                
        self.chat_area_widget.add_message(response, is_user=False)
        multicoder_core.add_message(self.current_project_id, "assistant", response)
        
        # Если код безопасен, предлагаем сборку
        if generation_result['success'] and security_analysis['safe']:
            # Здесь можно добавить логику сборки exe
            pass

    def handle_file_selected(self, fname):
        size_mb = os.path.getsize(fname) / (1024 * 1024)
        if size_mb > 50:
            self.chat_area_widget.add_message(f"Ошибка: файл '{os.path.basename(fname)}' превышает 50 МБ.", is_user=False)
            return
            
        # Создаём проект, если его нет
        if not self.current_project_id:
            try:
                self.current_project_id = multicoder_core.create_project(
                    f"Проект с файлом {os.path.basename(fname)}",
                    f"Автоматически создан для файла {fname}"
                )
            except ValueError as e:
                self.chat_area_widget.add_message(f"Ошибка безопасности: {str(e)}", is_user=False)
                return
                
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.chat_area_widget.add_message(f"Файл '{os.path.basename(fname)}' выбран. Загрузка...", is_user=True)
        
        # Добавляем файл в проект
        try:
            if multicoder_core.add_file(self.current_project_id, fname):
                self.progress_bar.setValue(100)
                self.chat_area_widget.add_message(f"Файл '{os.path.basename(fname)}' успешно загружен в проект.", is_user=False)
            else:
                self.chat_area_widget.add_message(f"Ошибка при загрузке файла '{os.path.basename(fname)}'.", is_user=False)
        except Exception as e:
            self.chat_area_widget.add_message(f"Ошибка: {str(e)}", is_user=False)

    def eventFilter(self, obj, event):
        if obj == self.input_box and event.type() == event.KeyPress:
            if event.key() == Qt.Key_Return and not event.modifiers() & Qt.ShiftModifier:
                self.send_message()
                return True
        return super().eventFilter(obj, event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_EnableHighDpiScaling)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps)
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec_()) 