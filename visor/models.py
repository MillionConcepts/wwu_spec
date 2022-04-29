import json
import os
from ast import literal_eval
from functools import cached_property
from itertools import accumulate, repeat
from operator import add

import PIL
import PIL.ImageFile
import numpy as np
import pandas as pd
from PIL import Image
from django import forms
from django.conf import settings
from django.db import models, IntegrityError
from toolz import valmap

from visor.dj_utils import model_values
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

    @cached_property
    def filterbank(self):
        filters = json.loads(self.filters)
        for filt in filters:
            filters[filt] = np.array(filters[filt])
        return filters

    @cached_property
    def wavelength_array(self):
        return np.array(json.loads(self.wavelengths))

    @cached_property
    def illumination_array(self):
        return np.array(json.loads(self.illumination))


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
    min_wavelength = models.FloatField(
        "Minimum Wavelength", blank=True, db_index=True
    )
    sample_name = models.CharField(
        "Sample Name", blank=True, max_length=40, db_index=True
    )
    max_wavelength = models.FloatField(
        "Maximum Wavelength", blank=True, db_index=True
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
    sample_id = models.CharField(
        "Sample ID", max_length=40, db_index=True, unique=True
    )
    original_sample_id = models.CharField(
        "Original Sample ID", max_length=40, db_index=True
    )
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
    # defined groups of fields we can and cannot use for various sorts of
    # operations.
    # note: double underscore in these field names is an ugly but compact way
    # to access the ForeignKey object fields.
    phrase_fields = ["sample_name"]
    choice_fields = ["origin__name", "sample_type__name"]
    numeric_fields = ["min_wavelength", "max_wavelength"]
    m2m_managers = ["library"]
    searchable_fields = phrase_fields + choice_fields + numeric_fields

    # private attributes used during creation process
    _warnings = []
    _errors = []

    def clean(self, *args, **kwargs):
        """
        step-1 data cleaning and validation function for Sample.
        ideally shouldn't interact with anything in the database.
        """
        # reset warnings and errors
        self._warnings = []
        self._errors = []
        if self.import_notes:
            self._warnings += literal_eval(self.import_notes)
        # TODO: do I really like this IDL-esque list of procedures?
        self._regularize_metadata_strings()
        self._transform_reflectance_to_numpy_array()
        self._check_for_numeracy()
        self._check_for_absurd_values()
        self._eliminate_negativity()
        self._reshape_and_sort_reflectance()
        self._bound_and_jsonify_reflectance()
        self._warn_and_raise()

    def save(self, *args, **kwargs):
        """
        step-2 cleaning and validation function for Sample objects. unlike
        Sample.clean(), this function can interact with the database -- and
        at the end, it inserts the Sample into the database.
        """
        # check to see if this appears to be in the database
        # but don't do this check if it's from the admin console
        # i.e., allow updating
        pks = model_values(Sample, "id")
        if int(self.id) in pks:
            if kwargs.pop("uploaded", False) is True:
                raise ValueError(
                    "Sorry, modifying an existing sample is not allowed "
                    "from this interface."
                )
        else:
            # if it's not an update to an existing sample,
            # check duplicate sample ids and true duplicates
            self._handle_duplicate_sample_ids()
        if self.image:
            self._clean_image_field()
        convolve = kwargs.pop("convolve", True)
        if convolve:
            self._create_simulated_spectra()
        self._warn_and_raise()
        super(Sample, self).save(*args, **kwargs)

    def as_dict(self):
        self_dict = {}
        for field in self._meta.fields:
            self_dict |= {field.name: getattr(self, field.name)}
        return self_dict

    def metadata_csv_block(self):
        return "\n".join(
            [
                f"{field.verbose_name}," f"{getattr(self, field.name)}"
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

    def sim_csv_blocks(self):
        sims = dict(json.loads(self.simulated_spectra))
        instruments = [key for key in sims if key.endswith("_no_illumination")]
        frames = {}
        for instrument in instruments:
            frame = pd.read_json(sims[instrument])
            base_name = instrument.strip("_no_illumination")
            if base_name in sims.keys():
                frame["solar_illuminated_response"] = pd.read_json(
                    sims[base_name]
                )["response"]
            frames[base_name] = frame.to_csv(index=None)
        return frames

    # TODO: is this really appropriate? it's very specifically intended to get
    #  it into a format the graph js likes. do I want this to perhaps not even
    #  live on the model? I don't like it, in any case.
    def as_json(self, brief=False):
        json_dict = {}
        brief_fields = (
            "id",
            "sample_id",
            "sample_name",
            "origin",
            "sample_type"
        )
        for field in self._meta.fields:
            if not getattr(self, field.name):
                continue
            if brief and (field.name not in brief_fields):
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
            json_dict[
                "wavelength_range"
            ] = f"{self.min_wavelength}-{self.max_wavelength}"
        return json_dict

    @cached_property
    def data_array(self):
        return np.array(json.loads(self.reflectance))

    def get_simulated_spectra(self):
        return valmap(literal_eval, literal_eval(self.simulated_spectra))

    def _raise_for_duplicates(self):
        for refl_array in Sample.objects.filter(
            sample_id__icontains=self.original_sample_id
        ).values("reflectance"):
            if self.reflectance == refl_array["reflectance"]:
                # TODO: make this a reporting thing instead
                # raise ValueError(
                #     f"The sample {self.original_sample_id} appears to "
                #     f"already be in the database (with an identical "
                #     f"spectrum). If you're sure this is a unique sample, "
                #     f"please give it a new ID. If you want to correct a "
                #     f"previously uploaded sample, please contact the site "
                #     f"administrator to delete your previous uploads."
                # )
                raise IntegrityError(
                    f"{self.original_sample_id} already in database "
                    f"w/identical spectrum"
                )

    def _handle_duplicate_sample_ids(self):
        """
        safety-feature validation step to prevent duplicate sample_id +
        reflectance.
        """
        ids = model_values(Sample, "sample_id")
        if self.sample_id not in ids:
            return
        self._raise_for_duplicates()
        # add incrementing numbers after an underscore with an 'f'
        naturals = accumulate(repeat(1), add)
        while (new_id := self.sample_id + f"_f{next(naturals)}") in ids:
            continue
        self._warnings.append(
            f"A spectrum with sample ID {self.sample_id} was already in the "
            f"database, but the spectrum is distinct. This spectrum has been "
            f"renamed to {new_id}."
        )
        self.sample_id = new_id

    def _clean_image_field(self):
        image_path = settings.SAMPLE_IMAGE_PATH
        # this Sample may have been initialized either with an
        # in-memory raster (as with an upload) or with a string representing
        # a path to an image file (as in most local sample creation)
        if isinstance(self.image, str):
            if os.path.exists(os.path.join(image_path, self.image)):
                # don't open and re-save existing images
                return
            else:
                self._load_image()
        self._update_image_path(image_path)

    def _create_simulated_spectra(self):
        sims = {}
        for filterset in FilterSet.objects.all():
            sims[filterset.short_name] = simulate_spectrum(self, filterset)
            sims[
                filterset.short_name + "_no_illumination"
            ] = simulate_spectrum(self, filterset, illuminated=False)
        for sim in sims:
            sims[sim] = sims[sim].reset_index(drop=True).to_json()
        self.simulated_spectra = json.dumps(sims)

    def _update_image_path(self, image_path):
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
                "PIL.ImageFile.ImageFile" + " object or a path to an image."
            )

    def _regularize_metadata_strings(self):
        """
        regularize whitespace padding and capitalization; get rid of commas.
        don't mess with arrays or pathnames.
        """
        for field in self._meta.fields:
            if field.name in ["reflectance", "image"]:
                continue
            value = getattr(self, field.name)
            if not value:
                continue
            if field.name not in ["origin", "sample_type"]:
                value = str(value).strip().replace(",", "_")
                value = value[:1].upper() + value[1:]
                setattr(self, field.name, value)

    def _load_image(self):
        try:
            raster = Image.open(self.image)
            if raster.mode != "RGB":
                self.image = raster.convert("RGB")
        except (FileNotFoundError, PIL.UnidentifiedImageError):
            raise ValueError(
                "The image associated with "
                + self.sample_id
                + " is missing or can't be read."
            )

    def _warn_and_raise(self):
        self.import_notes = str(self._warnings)
        if len(self._errors) > 0:
            raise forms.ValidationError(self._errors)

    def _transform_reflectance_to_numpy_array(self):
        try:
            if isinstance(self.reflectance, str):
                self.reflectance = json.loads(self.reflectance)
            self.reflectance = np.array(self.reflectance)
        except ValueError:
            # this should only happen if someone's made typos in the admin
            # console, not with uploaded CSV
            self._errors.append(
                "Error: the reflectance values don't appear to be formatted "
                "as an array. "
            )
            self._warn_and_raise()

    def _check_for_absurd_values(self):
        max_reflectance = self.reflectance[:, 1].max()
        try:
            assert max_reflectance < 5
        except AssertionError:
            self._errors.append(
                f"Error: max reflectance {max_reflectance} above cutoff of 5"
            )
            self._warn_and_raise()

    def _eliminate_negativity(self):
        positives = np.all((self.reflectance >= 0), axis=1)
        if not all(positives):
            self._warnings.append(
                f"Warning: there are negative reflectance values in "
                f"{self.sample_id}. These have been deleted."
            )
            self.reflectance = self.reflectance[positives]

    def _check_for_numeracy(self):
        try:
            self.reflectance = self.reflectance.astype(np.float64)
        except ValueError:
            self._errors.append(
                "Error: some fields in the reflectance data can't be "
                "interpreted as numbers. It's possible that you haven't "
                "placed the reflectance data after all of the metadata, "
                "or that there are some non-numeric characters in the "
                "reflectance data."
            )
            self._warn_and_raise()

    def _bound_and_jsonify_reflectance(self):
        self.min_wavelength = round(self.reflectance[0][0])
        self.max_wavelength= round(self.reflectance[-1][0])
        self.reflectance = json.dumps(self.reflectance.tolist())

    def _reshape_and_sort_reflectance(self):
        # switch to 2-column matrix, sort, check for correct shape,
        # find min and max reflectance
        if self.reflectance.shape[1] != 2:
            self.reflectance = self.reflectance.T
        # sorts by returning indices that would sort the wavelength
        # column
        self.reflectance = self.reflectance[self.reflectance[:, 0].argsort()]
        if self.reflectance.shape[1] != 2:
            self._errors.append(
                "Error: the reflectance values don't appear to be "
                "properly organized into two columns. "
            )

    def __str__(self):
        if self.origin.short_name is not None:
            return (
                f"{self.sample_name}_{self.sample_id}_"
                f"{self.origin.short_name}"
            )
        return (
            f"{self.sample_name}_{self.sample_id}_"
            f"{self.origin.name.split()[0]}"
        )

    class Meta:
        ordering = ["sample_id"]


