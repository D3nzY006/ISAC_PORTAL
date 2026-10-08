import re
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import Event, Fine, Announcement, Profile, ClearanceRecord, AttendanceRecord, Program

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ["title","description","venue","event_date","start_time","end_time","points","status"]
        widgets = {
            "event_date": forms.DateInput(attrs={"type":"date"}),
            "start_time": forms.TimeInput(attrs={"type":"time"}),
            "end_time": forms.TimeInput(attrs={"type":"time"}),
        }

class FineForm(forms.ModelForm):
    class Meta:
        model = Fine
        fields = ["student","event","reason","amount","status"]

class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ["title","body","category","status"]

class ClearanceForm(forms.ModelForm):
    class Meta:
        model = ClearanceRecord
        fields = ["status"]

class AttendanceRecordForm(forms.ModelForm):
    class Meta:
        model = AttendanceRecord
        fields = ["student", "event", "status"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["student"].queryset = Profile.objects.filter(role="student").select_related("user", "college").order_by("last_name", "first_name")
        self.fields["event"].queryset = Event.objects.order_by("-event_date", "title")

    def clean_student(self):
        student = self.cleaned_data["student"]
        if student.role != "student":
            raise forms.ValidationError("Choose a student account.")
        return student

class UserManagementForm(forms.ModelForm):
    role = forms.ChoiceField(
        label="Account role",
        choices=Profile.ROLE_CHOICES,
        widget=forms.Select(attrs={"autocomplete": "off"}),
    )
    new_password = forms.CharField(
        label="Set a new password",
        required=False,
        strip=False,
        help_text="Leave blank to keep the current password.",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password", "placeholder": "Enter a temporary password"}),
    )
    confirm_new_password = forms.CharField(
        label="Confirm new password",
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password", "placeholder": "Re-enter the new password"}),
    )

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "is_active"]
        widgets = {
            "username": forms.TextInput(attrs={"autocomplete": "username", "autocapitalize": "none", "spellcheck": "false"}),
            "first_name": forms.TextInput(attrs={"autocomplete": "given-name"}),
            "last_name": forms.TextInput(attrs={"autocomplete": "family-name"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
        }

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("That username is already in use. Choose another one.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_new_password = cleaned_data.get("confirm_new_password")
        if new_password or confirm_new_password:
            if new_password != confirm_new_password:
                self.add_error("confirm_new_password", "The passwords do not match.")
            if new_password:
                try:
                    validate_password(new_password, self.instance)
                except forms.ValidationError as error:
                    self.add_error("new_password", error)
        return cleaned_data

class ProgramChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, program):
        return program.name


class SignUpForm(forms.Form):
    first_name = forms.CharField(
        max_length=80,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "First Name", "class": "form-control", "autocomplete": "given-name"})
    )
    middle_name = forms.CharField(
        max_length=80,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Middle Name (optional)", "class": "form-control", "autocomplete": "additional-name"})
    )
    last_name = forms.CharField(
        max_length=80,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "Last Name", "class": "form-control", "autocomplete": "family-name"})
    )
    student_no = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Student No. (e.g. 2026-0001)", "class": "form-control"})
    )
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "Username", "class": "form-control", "autocomplete": "username"})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"placeholder": "name@example.com", "class": "form-control", "autocomplete": "email"})
    )
    program = ProgramChoiceField(
        queryset=Program.objects.select_related("college").order_by("college__name", "name"),
        empty_label="Select course or program",
        required=True,
        widget=forms.Select(attrs={"class": "form-input"})
    )
    year_level = forms.TypedChoiceField(
        choices=[(1, "1st Year"), (2, "2nd Year"), (3, "3rd Year"), (4, "4th Year"), (5, "5th Year"), (6, "6th Year")],
        coerce=int,
        required=True,
        widget=forms.Select(attrs={"class": "form-input"})
    )
    requested_role = forms.ChoiceField(
        choices=Profile.ROLE_CHOICES,
        initial="student",
        required=True,
        widget=forms.Select(attrs={"class": "form-input"})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "••••••••", "class": "form-control", "autocomplete": "new-password"})
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "••••••••", "class": "form-control", "autocomplete": "new-password"})
    )

    def clean_username(self):
        username = self.cleaned_data.get("username", "").strip()
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9._-]{2,29}", username):
            raise forms.ValidationError(
                "Use 3–30 characters, start with a letter, and use only letters, numbers, dots, underscores, or hyphens."
            )
        letters = [character.lower() for character in username if character.isalpha()]
        if len(letters) >= 7 and not any(character in "aeiouy" for character in letters):
            raise forms.ValidationError("Use a recognizable username with at least one vowel.")
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken. Please choose another.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password")
        p2 = cleaned_data.get("password_confirm")
        if p1 and p2 and p1 != p2:
            self.add_error("password_confirm", "Passwords do not match.")
        if p1 and len(p1) < 6:
            self.add_error("password", "Password must be at least 6 characters.")
        return cleaned_data
