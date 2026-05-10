def phrases_to_txt_bytes(phrases: list[str]) -> bytes:
    text = "\n".join(phrases)
    if text and not text.endswith("\n"):
        text += "\n"
    return text.encode("utf-8")
