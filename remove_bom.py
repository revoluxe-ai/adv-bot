import pathlib
import sys

BOM = b"\xef\xbb\xbf"


def remove_bom_from_file(path: pathlib.Path) -> bool:
    """Удаляет BOM из файла, если он есть. Возвращает True, если был изменён."""
    if not path.is_file():
        print(f"⚠️  Файл {path} не найден")
        return False
    data = path.read_bytes()
    if data.startswith(BOM):
        path.write_bytes(data[len(BOM) :])
        return True
    return False


def main():
    args = sys.argv[1:]
    project_root = pathlib.Path(__file__).parent
    modified = []

    if args:
        # Режим: обработка конкретного файла
        for arg in args:
            file_path = pathlib.Path(arg)
            if remove_bom_from_file(file_path):
                modified.append(file_path)
    else:
        # Режим: пройти по проекту
        for ext in ("*.toml", "*.py"):
            for file in project_root.rglob(ext):
                if remove_bom_from_file(file):
                    modified.append(file)

    if modified:
        print("✅ Удалён BOM из файлов:")
        for f in modified:
            print("  -", f)
    else:
        print("✔️ BOM не найден")


if __name__ == "__main__":
    main()
