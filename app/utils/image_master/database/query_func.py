import logging

logger = logging.getLogger(__name__)


#
#
# def write_query_with_callback(session:Session, query_func, callback):
#     try:
#         query_func()
#         while True:
#             try:
#                 session.commit()
#                 break
#             except Exception as exc:
#                 logger.error(exc)
#                 sleep(3)
#
#         if callback:
#             callback()
#     except SQLAlchemyError as exc:
#         raise exc
#     finally:
#         session.close()
