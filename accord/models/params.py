import datetime
import pathlib
import typing

import pydantic
import pylinac

import accord.models.annotatedTypes
import accord.models.trs398


class AnalyzeImagePlanar(pydantic.BaseModel):
    """
    This class defines the parameters for the analyze image planar command.
    It is used to validate the parameters passed to the command and to provide a structured way to access them.
    """

    model_config = pydantic.ConfigDict(
        extra="forbid",
        strict=True,
    )

    path: accord.models.annotatedTypes.AbsolutePath
    protocol: pylinac.Protocol = pylinac.Protocol.NONE
    output: accord.models.annotatedTypes.AbsolutePath

    @pydantic.field_validator("protocol", mode="before")
    @classmethod
    def cast_to_enum(cls: type[pydantic.BaseModel], value: typing.Any) -> pylinac.Protocol:
        """Convierte el valor a un miembro del enum Protocol, si es una cadena."""
        if isinstance(value, str):
            try:
                return pylinac.Protocol[value]
            except ValueError:
                raise ValueError(f"Invalid protocol: {value}. Must be one of {[e.value for e in pylinac.Protocol]}")
        return value


class CreateImagePlanar(pydantic.BaseModel):
    """
    This class defines the parameters for the create image planar command.
    It is used to validate the parameters passed to the command and to provide
    a structured way to access them.
    """

    model_config = pydantic.ConfigDict(
        extra="forbid",
        strict=True
    )

    path: accord.models.annotatedTypes.AbsolutePath
    field_size_mm: accord.models.annotatedTypes.Float2Tuple # = pydantic.Field(alias="field-size-mm")
    sigma_mm: float #= pydantic.Field(alias="sigma-mm")
    gantry_angle: float #= pydantic.Field(alias="gantry-angle")
    epid: str


class PreliminaryAnalysisParams(pydantic.BaseModel):
    """
    This class defines the parameters for the preliminary analysis command.
    It is used to validate the parameters passed to the command and to provide
    a structured way to access them.
    """

    model_config = pydantic.ConfigDict(
        extra="forbid",
        strict=True,
    )

    summary: accord.models.annotatedTypes.AbsolutePath
    devices: accord.models.annotatedTypes.AbsolutePath
    input_dir: accord.models.annotatedTypes.AbsolutePath
    output_dir: accord.models.annotatedTypes.AbsolutePath
    input_preffix: str
    output_preffix: str
    filetype: str
    max_ptp: float
    ref_temp: float
    k: int


class GenerateCalibrationReportParams(pydantic.BaseModel):
    """
    This class defines the parameters for the generate calibration report command.
    It is used to validate the parameters passed to the command and to provide
    a structured way to access them.
    """

    model_config = pydantic.ConfigDict(
        extra="forbid",
        strict=True,
        populate_by_name=True
    )

    path: accord.models.annotatedTypes.AbsolutePath # not belongs to pylinac.

    # TRS398Photon parameters:
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
    # press: float
    press: accord.models.annotatedTypes.PressTuple # -> float in pylinac.
    temp: float
    voltage_reference: int
    voltage_reduced: int
    m_reference: accord.models.annotatedTypes.Float3Tuple | float
    m_reduced: accord.models.annotatedTypes.Float3Tuple | float
    m_opposite: accord.models.annotatedTypes.Float3Tuple | float
    k_elec: float
    clinical_pdd_zref: float | None = None
    clinical_tmr_zref: float | None = None
    tissue_correction: float = 1.0

    # publish_pdf method parameters:
    filename: accord.models.annotatedTypes.AbsolutePath = pydantic.Field(alias="output")
    notes: accord.models.annotatedTypes.NotesList | None = None
    open_file: bool = False
    metadata: dict | None = None

    @property
    def to_domain_scheme(self) -> accord.models.trs398.TRS398PhotonScheme:
        """Construye el objeto complejo a partir de los campos planos."""

        # Converting press from tuple to float in kPa.
        # TODO: Deal with the case of a wrong unit.
        press_value, press_unit = self.press
        if press_unit == "kPa":
            press_kpa = press_value
        elif press_unit == "mmHg":
            press_kpa = pylinac.calibration.trs398.mmHg2kPa(press_value)
        elif press_unit == "mbar":
            press_kpa = pylinac.calibration.trs398.mbar2kPa(press_value)

        return accord.models.trs398.TRS398PhotonScheme(
            institution=self.institution,
            physicist=self.physicist,
            unit=self.unit,
            measurement_date=self.measurement_date,
            electrometer=self.electrometer,
            setup=self.setup,
            chamber=self.chamber,
            n_dw=self.n_dw,
            mu=self.mu,
            tpr2010=self.tpr2010,
            energy=self.energy,
            fff=self.fff,
            press=press_kpa,
            temp=self.temp,
            voltage_reference=self.voltage_reference,
            voltage_reduced=self.voltage_reduced,
            m_reference=self.m_reference,
            m_reduced=self.m_reduced,
            m_opposite=self.m_opposite,
            k_elec=self.k_elec,
            clinical_pdd_zref=self.clinical_pdd_zref,
            clinical_tmr_zref=self.clinical_tmr_zref,
            tissue_correction=self.tissue_correction
        )


