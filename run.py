import logging
from python_modules import setup_uvloop, setup_logging
from predict_ctr_service.utils.settings import settings

setup_uvloop()
setup_logging(settings)

logger = logging.getLogger(__name__)



def run_predict_ctr_service() -> None:
    logger.debug("run_predict_ctr_service: Импортирую main из predict_ctr_service.server")
    from predict_ctr_service.server import main
    logger.debug("run_predict_ctr_service: Запускаю main() из predict_ctr_service.server")
    main()
    logger.debug("run_predict_ctr_service: main() завершён")


if __name__ == "__main__":
    logger.debug("Точка входа: __main__ - старт run_predict_ctr_service()")
    run_predict_ctr_service()
    logger.debug("Точка входа: __main__ - завершение run_predict_ctr_service()")