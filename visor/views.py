from ast import literal_eval
from functools import reduce
import json
from operator import or_
from pathlib import Path
from typing import TYPE_CHECKING

from django.http import HttpResponse
from django.shortcuts import render
import PIL
from PIL import Image

from visor.io import handlers
from visor.search import (
    search_all_samples,
    paginate_results,
    perform_search_from_form,
)
from visor.forms import (
    UploadForm,
    AdminUploadImageForm,
    concealed_search_factory,
)
from visor.models import Database, Sample, FilterSet

if TYPE_CHECKING:
    from django.core.handlers.wsgi import WSGIRequest


def search(request: "WSGIRequest") -> HttpResponse:
    """
    render the search page with an empty search form.
    """
    page_params = {"search_formset": concealed_search_factory(request)}
    return render(request, "search.html", page_params)


def no_results(request: "WSGIRequest") -> HttpResponse:
    return render(
        request,
        "results.html",
        {
            "page_ids": None,
            "selected_ids": None,
            "page_choices": None,
            "page_results": None,
            "search_results": None,
            "search_formset": None,
        },
    )


def results(request: "WSGIRequest") -> HttpResponse:
    """
    view function used to render the results of searches, including page flips
    and sorts on columns.
    """
    if ("jump-button" in request.GET) and (request.GET["jump-to-page"] == ""):
        return HttpResponse(status=204)

    # selected_spectra = Sample.objects.none() # TODO: missing functionality?
    # deliver an empty page for malformed requests.
    # also deliver clean data for each form while we're at it.
    try:
        search_formset = concealed_search_factory(request)(request.GET)
        assert len(search_formset.forms) == 1
        search_form = search_formset.forms[0]
        assert search_form.is_valid()
    except AssertionError:
        return no_results(request)

    sort_params = request.GET.getlist("sort_params", ["sample_id"])
    search_results = Sample.objects.only(*Sample.searchable_fields)
    # hide unreleased samples from non-superusers
    if not request.user.is_superuser:
        search_results = search_results.filter(released=True)
    # TODO, maybe: have a cache somewhere of search result IDs? harder to
    #  deeplink. but it could be used iff the sort button was pressed? could
    #  it live in shared memory on the backend somewhere?
    # sort results, if this view function got accessed via a sort button
    search_results = search_results.order_by(*sort_params)
    # actually perform the search
    search_results = perform_search_from_form(search_form, search_results)
    selections = request.GET.getlist("selection")
    selected_spectra = Sample.objects.filter(id__in=selections)
    selected_list = []
    for spectra in selected_spectra:
        selected_list.append(spectra.id)
    search_results_id_list = []
    for result in search_results:
        search_results_id_list.append(result.id)
    page_choices, page_ids, page_results = paginate_results(
        request, search_results
    )
    return render(
        request,
        "results.html",
        {
            "search_formset": search_formset,
            "page_ids": page_ids,
            "selected_ids": selected_list,
            "page_choices": page_choices,
            "page_results": page_results,
            "search_results": search_results_id_list,
            "sort_params": sort_params,
        },
    )


def graph(request, template="graph.html") -> HttpResponse:
    if not request.method == "GET":
        return HttpResponse(status=204)
    if "graphForm" not in request.GET:
        return HttpResponse(status=204)
    selections = request.GET.getlist("selection")
    if not selections:
        return HttpResponse(status=204)
    search_formset = concealed_search_factory(request)(request.GET)

    samples = Sample.objects.filter(id__in=selections)

    dumplist = [obj.as_json() for obj in samples]

    json_string = json.dumps(dumplist)

    filtersets = [
        filterset.short_name
        for filterset in FilterSet.objects.all().order_by("display_order")
    ]
    # TODO: cruft?
    filtersets += [
        filterset.short_name + " (no illumination)"
        for filterset in FilterSet.objects.all().order_by("display_order")
    ]
    return render(
        request,
        template,
        {
            "selected_ids": selections,
            "graphResults": samples,
            "graphJSON": json_string,
            "search_formset": search_formset,
            "filtersets": filtersets,
        },
    )


def meta(request: "WSGIRequest") -> HttpResponse:
    if request.method == "GET":
        if "meta" not in request.GET:  # something's busted, just ignore it
            return HttpResponse(status=204)
        selections = request.GET.getlist("selection")
        prev_selected_list = request.GET.getlist("prev_selected")
        search_formset = concealed_search_factory(request)(request.GET)
        selections = list(set(selections + prev_selected_list))
        samples = Sample.objects.filter(id__in=selections)
        dictionaries = [obj.as_dict() for obj in samples]
        return render(
            request,
            "meta.html",
            {
                "search_formset": search_formset,
                "metaResults": samples,
                "reflectancedict": dictionaries,
            },
        )


def export(request: "WSGIRequest") -> HttpResponse:
    selections = request.GET.getlist("selection")
    export_sim = False
    if "do-we-export-sim" in request.GET:
        if request.GET["do-we-export-sim"] == "True":
            export_sim = True
    if export_sim:
        simulated_instrument = request.GET["sim-instrument-for-export"]
    else:
        simulated_instrument = ""
    selections = list(selections)
    return handlers.construct_export_zipfile(
        selections, export_sim, simulated_instrument
    )


def upload(request: "WSGIRequest") -> HttpResponse:
    form = UploadForm(request.POST, request.FILES)
    if not form.is_valid():
        form = UploadForm()
        return render(request, "upload.html", {"form": form})
    uploaded_file = request.FILES["file"]
    # these are separate cases mostly because we allow people to jam images
    # into zipped archives, which requires extra validation steps.
    if Path(uploaded_file.name).suffix == ".csv":
        upload_results = handlers.process_csv_file(uploaded_file)
    elif Path(uploaded_file.name).suffix == ".zip":
        upload_results = handlers.process_zipfile(uploaded_file)
    # we don't mess around with files that don't have one of those extensions
    else:
        return render(
            request,
            "upload.html",
            {
                "form": form,
                "headline": "File upload failed.",
                "upload_errors": ["Please upload a csv or zip file."],
            },
        )
    # this first case is mostly: we couldn't open the zip file or its contents
    # were badly organized; we didn't even try to parse anything
    if upload_results["status"] == "failed before ingest":
        return render(
            request,
            "upload.html",
            {
                "form": form,
                "upload_errors": upload_results["errors"]
            }
        )
    if upload_results["status"] == "failed during ingest":
        headline = "No samples uploaded successfully."
    elif upload_results["status"] == "partially successful":
        headline = "The following samples uploaded successfully:"
    else:
        headline = "Upload successful."
    return render(
        request,
        "upload.html",
        {
            "form": form,
            "successful": upload_results["good"],
            "unsuccessful": upload_results["bad"],
            "upload_errors": upload_results["errors"],
            "headline": headline,
        },
    )


def admin_upload_image(request, ids=None) -> HttpResponse:
    warn_multiple = False
    if ids:
        ids = literal_eval(ids)
        if len(ids) > 1:
            warn_multiple = True
    if request.method == "POST":
        form = AdminUploadImageForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                image = PIL.Image.open(request.FILES["file"])
            except (FileNotFoundError, PIL.UnidentifiedImageError):
                return HttpResponse("The image file couldn't be parsed.")
            samples = Sample.objects.filter(id__in=ids)
            for sample in samples:
                sample.image = image
                sample.clean()
                sample.save()
            return HttpResponse("Upload successful.")
            # maybe redirect to metadata
    else:
        form = AdminUploadImageForm()

    return render(
        request,
        "admin_upload_image.html",
        {"ids": ids, "form": form, "warn_multiple": warn_multiple},
    )


def about(request: "WSGIRequest") -> HttpResponse:
    databases = Database.objects.all()
    filtersets = FilterSet.objects.all().order_by("display_order")
    return render(
        request,
        "about.html",
        {"databases": databases, "filtersets": filtersets},
    )


def status(request: "WSGIRequest") -> HttpResponse:
    return render(request, "status.html")


def bulk_export(request: "WSGIRequest") -> HttpResponse:
    """
    specialized view function for a page inaccessible through HTML links.
    designed to be used for CLI access to the database.
    """
    bulk_results = Sample.objects.only("sample_name")
    if not request.user.is_superuser:
        bulk_results = bulk_results.filter(released=True)
    for field in ["sample_name"]:
        if field not in request.GET:
            continue
        entry = request.GET[field]
        if not entry:
            continue
        # "Any" entries do not restrict the search
        if entry == "Any":
            continue
        query = field + "__iexact"
        if Sample.objects.filter(**{query: entry}):
            bulk_results = bulk_results.filter(**{query: entry})
        # otherwise treat multiple words as an 'or' search
        else:
            query = field + "__icontains"
            filters = [
                bulk_results.filter(**{query: word})
                for word in entry.split(" ")
            ]
            bulk_results = reduce(or_, filters)
    if bulk_results:
        # 'search all fields' function
        if "any_field" in request.GET:
            bulk_results = bulk_results & search_all_samples(
                request.GET["any_field"]
            )
    search_results_id_list = [result.id for result in bulk_results]
    if "simulate" in request.GET:
        simulated_instrument = request.GET["simulate"].replace("_", " ")
        simulate = True
    else:
        simulated_instrument = ""
        simulate = False
    return construct_export_zipfile(
        search_results_id_list, simulate, simulated_instrument
    )
