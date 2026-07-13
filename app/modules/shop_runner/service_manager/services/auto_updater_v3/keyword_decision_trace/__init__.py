"""Журнал решений V3 по operable keywords (observer preamble, Redis TTL 7d).

Отдельный от ``V3KeywordChangesSnapshot``: полный cascade SKIP/APPLY/BLOCK/PASS
для каждого operable ключа на тике, включая unchanged OFF.
"""

from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_decision_trace.builder import (
    build_keyword_decision_trace_snapshot,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_decision_trace.collector import (
    KeywordDecisionTraceCollector,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_decision_trace.models import (
    KeywordDecisionTraceEntry,
    KeywordDecisionTraceSnapshot,
    KeywordDecisionTraceStep,
    TraceStepStatus,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_decision_trace.query import (
    find_trace_entry,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_decision_trace.redis import (
    KeywordDecisionTraceRedisCache,
    persist_keyword_decision_trace,
)

__all__ = [
    "KeywordDecisionTraceCollector",
    "KeywordDecisionTraceEntry",
    "KeywordDecisionTraceRedisCache",
    "KeywordDecisionTraceSnapshot",
    "KeywordDecisionTraceStep",
    "TraceStepStatus",
    "build_keyword_decision_trace_snapshot",
    "find_trace_entry",
    "persist_keyword_decision_trace",
]
