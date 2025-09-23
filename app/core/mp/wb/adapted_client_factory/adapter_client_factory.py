






class AdaptedClientFactory:

    __promotion_client:   = None


    @property
    def promotion_client(self):
        from ..generated.promotion.v1.client.client import AuthenticatedClient


        return self.__get


    def __get_adapted_client(self, client_class: A):


