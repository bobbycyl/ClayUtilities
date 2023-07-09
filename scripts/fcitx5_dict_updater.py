import os
import random
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
            os.path.join(os.environ["HOME"], ".local/share/fcitx5/pinyin/dictionaries/")
        )
        for dict_name, dict_url in self.dicts.items():
            print(dict_name, dict_url)
            d.start(dict_url, dict_name)


def _download_tmp(output_dir):
    global archlinuxcn_link
    d = Downloader(output_dir)
    d.start("%s/pkginfo.db" % archlinuxcn_link)
    d.start(
        "https://gitlab.archlinux.org/archlinux/packaging/packages/fcitx5-pinyin-zhwiki/-/raw/main/PKGBUILD"
    )


def _get_zhwiki_url(output_dir):
    global github_link
    p = Properties("%s/PKGBUILD" % output_dir)
    pd = p.properties
    return "%s/felixonmars/fcitx5-pinyin-zhwiki/releases/download/%s/zhwiki-%s.dict" % (
        github_link,
        pd.get("_converterver"),
        pd.get("_webslangver"),
    )


def _get_moegirl_url(output_dir):
    global github_link
    conn = sqlite3.connect("%s/pkginfo.db" % output_dir)
    c = conn.cursor()
    cursor = c.execute(
        'SELECT * FROM pkginfo WHERE pkgname = "fcitx5-pinyin-moegirl" AND forarch = "x86_64" ORDER BY mtime DESC;'
    )
    pkgver: str = cursor.fetchone()[3]
    hyphen_loc = pkgver.find("-")
    tag = pkgver[:hyphen_loc]
    return "%s/outloudvi/mw2fcitx/releases/download/%s/moegirl.dict" % (
        github_link,
        tag,
    )


if __name__ == "__main__":
    # ==========================================================================
    # 脚本更新默认词库包含：
    # 1. zhwiki
    # 2. moegirl
    # 3. cedict
    # 4. chinese-frequency-word-list
    # ==========================================================================

    # GitHub mirrors
    use_mirrors = True
    github_mirrors = [
        "https://gh.ddlc.top/https://github.com",
        "https://gh.gh2233.ml/https://github.com",
        "https://github.moeyy.xyz/https://github.com",
        "https://cors.isteed.cc/github.com",
    ]
    archlinuxcn_mirrors = [
        "https://mirrors.tuna.tsinghua.edu.cn/archlinuxcn",
        "https://mirrors.ustc.edu.cn/archlinuxcn",
        "https://mirror.sjtu.edu.cn/archlinux-cn",
        "https://mirror.nju.edu.cn/archlinuxcn",
    ]
    github_link = random.choice(github_mirrors) if use_mirrors else "https://github.com"
    archlinuxcn_link = (
        random.choice(archlinuxcn_mirrors)
        if use_mirrors
        else "https://repo.archlinuxcn.org"
    )

    # 设置临时文件夹为当前目录
    tmp_dir = os.path.abspath("./")

    # 下载临时文件
    _download_tmp(tmp_dir)

    # 设置词库
    fcitx5_dicts_dict = {
        "zhwiki": _get_zhwiki_url(tmp_dir),
        "moegirl": _get_moegirl_url(tmp_dir),
        "cedict": "%s/cathaysia/fcitx5_dicts/releases/download/0.0.1/cedict.dict"
        % github_link,
        "chinese-frequency-word-list": "%s/cathaysia/fcitx5_dicts/releases/download/v0.0.2/chinese-frequency-word-list.dict"
        % github_link,
    }

    Fcitx5DictUpdater(fcitx5_dicts_dict).download_dicts()
