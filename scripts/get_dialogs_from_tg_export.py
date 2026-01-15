import os
import shutil
from pathlib import Path

ROOT = Path(r"C:\Users\vkita\Desktop\диалоги")

def get_unique_name(dest_dir: Path, filename: str) -> Path:
    """
    Возвращает путь с уникальным именем файла:
    file.txt -> file_1.txt -> file_2.txt ...
    """
    dest = dest_dir / filename
    if not dest.exists():
        return dest

    stem = dest.stem
    suffix = dest.suffix
    counter = 1

    while True:
        candidate = dest_dir / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def main():
    if not ROOT.exists():
        raise RuntimeError(f"Папка не существует: {ROOT}")

    # Идём снизу вверх, чтобы потом можно было удалять папки
    for dirpath, dirnames, filenames in os.walk(ROOT, topdown=False):
        dirpath = Path(dirpath)

        # Пропускаем сам корень
        if dirpath == ROOT:
            continue

        for filename in filenames:
            src = dirpath / filename
            dst = get_unique_name(ROOT, filename)

            shutil.move(str(src), str(dst))
            print(f"Перемещён: {src} -> {dst.name}")

        # Удаляем папку, если она пустая
        try:
            dirpath.rmdir()
            print(f"Удалена папка: {dirpath}")
        except OSError:
            # не пустая — значит там что-то осталось (например, скрытые файлы)
            pass


if __name__ == "__main__":
    main()
