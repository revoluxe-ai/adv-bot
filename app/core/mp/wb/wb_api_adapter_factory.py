class WBApiAdapterFactory:
    # ключ доступа к кеш-адаптеру: shop_id, section
    adapters: dict[tuple[str, str], "BaseAdapter"] = {}
