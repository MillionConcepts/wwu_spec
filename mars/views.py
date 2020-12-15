import csv
import datetime as dt
import io
import json
import zipfile
from ast import literal_eval
from functools import reduce
from operator import or_

import PIL
from PIL import Image
from django.conf import settings
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render

from mars.forms import UploadForm, AdminUploadImageForm, \
    concealed_search_factory
from mars.models import Database, Sample, FilterSet
from mars.utils import search_all_samples, handle_csv_upload, \
    handle_zipped_upload


def search(request):
    """
    render the search page with an empty search form.
    presently doesn't do any other manipulation (some former
    features determined crufty and cut)
    """
    page_params = {
        "search_formset": concealed_search_factory(request)
    }
    return render(request, "search.html", page_params)


def results(request):
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

    phrase_fields = [
        "sample_name"
    ]

    choice_fields = ["origin__name", "sample_type__name", "library__name"]

    numeric_fields = ['min_reflectance', 'max_reflectance']

    searchable_fields = choice_fields + phrase_fields + numeric_fields

    form_results = Sample.objects.only(*searchable_fields)

    if not request.user.is_superuser:
        form_results = form_results.filter(
            released=True
        )
    form_results = form_results.order_by(*sort_params)

    for field in phrase_fields + choice_fields:
        entry = search_form.cleaned_data.get(field, None)
        if not entry:
            continue
        # "Any" entries do not restrict the search
        if entry == "Any":
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
                form_results.filter(**{query: word}) for word in
                entry.split(" ")
            ]
            form_results = reduce(or_, filters)

    # this is a placeholder for the planned 'select by band' functionality
    # numeric_constraints = ["min_included_range", "max_included_range"]
    # for field in numeric_constraints:
    #     entry = search_form.cleaned_data.get(field)
    #     if entry:
    #         if field == "min_included_range":
    #             query = "min_reflectance__lte"
    #         elif field == "max_included_range":
    #             query = "max_reflectance__gte"
    #         form_results = form_results.filter(**{query: entry})

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
    page_selected = int(request.GET.get("page_selected", 1))
    page_results = paginator.page(page_selected)
    page_choices = range(
        max(1, page_selected - 3),
        min(page_selected + 4, paginator.num_pages + 1)
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


def graph(request):
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
        for filterset
        in FilterSet.objects.all().order_by("display_order")
    ]
    filtersets += [
        filterset.short_name + " (no illumination)"
        for filterset
        in FilterSet.objects.all().order_by("display_order")
    ]
    return render(
        request,
        "graph.html",
        {
            "selected_ids": selections,
            "graphResults": samples,
            "graphJSON": json_string,
            "search_formset": search_formset,
            "filtersets": filtersets,
        },
    )


def meta(request):
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


def export(request):
    selections = request.GET.getlist("selection")

    # TODO: is this actually desired?
    # prev_selected_list = request.POST.getlist("prev_selected")

    selections = list(selections)
    samples = Sample.objects.filter(id__in=selections)
    zip_buffer = io.BytesIO()
    field_list = [[field.verbose_name, field.name] for field in
                  Sample._meta.fields]
    field_list.sort()

    with zipfile.ZipFile(zip_buffer, "w") as output:

        # write each sample line-by-line into text buffer,
        # also splitting reflectance dictionary into lines

        for sample in samples:
            text_buffer = io.StringIO()
            writer = csv.writer(text_buffer)
            for field in field_list:
                if field[1] not in [
                    "image",
                    "id",
                    "reflectance",
                    "filename",
                    "import_notes",
                    "simulated_spectra",
                    "flagged",
                ]:
                    writer.writerow([field[0], getattr(sample, field[1])])
            writer.writerow(["Wavelength"])
            for row in literal_eval(sample.reflectance):
                writer.writerow([row[0], row[1]])
            writer.writerow(["Simulated Spectra"])
            sim_spectra = sample.write_sims()
            writer.writerow(sim_spectra)
            text_buffer.seek(0)

            # write csv into zip buffer

            output.writestr(sample.sample_id + ".csv", text_buffer.read())

            # write image into zip buffer

            if sample.image:
                filename = settings.SAMPLE_IMAGE_PATH + "/" + sample.image
                output.write(filename, arcname=sample.image)
    zip_buffer.seek(0)

    # name the zip file and send it as http

    date = dt.datetime.today().strftime("%y-%m-%d")
    response = HttpResponse(zip_buffer, content_type="application/zip")
    response[
        "Content-Disposition"] = "attachment; filename=spectra-%s.zip;" % date

    return response


def upload(request):
    if not request.method == "POST":
        # ignore it!
        return HttpResponse(status=204)

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
            {"form": form, "headline": headline,
             "upload_errors": upload_errors},
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
            headline = upload_results[0][
                           "filename"] + "uploaded successfully."
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


def admin_upload_image(request, ids):
    ids = literal_eval(ids)
    if len(ids) > 1:
        warn_multiple = True
    else:
        warn_multiple = False

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


def about(request):
    databases = Database.objects.all()
    filtersets = FilterSet.objects.all().order_by("display_order")
    return render(
        request,
        "about.html",
        {"databases": databases, "filtersets": filtersets}
    )


def status(request):
    return render(request, "status.html")
