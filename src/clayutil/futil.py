import asyncio
import cgi
import functools
import os
import re
import shutil
import zipfile
from collections import OrderedDict
from datetime import datetime
from time import sleep
from typing import Optional, Union
from urllib import parse

import aiohttp
import requests

__all__ = (
    "check_duplicate_filename",
    "compress_as_zip",
    "PropertiesValueError",
    "Properties",
    "Downloader",
    "filelock",
)


def check_duplicate_filename(filename: str, pattern_string: str = r" \({n}\)") -> str:
    pattern = re.compile(r"(.*%s)" % pattern_string.replace("{n}", r")(\d+)("))
    if os.path.exists(filename):
        splitext_filename = os.path.splitext(filename)
        m = pattern.match(splitext_filename[0])
        if m:
            filename = "%s%s" % (pattern.sub(lambda m: "%s%d%s" % (m.group(1), int(m.group(2)) + 1, m.group(3)), splitext_filename[0]), splitext_filename[1])
        else:
            filename = "%s%s%s" % (splitext_filename[0], pattern_string.replace("\\", "").format(n=1), splitext_filename[1])
        return check_duplicate_filename(filename)
    return filename


def compress_as_zip(path: str, zip_filename: str) -> None:
    with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(path):
            relpath = os.path.relpath(root, path)
            for filename in files:
                zipf.write(os.path.join(root, filename), os.path.join(relpath, filename))


class PropertiesValueError(ValueError):
    pass


PropertiesOrderedDict = OrderedDict[str, Union[int, bool, str]]


class Properties(PropertiesOrderedDict):
    """
    A tool for parsing and writing properties files.

    a line matches "key=value" will be parsed as a key-value pair,
    while a line starts with "#" will be parsed as a comment.
    """

    pattern = re.compile(r"^([^#]+?)=(.+)\n$")

    def __init__(self, filename: str, encoding: str = "utf-8"):
        super().__init__()
        self.filename: str = filename
        self.encoding: str = encoding
        if not os.path.exists(self.filename):
            with open(self.filename, "w", encoding=self.encoding) as pf:
                pf.write("# %s\n" % datetime.ctime(datetime.now()))

    def load(self):
        with open(self.filename, "r", encoding=self.encoding) as pf:
            for i, line in enumerate(pf, 1):
                m = self.pattern.match(line)
                if m is None:
                    if line[0] != "#":
                        continue
                    self.__setitem__("#%i" % i, line)
                else:
                    v: Union[int, bool, str]
                    if m.group(2).isdigit():
                        v = int(m.group(2))
                    elif m.group(2) == "true":
                        v = True
                    elif m.group(2) == "false":
                        v = False
                    else:
                        v = m.group(2)
                    self.__setitem__(m.group(1), v)

    def dump(self):
        with open(self.filename, "w", encoding=self.encoding) as pf:
            for key, value in self.items():
                if key[0] == "#":
                    pf.write("%s" % value)
                else:
                    if isinstance(value, bool):
                        if value:
                            value = "true"
                        else:
                            value = "false"
                    pf.write("%s=%s\n" % (key, value))


class Downloader(object):
    """
    A tool for downloading files from the Internet.

    It will send a GET request to a specified URL,
    and save the response content to a local file.

    It features mirror list support.
    """

    LEGACY_CHROME_UA = "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36"
    CHROME_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36"

    def __init__(self, output_dir: str, mirrors: Optional[dict[str, list[str]]] = None):
        """
        Initialize the Downloader object.

        :param output_dir: The directory where the downloaded files will be saved.
        :param mirrors: {old_string: [new_string]}
        """

        os.makedirs(output_dir, exist_ok=True)
        self.__output_dir: str = output_dir
        self.mirrors: dict[str, list[str]] = mirrors if mirrors is not None else {}
        self.history: list[tuple[str, str, int, str]] = []  # url, filename, content_length, content_type

    def start(self, url: str, filename: str = "", headers: Optional[dict] = None, check_duplicate: bool = False, proxies: Optional[dict] = None) -> str:
        """
        Copy the target file to the output directory, and rename it if the filename argument is not None.

        When a mirror is used, proxies will be omitted.

        Renaming rules:
            1. If the filename argument is empty, use the filename according to the url.
            2. If the filename argument does not contain an extension, use the extension from the url.
            3. If the filename argument contains an extension, use the specified extension.

        :param url: the URL of the target file
        :param filename: the name of the local file
        :param headers: HTTP headers to send with the request
        :param check_duplicate: whether to check for duplicate filenames and rename if necessary
        :param proxies: the proxies to use for the request
        :return: the absolute path of the downloaded local file
        """

        if headers is None:
            headers = {"User-Agent": self.CHROME_UA}

        for old_url, new_urls in self.mirrors.items():
            if old_url in url:
                for new_url in new_urls:
                    test_url = url.replace(old_url, new_url)
                    try:
                        test_r = requests.get(test_url, headers=headers, stream=True, allow_redirects=True)
                    except requests.RequestException:
                        continue
                    if test_r.status_code == 200:
                        proxies = None
                        url = test_url
                        break
                break

        with requests.get(url, headers=headers, stream=True, allow_redirects=True, proxies=proxies if proxies is not None else {}) as r:
            try:
                processed_filename = os.path.join(self.__output_dir, parse.unquote(cgi.parse_header(r.headers["content-disposition"])[1]["filename*"]).lstrip("utf-8''"))
            except KeyError:
                processed_filename = os.path.join(self.__output_dir, os.path.split(r.url)[1].split("?", 1)[0])

            if filename:
                processed_filename = self.__rename(processed_filename, filename)

            if check_duplicate:
                processed_filename = check_duplicate_filename(processed_filename)

            content_type = str(r.headers.get("Content-Type"))
            if content_type[:5] == "text/":
                r.encoding = r.apparent_encoding
                with open(processed_filename, "w", encoding=r.encoding) as f:
                    f.write(r.text)
            else:
                with open(processed_filename, "wb") as fb:
                    shutil.copyfileobj(r.raw, fb)

            self.history.append((r.url, processed_filename, int(str(r.headers.get("Content-Length", 0))), content_type))
        return os.path.abspath(processed_filename)

    async def async_start(self, url: str, filename: str = "", headers: Optional[dict] = None) -> str:
        """

        similar to start() but using asyncio

        :param url: the URL of the target file
        :param filename: the name of the local file
        :param headers: HTTP headers to send with the request
        :return: the absolute path of the downloaded local file
        """
        if headers is None:
            headers = {"User-Agent": self.CHROME_UA}

        for old_url, new_urls in self.mirrors.items():
            if old_url in url:
                for new_url in new_urls:
                    test_url = url.replace(old_url, new_url)
                    try:
                        async with aiohttp.ClientSession(trust_env=True) as session:
                            async with session.get(url, headers=headers, allow_redirects=True) as resp:
                                code = resp.status
                    except aiohttp.ClientError:
                        continue
                    if code == 200:
                        url = test_url
                        break
                break

        async with aiohttp.ClientSession(trust_env=True) as session:
            async with session.get(url, headers=headers, allow_redirects=True) as resp:
                content_length = int(str(resp.headers.get("Content-Length", 0)))
                content_type = str(resp.headers.get("Content-Type"))
                response_url = str(resp.url)
                try:
                    processed_filename = os.path.join(self.__output_dir, parse.unquote(cgi.parse_header(resp.headers["content-disposition"])[1]["filename*"]).lstrip("utf-8''"))
                except KeyError:
                    processed_filename = os.path.join(self.__output_dir, os.path.split(response_url)[1].split("?", 1)[0])

                async with asyncio.Lock():
                    if filename:
                        processed_filename = self.__rename(processed_filename, filename)

                    processed_filename = check_duplicate_filename(processed_filename)

                    with open(processed_filename, "wb") as fb:
                        async for chunk in resp.content.iter_chunked(1024):
                            fb.write(chunk)

        async with asyncio.Lock():
            self.history.append((response_url, processed_filename, content_length, content_type))
        return os.path.abspath(processed_filename)

    def __rename(self, old_filename: str, new_filename: str) -> str:
        if os.path.splitext(new_filename)[1] == "":
            renamed_filename = os.path.join(
                self.__output_dir,
                "%s%s" % (new_filename, os.path.splitext(old_filename)[1]),
            )
        else:
            renamed_filename = os.path.join(self.__output_dir, new_filename)
        return renamed_filename


def filelock(index):
    """simple file lock

    lock filename based on the specific argument of the function if exists else LCK
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if len(args) > 0:
                filename = "%s.LCK" % args[index]
            else:
                filename = "LCK"
            while os.path.exists(filename):
                sleep(1)
            with open(filename, "w"):
                pass
            try:
                return func(*args, **kwargs)
            finally:
                os.remove(filename)

        return wrapper

    return decorator
