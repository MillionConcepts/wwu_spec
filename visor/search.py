import ast
import warnings
from collections import defaultdict
from functools import reduce
from itertools import chain
from operator import or_

from django.core.paginator import Paginator
from django.db import models
from dustgoggles.func import gmap
from numpy import inf

from visor.constants import WAVELENGTH_RANGES
from visor.models import Sample, Library


def search_all_samples(entry: str) -> models.QuerySet:
    queries = [
        {field.name + "__icontains": entry}
        for field in Sample._meta.fields
        if field.name not in list(Sample.unprintable_fields) + [
            "origin",
            "sample_type",
            "min_wavelength",
            "max_wavelength",
            "date_added"
        ]
    ]
    queries += [
        {field + "__name__icontains": entry}
        for field in ["origin", "sample_type"]
    ]
    filter_list = [Sample.objects.filter(**query) for query in queries]
    return reduce(or_, filter_list)


def wavelength_range_filter(form_results, wavelength_query):
    requested_range = list(
        chain.from_iterable(
            [WAVELENGTH_RANGES[range_name] for range_name in wavelength_query]
        )
    )
    maximum_minimum = requested_range[1]
    minimum_maximum = requested_range[-2]
    form_results = form_results.filter(min_wavelength__lte=maximum_minimum)
    form_results = form_results.filter(max_wavelength__gte=minimum_maximum)
    return form_results


def make_grain_size_dicts(search_results):
    values = search_results.values('grain_size', 'id')
    nums, objs, unk = defaultdict(set), set(), set()
    unknown = {'Unknown', 'Unspecified Particulate', ''}
    for v in values:
        # TODO: this replace() should not be necessary. db needs cleaning.
        i, g = v['id'], v['grain_size'].replace("_", ",")
        if g.startswith("("):
            tup = ast.literal_eval(g)
            if quant := {g for g in tup if isinstance(g, float)}:
                nums[i].update(quant)
            if unknown.intersection(g):
                unk.add(i)
            elif "Whole Object" in g:
                objs.add(i)
        elif g in unknown:
            unk.add(i)
        elif g == "Whole Object":
            objs.add(i)
        elif g.replace('.', '').isnumeric():
            nums[i].add(float(g))
        else:
            warnings.warn(f"invalid size string {g} for sample with pk {i}")
    return nums, objs, unk

def noneinf(x, ishigh=True):
    if x is not None:
        return x
    if ishigh is True:
        return inf
    return -inf

def match_num_ranges(nums, size_ranges):
    matches, use_range = set(), []
    size_ranges = [(noneinf(a, False), noneinf(b)) for a, b in size_ranges]
    for i, g in nums.items():
        for size_range in size_ranges:
            try:
                if (min(g) >= size_range[0]) and (max(g) <= size_range[1]):
                    matches.add(i)
                    break
            except ValueError:
                continue
    return matches


def size_filter(search_results, sizes):
    matches = set()
    nums, objs, unk = make_grain_size_dicts(search_results)
    if size_ranges := [t for t in sizes if isinstance(t, tuple)]:
        matches.update(match_num_ranges(nums, size_ranges))
    if "Whole Object" in sizes:
        matches.update(objs)
    if None in sizes:
        matches.update(unk)
    return search_results.filter(id__in=matches)


def qual_field_filter(field, entry, search_results):
    # library is handled differently because it is a many-to-many
    # relation.
    if field == "library":
        library = Library.objects.get(name__exact=entry)
        return search_results & library.sample_set.all()
    # require exact phrase searches for choice fields,
    # don't waste time checking any other possibilities
    query = field + "__in"
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
    # Allow user to specify results per page
    if "update-page-size" in request.GET or "results-per-page" in request.GET:
        try:
            results_per_page = int(request.GET.get("results-per-page", 15))
            results_per_page = max(5, min(100, results_per_page))
        except (ValueError, TypeError):
            results_per_page = 15
    else:
        results_per_page = 15
    
    paginator = Paginator(search_results, results_per_page)
    if "jump-button" in request.GET:
        page_selected = max(1, int(request.GET.get("jump-to-page")))
        page_selected = min(paginator.num_pages, page_selected)
    elif "update-page-size" in request.GET:
        page_selected = 1 # Resets to page 1 if num results/page changes to prevent bug caused by user from viewing a page with 0 results 
    else:
        page_selected = int(request.GET.get("page_selected", 1))
    page_results = paginator.page(page_selected)
    page_choices = range(
        max(1, page_selected - 6),
        min(page_selected + 6, paginator.num_pages+1), # Requested to display last partially full page
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
        if entry in [None, "Any", '', []]:
            continue
        search_results = qual_field_filter(field, entry, search_results)
    wavelength_query = search_form.cleaned_data.get("wavelength_range")
    if wavelength_query:
        search_results = wavelength_range_filter(
            search_results, wavelength_query
        )
    if (sizes := search_form.cleaned_data.get("sizes")) is not None:
        sizes = gmap(
            lambda s: ast.literal_eval(s), filter(lambda s: s != "", sizes)
        )
        if sizes != ():
            search_results = size_filter(search_results, sizes)
    # don't bother continuing if we're already empty
    if search_results:
        # 'search all fields' function
        entry = search_form.cleaned_data.get("any_field", None)
        if entry is not None:
            search_results = search_results & search_all_samples(entry)
    return search_results.distinct()
