"""
Скрипт для генерации gRPC артефактов из proto файлов.
"""

import subprocess
import sys
from pathlib import Path


def generate_grpc_files():
    """
    Генерация Python файлов из proto файлов.
    """
    # Пути к файлам
    current_dir = Path(__file__).parent
    proto_file = current_dir / "protos" / "image_vector.proto"
    output_dir = current_dir / "grpc_service"

    # Проверка существования proto файла
    if not proto_file.exists():
        print(f"Ошибка: proto файл не найден: {proto_file}")
        sys.exit(1)

    # Создание директории для выходных файлов
    output_dir.mkdir(exist_ok=True)

    # Команда для генерации
    cmd = [
        sys.executable,
        "-m",
        "grpc_tools.protoc",
        f"--proto_path={proto_file.parent}",
        f"--python_out={output_dir}",
        f"--grpc_python_out={output_dir}",
        str(proto_file),
    ]

    print(f"Генерирую gRPC файлы из {proto_file}")
    print(f"Команда: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Генерация успешно завершена!")
        print(f"Сгенерированные файлы в {output_dir}:")

        # Показываем созданные файлы
        for file in output_dir.glob("*.py"):
            print(f"  - {file.name}")

    except subprocess.CalledProcessError as e:
        print(f"Ошибка при генерации: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        sys.exit(1)
    except FileNotFoundError:
        print("Ошибка: grpc_tools не установлен. Установите его командой:")
        print("pip install grpcio-tools")
        sys.exit(1)


if __name__ == "__main__":
    generate_grpc_files()
