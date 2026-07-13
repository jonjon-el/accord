import pylinac.calibration.trs398
import pylinac.calibration.tg51
import pylinac.core.image_generator.layers
import pylinac
print(f"Pylinac version: {pylinac.__version__}")
pylinac_min_version = "3.43.2"
if pylinac.__version__ < pylinac_min_version:
    raise ImportError(f"Pylinac version must be at least {pylinac_min_version}.")

import click # for creating the CLI. # TODO: evaluate if using Typer instead of Click is better for this project.
import numpy as np # for calculating statistical quantities and uncertainties. # TODO: migrate from using csv to pandas and numpy
import matplotlib
matplotlib.use("Agg") # for plotting the analyzed images without needing a display.
import pydantic # for validating the parameters of the commands.

import json # output files and summary file are in json format
import tomllib # config files and devices specifications files are in toml format.
import csv # preliminary data are in csv format.
import sys
import pathlib
import importlib.resources

import accord.core.nel_aux
import accord.core.customSim
import accord.core.metrology
import accord.core.corrections
import accord.core.models.params

separator = {
    "cli": "-",
    "file": "_"
}


@click.group(invoke_without_command=True)
@click.version_option("0.2.0", prog_name="accord")
@click.option("--config", type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=pathlib.Path), is_eager=True, expose_value=True, help="Path to config file.")
#@click.option("--verbose", is_flag=True, help="Enable verbose output.")
@click.option("--generate-sample-files", type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=pathlib.Path), help="Generate sample file at the specified path.")
@click.option("--file-class", type=click.Choice(["config", "calibration", "preliminary", "devices", "all"]), help="Class of sample file to copy. Required if --generate-sample-files is specified.")
@click.pass_context
def main(ctx, **kwargs):
    """Main command line interface for the program."""
    # Check for incompatible options.
    if kwargs["config"] and (kwargs["generate_sample_files"] or kwargs["file_class"]):
        raise click.ClickException("Cannot specify --config and --generate-sample-files or --file-class at the same time.")

    if kwargs["generate_sample_files"] and not kwargs["file_class"]:
        raise click.ClickException("Must specify --file-class when using --generate-sample-files.")
    
    if kwargs["file_class"] and not kwargs["generate_sample_files"]:
        raise click.ClickException("Must specify --generate-sample-files when using --file-class.")

    # If generate sample files and file class are specified, copy the sample files and exit.
    if kwargs["generate_sample_files"] and kwargs["file_class"]:
        try:
            if kwargs["file_class"] == "all":
                for file_class in ["config", "calibration", "preliminary", "devices"]:
                    accord.core.nel_aux.copy_sample_files(kwargs["generate_sample_files"], file_class)
                    click.echo(f"Sample files of class '{file_class}' copied to {kwargs['generate_sample_files']}")
            else:
                accord.core.nel_aux.copy_sample_files(kwargs["generate_sample_files"], kwargs["file_class"])
                click.echo(f"Sample files of class '{kwargs['file_class']}' copied to {kwargs['generate_sample_files']}")
        except FileExistsError:
            click.echo(f"File already exists at {kwargs['generate_sample_files']}")
        except ValueError as e:
            click.echo(str(e))
        except Exception as e:
            click.echo(f"An error occurred while copying sample files of class '{file_class}': {str(e)}")    
        sys.exit(0)

    # If there are no subcomannd and not generating files then show the help message and exit.
    if ctx.invoked_subcommand is None and not kwargs["generate_sample_files"]:
        click.echo(ctx.get_help())
        sys.exit(0)

    # If config file is specified, load the config file and store the config data in the context object for use in the subcommands.
    ctx.ensure_object(dict)
    config_path = kwargs["config"]

    if config_path:

        try:
            with open(config_path, "rb") as f:
                config_data = tomllib.load(f)

            config_section = config_data.get(ctx.invoked_subcommand, {}) or config_data.get(ctx.invoked_subcommand.replace(separator["cli"], separator["file"]), {})
            config_section_normalized = {k.replace(separator["cli"], separator["file"]): v for k, v in config_section.items()}
            ctx.obj.update(config_section_normalized)

        except Exception as e:
            raise click.ClickException(f"Error loading config file: {e}")
    
    

#copy a sample file to a given location.
# @click.command()
# @click.argument("path", type=click.Path(file_okay=True, dir_okay=True, path_type=pathlib.Path), required=True)
# @click.option("--file-class", type=click.Choice(["config", "calibration", "preliminary", "devices"]), required=True, help="Class of sample file to copy.")
# def create_sample_file(path: pathlib.Path, file_class: str):
#     """Copy a sample file."""

#     accord.core.nel_aux.copy_sample_files(path, file_class)

#     sys.exit(0)

#create image for 2D profiling.
@click.command()
@click.argument("path", type=click.Path(file_okay=True, dir_okay=False, path_type=pathlib.Path), required=True)
@click.option("--field-size-mm", type=click.Tuple([click.FLOAT, click.FLOAT]), help="Field size in mm.")
@click.option("--sigma-mm", type=click.FLOAT, help="Sigma in mm for the Gaussian filter.")
@click.option("--gantry-angle", type=click.FLOAT, help="Gantry angle in degrees.")
@click.option("--epid", type=click.STRING, help="Name of the EPID that will be simulated.")
@click.pass_context
def create_image_planar(ctx: click.Context, **kwargs: dict):
    """Create planar image for 2D profiling."""

    valid_kwargs = {k: v for k, v in kwargs.items() if v is not None and (not isinstance(v, (list, tuple)) or len(v) > 0)}

    config_to_pydantic = {**ctx.obj, **valid_kwargs}

    # Check with Pydantic that the options have the correct types and values.
    try:
        safe_params = accord.core.models.params.CreateImagePlanar.model_validate(config_to_pydantic)
        
    except pydantic.ValidationError as e:
        # Extracting only the first error to not overwhelm the user with a long list of errors.
        # The error message is more user-friendly than the default Pydantic error message.
        error_info = e.errors()[0]
        field = ".".join(str(loc) for loc in error_info['loc'])
        message = error_info['msg']
        
        # Click exception
        raise click.ClickException(
            f"Pydantic Error in configuration ('{field}'): {message}"
        )

    #Load the appropiated epid class.
    if safe_params.epid == "iViewGT":
        iViewGT0 = accord.core.customSim.iViewGTImage()
    else:
        raise click.exceptions.BadParameter(f"Unknown EPID name for class instance: {safe_params.epid}.")
    
    iViewGT0.add_layer(pylinac.core.image_generator.layers.FilteredFieldLayer(field_size_mm=safe_params.field_size_mm))
    iViewGT0.add_layer(pylinac.core.image_generator.layers.GaussianFilterLayer(sigma_mm=safe_params.sigma_mm))
    iViewGT0.generate_dicom(file_out_name=str(safe_params.path), gantry_angle=safe_params.gantry_angle)

    click.echo("Sample images created.")
    sys.exit(0)

# analyze the preliminary data: calculate uncertainty of termometer, barometer and the stability of the electrometer across measurements.
@click.command()
@click.option("--summary", type=click.Path(file_okay=True, dir_okay=False, path_type=pathlib.Path), help="Path to summary file.")
@click.option("--devices", type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=pathlib.Path), help="File with specifications of devices used in the measure.")
@click.option("--input-dir", type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=pathlib.Path), help="Path of input file directory.")
@click.option("--output-dir", type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=pathlib.Path), help="Path of output file directory.")
@click.option("--input-preffix", type=click.STRING, help="Input fileName preffix.")
@click.option("--output-preffix", type=click.STRING, help="Output fileName preffix.")
@click.option("--filetype", type=click.STRING, help="FileType of the input and output files.")
@click.option("--max-ptp", type=click.FLOAT, help="Maximum limit for PTP.")
@click.option("--ref-temp", type=click.FLOAT, help="Reference temperature for k_TP calculation.")
@click.option("--k", type=click.INT, help="Coverage factor for calculating expanded uncertainty using normal distribution.")
@click.pass_context
def analyze_preliminary(ctx: click.Context, **kwargs: dict):
    """Analyze calibration preliminary data about measurements."""

    valid_kwargs = {k: v for k, v in kwargs.items() if v is not None and (not isinstance(v, (list, tuple)) or len(v) > 0)}

    config_to_pydantic = {**ctx.obj, **valid_kwargs}

    # Check with Pydantic that the options have the correct types and values.
    try:
        safe_params = accord.core.models.params.PreliminaryAnalysisParams.model_validate(config_to_pydantic)
        
    except pydantic.ValidationError as e:
        # Extracting only the first error to not overwhelm the user with a long list of errors.
        # The error message is more user-friendly than the default Pydantic error message.
        error_info = e.errors()[0]
        field = ".".join(str(loc) for loc in error_info['loc'])
        message = error_info['msg']
        
        # Click exception
        raise click.ClickException(
            f"Pydantic Error in configuration ('{field}'): {message}"
        )
    

    ## from data files to tables of values with the appropiate base types.

    # Loading file formats.
    # The order of the columns on input files are specified in a row of the input file itself.
    # The order of the columns on output files are specified in the file formats file.
    
    fileFormats_traversable = importlib.resources.files("accord").joinpath("formats/fileFormats.json")
    
    try:
        with fileFormats_traversable.open("r", encoding="utf-8") as fileFormatsFile:
            fileFormatsData = json.load(fileFormatsFile)
    except FileNotFoundError:
        raise click.ClickException(f"File formats file not found in {fileFormats_traversable}.")
    except json.JSONDecodeError:
        raise click.ClickException(f"Invalid JSON in file formats file {fileFormats_traversable}.")

    # Getting the input filenames.
    filepaths = list()
    for file in pathlib.Path(safe_params.input_dir).iterdir():
        if file.is_file():
            if file.name.startswith(safe_params.input_preffix) and file.suffix == f".{safe_params.filetype}":
                filepaths.append(str(file.resolve()))
    if len(filepaths) == 0:
        raise FileNotFoundError("Cannot find input files.")

    # Loading quantities data.
    quantities_traversable = importlib.resources.files("accord").joinpath("formats/quantities.json")
    try:
        with quantities_traversable.open("r", encoding="utf-8") as quantitiesFile:
            quantitiesData = json.load(quantitiesFile)
    except FileNotFoundError:
        raise click.ClickException(f"Quantities file not found in {quantities_traversable}.")
    except json.JSONDecodeError:
        raise click.ClickException(f"Invalid JSON in quantities file {quantities_traversable}.")

    # Read the files and convert them to rawMeasurement_list_tries
    input_preliminary_column_separator = fileFormatsData["input_preliminary"]["column_delimiter"]

    rawMeasurement_list_tries = list()
    for filepath in filepaths:    
        with open(filepath, "r", encoding = "utf-8") as csvFile:
            csvDictReader = csv.DictReader(csvFile, delimiter=input_preliminary_column_separator)
            input_preliminary_quantities = csvDictReader.fieldnames # Getting the current header in first line
            input_preliminary_units = next(csvDictReader) # Getting the units in second line. Try deleting for specify in config file.
            rawMeasurement_list = list()
            for row in csvDictReader: # Getting the values
                rawMeasurement = accord.core.nel_aux.Row2Measurement2(row=row, quantities=quantitiesData)
                rawMeasurement_list.append(rawMeasurement.copy())
        rawMeasurement_list_tries.append(rawMeasurement_list.copy())

    ## from tables of values to tables of values with the appropiate units and the new calculated quantities.

    # Changing bounds of k_tp to avoid BoundError
    # Value are the just as closest posible to default values
    # TODO: evaluate if changing the bounds of k_tp is the best way to avoid the BoundError or if it is better to catch the error and set k_tp to the closest bound value.
    # TODO: find an explanation of why the default values of k_tp are so far from the calculated values for the measurements in this preliminary analysis. This may be due to the fact that the default values of k_tp are for a reference temperature of 20 degrees Celsius and a reference pressure of 101.325 kPa, while the measurements in this preliminary analysis may have been taken at different temperatures and pressures.
    # If this is the case, it may be better to set the default values of k_tp to the expected values for the measurements in this preliminary analysis, rather than changing the bounds of k_tp.
    pylinac.calibration.trs398.MAX_PTP = safe_params.max_ptp

    # Convert the units and calculate the corrected charge and the temperature-pressure correction factor
    measurement_list_tries = list()

    for rawMeasurement_list in rawMeasurement_list_tries:
        measurement_list = list()
        for rawMeasurement in rawMeasurement_list:
            measurement = accord.core.nel_aux.Convert_measurement_to_pylinac_units(measurement=rawMeasurement, oldUnits=input_preliminary_units)
            measurement["k_TP"] = pylinac.calibration.trs398.k_tp(temp = measurement["T"], press = measurement["P"], ref_temp=safe_params.ref_temp) # Calculation of k_TP with the reference temperature specified by the user.
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
        m_corrected_average_item = accord.core.nel_aux.FindAverage(m_corrected_list)
        m_corrected_averageList.append(m_corrected_average_item)

        # Calculate the standard deviation of m_corrected
        m_corrected_stdDev_item = accord.core.nel_aux.FindStdDev(m_corrected_list)
        m_corrected_stdDevList.append(m_corrected_stdDev_item)

        # Calculate the expected value of m_corrected
        m_corrected_expectedValue_item = accord.core.nel_aux.FindExpectedValue(m_corrected_list)
        m_corrected_expectedValueList.append(m_corrected_expectedValue_item)
    
    ## Calculating uncertainties.

    # Device specifications.
    try:
        with open(safe_params.devices, "rb") as devicesFile:
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
    u_L = accord.core.metrology.calc_u_A(*m_corrected_averageList)
    u_T_resolution = accord.core.metrology.calc_u_B(error_value=termometer_resolution, distribution=termometer_distribution, k=termometer_k)
    u_T_accuracy = accord.core.metrology.calc_u_B(error_value=termometer_accuracy, distribution=termometer_distribution, k=termometer_k)
    u_T = accord.core.metrology.calc_u_c(u_T_resolution, u_T_accuracy)
    u_P_resolution = accord.core.metrology.calc_u_B(error_value=barometer_resolution, distribution=barometer_distribution, k=barometer_k)
    u_P_accuracy = accord.core.metrology.calc_u_B(error_value=barometer_accuracy, distribution=barometer_distribution, k=barometer_k)
    u_P = accord.core.metrology.calc_u_c(u_P_resolution, u_P_accuracy)

    # Calculating sensitivity coefficients.
    c_L = accord.core.corrections.calc_c_L(T_expected_value=20, P_expected_value=101.325, T_ref=20, P_ref=101.325)
    c_T = accord.core.corrections.calc_c_T(P_expected_value=101.325, T_ref=20, P_ref=101.325)
    c_P = accord.core.corrections.calc_c_P(L_expected_value=1, T_expected_value=20, P_expected_value=101.325, T_ref=20, P_ref=101.325)

    # Calculating combined standard uncertainty.
    u_c = accord.core.metrology.calc_u_c(c_L*u_L, c_T*u_T, c_P*u_P)
    
    # Coverage factor for a confidence level of approximately 95% for a normal distribution.
    # TODO: Calculate the effective degrees of freedom and the corresponding coverage factor with the Welch-Satterthwaite formula or specify in command line.
    # k = 2
    
    # Calculating expanded uncertainty.
    U = accord.core.metrology.calc_U(u_c, safe_params.k)

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
    
    fileFormats_traversable = importlib.resources.files("accord").joinpath("formats/fileFormats.json")
    
    try:
        with fileFormats_traversable.open("r", encoding="utf-8") as fileFormatsFile:
            fileFormatsData = json.load(fileFormatsFile)
    except FileNotFoundError:
        raise click.ClickException(f"File formats file not found in {fileFormats_traversable}.")
    except json.JSONDecodeError:
        raise click.ClickException(f"Invalid JSON in file formats file {fileFormats_traversable}.")
    
    output_preliminary_quantities = [column for column in fileFormatsData["output_preliminary"]["columns"].keys()]
    output_preliminary_units = {column_id: column["unit"] for column_id, column in fileFormatsData["output_preliminary"]["columns"].items()}
    output_preliminary_column_separator = fileFormatsData["output_preliminary"]["column_delimiter"]

    # Writing output files.
    i = 0
    for i in range(len(measurement_list_tries)):
        filePath = filepaths[i]
        dirs = pathlib.Path(filePath).parent
        stem = pathlib.Path(filePath).stem
        suffix = pathlib.Path(filePath).suffix
        output_filename = f"{safe_params.output_preffix}{i}{suffix}"
        output_filePath = pathlib.Path(safe_params.output_dir) / output_filename
        
        with open(output_filePath, "w", encoding="utf-8", newline='') as csvFile:
            csvWriter = csv.DictWriter(csvFile, fieldnames=output_preliminary_quantities, delimiter=output_preliminary_column_separator)
            csvWriter.writeheader()
            csvWriter.writerow(output_preliminary_units)
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
    output_quantities["k"] = safe_params.k
    output_quantities["U"] = U

    summaryPath = safe_params.summary # TODO: Check if summary should really be inside output_dir
    with open(summaryPath, "w", encoding="utf-8") as summaryFile:
        json.dump(output_quantities, summaryFile, indent=4)
        print(f"Output file {safe_params.summary} created.")

    click.echo("Preliminary analysis done.")
    sys.exit(0)

# analyze the image created by create-image-planar.
@click.command()
@click.argument("path", type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=pathlib.Path), required=True)
@click.option("--protocol", type=click.Choice(pylinac.Protocol), help="Protocol used for calculations.")
@click.option("--output", type=click.Path(file_okay=True, dir_okay=False, path_type=pathlib.Path), help="Path to output analysis file.")
@click.pass_context
def analyze_image_planar(ctx: click.Context, **kwargs: dict):
    """Analyze field images."""

    valid_kwargs = {k: v for k, v in kwargs.items() if v is not None and (not isinstance(v, (list, tuple)) or len(v) > 0)}

    config_to_pydantic = {**ctx.obj, **valid_kwargs}

    # Check with Pydantic that the options have the correct types and values.
    try:
        safe_params = accord.core.models.params.AnalyzeImagePlanar.model_validate(config_to_pydantic)
        
    except pydantic.ValidationError as e:
        # Extracting only the first error to not overwhelm the user with a long list of errors.
        # The error message is more user-friendly than the default Pydantic error message.
        error_info = e.errors()[0]
        field = ".".join(str(loc) for loc in error_info['loc'])
        message = error_info['msg']
        
        # Click exception
        raise click.ClickException(
            f"Pydantic Error in configuration ('{field}'): {message}"
        )


    # Load input files: field images
    field_analysis = pylinac.FieldAnalysis(path=str(safe_params.path))
    
    # performing analysis
    # field_analysis.analyze(protocol=protocol_class)
    field_analysis.analyze(protocol=safe_params.protocol)
    field_analysis.plot_analyzed_image()
    field_analysis.publish_pdf(filename=str(safe_params.output))
    
    click.echo(f"2D images analyzed.")
    sys.exit(0)

# generate the calibration report in PDF.
@click.command()
@click.argument("path", type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=pathlib.Path), is_eager=True, expose_value=True, required=True)
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
@click.pass_context
def generate_calibration_report(ctx, **kwargs):
    """Generate report about calibration."""

    try:
        with open(kwargs["path"], "rb") as f:
            config_calibration = tomllib.load(f)
    except Exception as e:
        raise click.ClickException(f"Error loading config file: {e}")

    normalized_calibration_config = {k.replace(separator["cli"], separator["file"]): v for k, v in config_calibration.items()}

    valid_kwargs = {k: v for k, v in kwargs.items() if v is not None and (not isinstance(v, (list, tuple)) or len(v) > 0)}
    
    valid_config_calibration = {**normalized_calibration_config, **valid_kwargs}

    config_to_pydantic = {**ctx.obj, **valid_config_calibration}

    # Check with Pydantic that the options have the correct types and values.
    try:
        safe_params = accord.core.models.params.GenerateCalibrationReportParams.model_validate(config_to_pydantic)
        
    except pydantic.ValidationError as e:
        # Extracting only the first error to not overwhelm the user with a long list of errors.
        # The error message is more user-friendly than the default Pydantic error message.
        error_info = e.errors()[0]
        field = ".".join(str(loc) for loc in error_info['loc'])
        message = error_info['msg']
        
        # Click exception
        raise click.ClickException(
            f"Pydantic Error in configuration ('{field}'): {message}"
        )

    trs398PhotonScheme = safe_params.to_domain_scheme

    # Calculations with pylinac.
    # TODO: The order of the parameters is the same as the order of the parameters in the TRS398Photon class, so we can use the ** operator to unpack the parameters from the dataclass to the TRS398Photon class.
    trs398_calculator = pylinac.calibration.trs398.TRS398Photon(
        chamber=trs398PhotonScheme.chamber,
        clinical_pdd_zref=trs398PhotonScheme.clinical_pdd_zref,
        energy=trs398PhotonScheme.energy,
        fff=trs398PhotonScheme.fff,
        institution=trs398PhotonScheme.institution,
        k_elec=trs398PhotonScheme.k_elec,
        m_opposite=trs398PhotonScheme.m_opposite,
        m_reference=trs398PhotonScheme.m_reference,
        m_reduced=trs398PhotonScheme.m_reduced,
        measurement_date=trs398PhotonScheme.measurement_date,
        mu=trs398PhotonScheme.mu,
        n_dw=trs398PhotonScheme.n_dw,
        physicist=trs398PhotonScheme.physicist,
        press=trs398PhotonScheme.press,
        setup=trs398PhotonScheme.setup,
        temp=trs398PhotonScheme.temp,
        tissue_correction=trs398PhotonScheme.tissue_correction,
        tpr2010=trs398PhotonScheme.tpr2010,
        unit=trs398PhotonScheme.unit,
        voltage_reduced=trs398PhotonScheme.voltage_reduced,
        voltage_reference=trs398PhotonScheme.voltage_reference
    )

    trs398_calculator.publish_pdf(
        filename=str(safe_params.filename),
        notes=safe_params.notes,
        open_file=False
        )
    click.echo(f"Output file {safe_params.filename} created.")

    #Creating output file for further processing.
    output_debug_filename = f"calibration-calculatedValues-{safe_params.energy}MV.csv"
    with open(output_debug_filename, "w", encoding="utf-8", newline="") as f:
        csvWriter_calibration = csv.writer(f, delimiter=";")
        csvWriter_calibration.writerow(["Quantity", "Unit", "Value-calculated"])
        csvWriter_calibration.writerow(["k_q", "", trs398_calculator.kq])
        csvWriter_calibration.writerow(["K-s", "", trs398_calculator.k_s])
        csvWriter_calibration.writerow(["K-pol", "", trs398_calculator.k_pol])
        csvWriter_calibration.writerow(["k_tp", "", trs398_calculator.k_tp])
        csvWriter_calibration.writerow(["m_corrected", "nC", trs398_calculator.m_corrected])
        csvWriter_calibration.writerow(["D_ref", "Gy", trs398_calculator.dose_mu_zref])
        csvWriter_calibration.writerow(["D_max", "Gy", trs398_calculator.dose_mu_zmax])

    print(f"Debug output file {output_debug_filename} created.")

    sys.exit(0)

# cli.add_command(create_sample_file)
main.add_command(create_image_planar)
main.add_command(analyze_preliminary)
main.add_command(analyze_image_planar)
main.add_command(generate_calibration_report)

if __name__ == "__main__":
    main()
    print(f"Program terminated.")