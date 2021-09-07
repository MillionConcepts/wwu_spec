"""
functionality for dealing with various sorts of project-internal
export and display formats
"""

import csv
import datetime as dt
import io
import zipfile

from django.conf import settings
from django.http import HttpResponse

from visor.models import Sample


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
            "simulated_spectra",
            "released",
        ]:
            writer.writerow([field[0], getattr(sample, field[1])])
    return writer, text_buffer


def construct_export_zipfile(selections, export_sim, simulated_instrument):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_buffer:
        zip_buffer = write_samples_into_buffer(
            export_sim, zip_buffer, selections, simulated_instrument
        )
    zip_buffer.seek(0)
    # name the zip file and send it as http
    date = dt.datetime.today().strftime("%y-%m-%d")
    response = HttpResponse(zip_buffer, content_type="application/zip")
    response["Content-Disposition"] = (
        "attachment; filename=spectra-%s.zip;" % date
    )
    return response


def write_samples_into_buffer(
    export_sim, buffer, selections, simulated_instrument
):
    samples = Sample.objects.filter(id__in=selections)
    # write each sample line-by-line into text buffer,
    # also splitting reflectance dictionary into lines
    for sample in samples:
        metadata = sample.metadata_csv_block()
        buffer = write_spectrum_to_buffer(metadata, buffer, sample)
        if export_sim:
            buffer = write_simulated_spectra_to_buffer(
                metadata, buffer, sample, simulated_instrument
            )
        # write image into output (e.g. zipfile) buffer
        if sample.image:
            filename = settings.SAMPLE_IMAGE_PATH + "/" + sample.image
            buffer.write(filename, arcname=sample.image)
    return buffer


def write_spectrum_to_buffer(metadata, buffer, sample):
    data = sample.data_csv_block()
    text_buffer = io.StringIO(metadata + "\n" + data)
    text_buffer.seek(0)
    # write sample into buffer
    buffer.writestr(
        f"{sample.sample_id.replace('/', '_')}_{sample.id}.csv",
        text_buffer.read(),
    )
    return buffer


def write_simulated_spectra_to_buffer(
    metadata, output, sample, simulated_instrument
):
    sims = sample.sim_csv_blocks()
    if simulated_instrument == "all":
        simulated_instruments = sims.keys()
    else:
        simulated_instruments = [simulated_instrument]
    for instrument in simulated_instruments:
        text_buffer = io.StringIO(metadata + "\n" + sims[instrument])
        text_buffer.seek(0)
        output.writestr(
            f"{sample.sample_id.replace('/', '_')}"
            f"_simulated_{instrument}_{sample.id}.csv",
            text_buffer.read(),
        )
    return output
