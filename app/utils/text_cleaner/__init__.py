def clear(text) -> str:
    text = text.replace("_", "")
    text = text.replace('"', "")
    text = text.replace("""'""", "")
    text = text.replace(",", "")
    text = text.replace(".", "")
    return text
