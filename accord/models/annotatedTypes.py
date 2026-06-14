import pathlib
import typing

import pydantic
import pylinac


# Define a type for a validated path.

def ConvertToPath(value: typing.Any) -> pathlib.Path:
    """Convert a string to a Path object"""
    if isinstance(value, str):
        return pathlib.Path(value)
    return value

def ValidateAndResolvePath(path: pathlib.Path) -> pathlib.Path:
    """Validate the path and resolve it to an absolute path"""
    absolutePath = path.resolve()
    return absolutePath

AbsolutePath = typing.Annotated[
    pathlib.Path,
    pydantic.BeforeValidator(ConvertToPath),
    pydantic.AfterValidator(ValidateAndResolvePath)
]

## types for list -> tuple
def coerce_to_tuple(v: typing.Any) -> typing.Any:
    if isinstance(v, list):
        return tuple(v)
    return v

# 'press': (float, str)
PressTuple = typing.Annotated[
    tuple[float, str],
    pydantic.BeforeValidator(coerce_to_tuple)
]

Float2Tuple = typing.Annotated[
    tuple[float, float],
    pydantic.BeforeValidator(coerce_to_tuple)
]

Float3Tuple = typing.Annotated[
    tuple[float, float, float],
    pydantic.BeforeValidator(coerce_to_tuple)
]

## types for tuple -> list
def coerce_to_list(v: typing.Any) -> typing.Any:
    if isinstance(v, tuple):
        return list(v)
    return v

# type for notes to be list of strings
NotesList = typing.Annotated[
    list[str],
    pydantic.BeforeValidator(coerce_to_list)
]


# --- Validator for EPID protocols ---
def validate_pylinac_protocol(v: typing.Any) -> pylinac.Protocol:
    if isinstance(v, pylinac.Protocol):
        return v
    if isinstance(v, str):
        name = v.upper().strip()
        try:
            return pylinac.Protocol[name]
        except KeyError:
            raise ValueError(f"'{v}' is not a valid protocol (VARIAN, SIEMENS, ELEKTA, NONE)")
    raise ValueError("Invalid protocol format. Must be a pylinac.Protocol or a string.")

PylinacProtocol = typing.Annotated[pylinac.Protocol, pydantic.BeforeValidator(validate_pylinac_protocol)]