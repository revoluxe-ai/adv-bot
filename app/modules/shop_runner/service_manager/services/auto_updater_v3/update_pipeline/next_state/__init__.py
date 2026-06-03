"""NextStateManager: in-place операции над ``KeywordDTO`` для preamble executors."""

from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.manager import (
    NextStateManager,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.phase_report import (
    next_state_steps_for_executor,
    steps_to_v3_actions,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.ledger_sync import (
    sync_update_context_to_ledger,
)

__all__ = (
    "NextStateManager",
    "next_state_steps_for_executor",
    "steps_to_v3_actions",
    "sync_update_context_to_ledger",
)
