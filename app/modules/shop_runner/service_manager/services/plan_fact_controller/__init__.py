"""Plan fact stats: ClickHouse sync and controllers."""

__all__ = ["PlanFactController", "PlanFactManager"]


def __getattr__(name: str) -> object:
    if name == "PlanFactController":
        from .plan_fact_controller import PlanFactController

        return PlanFactController
    if name == "PlanFactManager":
        from .plan_fact_manager import PlanFactManager

        return PlanFactManager
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
