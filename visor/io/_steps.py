"""
functions intended primarily to be called as steps of of the ingest/export
pipelines defined in visor.io.handlers.
"""
import io
import random
from pathlib import Path
from typing import Optional, Sequence
import zipfile

from django.conf import settings
import numpy as np
import pandas as pd
import PIL

from visor.dj_utils import model_values, extension_is, split_on
from visor.models import SampleType, Database, Sample


def map_metadata_to_related_tables(
    field_dict: dict, warnings: list, errors: list
) -> (dict, list, list):
    # maps upload text to ForeignKey fields.
    # This behavior is inconsistent but matches current spec.
    # 1. checks and assigns SampleType (will not create new)
    # 2. checks and assigns Database (will create new)
    # 3. assigns a random sample ID if not present
    uploaded_sample_type = field_dict.get("sample_type")
    if (
        uploaded_sample_type is not None
        and uploaded_sample_type not in SampleType.objects.values_list("name")
    ):
        errors.append(
            f"{field_dict['sample_type']} is not an allowable sample type."
        )
    elif uploaded_sample_type is not None:
        field_dict["sample_type"] = SampleType.objects.get(
            name=uploaded_sample_type
        )
    if field_dict["origin"] not in model_values(Database, "name"):
        # note: actually makes a new Database object
        warnings = create_database_from_origin_field(field_dict, warnings)
    field_dict["origin"] = Database.objects.get(name=field_dict["origin"])
    if "sample_id" not in field_dict.keys():
        field_dict["sample_id"], warnings = random_sample_id(warnings)
    return field_dict, warnings, errors


def flip_and_strip_whitespace(csv_in: pd.DataFrame) -> pd.DataFrame:
    """
    ensure the passed csv file is in long format and strip whitespace.
    TODO: the check for long format may be cruft.
    """
    if csv_in.shape[1] > csv_in.shape[0]:
        csv_in = csv_in.T
    for series in csv_in:
        csv_in[series] = csv_in[series].str.strip()
    return csv_in


def create_database_from_origin_field(
    field_dict: dict, warnings: list
) -> list:
    new_database_name = str(field_dict["origin"]).strip()
    warnings.append(
        f"{new_database_name} was not previously listed among our "
        f"affiliate databases and has been added as a database of "
        f"origin. "
    )
    new_database = Database(name=new_database_name)
    new_database.save()
    return warnings


def random_sample_id(warnings: list) -> (str, list):
    random_id = str(random.randint(1000000,9999999))
    warnings.append(
        f"No id was provided for this sample. It has been assigned the "
        f"placeholder identifier {random_id}."
    )
    return random_id, warnings


def ingested_sample_dict(
    s: Optional[Sample], f: str, w: list, e: list
) -> dict:
    """wrap ingested sample and its (backend) metadata in standardized dict"""
    return {"sample": s, "filename": f, "warnings": w, "errors": e}


def split_data_and_metadata(
    csv_in: pd.DataFrame, filename: str, warnings: list[str], errors: list[str]
) -> (Optional[pd.DataFrame], Optional[pd.DataFrame], list[str], list[str]):
    # the first column of the CSV should consist of metadata field
    # names followed by the separator 'Wavelength' followed by wavelength
    # values (in nm).
    header_wave_column = csv_in[0]
    # look for the separator
    wavelength_positions = header_wave_column.loc[
        header_wave_column == "Wavelength"
    ].index
    # if the separator appears more than once, fail with useful error message
    if wavelength_positions.size != 1:
        if wavelength_positions.size == 0:
            errors.append(f"Error: 'Wavelength' wasn't found in {filename}.")
            return None, None, warnings, errors
        if wavelength_positions.size > 1:
            errors.append(
                f"Error: 'Wavelength' appears more than once in {filename}."
            )
        return None, None, warnings, errors
    # split data and metadata "blocks" at the separator
    data_start = wavelength_positions[0]
    data_frame = csv_in.iloc[data_start + 1 :]  # don't include separator row
    meta_frame = csv_in.iloc[:data_start]
    # attempt to convert data block to float
    try:
        data_frame = data_frame.astype(np.float64)
    except ValueError:
        errors.append(
            "Error: some fields in the reflectance data can't be interpreted "
            "as numbers. It's possible that you haven't placed the "
            "reflectance data after all of the metadata, or that there are "
            "some non-numeric characters in the reflectance data. "
        )
    # make sure float NaNs have not sneakily crept in
    meta_frame = meta_frame.astype(str)
    return data_frame, meta_frame, warnings, errors


def associate_zipped_images(
    zipped_file: zipfile.ZipFile, manifest: dict, upload_errors: list
):
    """
    attempt to open images and associate them with csv files
    we're fairly strict about this to avoid confusing situations for users
    and also to avoid saving mangled files into our media space
    """
    image_associations = {}
    csv_stems = [Path(csv_file).stem for csv_file in manifest["csv_files"]]
    for jpg_file in manifest["jpg_files"]:
        matches = [
            f"{csv_stem}.csv"
            for csv_stem in csv_stems
            if csv_stem == Path(jpg_file).stem
        ]
        if len(matches) == 1:
            # great, a match, fine
            try:
                matching_image = PIL.Image.open(zipped_file.open(jpg_file))
                image_associations[matches[0]] = matching_image
            except (FileNotFoundError, PIL.UnidentifiedImageError):
                upload_errors.append(
                    f"{jpg_file} does not appear to be a valid image file. "
                    f"Please verify it and reload."
                )
        elif len(matches) == 0:
            # aww, no match
            upload_errors.append(
                f"{jpg_file} is not associated with any csv file. Please "
                f"remove it from the zip file and reload."
            )
        elif len(matches) > 1:
            # look, don't do this
            upload_errors.append(
                f"{jpg_file} appears to have multiple related CSV files. "
                f"Please give things distinct filenames and reload."
            )
    return image_associations, upload_errors


def check_for_inappropriate_files(
    csv_files: list[str], other_files: list[str], upload_errors: list[str]
) -> list[str]:
    if other_files:
        upload_errors.append(
            "There are files that do not have a csv or jpg extension in the "
            "upload. Please correct this and reload."
        )
    if len(csv_files) != len(set(csv_files)):
        upload_errors.append(
            "There appear to be duplicate csv filenames in the upload. "
            + "Please correct this and reload."
        )
    if len(csv_files) == 0:
        upload_errors.append(
            "There do not appear to be any csv files in this upload."
        )
    return upload_errors


def classify_zip_file_contents(
    zipped_file: zipfile.ZipFile, upload_errors: list[str]
) -> (dict, list[str]):
    files = zipped_file.namelist()
    manifest = {
        "csv_files": list(filter(extension_is(".csv"), files)),
        "jpg_files": list(filter(extension_is(".jpg"), files)),
        "other_files": list(
            filter(
                lambda x: not extension_is(".jpg")
                and not extension_is(".csv"),
                files,
            )
        ),
    }
    upload_errors = check_for_inappropriate_files(
        manifest["csv_files"],
        manifest["other_files"],
        upload_errors,
    )
    return manifest, upload_errors


def add_images_to_results(
    image_associations: dict, results: Sequence[dict]
) -> Sequence[dict]:
    """
    plug images from filename lookup table into attributes of corresponding
    Sample objects being passed around as a sequence of result dicts
    """
    for result in results:
        if result["sample"].filename in image_associations.keys():
            result["sample"].image = image_associations[
                result["sample"].filename
            ]
    return results


def unpack_multi_samples(multi_samples):
    flat_samples = []
    for multi_sample in multi_samples:
        for sample in multi_sample["sample"]:
            flat_samples.append(
                {
                    "sample": sample,
                    "filename": multi_sample["filename"],
                    "warnings": multi_sample["warnings"],
                    "errors": multi_sample["errors"],
                }
            )
    return flat_samples


def flatten_multisamples(
    ingest_results: Sequence[dict]
) -> list[dict]:
    """flatten lists produced by ingest_sample_csv from multicolumn files"""
    # check for lists
    multi_samples, single_samples = split_on(
        lambda x: isinstance(x["sample"], list), ingest_results
    )
    # if present, flatten them
    if len(multi_samples) > 0:
        flat_samples = unpack_multi_samples(multi_samples)
        ingest_results = single_samples + flat_samples
    return ingest_results


def write_samples_into_buffer(
    export_sim, buffer, selections, simulated_instrument
):
    samples = Sample.objects.filter(id__in=selections)
    # write each sample line-by-line into text buffer,
    # also splitting reflectance dictionary into lines
    for sample in samples:
        metadata = sample.metadata_csv_block()
        buffer = write_spectrum_to_buffer(metadata, buffer, sample)
        if export_sim:
            buffer = write_simulated_spectra_to_zipfile(
                metadata, buffer, sample, simulated_instrument
            )
        # write image into output (e.g. zipfile) buffer
        if sample.image:
            filename = settings.SAMPLE_IMAGE_PATH + "/" + sample.image
            buffer.write(filename, arcname=sample.image)
    return buffer


def write_spectrum_to_buffer(metadata, buffer, sample):
    data = sample.data_csv_block()
    text_buffer = io.StringIO(metadata + "\n" + data)
    text_buffer.seek(0)
    # write sample into buffer
    buffer.writestr(
        f"{sample.sample_id.replace('/', '_')}_{sample.id}.csv",
        text_buffer.read(),
    )
    return buffer


def map_field_name(field_name, warnings, errors):
    """
    if a field name given in an uploaded CSV file isn't one of our known
    field names, check to see if it's empty or a legacy field, and respond
    appropriately.
    """
    if field_name == "nan":
        warnings.append(
            "Warning: a row in the input was interpreted as NaN. This "
            "is generally harmless and caused by idiosyncracies in "
            "how pandas.read_csv handles stray separators."
        )
        mapped_field = None
    elif field_name == "data id":
        warnings.append(
            "Warning: the Data ID field is recognized for legacy "
            "purposes but is not used by the database unless you have "
            "not provided a Sample ID."
        )
        mapped_field = "sample_id"
    elif field_name == "mineral name" or field_name == "sample name":
        warnings.append(
            "Warning: the {column_name} field is interpreted as "
            "sample_name."
        )
        mapped_field = "sample_name"
    elif "origin" in field_name:
        mapped_field = "origin"
    # and raise an error for extraneous fields
    else:
        errors.append(
            f"{field_name} is not a valid field name for this database."
        )
        mapped_field = None
    return mapped_field


def parse_csv_metadata(
    meta_frame: pd.DataFrame, warnings: list, errors: list
) -> (pd.DataFrame, list, list):
    """
    map rows from csv file to the fields of a Sample object
    and record errors if the csv file is formatted improperly
    """
    field_names = {
        field.verbose_name.lower(): field.name for field in Sample._meta.fields
    }
    # dict to hold field / value pairs
    field_dict = {}
    for header, value in zip(meta_frame[0], meta_frame[1]):
        # ignore empty fields
        if value == "nan":
            continue
        # check to see if the input field is in the model
        field = header.strip().lower()
        # if it's not, check to see if it's an empty or legacy field;
        # note an error for fields that are neither
        if field not in field_names.keys():
            mapped_field = map_field_name(field, warnings, errors)
            if mapped_field is not None:
                field_dict[mapped_field] = value
        # note an error for a field that appears more than once in the CSV
        elif len(list(filter(lambda x: x == field, field_names.keys()))) > 1:
            errors.append(
                f"Error: {field} appears to be assigned more than once."
            )
        # ignore explicitly-given min/max reflectance (far too often wrong)
        elif "reflectance" in field:
            warnings.append(
                "The minimum and maximum reflectance fields are "
                "recognized for legacy purposes but the database actually "
                "computes these values from the reflectance data."
            )
        else:
            # successful in a normal way!
            field_dict[field_names[field]] = value
    return field_dict, warnings, errors


def save_ingest_results_into_database(
    ingest_results: Sequence[dict],
) -> Sequence[dict]:
    """save ingest results into the database."""
    for result in ingest_results:
        try:
            result["sample"].clean()
            result["sample"].save(uploaded=True)
        except Exception as ex:
            result["errors"] = f"{type(ex)}: {ex}"
    return ingest_results


def write_simulated_spectra_to_zipfile(
    metadata: str,
    output: zipfile.ZipFile,
    sample: Sample,
    simulated_instrument: str,
) -> zipfile.ZipFile:
    """
    writes simulated spectra into an in-memory ZipFile object as multiple
    distinct CSV files (compressed in that archive)
    """
    sims = sample.sim_csv_blocks()
    if simulated_instrument == "all":
        simulated_instruments = sims.keys()
    else:
        simulated_instruments = [simulated_instrument]
    for instrument in simulated_instruments:
        text_buffer = io.StringIO(metadata + "\n" + sims[instrument])
        text_buffer.seek(0)
        output.writestr(
            f"{sample.sample_id.replace('/', '_')}"
            f"_simulated_{instrument}_{sample.id}.csv",
            text_buffer.read(),
        )
    return output


def make_dict_for_view_function(bad_results, good_results):
    if not good_results:
        status = "failed during ingest"
    elif bad_results:
        status = "partially successful"
    else:
        status = "successful"
    return {
        "status": status,
        "good": good_results,
        "bad": bad_results,
        "errors": [],
    }
