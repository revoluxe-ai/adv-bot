# Скрипт для удаления BOM из файла Python
import sys
import os

filename = r"app/modules/billing/event_manager/models.py"

with open(filename, "rb") as f:
    content = f.read()

# Удаляем BOM, если есть
BOM = b"\xef\xbb\xbf"
if content.startswith(BOM):
    content = content[len(BOM):]
    with open(filename, "wb") as f:
        f.write(content)
    print(f"BOM удалён из {filename}")
else:
    print(f"BOM не найден в {filename}")

