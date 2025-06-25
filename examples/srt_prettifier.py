import argparse
import os
from itertools import batched

from clayutil.tutil import zh_prettifier

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="srt file path")
    parser.add_argument("-strip_last_symbol", action="store_true", help="strip last symbol")
    args = parser.parse_args()
    lines = []
    with open(args.file, "r", encoding="utf-8") as fi:
        # 每次读 4 行，对于第 3 行的内容进行 zh_prettifier
        for batch in batched(fi, 4):
            try:
                lines.append(batch[0])
                lines.append(batch[1])
                lines.append(zh_prettifier(batch[2], args.strip_last_symbol))
                lines.append(batch[3])
            except IndexError:
                break

    with open("%s_prettifier%s" % os.path.splitext(args.file), "w", encoding="utf-8") as fo:
        fo.writelines(lines)
