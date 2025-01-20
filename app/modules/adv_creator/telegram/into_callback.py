from app.core.telegram import aiogram_objects as ao


class CreateNewAdv(ao.CallbackData, prefix="create_new_adv"):
    wb_user_cabinet_original_id: int