import numpy as np
from PIL import Image as PilImg





class ImageTools:

    @staticmethod
    def dhash(image:PilImg):
        hash_size = 16
        # Изменение размера изображения и преобразование в градации серого
        resized = image.resize((hash_size + 1, hash_size), PilImg.Resampling.LANCZOS)
        grayscale = resized.convert("L")
        # Вычисление различий между соседними пикселями
        pixels = list(grayscale.getdata())
        difference = []
        for row in range(hash_size):
            for col in range(hash_size):
                pixel_left = pixels[row * (hash_size + 1) + col]
                pixel_right = pixels[row * (hash_size + 1) + col + 1]
                difference.append(pixel_left > pixel_right)

        # Конвертация в числовое значение хеша
        decimal_value = 0
        hex_string = []
        for index, value in enumerate(difference):
            if value:
                decimal_value += 2 ** (index % 8)
            if (index % 8) == 7:
                hex_string.append(hex(decimal_value)[2:].rjust(2, "0"))
                decimal_value = 0

        return ''.join(hex_string)

    @staticmethod
    def _get_image_aspect_ratio(cropped_img):
        width, height = cropped_img.size
        larger_side = max(width, height)
        smaller_side = min(width, height)
        aspect_ratio = larger_side / smaller_side
        return aspect_ratio

    def get_paint_size(self, image: PilImg):
        image = self.remove_white_space(image)
        width, height = image.size
        if width > height:
            width = 50
            height = 40
        else:
            width = 40
            height = 50
        return  width, height




    def get_standard_proportion(self, image: PilImg, registered_sizes):
        cropped_image = self.remove_white_space(image)
        aspect_ratio = self._get_image_aspect_ratio(cropped_image)
        return self._find_closest_size(aspect_ratio, registered_sizes)

    @staticmethod
    def _find_closest_size(proportion, registered_sizes)->int:
        size_proportions = []
        for size in registered_sizes:
            width, height = map(int, size.split('x'))
            size_proportions.append(max(width, height) / min(width, height))
        differences = [abs(proportion - size_prop) for size_prop in size_proportions]
        closest_index = differences.index(min(differences))
        size_str: str = registered_sizes[closest_index]
        return int(size_str.replace('x', ''))


    @staticmethod
    def remove_white_space( img: PilImg):
        np_img = np.array(img)
        non_white_pixels = np.all(np_img < 248, axis=-1)
        non_white_pixel_coords = np.where(non_white_pixels)
        if non_white_pixel_coords[0].size > 0 and non_white_pixel_coords[1].size > 0:
            top_left = (np.min(non_white_pixel_coords[1]), np.min(non_white_pixel_coords[0]))
            bottom_right = (np.max(non_white_pixel_coords[1]), np.max(non_white_pixel_coords[0]))
            cropped_img = img.crop((top_left[0], top_left[1], bottom_right[0], bottom_right[1]))
            return cropped_img
        else:
            # Если не белых пикселей нет, возвращаем исходное изображение
            return img

    @staticmethod
    def check_image_orientation(image):
        # Загрузка изображения
        # Получение размеров изображения
        width, height = image.size
        # Определение ориентации
        if width > height:
            return "Горизонтальное"
        elif height > width:
            return "Вертикальное"

    @staticmethod
    def check_image_orientation_en(image):
        # Загрузка изображения
        # Получение размеров изображения
        width, height = image.size
        # Определение ориентации
        if width > height:
            return 'gorizont'
        elif height > width:
            return 'vertical'


    @staticmethod
    def resize_image_proportionally(image, min_side_length)-> PilImg:
        # Загружаем изображение
        # Определяем текущие размеры
        width, height = image.size
        # Определяем коэффициент масштабирования на основе наименьшей стороны
        if width < height:
            scale_factor = min_side_length / width
        else:
            scale_factor = min_side_length / height
        # Вычисляем новые размеры
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        # Изменяем размер изображения
        resized_image = image.resize((new_width, new_height), PilImg.Resampling.LANCZOS)
        # Сохраняем измененное изображение
        return resized_image

    @staticmethod
    def get_full_image(image, padding_left, padding_right, padding_top, padding_bottom, fill_color):
        # Расчет новых размеров изображения с учетом дополнительных полей
        new_width = image.width + padding_left + padding_right
        new_height = image.height + padding_top + padding_bottom
        # Создание нового изображения с учетом новых размеров и цвета заливки
        new_image = PilImg.new("RGB", (new_width, new_height), fill_color)
        # Вставка исходного изображения в новое изображение с учетом отступов
        new_image.paste(image, (padding_left, padding_top))
        return new_image



    @staticmethod
    def hamming_distance(dhash1, dhash2):
        """
        Вычисляет расстояние Хэмминга между двумя dhash.

        :param dhash1: Первый dhash как строка шестнадцатеричных символов.
        :param dhash2: Второй dhash как строка шестнадцатеричных символов.
        :return: Расстояние Хэмминга как целое число.
        """
        # Преобразование хешей в двоичное представление
        bin_dhash1 = bin(int(dhash1, 16))[2:].zfill(64)
        bin_dhash2 = bin(int(dhash2, 16))[2:].zfill(64)

        # Расчет расстояния Хэмминга
        distance = sum(char1 != char2 for char1, char2 in zip(bin_dhash1, bin_dhash2))

        return distance

    @staticmethod
    def image_distance_norm(distance):
        # Проверка, что distance находится в допустимом диапазоне
        if not (0 <= distance <= 2):
            raise ValueError("distance должен быть в диапазоне от 0 до 2")

        # Нормализация значения distance
        if distance <= 0.5:
            return 0
        elif distance >= 1.5:
            return 1
        else:
            # Нормализация оставшегося диапазона (0.5 - 1.5) к (0 - 1) и инвертирование
            return (distance - 0.5) / (1.5 - 0.5)
