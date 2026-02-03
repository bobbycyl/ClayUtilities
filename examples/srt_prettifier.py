import argparse
import os
from itertools import groupby

from clayutil.tutil import zh_prettifier

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="srt file path")
    parser.add_argument("-strip-last-symbol", action="store_true", help="strip last symbol")
    args = parser.parse_args()
    with open(args.file, "r", encoding="utf-8") as fi:
        # SRT 字幕格式：
        # 第一行：字幕序号
        # 第二行：时间码
        # 第三行之后：字幕文本（可以多行）
        # 分隔符：空行
        with open("%s_prettifier%s" % os.path.splitext(args.file), "w", encoding="utf-8") as fo:
            for is_key, group in groupby(fi, lambda line: bool(line.strip())):
                if is_key:
                    for i, current in enumerate(group):
                        if i <= 1:
                            fo.write(current)
                        else:
                            fo.write(zh_prettifier(current, args.strip_last_symbol))
                            fo.write("\n")
                    fo.write("\n")
