import pylinac.calibration.trs398
import tomllib
import click


# Load a TOML file
def load_toml_file(path):
    with open(path, "rb") as f:
        return tomllib.load(f)

# Get a nested value in a dictionary
def get_nested(dictObj, *keys, default=None):
    for key in keys:
        if isinstance(dictObj, dict):
            dictObj = dictObj.get(key)
        else:
            return default
    return dictObj if dictObj is not None else default

# Validate option helper.
def resolve_option(cli_value, config, key_path, *, required=False, prompt=False, prompt_text=None):
    keys = key_path.split(".")
    value = cli_value or get_nested(config, *keys)

    if value is None:
        if prompt:
            return click.prompt(prompt_text or f"Enter value for '{key_path}'")
        if required:
            raise click.UsageError(f"Missing required option: --{keys[-1]} or '{key_path}' in config.")
    return value

def resolve_option2(cli_value, config, key_path):
    keys = key_path.split(".")
    value = cli_value or get_nested(config, *keys)

    if value is None:
        raise click.UsageError(f"Missing required option: --{keys[-1]} or '{key_path}' in config.")
    return value

# Example calibration data structure used in the calibration file.
calibration_data = {
    "chamber":"30013",
    "clinical_pdd_zref": 66.5,
    "energy": 6,
    "fff": False,
    "institution": "Your institution here",
    "k_elec": 1.000,
    "m_opposite": [25.64, 25.65, 25.65],
    "m_reference": [25.65, 25.66, 25.65],
    "m_reduced": [25.64, 25.63, 25.63],
    "measurement_date": "2025-05-16",
    "mu": 200,
    "n_dw": 5.443,
    "physicist": "Person realizing the calibration",
    "press": 100.65839,
    "setup": "SSD",
    "temp": 22.1,
    "tissue_correction": 1.0,
    "tpr2010": 0.573573574,
    "unit": "Unit employed",
    "voltage_reduced": -150,
    "voltage_reference": -300,
    "notes": "Sample note."
}

def GetBaseTypes(config_quantities: dict) -> dict:
    """
    Get the base types of the quantities from the config file.
    """
    baseTypes = dict()
    for key in config_quantities:
        baseTypes[key] = config_quantities[key]["baseType"]
    return baseTypes

def Row2Measurement(row: dict, header: dict, baseTypes: dict) -> dict:
    """
    Convert a row from the CSV file into a measurement dictionary.
    """
    measurement = dict()
    for key in row:
        if baseTypes[key] == "int":
            measurement[key] = int(row[key])
        elif baseTypes[key] == "float":
            measurement[key] = float(row[key])

    return measurement

def ConvertMeasurement(rawMeasurement: dict, oldUnits: dict, newUnits: dict) -> dict:
    """
    Converts raw measurement in old units to new units.
    """
    measurement = rawMeasurement.copy()
    for key in rawMeasurement:
        if oldUnits[key] != newUnits[key]:
            if key == "T":
                # measurement[key] = trs398.convert_temperature(rawMeasurement[key], oldUnits[key], newUnits[key])
                if oldUnits[key] == "°F":
                    measurement[key] = pylinac.calibration.trs398.fahrenheit2celsius(rawMeasurement[key])
                elif oldUnits[key] == "K":
                    measurement[key] = rawMeasurement[key] + 273
            elif key == "P":
                # measurement[key] = trs398.convert_pressure(rawMeasurement[key], oldUnits[key], newUnits[key])
                if oldUnits[key] == "mbar":
                    measurement[key] = pylinac.calibration.trs398.mbar2kPa(rawMeasurement[key])
                elif oldUnits[key] == "mmHg":
                    measurement[key] = pylinac.calibration.trs398.mmHg2kPa(rawMeasurement[key])
            # elif key == "m":
            #     measurement[key] = trs398.convert_charge(rawMeasurement[key], oldUnits[key], newUnits[key])
            # elif key == "k_TP":
            #     measurement[key] = trs398.convert_temperature_pressure_correction_factor(rawMeasurement["T"], rawMeasurement["P"], oldUnits["T"], oldUnits["P"], newUnits["T"], newUnits["P"])
            # elif key == "m_corrected":
            #     measurement[key] = trs398.convert_charge(rawMeasurement[key], oldUnits[key], newUnits[key])
    return measurement

def FindAverage(numberList: list) -> float:
    acum = 0
    for number in numberList:
        acum = acum + number
    # DEBUG: FAIL. With empty value .csv input files.
    return acum / len(numberList)

def FindStdDev(numberList: list) -> float:
    average = FindAverage(numberList)
    acum = 0
    for number in numberList:
        acum = acum + (number - average) ** 2
    return (acum / len(numberList)) ** 0.5

def FindExpectedValue(numberList: list) -> float:
    return FindAverage(numberList)

def main():
    return 0

if __name__ == "__main__":
    errorCode = main()
    print(f"Program terminated with errorCode: {errorCode}")