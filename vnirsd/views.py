import csv
import datetime as dt
import io
import json
import zipfile
from ast import literal_eval
from functools import reduce
from itertools import chain
from operator import or_

import pandas as pd
import PIL
from PIL import Image
from django.conf import settings
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render

from vnirsd.dj_utils import (
    search_all_samples,
    handle_csv_upload,
    handle_zipped_upload,
)
from vnirsd.forms import (
    UploadForm,
    AdminUploadImageForm,
    concealed_search_factory,
)
from vnirsd.models import Database, Sample, FilterSet, Library


def search(request) -> HttpResponse:
    """
    render the search page with an empty search form.
    presently doesn't do any other manipulation (some former
    features determined crufty and cut)
    """
    page_params = {"search_formset": concealed_search_factory(request)}
    return render(request, "search.html", page_params)


def results(request) -> HttpResponse:
    if ('jump-button' in request.GET) and (request.GET['jump-to-page'] == ""):
        return HttpResponse(status=204)
    search_results_id_list = []
    search_results = Sample.objects.none()
    # selected_spectra = Sample.objects.none() # TODO: missing functionality?
    # deliver an empty page for malformed requests.
    # also deliver clean data for each form while we're at it.
    try:
        search_formset = concealed_search_factory(request)(request.GET)
        assert len(search_formset.forms) == 1
        search_form = search_formset.forms[0]
        assert search_form.is_valid()
    except AssertionError:
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

    sort_params = request.GET.getlist("sort_params", ["sample_id"])

    # double underscore in these field names is an ugly but compact way to
    # access the ForeignKey object fields

    phrase_fields = ["sample_name"]
    choice_fields = ["origin__name", "sample_type__name"]
    numeric_fields = ["min_reflectance", "max_reflectance"]
    m2m_managers = ["library"]
    searchable_fields = phrase_fields + choice_fields + numeric_fields
    form_results = Sample.objects.only(*searchable_fields)

    if not request.user.is_superuser:
        form_results = form_results.filter(released=True)

    form_results = form_results.order_by(*sort_params)

    for field in phrase_fields + choice_fields + m2m_managers:
        entry = search_form.cleaned_data.get(field, None)
        if not entry:
            continue
        # "Any" entries do not restrict the search
        if entry == "Any":
            continue
        # library is handled differently because it is a many-to-many
        # relation.
        if field == "library":
            library = Library.objects.get(name__exact=entry)
            form_results = form_results & library.sample_set.all()
            continue
        # require exact phrase searches for choice fields,
        # don't waste time checking any other possibilities
        query = field + "__iexact"
        if field in choice_fields:
            form_results = form_results.filter(**{query: entry})
        # use an inflexible search for other fields
        # if an exact phrase match exists in the currently-
        # selected corpus
        # NOTE: making this form_results.filter rather than
        # Sample.objects.filter would (1) make it slightly more permissive
        # and (2) means that ordering of fields in this loop matters
        elif Sample.objects.filter(**{query: entry}):
            form_results = form_results.filter(**{query: entry})
        # otherwise treat multiple words as an 'or' search
        else:
            query = field + "__icontains"
            filters = [
                form_results.filter(**{query: word})
                for word in entry.split(" ")
            ]
            form_results = reduce(or_, filters)

    # NOTE: this function assumes that there are no large gaps in
    # wavelength coverage within a given lab spectrum; i.e., that if a
    # spectrum has both UVA and NIR, it also has VIS. if this becomes a bad
    # assumption, we will need to modify it.
    wavelength_ranges = {
        "UVB": [0, 314],
        "UVA": [315, 399],
        "VIS": [400, 749],
        "NIR": [750, 2500],
        "MIR": [2501, 10000000],
    }

    wavelength_query = search_form.cleaned_data.get("wavelength_range")
    if wavelength_query:
        requested_range = list(
            chain.from_iterable(
                [
                    wavelength_ranges[range_name]
                    for range_name in wavelength_query
                ]
            )
        )
        maximum_minimum = requested_range[1]
        minimum_maximum = requested_range[-2]
        form_results = form_results.filter(
            min_reflectance__lte=maximum_minimum
        )
        form_results = form_results.filter(
            max_reflectance__gte=minimum_maximum
        )
    # don't bother continuing if we're already empty
    if form_results:
        # 'search all fields' function
        entry = search_form.cleaned_data.get("any_field")
        if entry:
            form_results = form_results & search_all_samples(entry)
    search_results = search_results | form_results

    selections = request.GET.getlist("selection")

    selected_spectra = Sample.objects.filter(id__in=selections)

    selected_list = []
    for spectra in selected_spectra:
        selected_list.append(spectra.id)

    for result in search_results:
        search_results_id_list.append(result.id)

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
    # TODO: cruft?
    # prev_selected_list = request.GET.getlist("prev_selected")
    # selections = list(set(selections + prev_selected_list))
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


# debug
def graph_future(request):
    return graph(request, "graph_future.html")


def meta(request) -> HttpResponse:
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


def write_sample_csv(field_list, sample):
    text_buffer = io.StringIO()
    writer = csv.writer(text_buffer)
    for field in field_list:
        if field[1] not in [
            "image",
            "id",
            "reflectance",
            "filename",
            "import_notes",
            "flagged",
            "simulated_spectra"
        ]:
            writer.writerow([field[0], getattr(sample, field[1])])
    return writer, text_buffer


def construct_export_zipfile(selections, export_sim, simulated_instrument):
    samples = Sample.objects.filter(id__in=selections)
    zip_buffer = io.BytesIO()
    field_list = [
        [field.verbose_name, field.name] for field in Sample._meta.fields
    ]
    field_list.sort()

    with zipfile.ZipFile(zip_buffer, "w") as output:
        # write each sample line-by-line into text buffer,
        # also splitting reflectance dictionary into lines
        for sample in samples:
            writer, text_buffer = write_sample_csv(field_list, sample)
            writer.writerow(["Wavelength", "Response"])
            for row in literal_eval(sample.reflectance):
                writer.writerow([row[0], row[1]])
            text_buffer.seek(0)
            # write sample into zip buffer
            output.writestr(
                sample.sample_id.replace("/", "_") + ".csv", text_buffer.read()
            )
            if export_sim:
                writer, text_buffer = write_sample_csv(field_list, sample)
                sims = sample.get_simulated_spectra()
                illuminated_df = pd.DataFrame(sims[simulated_instrument])
                dark_series = sims[simulated_instrument + "_no_illumination"][
                    "response"
                ].values()
                illuminated_df['unilluminated_response'] = dark_series
                illuminated_df.columns = ['filter', 'wavelength',
                                          'solar_illuminated_response',
                                          'response']
                illuminated_df.to_csv(text_buffer, index=False)
                text_buffer.seek(0)
                output.writestr(
                    sample.sample_id.replace("/", "_")
                    + "_simulated_"
                    + simulated_instrument
                    + ".csv",
                    text_buffer.read(),
                )
            # write image into zip buffer
            if sample.image:
                filename = settings.SAMPLE_IMAGE_PATH + "/" + sample.image
                output.write(filename, arcname=sample.image)
    zip_buffer.seek(0)

    # name the zip file and send it as http

    date = dt.datetime.today().strftime("%y-%m-%d")
    response = HttpResponse(zip_buffer, content_type="application/zip")
    response["Content-Disposition"] = (
            "attachment; filename=spectra-%s.zip;" % date
    )
    return response


def export(request) -> HttpResponse:
    selections = request.GET.getlist("selection")
    export_sim = False
    if 'do-we-export-sim' in request.GET:
        if request.GET["do-we-export-sim"] == "True":
            export_sim = True
    if export_sim:
        simulated_instrument = request.GET["sim-instrument-for-export"]
    else:
        simulated_instrument = ""
    # TODO: is this actually desired?
    # prev_selected_list = request.POST.getlist("prev_selected")
    selections = list(selections)
    return construct_export_zipfile(selections, export_sim,
                                    simulated_instrument)


def bulk_export(request) -> HttpResponse:
    print(request.GET)

    bulk_results = Sample.objects.only('sample_name')
    if not request.user.is_superuser:
        bulk_results = bulk_results.filter(released=True)
    for field in ['sample_name']:
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
        if 'any_field' in request.GET:
            bulk_results = bulk_results & search_all_samples(entry)
    search_results_id_list = [
        result.id for result in bulk_results
    ]
    if "simulate" in request.GET:
        simulated_instrument = request.GET["simulate"].replace("_", " ")
        simulate = True
    else:
        simulated_instrument = ""
        simulate = False
    return construct_export_zipfile(search_results_id_list, simulate,
                                    simulated_instrument)


def upload(request) -> HttpResponse:
    form = UploadForm(request.POST, request.FILES)

    upload_errors = []
    if not form.is_valid():
        form = UploadForm()
        return render(request, "upload.html", {"form": form})
    uploaded_file = request.FILES["file"]
    if uploaded_file.name[-3:] == "csv":
        upload_results = handle_csv_upload(uploaded_file)
    elif uploaded_file.name[-3:] == "zip":
        upload_results = handle_zipped_upload(uploaded_file)
    else:
        headline = "File upload failed."
        upload_errors.append("Please upload a csv or zip file.")
        return render(
            request,
            "upload.html",
            {
                "form": form,
                "headline": headline,
                "upload_errors": upload_errors,
            },
        )

    successful = []
    unsuccessful = []
    # we get an integer flag at the beginning from handle_zipped_upload
    if isinstance(upload_results[0], int):
        if upload_results[0] == 0:
            upload_errors = upload_results[1]
            return render(
                request,
                "upload.html",
                {"form": form, "upload_errors": upload_errors},
            )

        elif upload_results[0] == 1:
            headline = "No samples uploaded successfully."
            unsuccessful = [
                {
                    "filename": upload_result["filename"],
                    "errors": upload_result["errors"],
                }
                for upload_result in upload_results[1]
            ]

        else:
            headline = "The following samples uploaded successfully."
            successful = [
                {
                    "filename": file_result["filename"],
                    "sample": file_result["sample"],
                    "warnings": file_result["sample"].import_notes,
                }
                for file_result in upload_results[1]
            ]

            if upload_results[0] == 2:
                unsuccessful = [
                    {
                        "filename": file_result["filename"],
                        "sample": file_result["sample"],
                        "errors": file_result["errors"],
                    }
                    for file_result in upload_results[2]
                ]

    # and here's the logic for displaying the results of a single CSV
    # file upload it might be better to concatenate both of these into a
    # single, distinct function now that we're handling multisamples

    else:
        if upload_results[0]["errors"] is not None:
            headline = (
                    upload_results[0][
                        "filename"] + " did not upload successfully."
            )
            unsuccessful = [
                {
                    "filename": upload_results[0]["filename"],
                    "errors": upload_results[0]["errors"],
                }
            ]
        else:
            headline = upload_results[0]["filename"] + "uploaded successfully."
            successful = [
                {
                    "filename": upload_result["filename"],
                    "sample": upload_result["sample"],
                    "warnings": upload_result["sample"].import_notes,
                }
                for upload_result in upload_results
            ]

    return render(
        request,
        "upload.html",
        {
            "form": form,
            "successful": successful,
            "unsuccessful": unsuccessful,
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


def about(request) -> HttpResponse:
    databases = Database.objects.all()
    filtersets = FilterSet.objects.all().order_by("display_order")
    return render(
        request,
        "about.html",
        {"databases": databases, "filtersets": filtersets},
    )


def status(request) -> HttpResponse:
    return render(request, "status.html")
