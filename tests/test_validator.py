import pytest

from clayutil import validator


class Component(object):
    name = validator.String(3, 15, str.isascii, False)
    gender = validator.OneOf("f", "m", "o")
    score = validator.Integer(0, 100, True)

    def __init__(self, mid, gender, score=None):
        self.name = mid
        self.gender = gender
        self.score = score

    def __str__(self):
        return f"{self.__class__.__name__}({self.name}, {self.gender}, {self.score})"

    __repr__ = __str__


def test():
    c = Component(
        "john.doe",
        "f",
        80,
    )
    assert validator.validate_not_none("") == ""
    assert validator.validate_type("hi", str, 1, 3) == "hi"
    assert validator.validate_type(-3.14, float, -5, 0) == -3.14
    assert validator.validate_type(100, int, 0, 100) == 100
    assert Component("john.doe", "m")
    assert validator.validate_and_decode_json_string('{"a": [1, 2], "b": [3, 4]}') == {
        "a": [1, 2],
        "b": [3, 4],
    }


def test_exception():
    with pytest.raises(validator.ValidationError, match="expected length of 'hi' to be at least 3"):
        validator.validate_type("hi", str, 3, 15)
    with pytest.raises(validator.ValidationError, match="expected '-1' to be of <class 'int'>"):
        validator.validate_type("-1", int, 0, 100)
    with pytest.raises(validator.ValidationError, match="expected -1 to be at least 0"):
        Component("john.doe", "m", -1)
    with pytest.raises(validator.ValidationError, match="expected 101 to be no more than 100"):
        Component("john.doe", "m", 101)
    with pytest.raises(
        validator.ValidationError,
        match="expected None to be of <class 'str'>",
    ):
        Component(None, "f")
    with pytest.raises(validator.ValidationError, match="expected 'x' to be one of {'f', 'm', 'o'}"):
        Component("john.doe", "x", 60)
    with pytest.raises(validator.ValidationError, match="'invalid' is not of type 'number'"):
        schema = {
            "properties": {"name": {"type": "string"}, "price": {"type": "number"}},
            "type": "object",
        }
        validator.validate_and_decode_json_string('{"name" : "Eggs", "price" : "invalid"}', schema)
