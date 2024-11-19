from functools import reduce, wraps, partial
from operator import and_, contains
from pathlib import Path
from typing import Iterable, Callable, Any, Sequence, Union

from django.db import models


# query abstractions

# note: PyTypeChecker can't identify model subclasses
def model_values(model: Any, attribute: str):
    return model.objects.values_list(attribute, flat=True)


def djget(
    model: Any,
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


def fields(model: Any) -> list[str]:
    return [field.name for field in model._meta.fields]


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
    # choice_data.insert(0, ("Any", "Any"))
    choice_data.insert(0, ("", ""))
    return choice_data


def eta(input_function: Callable, *args, kwarg_list=()) -> Callable:
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


def are_in(
    items: Iterable, oper: Callable = and_
) -> Callable[[Sequence], bool]:
    """
    returns a predicate function that evaluates to True iff evaluated on a
    sequence that contains all (or by changing oper, perhaps any) items
    """

    def in_it(container: Iterable) -> bool:
        inclusion = partial(contains, container)
        return reduce(oper, map(inclusion, items))

    return in_it


def extension_is(extension: str) -> Callable[[Union[str, Path]], bool]:
    """
    returns a predicate function that evaluates to True iff evaluated on a
    string or Path whose filetype extension matches "extension",
    e.g. extension_is(".txt")("buffer.txt") == True
    """

    def is_extension(fn):
        return Path(fn).suffix == extension

    return is_extension


def inverse(predicate: Callable[[Any], bool]) -> Callable[[Any], bool]:
    """
    given predicate f, return predicate g such that
    f(x) -> ~g(x) and g(x) -> ~f(x)
    """

    def inverted(*args, **kwargs):
        return not predicate(*args, **kwargs)

    return inverted


def split_on(
    predicate: Callable[[Any], bool], sequence: Sequence
) -> (list, list):
    """
    splits sequence into lists x and y such that
    1. predicate(a) is True for all a in x
    2. predicate(b) is False for all b in y
    """
    return (
        list(filter(predicate, sequence)),
        list(filter(inverse(predicate), sequence)),
    )


# def make_autocomplete_list(autocomplete_fields: dict):
#     """
#     format data to feed to jquery autocomplete.
#     currently vestigial but may become useful again later.
#     """
#     autocomplete_data = {}
#     for autocomplete_category in autocomplete_fields:
#         model = autocomplete_fields[autocomplete_category][0]
#         field = autocomplete_fields[autocomplete_category][1]
#         autocomplete_data[autocomplete_category] = [
#             name
#             for name in model.objects.values_list(field, flat=True)
#             .order_by(field)
#             .distinct()
#             if name != ""
#         ]
#     return autocomplete_data
