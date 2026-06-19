import base64
import re
import unicodedata

__all__ = (
    "base64_encode",
    "base64_decode",
    "zh_prettifier",
    "zh_clean_spaces",
    "zh_is_garbled",
)

WEB_STOP_TERMS = [
    "&amp",
    "&lt",
    "&gt",
    "&quot",
    "&apos",
    "&nbsp",
    "&copy",
    "&reg",
    "&trade",
    "&euro",
    "&pound",
    "&yen",
    "&mdash",
    "&ndash",
    "&lsquo",
    "&rsquo",
    "&ldquo",
    "&rdquo",
    "&hellip",
    "&amp;",
    "&lt;",
    "&gt;",
    "&quot;",
    "&apos;",
    "&nbsp;",
    "&copy;",
    "&reg;",
    "&trade;",
    "&euro;",
    "&pound;",
    "&yen;",
    "&mdash;",
    "&ndash;",
    "&lsquo;",
    "&rsquo;",
    "&ldquo;",
    "&rdquo;",
    "&hellip;",
]
END_PUNCT = list("。！？.!?")
END_PUNCT_EXT = list("。，！？：；、.,!?:;")
MAX_GARBAGE_RATIO = 0.12  # 私用区/替换字符占比上限
MAX_CTRL_RATIO = 0.08  # 控制字符（非换行）占比上限
MAX_LATIN1_RATIO = 0.15  # Latin-1 扩展区字符占比上限
PDF_MIN_CHARS = 50  # PDF 页面模式：有效字符低于此 → 图片/扫描件
STR_MIN_CHARS = 5  # 字符串模式：有效字符低于此 → 内容太短
WIERD_PATTERN = re.compile(r"[%&\'*+^!@#$]{2,}")
ANCHOR_PATTERN = re.compile(r"(?:万元|业绩|产业|企业|公共|创新|利润|利率|发展|同比|增速|增长|市委|建设|战略|打造|收入|改革|教育|深化|生产|省委|营收|落实|行业|规划|计划|贯彻)")
ASCII_ENGINEERING_PATTERN = re.compile(r"[0-9a-zA-Z\s.,|\-()/]")
TITLE_ANCHORS = {"摘要", "关键词", "参考文献", "致谢", "引言", "前言", "结论", "绪论", "专栏", "目录"}
MAX_TITLE_LEN = 50


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


def sort_text(text: str, split_char: str = "\n", regex: bool = False) -> str:
    return split_char.join(sorted(re.split(split_char, text) if regex else text.split(split_char)))


def is_cjk(char: str) -> bool:
    return "\u4e00" <= char <= "\u9fa5"  # 中文字符范围


def is_alpha_number(char: str) -> bool:
    # 这里不能用 str.isalnum()
    return "a" <= char <= "z" or "A" <= char <= "Z" or "0" <= char <= "9"


def zh_prettifier(text: str, strip_end_punct: bool = False) -> str:
    """在中文和英文、数字之间添加一个空格，并清除首尾空白

    :param text: 待处理文本
    :param strip_end_punct: 是否剔除末尾标点符号
    :return: 处理后文本（strip 后）
    """
    if not text:
        return text

    text = text.strip()
    result = []
    prev_char = text[0]
    result.append(prev_char)

    for i in range(1, len(text)):
        current_char = text[i]

        # 检查是否需要添加空格
        # 确保前一个字符后没有空格（避免重复添加）
        if (is_cjk(prev_char) and is_alpha_number(current_char)) or (is_cjk(current_char) and is_alpha_number(prev_char)) and result[-1] != " ":
            result.append(" ")

        result.append(current_char)
        prev_char = current_char

    if strip_end_punct and result and result[-1] in END_PUNCT_EXT:
        result.pop()

    return "".join(result)


def zh_clean_spaces(text: str) -> str:
    """"""
    # 汉字
    han = r"\u4e00-\u9fff\u3400-\u4dbf\U00020000-\U0002a6df\uf900-\ufaff"
    # 中文标点
    cn_punct = r"\u3000-\u303f\uff00-\uffef"
    # 空格和全角空格
    spaces = r"[ \u3000\t]"

    # 1. 删除中文-中文之间的空格（循环处理，防止 "你 好 世界" 一次清不干净）
    pattern = re.compile(rf"([{han}]){spaces}+([{han}])")
    while True:
        new = pattern.sub(r"\1\2", text)
        if new == text:
            break
        text = new

    # 2. 删除中文标点两边的空格
    text = re.sub(rf"{spaces}*([{cn_punct}]){spaces}*", r"\1", text)

    return text


def classify_char(ch: str) -> str:
    cp = ord(ch)
    if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF or 0x20000 <= cp <= 0x2A6DF or 0xF900 <= cp <= 0xFAFF:
        return "han"
    if 0x3000 <= cp <= 0x303F or 0xFF00 <= cp <= 0xFFEF:
        return "cn_punct"
    if ch in " \t\n\r\f" or cp == 0x0C:
        return "space"
    if cp < 0x20 or cp == 0x7F or 0x80 <= cp <= 0x9F:
        return "ctrl"
    if 0xA1 <= cp <= 0xFF:
        return "latin1"
    if 0x20 <= cp <= 0x7E:
        return "ascii"
    if 0xE000 <= cp <= 0xF8FF or 0xF0000 <= cp <= 0xFFFFF or 0x100000 <= cp <= 0x10FFFF:
        return "garbage"
    cat = unicodedata.category(ch)
    if cat in ("Cs", "Co"):
        return "garbage"
    return "other"


def _analyze(text: str) -> tuple[dict[str, int], int]:
    counts = {"han": 0, "cn_punct": 0, "ascii": 0, "space": 0, "garbage": 0, "other": 0, "ctrl": 0, "latin1": 0}
    for ch in text:
        counts[classify_char(ch)] += 1
    non_sp = len(text) - counts["space"]
    return counts, non_sp


def zh_is_garbled(text: str, pdf_page_mode: bool = False) -> tuple[bool, str]:
    counts, non_sp = _analyze(text)

    if non_sp == 0:
        return True, "空内容"

    min_chars = PDF_MIN_CHARS if pdf_page_mode else STR_MIN_CHARS
    meaningful = counts["han"] + counts["ascii"] + counts["other"]
    weird_r = len(WIERD_PATTERN.findall(text)) / non_sp  # 这是次数与字符数的比值，可能失真，但暂时保持此算法
    ascii_engineering_r = len(ASCII_ENGINEERING_PATTERN.findall(text)) / non_sp

    # 规则0：提前拦截，有效字符极少 → 图片 PDF / 扫描件
    if meaningful < min_chars:
        return True, f"有效字符仅 {meaningful} 个（门槛 {min_chars}）"

    han_r = counts["han"] / non_sp
    garbage_r = counts["garbage"] / non_sp
    ctrl_r = counts["ctrl"] / non_sp
    latin1_r = counts["latin1"] / non_sp
    other_r = counts["other"] / non_sp
    ascii_r = counts["ascii"] / non_sp

    # 规则1：私用区 / 替换字符过多
    if garbage_r > MAX_GARBAGE_RATIO:
        return True, f"私用区字符占 {garbage_r * 100:.1f}%"

    # 规则2：控制字符过多
    if ctrl_r > MAX_CTRL_RATIO:
        return True, f"控制字符占 {ctrl_r * 100:.1f}%"

    # 规则3：Latin-1 扩展区字符过多
    if latin1_r > MAX_LATIN1_RATIO:
        return True, f"Latin-1 扩展区字符占 {latin1_r * 100:.1f}%"

    # 规则4：纯数字/表格
    if ascii_engineering_r > 0.80 and latin1_r < 0.01 and weird_r > 0.15:
        return True, f"无意义 ASCII 字符占 {weird_r * 100:.1f}%"

    # 规则5：高频词锚点
    if 0.05 <= han_r <= 0.3:
        has_anchor = bool(ANCHOR_PATTERN.search(text))
        if has_anchor:
            return False, "触发高频词锚点，提前返回"  # 只要触发锚点就提前返回，以免后续判断变更
        if latin1_r > 0:
            # 规则3 在低中文比率时的严格拦截
            return True, f"中文过少，同时 Latin-1 扩展区字符占 {latin1_r * 100:.1f}"

    # 规则6：字体 ToUnicode 映射缺失
    # 表现：有足量字符，但汉字极少，扩展拉丁/特殊字符堆积
    if han_r < 0.02 and other_r > 0.1 and meaningful > min_chars:
        return True, f"汉字仅占 {han_r * 100:.1f}%，未知字符占 {other_r * 100:.1f}%（字体 ToUnicode 映射缺失）"

    # 规则7：汉字被错误映射为大写字母序列
    # 特征：几乎纯 ASCII，含连续大写串，却无任何可读小写英文单词（≥3字母）
    if ascii_r > 0.85 and han_r < 0.01:
        has_lower_word = bool(re.search(r"[a-z]{3,}", text))
        has_upper_run = bool(re.search(r"[A-Z]{3,}", text))
        upper_r = sum(1 for c in text if c.isupper()) / non_sp
        if has_upper_run and not has_lower_word and upper_r > 0.15:
            return True, f"大写字母串占 {upper_r * 100:.1f}%，无可读小写英文词（汉字映射为字母乱码）"

    # 规则8：中文专项拦截
    if han_r < 0.01 and ascii_engineering_r < 0.75:
        return True, "外语嫌疑"

    # 规则9：规则4 在极少汉字时的加强拦截
    if weird_r > 0.2 and han_r < 0.01:
        return True, f"垃圾字符占 {weird_r * 100:.1f}%"

    return False, "正常"


def zh_is_title_line(line: str):
    line = line.strip()
    if not line:
        return False

    if line in TITLE_ANCHORS or any(line.startswith(ft) and len(line) < MAX_TITLE_LEN for ft in TITLE_ANCHORS):
        return True

    if len(line) < MAX_TITLE_LEN and re.match(r"^第[一二三四五六七八九十百零〇0-9]+[章节篇部分]", line):
        return True

    if len(line) < MAX_TITLE_LEN and re.match(r"^[（(]?[一二三四五六七八九十]+[）)]?[\s、.]", line):
        return True

    return bool(re.match(r"^附录[A-Za-z]?", line))

    return False


def merge_lines_by_punct(lines):
    if not lines:
        return []

    paragraphs = []
    current = ""

    for _i, line in enumerate(lines):
        stripped_line = line.strip()
        if not stripped_line:
            continue

        # 如果当前行是标题 → 先保存 current（如果不为空），然后新开一段
        if zh_is_title_line(stripped_line):
            if current:
                paragraphs.append(current)
            paragraphs.append(stripped_line)  # 标题独立成段
            current = ""  # 重置，标题后的内容从新段开始
        else:
            # 非标题行：判断是否接在 current 后面
            if current == "":
                current = stripped_line
            else:
                # 检查 current 末尾是否有结束标点
                if current and current[-1] in END_PUNCT_EXT:
                    # 已结束，存入并新开
                    paragraphs.append(current)
                    current = stripped_line
                else:
                    # 未结束，合并
                    current += stripped_line

    # 循环结束后，处理剩余 current
    if current:
        paragraphs.append(current)

    return paragraphs
