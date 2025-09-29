import os
import time
import logging
import grpc
from app.grpc_service.predict_ctr_service_pb2 import PredictCtrRequest
from app.grpc_service.predict_ctr_service_pb2_grpc import CtrServiceStub

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s | %(levelname)s | %(name)s | %(message)s')
logger = logging.getLogger("test_client")

def get_active_port(path: str = "work_folder/active_port.txt", timeout: float = 10.0) -> int:
    start = time.time()
    while time.time() - start < timeout:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            if content.isdigit():
                return int(content)
        time.sleep(0.2)
    raise RuntimeError("Не удалось получить активный порт из active_port.txt за отведённое время")


def main():
    port = get_active_port()
    target = f"127.0.0.1:{port}"
    logger.info("Подключаюсь к %s", target)
    with grpc.insecure_channel(target) as channel:
        stub = CtrServiceStub(channel)
        request = PredictCtrRequest(nmids=[111111], phrases=["Test Keyword One", "another_keyword"])
        response = stub.PredictCtr(request, timeout=5)
        logger.info("Ответ сервера: %s", response.predictions)

if __name__ == '__main__':
    main()

