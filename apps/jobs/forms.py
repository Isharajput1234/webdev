from django import forms
from .models import Job, Application, Category

_field_class = (
    'w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-sm '
    'focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all '
    'hover:border-blue-400'
)


class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = [
            'title', 'category', 'description', 'requirements',
            'location', 'salary', 'job_type', 'deadline'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': _field_class}),
            'category': forms.Select(attrs={'class': _field_class}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': _field_class}),
            'requirements': forms.Textarea(attrs={'rows': 4, 'class': _field_class}),
            'location': forms.TextInput(attrs={'class': _field_class}),
            'salary': forms.TextInput(attrs={'class': _field_class}),
            'job_type': forms.Select(attrs={'class': _field_class}),
            'deadline': forms.DateInput(
                attrs={'type': 'date', 'class': _field_class}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].required = True


class JobApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ['cover_letter']
        widgets = {
            'cover_letter': forms.Textarea(
                attrs={'rows': 4, 'placeholder': 'Write your cover letter here...'}
            )
        }


class JobSearchForm(forms.Form):
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Job title or keyword'})
    )

    location = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Location'})
    )

    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label="All Categories"
    )

    job_type = forms.ChoiceField(
        required=False,
        choices=[('', 'All Types')] + Job.JOB_TYPE_CHOICES
    )
