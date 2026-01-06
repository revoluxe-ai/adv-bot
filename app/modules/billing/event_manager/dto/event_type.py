from enum import StrEnum


class EventType(StrEnum):
    ADD_BALANCE_CLICK = "add_balance_click"
    OFFERTA_SHOWN = "offerta_shown"
    OFFERTA_CONFIRM_CLICK = "offerta_confirm_click"
    AMOUNT_INPUT_RECEIVED = "amount_input_received"
    AMOUNT_INPUT_INVALID = "amount_input_invalid"
    AMOUNT_PROMPT_SHOWN = "amount_prompt_shown"
    INVOICE_SENT = "invoice_sent"
    PRE_CHECKOUT_OK = "pre_checkout_ok"
    PRE_CHECKOUT_FAILED = "pre_checkout_failed"
    SUCCESSFUL_PAYMENT_RECEIVED = "successful_payment_received"
    BALANCE_TOPUP_APPLIED = "balance_topup_applied"
    BALANCE_REMINDER_SENT = "balance_reminder_sent"
    BALANCE_REMINDER_FAILED = "balance_reminder_failed"
    ADD_BALANCE_CONTEXT_LOST = "add_balance_context_lost"
    ERROR = "billing_error"

