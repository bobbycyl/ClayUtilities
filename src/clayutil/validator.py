from abc import ABC, abstractmethod
from collections import Counter

import jsonschema
import ujson

__all__ = (
    "ValidationError",
    "Validator",
    "validate_not_none",
    "validate_range",
    "validate_type",
    "validate_and_decode_json_string",
    "Integer",
    "Float",
    "String",
    "Bool",
    "OneOf",
)


class ValidationError(ValueError):
    pass


class Validator(ABC):
    def __set_name__(self, owner, name):
        self.priv_name = "_" + name

    def __get__(self, instance, owner):
        return getattr(instance, self.priv_name)

    def __set__(self, instance, value):
        self.validate(value)
        setattr(instance, self.priv_name, value)

    @abstractmethod
    def validate(self, value):
        pass


def validate_not_none(value):
    if value is None:
        raise ValidationError(f"expected {value!r} to not be None")
    return value


def validate_range(value, min_value=None, max_value=None):
    if min_value is not None and value < min_value:
        raise ValidationError(f"expected {value!r} to be at least {min_value!r}")
    if max_value is not None and value > max_value:
        raise ValidationError(f"expected {value!r} to be no more than {max_value!r}")


def validate_length(value, min_value=None, max_value=None):
    if min_value is not None and len(value) < min_value:
        raise ValidationError(f"expected length of {value!r} to be at least {min_value!r}")
    if max_value is not None and len(value) > max_value:
        raise ValidationError(f"expected length of {value!r} to be no more than {max_value!r}")


def validate_type(value, type_, min_value=None, max_value=None, predicate=None):
    if not isinstance(value, type_):
        raise ValidationError(f"expected {value!r} to be of {type_!r}")

    if hasattr(type_, "__len__"):
        validate_length(value, min_value, max_value)
    else:
        validate_range(value, min_value, max_value)

    if predicate is not None and not predicate(value):
        raise ValidationError(f"expected {value!r} to match {predicate!r}")

    return value


def validate_and_decode_json_string(value, schema=None):
    try:
        obj = ujson.decode(value)
    except ValidationError as e:
        raise ValidationError(f"expected {value!r} to be a valid JSON string") from e
    except ujson.JSONDecodeError as e:
        raise ValidationError(f"expected {value!r} to be a valid JSON string") from e

    if schema is not None:
        try:
            jsonschema.validate(obj, schema)
        except jsonschema.ValidationError as e:
            raise ValidationError(e.message) from e

    return obj


class Integer(Validator):
    def __init__(self, min_value=None, max_value=None, allow_optional=False):
        self.min_value = min_value
        self.max_value = max_value
        self.allow_optional = allow_optional

    def validate(self, value):
        if not (value is None and self.allow_optional):
            validate_type(value, int, self.min_value, self.max_value)


class Float(Validator):
    def __init__(self, min_value=None, max_value=None, allow_optional=False):
        self.min_value = min_value
        self.max_value = max_value
        self.allow_optional = allow_optional

    def validate(self, value):
        if not (value is None and self.allow_optional):
            validate_type(value, float, self.min_value, self.max_value)


class String(Validator):
    def __init__(self, min_value=None, max_value=None, predicate=None, allow_optional=False):
        self.min_value = min_value
        self.max_value = max_value
        self.predicate = predicate
        self.allow_optional = allow_optional

    def validate(self, value):
        if not (value is None and self.allow_optional):
            validate_type(value, str, self.min_value, self.max_value, self.predicate)


class Bool(Validator):
    def validate(self, value):
        validate_type(value, bool)


class OneOf(Validator):
    def __init__(self, *options):
        self.options = Counter(options)

    def validate(self, value):
        if value not in self.options:
            raise ValidationError(f"expected {value!r} to be one of {'{' + ', '.join(f'{o!r}' for o in self.options.keys()) + '}'}")
