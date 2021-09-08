from functools import reduce
from itertools import chain
from operator import or_

from django.core.paginator import Paginator
from django.db import models

from visor.constants import WAVELENGTH_RANGES
from visor.dj_utils import or_query
from visor.models import Sample, Library


def search_all_samples(entry: str) -> models.QuerySet:
    queries = [
        {field.name + "__icontains": entry}
        for field in Sample._meta.fields
        if field.name not in list(Sample.unprintable_fields) + [
            "origin",
            "sample_type",
            "min_reflectance",
            "max_reflectance",
            "date_added"
        ]
    ]
    queries += [
        {field + "__name__icontains": entry}
        for field in ["origin", "sample_type"]
    ]
    filter_list = [Sample.objects.filter(**query) for query in queries]
    return reduce(or_query, filter_list)


def wavelength_range_filter(form_results, wavelength_query):
    requested_range = list(
        chain.from_iterable(
            [WAVELENGTH_RANGES[range_name] for range_name in wavelength_query]
        )
    )
    maximum_minimum = requested_range[1]
    minimum_maximum = requested_range[-2]
    form_results = form_results.filter(min_reflectance__lte=maximum_minimum)
    form_results = form_results.filter(max_reflectance__gte=minimum_maximum)
    return form_results


def qual_field_filter(field, entry, search_results):
    # library is handled differently because it is a many-to-many
    # relation.
    if field == "library":
        library = Library.objects.get(name__exact=entry)
        return search_results & library.sample_set.all()
    # require exact phrase searches for choice fields,
    # don't waste time checking any other possibilities
    query = field + "__iexact"
    if field in Sample.choice_fields:
        search_results = search_results.filter(**{query: entry})
    # use an inflexible search for other fields
    # if an exact phrase match exists in the currently-selected corpus
    # NOTE: making this form_results.filter rather than
    # Sample.objects.filter would (1) make it slightly more permissive
    # and (2) make ordering of fields in this loop matter
    elif Sample.objects.filter(**{query: entry}):
        search_results = search_results.filter(**{query: entry})
    # otherwise treat multiple words as an 'or' search
    else:
        query = field + "__icontains"
        filters = [
            search_results.filter(**{query: word})
            for word in entry.split(" ")
        ]
        search_results = reduce(or_, filters)
    return search_results


def paginate_results(request, search_results):
    paginator = Paginator(search_results, 10)
    if "jump-button" in request.GET:
        page_selected = max(1, int(request.GET.get("jump-to-page")))
        page_selected = min(paginator.num_pages, page_selected)
    else:
        page_selected = int(request.GET.get("page_selected", 1))
    page_results = paginator.page(page_selected)
    page_choices = range(
        max(1, page_selected - 6),
        min(page_selected + 6, paginator.num_pages),
    )
    page_ids = []
    for sample in page_results.object_list:
        page_ids.append(sample.id)
    return page_choices, page_ids, page_results


def perform_search_from_form(search_form, search_results):
    for field in (
            Sample.phrase_fields + Sample.choice_fields + Sample.m2m_managers
    ):
        entry = search_form.cleaned_data.get(field, None)
        # "Any" entries do not restrict the search, nor do empty form fields
        if entry in [None, "Any"]:
            continue
        search_results = qual_field_filter(field, entry, search_results)
    wavelength_query = search_form.cleaned_data.get("wavelength_range")
    if wavelength_query:
        search_results = wavelength_range_filter(
            search_results, wavelength_query
        )
    # don't bother continuing if we're already empty
    if search_results:
        # 'search all fields' function
        entry = search_form.cleaned_data.get("any_field", None)
        if entry is not None:
            search_results = search_results & search_all_samples(entry)
    return search_results