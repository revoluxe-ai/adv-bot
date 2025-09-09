from app.configs.infrastructure_config.wb_config import WBConfig
from app.core.di import Provide, inject
from app.core.di.app_container import AppContainer

SERVICE_DOMAINS: dict[str, str] = {
    "content": "content-api",
    "discounts": "discounts-prices-api",
    "statistics": "statistics-api",
    "promotion": "advert-api",
    "feedbacks": "feedbacks-api",
    "marketplace": "marketplace-api",
}

SANDBOX_SUPPORTED: set[str] = {
    "content",
    "discounts",
    "statistics",
    "promotion",
    "feedbacks",
    "marketplace",
}


@inject
def resolve_wb_base_url(
    service: str,
    wb_config: WBConfig = Provide[AppContainer.settings.provided.infrastructure.wb],
) -> str:
    domain = SERVICE_DOMAINS.get(service)
    if not domain:
        raise ValueError(f"Unknown WB service: {service}")

    if wb_config.test_mode and service in SANDBOX_SUPPORTED:
        domain = f"{domain}-sandbox"

    return f"https://{domain}.wildberries.ru"
