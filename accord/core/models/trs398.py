import pydantic
import enum
import pydantic_core

class TRS398Scheme_setup(str, enum.Enum):
    """
    This enum defines the possible setups for the TRS398 calibration scheme.
    """

    SSD = "SSD"
    SAD = "SAD"

class TRS398PhotonScheme(pydantic.BaseModel):
    """
    This class defines the parameters for the TRS398 calibration scheme.
    """

    model_config = pydantic.ConfigDict(
        extra="forbid",
        strict=True,
    )

    institution: str = ""
    physicist: str = ""
    unit: str = ""
    measurement_date: str = ""
    electrometer: str = ""
    setup: str
    chamber: str
    n_dw: float
    mu: int
    tpr2010: float
    energy: int
    fff: bool
    press: float
    temp: float
    voltage_reference: int
    voltage_reduced: int
    m_reference: tuple | float
    m_reduced: tuple | float
    m_opposite: tuple | float
    k_elec: float
    clinical_pdd_zref: float | None = None
    clinical_tmr_zref: float | None = None
    tissue_correction: float = 1.0
