from django import forms
from mars.models import *
from mars.utils import *

class SearchForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(SearchForm, self).__init__(*args, **kwargs)

        choice_fields = {'origin__name': [Database,'name'],
                     'sample_type__name': [SampleType, 'name'],
                     'filterset_name': [FilterSet,'name']
                     }

        choice_data = make_choice_list(choice_fields)
        for field in choice_data:
            self.fields[field].choices = choice_data[field]
            
    sample_name = forms.CharField(required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Gypsum',\
            'id':'sample_name','class':'autocomplete'}))
    material_class = forms.CharField(required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Sulfate',\
            'id':'material_class', 'class':'autocomplete'}))
    sample_id = forms.CharField(required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. ASD_SUL_21',
            'id':'sample_id','class':'autocomplete'}))
    any_field = forms.CharField(required=False,widget=
        forms.TextInput(attrs={'id':'any_field'}))
    min_included_range = forms.IntegerField(required = False,
        widget = forms.NumberInput(), label='Min X (nm)')
    max_included_range = forms.IntegerField(required = False,
        widget = forms.NumberInput(), label='Max X (nm)')
    id = forms.CharField(required=False)

    filterset_name = forms.ChoiceField(required = False, label = "Filterset Name")
    origin__name = forms.ChoiceField(required=False, label="Database of Origin")
    sample_type__name = forms.ChoiceField(required=False, label="Type of Sample")


class AdminUploadImageForm(forms.Form):
    file = forms.FileField(
        label = 'Select an image',
        )

class uploadForm(forms.Form):
    file = forms.FileField(
        label = 'Select a file.',
        )