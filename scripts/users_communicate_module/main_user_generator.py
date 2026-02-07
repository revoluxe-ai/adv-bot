from typing import AsyncIterator

from scripts.get_users.filters.filters import (get_non_zero_users,
                                               get_user_with_near_payment,
                                                get_users_by_telegram_id,
                                               get_test_users)
from scripts.get_users.get_users import get_users
from scripts.users_csv_exporter.dto import UserDTO

batch_size = 30

def get_test_users_iterator():
    filter_ids = [373435337]
    get_users_generator = get_users(batch_size=batch_size, telegram_ids_filter=filter_ids)
    final_final_users_generator =  get_test_users(get_users_generator)
    return final_final_users_generator


async def get_users_iterator(
    only_with_auto_campaign: bool = False,
) -> AsyncIterator[UserDTO]:
    telegram_ids_filter = None

    get_users_generator = get_users(
        batch_size=batch_size,
        telegram_ids_filter=telegram_ids_filter,
        only_with_auto_campaign=only_with_auto_campaign,
    )

    final_users_generator = get_users_generator

    return final_users_generator
