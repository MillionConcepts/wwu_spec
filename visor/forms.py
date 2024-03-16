from functools import partial

from django import forms
from django.forms import formset_factory

from visor.models import Database, SampleType, Library
from visor.dj_utils import make_choice_list


class SelectMultipleHide(forms.SelectMultiple):

    def create_option(
        self, name, value, label, selected, index, subindex=None, attrs=None
    ):
        index = str(index) if subindex is None else "%s_%s" % (index, subindex)
        attrs = {} if attrs is None else attrs
        attrs = {"value": "", "placeholder": ""} | attrs
        option_attrs = (
            self.build_attrs(self.attrs, attrs)
            if self.option_inherits_attrs
            else {}
        )
        if selected:
            option_attrs.update(self.checked_attribute)
        if "id" in option_attrs:
            option_attrs["id"] = self.id_for_label(option_attrs["id"], index)
        if not value:
            option_attrs["disabled"] = "disabled"
            option_attrs["hidden"] = True
        return {
            "name": name,
            "value": value,
            "label": label,
            "selected": selected,
            "index": index,
            "attrs": option_attrs,
            "type": self.input_type,
            "template_name": self.option_template_name,
            "wrap_label": True,
        }


class SearchForm(forms.Form):
    def __init__(self, *args, conceal_unreleased=True, **kwargs):
        super(SearchForm, self).__init__(*args, **kwargs)
        model_choice_fields = {
            "origin__name": [Database, "name"],
            "sample_type__name": [SampleType, "name"],
            # TODO: restore if we ever actually use this
            # "library": [Library, "name"],
        }
        for form_field, model_plus_field in model_choice_fields.items():
            self.fields[form_field].choices = make_choice_list(
                *model_plus_field, conceal_unreleased=conceal_unreleased
            )

    sample_name = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={"placeholder": "e.g. Gypsum", "id": "sample-name"}
        ),
    )
    any_field = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "id": "any-field",
                "placeholder": "e.g., Sulfate, or Gypsum, or SPT127"
            }
        )
    )
    id = forms.CharField(required=False)
    # TODO: restore if and when we actually populate these
    # library = forms.MultipleChoiceField(
    #     required=False, label="Library Name", widget=SelectMultipleHide()
    # )
    origin__name = forms.MultipleChoiceField(
        required=False, label="Database of Origin", widget=SelectMultipleHide()
    )
    sample_type__name = forms.MultipleChoiceField(
        required=False, label="Type of Sample", widget=SelectMultipleHide()
    )
    wavelength_range = forms.MultipleChoiceField(
        required=False,
        label="require wavelength ranges:",
        widget=SelectMultipleHide(attrs={"id": "wavelength-range"}),
        choices=[
            ("", ""),
            ("UVB", "UVB (<315 nm)"),
            ("UVA", "UVA (315-400 nm)"),
            ("VIS", "VIS (400-750 nm)"),
            ("NIR", "NIR  (750-2500 nm)"),
            ("MIR", "MIR (>2500 nm)"),
        ],
    )
    sizes = forms.MultipleChoiceField(
        required=False,
        label="restrict to size categories",
        widget=SelectMultipleHide(attrs={'id': 'size-range'}),
        choices=[
            # note: labels should all be suitable input for literal_eval()
            ("", ""),
            ("(None, 50)", "<=50 μm"),
            ("(50, 100)", "50-100 μm"),
            ("(100, 250)", "100-250 μm"),
            ("(250, 500)", "250-500 μm"),
            ("(500, 1000)", "500-1000 μm"),
            ("(1000, 2000)", "1-2 mm"),
            ("(2000, 5000)", "2-5 mm"),
            ("(5000, None)", ">=5 mm"),
            ("'Whole Object'", "Whole Object"),
            ("None", "Unspecified")
        ],
    )



def concealed_search_factory(request):
    return partial(
        formset_factory(SearchForm),
        form_kwargs=({"conceal_unreleased": not request.user.is_superuser}),
    )


class AdminUploadImageForm(forms.Form):
    file = forms.FileField(
        label="Select an image",
    )


class UploadForm(forms.Form):
    file = forms.FileField(
        label="Select a file.",
    )
