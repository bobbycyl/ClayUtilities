__all__ = ("Properties", "GetQueryDownloader")

import os
import re
import shutil
from collections import OrderedDict
from datetime import datetime
from typing import Optional

import requests


class Properties(object):
    """一个宽松的单行键值对文件工具类"""

    def __init__(self, filename, encoding="utf-8"):
        self.__filename = filename
        self.__encoding = encoding
        self.properties = OrderedDict()  # 键值对内容，按行的顺序存储
        if not os.path.exists(filename):
            with open(filename, "w") as f:
                f.write("# %s\n" % datetime.ctime(datetime.now()))
        self.parse()

    def parse(self):
        with open(self.__filename, "r", encoding=self.__encoding) as pf:
            for i, line in enumerate(pf):
                m = re.match(r"^([^#]+)=(.+)\n$", line)  # 符合“key=value”样式的键值对
                if m is None:
                    self.properties["#%i" % i] = line  # 不符合即视为注释
                else:
                    v = m.group(2)
                    if v.isdigit():
                        v = int(v)
                    elif v == "true":
                        v = True
                    elif v == "false":
                        v = False
                    self.properties[m.group(1)] = v

    def override(self):
        with open(self.__filename, "w", encoding=self.__encoding) as pf:
            for key, value in self.properties.items():
                if key[0] == "#" and key[1:].isdigit():
                    pf.write("%s" % value)
                else:
                    if str(value) == "True":
                        value = "true"
                    elif str(value) == "False":
                        value = "false"
                    else:
                        value = str(value)
                    pf.write("%s=%s\n" % (key, value))


class GetQueryDownloader(object):
    """Get请求下载器

    发送一个Get请求，可以指定headers，允许重定向，
    将目标文本文件或二进制文件保存到指定本地文件。

    Attributes:
        content_length: 返回内容的大小
        content_type: 返回内容的MIME类型
    """

    def __init__(self, output_dir: str):
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)
        self.__output_dir = output_dir
        self.__url = ""
        self.content_length = 0
        self.content_type = ""
        self.__filename = ""

    def start(
        self,
        url: str,
        filename: str = "",
        headers: Optional[dict] = None,
    ) -> str:
        """发起Get请求与下载文件

        将目标文件复制到指定保存目录中，若filename参数不为空，则进行重命名。
        重命名规则：
        1. 若filename参数为空，则由目标文件的文件名命名本地文件
        2. 若filename不包含扩展名，则使用目标文件的扩展名
        3. 若filename包含扩展名，则使用指定的扩展名

        :param url: 欲发送Get请求的URL地址
        :param filename: 本地文件名，留空则自动获取
        :param headers: 指定的HTTP Headers，留空则使用默认值
        :return: 下载完成的本地文件名的绝对路径
        """
        # 设置HTTP Headers
        if headers is None:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36"
            }

        # 对目标文件地址发起Get请求
        r = requests.get(url, headers=headers, stream=True, allow_redirects=True)
        self.__url = r.url
        self.content_length = int(str(r.headers.get("Content-Length")))
        self.content_type = str(r.headers.get("Content-Type"))
        self.__filename = os.path.join(self.__output_dir, self.__url.split("/")[-1])

        # 如果给定文件名则进行重命名
        if filename:
            self.__rename(filename)

        # 开始下载
        if str(self.content_type)[:4] == "text":  # 响应的内容是文本内容
            r.encoding = r.apparent_encoding
            with open(self.__filename, "w") as f:
                f.write(r.text)
        else:
            with open(self.__filename, "wb") as fb:  # 响应的内容是二进制内容
                shutil.copyfileobj(r.raw, fb)
        return os.path.abspath(self.__filename)

    def __rename(self, new_filename: str):
        """重命名下载的文件

        如果新文件名含有扩展名，则使用指定的扩展名，否则保留原扩展名

        :param new_filename: 用于重命名的新文件名
        """
        if os.path.splitext(new_filename)[1] == "":
            self.__filename = os.path.join(
                self.__output_dir,
                "%s%s" % (new_filename, os.path.splitext(self.__filename)[1]),
            )
        else:
            self.__filename = os.path.join(self.__output_dir, new_filename)
