import os
import re

# 📂 путь к папке с логами
LOG_DIR = r"./reports"   # поменяй на свой путь
OUTPUT_FILE = "./invited_users.txt"

# шаблон для поиска блока "Удалось пригласить:"
block_pattern = re.compile(
    r"Удалось пригласить:(.*?)(?:Не удалось пригласить:|= = =|$)",
    re.DOTALL
)

# шаблон для поиска всех @username
username_pattern = re.compile(r"@[\w\d_]+")

all_usernames = set()

for filename in os.listdir(LOG_DIR):
    filepath = os.path.join(LOG_DIR, filename)
    if not os.path.isfile(filepath):
        continue
    with open(filepath, encoding="utf-8") as f:
        text = f.read()
        # ищем блок "Удалось пригласить"
        matches = block_pattern.findall(text)
        for block in matches:
            # ищем все @username внутри блока
            usernames = username_pattern.findall(block)
            all_usernames.update(usernames)

# сохраняем результат
with open(os.path.join(OUTPUT_FILE), "w", encoding="utf-8") as f:
    f.write("\n".join(sorted(all_usernames)))

print(f"✅ Найдено {len(all_usernames)} уникальных имён. Сохранено в {OUTPUT_FILE}")



if __name__ == '__main__':
    pass