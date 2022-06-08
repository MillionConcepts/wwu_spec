"""
functions to ingest observational data -- right now just including
XCAM ROI files
"""
from itertools import chain

from marslab.compat.xcam import DERIVED_CAM_DICT, polish_xcam_spectrum
import numpy as np
import pandas as pd

from visor.models import Database, Sample


def make_cam_db_entry(instrument: str):
    """
    if we don't have a database-of-origin entry for ROIs from this instrument,
    make one
    """
    try:
        database = Database.objects.get(
            **{"name__iexact": instrument + " ROIs"}
        )
    except Database.DoesNotExist:
        database = Database(
            name=instrument + " ROIs",
            short_name=instrument + " ROIs",
            released=True,
        )
        database.clean()
        database.save()
    return database


def make_xcam_reflectance_array(instrument: str, spectrum: dict) -> np.ndarray:
    # scale to the first present pair we find
    scale_to = None
    for pair in DERIVED_CAM_DICT[instrument][
        "virtual_filter_mapping"
    ].values():
        if all(filt in spectrum.keys() for filt in pair):
            scale_to = pair
            break
    polished_spectrum = polish_xcam_spectrum(
        spectrum,
        DERIVED_CAM_DICT[instrument],
        scale_to=scale_to,
        average_filters=True,
    )
    return np.vstack(
        [[filt["wave"], filt["mean"]] for filt in polished_spectrum.values()]
    )


def roi_to_sample(
    instrument: str,
    database: "Database",
    metadata: dict,
    spectrum: dict,
    filename: str,
) -> "Sample":
    """
    convert a single spectrum from a marslab file to a VISOR Sample object
    and save it in the database
    """
    reflectance = make_xcam_reflectance_array(instrument, spectrum)
    notes = "\n".join(
        [str(key) + ": " + str(value) for key, value in metadata.items()]
    )
    name = (
        metadata["SEQ_ID"]
        + "_"
        + metadata["COLOR"]
        + "_sol_"
        + str(metadata["SOL"])
    )
    spectrum_entry = Sample(
        sample_name=name,
        sample_id="",
        reflectance=reflectance,
        origin=database,
        filename=filename,
        sample_desc=notes,
        released=True,
    )
    spectrum_entry.clean()
    spectrum_entry.save()
    print("Successfully added " + name + " to the database")
    return spectrum_entry


def ingest_xcam_roi_file(filename: str) -> None:
    """
    ingest all spectra from a marslab file into VISOR.
    """
    if not filename.startswith("marslab_"):
        raise ValueError("This function only takes marslab files.")
    spectra = pd.read_csv(filename)
    instrument = spectra["INSTRUMENT"].iloc[0]
    database = make_cam_db_entry(instrument)
    data_columns = [
        col for col in spectra.columns
        if col in DERIVED_CAM_DICT[instrument]['filters']
    ]
    metadata_columns = [
        col for col in spectra.columns
        if col not in chain.from_iterable([
            DERIVED_CAM_DICT[instrument]['filters'],
            map(lambda s: f"{s}_ERR", DERIVED_CAM_DICT[instrument]['filters'])
        ])
    ]
    for _, line in spectra.iterrows():
        metadata = line[metadata_columns].dropna().to_dict()
        spectrum = line[data_columns].dropna().to_dict()
        roi_to_sample(instrument, database, metadata, spectrum, filename)
