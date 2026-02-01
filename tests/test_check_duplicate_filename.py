from clayutil.futil import check_duplicate_filename


def test():
    assert check_duplicate_filename("./test.txt") == "./test (1).txt"
    assert check_duplicate_filename("./test (1).txt") == "./test (1).txt"
    assert check_duplicate_filename("./test (1) (1).txt") == "./test (1) (4).txt"
    assert check_duplicate_filename("./test (999).txt") == "./test (1000).txt"
    assert check_duplicate_filename("./test_5.test", r"_{n}") == "./test_6.test"
