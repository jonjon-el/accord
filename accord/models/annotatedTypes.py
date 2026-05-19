from pathlib import Path
from typing import Annotated, Any

from pydantic import BeforeValidator, AfterValidator


# Define a type for a validated path.

def ConvertToPath(value: Any) -> Path:
    """Convert a string to a Path object"""
    if isinstance(value, str):
        return Path(value)
    return value

def ValidateAndResolvePath(path: Path) -> Path:
    """Validate the path and resolve it to an absolute path"""
    absolutePath = path.resolve()
    if not absolutePath.exists():
        raise ValueError(f"Path does not exist: {absolutePath}")
    return absolutePath

AbsolutePath = Annotated[
    Path,
    BeforeValidator(ConvertToPath),
    AfterValidator(ValidateAndResolvePath)
]