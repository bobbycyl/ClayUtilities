import os

from clayutil.futil import Downloader


def test():
    proxies = {"http": "http://127.0.0.1:2334", "https": "http://127.0.0.1:2334"}
    mirrors = {
        "https://repo.archlinuxcn.org/": ["https://mirrors.tuna.tsinghua.edu.cn/archlinuxcn/", "https://mirrors.ustc.edu.cn/archlinuxcn/"],
        "https://github.com/ventoy/Ventoy/releases/download/": ["https://null/"],
    }
    d = Downloader("./", mirrors)

    path = d.start("https://repo.archlinuxcn.org/lastupdate", "ArchLinuxCN_lastupdate", proxies=proxies)
    print(d.url, d.filename, path)
    assert d.filename == os.path.join("./", "ArchLinuxCN_lastupdate")
    path = d.start("https://repo.archlinuxcn.org/lastupdate", "ArchLinuxCN_lastupdate", check_duplicate=True, proxies=proxies)
    print(d.url, d.filename, path)
    assert d.filename == os.path.join("./", "ArchLinuxCN_lastupdate (1)")

    path = d.start("https://github.com/ventoy/Ventoy/releases/download/v1.0.97/sha256.txt", "Ventoy_v1.0.97.sha256", proxies=proxies)
    print(d.url, d.filename, path)
    assert d.filename == os.path.join("./", "Ventoy_v1.0.97.sha256")
    path = d.start("https://github.com/ventoy/Ventoy/releases/download/v1.0.97/sha256.txt", "Ventoy_v1.0.97.sha256", check_duplicate=True, proxies=proxies)
    print(d.url, d.filename, path)
    assert d.filename == os.path.join("./", "Ventoy_v1.0.97 (1).sha256")

    d.start("https://dl.sayobot.cn/beatmaps/download/full/517474")
    assert d.filename == os.path.join("./", "517474 Camellia - Exit This Earth's Atomosphere.osz")


def teardown_module():
    for filename in ["./ArchLinuxCN_lastupdate", "./ArchLinuxCN_lastupdate (1)", "./Ventoy_v1.0.97.sha256", "./Ventoy_v1.0.97 (1).sha256", "517474 Camellia - Exit This Earth's Atomosphere.osz"]:
        try:
            os.remove(filename)
        except FileNotFoundError:
            pass
