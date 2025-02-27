from django import forms
from ams_app.models import Courses, SessionYearModel, Subjects, Students
from django.forms import ChoiceField

class ChoiceNoValidation(ChoiceField):
    def validate(self, value):
        pass

class DateInput(forms.DateInput):
    input_type = "date"

class AddStudentForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(AddStudentForm, self).__init__(*args, **kwargs)
        self.fields['course'].choices = [(course.id, course.course_name) for course in Courses.objects.all()]
        self.fields['session_year_id'].choices = [
            (ses.id, f"{ses.session_start_date} TO {ses.session_end_date}") for ses in SessionYearModel.objects.all()
        ]

    email = forms.EmailField(label="Email", max_length=50, widget=forms.EmailInput(attrs={"class": "form-control"}))
    password = forms.CharField(label="Password", max_length=50, widget=forms.PasswordInput(attrs={"class": "form-control"}))
    first_name = forms.CharField(label="First Name", max_length=50, widget=forms.TextInput(attrs={"class": "form-control"}))
    last_name = forms.CharField(label="Last Name", max_length=50, widget=forms.TextInput(attrs={"class": "form-control"}))
    username = forms.CharField(label="Username", max_length=50, widget=forms.TextInput(attrs={"class": "form-control"}))
    id_number = forms.CharField(label="Student ID", max_length=50, widget=forms.TextInput(attrs={"class": "form-control"}))
    rfid = forms.CharField(label="RFID", max_length=50, widget=forms.TextInput(attrs={"class": "form-control"}))

    gender_choices = (("Male", "Male"), ("Female", "Female"))
    gender = forms.ChoiceField(label="Gender", choices=gender_choices, widget=forms.Select(attrs={"class": "form-control"}))

    course = forms.ChoiceField(label="Course", choices=[], widget=forms.Select(attrs={"class": "form-control"}))
    session_year_id = forms.ChoiceField(label="Session Year", choices=[], widget=forms.Select(attrs={"class": "form-control"}))

    profile_pic = forms.FileField(label="Profile Picture", max_length=50, widget=forms.FileInput(attrs={"class": "form-control"}))

class EditStudentForm(forms.Form):
    email = forms.EmailField(label="Email", max_length=50, widget=forms.EmailInput(attrs={"class": "form-control"}))
    first_name = forms.CharField(label="First Name", max_length=50, widget=forms.TextInput(attrs={"class": "form-control"}))
    last_name = forms.CharField(label="Last Name", max_length=50, widget=forms.TextInput(attrs={"class": "form-control"}))
    username = forms.CharField(label="Username", max_length=50, widget=forms.TextInput(attrs={"class": "form-control"}))
    id_number = forms.CharField(label="Student ID", max_length=50, widget=forms.TextInput(attrs={"class": "form-control"}))
    rfid = forms.CharField(label="RFID", max_length=50, widget=forms.TextInput(attrs={"class": "form-control"}))

    gender_choices = (("Male", "Male"), ("Female", "Female"))
    gender = forms.ChoiceField(label="Gender", choices=gender_choices, widget=forms.Select(attrs={"class": "form-control"}))
    
    profile_pic = forms.FileField(label="Profile Picture", max_length=50, widget=forms.FileInput(attrs={"class": "form-control"}), required=False)

    def __init__(self, *args, **kwargs):
        super(EditStudentForm, self).__init__(*args, **kwargs)
        self.fields['course'].choices = [(course.id, course.course_name) for course in Courses.objects.all()]
        self.fields['session_year_id'].choices = [
            (ses.id, f"{ses.session_start_date} TO {ses.session_end_date}") for ses in SessionYearModel.objects.all()
        ]

    course = forms.ChoiceField(label="Course", choices=[], widget=forms.Select(attrs={"class": "form-control"}))
    session_year_id = forms.ChoiceField(label="Session Year", choices=[], widget=forms.Select(attrs={"class": "form-control"}))
