import sys
import os

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
)
import argparse
import asyncio
import logging

from app.modules.grpcs.predict_ctr_service.predict_ctr_service import PredictCTRService

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict CTR gRPC Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=50053, help="Port to bind to")
    args = parser.parse_args()

    # Переопределяем HOST и PORT для сервиса (если нужно)
    # Но сам сервис использует значения из config.py, поэтому можно только логировать
    logger.info(f"Запуск PredictCTRService на {args.host}:{args.port}")
    try:
        asyncio.run(PredictCTRService(host=args.host, port=args.port).main())
    except KeyboardInterrupt:
        logger.info("Сервер остановлен пользователем")
    except Exception as exc:
        logger.error(f"Критическая ошибка: {exc}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
