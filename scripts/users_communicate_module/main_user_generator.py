from typing import AsyncIterator

from scripts.get_users.filters.filters import get_non_zero_users, get_user_with_near_payment
from scripts.get_users.get_users import get_users


async def get_users_iterator(batch_size) -> AsyncIterator:
    get_users_generator = get_users(batch_size=batch_size)
    final_users_generator = get_user_with_near_payment(get_users_generator, max_for_payment=14)
    return final_users_generator
