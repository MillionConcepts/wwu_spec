"""
functionality for dealing with various sorts of project-internal
input and output formats
"""
import csv
import datetime as dt
import io
import zipfile
from typing import Union, IO, Any

import PIL
import numpy as np
import pandas as pd
from django.conf import settings
from django.http import HttpResponse

from visor.dj_utils import parse_sample_csv
from visor.models import SampleType, Database, Sample


"""
TODO: refactor all this garbage
"""


def check_sample_csv(
    field_dict: dict, warnings: list, errors: list
) -> (dict, list, list):
    # maps upload text to the ForeignKey fields
    # creates database entries if not present
    # and assigns a sample ID if not present
    if "sample_type" in field_dict.keys():
        if field_dict["sample_type"] not in [
            sample_type.name for sample_type in SampleType.objects.all()
        ]:
            errors.append(
                field_dict["sample_type"] + " is not an allowable sample type."
            )
        else:
            field_dict["sample_type"] = SampleType.objects.get(
                name=field_dict["sample_type"]
            )
    if "origin" in field_dict.keys():
        if field_dict["origin"] not in [
            database.name for database in Database.objects.all()
        ]:
            active_database = str(field_dict["origin"]).strip()
            warnings.append(
                active_database
                + " was not previously listed among our affiliate databases "
                "and has been added as a database of origin. "
            )
            new_database = Database(name=active_database)
            new_database.save()
        field_dict["origin"] = Database.objects.get(name=field_dict["origin"])
    if "sample_id" not in field_dict.keys():
        field_dict["sample_id"] = str(np.random.randint(1000000))
        warnings.append(
            "No name was provided for the sample in"
            + field_dict["filename"]
            + ".it has been"
            "assigned the placeholder identifier "
            + field_dict["sample_id"]
            + "."
        )
    return field_dict, warnings, errors


def ingest_sample_csv(csv_file: Union[str, IO, zipfile.ZipExtFile]) -> dict:
    warnings = []
    errors = []

    if isinstance(csv_file, zipfile.ZipExtFile):
        filename = csv_file.name

    else:
        filename = csv_file

    try:
        csv_in = pd.read_csv(csv_file, header=None)
    except Exception as ex:
        errors.append("This doesn't appear to be a .csv file: " + str(ex))
        return {
            "sample": None,
            "filename": csv_file,
            "warnings": warnings,
            "errors": errors,
        }

    if csv_in.shape[1] > csv_in.shape[0]:
        csv_in = csv_in.T

    csv_in = csv_in.astype("str")

    for series in csv_in:
        csv_in[series] = csv_in[series].str.strip()
    csv_in = csv_in.to_numpy().swapaxes(0, 1)
    refl_search = np.nonzero(csv_in[0] == "Wavelength")[0]
    if refl_search.size == 0:
        errors.append(
            'Error: the "Wavelength" separator wasn\'t found in '
            + filename
            + "."
        )
        return {
            "sample": None,
            "filename": csv_file,
            "warnings": warnings,
            "errors": errors,
        }
    if refl_search.size > 1:
        errors.append(
            'Error: the "Wavelength" separator appears more than once in '
            + filename
            + "."
        )
        return {
            "sample": None,
            "filename": csv_file,
            "warnings": warnings,
            "errors": errors,
        }

    refl_start = refl_search[0]
    meta_array = np.array(csv_in[0:, 0:refl_start])
    refl_array = np.array(csv_in[0:, refl_start + 1 :])
    try:
        refl_array = refl_array.astype(np.float64)
    except ValueError:
        errors.append(
            "Error: some fields in the reflectance data can't be interpreted "
            "as numbers. "
            + "It's possible that you haven't placed the reflectance data "
            "after all of the "
            "metadata, or that there are some non-numeric characters in the "
            "reflectance data. "
        )

    # check for and handle multicolumn reflectance data

    sample_split = False
    split_refl = []
    if refl_array.shape[0] > 2:
        sample_split = True
        meta_array = meta_array[0:2]
        split_refl = [
            np.vstack((refl_array[0, :], refl_array[col + 1, :]))
            for col in np.arange(refl_array.shape[0] - 1)
        ]

    parsed_csv = parse_sample_csv(meta_array, warnings, errors)
    field_dict = parsed_csv[0]
    warnings = parsed_csv[1]
    errors = parsed_csv[2]
    field_dict |= {"filename": filename}
    field_dict, warnings, errors = check_sample_csv(
        field_dict, warnings, errors
    )
    field_dict |= {"import_notes": str(warnings)}
    # split multicolumn data into multiple Sample objects

    if errors:
        return {
            "sample": None,
            "filename": filename,
            "warnings": warnings,
            "errors": errors,
        }

    if sample_split:
        sample_out = [
            Sample(
                **(
                    field_dict
                    | {
                        "reflectance": sample,
                        "sample_id": field_dict["sample_id"] + "_" + str(ix),
                    }
                )
            )
            for ix, sample in enumerate(split_refl)
        ]
    else:
        sample_out = Sample(**(field_dict | {"reflectance": refl_array}))

    return {
        "sample": sample_out,
        "filename": filename,
        "warnings": warnings,
        "errors": None,
    }


def handle_csv_upload(csv_file: Union[str, zipfile.ZipExtFile]) -> list[dict]:
    csv_in = ingest_sample_csv(csv_file)
    if csv_in["errors"] is not None:
        return [{"filename": csv_file.name, "errors": csv_in["errors"]}]

    sample = csv_in["sample"]
    save_errors = []

    try:
        if type(sample) == list:
            for active_sample in sample:
                active_sample.clean()
                active_sample.save(uploaded=True)
        else:
            sample.clean()
            sample.save(uploaded=True)
    except Exception as ex:
        save_errors = str(ex)
    if save_errors:
        return [{"filename": csv_file.name, "errors": save_errors}]

    # flatten multisample
    if type(sample) == list:
        flat_samples = []
        for active_sample in sample:
            flat_samples.append(
                {
                    "sample": active_sample,
                    "filename": csv_file.name,
                    "errors": None,
                }
            )
        return flat_samples

    return [{"sample": sample, "filename": csv_file.name, "errors": None}]


def check_zip_structure(
    zipped_file: zipfile.ZipFile, upload_errors: list
) -> Union[
    list[Union[int, list]], dict[str, Union[list, list[str], dict[str, Any]]]
]:
    uploaded_files = zipped_file.namelist()

    csv_files = [file for file in uploaded_files if file[-3:] == "csv"]
    jpg_files = [file for file in uploaded_files if file[-3:] == "jpg"]
    other_files = [
        file for file in uploaded_files if file[-3:] not in ["csv", "jpg"]
    ]

    # check for inappropriate filetypes

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
    if upload_errors:
        return [0, upload_errors]

    # attempt to open images and associate them with csv files
    # we're strict about this to avoid confusing situations for users
    # and also saving mangled files into our media space

    image_associations = {}

    for jpg_file in jpg_files:
        if jpg_file[:-4] not in [csv_file[:-4] for csv_file in csv_files]:
            upload_errors.append(
                jpg_file
                + " is not associated with any csv file."
                + " Please remove it from the zip file and reload."
            )
        elif jpg_file[-3:] != "jpg":
            upload_errors.append(
                jpg_file[:-4]
                + "Has the same name as a csv file but doesn't appear to be "
                "a JPEG"
                + " image. Please remove it from the zip file and reload."
            )
        else:
            matching_csv_file = [
                csv_file
                for csv_file in csv_files
                if csv_file[:-4] == jpg_file[:-4]
            ][0]
            try:
                matching_image = PIL.Image.open(zipped_file.open(jpg_file))
                image_associations[matching_csv_file] = matching_image
            except (FileNotFoundError, PIL.UnidentifiedImageError):
                upload_errors.append(
                    jpg_file
                    + " does not appear to be a valid image file."
                    + " Please verify it and reload."
                )
    return {
        "upload_errors": upload_errors,
        "jpg_files": jpg_files,
        "csv_files": csv_files,
        "image_associations": image_associations,
    }


def handle_zipped_upload(zipped_file: IO):
    upload_errors = []

    # try opening the file
    try:
        zipped_file = zipfile.ZipFile(zipped_file)
    except Exception as error:
        upload_errors.append(
            "The input can't be parsed as a zip file."
            + " Please verify it and reload."
        )
        upload_errors.append(error)
        return [0, upload_errors]

    check = check_zip_structure(zipped_file, upload_errors)
    upload_errors = check["upload_errors"]
    csv_files = check["csv_files"]
    # jpg_files = check["jpg_files"]
    image_associations = check["image_associations"]
    if upload_errors:
        return [0, upload_errors]

    # if all the files are ok as files, go ahead and check them against the
    # model

    # process the CSV and see if there are problems there

    samples = [ingest_sample_csv(zipped_file.open(file)) for file in csv_files]

    # log samples that were successful and erroneous at this stage

    erroneous_samples = [
        sample for sample in samples if sample["errors"] is not None
    ]
    successful_samples = [
        sample for sample in samples if sample["errors"] is None
    ]

    # flatten sample list in case of multicolumn uploads

    single_samples = [
        samp for samp in successful_samples if type(samp["sample"]) != list
    ]
    multi_samples = [
        samplist
        for samplist in successful_samples
        if type(samplist["sample"]) == list
    ]
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
    successful_samples = single_samples + flat_samples

    for sample in successful_samples:
        if sample["sample"].filename in image_associations.keys():
            sample["sample"].image = image_associations[
                sample["sample"].filename
            ]

    # check against the model's main clean and save methods; also, you know,
    # save

    for sample in successful_samples:
        try:
            sample["sample"].clean()
            sample["sample"].save(uploaded=True)
        except Exception as ex:
            sample["errors"] = str(ex)

    # divide samples that had errors at either stage from those that saved
    # successfully

    erroneous_samples += [
        sample for sample in successful_samples if sample["errors"] is not None
    ]
    successful_samples = [
        sample for sample in successful_samples if sample["errors"] is None
    ]

    if not successful_samples:
        return [1, erroneous_samples]
    if erroneous_samples:
        return [2, successful_samples, erroneous_samples]
    return [3, successful_samples]


def write_sample_csv(field_list, sample):
    text_buffer = io.StringIO()
    writer = csv.writer(text_buffer)
    for field in field_list:
        if field[1] not in [
            "image",
            "id",
            "reflectance",
            "filename",
            "import_notes",
            "flagged",
            "simulated_spectra",
            "released",
        ]:
            writer.writerow([field[0], getattr(sample, field[1])])
    return writer, text_buffer


def construct_export_zipfile(selections, export_sim, simulated_instrument):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as buffer:
        write_samples_into_buffer(
            export_sim, buffer, selections, simulated_instrument
        )
    zip_buffer.seek(0)
    # name the zip file and send it as http
    date = dt.datetime.today().strftime("%y-%m-%d")
    response = HttpResponse(zip_buffer, content_type="application/zip")
    response["Content-Disposition"] = (
        "attachment; filename=spectra-%s.zip;" % date
    )
    return response


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
            buffer = write_simulated_spectra_to_buffer(
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


def write_simulated_spectra_to_buffer(
    metadata, output, sample, simulated_instrument
):
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
