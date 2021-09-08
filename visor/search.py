from functools import reduce
from itertools import chain

from django.db import models

from visor.dj_utils import or_query
from visor.models import Sample


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


def filter_results_for_wavelength_ranges(
    form_results, wavelength_query, wavelength_ranges
):
    requested_range = list(
        chain.from_iterable(
            [wavelength_ranges[range_name] for range_name in wavelength_query]
        )
    )
    maximum_minimum = requested_range[1]
    minimum_maximum = requested_range[-2]
    form_results = form_results.filter(min_reflectance__lte=maximum_minimum)
    form_results = form_results.filter(max_reflectance__gte=minimum_maximum)
    return form_results
