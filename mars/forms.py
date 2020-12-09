from django import forms

from mars.models import Database, SampleType, Library
from mars.utils import make_choice_list


class SearchForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(SearchForm, self).__init__(*args, **kwargs)
        choice_fields = {
            'origin__name': [Database, 'name'],
            'sample_type__name': [SampleType, 'name'],
            'library__name': [Library, 'name']
        }
        choice_data = make_choice_list(choice_fields)
        for field in choice_data:
            self.fields[field].choices = choice_data[field]

    sample_name = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                'placeholder': 'e.g. Gypsum',
                'id': 'sample_name',
                'class': 'autocomplete'
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


class AdminUploadImageForm(forms.Form):
    file = forms.FileField(
        label='Select an image',
    )


class UploadForm(forms.Form):
    file = forms.FileField(
        label='Select a file.',
    )
