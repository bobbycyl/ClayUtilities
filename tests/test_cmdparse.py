import pytest

from clayutil.cmdparse import *
from test_validator import Component


def func(*args, **kwargs):
    return list(enumerate(args, start=1)), [f"{k!r:<} -> {v!r:<}" for k, v in kwargs.items()]


def run(g):
    while True:
        try:
            print(next(g))
        except CommandError:
            raise
        except ValueError:
            break
        except StopIteration as e:
            print(f"{e.value} done")
            break
    print("=" * 100)


def test():
    a = Component("c_a", "f", 65)
    b = Component("c_b", "f", 75)
    c = Component("c_c", "m", 80)
    d = Component("c_d", "m", 60)
    e = Component("c_e", "f", 90)
    f = Component("c_f", "m", 90)
    cmdparser = CommandParser()
    cmd_test = Command(
        "test",
        "test command",
        [
            StringField("arg1"),
            IntegerField("arg2"),
            FloatField("arg3"),
            CustomField("arg4", {c.name: c for c in [a, b, c, d, e, f]}),
            JSONStringField("arg5", True),
        ],
        0,
        func,
    )
    cmdparser.register_command(0, cmd_test)
    run(cmdparser.parse_command("help"))
    run(cmdparser.parse_command("help test"))
    run(cmdparser.parse_command('test hi 3 -3 c_a {"a":[0,1],"b":[2,3]}', extra_key1="value1", extra_key2=-1))
    run(cmdparser.parse_command('test "hello world" 3 3.14 @["c_a","c_c"] {"a": [0, 1], "b": [2, 3]}', extra_key1="value1", extra_key2=-1))
    run(cmdparser.parse_command('test \'a b c d\' 3 3.14 @{"score":["!=80"],"gender":"f"} {"a": [0, 1], "b": [2, 3]}'))
    with pytest.raises(CommandError):
        run(cmdparser.parse_command('test hi 3 3.14 @[@{"score":["=80"]},@{"score":["<65"]}]'))
        run(cmdparser.parse_command("test hi 3 3.14"))
        run(cmdparser.parse_command("help test test2"))
