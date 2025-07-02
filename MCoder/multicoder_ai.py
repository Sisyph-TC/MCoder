import requests
import json
import time
import threading
from typing import Dict, List, Optional
from urllib.parse import quote
import logging

class AIIntegration:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Конфигурация нейросетей
        self.ai_services = {
            'deepseek': {
                'url': 'https://coder.deepseek.com',
                'available': True,
                'fallback': 'codegeex'
            },
            'codegeex': {
                'url': 'https://codegeex.cn/ide',
                'available': True,
                'fallback': 'starcoder'
            },
            'starcoder': {
                'url': 'https://huggingface.co/chat',
                'available': True,
                'fallback': None
            }
        }
        
    def search_internet(self, query: str) -> List[Dict]:
        """Поиск информации в интернете"""
        results = []
        
        try:
            # Поиск через DuckDuckGo (не требует API ключа)
            search_url = f"https://duckduckgo.com/html/?q={quote(query)}"
            response = self.session.get(search_url, timeout=10)
            
            if response.status_code == 200:
                # Простой парсинг результатов (в реальной версии нужен BeautifulSoup)
                content = response.text.lower()
                
                # Поиск GitHub репозиториев
                if 'github.com' in content:
                    results.append({
                        'type': 'github_repo',
                        'title': f'GitHub репозиторий по запросу: {query}',
                        'url': f'https://github.com/search?q={quote(query)}',
                        'description': 'Найден репозиторий на GitHub'
                    })
                
                # Поиск документации
                if 'docs' in content or 'documentation' in content:
                    results.append({
                        'type': 'documentation',
                        'title': f'Документация: {query}',
                        'url': f'https://www.google.com/search?q={quote(query + " documentation")}',
                        'description': 'Найдена документация'
                    })
                
                # Общие результаты поиска
                results.append({
                    'type': 'general',
                    'title': f'Поиск: {query}',
                    'url': f'https://www.google.com/search?q={quote(query)}',
                    'description': 'Общие результаты поиска'
                })
                
        except Exception as e:
            self.logger.error(f"Ошибка поиска в интернете: {e}")
            results.append({
                'type': 'error',
                'title': 'Ошибка поиска',
                'url': '',
                'description': f'Не удалось выполнить поиск: {str(e)}'
            })
            
        return results
        
    def generate_code_deepseek(self, prompt: str) -> Optional[str]:
        """Генерация кода через DeepSeek"""
        try:
            # Здесь будет интеграция с DeepSeek API или web-интерфейсом
            # Пока возвращаем заглушку
            return f"# Код сгенерирован DeepSeek\n# Запрос: {prompt}\n\ndef main():\n    print('Hello from DeepSeek')\n\nif __name__ == '__main__':\n    main()"
        except Exception as e:
            self.logger.error(f"Ошибка DeepSeek: {e}")
            return None
            
    def generate_code_codegeex(self, prompt: str) -> Optional[str]:
        """Генерация кода через CodeGeeX"""
        try:
            # Здесь будет интеграция с CodeGeeX API или web-интерфейсом
            return f"// Код сгенерирован CodeGeeX\n// Запрос: {prompt}\n\n#include <iostream>\n\nint main() {{\n    std::cout << \"Hello from CodeGeeX\" << std::endl;\n    return 0;\n}}"
        except Exception as e:
            self.logger.error(f"Ошибка CodeGeeX: {e}")
            return None
            
    def generate_code_starcoder(self, prompt: str) -> Optional[str]:
        """Генерация кода через StarCoder"""
        try:
            # Здесь будет интеграция с StarCoder API или web-интерфейсом
            return f"# Код сгенерирован StarCoder\n# Запрос: {prompt}\n\nimport sys\n\ndef main():\n    print('Hello from StarCoder')\n    return 0\n\nif __name__ == '__main__':\n    sys.exit(main())"
        except Exception as e:
            self.logger.error(f"Ошибка StarCoder: {e}")
            return None
            
    def generate_code_multi(self, prompt: str, preferred_service: str = None) -> Dict:
        """Генерация кода через несколько нейросетей с fallback"""
        results = {}
        errors = []
        
        # Определяем порядок попыток
        if preferred_service and preferred_service in self.ai_services:
            services_order = [preferred_service]
            fallback = self.ai_services[preferred_service]['fallback']
            if fallback:
                services_order.append(fallback)
        else:
            services_order = ['deepseek', 'codegeex', 'starcoder']
            
        # Пробуем каждую нейросеть
        for service in services_order:
            if not self.ai_services[service]['available']:
                continue
                
            try:
                if service == 'deepseek':
                    code = self.generate_code_deepseek(prompt)
                elif service == 'codegeex':
                    code = self.generate_code_codegeex(prompt)
                elif service == 'starcoder':
                    code = self.generate_code_starcoder(prompt)
                else:
                    continue
                    
                if code:
                    results[service] = {
                        'code': code,
                        'status': 'success',
                        'timestamp': time.time()
                    }
                    break  # Останавливаемся на первом успешном результате
                else:
                    errors.append(f"{service}: не удалось сгенерировать код")
                    
            except Exception as e:
                errors.append(f"{service}: {str(e)}")
                self.ai_services[service]['available'] = False  # Временно отключаем
                
        return {
            'results': results,
            'errors': errors,
            'success': len(results) > 0
        }
        
    def analyze_security(self, code: str) -> Dict:
        """Анализ безопасности сгенерированного кода"""
        security_issues = []
        risk_level = "LOW"
        
        # Проверка на опасные паттерны в коде
        dangerous_patterns = [
            'os.system', 'subprocess.call', 'eval(', 'exec(',
            'open(', 'file(', '__import__', 'globals()',
            'locals()', 'vars()', 'dir()', 'type('
        ]
        
        code_lower = code.lower()
        for pattern in dangerous_patterns:
            if pattern in code_lower:
                security_issues.append(f"Обнаружен опасный паттерн: {pattern}")
                risk_level = "HIGH"
                
        # Проверка на сетевые операции
        if 'requests.get' in code_lower or 'urllib' in code_lower:
            security_issues.append("Обнаружены сетевые операции")
            risk_level = "MEDIUM"
            
        return {
            'safe': risk_level == "LOW",
            'risk_level': risk_level,
            'issues': security_issues,
            'recommendation': 'APPROVE' if risk_level == 'LOW' else 'REVIEW'
        }
        
    def build_exe_cloud(self, code: str, language: str = "python") -> Dict:
        """Облачная сборка exe-файла"""
        try:
            # Здесь будет интеграция с облачными сборщиками (Replit, GitHub Actions)
            # Пока возвращаем заглушку
            
            if language == "python":
                build_script = f"""
# Автоматически сгенерированный скрипт сборки
import os
import subprocess

# Сохраняем код
with open('main.py', 'w', encoding='utf-8') as f:
    f.write('''{code}''')

# Устанавливаем pyinstaller
subprocess.run(['pip', 'install', 'pyinstaller'])

# Собираем exe
subprocess.run(['pyinstaller', '--onefile', 'main.py'])

print("Сборка завершена!")
"""
            else:
                build_script = f"# Сборка для {language}\n{code}"
                
            return {
                'success': True,
                'build_script': build_script,
                'download_url': 'https://example.com/download.exe',  # Заглушка
                'message': 'Exe-файл готов к скачиванию'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Ошибка сборки exe-файла'
            }

# Глобальный экземпляр AI интеграции
ai_integration = AIIntegration() 