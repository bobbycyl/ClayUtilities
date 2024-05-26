import shlex
from abc import ABC, abstractmethod
from collections import UserDict
from collections.abc import Callable, Iterable, Mapping
from itertools import product
from typing import Any, Generator, Optional, Union

import ujson

from .validator import Bool, Integer, String, validate_and_decode_json_string

__all__ = (
    "CommandError",
    "Field",
    "IntegerField",
    "FloatField",
    "StringField",
    "JSONStringField",
    "parse_conditions",
    "CustomField",
    "Command",
    "CommandParser",
)


class CommandError(Exception):
    pass


MAX_EXECUTING_AT_A_TIME = 65535


class Field(ABC):
    __slots__ = ("_param", "_optional")
    param = String(predicate=str.isidentifier)
    optional = Bool()

    def __init__(self, param: str, optional: bool = False):
        self.param = param
        self.optional = optional

    @abstractmethod
    def parse_arg(self, arg: str) -> Iterable:
        pass

    def __str__(self):
        return f"[{self.__class__.__name__}: {self.param}]" if self.optional else f"<{self.__class__.__name__}: {self.param}>"

    __repr__ = __str__


class IntegerField(Field):
    def parse_arg(self, arg: str) -> tuple[int]:
        return (int(arg),)


class FloatField(Field):
    def parse_arg(self, arg: str) -> tuple[float]:
        return (float(arg),)


class StringField(Field):
    def parse_arg(self, arg: str) -> tuple[str]:
        return (arg.strip('"'),)


class JSONStringField(Field):
    schema = None

    def parse_arg(self, arg) -> tuple:
        return (validate_and_decode_json_string(arg, self.schema),)


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
            raise CommandError(f"invalid condition {cond!r}") from e
    return all(it)


class CustomField(Field):
    __slots__ = ("_param", "__scope", "_optional")
    __scope: Mapping

    def __init__(self, param: str, scope: Mapping, optional: bool = False):
        super().__init__(param, optional)
        self.__scope = scope

    def parse_arg(self, arg: str) -> Union[tuple, filter, Generator]:
        try:
            if arg[0] == "@":  # selector
                selector = ujson.loads(arg[1:])
                return self.select(selector)
            else:
                return (self.__scope[arg],)
        except ujson.JSONDecodeError as e:
            raise ValueError(f"{arg!r} is not a valid selector")
        except KeyError as e:
            raise ValueError(f"{arg!r} outside of the scope of {self.param!r}")
        except AttributeError as e:
            raise ValueError(f"{self.param!r} has no attribute {arg!r}")

    def select(self, selector):
        if isinstance(selector, dict):  # {attr: [cond]} or {attr: value}
            return filter(
                lambda x: all([parse_conditions(getattr(x, k), v) if isinstance(v, list) else getattr(x, k) == v for k, v in selector.items() if k[0] != "_"]),
                self.__scope.values(),
            )
        elif isinstance(selector, list):  # [value]
            return (self.parse_arg(arg)[0] for arg in selector)


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

        JSONStringField is recommended to put at the end of the params
        due to the automatic merging mechanism of the parsing process.

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
        return "%s\n%s" % (self.description, self.info[2])

    __repr__ = __str__


class CommandParser(UserDict):
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
                    # auto merge
                    cut = max_len - 1
                    tmp = recognized_command_args[:cut]
                    tmp.append("".join(recognized_command_args[cut:]))
                    recognized_command_args = tmp
                    recognized_command_args_len = max_len
                for i in range(recognized_command_args_len):
                    try:
                        parsed_arg = recognized_command.params[i].parse_arg(recognized_command_args[i])
                    except ValueError as e:
                        raise ValueError(f"could not parse {recognized_command_args[i]!r} as {recognized_command.params[i]!r}") from e
                    parsed_args.append(parsed_arg)
        except ValueError as e:
            raise CommandError(f"failed to parse {command_text!r}: {e}") from None
        for args in product(*parsed_args):
            if hasattr(recognized_command.func, "__func__") and hasattr(recognized_command.func, "__self__"):  # method
                yield recognized_command.func.__func__(recognized_command.func.__self__, *args, **kwargs)
            else:
                yield recognized_command.func(*args, **kwargs)
            exec_counter += 1
        return exec_counter

    def help(self, command_name: Optional[str] = None) -> str:
        if command_name is None:
            return "\n".join(f"{command.name} - {command.description}" for command in self.data.values())
        else:
            if command_name not in self.data:
                raise ValueError(f"unknown command {command_name!r}")
            return str(self.data[command_name])
