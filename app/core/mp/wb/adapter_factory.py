from .adapter_enums import AdapterSection, AdapterVersion


class AdapterFactory:
    __adapters: dict[tuple[str, str, int], BaseAdapter] = {}
    __client_factory = AuthenticatedClientFactory()


    def get_adapter(self, shop_id: str, section: AdapterSection, version: AdapterVersion) -> "BaseAdapter"":
        key = (shop_id, section.value, version.value)
        adapter = self.__adapters.get(key)
        if not adapter:

            adapter = self.__get_new_adapter(section, version)
            self.__adapters[key] = adapter
        client = self.__client_factory.get_client(shop_id, section, version)
        adapter.set_client(client)
        return adapter


    def __get_new_adapter(self, section: AdapterSection, version: AdapterVersion) -> "BaseAdapter":
        if section == AdapterSection.PROMOTION and version == AdapterVersion.V1:
            from .adapters.promotion.v1 import PromotionV1Adapter
            return PromotionV1Adapter()
        else:
            raise ValueError(f"No adapter found for section {section} and version {version}")
