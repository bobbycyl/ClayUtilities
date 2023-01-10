import os
import sqlite3
from typing import Dict

from clayutil.futil import GetQueryDownloader as Downloader, Properties


class Fcitx5DictUpdater(object):
    """Fcitx5词库更新工具

    更新Fcitx5默认词库目录中的指定词库

    Attributes:
        dicts: {词库名(文件名): 词库URL地址}
    """

    def __init__(self, dicts):
        self.dicts: Dict[str, str] = dicts

    def download_dicts(self):
        d = Downloader(
            "%s%s" % (os.environ["HOME"], "/.local/share/fcitx5/pinyin/dictionaries/")
        )
        for dict_name, dict_url in self.dicts.items():
            d.start(dict_url, dict_name)


def _download_tmp(output_dir):
    d = Downloader(output_dir)
    d.start("https://mirrors.ustc.edu.cn/archlinuxcn/pkginfo.db")
    d.start(
        "https://raw.fastgit.org/archlinux/svntogit-community/packages/fcitx5-pinyin-zhwiki/trunk/PKGBUILD"
    )


def _get_zhwiki_url(output_dir):
    p = Properties("%s/PKGBUILD" % output_dir)
    pd = p.properties
    return (
        "https://download.fastgit.org/felixonmars/fcitx5-pinyin-zhwiki/releases/download/%s/zhwiki-%s.dict"
        % (pd.get("_converterver"), pd.get("_webslangver"))
    )


def _get_moegirl_url(output_dir):
    conn = sqlite3.connect("%s/pkginfo.db" % output_dir)
    c = conn.cursor()
    cursor = c.execute(
        'SELECT * FROM pkginfo WHERE pkgname = "fcitx5-pinyin-moegirl" AND forarch = "x86_64" ORDER BY mtime DESC;'
    )
    pkgver: str = cursor.fetchone()[3]
    hyphen_loc = pkgver.find("-")
    tag = pkgver[:hyphen_loc]
    return (
        "https://download.fastgit.org/outloudvi/mw2fcitx/releases/download/%s/moegirl.dict"
        % tag
    )


if __name__ == "__main__":
    # ==========================================================================
    # 脚本更新默认词库包含：
    # 1. zhwiki
    # 2. moegirl
    # 3. cedict
    # 4. chinese-frequency-word-list
    # ==========================================================================

    # 设置临时文件夹为当前目录
    tmp_dir = os.path.abspath("./")

    # 下载临时文件
    _download_tmp(tmp_dir)

    # 设置词库
    fcitx5_dicts_dict = {
        "zhwiki": _get_zhwiki_url(tmp_dir),
        "moegirl": _get_moegirl_url(tmp_dir),
        "cedict": "https://download.fastgit.org/cathaysia/fcitx5_dicts/releases/download/0.0.1/cedict.dict",
        "chinese-frequency-word-list": "https://download.fastgit.org/cathaysia/fcitx5_dicts/releases/download/v0.0.2/chinese-frequency-word-list.dict",
    }

    Fcitx5DictUpdater(fcitx5_dicts_dict).download_dicts()
