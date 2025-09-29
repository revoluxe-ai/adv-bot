import sys
import os
import argparse
import logging

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
)

from .predict_ctr_service import PredictCTRService

logger = logging.getLogger(__name__)


async def run_server_async() -> None:
    logger.debug("run_server_async(): parsing arguments")
    parser = argparse.ArgumentParser(description="Predict CTR gRPC Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=50053, help="Port to bind to")
    args = parser.parse_args()

    logger.info(f"Запуск PredictCTRService на {args.host}:{args.port}")
    try:
        service = PredictCTRService(host=args.host, port=args.port)
        logger.debug("PredictCTRService instance created, calling main()")
        await service.main()
        logger.debug("PredictCTRService.main() completed (normal stop)")
    except KeyboardInterrupt:
        logger.info("Сервер остановлен пользователем")
    except Exception as exc:
        logger.error(f"Критическая ошибка: {exc}", exc_info=True)
        raise
