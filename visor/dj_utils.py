import zipfile
from functools import reduce, wraps, partial
from operator import and_, contains
from typing import Union, Any, IO, Iterable, Callable

import PIL
import numpy as np
import pandas as pd
from PIL import Image
from django.db import models

# queryset constructors
from visor.models import Sample, SampleType, Database


def qlist(queryset: models.QuerySet, attribute: str):
    return list(queryset.values_list(attribute, flat=True))


# PyTypeChecker can't identify model subclasses
def djget(
    model,
    value: str,
    field: str = "name",
    method_name: str = "filter",
    querytype: str = "iexact",
) -> models.QuerySet:
    """flexible interface to queryset methods"""
    # get the requested queryset-generating method of model.objects
    method = getattr(model.objects, method_name)
    # and then evaluate it on the requested parameters
    return method(**{field + "__" + querytype: value})


def modeldict(django_model_object: models.Model) -> dict:
    """tries to construct a dictionary from arbitrary django model instance"""
    return {
        field.name: getattr(django_model_object, field.name)
        for field in django_model_object._meta.get_fields()
    }


def unique_values(queryset: models.QuerySet, field: str) -> set:
    return set([entry[field] for entry in list(queryset.values(field))])


# PyTypeChecker can't identify model subclasses
def fields(model) -> list[str]:
    return [field.name for field in model._meta.fields]


def or_query(
    first_query: models.QuerySet, second_query: models.QuerySet
) -> models.QuerySet:
    return first_query | second_query


def search_all_samples(entry: str) -> models.QuerySet:
    queries = [
        {field.name + "__icontains": entry}
        for field in Sample._meta.fields
        if field.name not in ["origin", "sample_type", "id"]
    ]
    queries += [
        {field + "__name__icontains": entry}
        for field in ["origin", "sample_type"]
    ]
    filter_list = [Sample.objects.filter(**query) for query in queries]
    return reduce(or_query, filter_list)


# utilities for making lists to render in html


def make_choice_list(
    model: models.Model, field: str, conceal_unreleased=False
) -> list[tuple]:
    """
    format data to feed to html selection fields.
    used by forms.SearchForm
    """
    queryset: models.query.QuerySet  # just a type hint, for secret reasons
    if conceal_unreleased and ("released" in fields(model)):
        queryset = model.objects.filter(released=True)
    else:
        queryset = model.objects.all()
    choice_data = [(c, c) for c in queryset.values_list(field, flat=True)]
    choice_data.insert(0, ("Any", "Any"))
    return choice_data


def make_autocomplete_list(autocomplete_fields: dict):
    """
    format data to feed to jquery autocomplete.
    currently vestigial but may become useful again later.
    """
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


def parse_sample_csv(meta_array: np.ndarray, warnings: list, errors: list):
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
                    + "This is generally harmless and caused by "
                    "idiosyncracies "
                    + " in how pandas.read_csv handles stray separators."
                )
            elif input_field == "data id":
                warnings.append(
                    "Warning: the Data ID field is recognized for legacy "
                    "purposes but is not used by the"
                    + " database unless you have not provided a Sample ID."
                )
                field_dict["sample_id"] = column[1]
            elif input_field == "mineral name" or input_field == "sample name":
                warnings.append(
                    "Warning: the "
                    + column[0]
                    + " field is interpreted as sample name."
                )
                field_dict["sample_name"] = column[1]
            # and raise an error for extraneous fields
            else:
                errors.append(
                    column[0] + " is not a valid field name for this database."
                )
        elif field_search.size > 1:
            errors.append(
                "Error: "
                + column[0]
                + " appears to be assigned more than once."
            )
        else:
            if column[1] == "nan":
                continue
            active_field = field_names[field_search][0][0]
            if "reflectance" in active_field:
                warnings.append(
                    "The minimum and maximum reflectance fields are "
                    "recognized for legacy purposes but the database actually"
                    " computes these values from the reflectance data."
                )
            # elif np.isnan(column[1]):
            #     continue
            else:
                field_dict[active_field] = str(column[1]).strip()
    return field_dict, warnings, errors


def check_sample_csv(
    field_dict: dict, warnings: list, errors: list
) -> (dict, list, list):
    # maps upload text to the ForeignKey fields
    # creates database entries if not present
    # and assigns a sample ID if not present
    if "sample_type" in field_dict.keys():
        if field_dict["sample_type"] not in [
            sample_type.name
            for sample_type in SampleType.objects.all()
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


# TODO: investigate control flow here as part of refactoring
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


"""
TODO: the way that this semiautomatically generated return signature looks 
suggests to me that I should refactor this code.
"""


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


# generic


def eta(input_function, *args, kwarg_list=()):
    """
    create an eta abstraction g of input function with arbitrary argument
    ordering. positional arguments to g _after_ the arguments defined in
    kwarg_list are mapped to positional arguments of input_function; all
    keyword arguments to g are mapped to keyword arguments of input_function.
    positional arguments to g matching keywords in kwarg_list override keyword
    arguments to g.

    can be used to make short forms of functions. also useful along with
    partial to create partially applied versions of functions free from
    argument collision.

    passing eta a function with no further arguments simply produces an alias.

    note that because keyword mapping incurs some (very small) performance
    cost at runtime, it may be inadvisable to use this on a function that is
    to be called many times.
    """
    if not (args or kwarg_list):
        # with no arguments, just alias input_function. the remainder of the
        # function accomplishes basically this, but just passing the function
        # is cheaper
        return input_function
    kwarg_list = args + tuple(kwarg_list)

    @wraps(input_function)
    def do_it(*do_args, **do_kwargs):
        output_kwargs = {}
        positionals = []
        # are there more args than the eta-defined argument list? pass them to
        # input_function.
        if len(do_args) > len(kwarg_list):
            positionals = do_args[len(kwarg_list) :]
        # do we have an argument list? then zip it with args up to its
        # length.
        if kwarg_list:
            output_kwargs = dict(
                zip(kwarg_list[: len(kwarg_list)], do_args[: len(kwarg_list)])
            )
        # do we have kwargs? merge them with the keyword dictionary generated
        # from do_it's args.
        if do_kwargs:
            output_kwargs = do_kwargs | output_kwargs
        if not output_kwargs:
            return input_function(*positionals)
        return input_function(*positionals, **output_kwargs)

    return do_it


def are_in(items: Iterable, oper: Callable = and_) -> Callable:
    """
    iterable -> function
    returns function that checks if its single argument contains all
    (or by changing oper, perhaps any) items
    """

    def in_it(container: Iterable) -> bool:
        inclusion = partial(contains, container)
        return reduce(oper, map(inclusion, items))

    return in_it
