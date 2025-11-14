import os
import shutil

import pytest

from clayutil.futil import FolderMonitor


@pytest.fixture
def clean_tmp_files():
    shutil.rmtree("./tmp", ignore_errors=True)
    os.mkdir("./tmp")
    yield
    shutil.rmtree("./tmp")


def test(clean_tmp_files):
    monitor = FolderMonitor("./tmp")
    monitor.start()
    with open("./tmp/test.txt", "w") as f:
        f.write("test")
    monitor.stop()
