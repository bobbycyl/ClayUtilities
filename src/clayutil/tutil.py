import base64

__all__ = (
    "base64_encode",
    "base64_decode",
    "zh_prettifier",
)

last_symbols = list("。，！？：；、.,!?:;")


def base64_encode(data: bytes, url_safe: bool = False) -> bytes:
    if url_safe:
        return base64.urlsafe_b64encode(data)
    else:
        return base64.b64encode(data)


def base64_decode(data: bytes, url_safe: bool = False) -> bytes:
    if url_safe:
        return base64.urlsafe_b64decode(data)
    else:
        return base64.b64decode(data)


def zh_prettifier(text: str, strip_last_symbol: bool = False) -> str:
    """在中文和英文、数字之间添加一个空格

    :param text: 待处理文本
    :param strip_last_symbol: 是否剔除末尾字符
    :return: 处理后文本
    """
    if not text:
        return text

    text = text.strip()
    result = []
    prev_char = text[0]
    result.append(prev_char)

    for i in range(1, len(text)):
        current_char = text[i]
        prev_is_cjk = "\u4e00" <= prev_char <= "\u9fa5"  # 中文字符范围
        current_is_ascii = "a" <= current_char <= "z" or "A" <= current_char <= "Z" or "0" <= current_char <= "9"  # 英文/数字

        # 检查是否需要添加空格
        if (prev_is_cjk and current_is_ascii) or (current_char >= "\u4e00" and prev_char <= "\u9fa5" and ("a" <= prev_char <= "z" or "A" <= prev_char <= "Z" or "0" <= prev_char <= "9")):

            # 确保前一个字符后没有空格（避免重复添加）
            if result[-1] != " ":
                result.append(" ")

        result.append(current_char)
        prev_char = current_char

    if strip_last_symbol and result and result[-1] in last_symbols:
        result.pop()

    return "".join(result)
