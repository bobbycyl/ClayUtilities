import asyncio
import os
import time

import pytest

from clayutil.futil import Downloader
from clayutil.sutil import md5sum


@pytest.fixture
def clean_tmp_files():
    yield
    for filename in ["./ArchLinuxCN_lastupdate", "./ArchLinuxCN_lastupdate (1)", "./Ventoy_v1.0.97.sha256", "./Ventoy_v1.0.97 (1).sha256", "TRUE - Storyteller (IOException) [Expert].osu", "3477131.osu", "3477131"]:
        try:
            os.remove(filename)
        except FileNotFoundError:
            pass


def test(clean_tmp_files):
    proxies = {"http": "http://127.0.0.1:12334", "https": "http://127.0.0.1:12334"}
    mirrors = {
        "https://repo.archlinuxcn.org/": ["https://mirrors.tuna.tsinghua.edu.cn/archlinuxcn/", "https://mirrors.ustc.edu.cn/archlinuxcn/"],
        "https://github.com/ventoy/Ventoy/releases/download/": ["https://null/"],
    }
    d = Downloader("./", mirrors)

    d.start("https://repo.archlinuxcn.org/lastupdate", "ArchLinuxCN_lastupdate", proxies=proxies)
    downloaded = d.history.pop()
    print(downloaded)
    assert downloaded[1] == os.path.join("./", "ArchLinuxCN_lastupdate")
    d.start("https://repo.archlinuxcn.org/lastupdate", "ArchLinuxCN_lastupdate", check_duplicate=True, proxies=proxies)
    downloaded = d.history.pop()
    print(downloaded)
    assert downloaded[1] == os.path.join("./", "ArchLinuxCN_lastupdate (1)")

    d.start("https://github.com/ventoy/Ventoy/releases/download/v1.0.97/sha256.txt", "Ventoy_v1.0.97.sha256", proxies=proxies)
    downloaded = d.history.pop()
    print(downloaded)
    assert downloaded[1] == os.path.join("./", "Ventoy_v1.0.97.sha256")
    d.start("https://github.com/ventoy/Ventoy/releases/download/v1.0.97/sha256.txt", "Ventoy_v1.0.97.sha256", check_duplicate=True, proxies=proxies)
    downloaded = d.history.pop()
    print(downloaded)
    assert downloaded[1] == os.path.join("./", "Ventoy_v1.0.97 (1).sha256")

    d.start("https://osu.ppy.sh/osu/3477131")
    downloaded = d.history.pop()
    # 验证 md5
    with open(downloaded[1], "rb") as fi_b:
        assert md5sum(fi_b.read()) == "BD54DB0CFE5C44EF576D9DEC7D5C0F9F".lower()


async def async_test_main():
    mirrors = {
        "https://repo.archlinuxcn.org/": ["https://mirrors.tuna.tsinghua.edu.cn/archlinuxcn/", "https://mirrors.ustc.edu.cn/archlinuxcn/"],
        "https://github.com/ventoy/Ventoy/releases/download/": ["https://null/"],
    }
    d = Downloader("./", mirrors)
    async with asyncio.TaskGroup() as tg:
        tg.create_task(d.async_start("https://repo.archlinuxcn.org/lastupdate", "ArchLinuxCN_lastupdate"))
        tg.create_task(d.async_start("https://repo.archlinuxcn.org/lastupdate", "ArchLinuxCN_lastupdate"))
        tg.create_task(d.async_start("https://osu.ppy.sh/osu/3477131", "TRUE - Storyteller (IOException) [Expert].osu"))
    return d.history


def test_async(clean_tmp_files):
    time.sleep(2)
    history = asyncio.run(async_test_main())
    filenames = sorted([i[1] for i in history if "TRUE - Storyteller (IOException) [Expert]" not in i[1]])
    assert filenames == ["./ArchLinuxCN_lastupdate", "./ArchLinuxCN_lastupdate (1)"]
    # 验证 md5
    # 选中 filename
    for filename in history:
        if "TRUE - Storyteller (IOException) [Expert]" in filename[1]:
            with open(filename[1], "rb") as fi_b:
                assert md5sum(fi_b.read()) == "BD54DB0CFE5C44EF576D9DEC7D5C0F9F".lower()
