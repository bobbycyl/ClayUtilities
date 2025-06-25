from clayutil.tutil import zh_prettifier


def test():
    s1 = "测试123test测试 test 123 测试"
    assert zh_prettifier(s1) == "测试 123test 测试 test 123 测试"
