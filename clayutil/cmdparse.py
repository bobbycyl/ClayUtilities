__all__ = (
    "Command",
    "CommandParser",
    "AnyField",
    "ArgTypeError",
    "StringField",
    "IntegerField",
    "FloatField",
    "JsonStringField",
    "convert_arg_type",
)

import json
import re
from collections import namedtuple
from typing import Dict, List, Tuple


class AnyField(object):
    """静态命令参数数据类型

    Attributes:
        param: 命令形参名
        default_value: 若为可选参数，则指定默认值
    """

    __slots__ = ("param", "default_value")

    def __init__(self, param: str, default_value=None):
        self.param = param
        self.default_value = default_value

    def convert_type(self, arg):
        """Convert the datetype of 'arg' to which the class defines.

        May be overridden.

        """
        return arg

    def __str__(self):
        if self.default_value is None:
            return "<%s: %s>" % (self.__class__.__name__, self.param)
        else:
            return "[%s: %s]" % (self.__class__.__name__, self.param)

    __repr__ = __str__


class ArgTypeError(ValueError):
    pass


class StringField(AnyField):
    def convert_type(self, arg) -> str:
        try:
            return str(arg)
        except ValueError:
            raise ArgTypeError("Argument %s is not a String." % repr(arg))


class IntegerField(AnyField):
    def convert_type(self, arg) -> int:
        try:
            return int(arg)
        except ValueError:
            raise ArgTypeError("Argument %s is not an Integer." % repr(arg))


class FloatField(AnyField):
    def convert_type(self, arg) -> float:
        try:
            return float(arg)
        except ValueError:
            raise ArgTypeError("Argument %s is not a Float." % repr(arg))


class JsonStringField(StringField):
    def convert_type(self, arg):
        try:
            return json.loads(super(JsonStringField, self).convert_type(arg))
        except json.decoder.JSONDecodeError:
            raise ArgTypeError("Argument %s is not a JsonString." % repr(arg))


def convert_arg_type(param_type: AnyField, arg):
    return param_type.convert_type(arg)


class Command(object):
    def __init__(self, root: str, params: List[AnyField], description: str = ""):
        optional_counter = 0
        for param in params:
            if param.default_value is None:
                if optional_counter > 0:
                    raise ArgTypeError(
                        f"required parameter {param} follows optional parameter"
                    )
            else:
                optional_counter += 1

        self.__root = root
        self.params = params
        self.description = description

    @property
    def root(self):
        return self.__root

    def __str__(self):
        return "%s %s" % (self.root, " ".join([str(param) for param in self.params]))

    __repr__ = __str__


class CommandParser(object):
    """拥有静态类型的命令解析工具"""

    pattern = re.compile(r"(?<!\\) ")  # 转义规则

    cmds: Dict[str, Command]  # {root_cmd: Command}

    def __init__(self):
        self.cmds = {}

    def add_command(self, cmd: Command):
        """添加一条命令"""
        root_cmd = cmd.root
        if root_cmd in self.cmds:
            raise ValueError("command '%s' already exists" % root_cmd)
        self.cmds[root_cmd] = cmd

    def parse_command(self, cmd: str) -> Tuple[str, tuple]:
        """解析命令

        解析过程如下：
        1. 检查命令是否存在
        2. 检查命令实参个数是否与命令模板形参个数相等
        3. 检查命令实参类型是否正确

        :param cmd: 传入的实际命令
        :return: (root_cmd, args)
        """
        split_cmd = [x.replace(r"\ ", " ") for x in self.pattern.split(cmd.rstrip())]
        recognized_root_cmd = str(split_cmd[0])

        if recognized_root_cmd not in self.cmds:
            raise ValueError("unknown command '%s'" % recognized_root_cmd)

        args = split_cmd[1:]
        initial_args_length = len(args)
        recognized_cmd = self.cmds[recognized_root_cmd]
        params = recognized_cmd.params
        params_length = len(params)

        if initial_args_length > params_length:
            raise ValueError(f"too many arguments given: {recognized_cmd}")

        # 填充可选参数
        for i in range(params_length - initial_args_length):
            cur_param = params[initial_args_length + i]
            if cur_param.default_value is None:
                raise ValueError(f"too few arguments given: {recognized_cmd}")
            args.append(cur_param.default_value)

        Args = namedtuple("Args", [param.param for param in params])
        converted_args = [
            convert_arg_type(params[i], args[i]) for i in range(params_length)
        ]
        return recognized_root_cmd, Args._make(converted_args)

    def __getitem__(self, item):
        return self.cmds[item]


if __name__ == "__main__":

    class Example(object):
        example_cmdparser = CommandParser()
        for cmd in [
            Command("help", [StringField("command", "")], "show help"),
            Command("add", [IntegerField("a"), IntegerField("b")], "add two numbers"),
            Command("exit", [], "exit"),
        ]:
            example_cmdparser.add_command(cmd)

        def __init__(self):
            self.loop = True

        def main(self):
            while self.loop:
                try:
                    print(self.handle_command(input("> ")))
                except ArgTypeError as e:
                    print(e)
                except KeyError as e:
                    print("help: unknown command %s" % e)
                except ValueError as e:
                    print(e)

        def handle_command(self, cmd: str) -> str:
            root_cmd, args = self.example_cmdparser.parse_command(cmd)
            return eval("self._handle_command_%s" % root_cmd)(args)

        def _handle_command_help(self, args):
            if args.command == "":
                print("available commands:")
                return str([cmd.root for cmd in self.example_cmdparser.cmds.values()])
            else:
                return (
                    self.example_cmdparser[args.command].description
                    + "\n"
                    + str(self.example_cmdparser[args.command])
                )

        def _handle_command_add(self, args):
            return args.a.__add__(args.b)

        def _handle_command_exit(self, args):
            self.loop = False
            return "exit"

    # create instance

    example = Example()
    example.main()

    # > help
    # available commands:
    # ['help', 'add', 'exit']
    # > help add
    # add two numbers
    # add <IntegerField: a> <IntegerField: b>
    # > add 1 2
    # 3
    # > add 1
    # too few arguments given: add <IntegerField: a> <IntegerField: b>
    # > add 1.1 2
    # Argument '1.1' is not an Integer.
    # > exit 1
    # too many arguments given: exit
    # > exit
    # exit
