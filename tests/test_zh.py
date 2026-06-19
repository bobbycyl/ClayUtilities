from clayutil.tutil import zh_clean_spaces, zh_prettifier


def test_prettifier():
    s1 = "\n测试123test测试 test 123 测试\n"
    assert zh_prettifier(s1) == "测试 123test 测试 test 123 测试"


def test_clean_spaces():
    samples = [
        "我是 一个 2 apple ， 一 《 二 》 。",
        "Hello world 。 你好\n世界 。\t你\t好\t abc .",
    ]
    sample_results = [
        "我是一个 2 apple，一《二》。",
        "Hello world。你好\n世界。你好\t abc .",
    ]

    for sample, sample_result in zip(samples, sample_results, strict=True):
        assert zh_clean_spaces(sample) == sample_result
