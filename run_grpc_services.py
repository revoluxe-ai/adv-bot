import os
import signal
import subprocess


services = [
    "python app/modules/grpcs/image_vector_service/server.py --host 0.0.0.0 --port 50052",
    "python app/modules/grpcs/word2vec_service/server.py --host 0.0.0.0 --port 50051",
    "python app/modules/grpcs/predict_ctr_service/server.py --host 0.0.0.0 --port 50053",
]

processes = []

try:
    for cmd in services:
        if os.name == "nt":
            p = subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            p = subprocess.Popen(cmd, shell=True)
        processes.append(p)
    print("Все gRPC сервисы запущены. Для остановки нажмите Ctrl+C.")
    for p in processes:
        p.wait()
except KeyboardInterrupt:
    print("Остановка всех сервисов...")
    for p in processes:
        try:
            if os.name == "nt":
                p.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                p.terminate()
        except Exception:
            pass
    for p in processes:
        p.wait()
    print("Все сервисы остановлены.")
