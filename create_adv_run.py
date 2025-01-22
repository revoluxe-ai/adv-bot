from time import sleep
import redis
from app.client_bot import const
from app.modules.adv_creator.backend.tasks import create_complex_advs_task

r = redis.StrictRedis(host='localhost', port=6379, db=1)

# Очистка всех задач в очереди
r.delete('celery')  # Имя очереди по умолчанию - 'celery'

shop_id = '8f4fad97-ea21-4cdc-8f4f-8f067076b05c'
# shop_id_orion = '88001207-a155-47d2-9891-77f0c23755c3'
# shop_id_skl_group = '84f86c01-137d-5992-8f62-614d5f119bd1'


if __name__ == '__main__':
    with open('nmids_for_create_advs.txt', 'r') as f:
        nmids = f.readlines()

    for nmid in nmids:
        # nmid = row[0]
        # sho_id = row[1]
        nmid = nmid.replace('\n', '')
        nmid = int(nmid)
        # while True:
        #     try:
        #         create_complex_advs_task(nmid, shop_id, hard_mode=False)
        #     except Exception:
        #         logger.error(f'Ошибка при создании комплексной рк для артикула {nmid}', exc_info=True)
        #         sleep(60)
        # create_complex_advs_task(nmid, shop_id, False, const.ADMINS[0])
        create_complex_advs_task.apply_async((nmid, shop_id, False, const.ADMINS[0]))
        print(f'Создана задача на создание комплексной рк для артикула {nmid}')
        pass