from ast import literal_eval
from functools import reduce
import json
import logging
from operator import or_
from pathlib import Path
import random
from typing import TYPE_CHECKING

from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
import PIL
from PIL import Image

from notetaking.notepad import Notepad
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

logger = logging.getLogger("django")


def ip(request):
    # forwarded ip from server layer -- this specific property may only
    # be populated by nginx
    forwarded_ip = request.META.get('HTTP_X_REAL_IP')
    if forwarded_ip is not None:
        return forwarded_ip
    return request.META.get('REMOTE_ADDR')


def session_id(request):
    address = ip(request)
    if request.session.get('identifier') is None:
        request.session[
            'identifier'
        ] = f"{address}_{random.randint(1000000, 9999999)}"
        logger.warning(
            f"started session with identifier "
            f"{request.session['identifier']}"
        )
    return request.session['identifier']


def get_inventory_id_json(request) -> str:
    try:
        user_notes = Notepad(session_id(request))
    except FileNotFoundError:
        user_notes = Notepad.open(session_id(request))
        user_notes['inventory'] = "[]"
    return user_notes['inventory']


def set_inventory_id_json(request) -> None:
    inventory_ids = request.GET.get("inventory")
    try:
        user_notes = Notepad(session_id(request))
    except FileNotFoundError:
        user_notes = Notepad.open(session_id(request))
    user_notes['inventory'] = inventory_ids


def load_inventory(inventory_id_json: str) -> str:
    inventory_id_list = json.loads(inventory_id_json)
    inventory_samples = Sample.objects.filter(id__in=inventory_id_list)
    return json.dumps(
        [sample.as_json(brief=True) for sample in inventory_samples]
    )


@never_cache
def inventory_check(request):
    return HttpResponse(load_inventory(get_inventory_id_json(request)))


@never_cache
def inventory(request: "WSGIRequest") -> HttpResponse:
    set_inventory_id_json(request)
    return HttpResponse(status=204)


@never_cache
def search(request: "WSGIRequest") -> HttpResponse:
    """
    render the search page with an empty search form.
    """
    page_params = {
        "search_formset": concealed_search_factory(request),
        "sample_json": "[]",
        "inventory_json": load_inventory(get_inventory_id_json(request))
    }
    response = render(request, "search.html", page_params)
    return response


@never_cache
def no_results(request: "WSGIRequest") -> HttpResponse:
    response = render(
        request,
        "results.html",
        {
            "page_ids": None,
            "selected_ids": None,
            "page_choices": None,
            "page_results": None,
            "search_results": None,
            "search_formset": None,
            "sample_json": "[]",
            "inventory_json": load_inventory(get_inventory_id_json(request))
        }
    )
    return response


@never_cache
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

    sort_params = request.GET.getlist("sort_params", ["sample_name"])
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
    # Todo: when does this happen?
    selections = get_selections(request)
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
    sample_json = json.dumps(
        [sample.as_json(brief=True) for sample in page_results.object_list]
    )
    response = render(
        request,
        "results.html",
        {
            "search_formset": search_formset,
            "page_ids": page_ids,
            "selected_ids": selected_list,
            "page_choices": page_choices,
            "page_results": page_results,
            "sample_json": sample_json,
            "inventory_json": load_inventory(get_inventory_id_json(request)),
            "search_results": search_results_id_list,
            "sort_params": sort_params,
        }
    )
    return response


def get_selections(request):
    try:
        selection_key = next(
            filter(lambda k: k.endswith("selection"), request.GET.keys())
        )
        return request.GET.getlist(selection_key)
    except StopIteration:
        return []


@never_cache
def graph(request, template="graph.html") -> HttpResponse:
    if not request.method == "GET":
        return HttpResponse(status=204)
    if "graph" not in request.GET:
        return HttpResponse(status=204)
    if not (selections := get_selections(request)):
        return HttpResponse(status=204)

    search_formset = concealed_search_factory(request)(request.GET)
    samples = Sample.objects.filter(id__in=selections)
    sample_json = json.dumps([sample.as_json() for sample in samples])
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
            "sample_json": sample_json,
            "inventory_json": load_inventory(get_inventory_id_json(request)),
            "search_formset": search_formset,
            "filtersets": filtersets,
        }
    )


@never_cache
def meta(request: "WSGIRequest") -> HttpResponse:
    if request.method == "GET":
        if "meta" not in request.GET:  # something's busted, just ignore it
            return HttpResponse(status=204)
        if not (selections := get_selections(request)):
            return HttpResponse(status=204)
        search_formset = concealed_search_factory(request)(request.GET)
        samples = Sample.objects.filter(id__in=selections)
        dictionaries = [obj.as_dict() for obj in samples]
        sample_json = json.dumps(
            [sample.as_json(brief=True) for sample in samples]
        )
        response = render(
            request,
            "meta.html",
            {
                "search_formset": search_formset,
                "metaResults": samples,
                "reflectancedict": dictionaries,
                "sample_json": sample_json,
                "inventory_json": load_inventory(get_inventory_id_json(request)),
            }
        )
        return response


@never_cache
def export(request: "WSGIRequest") -> HttpResponse:
    if not (selections := get_selections(request)):
        return HttpResponse(status=204)
    export_sim = False
    if "do-we-export-sim" in request.GET:
        if request.GET["do-we-export-sim"] == "True":
            export_sim = True
    if export_sim:
        simulated_instrument = request.GET["sim-instrument-for-export"]
    else:
        simulated_instrument = ""
    return handlers.construct_export_zipfile(
        selections, export_sim, simulated_instrument
    )


@never_cache
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
            {"form": form, "upload_errors": upload_results["errors"]},
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


@never_cache
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
        {
            "ids": ids,
            "form": form,
            "warn_multiple": warn_multiple,
        },
    )


@never_cache
def about(request: "WSGIRequest") -> HttpResponse:
    databases = Database.objects.all()
    filtersets = FilterSet.objects.all().order_by("display_order")
    return render(
        request,
        "about.html",
        {
            "databases": databases,
            "filtersets": filtersets,
        },
    )


@never_cache
def status(request: "WSGIRequest") -> HttpResponse:
    return render(
        request,
        "status.html",
    )


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
    return handlers.construct_export_zipfile(
        search_results_id_list, simulate, simulated_instrument
    )
