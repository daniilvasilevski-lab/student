#!/usr/bin/env python3

# Читаем файл
with open('unified_launcher.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Исправляем разорванные f-строки
fixes = [
    ('print(f"\n{Fore.YELLOW}📤 Получен сигнал завершения...")', 'print(f"\\n{Fore.YELLOW}📤 Получен сигнал завершения...")'),
    ('print(f"{Fore.CYAN}{\'=\'*80}\\\n")', 'print(f"{Fore.CYAN}{\'=\'*80}\\n")'),
    ('print(f"\n{Fore.CYAN}{\'─\'*60}")', 'print(f"\\n{Fore.CYAN}{\'─\'*60}")'),
    ('print(f"\n{Fore.BLUE}⚙️  Задачи:")', 'print(f"\\n{Fore.BLUE}⚙️  Задачи:")'),
    ('print(f"\n{Fore.MAGENTA}📋 Очередь:")', 'print(f"\\n{Fore.MAGENTA}📋 Очередь:")'),
    ('print(f"\n{Fore.CYAN}📊 Прогресс обработки:")', 'print(f"\\n{Fore.CYAN}📊 Прогресс обработки:")'),
    ('print(f"\n{Fore.YELLOW}🛑 Остановка системы...")', 'print(f"\\n{Fore.YELLOW}🛑 Остановка системы...")'),
    (', end="\\r")', ', end="\\r")')
]

for old, new in fixes:
    content = content.replace(old, new)

# Записываем обратно
with open('unified_launcher.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Исправлены f-строки!")