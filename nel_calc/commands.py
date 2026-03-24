import numpy as np
import sys
import json
#import tomlkit
import tomllib
import csv
import pathlib
import datetime
import importlib.resources
import shutil

import pylinac.calibration.trs398
import pylinac.calibration.tg51
import pylinac.core.image_generator.layers
import pylinac
print(f"Pylinac version: {pylinac.__version__}")
from nel_calc.trs398custom import TRS398Custom

import click
# import click_datetime
# import pandas as pd
# import matplotlib.pyplot as plt
# plt.switch_backend('Agg')  # Use a non-interactive backend for matplotlib

import nel_calc.nel_config
import nel_calc.nel_aux
import nel_calc.customSim

import nel_calc.metrology
import nel_calc.corrections

def validate_config_path_exclusive_option(ctx, param, value):
    """Validate that config_path is not used with other options."""
    click.echo(f"Context: {ctx}")
    click.echo(f"Parameter: {param}")
    click.echo(f"Value: {value}")
    click.echo(f'Params: {ctx.params if ctx else "No context"}')

    if value:
        for other_param in ctx.params:
            if other_param == "config_path":
                raise click.UsageError(f"Options '{param.name}' and '{other_param}' cannot be used together.")

    return value

def validate_mutually_exclusive_options(ctx, param, value):
    """Validate that only one of the options is used."""
    click.echo(f"Context: {ctx}")
    click.echo(f"Parameter: {param}")
    click.echo(f"Value: {value}")
    click.echo(f'Params: {ctx.params if ctx else "No context"}')
    
    if value:
        for other_param in ctx.params:
            if other_param != param.name and ctx.params[other_param]:
                raise click.UsageError(f"Options '{param.name}' and '{other_param}' cannot be used together.")
            
    return value

@click.group()
@click.version_option("0.2.0", prog_name="nel_calc")
def cli():
    """Main command line interface for the program."""
    pass

#command to copy a sample file
@click.command()
@click.argument("path", type=click.Path(file_okay=True, dir_okay=True, path_type=pathlib.Path), required=True)
@click.option("--file-class", type=click.Choice(["config", "calibration", "preliminary", "devices"]), required=True, help="Class of sample file to copy.")
def copy_sample(path: pathlib.Path, file_class: str):
    """Copy a sample file."""
    # Check if the file already exists.
    
    # if pathlib.Path(path).exists() and pathlib.Path(path).is_file():
    #    raise click.BadParameter("File already exists. Please choose a different name or delete the existing file.")

    if file_class == "config":
        configTraversable = importlib.resources.files("nel_calc").joinpath("sampleFiles/config.toml")
    elif file_class == "calibration":
        configTraversable = importlib.resources.files("nel_calc").joinpath("sampleFiles/calibration.toml")
    elif file_class == "preliminary":
        configTraversable = importlib.resources.files("nel_calc").joinpath("sampleFiles/preliminary_0.csv")
    elif file_class == "devices":
        configTraversable = importlib.resources.files("nel_calc").joinpath("sampleFiles/devices.toml")
    else:
        raise click.BadParameter("Invalid file type. Please choose 'config', 'calibration', 'preliminary', or 'devices'.")

    try:
        with importlib.resources.as_file(configTraversable) as configPath:
            shutil.copy(configPath, path)
            click.echo(f"File copied.")
    except FileNotFoundError:
        raise click.ClickException(f"Sample file not found in {configPath}.")
    except PermissionError:
        raise click.ClickException(f"Permission denied when copying file.")
    except shutil.SameFileError:
        raise click.ClickException(f"Source and destination represents the same file.")
    except OSError as e:
        raise click.ClickException(f"Error copying file: {e.strerror}.")
    
    sys.exit(0)

#command to create image for 2D profiling.
@click.command()
@click.argument("path", type=click.Path(file_okay=True, dir_okay=False, path_type=pathlib.Path), required=True)
@click.option("--config", type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=pathlib.Path), help="Path to config file.")
@click.option("--field-size-mm", type=click.Tuple([click.FLOAT, click.FLOAT]), help="Field size in mm.")
@click.option("--sigma-mm", type=click.FLOAT, help="Sigma in mm for the Gaussian filter.")
@click.option("--gantry-angle", type=click.FLOAT, help="Gantry angle in degrees.")
@click.option("--epid", type=click.STRING, help="Name of the EPID that will be simulated.")
def create_image_planar(
    path: pathlib.Path,
    config: pathlib.Path,
    field_size_mm: tuple[float, float],
    sigma_mm: float,
    gantry_angle: float,
    epid: str):
    """Create planar image for 2D profiling."""

    cfg = nel_calc.nel_aux.load_toml_file(config) if config else {}

    field_size_mm = nel_calc.nel_aux.resolve_option2(field_size_mm, cfg, "create-image-planar.field-size-mm")
    sigma_mm = nel_calc.nel_aux.resolve_option2(sigma_mm, cfg, "create-image-planar.sigma-mm")
    gantry_angle = nel_calc.nel_aux.resolve_option2(gantry_angle, cfg, "create-image-planar.gantry-angle")
    epid = nel_calc.nel_aux.resolve_option2(epid, cfg, "create-image-planar.epid")

    # Check types
    safe = dict()    

    if isinstance(field_size_mm, list) and len(field_size_mm) == 2 and all(isinstance(x, float) for x in field_size_mm): #TOML files return lists not tuples
        safe["field_size_mm"] = tuple(field_size_mm)
    elif isinstance(field_size_mm, tuple) and len(field_size_mm) == 2 and all(isinstance(x, float) for x in field_size_mm):
        safe["field_size_mm"] = field_size_mm
    else:
        raise click.BadParameter("field-size-mm must be a tuple of two floats.")

    if isinstance(sigma_mm, float):
        safe["sigma_mm"] = sigma_mm
    else:
        raise click.BadParameter("sigma-mm must be a float.")

    if isinstance(gantry_angle, float):
        safe["gantry_angle"] = gantry_angle
    else:
        raise click.BadParameter("gantry-angle must be a float.")
    
    if isinstance(epid, str):
        safe["epid"] = epid
    else:
        raise click.BadParameter("epid must be a string.")

    #Load the appropiated epid class.
    if safe["epid"] == "iViewGT":
        iViewGT0 = nel_calc.customSim.iViewGTImage()
    else:
        raise click.exceptions.BadParameter(f"Unknown EPID name for class instance: {safe["epid"]}.")
    
    iViewGT0.add_layer(pylinac.core.image_generator.layers.FilteredFieldLayer(field_size_mm=safe["field_size_mm"]))
    iViewGT0.add_layer(pylinac.core.image_generator.layers.GaussianFilterLayer(sigma_mm=safe["sigma_mm"]))
    

    iViewGT0.generate_dicom(file_out_name=str(path), gantry_angle=safe["gantry_angle"])

    click.echo("Sample images created.")
    sys.exit(0)

#analyze-preliminary command.
@click.command()
@click.option("--config", type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=pathlib.Path), help="Path to config file.")
@click.option("--summary", type=click.Path(file_okay=True, dir_okay=False, path_type=pathlib.Path), help="Path to summary file.")
@click.option("--devices", type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=pathlib.Path), help="File with specifications of devices used in the measure.")
@click.option("--input-dir", type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=pathlib.Path), help="Path of input file directory.")
@click.option("--output-dir", type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=pathlib.Path), help="Path of output file directory.")
@click.option("--input-preffix", type=click.STRING, help="Input fileName preffix.")
@click.option("--output-preffix", type=click.STRING, help="Output fileName preffix.")
@click.option("--filetype", type=click.STRING, help="FileType of the input and output files.")
@click.option("--max-PTP", type=click.FLOAT, help="Maximum limit for PTP.")
@click.option("--ref-temp", type=click.FLOAT, help="Reference temperature for k_TP calculation.")
@click.option("--k", type=click.FLOAT, help="Coverage factor for calculating expanded uncertainty using normal distribution.")
def analyze_preliminary(config: pathlib.Path,
                        summary: pathlib.Path,
                        devices: pathlib.Path,
                        input_dir: pathlib.Path,
                        output_dir: pathlib.Path,
                        input_preffix: str,
                        output_preffix: str,
                        filetype: str,
                        max_ptp: float,
                        ref_temp: float,
                        k: float):
    """Analyze calibration preliminary data about measurements."""

    cfg = nel_calc.nel_aux.load_toml_file(config) if config else {}
    input_dir = nel_calc.nel_aux.resolve_option2(input_dir, cfg, "analyze-preliminary.input-dir")
    output_dir = nel_calc.nel_aux.resolve_option2(output_dir, cfg, "analyze-preliminary.output-dir")
    input_preffix = nel_calc.nel_aux.resolve_option2(input_preffix, cfg, "analyze-preliminary.input-preffix")
    output_preffix = nel_calc.nel_aux.resolve_option2(output_preffix, cfg, "analyze-preliminary.output-preffix")
    filetype = nel_calc.nel_aux.resolve_option2(filetype, cfg, "analyze-preliminary.filetype")
    summary = nel_calc.nel_aux.resolve_option2(summary, cfg, "analyze-preliminary.summary")
    max_ptp = nel_calc.nel_aux.resolve_option2(max_ptp, cfg, "analyze-preliminary.max-PTP")
    ref_temp = nel_calc.nel_aux.resolve_option2(ref_temp, cfg, "analyze-preliminary.ref-temp")
    devices = nel_calc.nel_aux.resolve_option2(devices, cfg, "analyze-preliminary.devices")
    k = nel_calc.nel_aux.resolve_option2(k, cfg, "analyze-preliminary.k")
    
    # Check types
    safe = dict()
    if isinstance(input_dir, str):
        safe["input_dir"] = pathlib.Path(input_dir)
    elif isinstance(input_dir, pathlib.Path):
        safe["input_dir"] = input_dir
    else:
        raise click.BadParameter("input-dir must be a pathlib.Path.")
    
    if isinstance(output_dir, str):
        safe["output_dir"] = pathlib.Path(output_dir)
    elif isinstance(output_dir, pathlib.Path):
        safe["output_dir"] = output_dir
    else:
        raise click.BadParameter("output-dir must be a pathlib.Path.")
    
    if isinstance(input_preffix, str):
        safe["input_preffix"] = input_preffix
    else:
        raise click.BadParameter("input-preffix must be a string.")
    
    if isinstance(output_preffix, str):
        safe["output_preffix"] = output_preffix
    else:
        raise click.BadParameter("output-preffix must be a string.")
    
    if isinstance(filetype, str):
        safe["filetype"] = filetype
    else:
        raise click.BadParameter("filetype must be a string.")
    
    if isinstance(summary, str):
        safe["summary"] = pathlib.Path(summary)
    elif isinstance(summary, pathlib.Path):
        safe["summary"] = summary
    else:
        raise click.BadParameter("summary must be a pathlib.Path or a string.")
    
    if isinstance(max_ptp, float):
        safe["max_ptp"] = max_ptp
    else:
        raise click.BadParameter("max-PTP must be a float.")

    if isinstance(ref_temp, float):
        safe["ref_temp"] = ref_temp
    else:
        raise click.BadParameter("ref-temp must be a float.")

    if isinstance(devices, str):
        safe["devices"] = pathlib.Path(devices)
    elif isinstance(devices, pathlib.Path):
        safe["devices"] = devices
    else:
        raise click.BadParameter("devices must be a pathlib.Path or a string.")

    if isinstance(k, float):
        safe["k"] = k
    else:
        raise click.BadParameter("k must be a float.")

    ## from data files to tables of values with the appropiate base types.

    # Getting the input filenames.
    filepaths = list()
    for file in pathlib.Path(input_dir).iterdir():
        if file.is_file():
            if file.name.startswith(input_preffix) and file.suffix == f".{filetype}":
                filepaths.append(str(file.resolve()))
    if len(filepaths) == 0:
        raise FileNotFoundError("Cannot find input files.")

    # Loading quantities data.
    quantities_traversable = importlib.resources.files("nel_calc").joinpath("quantities.json")
    try:
        with quantities_traversable.open("r", encoding="utf-8") as quantitiesFile:
            quantitiesData = json.load(quantitiesFile)
    except FileNotFoundError:
        raise click.ClickException(f"Quantities file not found in {quantities_traversable}.")
    except json.JSONDecodeError:
        raise click.ClickException(f"Invalid JSON in quantities file {quantities_traversable}.")

    # Read the files and convert them to rawMeasurement_list_tries
    rawMeasurement_list_tries = list()
    for filepath in filepaths:    
        with open(filepath, "r", encoding = "utf-8") as csvFile:
            csvDictReader = csv.DictReader(csvFile)
            input_preliminary_quantities = csvDictReader.fieldnames # Getting the current header in first line
            input_preliminary_units = next(csvDictReader) # Getting the units in second line. Try deleting for specify in config file.
            rawMeasurement_list = list()
            for row in csvDictReader: # Getting the values
                rawMeasurement = nel_calc.nel_aux.Row2Measurement2(row=row, quantities=quantitiesData)
                rawMeasurement_list.append(rawMeasurement.copy())
        rawMeasurement_list_tries.append(rawMeasurement_list.copy())

    ## from tables of values to tables of values with the appropiate units and the new calculated quantities.

    # Changing bounds of k_tp to avoid BoundError
    # Value are the just as closest posible to default values
    pylinac.calibration.trs398.MAX_PTP = max_ptp

    # Convert the units and calculate the corrected charge and the temperature-pressure correction factor
    measurement_list_tries = list()

    for rawMeasurement_list in rawMeasurement_list_tries:
        measurement_list = list()
        for rawMeasurement in rawMeasurement_list:
            measurement = nel_calc.nel_aux.Convert_measurement_to_pylinac_units(measurement=rawMeasurement, oldUnits=input_preliminary_units)
            measurement["k_TP"] = pylinac.calibration.trs398.k_tp(temp = measurement["T"], press = measurement["P"], ref_temp=ref_temp) # Calculation of k_TP with the reference temperature specified by the user.
            measurement["m_corrected"] = pylinac.calibration.trs398.m_corrected(m_reference=measurement["m"],
                                                            k_tp=measurement["k_TP"],
                                                            k_elec=1,
                                                            k_pol=1,
                                                            k_s=1)
            measurement_list.append(measurement.copy())
        measurement_list_tries.append(measurement_list.copy())

    ## Calculating general statistical quantities.

    # Calculate the average, standard deviation and expected value of m_corrected
    m_corrected_averageList = list()
    m_corrected_stdDevList = list()
    m_corrected_expectedValueList = list()

    for measurement_list in measurement_list_tries:
        m_corrected_list = [measurement["m_corrected"] for measurement in measurement_list]

        # Calculate the average of m_corrected
        m_corrected_average_item = nel_calc.nel_aux.FindAverage(m_corrected_list)
        m_corrected_averageList.append(m_corrected_average_item)

        # Calculate the standard deviation of m_corrected
        m_corrected_stdDev_item = nel_calc.nel_aux.FindStdDev(m_corrected_list)
        m_corrected_stdDevList.append(m_corrected_stdDev_item)

        # Calculate the expected value of m_corrected
        m_corrected_expectedValue_item = nel_calc.nel_aux.FindExpectedValue(m_corrected_list)
        m_corrected_expectedValueList.append(m_corrected_expectedValue_item)
    
    ## Calculating uncertainties.

    # Device specifications.
    try:
        with open(safe["devices"], "rb") as devicesFile:
            devicesData = tomllib.load(devicesFile)
            # Example of how to access the data:
            termometer_resolution = devicesData["termometer"]["resolution"]
            termometer_accuracy = devicesData["termometer"]["accuracy"]
            termometer_distribution = devicesData["termometer"]["distribution"]
            termometer_k = devicesData["termometer"]["k"]
            barometer_resolution = devicesData["barometer"]["resolution"]
            barometer_accuracy = devicesData["barometer"]["accuracy"]
            barometer_distribution = devicesData["barometer"]["distribution"]
            barometer_k = devicesData["barometer"]["k"]
    except tomllib.TOMLDecodeError as e:
        print(f"Error at line {e.lineno}, col {e.colno}: {e.msg}")
    except FileNotFoundError:
        print("Devices file not found.")

    m_corrected_average_123 = np.mean(m_corrected_averageList) # Average of the averages of m_corrected for each try. This is the same as the average of all m_corrected values.

    # Calculating standard uncertainties.
    u_L = nel_calc.metrology.calc_u_A(*m_corrected_averageList)
    u_T_resolution = nel_calc.metrology.calc_u_B(error_value=termometer_resolution, distribution=termometer_distribution, k=termometer_k)
    u_T_accuracy = nel_calc.metrology.calc_u_B(error_value=termometer_accuracy, distribution=termometer_distribution, k=termometer_k)
    u_T = nel_calc.metrology.calc_u_c(u_T_resolution, u_T_accuracy)
    u_P_resolution = nel_calc.metrology.calc_u_B(error_value=barometer_resolution, distribution=barometer_distribution, k=barometer_k)
    u_P_accuracy = nel_calc.metrology.calc_u_B(error_value=barometer_accuracy, distribution=barometer_distribution, k=barometer_k)
    u_P = nel_calc.metrology.calc_u_c(u_P_resolution, u_P_accuracy)

    # Calculating sensitivity coefficients.
    c_L = nel_calc.corrections.calc_c_L(T_expected_value=20, P_expected_value=101.325, T_ref=20, P_ref=101.325)
    c_T = nel_calc.corrections.calc_c_T(P_expected_value=101.325, T_ref=20, P_ref=101.325)
    c_P = nel_calc.corrections.calc_c_P(L_expected_value=1, T_expected_value=20, P_expected_value=101.325, T_ref=20, P_ref=101.325)

    # Calculating combined standard uncertainty.
    u_c = nel_calc.metrology.calc_u_c(c_L*u_L, c_T*u_T, c_P*u_P)
    
    # Coverage factor for a confidence level of approximately 95% for a normal distribution.
    # TODO: Calculate the effective degrees of freedom and the corresponding coverage factor with the Welch-Satterthwaite formula or specify in command line.
    # k = 2
    
    # Calculating expanded uncertainty.
    U = nel_calc.metrology.calc_U(u_c, safe["k"])

    print(f"Mean of corrected values (Series 1, 2, 3): {m_corrected_average_123: .3f}")
    
    print("Sensitivity coefficients:")
    print(f"  Sensitivity coefficient for repetibility c_L: {c_L: .3f}")
    print(f"  Sensitivity coefficient for measurement temperature c_T: {c_T: .3f}")
    print(f"  Sensitivity coefficient for measurement pressure c_P: {c_P: .3f}")
    
    print("Standard uncertainties:")
    print(f"  Standard uncertainty for repetibility u_L: {u_L: .3f}")
    print(f"  Standard uncertainty for measurement temperature u_T: {u_T: .3f}")
    print(f"  Standard uncertainty for measurement pressure u_P: {u_P: .3f}")

    print("Standard uncertainties for sensitivity coefficients:")
    print(f"  Standard uncertainty for sensitivity coefficient c_L*u_L: {c_L*u_L: .3f}")
    print(f"  Standard uncertainty for sensitivity coefficient c_T*u_T: {c_T*u_T: .3f}")
    print(f"  Standard uncertainty for sensitivity coefficient c_P*u_P: {c_P*u_P: .3f}")

    print(f"Combined standard uncertainty: {u_c: .3f}")
    print(f"Coverage factor: 2")
    print(f"Expanded uncertainty (Series 1, 2, 3): {U: .3f}")
    print(f"Relative expanded uncertainty (Series 1, 2, 3): {U / m_corrected_average_123 * 100: .2f} %")

    ## From tables with calculated values to output files.
    
    # Loading file formats.
    # The order of the columns on input files are specified in a row of the input file itself.
    # The order of the columns on output files are specified in the file formats file.
    
    fileFormats_traversable = importlib.resources.files("nel_calc").joinpath("fileFormats.json")
    
    try:
        with fileFormats_traversable.open("r", encoding="utf-8") as fileFormatsFile:
            fileFormatsData = json.load(fileFormatsFile)
    except FileNotFoundError:
        raise click.ClickException(f"File formats file not found in {fileFormats_traversable}.")
    except json.JSONDecodeError:
        raise click.ClickException(f"Invalid JSON in file formats file {fileFormats_traversable}.")
    
    output_preliminary_quantities = fileFormatsData["output_preliminary"]["columns"]
    output_preliminary_units = fileFormatsData["output_preliminary"]["units"]

    # The quantities of the output files are the same as the input files plus the new quantities calculated in this command. The order of the columns in the output files are specified here.
    # Csvwriter writes the columns in the order specified in fieldnames.
    # fieldnames is a list.
    output_preliminary_quantities_complete = input_preliminary_quantities + output_preliminary_quantities

    # The units of the output files are written in the second line of the output files.
    # They are not list, but dict, because they are written as a row of CsvWriter to the csv file, so the keys are the column names and the values are the units.
    output_preliminary_units_dict = dict(zip(output_preliminary_quantities, output_preliminary_units))
    # The units of the output files are the same as the input files plus the new units specified here. The order of the columns in the output files are specified here.
    output_preliminary_units_complete = input_preliminary_units | output_preliminary_units_dict

    # Writing output files.
    i = 0
    for i in range(len(measurement_list_tries)):
        filePath = filepaths[i]
        dirs = pathlib.Path(filePath).parent
        stem = pathlib.Path(filePath).stem
        suffix = pathlib.Path(filePath).suffix
        output_filename = f"{output_preffix}{i}{suffix}"
        output_filePath = pathlib.Path(output_dir) / output_filename
        
        with open(output_filePath, "w", encoding="utf-8", newline='') as csvFile:
            csvWriter = csv.DictWriter(csvFile, fieldnames=output_preliminary_quantities_complete)
            csvWriter.writeheader()
            csvWriter.writerow(output_preliminary_units_complete)
            measurement_list = measurement_list_tries[i]
            for measurement in measurement_list:
                csvWriter.writerow(measurement)
            print(f"Output file {output_filename} created.")
            i = i + 1

    # Create the summary file.
    # .json
    output_quantities = dict()
    output_quantities["m_corrected_average"] = m_corrected_average_123
    output_quantities["c_L"] = c_L
    output_quantities["c_T"] = c_T
    output_quantities["c_P"] = c_P
    output_quantities["u_L"] = u_L
    output_quantities["u_T"] = u_T
    output_quantities["u_P"] = u_P
    output_quantities["c_L*u_L"] = c_L * u_L
    output_quantities["c_T*u_T"] = c_T * u_T
    output_quantities["c_P*u_P"] = c_P * u_P
    output_quantities["u_c"] = u_c
    output_quantities["k"] = k
    output_quantities["U"] = U

    summaryPath = safe["summary"] # TODO: Check if summary should really be inside output_dir
    with open(summaryPath, "w", encoding="utf-8") as summaryFile:
        json.dump(output_quantities, summaryFile, indent=4)
        print(f"Output file {safe['summary']} created.")

    click.echo("Preliminary analysis done.")
    sys.exit(0)

# analyze-image-planar.
@click.command()
@click.argument("path", type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=pathlib.Path), required=True)
@click.option("--protocol", type=click.Choice(pylinac.Protocol), help="Protocol used for calculations.")
@click.option("--output", type=click.Path(file_okay=True, dir_okay=False, path_type=pathlib.Path), help="Path to output analysis file.")
@click.option("--config", type=click.Path(exists=True, file_okay=True, path_type=pathlib.Path), help="Path to config file.")
def analyze_image_planar(
    path: pathlib.Path,
    config: pathlib.Path,
    protocol: str,
    output: pathlib.Path
    ):
    """Analyze field images."""

    cfg = nel_calc.nel_aux.load_toml_file(config) if config else {}

    protocol = nel_calc.nel_aux.resolve_option2(protocol, cfg, "analyze-image-planar.protocol")
    output = nel_calc.nel_aux.resolve_option2(output, cfg, "analyze-image-planar.output")

    # Check types
    safe = dict()

    if isinstance(protocol, str):
        if protocol == "elekta":
            safe["protocol"] = pylinac.Protocol.ELEKTA
        elif protocol == "varian":
            safe["protocol"] = pylinac.Protocol.VARIAN
        elif protocol == "siemens":
            safe["protocol"] = pylinac.Protocol.SIEMENS
        elif protocol == "none":
            safe["protocol"] = pylinac.Protocol.NONE
        else:
            raise click.BadParameter(f"Unknown protocol: {protocol}.")
    elif isinstance(protocol, pylinac.Protocol):
        safe["protocol"] = protocol
    else:
        raise click.BadParameter("protocol must be a pylinac.Protocol.")

    if isinstance(output, pathlib.Path):
        safe["output"] = output
    else:
        raise click.BadParameter("output must be a pathlib.Path.")

    # Load input files: field images
    field_analysis = pylinac.FieldAnalysis(path=str(path))
    
    # Picking the asked protocol.
    # if safe["protocol"] == "elekta":
        # protocol_class = pylinac.Protocol.ELEKTA
    # elif safe["protocol"] == "varian":
        # protocol_class = pylinac.Protocol.VARIAN
    # elif safe["protocol"] == "siemens":
        # protocol_class = pylinac.Protocol.SIEMENS
    # elif safe["protocol"] == None:
        # protocol_class = pylinac.Protocol.NONE
    # else:
        # raise click.exceptions.BadParameter(f"Unknown protocol: {safe['protocol']}.")
    
    # performing analysis
    # field_analysis.analyze(protocol=protocol_class)
    field_analysis.analyze(protocol=safe["protocol"])
    field_analysis.plot_analyzed_image()
    field_analysis.publish_pdf(filename=str(safe["output"]))
    
    click.echo(f"2D images analyzed.")
    sys.exit(0)

# # generate-calibration-report.
# @click.command()
# @click.argument("path", type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=pathlib.Path), required=True)
# @click.option("--config", type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=pathlib.Path), help="Config filename.")
# @click.option("--output", type=click.Path(file_okay=True, dir_okay=False, path_type=pathlib.Path), help="Output filename.")
# @click.option("--chamber", type=click.STRING, help="Chamber model.")
# @click.option("--clinical-pdd-zref", type=click.FLOAT, help="Clinical PDD Zref.")
# @click.option("--energy", type=click.INT, help="Energy.")
# @click.option("--fff", type=click.BOOL, help="FFF.")
# @click.option("--institution", type=click.STRING, help="Institution.")
# @click.option("--k-elec", type=click.FLOAT, help="K-electron.")
# # @click.option("--m-opposite", type=click.FLOAT, nargs=3, help="M opposite.")
# @click.option("--m-reference", type=click.FLOAT, nargs=3, help="M reference.")
# # @click.option("--m-reduced", type=click.FLOAT, nargs=3, help="M reduced.")
# @click.option("--measurement-date", type=click.STRING, help="Date of the measurement.")
# @click.option("--mu", type=click.INT, help="MU.")
# @click.option("--n-dw", type=click.FLOAT, help="N_Dw.")
# @click.option("--physicist", type=click.STRING, help="Physicist.")
# @click.option("--press", type=click.Tuple([click.FLOAT, click.Choice(['kPa', 'mbar', 'mmHg'])]), help="Pressure.")
# @click.option("--setup", type=click.STRING, help="Experimental setup.")
# @click.option("--temp", type=click.FLOAT, help="Temperature.")
# @click.option("--tissue-correction", type=click.FLOAT, help="Tissue correction.")
# # @click.option("--tpr2010", type=click.FLOAT, help="TPR2010.")
# @click.option("--unit", type=click.STRING, help="Unit.")
# # @click.option("--voltage-reduced", type=click.INT, help="Voltage reduced.")
# # @click.option("--voltage-reference", type=click.INT, help="Voltage reference.")
# @click.option("--notes", type=click.STRING, multiple=True, help="Notes.")
# @click.option("--ref-temp", type=click.FLOAT, help="Reference temperature.")
# @click.option("--k-q-direct", type=click.FLOAT, help="K-Q direct.")
# @click.option("--k-s", type=click.FLOAT, help="K-s correction factor.")
# @click.option("--k-pol", type=click.FLOAT, help="K-pol correction factor.")
# def generate_calibration_report(
#     path: pathlib.Path,
#     config: pathlib.Path,
#     output: pathlib.Path,
#     chamber: str,
#     clinical_pdd_zref: float,
#     energy: int,
#     fff: bool,
#     institution: str,
#     k_elec: float,
#     m_opposite: tuple[float, float, float]|None,
#     m_reference: tuple[float, float, float]|None,
#     m_reduced: tuple[float, float, float]|None,
#     measurement_date: str,
#     mu: int,
#     n_dw: float,
#     physicist: str,
#     press: tuple[float, str],
#     setup: str,
#     temp: float,
#     tissue_correction: float,
#     tpr2010: float,
#     unit: str,
#     voltage_reduced: int,
#     voltage_reference: int,
#     notes: tuple[str, ...],
#     ref_temp: float,
#     k_q_direct: float,
#     k_s: float,
#     k_pol: float
# ):
# generate-calibration-report.
@click.command()
@click.argument("path", type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=pathlib.Path), required=True)
@click.option("--config", type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=pathlib.Path), help="Config filename.")
@click.option("--output", type=click.Path(file_okay=True, dir_okay=False, path_type=pathlib.Path), help="Output filename.")
@click.option("--chamber", type=click.STRING, help="Chamber model.")
@click.option("--clinical-pdd-zref", type=click.FLOAT, help="Clinical PDD Zref.")
@click.option("--energy", type=click.INT, help="Energy.")
@click.option("--fff", type=click.BOOL, help="FFF.")
@click.option("--institution", type=click.STRING, help="Institution.")
@click.option("--k-elec", type=click.FLOAT, help="K-electron.")
@click.option("--m-opposite", type=click.FLOAT, nargs=3, help="M opposite.")
@click.option("--m-reference", type=click.FLOAT, nargs=3, help="M reference.")
@click.option("--m-reduced", type=click.FLOAT, nargs=3, help="M reduced.")
@click.option("--measurement-date", type=click.STRING, help="Date of the measurement.")
@click.option("--mu", type=click.INT, help="MU.")
@click.option("--n-dw", type=click.FLOAT, help="N_Dw.")
@click.option("--physicist", type=click.STRING, help="Physicist.")
@click.option("--press", type=click.Tuple([click.FLOAT, click.Choice(['kPa', 'mbar', 'mmHg'])]), help="Pressure.")
@click.option("--setup", type=click.STRING, help="Experimental setup.")
@click.option("--temp", type=click.FLOAT, help="Temperature.")
@click.option("--tissue-correction", type=click.FLOAT, help="Tissue correction.")
@click.option("--tpr2010", type=click.FLOAT, help="TPR2010.")
@click.option("--unit", type=click.STRING, help="Unit.")
@click.option("--voltage-reduced", type=click.INT, help="Voltage reduced.")
@click.option("--voltage-reference", type=click.INT, help="Voltage reference.")
@click.option("--notes", type=click.STRING, multiple=True, help="Notes.")
# @click.option("--ref-temp", type=click.FLOAT, help="Reference temperature.")
# @click.option("--k-q-direct", type=click.FLOAT, help="K-Q direct.")
# @click.option("--k-s", type=click.FLOAT, help="K-s correction factor.")
# @click.option("--k-pol", type=click.FLOAT, help="K-pol correction factor.")
def generate_calibration_report(
    path: pathlib.Path,
    config: pathlib.Path,
    output: pathlib.Path,
    chamber: str,
    clinical_pdd_zref: float,
    energy: int,
    fff: bool,
    institution: str,
    k_elec: float,
    m_opposite: tuple[float, float, float],
    m_reference: tuple[float, float, float],
    m_reduced: tuple[float, float, float],
    measurement_date: str,
    mu: int,
    n_dw: float,
    physicist: str,
    press: tuple[float, str],
    setup: str,
    temp: float,
    tissue_correction: float,
    unit: str,
    notes: tuple[str, ...],
    tpr2010: float,
    voltage_reduced: int,
    voltage_reference: int
    # ref_temp: float,
    # k_q_direct: float,
    # k_s: float,
    # k_pol: float
):
    """Generate report about calibration."""

    # Load config file
    cfg = nel_calc.nel_aux.load_toml_file(config) if config else {}

    # Load calibration file
    calibrationFile = nel_calc.nel_aux.load_toml_file(path)

    # Load values from files
    output = nel_calc.nel_aux.resolve_option2(output, cfg, "generate-calibration-report.output")
    # ref_temp = nel_calc.nel_aux.resolve_option2(ref_temp, cfg, "generate-calibration-report.ref-temp")

    chamber = nel_calc.nel_aux.resolve_option2(chamber, calibrationFile, "chamber")
    clinical_pdd_zref = nel_calc.nel_aux.resolve_option2(clinical_pdd_zref, calibrationFile, "clinical-pdd-zref")
    energy = nel_calc.nel_aux.resolve_option2(energy, calibrationFile, "energy")
    fff = nel_calc.nel_aux.resolve_option2(fff, calibrationFile, "fff")
    institution = nel_calc.nel_aux.resolve_option2(institution, calibrationFile, "institution")
    k_elec = nel_calc.nel_aux.resolve_option2(k_elec, calibrationFile,  "k-elec")
    m_opposite = nel_calc.nel_aux.resolve_option2(m_opposite, calibrationFile, "m-opposite")
    m_reference = nel_calc.nel_aux.resolve_option2(m_reference, calibrationFile, "m-reference")
    m_reduced = nel_calc.nel_aux.resolve_option2(m_reduced, calibrationFile, "m-reduced")
    measurement_date = nel_calc.nel_aux.resolve_option2(measurement_date, calibrationFile, "measurement-date")
    mu = nel_calc.nel_aux.resolve_option2(mu, calibrationFile, "mu")
    n_dw = nel_calc.nel_aux.resolve_option2(n_dw, calibrationFile, "n-dw")
    physicist = nel_calc.nel_aux.resolve_option2(physicist, calibrationFile, "physicist")
    press = nel_calc.nel_aux.resolve_option2(press, calibrationFile, "press")
    setup = nel_calc.nel_aux.resolve_option2(setup, calibrationFile, "setup")
    temp = nel_calc.nel_aux.resolve_option2(temp, calibrationFile, "temp")
    tissue_correction = nel_calc.nel_aux.resolve_option2(tissue_correction, calibrationFile, "tissue-correction")
    tpr2010 = nel_calc.nel_aux.resolve_option2(tpr2010, calibrationFile, "tpr2010")
    unit = nel_calc.nel_aux.resolve_option2(unit, calibrationFile, "unit")
    voltage_reduced = nel_calc.nel_aux.resolve_option2(voltage_reduced, calibrationFile, "voltage-reduced")
    voltage_reference = nel_calc.nel_aux.resolve_option2(voltage_reference, calibrationFile, "voltage-reference")
    notes = nel_calc.nel_aux.resolve_option2(notes, calibrationFile, "notes")
    # k_q_direct = nel_calc.nel_aux.resolve_option2(k_q_direct, calibrationFile, "k-q-direct")
    # k_s = nel_calc.nel_aux.resolve_option2(k_s, calibrationFile, "k-s")
    # k_pol = nel_calc.nel_aux.resolve_option2(k_pol, calibrationFile, "k-pol")

    # Check types
    safe = dict()
    if isinstance(output, str):
        safe["output"] = pathlib.Path(output)
    elif isinstance(output, pathlib.Path):
        safe["output"] = output
    else:
        raise click.BadParameter("output must be a path")
    
    if isinstance(chamber, str):
        safe["chamber"] = chamber
    else:   
        raise click.BadParameter("chamber must be a string")
    
    if isinstance(clinical_pdd_zref, float):
        safe["clinical_pdd_zref"] = clinical_pdd_zref
    else:
        raise click.BadParameter("clinical_pdd_zref must be a float")
    
    if isinstance(energy, int):
        safe["energy"] = energy
    else:
        raise click.BadParameter("energy must be an integer")
    
    if isinstance(fff, bool):
        safe["fff"] = fff
    else:
        raise click.BadParameter("fff must be a boolean")
    
    if isinstance(institution, str):
        safe["institution"] = institution
    else:
        raise click.BadParameter("institution must be a string")
    
    if isinstance(k_elec, float):
        safe["k_elec"] = k_elec
    else:
        raise click.BadParameter("k_elec must be a float")
    
    if isinstance(m_opposite, list) and len(m_opposite) == 3 and all(isinstance(x, float) for x in m_opposite):
        safe["m_opposite"] = tuple(m_opposite)
    elif isinstance(m_opposite, tuple) and len(m_opposite) == 3 and all(isinstance(x, float) for x in m_opposite):
        safe["m_opposite"] = m_opposite
    else:
        raise click.BadParameter("m_opposite must be a tuple of three floats")
    
    if isinstance(m_reference, list) and len(m_reference) == 3 and all(isinstance(x, float) for x in m_reference):
        safe["m_reference"] = tuple(m_reference)
    elif isinstance(m_reference, tuple) and len(m_reference) == 3 and all(isinstance(x, float) for x in m_reference):
        safe["m_reference"] = m_reference
    else:
        raise click.BadParameter("m_reference must be a tuple of three floats")
    
    if isinstance(m_reduced, list) and len(m_reduced) == 3 and all(isinstance(x, float) for x in m_reduced):
        safe["m_reduced"] = tuple(m_reduced)
    elif isinstance(m_reduced, tuple) and len(m_reduced) == 3 and all(isinstance(x, float) for x in m_reduced):
        safe["m_reduced"] = m_reduced
    else:
        raise click.BadParameter("m_reduced must be a tuple of three floats")
    
    if isinstance(measurement_date, str):
        safe["measurement_date"] = measurement_date
    else:
        raise click.BadParameter("measurement_date must be a string")
    
    if isinstance(mu, int):
        safe["mu"] = mu
    else:
        raise click.BadParameter("mu must be an integer")
    
    if isinstance(n_dw, float):
        safe["n_dw"] = n_dw
    else:
        raise click.BadParameter("n_dw must be a float")
    
    if isinstance(physicist, str):
        safe["physicist"] = physicist
    else:
        raise click.BadParameter("physicist must be a string")
    
    # TODO: there is a problem with reading a list or tuple with elements of different types inside a TOML file. The current solution is to read the pressure as a string and then parse it. This is not ideal, but it works.
    if isinstance(press, dict) and "value" in press and "unit" in press and isinstance(press["value"], float) and isinstance(press["unit"], str):
        safe["press"] = (press["value"], press["unit"])
    elif isinstance(press, tuple) and len(press) == 2 and isinstance(press[0], float) and isinstance(press[1], str):
        safe["press"] = press
    else:
        raise click.BadParameter("press must be a tuple of a float and a string")
    
    if isinstance(setup, str):
        safe["setup"] = setup
    else:
        raise click.BadParameter("setup must be a string")
    
    if isinstance(temp, float):
        safe["temp"] = temp
    else:
        raise click.BadParameter("temp must be a float")
    
    if isinstance(tissue_correction, float):
        safe["tissue_correction"] = tissue_correction
    else:
        raise click.BadParameter("tissue_correction must be a float")
    
    if isinstance(tpr2010, float):
        safe["tpr2010"] = tpr2010
    else:
        raise click.BadParameter("tpr2010 must be a float")
    
    if isinstance(unit, str):
        safe["unit"] = unit
    else:
        raise click.BadParameter("unit must be a string")
    
    if isinstance(voltage_reduced, int):
        safe["voltage_reduced"] = voltage_reduced
    else:
        raise click.BadParameter("voltage_reduced must be an integer")
    
    if isinstance(voltage_reference, int):
        safe["voltage_reference"] = voltage_reference
    else:
        raise click.BadParameter("voltage_reference must be an integer")
    
    if isinstance(notes, list) and all(isinstance(note, str) for note in notes):
        safe["notes"] = notes
    elif isinstance(notes, tuple) and all(isinstance(note, str) for note in notes):
        safe["notes"] = list(notes)
    else:
        raise click.BadParameter("notes must be a list of strings")
    
    # if isinstance(ref_temp, float):
    #     safe["ref_temp"] = ref_temp
    # else:
    #     raise click.BadParameter("ref_temp must be a float")
    
    # # Maybe not present
    # if isinstance(k_q_direct, float):
    #     safe["k_q_direct"] = k_q_direct
    # else:
    #     raise click.BadParameter("k_q_direct must be a float")

    # # Maybe not present
    # if isinstance(k_s, float):
    #     safe["k_s"] = k_s
    # else:
    #     raise click.BadParameter("k_s must be a float")

    # # Maybe not present
    # if isinstance(k_pol, float):
    #     safe["k_pol"] = k_pol
    # else:
    #     raise click.BadParameter("k_pol must be a float")

    #Check and apply conversion of pressure to kPa if needed.
    if safe["press"][1] == "kPa":
        press_kPa = safe["press"][0]
    elif safe["press"][1] == "mbar":
        press_kPa = pylinac.trs398.mbar2kPa(safe["press"][0])
    elif safe["press"][1] == "mmHg":
        press_kPa = pylinac.trs398.mmHg2kPa(safe["press"][0])
    else:
        raise click.BadParameter("Invalid pressure unit. Must be 'kPa', 'mbar', or 'mmHg'.")
    
    # Fusions
    # fusion = dict()
    # if safe["p_ion"] is not None:
    #     fusion["p_ion"] = safe["p_ion"]
    # else:
    #     fusion["p_ion"] = safe["k_s"]
    #     # fusion["p_ion"] = pylinac.calibration.trs398.p_ion(chamber=safe["chamber"], energy=safe["energy"])

    # trs398_calculator = pylinac.calibration.trs398.TRS398Photon(
    #     setup=safe["setup"],
    #     mu=safe["mu"],
    #     energy=safe["energy"],
    #     n_dw=safe["n_dw"],
    #     k_fgh = safe["k_q_direct"],
    #     k_s = safe["k_s"],
    #     k_pol = safe["k_pol"],
    #     temperature=safe["temp"],
    #     pressure=safe["press"],
    #     m_reference=safe["m_reference"],
    #     clinical_pdd_zref=safe["clinical_pdd_zref"],
    #     chamber=safe["chamber"],
    #     institution=safe["institution"],
    #     k_elec=safe["k_elec"],
    #     measurement_date=safe["measurement_date"],
    #     tissue_correction=safe["tissue_correction"],
    #     unit=safe["unit"],
    #     ref_temp=safe["ref_temp"]
    # )

    # trs398_calculator = TRS398Custom(
    #     chamber=safe["chamber"],
    #     clinical_pdd_zref=safe["clinical_pdd_zref"],
    #     energy=safe["energy"],
    #     fff=safe["fff"],
    #     institution=safe["institution"],
    #     k_elec=safe["k_elec"],
    #     m_opposite=safe["m_opposite"],
    #     m_reference=safe["m_reference"],
    #     m_reduced=safe["m_reduced"],
    #     measurement_date=safe["measurement_date"],
    #     mu=safe["mu"],
    #     n_dw=safe["n_dw"],
    #     physicist=physicist,
    #     press=press_kPa,
    #     setup=safe["setup"],
    #     temp=safe["temp"],
    #     tissue_correction=safe["tissue_correction"],
    #     tpr2010=safe["tpr2010"],
    #     unit=safe["unit"],
    #     voltage_reduced=safe["voltage_reduced"],
    #     voltage_reference=safe["voltage_reference"],
    #     ref_temp=safe["ref_temp"]
    # )

    buffer_tpr2010 = pylinac.calibration.tg51.tpr2010_from_pdd2010(pdd2010=safe["tpr2010"])

    trs398_calculator = pylinac.calibration.trs398.TRS398Photon(
        chamber=safe["chamber"],
        clinical_pdd_zref=safe["clinical_pdd_zref"],
        energy=safe["energy"],
        fff=safe["fff"],
        institution=safe["institution"],
        k_elec=safe["k_elec"],
        m_opposite=safe["m_opposite"],
        m_reference=safe["m_reference"],
        m_reduced=safe["m_reduced"],
        measurement_date=safe["measurement_date"],
        mu=safe["mu"],
        n_dw=safe["n_dw"],
        physicist=physicist,
        press=press_kPa,
        setup=safe["setup"],
        temp=safe["temp"],
        tissue_correction=safe["tissue_correction"],
        tpr2010=safe["tpr2010"],
        unit=safe["unit"],
        voltage_reduced=safe["voltage_reduced"],
        voltage_reference=safe["voltage_reference"]
    )

    trs398_calculator.publish_pdf(
        filename=str(safe["output"]),
        notes=safe["notes"],
        open_file=False
        )
    click.echo(f"Output file {safe['output']} created.")

    #Creating output file for further processing.
    output_debug_filename = f"calibration-calculatedValues-{safe['energy']}MV.csv"
    # output_debug_filename = f"{safe['output'].stem}_debug.csv"
    with open(output_debug_filename, "w", encoding="utf-8", newline="") as f:
        csvWriter_calibration = csv.writer(f, delimiter=";")
        csvWriter_calibration.writerow(["Quantity", "Unit", "Value-calculated"])
        csvWriter_calibration.writerow(["k_q", "", trs398_calculator.kq])
        csvWriter_calibration.writerow(["K-s", "", trs398_calculator.k_s])
        csvWriter_calibration.writerow(["K-pol", "", trs398_calculator.k_pol])
        csvWriter_calibration.writerow(["k_tp", "", trs398_calculator.k_tp])
        csvWriter_calibration.writerow(["D_ref", "Gy", trs398_calculator.dose_mu_zref])
        csvWriter_calibration.writerow(["D_max", "Gy", trs398_calculator.dose_mu_zmax])


    print(f"Debug output file {output_debug_filename} created.")

    sys.exit(0)

# generate-graph command
# @click.command()
# @click.argument('path', type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=pathlib.Path), required=True)
# @click.option("--config", type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=pathlib.Path), help="Path to config file.")
# @click.option('--output', type=click.Path(file_okay=True, dir_okay=False, path_type=pathlib.Path), help='Path to output file.')
# @click.option('--figsize', type=click.Tuple([int, int]), help='Figure size as a tuple (x, y)')
# @click.option('--marker', type=click.STRING, help='Marker style for the graph')
# @click.option('--linestyle', type=click.STRING, help='Line style for the graph')
# @click.option('--title', type=click.STRING, help='Title of the graph')
# @click.option('--grid', type=click.BOOL, help='Whether to show grid on the graph')
# def generate_graph(
#     path: pathlib.Path,
#     config: pathlib.Path,
#     output: pathlib.Path,
#     figsize: tuple[int, int],
#     marker: str,
#     linestyle: str,
#     title: str,
#     grid: bool):
#     """Generates a graph from a given CSV file."""
    
#     cfg = nel_calc.nel_aux.load_toml_file(config) if config else {}

#     # Load command configuration
#     output = nel_calc.nel_aux.resolve_option2(output, cfg, "generate-graph.output")
#     figsize = nel_calc.nel_aux.resolve_option2(figsize, cfg, "generate-graph.figsize")
#     marker = nel_calc.nel_aux.resolve_option2(marker, cfg, "generate-graph.marker")
#     linestyle = nel_calc.nel_aux.resolve_option2(linestyle, cfg, "generate-graph.linestyle")
#     title = nel_calc.nel_aux.resolve_option2(title, cfg, "generate-graph.title")
#     grid = nel_calc.nel_aux.resolve_option2(grid, cfg, "generate-graph.grid")

#     # Check types
#     safe = dict()
#     if isinstance(output, pathlib.Path):
#         safe["output"] = output
#     else:
#         raise click.BadParameter("output must be a path")

#     if figsize is isinstance(figsize, list) and len(figsize) == 2 and all(isinstance(x, int) for x in figsize):
#         safe["figsize"] = tuple(figsize)
#     if figsize is isinstance(figsize, tuple) and len(figsize) == 2 and all(isinstance(x, int) for x in figsize):
#         safe["figsize"] = figsize
#     else:
#         raise click.BadParameter("figsize must be a tuple of two numbers")

#     if marker is isinstance(marker, str):
#         safe["marker"] = marker
#     else:
#         raise click.BadParameter("marker must be a string")
    
#     if linestyle is isinstance(linestyle, str):
#         safe["linestyle"] = linestyle
#     else:
#         raise click.BadParameter("linestyle must be a string")
    
#     if title is isinstance(title, str):
#         safe["title"] = title
#     else:
#         raise click.BadParameter("title must be a string")
    
#     if grid is isinstance(grid, bool):
#         safe["grid"] = grid
#     else:
#         raise click.BadParameter("grid must be a boolean")

#     # Load data
#     df = pd.read_csv(path)

#     # Size of the figure
#     plt.figure(figsize=safe["figsize"])

#     # Graph style
#     plt.plot(df.iloc[:, 0], df.iloc[:, 1], marker=safe["marker"], linestyle=safe["linestyle"])
    
#     # Graph titles
#     headers = df.columns.tolist()
#     plt.xlabel(headers[0])
#     plt.ylabel(headers[1])
#     plt.title(safe["title"])
#     plt.grid(safe["grid"])
#     # Save the graph
#     plt.savefig(safe["output"])
#     plt.close()
#     click.echo(f"Graph saved as {safe['output']}")
#     sys.exit(0)

cli.add_command(copy_sample)
cli.add_command(create_image_planar)
#cli.add_command(create_calibration)
cli.add_command(analyze_preliminary)
cli.add_command(analyze_image_planar)
cli.add_command(generate_calibration_report)
# cli.add_command(generate_graph)

if __name__ == "__main__":
    cli()
    print(f"Program terminated.")