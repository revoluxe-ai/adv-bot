from app.core.telegram import aiogram_objects as ao


class CreateNewAdvs(ao.CallbackData, prefix="create_new_adv"):
    wb_user_cabinet_original_id: int


class ConfirmCreateComplexAdv(ao.CallbackData, prefix="confirm_complex_adv"):
    action: str  # "continue" или "cancel"
    nmid: int
    wb_cabinet_original_id: int
