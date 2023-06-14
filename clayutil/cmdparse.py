__all__ = (
    "CommandParser",
    "AnyField",
    "StringField",
    "IntegerField",
    "FloatField",
    "JsonStringField",
)

import json
import re
from typing import Any, Dict, List


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
        """Convert the datetype of 'arg' to which the class defines

        May be overridden.

        """
        return arg

    def __str__(self):
        if self.default_value is not None:
            return "[%s: %s]" % (self.__class__.__name__, self.param)
        else:
            return "<%s: %s>" % (self.__class__.__name__, self.param)

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


class CommandParser(object):
    """拥有静态类型的命令解析工具"""

    pattern = re.compile(r"(?<!\\) ")  # 转义规则

    def __init__(self):
        self.__cmds: Dict[str, List[AnyField]] = {}  # {root_cmd: params}

    def add_command(self, root_cmd: str, *params: AnyField):
        """添加一条命令模板

        根命令不可重复，命令形参列表需要使用静态命令参数数据类型

        :param root_cmd: 根命令
        :param params: 命令形参列表
        """
        if root_cmd in self.__cmds:
            raise ValueError("command '%s' already exists" % root_cmd)
        optional_counter = 0
        for param in params:
            if param.default_value is not None:
                optional_counter += 1
            else:
                if optional_counter > 0:
                    raise ArgTypeError("optional parameter follows required parameter")
        self.__cmds[root_cmd] = list(params)

    def parse_command(self, cmd: str) -> Dict[str, Any]:
        """解析命令

        解析过程如下：
        1. 检查命令是否存在
        2. 检查命令实参个数是否与命令模板形参个数相等
        3. 检查命令实参类型是否正确

        :param cmd: 传入的实际命令
        :return: 实参字典
        """
        split_cmd = [x.replace(r"\ ", " ") for x in self.pattern.split(cmd.strip())]
        recognized_root_cmd = str(split_cmd[0])

        if recognized_root_cmd not in self.__cmds:
            raise ValueError("unknown command '%s'" % recognized_root_cmd)

        args = split_cmd[1:]
        initial_args_length = len(args)
        params = self.__cmds[recognized_root_cmd]
        params_length = len(params)

        if initial_args_length > params_length:
            raise ValueError(
                "too many arguments given: %s %s"
                % (
                    recognized_root_cmd,
                    " ".join([str(param) for param in params]),
                )
            )

        # 填充可选参数
        for i in range(params_length - initial_args_length):
            cur_param = params[initial_args_length + i]
            if cur_param.default_value is None:
                raise ValueError(
                    "too few arguments given: %s %s"
                    % (
                        recognized_root_cmd,
                        " ".join([str(param) for param in params]),
                    )
                )
            args.append(cur_param.default_value)

        return_dict = {"root_cmd": recognized_root_cmd}
        for i in range(len(args)):
            return_dict[params[i].param] = convert_arg_type(params[i], args[i])
        return return_dict

    def all(self):
        return self.__cmds.keys()

    def __getitem__(self, item):
        return self.__cmds[item]
