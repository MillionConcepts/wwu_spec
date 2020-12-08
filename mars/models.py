from ast import literal_eval
import json
import os
import re

from django.db import models
from django import forms
from django.conf import settings
import numpy as np
import pandas as pd
import PIL
from PIL import Image
import PIL.ImageFile

from mars.spectral import simulate_spectrum


# http://spectro.geol.wwu.edu/media/documents/Spectroscopy_Database_Sample_Upload_File_Format_xutE8kN.pdf


class FilterSet(models.Model):
    name = models.CharField(max_length=100, unique=True, blank=False)

    # stringified array of frequency bins, must be shared by all filters
    wavelengths = models.TextField(blank=False)

    # JSON string containing dictionary of filters, formatted like:
    # {"filter name":array_of_responsivity_values}
    # we expect all filters to be power-normalized
    # such that the integral over the frequency bins = 1
    # see normalize_power() in spectral.py
    filters = models.TextField(blank=False)

    # stringified 2-D array containing wavelength and spectrum
    # of reference illuminating radiation(e.g., solar spectrum)
    illumination = models.TextField(blank=True)

    # stringified 2-D array of effective center frequencies for
    # each filter, formatted like: ["filter name",center_frequency]
    # must have same names as filters
    filter_frequencies = models.TextField(blank=False)

    # TODO: it would be useful to have a reasonable cleaning function at
    #  some point

    citation = models.TextField(blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Library(models.Model):
    """
    table holding spectra assignments to custom libraries
    """
    name = models.CharField(max_length=100, unique=True, blank=False)
    description = models.TextField(blank=True)

    def clean(self, *args, **kwargs):
        self.name = str(self.name).strip()
        self.name = self.name.upper()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Libraries"


class Database(models.Model):
    """
    table holding information on source databases such as the
    USGS spectral database.
    """
    name = models.CharField(max_length=100, unique=True, blank=False)
    url = models.TextField(blank=True)
    description = models.TextField(blank=True)
    short_name = models.CharField(max_length=20, blank=True, null=True)
    citation = models.TextField(blank=True)

    def clean(self, *args, **kwargs):
        errors = []
        warnings = []
        if "errors" in kwargs:
            errors.append(kwargs["errors"])
        if "warnings" in kwargs:
            warnings.append(kwargs["warnings"])

        # regularize whitespace padding and capitalization

        self.name = str(self.name).strip()
        self.name = self.name[0].upper() + self.name[1:]

        if errors:
            raise forms.ValidationError(errors)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class SampleType(models.Model):
    name = models.CharField(
        verbose_name="Type Of Sample", max_length=20, unique=True, blank=False
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class Sample(models.Model):
    actions = ["mass_change_selected"]
    composition = models.CharField("Composition", blank=True, max_length=40)
    date_added = models.DateTimeField("Date Added", auto_now=True)
    filename = models.CharField("Name of Uploaded File", blank=True,
                                max_length=80)
    flagged = models.CharField("Flag Status", blank=True, max_length=10)
    formula = models.CharField("Formula", blank=True, max_length=40)
    grain_size = models.CharField("Grain Size", blank=True, max_length=40)
    image = models.CharField("Path to Image", blank=True, max_length=100)
    import_notes = models.TextField("File import notes", blank=True)
    locality = models.TextField("Locality", blank=True)
    library = models.ManyToManyField(Library, blank=True)
    min_reflectance = models.FloatField("Minimum Reflectance", blank=True)
    sample_name = models.CharField("Sample Name", blank=True, max_length=40)
    max_reflectance = models.FloatField("Maximum Reflectance", blank=True)
    origin = models.ForeignKey(
        Database,
        on_delete=models.PROTECT,
        blank=False,
        verbose_name="Database of Origin",
    )
    other = models.TextField("Other Information", blank=True)
    references = models.TextField("References", blank=True)

    # stringified array
    reflectance = models.TextField("Reflectance", default="[0,0]")
    resolution = models.CharField("Resolution", blank=True, max_length=40)
    material_class = models.CharField("Material Class", blank=True,
                                      max_length=40)
    sample_desc = models.TextField("Sample Description", blank=True)
    sample_id = models.CharField("Sample ID", max_length=40)
    sample_type = models.ForeignKey(
        SampleType, on_delete=models.PROTECT, null=True,
        verbose_name="Sample Type"
    )

    # dictionary of pandas dataframes stored as json string
    simulated_spectra = models.TextField("Simulated Spectra", default="{}")
    view_geom = models.CharField("Viewing Geometry", blank=True, max_length=40)

    def clean(self, *args, **kwargs):
        errors = []
        if self.import_notes:
            warnings = literal_eval(self.import_notes)
        else:
            warnings = []
        if "errors" in kwargs:
            errors.append(kwargs["errors"])
        if "warnings" in kwargs:
            warnings.append(kwargs["warnings"])

        # regularize whitespace padding and capitalization
        # don't mess with arrays or pathnames

        for field in self._meta.fields:
            if field.name not in ["reflectance", "image"]:
                value = getattr(self, field.name)
                if value:
                    if field.name not in ["origin", "sample_type"]:
                        value = str(value).strip()
                        value = value[:1].upper() + value[1:]
                        setattr(self, field.name, value)
        try:
            if isinstance(self.reflectance, str):
                self.reflectance = literal_eval(self.reflectance)
            self.reflectance = np.array(self.reflectance)
        except ValueError:
            # this should only happen if someone's made typos in the admin
            # console, not with uploaded CSV
            errors.append(
                "Error: the reflectance values don't appear to be formatted "
                "as an array. "
            )

        else:
            try:
                self.reflectance = self.reflectance.astype(np.float64)
            except ValueError:
                errors.append(
                    "Error: some fields in the reflectance data can't be "
                    "interpreted as numbers. It's possible that you haven't "
                    "placed the reflectance data after all of the metadata, "
                    "or that there are some non-numeric characters in the "
                    "reflectance data."
                )
            else:

                nonzeros = (self.reflectance != 0).all(0)
                if False in nonzeros:
                    warnings.append(
                        "Warning: there are zero- or negative-valued items "
                        "in the reflectance data for "
                        + self.sample_id
                        + ". These have been deleted."
                    )
                    first = self.reflectance[0][nonzeros]
                    second = self.reflectance[1][nonzeros]
                    self.reflectance = np.vstack([first, second])

                # switch to 2-column matrix, sort, check for correct shape,
                # find min and max reflectance
                if self.reflectance.shape[1] != 2:
                    self.reflectance = self.reflectance.T

                # sorts by returning indices that would sort the wavelength
                # column
                self.reflectance = self.reflectance[
                    self.reflectance[:, 0].argsort()]

                if self.reflectance.shape[1] != 2:
                    errors.append(
                        "Error: the reflectance data doesn't appear to be "
                        "properly organized into two columns. "
                    )

                # after I ingest all this switch this back to an error
                # or maybe we keep zero-valued stuff?

                self.min_reflectance = self.reflectance[0][0]
                self.max_reflectance = self.reflectance[-1][0]
                self.reflectance = str(self.reflectance.tolist())

        # TODO: remove in production

        self.import_notes = str(warnings)
        if errors:
            raise forms.ValidationError(errors)

    def save(self, *args, **kwargs):
        errors = []
        if self.import_notes:
            warnings = literal_eval(self.import_notes)
        else:
            warnings = []
        if "errors" in kwargs:
            errors.append(kwargs["errors"])
        if "warnings" in kwargs:
            warnings.append(kwargs["warnings"])

        image_path = settings.SAMPLE_IMAGE_PATH + "/"

        # check to see if this appears to be in the database
        # but don't do this check if it's from the admin console
        # i.e., allow updating

        uploaded = kwargs.pop("uploaded", False)
        if uploaded:
            if self.sample_id in [sample.sample_id for sample in
                                  Sample.objects.all()]:
                for refl_array in Sample.objects.filter(
                        sample_id__icontains=self.sample_id
                ).values("reflectance"):
                    if self.reflectance == refl_array["reflectance"]:
                        raise ValueError(
                            "The sample "
                            + self.sample_id
                            + " appears to already be in the database. If "
                            + "you're sure this is a unique sample, please "
                            + "give it a new ID. If you're trying to correct "
                            + "a previously uploaded sample, please contact "
                            + "the site administrator to delete your "
                            + "previous uploads."
                        )
                else:
                    old_id = self.sample_id
                    # just add incrementing numbers after an underscore
                    while self.sample_id in [
                        sample.sample_id for sample in Sample.objects.all()
                    ]:
                        under_search = re.search(r"_[0-9]+$", self.sample_id)
                        if under_search:
                            self.sample_id = self.sample_id[
                                             : under_search.start() + 1
                                             ] + str(int(
                                self.sample_id[under_search.start() + 1:]) + 1)
                        else:
                            self.sample_id = self.sample_id + "_1"
                    warnings.append(
                        "The sample name "
                        + old_id
                        + " was already in the database, but it appears to be"
                        + " for a distinct sample. It has been renamed to "
                        + self.sample_id
                    )

        if self.image:
            if isinstance(self.image, PIL.ImageFile.ImageFile):
                filename = self.sample_id + ".jpg"
                print("saving")
                self.image.save(image_path + filename, "JPEG")
                image = self.image
                self.image = filename
            elif isinstance(self.image, str):
                try:
                    image = Image.open(self.image)
                except (FileNotFoundError, PIL.UnidentifiedImageError):
                    warnings.append(
                        "The image associated with "
                        + self.sample_id
                        + " is damaged or missing."
                    )
            else:
                raise ValueError(
                    "Associated image field must be a PIL.ImageFile.ImageFile"
                    + " object or a pathname."
                )

            thumb_path = image_path + self.image[:-4] + "_thumb.jpg"

            if not os.path.exists(thumb_path):
                image.thumbnail((256, 256))
                image.save(thumb_path, "JPEG")

        sims = {}
        for filterset in FilterSet.objects.all():
            sims[filterset.name] = simulate_spectrum(self, filterset)
            sims[filterset.name + '_no_illumination'] = simulate_spectrum(
                self,
                filterset,
                illuminated=False
            )
        for sim in sims:
            sims[sim] = sims[sim].reset_index(drop=True).to_json()
        self.simulated_spectra = json.dumps(sims)

        super(Sample, self).save(*args, **kwargs)

    def __str__(self):
        if self.origin.short_name is not None:
            return self.sample_id + "_" + self.origin.short_name
        return self.sample_id + "_" + self.origin.name.split()[0]

    def as_dict(self):
        self_dict = {}
        for field in self._meta.fields:
            self_dict = dict(**self_dict,
                             **{field.name: getattr(self, field.name)})
        return self_dict

    def write_sims(self):
        sims = dict(json.loads(self.simulated_spectra))
        frames = [pd.read_json(sims[key]).reindex(
            columns=[key + ' filter', 'wavelength', 'response']) for key in
            sims]
        return [frame.to_csv() for frame in frames]

    def as_json(self):
        json_dict = {}
        for field in self._meta.fields:
            if getattr(self, field.name):
                if field.name == "reflectance":
                    json_dict = dict(
                        **json_dict,
                        **{"reflectance": dict(literal_eval(self.reflectance))}
                    )
                elif field.name == "date_added":
                    json_dict = dict(
                        **json_dict, **{"date_added": str(self.date_added)}
                    )
                elif isinstance(field, models.ForeignKey):
                    json_dict = dict(
                        **json_dict,
                        **{field.name: getattr(self, field.name).name}
                    )
                elif field.name == "simulated_spectra":
                    sims = json.loads(self.simulated_spectra)
                    for filterset in sims:
                        name = filterset
                        # 'astype(float)'' is added because json will not
                        # treat numpy.int64 as an int or float, unlike its
                        # treatment of numpy.float64, which causes problems
                        # for samples that have reflectance ranges that lie
                        # totally outside of a filterset's range
                        spectrum = dict(pd.read_json(sims[filterset]).drop(
                            columns="filter").values.astype(float))
                        json_dict = dict(**json_dict, **{name: spectrum})
                else:
                    json_dict = dict(
                        **json_dict, **{field.name: getattr(self, field.name)}
                    )
        return json_dict

    class Meta:
        ordering = ["sample_id"]
