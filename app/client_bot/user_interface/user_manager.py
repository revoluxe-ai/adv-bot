from .views import keyboards
from sqlalchemy.future import select
from ..db.model import Cabinet, User
from session_maker import get_async_session_maker

sm = get_async_session_maker()

async def go_to_shop_choice(message: types.Message):
    async with sm() as session:
        all_cabs = await session.execute(
            select(Cabinet).join(User).filter(User.telegram_id == message.from_user.id))
        all_cabs = all_cabs.all()
        all_cabs = [cab.Cabinet for cab in all_cabs]
        await message.answer('Ваши кабинеты:', reply_markup=keyboards.get_shop_keyboard(all_cabs))
        return

async def got_to_new_shop(message: types.Message):
    await state.set_state(states.CabinetRegistration.cabinet_name)
    await message.answer('Введите название магазина (кабинета):')
    return


async def go_to_adv_list(shop_id, message):

    return

