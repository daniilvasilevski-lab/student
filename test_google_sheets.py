#!/usr/bin/env python3
"""
Тестирование подключения к Google Sheets
"""

import os
import sys
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

def test_google_sheets_connection():
    """Тестирование подключения к Google Sheets"""
    
    # Проверка переменных окружения
    creds_path = os.getenv('GOOGLE_SERVICE_ACCOUNT_KEY')
    source_url = os.getenv('SOURCE_SHEET_URL')
    results_url = os.getenv('RESULTS_SHEET_URL')
    
    print("🔍 Проверка настроек Google Sheets...")
    print(f"📁 Путь к credentials: {creds_path}")
    print(f"📊 URL исходной таблицы: {source_url}")
    print(f"📋 URL таблицы результатов: {results_url}")
    
    # Проверка файла credentials
    if not creds_path or not os.path.exists(creds_path):
        print("❌ Файл google-credentials.json не найден!")
        print("💡 Создайте Service Account в Google Cloud Console и скачайте JSON файл")
        return False
        
    print("✅ Файл credentials найден")
    
    # Проверка URL
    if not source_url or not results_url:
        print("❌ URL таблиц не настроены в .env файле!")
        return False
        
    print("✅ URL таблиц настроены")
    
    try:
        # Подключение к Google Sheets
        print("🔗 Подключение к Google Sheets...")
        
        # Настройка области видимости
        scope = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Аутентификация
        credentials = Credentials.from_service_account_file(creds_path, scopes=scope)
        gc = gspread.authorize(credentials)
        
        print("✅ Аутентификация успешна")
        
        # Тестирование доступа к исходной таблице
        print("📊 Тестирование доступа к исходной таблице...")
        source_sheet = gc.open_by_url(source_url)
        worksheet = source_sheet.sheet1
        
        # Проверка заголовков
        headers = worksheet.row_values(1)
        expected_headers = ['ID', 'Name', 'Email', 'Phone', 'Preferences', 'CV_gcs', 
                          'video_gcs', 'CV_URL', 'Video_URL', 'created_at', 'Questions_URL', 'Processed']
        
        print(f"📋 Найденные заголовки: {headers}")
        
        missing_headers = [h for h in expected_headers if h not in headers]
        if missing_headers:
            print(f"⚠️  Отсутствующие заголовки: {missing_headers}")
            print("💡 Добавьте недостающие колонки в таблицу")
        else:
            print("✅ Все необходимые заголовки присутствуют")
            
        # Тестирование записи
        print("✏️  Тестирование записи в таблицу...")
        test_row = [
            "TEST_001",  # ID
            "Тест Кандидат",  # Name
            "test@example.com",  # Email
            "+7-123-456-78-90",  # Phone
            "Python Developer",  # Preferences
            "",  # CV_gcs
            "",  # video_gcs
            "https://example.com/cv.pdf",  # CV_URL
            "https://example.com/video.mp4",  # Video_URL
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # created_at
            "",  # Questions_URL
            "FALSE"  # Processed
        ]
        
        # Добавляем тестовую строку
        worksheet.append_row(test_row)
        print("✅ Тестовая запись добавлена успешно")
        
        # Читаем обратно для проверки
        all_records = worksheet.get_all_records()
        test_record = next((r for r in all_records if r.get('ID') == 'TEST_001'), None)
        
        if test_record:
            print("✅ Тестовая запись успешно прочитана")
            print(f"📄 Данные: {test_record}")
            
            # Удаляем тестовую запись
            rows = worksheet.get_all_values()
            for i, row in enumerate(rows):
                if row[0] == 'TEST_001':  # ID в первой колонке
                    worksheet.delete_rows(i + 1)
                    print("🗑️ Тестовая запись удалена")
                    break
        
        # Тестирование таблицы результатов
        print("📈 Тестирование доступа к таблице результатов...")
        results_sheet = gc.open_by_url(results_url)
        
        # Проверка наличия листов для разных языков
        worksheets = [ws.title for ws in results_sheet.worksheets()]
        required_sheets = ['Results_ru', 'Results_en', 'Results_pl']
        
        print(f"📋 Найденные листы: {worksheets}")
        
        missing_sheets = [sheet for sheet in required_sheets if sheet not in worksheets]
        if missing_sheets:
            print(f"⚠️  Отсутствующие листы: {missing_sheets}")
            print("💡 Создайте недостающие листы в таблице результатов")
            
            # Создаем недостающие листы
            for sheet_name in missing_sheets:
                try:
                    results_sheet.add_worksheet(title=sheet_name, rows=100, cols=20)
                    print(f"✅ Лист '{sheet_name}' создан")
                except Exception as e:
                    print(f"❌ Ошибка создания листа '{sheet_name}': {e}")
        else:
            print("✅ Все необходимые листы присутствуют")
            
        print("\n🎉 Тестирование Google Sheets завершено успешно!")
        print("✅ Система готова для автоматической обработки")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка подключения к Google Sheets: {e}")
        print("💡 Проверьте:")
        print("   - Правильность Service Account credentials")
        print("   - Доступ к таблицам (должны быть расшарены для Service Account)")
        print("   - URL таблиц в .env файле")
        return False

def main():
    """Главная функция"""
    
    # Загрузка переменных окружения
    from dotenv import load_dotenv
    load_dotenv()
    
    print("🔍 ТЕСТИРОВАНИЕ GOOGLE SHEETS ИНТЕГРАЦИИ")
    print("=" * 50)
    
    success = test_google_sheets_connection()
    
    if success:
        print("\n🚀 Готово! Теперь можно запускать автоматическую обработку:")
        print("   python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
        print("   curl -X POST http://localhost:8000/api/v1/tasks/start")
    else:
        print("\n❌ Необходимо исправить ошибки перед использованием")
        
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
