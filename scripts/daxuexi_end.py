import argparse
import os
import re

from clayutil.futil import GetQueryDownloader as Downloader


def get_end_jpg(flag: str) -> str:
    d = Downloader(
        os.path.join(
            os.environ.get("HOME", os.path.abspath("./")), "Downloads", "daxuexi"
        )
    )
    return d.start("https://h5.cyol.com/special/daxuexi/%s/images/end.jpg" % flag, flag)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    args = parser.parse_args()
    m = re.match(r"^http[s?]://h5.cyol.com/special/daxuexi/(.*?)/m.html$", args.url)
    if m:
        print(get_end_jpg(m.group(1)))
    else:
        raise ValueError("invalid URL")
