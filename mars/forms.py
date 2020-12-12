from functools import partial

from django import forms
from django.forms import formset_factory

from mars.models import Database, SampleType, Library
from mars.utils import make_choice_list


class SearchForm(forms.Form):
    def __init__(self, *args, conceal_unreleased=True, **kwargs):
        super(SearchForm, self).__init__(*args, **kwargs)
        choice_fields = {
            'origin__name': [Database, 'name'],
            'sample_type__name': [SampleType, 'name'],
            'library__name': [Library, 'name']
        }
        for form_field, model_plus_field in choice_fields.items():
            self.fields[form_field].choices = make_choice_list(
                *model_plus_field,
                conceal_unreleased=conceal_unreleased
            )

    sample_name = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                'placeholder': 'e.g. Gypsum',
                'id': 'sample_name',
            }
        )
    )
    any_field = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'id': 'any_field'})
    )

    id = forms.CharField(required=False)

    library__name = forms.ChoiceField(
        required=False, label="Library Name"
    )
    origin__name = forms.ChoiceField(
        required=False, label="Database of Origin"
    )
    sample_type__name = forms.ChoiceField(
        required=False, label="Type of Sample"
    )


def concealed_search_factory(request):
    return partial(
        formset_factory(SearchForm),
        form_kwargs=({'conceal_unreleased': not request.user.is_superuser})
    )


class AdminUploadImageForm(forms.Form):
    file = forms.FileField(
        label='Select an image',
    )


class UploadForm(forms.Form):
    file = forms.FileField(
        label='Select a file.',
    )
