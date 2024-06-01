
from abc import ABCMeta


class Generator(metaclass=ABCMeta):
    def __init__(self):
        # Проверка, чтобы предотвратить прямую инстанциацию
        self.__prevent_direct_instantiation()
        # Нормальная инициализация
        self.__common_setup_Generator()

    def __prevent_direct_instantiation(self):
        if type(self) is Generator:
            raise TypeError("MyAbstractClass is an abstract class and cannot be instantiated directly")

    def __common_setup_Generator(self):
        # Общая настройка для всех подклассов
        self._getter = GPTGetter()



