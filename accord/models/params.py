from pathlib import Path

from pydantic import BaseModel, ConfigDict

from accord.models.annotatedTypes import AbsolutePath

class PreliminaryAnalysisParams(BaseModel):
    """
    This class defines the parameters for the preliminary analysis command.
    It is used to validate the parameters passed to the command and to provide
    a structured way to access them.
    """

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
    )

    summary: AbsolutePath
    devices: AbsolutePath
    input_dir: AbsolutePath
    output_dir: AbsolutePath
    input_preffix: str
    output_preffix: str
    filetype: str
    max_ptp: float
    ref_temp: float
    k: int

