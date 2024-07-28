import re

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
        except ValueError as e:
            return str(e)
        except StopIteration as e:
            print("=" * 100)
            return e.value


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
            CollectionField("arg2", (1, 2, 3, 3.14)),
            FloatField("arg3"),
            CustomField("arg4", {c.name: c for c in [a, b, c, d, e, f]}),
            JSONStringField("arg5", True),
        ],
        0,
        func,
    )
    cmd_add = Command("add", "add command", [IntegerField("arg1"), IntegerField("arg2")], 0, lambda a, b: a + b)
    cmdparser.register_command(0, cmd_test, cmd_add)
    assert run(cmdparser.parse_command("help")) == 1
    assert run(cmdparser.parse_command("help test")) == 1
    assert run(cmdparser.parse_command('test hi 3 -3 c_a {"a":[0,1],"b":[2,3]}', extra_key1="value1", extra_key2=-1)) == 1
    assert run(cmdparser.parse_command('test "hello world" 3 3.14 @["c_a","c_c","c_c"] {"a": [0, 1], "b": [2, 3]}', extra_key1="value1", extra_key2=-1)) == 2
    assert run(cmdparser.parse_command('test hi 3 3.14 @["@{\\"score\\":[\\"=80\\"]}","@{\\"score\\":[\\"<65\\"],\\"gender\\":\\"f\\"}","@{\\"score\\":[\\"<=64\\"],\\"gender\\":\\"m\\"}"]')) == 2
    assert run(cmdparser.parse_command('test \'\' 3 3.14 @{"score":[">100"],"gender":"f"}')) == 0
    assert run(cmdparser.parse_command('test "" 3.6 3.14 c_f')) == 0
    assert run(cmdparser.parse_command('test \'a b c d\' 3.* 3.14 @{"score":["!=80","<90"],"gender":"f"} {"a": [0, 1], "b": [2, 3]}')) == 4
    assert run(cmdparser.parse_command("help test test2")) == "unknown command 'test test2'"
    cmdparser.MAX_SIM_EXEC = 1
    with pytest.raises(CommandError, match=re.escape("failed to parse 'test \"\" 3.6 3.14 c_9': 'c_9' outside of the scope 'arg4'")):
        run(cmdparser.parse_command('test "" 3.6 3.14 c_9'))
    with pytest.raises(CommandError, match=re.escape('failed to parse \'test \\\'a b c d\\\' 3 3.14 @{"score":["!=80"],"gender":"f"} {"a": [0, 1], "b": [2, 3]}\': too many possible simultaneous executions: 3 > 1')):
        run(cmdparser.parse_command('test \'a b c d\' 3 3.14 @{"score":["!=80"],"gender":"f"} {"a": [0, 1], "b": [2, 3]}'))
    cmdparser.MAX_SIM_EXEC = 127
    with pytest.raises(CommandError, match=re.escape('failed to parse \'test hi 3 3.14 @[@{"score":["=80"]},@{"score":["<65"]}]\': \'[@{"score":["=80"]},@{"score":["<65"]}]\' is not a valid selector')):
        run(cmdparser.parse_command('test hi 3 3.14 @[@{"score":["=80"]},@{"score":["<65"]}]'))
    with pytest.raises(CommandError, match=re.escape("failed to parse 'test hi 3 3.14': command 'test' expected 4 positional argument(s), 3 given")):
        run(cmdparser.parse_command("test hi 3 3.14"))
    with pytest.raises(CommandError, match=re.escape("failed to parse 'add 1 2 3': command 'add' expected 2 positional argument(s), 3 given")):
        run(cmdparser.parse_command("add 1 2 3"))
