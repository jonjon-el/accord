import pathlib
import csv

import accord.core.nel_aux

def FilterFilesByAffix(input_dir: pathlib.Path, preffix: str, suffix: str) -> list[pathlib.Path]:
    """
    Filter files in a directory by preffix and suffix.

    Args:
        input_dir (pathlib.Path): Directory to search for files.
        preffix (str): Preffix to filter files.
        suffix (str): Suffix to filter files.

    Returns:
        list[pathlib.Path]: List of filtered files.
    """
    filepaths = list()
    for file in pathlib.Path(input_dir).iterdir():
        if file.is_file() and file.name.startswith(preffix) and file.name.endswith(suffix):
            filepaths.append(file)
    return filepaths

class PreliminaryFileParser:
    def __init__(self):
        pass

    
    def IsReady(self) -> bool:
        """
        Check if the parser is ready to parse files.

        Returns:
            bool: True if ready, False otherwise.
        """
        return hasattr(self, "quantitiesData") and hasattr(self, "fileFormats")


    def ParseFiles(self, filepaths: list[pathlib.Path]):
        self.rawMeasurements_set = list()
        for filepath in filepaths:
            with open(filepath, "r", encoding="utf-8") as csvFile:
                csvDictReader = csv.DictReader(csvFile, delimiter=self.fileFormats["input_preliminary"]["column_delimiter"])
                self.input_preliminary_quantities = csvDictReader.fieldnames #RETURN
                self.input_preliminary_units = next(csvDictReader) #RETURN
                rawMeasurements_table = list()
                for row in csvDictReader:
                    rawMeasurement_row = accord.core.nel_aux.Row2Measurement2(row=row, quantities=self.quantitiesData)
                    rawMeasurements_table.append(rawMeasurement_row.copy())
            self.rawMeasurements_set.append(rawMeasurements_table.copy()) #RETURN