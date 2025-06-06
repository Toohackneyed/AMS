from django import forms
from ams_app.models import Courses, SessionYearModel, Subjects, Students, Sections
from django.forms import ChoiceField

# ChoiceNoValidation is a custom ChoiceField that overrides the validate method to do nothing.
class ChoiceNoValidation(ChoiceField):
    def validate(self, value):
        pass

class DateInput(forms.DateInput):
    input_type = "date"

# Form for adding a new student ==============================================================================================================================
class AddStudentForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.student_id = kwargs.pop("student_id", None)
        super(AddStudentForm, self).__init__(*args, **kwargs)
        self.fields['course'].choices = [(course.id, course.course_name) for course in Courses.objects.all()]
        self.fields['session_year_id'].choices = [
            (ses.id, f"{ses.session_start_date} TO {ses.session_end_date}") for ses in SessionYearModel.objects.all()
        ]
    email = forms.EmailField(label="Email", max_length=50, widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Enter email address"}))
    password = forms.CharField(label="Password", max_length=50, widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Enter password"}))
    first_name = forms.CharField(label="First Name", max_length=50, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter first name"}))
    last_name = forms.CharField(label="Last Name", max_length=50, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter last name"}))
    username = forms.CharField(label="Username", max_length=50, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter username"}))
    id_number = forms.CharField(label="Student ID", max_length=50, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter student ID"}))
    rfid = forms.IntegerField(label="RFID", widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "Enter RFID"}))
    gender_choices = (("Male", "Male"), ("Female", "Female"))   
    gender = forms.ChoiceField(label="Gender", choices=gender_choices, widget=forms.Select(attrs={"class": "form-control"}))
    course = forms.ChoiceField(label="Course", choices=[], widget=forms.Select(attrs={"class": "form-control"}))
    section = forms.ModelChoiceField(
        queryset=Sections.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-control"})
    )
    session_year_id = forms.ChoiceField(label="Session Year", choices=[], widget=forms.Select(attrs={"class": "form-control"}))
    profile_pic = forms.FileField(label="Profile Picture", max_length=50, widget=forms.FileInput(attrs={"class": "form-control"}))
    student_id = forms.CharField(widget=forms.HiddenInput(), required=False)

# Form for editing an existing student =========================================================================================================================
class EditStudentForm(forms.Form):
    def __init__(self, *args, **kwargs):
        student_instance = kwargs.pop("student_instance", None)
        super(EditStudentForm, self).__init__(*args, **kwargs)
        if student_instance:
            self.fields['student_id'].initial = student_instance.admin.id
        self.fields['course'].choices = [(course.id, course.course_name) for course in Courses.objects.all()]
        self.fields['session_year_id'].choices = [
            (ses.id, f"{ses.session_start_date} TO {ses.session_end_date}") for ses in SessionYearModel.objects.all()
        ]
        if student_instance:
            self.fields['section'].initial = student_instance.section
    email = forms.EmailField(label="Email", max_length=50, widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Enter email address"}))
    first_name = forms.CharField(label="First Name", max_length=50, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter first name"}))
    last_name = forms.CharField(label="Last Name", max_length=50, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter last name"}))
    username = forms.CharField(label="Username", max_length=50, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter username"}))
    id_number = forms.CharField(label="Student ID", max_length=50, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter student ID"}))
    rfid = forms.IntegerField(label="RFID", widget=forms.NumberInput(attrs={"class": "form-control", "placeholder": "Enter RFID"}))
    gender_choices = (("Male", "Male"), ("Female", "Female"))
    gender = forms.ChoiceField(label="Gender", choices=gender_choices, widget=forms.Select(attrs={"class": "form-control"}))
    course = forms.ChoiceField(label="Main Course", choices=[], widget=forms.Select(attrs={"class": "form-control"}))
    section = forms.ModelChoiceField(
        queryset=Sections.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-control"})
    )
    session_year_id = forms.ChoiceField(label="Session Year", choices=[], widget=forms.Select(attrs={"class": "form-control"}))
    profile_pic = forms.FileField(label="Profile Picture", widget=forms.FileInput(attrs={"class": "form-control"}), required=False)
    student_id = forms.CharField(widget=forms.HiddenInput(), required=False)

