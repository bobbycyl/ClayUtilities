import argparse
import os
from itertools import batched

from clayutil.tutil import zh_prettifier

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="srt file path")
    parser.add_argument("-strip-last-symbol", action="store_true", help="strip last symbol")
    args = parser.parse_args()
    lines = []
    with open(args.file, "r", encoding="utf-8") as fi:
        # 每次读 4 行，对于第 3 行的内容进行 zh_prettifier
        with open("%s_prettifier%s" % os.path.splitext(args.file), "w", encoding="utf-8") as fo:
            for batch in batched(fi, 4):
                # todo: 自动判断是否是双语字幕，调整batched的参数
                try:
                    fo.write(batch[0])
                    fo.write(batch[1])
                    fo.write(zh_prettifier(batch[2], args.strip_last_symbol))
                    fo.write("\n\n")
                except IndexError:
                    break
