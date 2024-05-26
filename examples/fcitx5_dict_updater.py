import os
import pathlib
import shutil
import sqlite3
from collections import UserDict
from typing import Dict

from clayutil.futil import Downloader, Properties


class Fcitx5DictUpdater(UserDict):
    global custom_proxies
    data: Dict[str, str]  # {词库名(文件名): 词库URL地址}

    def download_dicts(self):
        d = Downloader(os.path.join(pathlib.Path.home(), ".local/share/fcitx5/pinyin/dictionaries/"))
        for dict_name, dict_url in self.data.items():
            print(dict_name, dict_url)
            d.start(dict_url, dict_name, proxies=custom_proxies)


def _download_tmp(output_dir):
    d = Downloader(output_dir, mirrors=mirrors)
    d.start("https://repo.archlinuxcn.org/pkginfo.db")
    d.start("https://gitlab.archlinux.org/archlinux/packaging/packages/fcitx5-pinyin-zhwiki/-/raw/main/PKGBUILD")


def _get_zhwiki_url(output_dir):
    p = Properties(os.path.join(output_dir, "PKGBUILD"))
    p.load()
    return "https://github.com/felixonmars/fcitx5-pinyin-zhwiki/releases/download/%s/zhwiki-%s.dict" % (
        p.get("_converterver"),
        p.get("_webslangver"),
    )


def _get_moegirl_url(output_dir):
    conn = sqlite3.connect("%s/pkginfo.db" % output_dir)
    c = conn.cursor()
    cursor = c.execute('SELECT * FROM pkginfo WHERE pkgname = "fcitx5-pinyin-moegirl" AND forarch = "x86_64" ORDER BY mtime DESC;')
    pkgver: str = cursor.fetchone()[3]
    hyphen_loc = pkgver.find("-")
    tag = pkgver[:hyphen_loc]
    conn.close()
    return "https://github.com/outloudvi/mw2fcitx/releases/download/%s/moegirl.dict" % (tag,)


if __name__ == "__main__":
    ##################################
    # 脚本更新默认词库包含：          #
    # 1. zhwiki                      #
    # 2. moegirl                     #
    # 3. cedict                      #
    # 4. chinese-frequency-word-list #
    ##################################

    # 设置镜像
    mirrors = {
        "https://repo.archlinuxcn.org/": ["https://mirrors.cernet.edu.cn/archlinuxcn/"],
    }

    # 设置临时文件夹为tmp
    os.makedirs("./tmp", exist_ok=True)
    tmp_dir = os.path.abspath("./tmp")

    # 下载临时文件
    _download_tmp(tmp_dir)

    # 设置词库
    fcitx5_dicts_dict = {
        "zhwiki.dict": _get_zhwiki_url(tmp_dir),
        "moegirl.dict": _get_moegirl_url(tmp_dir),
        "cedict.dict": "https://github.com/cathaysia/fcitx5_dicts/releases/download/0.0.1/cedict.dict",
        "chinese-frequency-word-list.dict": "https://github.com/cathaysia/fcitx5_dicts/releases/download/v0.0.2/chinese-frequency-word-list.dict",
    }

    # 设置代理
    custom_proxies = {"http": "http://127.0.0.1:2334", "https": "http://127.0.0.1:2334"}
    Fcitx5DictUpdater(fcitx5_dicts_dict).download_dicts()

    # 清理临时目录
    shutil.rmtree("./tmp")
