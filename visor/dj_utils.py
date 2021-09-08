from functools import reduce, wraps, partial
from operator import and_, contains
from typing import Iterable, Callable

import numpy as np
from django.db import models

from visor.models import Sample

# queryset constructors


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
