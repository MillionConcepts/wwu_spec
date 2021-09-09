"""
ingest/export pipelines for dealing with various sorts of project-internal
input and output formats, especially uploaded and exported CSV
"""
import datetime as dt
import io
from typing import Union, IO
import zipfile

import pandas as pd
from django.http import HttpResponse

from visor.dj_utils import split_on
from visor.io._steps import (
    add_images_to_results,
    associate_zipped_images,
    classify_zip_file_contents,
    flatten_multisamples,
    flip_and_strip_whitespace,
    map_metadata_to_related_tables,
    ingested_sample_dict,
    parse_csv_metadata,
    save_ingest_results_into_database,
    split_data_and_metadata,
    write_samples_into_buffer, make_dict_for_view_function,
)
from visor.models import Sample


def ingest_sample_csv(csv_file: Union[str, IO, zipfile.ZipExtFile]) -> dict:
    warnings = []
    errors = []
    if isinstance(csv_file, (zipfile.ZipExtFile, IO)):
        filename = csv_file.name
    else:
        filename = csv_file
    try:
        # note that read_csv will happily read directly from ZipExtFiles
        csv_in = pd.read_csv(csv_file, header=None, dtype=str)
    except Exception as ex:
        errors.append("This doesn't appear to be a .csv file: " + str(ex))
        return ingested_sample_dict(None, filename, warnings, errors)
    csv_in = flip_and_strip_whitespace(csv_in)
    data_frame, meta_frame, warnings, errors = split_data_and_metadata(
        csv_in, filename, warnings, errors
    )
    if len(errors) > 0:
        return ingested_sample_dict(None, filename, warnings, errors)
    # check for and handle multicolumn reflectance data
    # we simply strip unwanted empty columns off the end of the metadata frame
    # and split the data frame into a list of dataframes
    if data_frame.shape[1] > 2:
        meta_frame = meta_frame.iloc[:, 0:2]
        split_frames = []
        for refl_col in data_frame.columns:
            if refl_col == 0:
                continue
            split_frame = data_frame[[0, refl_col]]
            split_frame.columns = [0, 1]
            split_frames.append(split_frame)
        data_frame = split_frames

    # map metadata field names to fields of visor.models.Sample
    field_dict, warnings, errors = parse_csv_metadata(
        meta_frame, warnings, errors
    )
    # map metadata values for FOREIGN KEY / many-to-many fields to instances
    # of those objects in our database
    field_dict, warnings, errors = map_metadata_to_related_tables(
        field_dict, warnings, errors
    )
    field_dict |= {"import_notes": str(warnings), "filename": filename}
    if errors:
        return ingested_sample_dict(None, filename, warnings, errors)
    # split multicolumn data into a list of Sample objects
    if isinstance(data_frame, list):
        sample_out = []
        for ix, column in enumerate(data_frame):
            unique_items = {
                "reflectance": column,
                # add incrementing numbers to distinguish the columns
                "sample_id": field_dict["sample_id"] + "_" + str(ix),
            }
            sample_out.append(Sample(**(field_dict | unique_items)))
    # and make single-column data into a single Sample object
    else:
        sample_out = Sample(**(field_dict | {"reflectance": data_frame}))
    return {
        "sample": sample_out,
        "filename": filename,
        "warnings": warnings,
        "errors": None,
    }


def process_zipfile(input_stream: Union[IO, str]) -> dict:
    """
    top-level handler for user-facing "upload all the files you like in a
    compressed blob" functionality. attempts to process files, including
    multisample files, into samples, and to save passed images. this perhaps
    does too much, but we are required to handle a lot of options.
    returns a dictionary with a status code, errors, and information
    about successful and unsuccessful ingests (when available).
    """
    upload_errors = []
    # try opening the stream as a zip file
    try:
        zipped_file = zipfile.ZipFile(input_stream)
    # TODO, maybe: make this more specific?
    except Exception as error:
        upload_errors.append(
            "This doesn't seem to be a zip file. Please verify it and reload."
        )
        # also list the specific error for more interesting debugging
        upload_errors.append(f"{type(error)}:{error}")
        return {"status": "failed before ingest", "errors": upload_errors}
    manifest, upload_errors = classify_zip_file_contents(
        zipped_file, upload_errors
    )
    image_associations, upload_errors = associate_zipped_images(
        zipped_file, manifest, upload_errors
    )
    if upload_errors:
        return {"status": "failed before ingest", "errors": upload_errors}
    # if the zipped bundle looks ok, try to turn the files into Samples.
    # first, process the CSV files
    ingest_results = [
        ingest_sample_csv(zipped_file.open(file))
        for file in manifest["csv_files"]
    ]
    # separate successful and failed ingests
    good_results, bad_results = split_on(
        lambda result: result["errors"] is None, ingest_results
    )
    # check for and, if present, flatten multisamples
    good_results = flatten_multisamples(good_results)
    # add associated images
    good_results = add_images_to_results(image_associations, good_results)
    # clean each sample and save it into the database
    save_results = save_ingest_results_into_database(good_results)
    # separate samples that had errors at either stage from successful ones
    good_results, badly_saved_results = split_on(
        lambda result: result["errors"] is None, save_results
    )
    bad_results += badly_saved_results
    return make_dict_for_view_function(bad_results, good_results)


def process_csv_file(csv_file: Union[str, IO]) -> dict:
    """
    a simpler form of process_zipfile, intended for a single CSV file --
    doesn't need to be constantly interrupted to associate images and so on.
    """
    results = ingest_sample_csv(csv_file)
    if results["errors"] is not None:
        return {
            "status": "failed during ingest",
            "errors": results["errors"],
            "good": [],
            "bad": []
        }
    # check for and, if present, flatten multisamples
    results = flatten_multisamples([results])
    save_results = save_ingest_results_into_database(results)
    good_results, bad_results = split_on(
        lambda result: result["errors"] is None, save_results
    )
    return make_dict_for_view_function(bad_results, good_results)


def construct_export_zipfile(database_ids, export_sim, simulated_instrument):
    """
    assemble a .zip file containing CSV and, if available, image files for
    Samples with PKs corresponding to elements of database_ids and wrap it
    in an HttpReponse.
    """
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as buffer:
        write_samples_into_buffer(
            export_sim, buffer, database_ids, simulated_instrument
        )
    zip_buffer.seek(0)
    # name the zip file and send it as http
    date = dt.datetime.today().strftime("%y-%m-%d")
    response = HttpResponse(zip_buffer, content_type="application/zip")
    response["Content-Disposition"] = (
        "attachment; filename=spectra-%s.zip;" % date
    )
    return response
