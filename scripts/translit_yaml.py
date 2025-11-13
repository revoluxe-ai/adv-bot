import sys

import yaml
from transliterate import translit  # type: ignore


def transliterate_key(key):
    # Транслитерируем только если есть кириллица
    if any("а" <= c <= "я" or "А" <= c <= "Я" for c in key):
        return translit(key, "ru", reversed=True)
    return key


def transliterate_dict(d):
    if isinstance(d, dict):
        new_dict = {}
        for k, v in d.items():
            new_k = transliterate_key(k)
            new_dict[new_k] = transliterate_dict(v)
        return new_dict
    elif isinstance(d, list):
        return [transliterate_dict(i) for i in d]
    else:
        if isinstance(d, str) and any("а" <= c <= "я" or "А" <= c <= "Я" for c in d):
            return translit(d, "ru", reversed=True)
        return d


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Использование: python translit_yaml.py input.yaml output.yaml")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    with open(input_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    data_translit = transliterate_dict(data)

    with open(output_file, "w", encoding="utf-8") as f:
        yaml.dump(data_translit, f, allow_unicode=True, sort_keys=False)

    print(f"Готово! Транслитерированный YAML сохранён в {output_file}")
