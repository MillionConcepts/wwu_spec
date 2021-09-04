import re
from functools import reduce
from operator import add

import numpy as np
import pandas as pd

from uwinn_ingest.cases import SPECTRAL_STOPWORDS


def convert_wavelength_units(base_values, unit_title):
    if re.search(r"ength.*(µm|um|microns)", unit_title):
        return um_to_nm(base_values)
    if re.search("wavenumber", unit_title, flags=re.I):
        return wavenumber_to_nm(base_values)
    else:
        return base_values


def ix_of_str(series, value, insensitive=True):
    if insensitive is True:
        value = re.compile(value, re.I)
    return series.loc[series.str.contains(value).fillna(False)].index


def ix_of_float(series: pd.Series, value: float):
    return series.loc[(series == value).fillna(False)].index


def ix_of_nan(series):
    return series.loc[series.isna()].index


def um_to_nm(um_series):
    return um_series * 1000


def wavenumber_to_nm(wavenumber_series):
    """
    assuming we mean reciprocal centimeters.
    which we always do in this context, right?
    """
    return 1 / wavenumber_series * 1e7


def end_spectra_ix(series):
    """returns index of any 'stopwords' or null values at base of wavelength"""
    ix = ix_of_str(series, f"(?={'|'.join(SPECTRAL_STOPWORDS)})").union(
        ix_of_nan(series)
    )
    if len(ix) > 0:
        return ix[0] - 1
    return None


def find_wavelength_ix(sheet: pd.DataFrame, header_col_ix: int = 0) -> tuple:
    """returns index of Wavelength separator."""
    wave_warnings = []
    header_col = sheet.iloc[:, header_col_ix]
    wave_positions = [
        ix
        for ix in ix_of_str(header_col, r"(?:wavelength|wavenumber)")
        if "range" not in header_col.loc[ix].lower()
    ]
    if len(wave_positions) == 0:
        raise NotImplementedError("ocean optics format or bad split")
    if len(wave_positions) > 1:
        wave_warnings.append(
            "multiple unit designations present, using last one"
        )
    return wave_positions[-1] + 1, wave_warnings


def invert_metadata_section(metadata, fields):
    metadata.index = fields
    return metadata.T


def index_unnamed_columns(df):
    new_column_names = []
    for ix, col in enumerate(df.columns):
        if pd.isna(col):
            new_column_names.append(f"unnamed: {ix}")
        else:
            new_column_names.append(col)
    return new_column_names


def concatenate_paragraph(indices, dataframe):
    """
    concatenate a group of columns in a dataframe
    """
    # get preceding, hopefully named, column
    broken_columns = [
        dataframe.iloc[:, ix].fillna("").astype(str) + "\n" for ix in indices
    ]
    return reduce(add, broken_columns).str.strip("\n")


def concatenate_duplicate_columns(df):
    col_counts = df.columns.value_counts()
    dupe_names = col_counts.loc[col_counts > 1]
    for dupe_name in dupe_names.index:
        dupe_indices = np.where(df.columns.values == dupe_name)[0]
        first_ix = dupe_indices[0]
        cat = concatenate_paragraph(dupe_indices, df)
        cat.name = dupe_name
        df = df.drop(columns=dupe_name)
        df = pd.concat(
            [df.iloc[:, :first_ix], cat, df.iloc[:, first_ix:]], axis=1
        )
    return df


def collapse_null_columns(dataframe):
    empty_indices = []
    for ix, column in enumerate(dataframe.columns):
        dataframe, empty_indices = handle_emptiness(
            empty_indices, column, ix, dataframe
        )
    dataframe, empty_indices = handle_emptiness(
        empty_indices, "", ix, dataframe
    )
    return dataframe.drop(
        columns=[c for c in dataframe.columns if "unnamed" in c]
    )


def enumerate_duplicate_ids(headers):
    for sample_id in headers["sample_id"].unique():
        id_group = headers.loc[headers["sample_id"] == sample_id]
        if len(id_group) > 1:
            for group_ix, ixrow in enumerate(id_group.iterrows()):
               headers.loc[ixrow[0], "sample_id"] = f"{sample_id}_{group_ix}"
    return headers


def handle_emptiness(empty_indices, column, ix, dataframe):
    if "unnamed" in column:
        empty_indices.append(ix)
    else:
        if empty_indices:
            dataframe.iloc[:, empty_indices[0] - 1] = concatenate_paragraph(
                [empty_indices[0] - 1] + empty_indices, dataframe
            )
            empty_indices = []
    return dataframe, empty_indices