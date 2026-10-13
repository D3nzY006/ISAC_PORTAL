from django.contrib import admin
from .models import *
admin.site.register([College, Program, Profile, Event, AttendanceRecord, ParticipationPoint, Fine, ClearanceRequirement, ClearanceRecord, Announcement, AuditLog])
