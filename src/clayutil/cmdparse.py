import re
import shlex
import sys
from abc import ABC, abstractmethod
from collections import UserDict
from collections.abc import Callable, Collection, Generator, Mapping
from itertools import chain, product
from typing import Any, Generic, Optional, TypeVar

import orjson

from .validator import Bool, Integer, String, validate_and_decode_json_string

__all__ = (
    "CommandError",
    "Field",
    "IntegerField",
    "FloatField",
    "BoolField",
    "StringField",
    "JSONStringField",
    "CollectionField",
    "parse_conditions",
    "CustomField",
    "Command",
    "CommandParser",
)

ENV = ""
if "streamlit" in sys.modules:
    ENV = "MD"


class CommandError(Exception):
    pass


class Field(ABC):
    __slots__ = ("_param", "_optional")
    param = String(predicate=str.isidentifier)
    optional = Bool()

    def __init__(self, param: str, optional: bool = False):
        self.param = param
        self.optional = optional

    @abstractmethod
    def parse_arg(self, arg: str, *args, **kwargs) -> Collection:
        raise NotImplementedError

    def __str__(self):
        if ENV == "MD":
            return f"[*{self.__class__.__name__}*: {self.param}]" if self.optional else f"<*{self.__class__.__name__}*: {self.param}>"
        else:
            return f"[{self.__class__.__name__}: {self.param}]" if self.optional else f"<{self.__class__.__name__}: {self.param}>"

    __repr__ = __str__


class IntegerField(Field):
    def __init__(self, param: str, optional: bool = False):
        """整型参数

        :param param: 参数名
        :param optional: 是否可选参数
        """
        super().__init__(param, optional)

    def parse_arg(self, arg: str, *args, **kwargs) -> tuple[int]:
        try:
            return (int(arg),)
        except Exception:
            raise ValueError(f"{arg!r} must be an integer")


class FloatField(Field):
    def __init__(self, param: str, optional: bool = False):
        """浮点型参数

        :param param: 参数名
        :param optional: 是否可选参数
        """
        super().__init__(param, optional)

    def parse_arg(self, arg: str, *args, **kwargs) -> tuple[float]:
        try:
            return (float(arg),)
        except Exception:
            raise ValueError(f"{arg!r} must be a float")


class BoolField(Field):
    def __init__(self, param: str, optional: bool = False):
        """布尔型参数

        只有 true 和 false 会被接受

        :param param: 参数名
        :param optional: 是否可选参数
        """
        super().__init__(param, optional)

    def parse_arg(self, arg: str, *args, **kwargs) -> tuple[bool]:
        if arg == "true":
            return (True,)
        elif arg == "false":
            return (False,)
        else:
            raise ValueError(f'{arg!r} must be "true" or "false"')


class StringField(Field):
    def __init__(self, param: str, optional: bool = False):
        """布尔型参数

        会自动删除首尾的英文双引号

        :param param: 参数名
        :param optional: 是否可选参数
        """
        super().__init__(param, optional)

    def parse_arg(self, arg: str, *args, **kwargs) -> tuple[str]:
        return (arg.strip('"'),)


class JSONStringField(Field):
    schema = None

    def __init__(self, param: str, optional: bool = False):
        """JSON 型参数

        强烈建议仅作为末尾参数使用，因为解析命令时末尾参数的自动合并功能可以解决 JSON 字符串中的空格问题

        :param param: 参数名
        :param optional: 是否可选参数
        """
        super().__init__(param, optional)

    def parse_arg(self, arg, *args, **kwargs) -> tuple:
        return (validate_and_decode_json_string(arg, self.schema),)


_T = TypeVar("_T", bound=Any)


class CollectionField(Generic[_T], Field):
    __slots__ = ("_param", "__scope", "_optional")
    __scope: Collection[_T]

    def __init__(self, param: str, scope: Collection[_T], optional: bool = False):
        """集合型参数

        :param param: 参数名
        :param scope: 用于正则匹配的域
        :param optional: 是否可选参数
        """
        super().__init__(param, optional)
        self.__scope = scope

    def parse_arg(self, arg: str, *args, **kwargs) -> tuple[_T, ...]:
        return tuple(filter(lambda x: re.match(f"^{arg}$", str(x)), self.__scope))

    def __str__(self):
        return f"[{self.param}{{.*}}]" if self.optional else f"<{self.param}{{.*}}>"

    __repr__ = __str__


def parse_conditions(value, conditions: list[str]) -> bool:
    it = []
    for cond in conditions:
        try:
            op = cond[0]
            if cond[1] == "=":
                value2 = cond[3:-1] if cond[2] == '"' and cond[-1] == '"' else float(cond[2:])
                match op:
                    case "!":
                        it.append(value != value2)
                    case ">":
                        it.append(value >= value2)
                    case "<":
                        it.append(value <= value2)
                    case _:
                        raise ValueError("invalid operator '%s='" % op)
            else:
                value2 = cond[2:-1] if cond[1] == '"' and cond[-1] == '"' else float(cond[1:])
                match op:
                    case ">":
                        it.append(value > value2)
                    case "<":
                        it.append(value < value2)
                    case "=":
                        it.append(value == value2)
                    case _:
                        raise ValueError("invalid operator '%s'" % op)
        except ValueError as e:
            raise ValueError(f"invalid condition {cond!r}")
    return all(it)


class CustomField(Generic[_T], Field):
    MAX_NEST = 2
    __slots__ = ("_param", "__scope", "_optional")
    __scope: Callable[[], Mapping[str, _T]] | Mapping[str, _T]

    def __init__(self, param: str, scope: Callable[[], Mapping[str, _T]] | Mapping[str, _T], optional: bool = False):
        """自定义类型参数

        :param param: 参数名
        :param scope: 用于条件匹配的域
        :param optional: 是否可选参数
        """
        super().__init__(param, optional)
        self.__scope = scope

    def parse_arg(self, arg: str, nested: int = 0, *args, **kwargs) -> tuple[_T, ...] | set[_T]:
        try:
            if arg[0] == "@":  # selector
                selector = orjson.loads(arg[1:])
                return self.select(selector, nested, *args, **kwargs)
            else:
                return (self.__scope(*args, **kwargs)[arg],) if hasattr(self.__scope, "__call__") else (self.__scope[arg],)
        except orjson.JSONDecodeError as e:
            raise ValueError(f"{arg[1:]!r} is not a valid selector")
        except KeyError as e:
            raise ValueError(f"{arg!r} outside of the scope {self.param!r}")
        except AttributeError as e:
            raise ValueError(f"{self.param!r} has no attribute {arg!r}")
        except ValueError:
            raise

    def select(self, selector, nested: int, *args, **kwargs) -> tuple[_T, ...] | set[_T]:
        if nested > self.MAX_NEST:
            raise ValueError("too many nested selectors")
        if isinstance(selector, dict):  # &
            return tuple(
                filter(
                    lambda x: all([parse_conditions(getattr(x, k), v) if isinstance(v, list) else getattr(x, k) == v for k, v in selector.items() if k[0] != "_"]),
                    self.__scope(*args, **kwargs).values() if hasattr(self.__scope, "__call__") else self.__scope.values(),
                ),
            )
        elif isinstance(selector, list):  # |
            return set(chain.from_iterable(self.parse_arg(arg, nested + 1) for arg in selector))
        else:
            raise ValueError(f"{selector!r} is not a valid selector")

    def __str__(self):
        return f"[@{self.param}]" if self.optional else f"<@{self.param}>"

    __repr__ = __str__


class Command(object):
    __slots__ = ("_name", "_description", "params", "_permission", "func", "info")
    name = String(predicate=str.isidentifier)
    description = String()
    params: list[Field]
    permission = Integer()
    func: Callable

    def __init__(self, name: str, description: str, params: list[Field], permission: int, func: Callable):
        """
        Create a command

        :param name: command name, should be a valid identifier
        :param description: command description
        :param params: command parameters, should be a list of Field
        :param permission: command permission level, users cannot use a command with a permission level higher than their own
        :param func: the function to be called when the command is executed
        """

        self.name = name
        self.description = description
        positional_params_len = 0
        optional_params_len = 0
        usage = name
        for param in params:
            if param.optional:
                optional_params_len += 1
            else:
                if optional_params_len > 0:
                    raise ValueError(f"cannot create command {name!r}: positional parameter {param!r} follows optional parameter")
                positional_params_len += 1
            usage += " %s" % param
        self.info = (positional_params_len, positional_params_len + optional_params_len, usage)
        self.params = params
        self.permission = permission
        self.func = func

    def __str__(self):
        return "%s  \n%s" % (self.description, self.info[2])

    __repr__ = __str__


class CommandParser(UserDict):
    MAX_SIM_EXEC = 127
    data: dict[str, Command]

    def __init__(self):
        super().__init__()
        self.register_command(
            0,
            Command(
                "help",
                "show the help page",
                [StringField("command_name", True)],
                0,
                self.help,
            ),
        )

    def register_command(self, permission: int, *commands: Command) -> int:
        counter = 0
        for command in commands:
            if command.permission <= permission:
                self.data[command.name] = command
            counter += 1
        return counter

    def parse_command(self, command_text: str, **kwargs) -> Generator[Any, Any, int]:
        recognized_command_name, *recognized_command_args = shlex.split(command_text, posix=False)
        if recognized_command_name not in self.data:
            raise CommandError(f"unknown command {recognized_command_name!r}")
        recognized_command = self.data[recognized_command_name]

        exec_counter = 0
        parsed_args = []
        try:
            min_len, max_len, _ = recognized_command.info
            recognized_command_args_len = len(recognized_command_args)
            if not recognized_command_args_len == min_len == 0:
                if recognized_command_args_len < min_len:
                    raise ValueError(f"command {recognized_command.name!r} expected {min_len} positional argument(s), {recognized_command_args_len} given")
                if recognized_command_args_len > max_len:
                    if min_len == max_len:  # no positional argument
                        raise ValueError(f"command {recognized_command.name!r} expected {min_len} positional argument(s), {recognized_command_args_len} given")
                    # auto merge
                    cut = max_len - 1
                    merged_command_args = recognized_command_args[:cut]
                    merged_command_args.append(" ".join(recognized_command_args[cut:]))
                    recognized_command_args = merged_command_args
                    recognized_command_args_len = max_len
                sim_exec_projection = 1
                for i in range(recognized_command_args_len):
                    # the basic command parser does not support *args and **kwargs for the argument parser
                    parsed_arg = recognized_command.params[i].parse_arg(recognized_command_args[i])
                    parsed_args.append(parsed_arg)
                    sim_exec_projection *= len(parsed_arg)
                    if sim_exec_projection > self.MAX_SIM_EXEC:
                        raise ValueError(f"too many possible simultaneous executions: {sim_exec_projection} > {self.MAX_SIM_EXEC}")
        except ValueError as e:
            raise CommandError(f"failed to parse {command_text!r}: {e}")
        except Exception as e:
            raise CommandError(f"failed to parse {command_text!r}") from e
        for args in product(*parsed_args):
            if hasattr(recognized_command.func, "__func__") and hasattr(recognized_command.func, "__self__"):  # method
                yield recognized_command.func.__func__(recognized_command.func.__self__, *args, **kwargs)
            else:
                yield recognized_command.func(*args, **kwargs)
            exec_counter += 1
        return exec_counter

    def help(self, command_name: Optional[str] = None) -> str:
        if command_name is None:
            if ENV == "MD":
                return 'use "help *command_name*" to show the help page of a command\n\n%s' % "  \n".join(f"**{command.name}** - {command.description}" for command in self.data.values())
            else:
                return 'use "help command_name" to show the help page of a command\n%s' % "\n".join(f"{command.name} - {command.description}" for command in self.data.values())
        else:
            if command_name not in self.data:
                raise ValueError(f"unknown command {command_name!r}")
            return str(self.data[command_name])
