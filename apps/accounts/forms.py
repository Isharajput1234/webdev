from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Employer, JobSeeker


def _normalize_email(email: str) -> str:
    if not email:
        return email
    e = email.strip().lower()
    # Common typos from users: gamil.com / gamail.com
    e = e.replace("@gamil.com", "@gmail.com").replace("@gamail.com", "@gmail.com")
    return e

class EmployerSignUpForm(UserCreationForm):
    company_name = forms.CharField(max_length=255)
    company_description = forms.CharField(widget=forms.Textarea, required=False)
    company_website = forms.URLField(required=False)
    company_logo = forms.ImageField(required=False)

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'email', 'password1', 'password2')

    def clean_email(self):
        return _normalize_email(self.cleaned_data.get("email"))

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_employer = True
        if commit:
            user.save()
            Employer.objects.create(
                user=user,
                company_name=self.cleaned_data.get('company_name'),
                company_description=self.cleaned_data.get('company_description'),
                company_website=self.cleaned_data.get('company_website'),
                company_logo=self.cleaned_data.get('company_logo')
            )
        return user

class JobSeekerSignUpForm(UserCreationForm):
    skills = forms.CharField(widget=forms.Textarea, required=False)
    resume = forms.FileField(required=False)
    experience = forms.CharField(widget=forms.Textarea, required=False)
    education = forms.CharField(widget=forms.Textarea, required=False)

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'email', 'password1', 'password2')

    def clean_email(self):
        return _normalize_email(self.cleaned_data.get("email"))

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_job_seeker = True
        if commit:
            user.save()
            JobSeeker.objects.create(
                user=user,
                skills=self.cleaned_data.get('skills'),
                resume=self.cleaned_data.get('resume'),
                experience=self.cleaned_data.get('experience'),
                education=self.cleaned_data.get('education')
            )
        return user 


class JobSeekerUpdateForm(forms.ModelForm):
    class Meta:
        model = JobSeeker
        fields = ("skills", "experience", "education", "resume")
        widgets = {
            "skills": forms.Textarea(attrs={"rows": 4}),
            "experience": forms.Textarea(attrs={"rows": 4}),
            "education": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = "w-full rounded-lg border border-gray-300 px-3 py-2 focus:ring-2 focus:ring-indigo-500/40 focus:border-indigo-500"
            if isinstance(field.widget, forms.ClearableFileInput):
                css = "w-full text-sm text-gray-700"
            field.widget.attrs["class"] = css


class ResumeAnalyzerForm(forms.Form):
    skills = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Python, Django, SQL, ..."}),
        required=False,
    )
    experience = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 6, "placeholder": "Role | Company | Dates\n- Bullet with results"}),
        required=False,
    )
    education = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Degree | University | Year"}),
        required=False,
    )
    resume_draft = forms.CharField(
        label="Full resume preview",
        widget=forms.Textarea(attrs={"rows": 14, "placeholder": "Edit your full resume text here..."}),
        required=False,
    )
    resume_file = forms.FileField(
        label="Upload resume to analyze (PDF or TXT)",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = "w-full rounded-lg border border-gray-300 px-3 py-2 focus:ring-2 focus:ring-indigo-500/40 focus:border-indigo-500 text-sm"
            field.widget.attrs["class"] = css


class EmployerUpdateForm(forms.ModelForm):
    class Meta:
        model = Employer
        fields = (
            "company_name",
            "company_description",
            "company_website",
            "company_logo",
            "location",
            "phone",
            "industry",
        )
        widgets = {
            "company_description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = "w-full rounded-lg border border-gray-300 px-3 py-2 focus:ring-2 focus:ring-indigo-500/40 focus:border-indigo-500"
            if isinstance(field.widget, forms.ClearableFileInput):
                css = "w-full text-sm text-gray-700"
            field.widget.attrs["class"] = css