import uuid
from django.contrib.auth.models import User
from django.db import models

class College(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150)
    def __str__(self): return f"{self.code} - {self.name}"

class Program(models.Model):
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name="programs")
    name = models.CharField(max_length=150)
    def __str__(self): return f"{self.college.code} - {self.name}"

class Profile(models.Model):
    ROLE_CHOICES = [("student","Student"),("officer","CSBO Officer"),("admin","Administrator")]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="student")
    requested_role = models.CharField(max_length=20, choices=ROLE_CHOICES, blank=True, default="")
    student_no = models.CharField(max_length=30, unique=True, null=True, blank=True)
    first_name = models.CharField(max_length=80, blank=True)
    middle_name = models.CharField(max_length=80, blank=True)
    last_name = models.CharField(max_length=80, blank=True)
    college = models.ForeignKey(College, on_delete=models.SET_NULL, null=True, blank=True)
    program = models.ForeignKey(Program, on_delete=models.SET_NULL, null=True, blank=True)
    year_level = models.PositiveSmallIntegerField(default=1)
    photo = models.ImageField(upload_to="students/", blank=True, null=True)
    qr_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    position = models.CharField(max_length=100, blank=True)
    def full_name(self):
        parts = [self.first_name, self.middle_name, self.last_name]
        name = " ".join([p for p in parts if p]).strip()
        return name or self.user.get_full_name() or self.user.username
    def __str__(self): return self.full_name()

class Event(models.Model):
    STATUS = [("upcoming","Upcoming"),("ongoing","Ongoing"),("completed","Completed"),("cancelled","Cancelled")]
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    venue = models.CharField(max_length=180)
    event_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    points = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS, default="upcoming")
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_events")
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.title

class AttendanceRecord(models.Model):
    STATUS = [("present","Present"),("absent","Absent"),("excused","Excused"),("corrected","Corrected")]
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="attendance")
    student = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="attendance")
    scanned_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="scans")
    scanned_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS, default="present")
    class Meta:
        constraints = [models.UniqueConstraint(fields=["event","student"], name="unique_event_student")]
        indexes = [models.Index(fields=["event","scanned_at"]), models.Index(fields=["student","scanned_at"])]

class ParticipationPoint(models.Model):
    student = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="points")
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    points = models.PositiveIntegerField()
    awarded_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["student","event"], name="unique_student_event_points")]

class Fine(models.Model):
    STATUS = [("unpaid","Unpaid"),("paid","Paid"),("waived","Waived")]
    student = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="fines")
    event = models.ForeignKey(Event, on_delete=models.SET_NULL, null=True, blank=True)
    reason = models.CharField(max_length=220)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS, default="unpaid")
    recorded_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="recorded_fines")
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class ClearanceRequirement(models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    required_points = models.PositiveIntegerField(default=0)
    required_events = models.PositiveIntegerField(default=0)
    def __str__(self): return self.name

class ClearanceRecord(models.Model):
    STATUS = [("pending","Pending"),("submitted","Submitted"),("completed","Completed"),("approved","Approved")]
    student = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="clearance_records")
    requirement = models.ForeignKey(ClearanceRequirement, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS, default="pending")
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["student","requirement"], name="unique_clearance")]

class Announcement(models.Model):
    CATEGORY = [("general","General"),("event","Event"),("clearance","Clearance"),("urgent","Urgent")]
    title = models.CharField(max_length=180)
    body = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY, default="general")
    published_by = models.ForeignKey(User, on_delete=models.PROTECT)
    published_at = models.DateTimeField(auto_now_add=True)
    status = models.BooleanField(default=True)

class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=120)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        indexes = [models.Index(fields=["created_at"])]

    def __str__(self): return f"{self.action} - {self.created_at}"
