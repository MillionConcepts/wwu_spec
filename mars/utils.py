import zipfile
from functools import reduce

import pandas as pd
import numpy as np

from django.db import models
from django import forms
from django.forms.models import model_to_dict
from django.conf import settings

from mars.models import *

# queryset constructors


def or_query(first_query, second_query):
    return first_query | second_query


def search_all_samples(entry):
    queries = [
        {field.name + "__icontains": entry}
        for field in Sample._meta.fields
        if field.name not in ["origin", "sample_type", "id"]
    ]
    queries += [
        {field + "__name__icontains": entry} for field in ["origin", "sample_type"]
    ]
    filter_list = [Sample.objects.filter(**query) for query in queries]
    return reduce(or_query, filter_list)


# utilities for making lists to render in html


def make_choice_list(choice_fields):
    # data to feed to html selection fields
    choice_data = {}
    for choice_category in choice_fields:
        model = choice_fields[choice_category][0]
        field = choice_fields[choice_category][1]
        choice_data[choice_category] = [
            (c, c) for c in model.objects.values_list(field, flat=True)
        ]
        choice_data[choice_category].insert(0, ("Any", "Any"))
        return choice_data


def make_autocomplete_list(autocomplete_fields):
    # data to feed to jquery autocomplete
    autocomplete_data = {}
    for autocomplete_category in autocomplete_fields:
        model = autocomplete_fields[autocomplete_category][0]
        field = autocomplete_fields[autocomplete_category][1]
        autocomplete_data[autocomplete_category] = [
            name
            for name in model.objects.values_list(field, flat=True)
            .order_by(field)
            .distinct()
            if name != ""
        ]
    return autocomplete_data


# utilities for reading uploaded sample data


def parse_sample_csv(meta_array, warnings, errors):
    # maps rows from csv file to the fields of a Sample object
    # and throws errors if the csv file is formatted improperly

    # get_fields gets relations, fields does not

    field_dict = {}
    field_names = np.vstack(
        [
            np.array([field.name, field.verbose_name.lower()])
            for field in Sample._meta.fields
        ]
    )

    for column in meta_array.T:
        # check to see if the input field is in the model
        input_field = column[0].strip().lower()
        field_search = np.nonzero(input_field == field_names[:, 1])[0]
        # if it's not, check to see if it's empty or a legacy field
        if field_search.size == 0:
            if input_field == "nan":
                warnings.append(
                    "Warning: a row in the input was interpreted as NaN."
                    + " This is generally harmless and caused by idiosyncracies"
                    + " in how pandas.read_csv handles stray separators."
                )
            elif input_field == "data id":
                warnings.append(
                    "Warning: the Data ID field is recognized for legacy purposes but is not used by the"
                    + " database unless you have not provided a Sample ID."
                )
                field_dict["sample_id"] = column[1]
            elif input_field == "mineral name" or input_field == "sample name":
                warnings.append(
                    'Warning: the "'
                    + column[0]
                    + '" field is interpreted as "Sample Name."'
                )
                field_dict["sample_name"] = column[1]
            # and raise an error for extraneous fields
            else:
                errors.append(
                    column[0] + " is not a valid field name for this database."
                )
        elif field_search.size > 1:
            errors.append(
                "Error: " + column[0] + " appears to be assigned more than once."
            )
        else:
            active_field = field_names[field_search][0][0]
            if "reflectance" in active_field:
                warnings.append(
                    "The minimum and maximum reflectance fields are recognized for legacy purposes"
                    + " but the database actually computes these values from the reflectance data."
                )
            else:
                field_dict[active_field] = str(column[1]).strip()
    return field_dict, warnings, errors


def check_sample_csv(field_dict, warnings, errors):
    # maps upload text to the ForeignKey fields
    # creates database entries if not present
    # and assigns a sample ID if not present
    if "sample_type" in field_dict.keys():
        if field_dict["sample_type"] not in [
            sample_type.typeOfSample for sample_type in SampleType.objects.all()
        ]:
            errors.append(
                field_dict["sample_type"] + " is not an allowable sample type."
            )
        else:
            field_dict["sample_type"] = SampleType.objects.get(
                typeOfSample=field_dict["sample_type"]
            )
    if "origin" in field_dict.keys():
        if field_dict["origin"] not in [
            database.name for database in Database.objects.all()
        ]:
            active_database = str(field_dict["origin"]).strip()
            warnings.append(
                active_database
                + " was not previously listed among our affiliate databases and has been added as a database of origin."
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
            "assigned the placeholder identifier " + field_dict["sample_id"] + "."
        )
    return field_dict, warnings, errors


def ingest_sample_csv(csv_file):
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
            'Error: the "Wavelength" separator wasn\'t found in ' + filename + "."
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
    except:
        errors.append(
            "Error: some fields in the reflectance data can't be interpreted as numbers. "
            + "It's possible that you haven't placed the reflectance data after all of the "
            "metadata, or that there are some non-numeric characters in the reflectance data."
        )

    ## check for and handle multicolumn reflectance data

    sample_split = False
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
    field_dict = dict(**field_dict, **{"filename": filename})
    checked_csv = check_sample_csv(field_dict, warnings, errors)
    field_dict = checked_csv[0]
    warnings = checked_csv[1]
    errors = checked_csv[2]
    field_dict = dict(**field_dict, **{"import_notes": str(warnings)})

    # split multicolumn data into multiple Sample objects

    if sample_split:
        sample_out = [
            Sample(**dict(**field_dict, **{"reflectance": sample})) for sample in split_refl
        ]
    else:
        sample_out = Sample(**dict(**field_dict, **{"reflectance": refl_array}))

    if errors != []:
        return {
            "sample": None,
            "filename": filename,
            "warnings": warnings,
            "errors": errors,
        }
    return {
        "sample": sample_out,
        "filename": filename,
        "warnings": None,
        "errors": None,
    }


def handle_csv_upload(csv_file):
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

    print(type(sample))

    
    # flatten multisample
    if type(sample) == list:
        flat_samples = []
        for active_sample in sample:
            flat_samples.append({
                'sample':active_sample,
                'filename':csv_file.name,
                'errors': None
            })
        return flat_samples

    return [{"sample": sample, "filename": csv_file.name, "errors": None}]

def check_zip_structure(zipped_file,upload_errors):

    uploaded_files = zipped_file.namelist()

    csv_files = [file for file in uploaded_files if file[-3:] == "csv"]
    jpg_files = [file for file in uploaded_files if file[-3:] == "jpg"]
    other_files = [file for file in uploaded_files if file[-3:] not in ["csv", "jpg"]]

    # check for inappropriate filetypes

    if other_files:
        upload_errors.append(
            "There are files that do not have a csv or jpg extension in the upload."
            + " Please correct this and reload."
        )
    if len(csv_files) != len(set(csv_files)):
        upload_errors.append(
            "There appear to be duplicate csv filenames in the upload."
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
                + "Has the same name as a csv file but doesn't appear to be a JPEG"
                + " image. Please remove it from the zip file and reload."
            )
        else:
            matching_csv_file = [
                csv_file for csv_file in csv_files if csv_file[:-4] == jpg_file[:-4]
            ][0]
            try:
                matching_image = PIL.Image.open(zipped_file.open(jpg_file))
                image_associations[matching_csv_file] = matching_image
            except Exception as ex:
                upload_errors.append(
                    jpg_file
                    + " does not appear to be a valid image file."
                    + " Please verify it and reload."
                )
    return {"upload_errors":upload_errors,"jpg_files":jpg_files,"csv_files":csv_files,"image_associations":image_associations}


def handle_zipped_upload(zipped_file):
    upload_errors = []

    # try opening the file
    try:
        zipped_file = zipfile.ZipFile(zipped_file)
    except Exception as ex:
        upload_errors.append(
            "The input can't be parsed as a zip file." + " Please verify it and reload."
        )
        upload_errors.append(ex)
        return [0, upload_errors]
    
    check = check_zip_structure(zipped_file,upload_errors)
    upload_errors = check["upload_errors"]
    csv_files = check["csv_files"]
    jpg_files = check["jpg_files"]
    image_associations = check["image_associations"]
    if upload_errors:
        return [0, upload_errors]

    # if all the files are ok as files, go ahead and check them against the model

    # process the CSV and see if there are problems there

    samples = []
    samples = [ingest_sample_csv(zipped_file.open(file)) for file in csv_files]

    # log samples that were successful and erroneous at this stage

    erroneous_samples = [sample for sample in samples if sample["errors"] is not None]
    successful_samples = [sample for sample in samples if sample["errors"] is None]

    # flatten sample list in case of multicolumn uploads

    single_samples = [samp for samp in successful_samples if type(samp["sample"]) != list]
    multi_samples = [samplist for samplist in successful_samples if type(samplist["sample"]) == list]
    flat_samples = []
    for multi_sample in multi_samples:
        for sample in multi_sample["sample"]:
            flat_samples.append({
                'sample':sample,
                'filename':multi_sample['filename'],
                'warnings':multi_sample['warnings'],
                'errors':multi_sample['errors']
            })
    successful_samples = single_samples + flat_samples

    for sample in successful_samples:
        if sample["sample"].filename in image_associations.keys():
            sample["sample"].image = image_associations[sample["sample"].filename]

    # check against the model's main clean and save methods; also, you know, save

    for sample in successful_samples:
        try:
            sample["sample"].clean()
            sample["sample"].save(uploaded=True)
        except Exception as ex:
            sample["errors"] = str(ex)

    # divide samples that had errors at either stage from those that saved successfully

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
