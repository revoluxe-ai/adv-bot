# examples/wb_container_boot.py
from app.core.mp.wb.containers import WBApiContainer

container = WBApiContainer()
container.config.promotion.base_url.from_value("https://advert-api.wildberries.ru/")

adapter_factory = container.adapter_factory()
print("WB container boot OK")
