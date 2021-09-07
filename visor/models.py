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
from toolz import valmap

from visor.spectral import simulate_spectrum


class FilterSet(models.Model):
    """
    model representing a set of filters/bandpasses/etc. from a real-world
    instrument. used for producing simulated versions of lab spectra
    instantiated as Samples.
    """

    short_name = models.CharField(
        max_length=45, unique=True, blank=False, db_index=True
    )
    name = models.CharField(max_length=120, blank=True, db_index=True)

    # stringified array of wavelength bins, must be shared by all filters
    wavelengths = models.TextField(blank=False, db_index=True)

    # JSON string containing dictionary of filters, formatted like:
    # {"filter name":array_of_responsivity_values}
    # we expect all filters to be power-normalized
    # such that the integral over the wavelength bins = 1
    # see normalize_power() in spectral.py
    filters = models.TextField(blank=False, db_index=True)

    # stringified 2-D array containing wavelength and spectrum
    # of reference illuminating radiation(e.g., solar spectrum)
    illumination = models.TextField(blank=True, db_index=True)

    # stringified 2-D array of effective center wavelength for
    # each filter, formatted like: ["filter name",center_wavelength]
    # must have same names as filters
    filter_wavelengths = models.TextField(blank=False, db_index=True)

    # TODO: it would be useful to have a reasonable cleaning function at
    # some point

    url = models.TextField(blank=True, db_index=True)
    description = models.TextField(blank=True, db_index=True)

    # display order in simulation dropdown
    display_order = models.IntegerField(
        blank=True, default=10000, db_index=True
    )

    def __str__(self):
        return self.name


class Library(models.Model):
    """
    table holding spectra assignments to custom libraries
    """

    name = models.CharField(
        max_length=100, unique=True, blank=False, db_index=True
    )
    description = models.TextField(blank=True, db_index=True)

    def clean(self, *args, **kwargs):
        self.name = str(self.name).strip()

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

    name = models.CharField(
        max_length=100, unique=True, blank=False, db_index=True
    )
    url = models.TextField(blank=True, db_index=True)
    description = models.TextField(blank=True, db_index=True)
    short_name = models.CharField(
        max_length=20, blank=True, null=True, db_index=True
    )
    citation = models.TextField(blank=True, db_index=True)
    released = models.BooleanField(
        "Released to Public", default=False, blank=False
    )

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
    """
    type of sample, such as mineral, vapor, etc.
    currently mostly not populated.
    """

    name = models.CharField(
        verbose_name="Type Of Sample", max_length=20, unique=True, blank=False
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


class Sample(models.Model):
    """
    model whose instances each represent a distinct laboratory spectrum.
    """

    actions = ["mass_change_selected"]
    composition = models.CharField(
        "Composition", blank=True, max_length=40, db_index=True
    )
    date_added = models.DateTimeField(
        "Date Added", auto_now=True, db_index=True
    )
    filename = models.CharField(
        "Name of Uploaded File", blank=True, max_length=80
    )
    formula = models.CharField(
        "Formula", blank=True, max_length=40, db_index=True
    )
    grain_size = models.CharField(
        "Grain Size", blank=True, max_length=40, db_index=True
    )
    image = models.CharField(
        "Path to Image", blank=True, null=True, max_length=100, db_index=True
    )
    import_notes = models.TextField(
        "File import notes", blank=True, null=True, db_index=True
    )
    locality = models.TextField("Locality", blank=True, db_index=True)
    libraries = models.ManyToManyField(Library, blank=True, db_index=True)
    min_reflectance = models.FloatField(
        "Minimum Reflectance", blank=True, db_index=True
    )
    sample_name = models.CharField(
        "Sample Name", blank=True, max_length=40, db_index=True
    )
    max_reflectance = models.FloatField(
        "Maximum Reflectance", blank=True, db_index=True
    )
    origin = models.ForeignKey(
        Database,
        on_delete=models.PROTECT,
        blank=False,
        verbose_name="Database of Origin",
    )
    other = models.TextField("Other Information", blank=True, db_index=True)
    references = models.TextField("References", blank=True, db_index=True)
    released = models.BooleanField(
        "Released to Public", default=False, blank=False
    )

    # stringified array
    reflectance = models.TextField(
        "Reflectance", default="[0,0]", db_index=True
    )
    resolution = models.CharField(
        "Resolution", blank=True, max_length=40, db_index=True
    )
    material_class = models.CharField(
        "Material Class", blank=True, max_length=40
    )
    sample_desc = models.TextField(
        "Sample Description", blank=True, db_index=True
    )
    sample_id = models.CharField("Sample ID", max_length=40, db_index=True)
    sample_type = models.ForeignKey(
        SampleType,
        on_delete=models.PROTECT,
        null=True,
        verbose_name="Sample Type",
    )

    # dictionary of pandas dataframes stored as json string
    simulated_spectra = models.TextField(
        "Simulated Spectra", default="{}", db_index=True
    )
    view_geom = models.CharField(
        "Viewing Geometry", blank=True, max_length=40, db_index=True
    )

    # fields we view as "private" or "data"
    unprintable_fields = (
        "image",
        "id",
        "reflectance",
        "filename",
        "import_notes",
        "flagged",
        "simulated_spectra",
        "released",
    )

    def clean(self, *args, **kwargs):
        """
        step-1 data cleaning and validation function for Sample.
        ideally shouldn't interact with anything in the database.
        """
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

                positives = np.all((self.reflectance > 0), axis=1)
                if not all(positives):
                    warnings.append(
                        "Warning: there are negative-valued items "
                        "in the reflectance data for "
                        + self.sample_id
                        + ". These have been deleted."
                    )
                    self.reflectance = self.reflectance[positives]

                # switch to 2-column matrix, sort, check for correct shape,
                # find min and max reflectance
                if self.reflectance.shape[1] != 2:
                    self.reflectance = self.reflectance.T

                # sorts by returning indices that would sort the wavelength
                # column
                self.reflectance = self.reflectance[
                    self.reflectance[:, 0].argsort()
                ]

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

        self.import_notes = str(warnings)
        if errors:
            raise forms.ValidationError(errors)

    def check_upload(self, warnings):
        """
        safety-feature validation step for samples uploaded by remote users.
        also probably useful in some cases for samples not uploaded by remote
        users.
        """
        if self.sample_id not in [
            sample.sample_id for sample in Sample.objects.all()
        ]:
            return
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
                    ] + str(
                        int(self.sample_id[under_search.start() + 1 :]) + 1
                    )
                else:
                    self.sample_id = self.sample_id + "_1"
            warnings.append(
                "The sample name "
                + old_id
                + " was already in the database, but it appears to be"
                + " for a distinct sample. It has been renamed to "
                + self.sample_id
            )
        return warnings

    def save(self, *args, **kwargs):
        """
        step-2 cleaning and validation function for Sample objects. unlike
        Sample.clean(), this function can interact with the database -- and
        at the end, it inserts the Sample into the database.
        """
        errors = []
        if self.import_notes:
            if isinstance(self.import_notes, str):
                warnings = literal_eval(self.import_notes)
            else:
                warnings = self.import_notes
        else:
            warnings = []
        if "errors" in kwargs:
            errors.append(kwargs["errors"])
        if "warnings" in kwargs:
            warnings.append(kwargs["warnings"])

        image_path = settings.SAMPLE_IMAGE_PATH

        # check to see if this appears to be in the database
        # but don't do this check if it's from the admin console
        # i.e., allow updating

        uploaded = kwargs.pop("uploaded", False)
        if uploaded:
            # impure function, modifies self and returns warnings
            warnings = self.check_upload(warnings)

        if self.image:
            has_existing_image = False
            if isinstance(self.image, str):
                if os.path.exists(os.path.join(image_path, self.image)):
                    # don't open and re-save existing images
                    has_existing_image = True
                else:
                    try:
                        raster = Image.open(self.image)
                        if raster.mode != "RGB":
                            raster = raster.convert("RGB")
                        self.image = raster
                    except (FileNotFoundError, PIL.UnidentifiedImageError):
                        raise ValueError(
                            "The image associated with "
                            + self.sample_id
                            + " is missing or can't be read."
                        )
            if not has_existing_image:
                if isinstance(self.image, PIL.Image.Image):
                    filename = self.sample_id + ".jpg"
                    # save image into application image directory
                    os.makedirs(image_path, exist_ok=True)
                    self.image.save(os.path.join(image_path, filename))
                    # make thumbnail
                    self.image.thumbnail((256, 256))
                    self.image.save(
                        os.path.join(image_path, filename[:-4] + "_thumb.jpg")
                    )
                    # set sample's image field to a link to that image
                    self.image = filename
                else:
                    raise ValueError(
                        "Associated image field must be a "
                        "PIL.ImageFile.ImageFile"
                        + " object or a path to an image."
                    )

        convolve = kwargs.pop("convolve", True)
        if convolve:
            # create simulated spectra
            sims = {}
            for filterset in FilterSet.objects.all():
                sims[filterset.short_name] = simulate_spectrum(self, filterset)
                sims[
                    filterset.short_name + "_no_illumination"
                ] = simulate_spectrum(self, filterset, illuminated=False)
            for sim in sims:
                sims[sim] = sims[sim].reset_index(drop=True).to_json()
            self.simulated_spectra = json.dumps(sims)
        self.import_notes = warnings
        super(Sample, self).save(*args, **kwargs)

    def __str__(self):
        if self.origin.short_name is not None:
            return (
                self.sample_name
                + "_"
                + self.sample_id
                + "_"
                + self.origin.short_name
            )
        return (
            self.sample_name
            + "_"
            + self.sample_id
            + "_"
            + self.origin.name.split()[0]
        )

    def as_dict(self):
        self_dict = {}
        for field in self._meta.fields:
            self_dict |= {field.name: getattr(self, field.name)}
        return self_dict

    def metadata_dict(self):
        return {
            field.verbose_name: getattr(self, field.name)
            for field in self._meta.fields
            if field.name not in self.unprintable_fields
        }

    def metadata_csv_block(self):
        return "\n".join(
            [
                field.verbose_name
                + ","
                + str(getattr(self, field.name)).replace(",", "_")
                for field in self._meta.fields
                if field.name not in self.unprintable_fields
            ]
        )

    def data_csv_block(self):
        return "Wavelength,Response\n" + "\n".join(
            [
                f"{wavelength},{response}"
                for wavelength, response in literal_eval(self.reflectance)
            ]
        )

    def simulated_csv_block(self, instrument):
        sims = self.get_simulated_spectra()
        metadata = self.metadata_csv_block()
        illuminated_df = pd.DataFrame(sims[instrument])
        dark_series = sims[instrument + "_no_illumination"][
            "response"
        ].values()
        illuminated_df["unilluminated_response"] = dark_series
        illuminated_df.columns = [
            "filter",
            "wavelength",
            "solar_illuminated_response",
            "response",
        ]

    def sim_csv_blocks(self):
        sims = dict(json.loads(self.simulated_spectra))
        frames = {
            key: pd.read_json(sims[key]).reindex(
                columns=["filter", "wavelength", "solar_illuminated_response"]
            )
            for key in sims
            if not key.endswith("_no_solar_illumination")
        }
        for key in sims:
            if key.endswith("_no_solar_illumination"):
                frames[key.replace("_no_solar_illumination", "")][
                    "response"
                ] = pd.read_json(sims[key]).iloc[:, 2]
        return {key: frame.to_csv() for key, frame in frames.items()}

    def as_json(self):
        json_dict = {}
        for field in self._meta.fields:
            if not getattr(self, field.name):
                continue
            if field.name == "reflectance":
                json_dict |= {
                    "reflectance": dict(literal_eval(self.reflectance))
                }
            elif field.name == "date_added":
                json_dict |= {"date_added": str(self.date_added)}
            elif isinstance(field, models.ForeignKey):
                json_dict |= {field.name: getattr(self, field.name).name}
            elif field.name == "simulated_spectra":
                sims = json.loads(self.simulated_spectra)
                for filterset in sims:
                    name = filterset
                    # 'astype(float)'' is added because json will not
                    # treat numpy.int64 as an int or float, unlike its
                    # treatment of numpy.float64, which causes problems
                    # for samples that have reflectance ranges that lie
                    # totally outside of a filterset's range
                    spectrum = dict(
                        pd.read_json(sims[filterset])
                        .drop(columns="filter")
                        .values.astype(float)
                    )
                    json_dict |= {name: spectrum}
            else:
                json_dict |= {field.name: getattr(self, field.name)}
        return json_dict

    def get_simulated_spectra(self):
        return valmap(
            literal_eval, literal_eval(self.as_dict()["simulated_spectra"])
        )

    def get_image(self):
        if isinstance(self.image, str):
            return Image.open(settings.SAMPLE_IMAGE_PATH + "/" + self.image)
        else:
            raise ValueError(
                "this sample doesn't have an image,  or it's not currently "
                "saved in the"
                " database. it may be an in-memory object."
            )

    class Meta:
        ordering = ["sample_id"]
