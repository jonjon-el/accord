import pylinac

from accord.adapters.base_adapter import BaseAdapter


def Measurement2PylinacUnits_row(measurement_row: dict, oldUnits: dict) -> dict:
    convertedMeasurement_row = measurement_row.copy()
    for key in convertedMeasurement_row:
        if key == "T":
            if oldUnits[key] == "°F":
                convertedMeasurement_row[key] = pylinac.calibration.trs398.fahrenheit2celsius(convertedMeasurement_row[key])
            elif oldUnits[key] == "°C":
                pass
            else:
                raise ValueError(f"Invalid temperature unit: {oldUnits[key]}")
        elif key == "P":
            if oldUnits[key] == "mbar":
                convertedMeasurement_row[key] = pylinac.calibration.trs398.mbar2kPa(convertedMeasurement_row[key])
            elif oldUnits[key] == "mmHg":
                convertedMeasurement_row[key] = pylinac.calibration.trs398.mmHg2kPa(convertedMeasurement_row[key])
            elif oldUnits[key] == "kPa":
                pass
            else:
                raise ValueError(f"Invalid pressure unit: {oldUnits[key]}")
            
    return convertedMeasurement_row


def Measurements2PylinacUnits_set(rawMeasurements_set: list[list[dict]], oldUnits: dict) -> list[list[dict]]:
    """
    Convert measurements to pylinac units.

    Args:
        rawMeasurements_set (list[list[dict]]): Raw measurements to process.
        oldUnits (dict): Old units for conversion.

    Returns:
        list[list[dict]]: Processed measurements.
    """
    measurements_set = list()
    for rawMeasurements_table in rawMeasurements_set:
        measurements_table = list()
        for rawMeasurement_row in rawMeasurements_table:
            measurement_row = Measurement2PylinacUnits_row(rawMeasurement_row, oldUnits)
            measurements_table.append(measurement_row.copy())
        measurements_set.append(measurements_table.copy())
    return measurements_set


def ProcessMeasurements_set(measurements_set: list[list[dict]], ref_temp: float, k_elec: float, k_pol: float, k_s: float) -> list[list[dict]]:
    """
    Process measurements to calculate corrected charge and temperature-pressure correction factor.

    Args:
        measurements_set (list[list[dict]]): Measurements to process in pylinac units.
        ref_temp (float): Reference temperature for correction.
        k_elec (float): Electric field correction factor.
        k_pol (float): Polarization correction factor.
        k_s (float): Scatter correction factor.

    Returns:
        list[list[dict]]: Processed measurements.
    """
    processedMeasurements_set = list()
    for measurements_table in measurements_set:
        processedMeasurements_table = list()
        for measurement_row in measurements_table:
            processedMeasurement_row = measurement_row.copy()
            processedMeasurement_row["k_TP"] = pylinac.calibration.trs398.k_tp(
                temp=measurement_row["T"],
                press=measurement_row["P"],
                ref_temp=ref_temp
            )
            processedMeasurement_row["m_corrected"] = pylinac.calibration.trs398.m_corrected(
                m_reference=measurement_row["m"],
                k_tp=processedMeasurement_row["k_TP"],
                k_elec=k_elec,
                k_pol=k_pol,
                k_s=k_s
            )
            processedMeasurements_table.append(processedMeasurement_row.copy())
        processedMeasurements_set.append(processedMeasurements_table.copy())
    return processedMeasurements_set


class AnalyzePreliminaryAdapter(BaseAdapter):
    def __init__(self):
        pass