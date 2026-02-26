import sys
import json
import csv
import pathlib
import datetime

import pylinac.calibration.trs398
import pylinac.core.image_generator.layers
import pylinac
import click
import click_datetime
import pandas as pd
import matplotlib.pyplot as plt
plt.switch_backend('Agg')  # Use a non-interactive backend for matplotlib

import nel_calc.nel_config
import nel_calc.nel_aux
import nel_calc.customSim

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

#command to create a config file
@click.command()
@click.argument("filename", type=click.Path(file_okay=True, dir_okay=False), required=True)
def create_config(filename):
    """Create a config file."""    
    # Check if the file already exists.
    if pathlib.Path(filename).exists():
        raise click.BadParameter("File already exists. Please choose a different name or delete the existing file.")
    with open(filename, "w", encoding="utf-8") as configFile:
        json.dump(nel_calc.nel_config.default_config, configFile, indent=4)
        click.echo(f"Config file {filename} created.")
    
    sys.exit(0)

#command to create image for 2D profiling. OK2
@click.command()
@click.argument("filename", type=click.Path(file_okay=True, dir_okay=False), required=True)
@click.option("--config-new", type=click.Path(exists=True, file_okay=True), help="Config filename.")
@click.option("--field-size-mm", type=click.Tuple([click.FLOAT, click.FLOAT]), callback=validate_config_path_exclusive_option, help="Field size in mm.")
@click.option("--sigma-mm", type=click.FLOAT, callback=validate_config_path_exclusive_option, help="Sigma in mm for the Gaussian filter.")
@click.option("--gantry-angle", type=click.FLOAT, callback=validate_config_path_exclusive_option, help="Gantry angle in degrees.")
@click.option("--epid", type=str, callback=validate_config_path_exclusive_option, help="Name of the EPID that will be simulated.")
def create_image_planar(
    filename: str,
    config_new: str,
    field_size_mm: tuple,
    sigma_mm: float,
    gantry_angle: float,
    epid: str):
    """Create planar image for 2D profiling."""

    cfg = nel_calc.nel_aux.load_toml_file(config_new) if config_new else {}

    field_size_mm = nel_calc.nel_aux.resolve_option2(field_size_mm, cfg, "create-image-planar.field-size-mm")
    sigma_mm = nel_calc.nel_aux.resolve_option2(sigma_mm, cfg, "create-image-planar.sigma-mm")
    gantry_angle = nel_calc.nel_aux.resolve_option2(gantry_angle, cfg, "create-image-planar.gantry-angle")
    epid = nel_calc.nel_aux.resolve_option2(epid, cfg, "create-image-planar.epid")

    # Check types
    if not isinstance(field_size_mm, tuple) or len(field_size_mm) != 2:
        raise click.BadParameter("field-size-mm must be a tuple of two floats.")
    if not all(isinstance(x, (int, float)) for x in field_size_mm):
        raise click.BadParameter("field-size-mm must be a tuple of two floats.")

    if not isinstance(sigma_mm, (int, float)):
        raise click.BadParameter("sigma-mm must be a float.")

    if not isinstance(gantry_angle, (int, float)):
        raise click.BadParameter("gantry-angle must be a float.")

    #Load the appropiated epid class.
    if epid == "iViewGT":
        iViewGT0 = nel_calc.customSim.iViewGTImage()
    else:
        raise click.exceptions.BadParameter(f"Unknown EPID name for class instance: {epid}.")
    
    iViewGT0.add_layer(pylinac.core.image_generator.layers.FilteredFieldLayer(field_size_mm=field_size_mm))
    iViewGT0.add_layer(pylinac.core.image_generator.layers.GaussianFilterLayer(sigma_mm=sigma_mm))
    iViewGT0.generate_dicom(file_out_name=filename, gantry_angle=gantry_angle)

    click.echo("Sample images created.")
    sys.exit(0)

#create calibration command. OK
@click.command()
@click.argument("filename", type=click.Path(file_okay=True, dir_okay=False), required=True)
def create_calibration(filename: str):
    """Create a calibration file."""

    # Opening calibration file for writing.
    with open(filename, "w", encoding="utf-8") as calibrationFile:
        json.dump(nel_calc.nel_aux.calibration_data, calibrationFile, indent=4, ensure_ascii=False)
        click.echo(f"Calibration file {filename} created.")
    
    sys.exit(0)

#analyze-preliminary command. OK
@click.command()
@click.option("--config-new", type=click.Path(exists=True, file_okay=True), help="Config filename.")
@click.option("--input-dir", type=click.Path(exists=True, dir_okay=True), help="Path of input file directory.")
@click.option("--output-dir", type=click.Path(exists=True, dir_okay=True), help="Path of output file directory.")
@click.option("--input-preffix", type=click.STRING, help="Input fileName preffix.")
@click.option("--output-preffix", type=click.STRING, help="Output fileName preffix.")
@click.option("--filetype", type=click.STRING, help="FileType of the input and output files.")
@click.option("--summary", type=click.Path(exists=False, file_okay=True), help="FileName of summary file.")
@click.option("--default-basetypes", type=click.Tuple([click.STRING, click.STRING, click.STRING, click.STRING, click.STRING, click.STRING]), help="Default basetypes of the values in the columns of csv files.")
@click.option("--column-class", type=click.Tuple([click.STRING, click.STRING, click.STRING, click.STRING, click.STRING, click.STRING]), help="Class of the values in the columns of csv files.")
@click.option("--new-input-units", type=click.Tuple([click.STRING, click.STRING, click.STRING, click.STRING, click.STRING, click.STRING]), help="Units of the values in the columns of csv input file.")
@click.option("--old-output-units", type=click.Tuple([click.STRING, click.STRING, click.STRING, click.STRING, click.STRING, click.STRING]), help="Class of the values in the columns of csv output file.")
@click.option("--max-PTP", type=click.FLOAT, help="Maximum limit for PTP.")
def analyze_preliminary(config_new: str | None,
                        input_dir: str,
                        output_dir: str,
                        input_preffix: str,
                        output_preffix: str,
                        filetype: str,
                        summary: str | None,
                        default_basetypes: tuple[str],
                        column_class: tuple[str],
                        new_input_units: tuple[str],
                        old_output_units: tuple[str],
                        max_ptp: float):
    """Analyze calibration preliminary data about measurements."""

    cfg = nel_calc.nel_aux.load_toml_file(config_new) if config_new else {}

    input_dir = nel_calc.nel_aux.resolve_option2(input_dir, cfg, "analyze-preliminary.input-dir")
    output_dir = nel_calc.nel_aux.resolve_option2(output_dir, cfg, "analyze-preliminary.output-dir")
    input_preffix = nel_calc.nel_aux.resolve_option2(input_preffix, cfg, "analyze-preliminary.input-preffix")
    output_preffix = nel_calc.nel_aux.resolve_option2(output_preffix, cfg, "analyze-preliminary.output-preffix")
    filetype = nel_calc.nel_aux.resolve_option2(filetype, cfg, "analyze-preliminary.filetype")
    summary = nel_calc.nel_aux.resolve_option2(summary, cfg, "analyze-preliminary.summary")
    default_basetypes = nel_calc.nel_aux.resolve_option2(default_basetypes, cfg, "analyze-preliminary.default-basetypes")
    column_class = nel_calc.nel_aux.resolve_option2(column_class, cfg, "analyze-preliminary.column-class")
    new_input_units = nel_calc.nel_aux.resolve_option2(new_input_units, cfg, "analyze-preliminary.new-input-units")
    old_output_units = nel_calc.nel_aux.resolve_option2(old_output_units, cfg, "analyze-preliminary.new-output-units")
    max_ptp = nel_calc.nel_aux.resolve_option2(max_ptp, cfg, "analyze-preliminary.max-PTP")

    # Check types
    if not isinstance(input_dir, str):
        raise click.BadParameter("input-dir must be a string.")
    if not isinstance(output_dir, str):
        raise click.BadParameter("output-dir must be a string.")
    if not isinstance(input_preffix, str):
        raise click.BadParameter("input-preffix must be a string.")
    if not isinstance(output_preffix, str):
        raise click.BadParameter("output-preffix must be a string.")
    if not isinstance(filetype, str):
        raise click.BadParameter("filetype must be a string.")
    if not isinstance(summary, str | None):
        raise click.BadParameter("summary must be a string or None.")

    if not isinstance(default_basetypes, tuple):
        raise click.BadParameter("default-basetypes must be a tuple of strings.")
    if not isinstance(column_class, tuple):
        raise click.BadParameter("column-class must be a tuple of strings.")
    if not isinstance(new_input_units, tuple):
        raise click.BadParameter("new-input-units must be a tuple of strings.")
    if not isinstance(old_output_units, tuple):
        raise click.BadParameter("old-output-units must be a tuple of strings.")

    # Base types for the quantities.
    default_baseTypes = dict(zip(column_class, default_basetypes)) # For new config file.

    #Obtaining the units that will be used in the output files.
    
    new_input_units = dict(zip(column_class, new_input_units)) # For new config file.

    old_output_units = dict(zip(column_class, old_output_units)) # For new config file.

    # Getting the input filenames.
    filenames = list()
    for file in pathlib.Path(input_dir).iterdir():
        if file.is_file():
            #if file.name.startswith(input_preffix) and file.suffix == input_suffix:
            if file.name.startswith(input_preffix) and file.suffix == filetype:
                filenames.append(str(file.resolve()))
    if len(filenames) == 0:
        print("Cannot find input files.")
        return
        #raise FileNotFoundError

    # from files to rawMeasurement_list_tries
    # Read the files and convert them to rawMeasurement_list_tries
    rawMeasurement_list_tries = list()
    for filename in filenames:    
        with open(filename, "r", encoding = "utf-8") as csvFile:
            csvDictReader = csv.DictReader(csvFile)
            input_header = csvDictReader.fieldnames # Getting the current header in first line
            old_input_units = next(csvDictReader) # Getting the units in second line
            rawMeasurement_list = list()
            for row in csvDictReader: # Getting the values
                rawMeasurement = nel_calc.nel_aux.Row2Measurement(row=row, header=input_header, baseTypes=default_baseTypes)
                rawMeasurement_list.append(rawMeasurement.copy())
        rawMeasurement_list_tries.append(rawMeasurement_list.copy())

    # Changing bounds of k_tp to avoid BoundError
    # Value are the just as closest posible to default values
    # pylinac.calibration.trs398.MAX_PTP = 1.2
    pylinac.calibration.trs398.MAX_PTP = max_ptp

    # from rawMeasurement_list_tries to measurement_list_tries
    # Convert the units and calculate the corrected charge and the temperature-pressure correction factor
    measurement_list_tries = list()

    for rawMeasurement_list in rawMeasurement_list_tries:
        measurement_list = list()
        for rawMeasurement in rawMeasurement_list:
            measurement = nel_calc.nel_aux.ConvertMeasurement(rawMeasurement=rawMeasurement, oldUnits=old_input_units, newUnits=new_input_units) #Conversion of units
            measurement["k_TP"] = pylinac.calibration.trs398.k_tp(temp = measurement["T"], press = measurement["P"])
            measurement["m_corrected"] = pylinac.calibration.trs398.m_corrected(m_reference=measurement["m"],
                                                            k_tp=measurement["k_TP"],
                                                            k_elec=1,
                                                            k_pol=1,
                                                            k_s=1)
            measurement_list.append(measurement.copy())
        measurement_list_tries.append(measurement_list.copy())

    # Calculate the average, standard deviation and expected value of m_corrected
    # from measurement_list_tries to m_corrected_average, m_corrected_stdDev and m_corrected_expectedValue
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

    m_corrected_average = nel_calc.nel_aux.FindAverage(m_corrected_averageList)
    m_corrected_stdDev = nel_calc.nel_aux.FindAverage(m_corrected_stdDevList)
    m_corrected_expectedValue = nel_calc.nel_aux.FindAverage(m_corrected_expectedValueList)
    
    print("General statistical quantities (Measurements 1, 2, 3):")
    print(f"Average: {m_corrected_average: .3f}")
    print(f"Standard deviation: {m_corrected_stdDev: .3f}")
    print(f"Expected value: {m_corrected_expectedValue: .3f}")

    # Creates output files.
    # .csv
    i = 0
    for i in range(len(measurement_list_tries)):
        filePath = filenames[i]
        dirs = pathlib.Path(filePath).parent
        stem = pathlib.Path(filePath).stem
        suffix = pathlib.Path(filePath).suffix
        output_filename = f"{output_preffix}{i}{suffix}"
        output_filePath = pathlib.Path(output_dir) / output_filename
        
        with open(output_filePath, "w", encoding="utf-8", newline='') as csvFile:
            csvWriter = csv.DictWriter(csvFile, fieldnames=column_class)
            csvWriter.writeheader()
            csvWriter.writerow(old_output_units)
            for measurement in measurement_list:
                csvWriter.writerow(measurement)
            print(f"Output file {output_filename} created.")
            i = i + 1

    # Create the summary file.
    # .json
    output_quantities = dict()
    output_quantities["m_corrected_average"] = m_corrected_average
    output_quantities["m_corrected_stdDev"] = m_corrected_stdDev
    output_quantities["m_corrected_expectedValue"] = m_corrected_expectedValue
    summaryPath = pathlib.Path(output_dir) / summary
    with open(summaryPath, "w", encoding="utf-8") as summaryFile:
        json.dump(output_quantities, summaryFile, indent=4)
        print(f"Output file {summary} created.")

    click.echo("Preliminary analysis done.")
    sys.exit(0)

# analyze-image-planar. OK
@click.command()
@click.argument("filename", type=click.Path(file_okay=True, dir_okay=False), required=True)
@click.option("--protocol", type=click.STRING, callback=validate_config_path_exclusive_option, help="Protocol used for calculations.")
@click.option("--output", type=click.Path(file_okay=True, dir_okay=False), callback=validate_config_path_exclusive_option, help="Output analysis filename.")
# @click.option("--config", type=click.Path(exists=True, file_okay=True), callback=validate_config_path_exclusive_option, help="Config filename.")
@click.option("--config-new", type=click.Path(exists=True, file_okay=True), help="Config filename.")
def analyze_image_planar(
    filename: str,
    config_new: str | None,
    protocol: str | None,
    output: str | None
    ):
    """Analyze field images."""

    cfg = nel_calc.nel_aux.load_toml_file(config_new) if config_new else {}

    protocol = nel_calc.nel_aux.resolve_option2(protocol, cfg, "analyze-image-planar.protocol", required=True)
    output = nel_calc.nel_aux.resolve_option2(output, cfg, "analyze-image-planar.output", required=True)

    # Check types
    if not isinstance(protocol, str | None):
        raise click.BadParameter("protocol must be a string or None.")
    if not isinstance(output, str | None):
        raise click.BadParameter("output must be a string or None.")

    # Load input files: field images
    field_analysis = pylinac.FieldAnalysis(path=filename)
    
    # Picking the asked protocol.
    if protocol == "elekta":
        protocol_class = pylinac.Protocol.ELEKTA
    elif protocol == "varian":
        protocol_class = pylinac.Protocol.VARIAN
    elif protocol == "siemens":
        protocol_class = pylinac.Protocol.SIEMENS
    elif protocol == None:
        protocol_class = None
    else:
        raise click.exceptions.BadParameter(f"Unknown protocol: {protocol}.")
    
    # performing analysis
    field_analysis.analyze(protocol=protocol_class)
    field_analysis.plot_analyzed_image()
    field_analysis.publish_pdf(filename=output)
    
    click.echo(f"2D images analyzed.")
    sys.exit(0)

# generate-calibration-report. OK
@click.command()
@click.argument("filename", type=click.Path(file_okay=True, dir_okay=False), required=True)
@click.option("--config-new", type=click.Path(exists=True, file_okay=True), help="Config filename.")
@click.option("--output", type=click.Path(file_okay=True, dir_okay=False), help="Output filename.")
@click.option("--chamber", type=click.STRING, help="Chamber model.")
@click.option("--clinical-pdd-zref", type=click.FLOAT, help="Clinical PDD Zref.")
@click.option("--energy", type=click.FLOAT, help="Energy.")
@click.option("--fff", type=click.BOOL, help="FFF.")
@click.option("--institution", type=click.STRING, help="Institution.")
@click.option("--k-elec", type=click.FLOAT, help="K-electron.")
@click.option("--m-opposite", type=click.Tuple([click.FLOAT, click.FLOAT, click.FLOAT]), help="M opposite.")
@click.option("--m-reference", type=click.Tuple([click.FLOAT, click.FLOAT, click.FLOAT]), help="M reference.")
@click.option("--m-reduced", type=click.Tuple([click.FLOAT, click.FLOAT, click.FLOAT]), help="M reduced.")
@click.option("--measurement-date", type=click_datetime.Datetime(format="%Y-%m-%d"), help="Date of the measurement.")
@click.option("--mu", type=click.FLOAT, help="MU.")
@click.option("--n-dw", type=click.FLOAT, help="N_Dw.")
@click.option("--physicist", type=click.STRING, help="Physicist.")
@click.option("--press", type=click.FLOAT, help="Pressure.")
@click.option("--setup", type=click.STRING, help="Experimental setup.")
@click.option("--temp", type=click.FLOAT, help="Temperature.")
@click.option("--tissue-correction", type=click.FLOAT, help="Tissue correction.")
@click.option("--tpr2010", type=click.FLOAT, help="TPR2010.")
@click.option("--unit", type=click.STRING, help="Unit.")
@click.option("--voltage-reduced", type=click.FLOAT, help="Voltage reduced.")
@click.option("--voltage-reference", type=click.FLOAT, help="Voltage reference.")
@click.option("--notes", type=click.STRING, help="Notes.")
# @click.option("--config", type=click.Path(exists=True, file_okay=True), help="Config filename.")
def generate_calibration_report(
    filename: str,
    config_new: str,
    output: str,
    chamber: str,
    clinical_pdd_zref: float,
    energy: float,
    fff: bool,
    institution: str,
    k_elec: float,
    m_opposite: tuple[float, float, float],
    m_reference: tuple[float, float, float],
    m_reduced: tuple[float, float, float],
    measurement_date: datetime.datetime,
    mu: float,
    n_dw: float,
    physicist: str,
    press: float,
    setup: str,
    temp: float,
    tissue_correction: float,
    tpr2010: float,
    unit: str,
    voltage_reduced: float,
    voltage_reference: float,
    notes: str
):
    """Generate report about calibration."""

    cfg = nel_calc.nel_aux.load_toml_file(config_new) if config_new else {}

    output = nel_calc.nel_aux.resolve_option2(output, cfg, "generate-calibration-report.output")
    chamber = nel_calc.nel_aux.resolve_option2(chamber, cfg, "generate-calibration-report.chamber")
    clinical_pdd_zref = nel_calc.nel_aux.resolve_option2(clinical_pdd_zref, cfg, "generate-calibration-report.clinical-pdd-zref")
    energy = nel_calc.nel_aux.resolve_option2(energy, cfg, "generate-calibration-report.energy")
    fff = nel_calc.nel_aux.resolve_option2(fff, cfg, "generate-calibration-report.fff")
    institution = nel_calc.nel_aux.resolve_option2(institution, cfg, "generate-calibration-report.institution")
    k_elec = nel_calc.nel_aux.resolve_option2(k_elec, cfg,  "generate-calibration-report.k-elec")
    m_opposite = nel_calc.nel_aux.resolve_option2(m_opposite, cfg, "generate-calibration-report.m-opposite")
    m_reference = nel_calc.nel_aux.resolve_option2(m_reference, cfg, "generate-calibration-report.m-reference")
    m_reduced = nel_calc.nel_aux.resolve_option2(m_reduced, cfg, "generate-calibration-report.m-reduced")
    measurement_date = nel_calc.nel_aux.resolve_option2(measurement_date, cfg, "generate-calibration-report.measurement-date")
    mu = nel_calc.nel_aux.resolve_option2(mu, cfg, "generate-calibration-report.mu")
    n_dw = nel_calc.nel_aux.resolve_option2(n_dw, cfg, "generate-calibration-report.n-dw")
    physicist = nel_calc.nel_aux.resolve_option2(physicist, cfg, "generate-calibration-report.physicist")
    press = nel_calc.nel_aux.resolve_option2(press, cfg, "generate-calibration-report.press")
    setup = nel_calc.nel_aux.resolve_option2(setup, cfg, "generate-calibration-report.setup")
    temp = nel_calc.nel_aux.resolve_option2(temp, cfg, "generate-calibration-report.temp")
    tissue_correction = nel_calc.nel_aux.resolve_option2(tissue_correction, cfg, "generate-calibration-report.tissue-correction")
    tpr2010 = nel_calc.nel_aux.resolve_option2(tpr2010, cfg, "generate-calibration-report.tpr2010")
    unit = nel_calc.nel_aux.resolve_option2(unit, cfg, "generate-calibration-report.unit")
    voltage_reduced = nel_calc.nel_aux.resolve_option2(voltage_reduced, cfg, "generate-calibration-report.voltage-reduced")
    voltage_reference = nel_calc.nel_aux.resolve_option2(voltage_reference, cfg, "generate-calibration-report.voltage-reference")
    notes = nel_calc.nel_aux.resolve_option2(notes, cfg, "generate-calibration-report.notes")
    
    # Check types
    if not isinstance(output, str):
        raise click.BadParameter("output must be a string")
    if not isinstance(chamber, str):
        raise click.BadParameter("chamber must be a string")
    if not isinstance(clinical_pdd_zref, (int, float)):
        raise click.BadParameter("clinical_pdd_zref must be a number")
    if not isinstance(energy, (int, float)):
        raise click.BadParameter("energy must be a number")
    if not isinstance(fff, bool):
        raise click.BadParameter("fff must be a boolean")
    if not isinstance(institution, str):
        raise click.BadParameter("institution must be a string")
    if not isinstance(k_elec, (int, float)):
        raise click.BadParameter("k_elec must be a number")
    if not (isinstance(m_opposite, (list, tuple)) and len(m_opposite) == 3 and all(isinstance(x, (int, float)) for x in m_opposite)):
        raise click.BadParameter("m_opposite must be a list or tuple of three numbers")
    if not (isinstance(m_reference, (list, tuple)) and len(m_reference) == 3 and all(isinstance(x, (int, float)) for x in m_reference)):
        raise click.BadParameter("m_reference must be a list or tuple of three numbers")
    if not (isinstance(m_reduced, (list, tuple)) and len(m_reduced) == 3 and all(isinstance(x, (int, float)) for x in m_reduced)):
        raise click.BadParameter("m_reduced must be a list or tuple of three numbers")
    if not isinstance(measurement_date, datetime.date):
        raise click.BadParameter("measurement_date must be a date")
    if not isinstance(mu, (int, float)):
        raise click.BadParameter("mu must be a number")
    if not isinstance(n_dw, (int, float)):
        raise click.BadParameter("n_dw must be a number")
    if not isinstance(physicist, str):
        raise click.BadParameter("physicist must be a string")
    if not isinstance(press, (int, float)):
        raise click.BadParameter("press must be a number")
    if not isinstance(setup, str):
        raise click.BadParameter("setup must be a string")
    if not isinstance(temp, (int, float)):
        raise click.BadParameter("temp must be a number")
    if not isinstance(tissue_correction, (int, float)):
        raise click.BadParameter("tissue_correction must be a number")
    if not isinstance(tpr2010, (int, float)):
        raise click.BadParameter("tpr2010 must be a number")
    if not isinstance(unit, str):
        raise click.BadParameter("unit must be a string")
    if not isinstance(voltage_reduced, (int, float)):
        raise click.BadParameter("voltage_reduced must be a number")
    if not isinstance(voltage_reference, (int, float)):
        raise click.BadParameter("voltage_reference must be a number")
    if not isinstance(notes, str):
        raise click.BadParameter("notes must be a string")

    # Load the input file.
    with open(filename, "r", encoding = "utf-8") as inputFile:
        inputJSON = json.load(inputFile)
        
    trs398_calculator = pylinac.calibration.trs398.TRS398Photon(
        chamber=inputJSON["chamber"],
        clinical_pdd_zref=inputJSON["clinical_pdd_zref"],
        energy=inputJSON["energy"],
        fff=inputJSON["fff"],
        institution=inputJSON["institution"],
        k_elec=inputJSON["k_elec"],
        m_opposite=inputJSON["m_opposite"],
        m_reference=inputJSON["m_reference"],
        m_reduced=inputJSON["m_reduced"],
        measurement_date=inputJSON["measurement_date"],
        mu=inputJSON["mu"],
        n_dw=inputJSON["n_dw"],
        physicist=inputJSON["physicist"],
        press=inputJSON["press"],
        setup=inputJSON["setup"],
        temp=inputJSON["temp"],
        tissue_correction=inputJSON["tissue_correction"],
        tpr2010=inputJSON["tpr2010"],
        unit=inputJSON["unit"],
        voltage_reduced=inputJSON["voltage_reduced"],
        voltage_reference=inputJSON["voltage_reference"]
    )

    trs398_calculator.publish_pdf(
        filename=output,
        notes=inputJSON["notes"],
        open_file=False
        )
    click.echo(f"Output file {output} created.")
    sys.exit(0)

# generate-graph command. OK
@click.command()
@click.argument('csv_file', type=click.Path(exists=True), required=True)
@click.option("--config-new", type=click.Path(exists=True, file_okay=True), help="Config filename.")
@click.option('--output', type=click.Path(exists=True, file_okay=True), help='Filename to save the graph')
@click.option('--figsize', type=click.Tuple([int, int]), help='Figure size as a tuple (x, y)')
@click.option('--marker', type=click.STRING, help='Marker style for the graph')
@click.option('--linestyle', type=click.STRING, help='Line style for the graph')
@click.option('--title', type=click.STRING, help='Title of the graph')
@click.option('--grid', type=click.BOOL, help='Whether to show grid on the graph')
def generate_graph(
    csv_file: str,
    config_new: str | None,
    output: str,
    figsize: tuple[int, int] | None,
    marker: str,
    linestyle: str,
    title: str,
    grid: bool):
    """Generates a graph from a given CSV file."""
    
    cfg = nel_calc.nel_aux.load_toml_file(config_new) if config_new else {}

    # Load command configuration
    output = nel_calc.nel_aux.resolve_option2(output, cfg, "generate-graph.output")
    figsize = nel_calc.nel_aux.resolve_option2(figsize, cfg, "generate-graph.figsize")
    marker = nel_calc.nel_aux.resolve_option2(marker, cfg, "generate-graph.marker")
    linestyle = nel_calc.nel_aux.resolve_option2(linestyle, cfg, "generate-graph.linestyle")
    title = nel_calc.nel_aux.resolve_option2(title, cfg, "generate-graph.title")
    grid = nel_calc.nel_aux.resolve_option2(grid, cfg, "generate-graph.grid")

    # Check types
    if not isinstance(output, str):
        raise click.BadParameter("output must be a string")
    
    if figsize is not None and not isinstance(figsize, (list, tuple)) or len(figsize) != 2:
        raise click.BadParameter("figsize must be a list or tuple of length 2")
    if isinstance(figsize, list):
        figsize = tuple(figsize)
    if figsize is not None:
        for i in range(2):
            if not isinstance(figsize[i], (int, float)):
                raise click.BadParameter("figsize values must be numbers")

    # marker should be a string
    if marker is not None and not isinstance(marker, str):
        raise click.BadParameter("marker must be a string")
    
    # linestyle should be a string
    if linestyle is not None and not isinstance(linestyle, str):
        raise click.BadParameter("linestyle must be a string")
    
    # title should be a string
    if title is not None and not isinstance(title, str):
        raise click.BadParameter("title must be a string")
    
    # grid should be a boolean
    if grid is not None and not isinstance(grid, bool):
        raise click.BadParameter("grid must be a boolean")

    # Load data
    df = pd.read_csv(csv_file)

    # Size of the figure
    plt.figure(figsize=figsize)

    # Graph style
    plt.plot(df.iloc[:, 0], df.iloc[:, 1], marker=marker, linestyle=linestyle)
    
    # Graph titles
    headers = df.columns.tolist()
    plt.xlabel(headers[0])
    plt.ylabel(headers[1])
    plt.title(title)
    plt.grid(grid)
    # Save the graph
    plt.savefig(output)
    plt.close()
    click.echo(f"Graph saved as {output}")
    sys.exit(0)

cli.add_command(create_config)
cli.add_command(create_image_planar)
cli.add_command(create_calibration)
cli.add_command(analyze_preliminary)
cli.add_command(analyze_image_planar)
cli.add_command(generate_calibration_report)
cli.add_command(generate_graph)

if __name__ == "__main__":
    cli()
    print(f"Program terminated.")