import logging

import numpy as np
import pandas as pd

from uwinn_ingest.cases import field_mapping, KNOWN_BAD_SPLITS
from uwinn_ingest.parse_utils import (
    convert_wavelength_units,
    end_spectra_ix,
    find_wavelength_ix,
    invert_metadata_section,
    index_unnamed_columns,
    concatenate_duplicate_columns,
    collapse_null_columns,
    enumerate_duplicate_ids,
)

logger = logging.getLogger("uwinn_split")
logger.setLevel(logging.INFO)
csv_handler = logging.FileHandler("uwinn_split_ingest.csv")
csv_handler.setLevel(logging.DEBUG)
csv_format = logging.Formatter("%(asctime)s,%(levelname)s,%(message)s")
csv_handler.setFormatter(csv_format)
logger.addHandler(csv_handler)


def read_uwinn_split(split_path):
    split_warnings = []
    try:
        table = pd.read_csv(split_path, low_memory=False)
    except UnicodeDecodeError:
        table = pd.read_csv(
            split_path, encoding="ISO-8859-1", low_memory=False
        )
    wave_begin_ix, wave_warnings = find_wavelength_ix(table)
    split_warnings += wave_warnings
    wave_series = table.iloc[wave_begin_ix:, 0]
    wave_end_ix = end_spectra_ix(wave_series)
    wave_series = wave_series.loc[:wave_end_ix].astype("float")
    wavelengths = convert_wavelength_units(
        base_values=wave_series, unit_title=table.iloc[wave_begin_ix - 1, 0]
    )
    reflectance = table.loc[wave_begin_ix:wave_end_ix]
    reflectance = reflectance.iloc[:, 1:].astype("float")
    wavelength_range = (wavelengths.min(), wavelengths.max())
    if (wavelength_range[0] < 150) or (wavelength_range[1] > 30000):
        raise ValueError(
            f"maybe the wrong units, range"
            f"{wavelength_range[0]} - {wavelength_range[1]}"
        )
    meta_fields = table.iloc[: wave_begin_ix - 1, 0]
    metadata = table.iloc[: wave_begin_ix - 1, 1:]
    return meta_fields, metadata, wavelengths, reflectance, split_warnings


def format_headers(metadata, fields):
    headers = invert_metadata_section(metadata, fields)
    # drop rows containing explicit no data instructions
    no_data = [
        ix for ix, row in headers.iterrows() if "no data" in str(row).lower()
    ]
    headers = headers.drop(no_data)
    # give columns non-nan, unique names
    headers.columns = index_unnamed_columns(headers)
    headers = concatenate_duplicate_columns(headers).dropna(axis=1, how="all")
    return collapse_null_columns(headers)


def translate_headers(headers, wavelengths, filename):
    rejects = []
    new_names = []
    for col in headers.columns:
        field, translation = field_mapping(col)
        field = field.replace('"', "")
        logger.info(f'{filename},interp,"{field}",{translation}')
        if translation is not None:
            new_names.append(translation)
        else:
            rejects.append(col)
    headers = headers.drop(columns=rejects)
    headers.columns = new_names
    headers = (
        headers.replace("", np.nan).dropna(how="all").reset_index(drop=True)
    )
    headers["filename"] = filename
    if "unnamed" not in wavelengths.name:
        if "references" not in headers.columns:
            headers["references"] = wavelengths.name
        else:
            headers["references"] += f"\n{wavelengths.name}"
    if "sample_name" not in headers.columns:
        logger.warning(f"{filename},sample_name not found")
    if "sample_id" not in headers.columns:
        if "sample_name" in headers.columns:
            headers["sample_id"] = headers["sample_name"]
        else:
            raise ValueError("sample_id not found")
    headers = enumerate_duplicate_ids(headers)
    return headers


def check_split_goodness(split_path):
    if (
        (split_path is None)
        or (split_path.name in KNOWN_BAD_SPLITS)
        or ("lichen" in split_path.name.lower())
        or ("asbetos" in split_path.name.lower())
        or ("crowley" in split_path.name.lower())
    ):
        return False
    return True
