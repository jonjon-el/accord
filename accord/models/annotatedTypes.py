import pathlib
import typing

import pydantic


# Define a type for a validated path.

def ConvertToPath(value: typing.Any) -> pathlib.Path:
    """Convert a string to a Path object"""
    if isinstance(value, str):
        return pathlib.Path(value)
    return value

def ValidateAndResolvePath(path: pathlib.Path) -> pathlib.Path:
    """Validate the path and resolve it to an absolute path"""
    absolutePath = path.resolve()
    # if absolutePath.exists():
    #    print(f"WARNING: Path '{absolutePath}' exists. Overwriting.")
    return absolutePath

AbsolutePath = typing.Annotated[
    pathlib.Path,
    pydantic.BeforeValidator(ConvertToPath),
    pydantic.AfterValidator(ValidateAndResolvePath)
]

## types for list -> tuple
# Función que convierte lista a tupla si es necesario
def coerce_to_tuple(v: typing.Any) -> typing.Any:
    if isinstance(v, list):
        return tuple(v)
    return v

# Definimos tipos anotados para tus campos específicos
# Para 'press': (float, str)
PressTuple = typing.Annotated[
    tuple[float, str],
    pydantic.BeforeValidator(coerce_to_tuple)
]

# Si tienes otros campos como 'm_opposite' que son 3 floats:
Float3Tuple = typing.Annotated[
    tuple[float, float, float],
    pydantic.BeforeValidator(coerce_to_tuple)
]

## types for list -> tuple
# Función que convierte tupla a lista si es necesario
def coerce_to_list(v: typing.Any) -> typing.Any:
    if isinstance(v, tuple):
        return list(v)
    return v

# type for notes to be list of strings
NotesList = typing.Annotated[
    list[str],
    pydantic.BeforeValidator(coerce_to_list)
]