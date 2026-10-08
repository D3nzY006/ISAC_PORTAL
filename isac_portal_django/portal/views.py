import io, json, calendar as calendar_utils
from urllib.parse import urlencode
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncDate
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.utils.dateparse import parse_date
from .models import *
from .forms import EventForm, FineForm, AnnouncementForm, ClearanceForm, SignUpForm, UserManagementForm, AttendanceRecordForm

def role_required(*roles):
    def deco(view):
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated: return redirect("login")
            role = getattr(getattr(request.user, "profile", None), "role", None)
            if role not in roles:
                messages.error(request, "You do not have permission to access this page.")
                return redirect("dashboard")
            return view(request, *args, **kwargs)
        return wrapped
    return deco

def current_profile(request):
    return getattr(request.user, "profile", None)

@login_required
def dashboard(request):
    p = current_profile(request)
    if p and p.role in ("officer","admin"):
        return redirect("officer_dashboard")
    return redirect("student_dashboard") if "student_dashboard" in [] else render_student_dashboard(request)

@login_required
def render_student_dashboard(request):
    p = current_profile(request)
    if not p: return redirect("/admin/")
    attended = AttendanceRecord.objects.filter(student=p).count()
    points = ParticipationPoint.objects.filter(student=p).aggregate(total=Sum("points"))["total"] or 0
    unpaid = Fine.objects.filter(student=p, status="unpaid").aggregate(total=Sum("amount"))["total"] or Decimal("0")
    reqs = ClearanceRequirement.objects.all()
    completed = ClearanceRecord.objects.filter(student=p, status__in=["completed","approved"]).count()
    progress = int((completed / reqs.count()) * 100) if reqs.exists() else 0
    return render(request, "portal/student_dashboard.html", {
        "profile":p,"attended":attended,"points":points,"unpaid":unpaid,"progress":progress,
        "events":Event.objects.filter(status__in=["upcoming","ongoing"]).order_by("event_date","start_time")[:5],
        "announcements":Announcement.objects.filter(status=True).order_by("-published_at")[:5],
        "recent":AttendanceRecord.objects.filter(student=p).select_related("event").order_by("-scanned_at")[:5],
    })

@login_required
def digital_id(request):
    import qrcode
    from base64 import b64encode
    p=current_profile(request)
    qr=qrcode.make(str(p.qr_token))
    buf=io.BytesIO()
    qr.save(buf, format="PNG")
    qr_data="data:image/png;base64," + b64encode(buf.getvalue()).decode()
    return render(request,"portal/digital_id.html",{"profile":p,"qr_data":qr_data})

@login_required
def event_calendar(request):
    today = timezone.localdate()
    try:
        year = int(request.GET.get("year", today.year))
        month = int(request.GET.get("month", today.month))
        first_day = date(year, month, 1)
    except (TypeError, ValueError):
        first_day = today.replace(day=1)
        year, month = first_day.year, first_day.month
    last_day = date(year, month, calendar_utils.monthrange(year, month)[1])
    month_events = list(Event.objects.filter(event_date__range=(first_day, last_day)).order_by("event_date", "start_time"))
    events_by_date = {}
    for event in month_events:
        events_by_date.setdefault(event.event_date, []).append(event)
    days = []
    for week in calendar_utils.Calendar(firstweekday=6).monthdayscalendar(year, month):
        for day_number in week:
            if day_number:
                day_date = date(year, month, day_number)
                days.append({"date": day_date, "day": day_number, "today": day_date == today, "events": events_by_date.get(day_date, [])})
            else:
                days.append({"date": None, "day": "", "today": False, "events": []})
    previous_month = first_day - timedelta(days=1)
    next_month = last_day + timedelta(days=1)
    return render(request, "portal/calendar.html", {
        "calendar_days": days, "events": month_events,
        "month_title": first_day.strftime("%B %Y"),
        "previous_month": previous_month, "next_month": next_month,
        "month_number": month, "year_number": year,
    })

@login_required
def my_activities(request):
    p=current_profile(request)
    return render(request,"portal/activities.html",{"records":AttendanceRecord.objects.filter(student=p).select_related("event").order_by("-scanned_at")})

@login_required
def clearance(request):
    p=current_profile(request)
    records=ClearanceRecord.objects.filter(student=p).select_related("requirement").order_by("status", "requirement__name")
    workflow = ("pending", "submitted", "completed", "approved")
    for record in records:
        active_step = workflow.index(record.status) if record.status in workflow else 0
        record.workflow_steps = [
            {"label": label, "complete": index < active_step or record.status == "approved", "current": index == active_step and record.status != "approved"}
            for index, label in enumerate(workflow)
        ]
    fines=Fine.objects.filter(student=p).order_by("-created_at")
    completed=records.filter(status__in=["completed","approved"]).count()
    total=records.count()
    progress=int(completed/total*100) if total else 0
    overall="Cleared" if total and completed==total and not fines.filter(status="unpaid").exists() else "Pending"
    return render(request,"portal/clearance.html",{"records":records,"fines":fines,"progress":progress,"overall":overall})

@login_required
def announcements(request):
    items = Announcement.objects.filter(status=True)
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    for term in query.split():
        items = items.filter(Q(title__icontains=term) | Q(body__icontains=term) | Q(category__icontains=term))
    if category in dict(Announcement.CATEGORY):
        items = items.filter(category=category)
    else:
        category = ""
    return render(request,"portal/announcements.html",{
        "items": items.order_by("-published_at"), "q": query, "category": category,
        "categories": Announcement.CATEGORY,
    })

@role_required("officer","admin")
def officer_dashboard(request):
    today = timezone.localdate()
    total_events = Event.objects.count()
    today_attendance = AttendanceRecord.objects.filter(
        scanned_at__date=today, status__in=("present", "corrected")
    ).count()
    pending = ClearanceRecord.objects.exclude(status__in=("completed", "approved")).count()
    unpaid = Fine.objects.filter(status="unpaid").aggregate(total=Sum("amount"))["total"] or 0

    latest_scans = list(
        AttendanceRecord.objects.select_related("student", "event")
        .order_by("-scanned_at")[:8]
    )

    year_level_rows = list(
        AttendanceRecord.objects.filter(status__in=("present", "corrected"))
        .values("student__year_level")
        .annotate(total=Count("student", distinct=True))
        .order_by("student__year_level")
    )
    year_level_data = [
        {"label": f"{row['student__year_level']}{'st' if row['student__year_level'] == 1 else 'nd' if row['student__year_level'] == 2 else 'rd' if row['student__year_level'] == 3 else 'th'} Year", "total": row["total"]}
        for row in year_level_rows
    ]

    attended_events = list(
        Event.objects.annotate(
            attendee_count=Count("attendance", filter=Q(attendance__status__in=("present", "corrected")))
        ).filter(attendee_count__gt=0).order_by("-event_date", "-start_time")[:50]
    )
    event_attendance = list(
        Event.objects.annotate(
            attendee_count=Count("attendance", filter=Q(attendance__status__in=("present", "corrected")))
        ).filter(attendee_count__gt=0).order_by("-attendee_count", "title")[:8]
    )
    selected_event = None
    requested_event_id = request.GET.get("analytics_event", "").strip()
    if requested_event_id.isdigit():
        selected_event = next((event for event in attended_events if event.id == int(requested_event_id)), None)
    if selected_event is None and attended_events:
        selected_event = attended_events[0]

    hourly_counts = {hour: 0 for hour in range(24)}
    if selected_event:
        scan_times = AttendanceRecord.objects.filter(
            event=selected_event, status__in=("present", "corrected")
        ).values_list("scanned_at", flat=True)
        for scanned_at in scan_times.iterator(chunk_size=2000):
            local_scan = timezone.localtime(scanned_at) if timezone.is_aware(scanned_at) else scanned_at
            hourly_counts[local_scan.hour] += 1

    semester_periods = []
    current_year = today.year
    current_half = 1 if today.month <= 6 else 2
    for offset in range(3, -1, -1):
        period_index = current_year * 2 + current_half - 1 - offset
        year, half_index = divmod(period_index, 2)
        half = half_index + 1
        semester_periods.append({
            "year": year,
            "half": half,
            "label": f"{year} {'Jan–Jun' if half == 1 else 'Jul–Dec'}",
            "start": date(year, 1 if half == 1 else 7, 1),
        })
    period_start = semester_periods[0]["start"]
    fine_counts = {(period["year"], period["half"]): {"paid": 0, "unpaid": 0, "waived": 0} for period in semester_periods}
    for row in Fine.objects.filter(created_at__date__range=(period_start, today)).values(
        "status", "created_at__year", "created_at__month"
    ).annotate(total=Count("id")):
        key = (row["created_at__year"], 1 if row["created_at__month"] <= 6 else 2)
        if key in fine_counts:
            fine_counts[key][row["status"]] = row["total"]

    clearance_counts = {(period["year"], period["half"]): {"cleared": 0, "pending": 0} for period in semester_periods}
    for row in ClearanceRecord.objects.filter(updated_at__date__range=(period_start, today)).values(
        "status", "updated_at__year", "updated_at__month"
    ).annotate(total=Count("id")):
        key = (row["updated_at__year"], 1 if row["updated_at__month"] <= 6 else 2)
        if key in clearance_counts:
            bucket = "cleared" if row["status"] in ("completed", "approved") else "pending"
            clearance_counts[key][bucket] += row["total"]

    chart_data = {
        "yearLevels": year_level_data,
        "eventAttendance": [{"label": event.title, "total": event.attendee_count} for event in event_attendance],
        "peakHours": [{"label": f"{hour % 12 or 12} {'AM' if hour < 12 else 'PM'}", "total": hourly_counts[hour]} for hour in range(24)],
        "semesterStatus": {
            "labels": [period["label"] for period in semester_periods],
            "clearanceCleared": [clearance_counts[(period["year"], period["half"])]["cleared"] for period in semester_periods],
            "clearancePending": [clearance_counts[(period["year"], period["half"])]["pending"] for period in semester_periods],
            "finesPaid": [fine_counts[(period["year"], period["half"])]["paid"] for period in semester_periods],
            "finesUnpaid": [fine_counts[(period["year"], period["half"])]["unpaid"] for period in semester_periods],
            "finesWaived": [fine_counts[(period["year"], period["half"])]["waived"] for period in semester_periods],
        },
    }
    return render(request, "portal/officer_dashboard.html", {
        "total_events": total_events,
        "today_attendance": today_attendance,
        "pending": pending,
        "unpaid": unpaid,
        "latest_scans": latest_scans,
        "attended_events": attended_events,
        "selected_event": selected_event,
        "chart_data": chart_data,
    })

@role_required("officer","admin")
def events_manage(request):
    return render(request,"portal/events_manage.html",{"events":Event.objects.all().order_by("-event_date","-start_time")})

@role_required("officer","admin")
def event_create(request):
    form=EventForm(request.POST or None)
    if form.is_valid():
        obj=form.save(commit=False); obj.created_by=request.user; obj.save()
        AuditLog.objects.create(user=request.user,action="CREATE_EVENT",details=obj.title)
        messages.success(request,"Event created successfully."); return redirect("events_manage")
    return render(request,"portal/form.html",{"form":form,"title":"Create Event","back":"events_manage"})

@role_required("officer","admin")
def event_edit(request,event_id):
    obj=get_object_or_404(Event,id=event_id); form=EventForm(request.POST or None,instance=obj)
    if form.is_valid():
        form.save(); AuditLog.objects.create(user=request.user,action="EDIT_EVENT",details=obj.title)
        messages.success(request,"Event updated."); return redirect("events_manage")
    return render(request,"portal/form.html",{"form":form,"title":"Edit Event","back":"events_manage"})

@role_required("officer","admin")
def event_delete(request,event_id):
    if request.method=="POST":
        obj=get_object_or_404(Event,id=event_id); title=obj.title; obj.delete()
        AuditLog.objects.create(user=request.user,action="DELETE_EVENT",details=title)
    return redirect("events_manage")

@role_required("officer","admin")
def scanner(request):
    return render(request,"portal/scanner.html",{"events":Event.objects.filter(status__in=["ongoing","upcoming"]).order_by("event_date","start_time")})

@role_required("officer","admin")
@transaction.atomic
def scan_attendance(request):
    if request.method!="POST": return JsonResponse({"ok":False,"message":"POST required"},status=405)
    try:
        data=json.loads(request.body or "{}")
        token=data.get("qr_token","").strip()
        student_id=data.get("student_id","").strip()
        event=get_object_or_404(Event,id=int(data.get("event_id")))
        if student_id:
            student=get_object_or_404(Profile,student_no=student_id)
        else:
            student=get_object_or_404(Profile,qr_token=token)
        if student.role if hasattr(student,"role") else False:
            pass
        if event.status not in ("ongoing",):
            return JsonResponse({"ok":False,"type":"invalid","message":"This event is not currently ongoing."})
        if AttendanceRecord.objects.filter(event=event,student=student).exists():
            return JsonResponse({"ok":False,"type":"duplicate","message":"Student is already recorded for this event.","student":student.full_name()})
        AttendanceRecord.objects.create(event=event,student=student,scanned_by=request.user)
        ParticipationPoint.objects.get_or_create(student=student,event=event,defaults={"points":event.points})
        AuditLog.objects.create(user=request.user,action="SCAN_ATTENDANCE",details=f"{student.student_no} - {event.title}")
        return JsonResponse({"ok":True,"type":"success","message":"Attendance recorded.","student":student.full_name(),"college":student.college.code if student.college else "—","year":student.year_level,"time":timezone.localtime().strftime("%I:%M %p")})
    except Exception as e:
        return JsonResponse({"ok":False,"type":"invalid","message":"Invalid QR code or scan request."},status=400)

@role_required("officer","admin")
def attendance_records(request):
    qs=AttendanceRecord.objects.select_related("student","student__college","event").order_by("-scanned_at")
    q=request.GET.get("q","").strip()
    if q: qs=qs.filter(Q(student__student_no__icontains=q)|Q(student__first_name__icontains=q)|Q(student__last_name__icontains=q)|Q(event__title__icontains=q))
    profile = current_profile(request)
    return render(request,"portal/attendance.html",{"records":qs[:300],"q":q,"can_manage_attendance":bool(profile and profile.role == "admin")})

@role_required("admin")
def attendance_create(request):
    form = AttendanceRecordForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        record = form.save(commit=False)
        record.scanned_by = request.user
        record.save()
        if record.status == "present":
            ParticipationPoint.objects.get_or_create(student=record.student, event=record.event, defaults={"points": record.event.points})
        AuditLog.objects.create(user=request.user, action="ADD_ATTENDANCE", details=f"{record.student.student_no} - {record.event.title} ({record.status})")
        messages.success(request, "Student attendance added.")
        return redirect("attendance_records")
    return render(request, "portal/form.html", {"form": form, "title": "Add Student Attendance", "back": "attendance_records"})

@role_required("admin")
@require_POST
def attendance_update_status(request, record_id):
    record = get_object_or_404(AttendanceRecord.objects.select_related("student", "event"), id=record_id)
    status = request.POST.get("status", "")
    if status not in {"present", "absent", "excused"}:
        messages.error(request, "Choose a valid attendance status.")
        return redirect("attendance_records")
    record.status = status
    record.save(update_fields=["status"])
    points = ParticipationPoint.objects.filter(student=record.student, event=record.event)
    if status == "present":
        ParticipationPoint.objects.get_or_create(student=record.student, event=record.event, defaults={"points": record.event.points})
    else:
        points.delete()
    AuditLog.objects.create(user=request.user, action="UPDATE_ATTENDANCE", details=f"{record.student.student_no} - {record.event.title} ({status})")
    messages.success(request, f"Attendance marked {status}.")
    return redirect("attendance_records")

@role_required("admin")
@require_POST
def attendance_delete(request, record_id):
    record = get_object_or_404(AttendanceRecord.objects.select_related("student", "event"), id=record_id)
    details = f"{record.student.student_no} - {record.event.title} ({record.status})"
    ParticipationPoint.objects.filter(student=record.student, event=record.event).delete()
    record.delete()
    AuditLog.objects.create(user=request.user, action="DELETE_ATTENDANCE", details=details)
    messages.success(request, "Attendance record deleted.")
    return redirect("attendance_records")

@role_required("officer","admin")
def fines(request):
    fines_qs = Fine.objects.select_related("student", "event").order_by("-created_at")
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()
    min_amount = request.GET.get("min_amount", "").strip()
    max_amount = request.GET.get("max_amount", "").strip()
    if query:
        fines_qs = fines_qs.filter(Q(student__student_no__icontains=query) | Q(student__first_name__icontains=query) | Q(student__last_name__icontains=query) | Q(reason__icontains=query))
    if status in {"paid", "unpaid", "waived"}:
        fines_qs = fines_qs.filter(status=status)
    parsed_date_from = parse_date(date_from) if date_from else None
    parsed_date_to = parse_date(date_to) if date_to else None
    if parsed_date_from:
        fines_qs = fines_qs.filter(created_at__date__gte=parsed_date_from)
    elif date_from:
        messages.error(request, "Enter a valid start date to filter fines.")
        date_from = ""
    if parsed_date_to:
        fines_qs = fines_qs.filter(created_at__date__lte=parsed_date_to)
    elif date_to:
        messages.error(request, "Enter a valid end date to filter fines.")
        date_to = ""
    try:
        minimum = Decimal(min_amount) if min_amount else None
        maximum = Decimal(max_amount) if max_amount else None
        if (minimum is not None and (not minimum.is_finite() or minimum < 0)) or (maximum is not None and (not maximum.is_finite() or maximum < 0)):
            raise InvalidOperation
        if minimum is not None:
            fines_qs = fines_qs.filter(amount__gte=minimum)
        if maximum is not None:
            fines_qs = fines_qs.filter(amount__lte=maximum)
    except InvalidOperation:
        messages.error(request, "Enter a valid amount to filter fines.")
        min_amount = max_amount = ""
    page_obj = Paginator(fines_qs, 20).get_page(request.GET.get("page"))
    return render(request, "portal/fines.html", {
        "fines": page_obj.object_list, "page_obj": page_obj,
        "query": query, "selected_status": status, "date_from": date_from,
        "date_to": date_to, "min_amount": min_amount, "max_amount": max_amount,
    })

@role_required("officer","admin")
def fine_create(request):
    form=FineForm(request.POST or None)
    if form.is_valid():
        obj=form.save(commit=False); obj.recorded_by=request.user; obj.save()
        AuditLog.objects.create(user=request.user,action="CREATE_FINE",details=f"{obj.student.student_no} {obj.amount}")
        messages.success(request,"Fine recorded."); return redirect("fines")
    return render(request,"portal/form.html",{"form":form,"title":"Record Fine","back":"fines"})

@role_required("officer","admin")
def fine_edit(request, fine_id):
    obj = get_object_or_404(Fine, id=fine_id)
    form = FineForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        AuditLog.objects.create(user=request.user, action="EDIT_FINE", details=f"Updated fine {obj.id} for {obj.student.student_no}")
        messages.success(request, "Fine record updated.")
        return redirect("fines")
    return render(request, "portal/form.html", {"form": form, "title": "Edit Fine", "back": "fines"})

@role_required("officer","admin")
@require_POST
def fine_delete(request, fine_id):
    obj = get_object_or_404(Fine, id=fine_id)
    details = f"Deleted fine {obj.id} for {obj.student.student_no} ({obj.amount})"
    obj.delete()
    AuditLog.objects.create(user=request.user, action="DELETE_FINE", details=details)
    messages.success(request, "Fine record deleted.")
    return redirect("fines")

@role_required("officer","admin")
def clearance_manage(request):
    if request.method=="POST":
        rec=get_object_or_404(ClearanceRecord,id=request.POST.get("id"))
        status=request.POST.get("status")
        if status not in dict(ClearanceRecord.STATUS):
            messages.error(request,"Choose a valid clearance status.")
            return _clearance_manage_redirect(request)
        rec.status=status; rec.updated_by=request.user; rec.save()
        AuditLog.objects.create(user=request.user,action="UPDATE_CLEARANCE",details=f"{rec.student.student_no}: {rec.status}")
        messages.success(request,"Clearance updated.")
        return _clearance_manage_redirect(request)
    records = ClearanceRecord.objects.select_related("student", "student__college", "requirement")
    query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status_filter", "").strip()
    requirement_id = request.GET.get("requirement_id", "").strip()
    if query:
        for term in query.split():
            records = records.filter(
                Q(student__student_no__icontains=term)
                | Q(student__first_name__icontains=term)
                | Q(student__middle_name__icontains=term)
                | Q(student__last_name__icontains=term)
                | Q(requirement__name__icontains=term)
                | Q(student__college__code__icontains=term)
            )
    valid_statuses = dict(ClearanceRecord.STATUS)
    if status_filter in valid_statuses:
        records = records.filter(status=status_filter)
    else:
        status_filter = ""
    if requirement_id.isdigit() and ClearanceRequirement.objects.filter(id=requirement_id).exists():
        records = records.filter(requirement_id=requirement_id)
    else:
        requirement_id = ""
    return render(request,"portal/clearance_manage.html",{
        "records": records.order_by("status", "student__last_name", "student__first_name", "requirement__name"),
        "q": query,
        "status_filter": status_filter,
        "requirement_id": requirement_id,
        "requirements": ClearanceRequirement.objects.order_by("name"),
    })

def _clearance_manage_redirect(request):
    filters = {key: request.POST.get(key, "").strip() for key in ("q", "status_filter", "requirement_id") if request.POST.get(key, "").strip()}
    url = reverse("clearance_manage")
    return redirect(f"{url}?{urlencode(filters)}" if filters else url)

@role_required("officer","admin")
def announcement_manage(request):
    items = Announcement.objects.all()
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    publish_status = request.GET.get("publish_status", "").strip()
    for term in query.split():
        items = items.filter(Q(title__icontains=term) | Q(body__icontains=term) | Q(category__icontains=term))
    if category in dict(Announcement.CATEGORY):
        items = items.filter(category=category)
    else:
        category = ""
    if publish_status == "published":
        items = items.filter(status=True)
    elif publish_status == "draft":
        items = items.filter(status=False)
    else:
        publish_status = ""
    return render(request,"portal/announcement_manage.html",{
        "items": items.order_by("-published_at"), "q": query, "category": category,
        "publish_status": publish_status, "categories": Announcement.CATEGORY,
    })

@role_required("officer","admin")
def announcement_create(request):
    form=AnnouncementForm(request.POST or None)
    if form.is_valid():
        obj=form.save(commit=False); obj.published_by=request.user; obj.save()
        messages.success(request,"Announcement published."); return redirect("announcement_manage")
    return render(request,"portal/form.html",{"form":form,"title":"Create Announcement","back":"announcement_manage"})

@role_required("officer","admin")
def announcement_edit(request, announcement_id):
    obj = get_object_or_404(Announcement, id=announcement_id)
    form = AnnouncementForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        AuditLog.objects.create(user=request.user, action="EDIT_ANNOUNCEMENT", details=obj.title)
        messages.success(request, "Announcement updated.")
        return redirect("announcement_manage")
    return render(request, "portal/form.html", {"form": form, "title": "Edit Announcement", "back": "announcement_manage"})

@role_required("officer","admin")
@require_POST
def announcement_delete(request, announcement_id):
    obj = get_object_or_404(Announcement, id=announcement_id)
    title = obj.title
    obj.delete()
    AuditLog.objects.create(user=request.user, action="DELETE_ANNOUNCEMENT", details=title)
    messages.success(request, "Announcement deleted.")
    return redirect("announcement_manage")

@role_required("officer","admin")
def reports(request):
    qs=AttendanceRecord.objects.select_related("student","event").order_by("-scanned_at")
    college=request.GET.get("college",""); year=request.GET.get("year",""); event=request.GET.get("event","")
    if college: qs=qs.filter(student__college__code=college)
    if year: qs=qs.filter(student__year_level=year)
    if event: qs=qs.filter(event_id=event)
    page_obj=Paginator(qs,25).get_page(request.GET.get("page"))
    return render(request,"portal/reports.html",{"records":page_obj.object_list,"page_obj":page_obj,"colleges":College.objects.all(),"events":Event.objects.all(),"filters":request.GET})

def _filtered_attendance(request):
    qs=AttendanceRecord.objects.select_related("student__college","student__program","event").order_by("-scanned_at")
    if request.GET.get("college"): qs=qs.filter(student__college__code=request.GET["college"])
    if request.GET.get("year"): qs=qs.filter(student__year_level=request.GET["year"])
    if request.GET.get("event"): qs=qs.filter(event_id=request.GET["event"])
    return qs

@role_required("officer","admin")
def report_excel(request):
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment
    wb=Workbook(); ws=wb.active; ws.title="Attendance Report"
    ws.append(["ISAC PORTAL","DMMMSU–NLUC Campus"])
    ws.append(["Campus Student Body Organization","Attendance Report"])
    ws.append(["Generated",timezone.localtime().strftime("%Y-%m-%d %H:%M"),"Officer",request.user.get_full_name() or request.user.username])
    ws.append([])
    ws.append(["Student ID","Student Name","College","Program","Year","Event","Date","Time","Status"])
    for r in _filtered_attendance(request):
        ws.append([r.student.student_no,r.student.full_name(),r.student.college.code if r.student.college else "",r.student.program.name if r.student.program else "",r.student.year_level,r.event.title,str(r.event.event_date),timezone.localtime(r.scanned_at).strftime("%H:%M"),r.status])
    for cell in ws[1]: cell.font=Font(bold=True,size=14)
    for col in ws.columns:
        letter=col[0].column_letter; ws.column_dimensions[letter].width=min(35,max(12,max(len(str(c.value or "")) for c in col)+2))
    out=io.BytesIO(); wb.save(out); out.seek(0)
    resp=HttpResponse(out.read(),content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"]='attachment; filename="ISAC_Attendance_Report.xlsx"'; return resp

@role_required("officer","admin")
def report_pdf(request):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    out=io.BytesIO(); doc=SimpleDocTemplate(out,pagesize=landscape(A4),rightMargin=25,leftMargin=25,topMargin=25,bottomMargin=25)
    styles=getSampleStyleSheet(); story=[Paragraph("ISAC PORTAL — DMMMSU–NLUC CAMPUS",styles["Title"]),Paragraph("Campus Student Body Organization — Attendance Report",styles["Heading2"]),Paragraph(f"Generated: {timezone.localtime().strftime('%Y-%m-%d %H:%M')} | Officer: {request.user.get_full_name() or request.user.username}",styles["Normal"]),Spacer(1,12)]
    data=[["Student ID","Student Name","College","Year","Event","Date","Time","Status"]]
    for r in _filtered_attendance(request):
        data.append([r.student.student_no,r.student.full_name(),r.student.college.code if r.student.college else "",r.student.year_level,r.event.title,str(r.event.event_date),timezone.localtime(r.scanned_at).strftime("%H:%M"),r.status])
    table=Table(data,repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#0F3D2A")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.5,colors.HexColor("#D9E2DC")),("FONTSIZE",(0,0),(-1,-1),8),("VALIGN",(0,0),(-1,-1),"MIDDLE")]))
    story.append(table); doc.build(story); out.seek(0)
    resp=HttpResponse(out.read(),content_type="application/pdf"); resp["Content-Disposition"]='attachment; filename="ISAC_Attendance_Report.pdf"'; return resp

@role_required("admin")
def user_manage(request):
    users = User.objects.select_related("profile").all().order_by("username", "id")
    query = request.GET.get("q", "").strip()
    role = request.GET.get("role", "").strip()
    status = request.GET.get("status", "").strip()

    if query:
        search_filter = (
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
            | Q(profile__student_no__icontains=query)
        )
        if query.isdigit():
            search_filter |= Q(id=int(query))
        users = users.filter(search_filter)
    if role in {"student", "officer", "admin"}:
        users = users.filter(profile__role=role)
    if status == "active":
        users = users.filter(is_active=True)
    elif status == "inactive":
        users = users.filter(is_active=False)

    page_obj = Paginator(users.distinct(), 15).get_page(request.GET.get("page"))
    role_requests = Profile.objects.filter(
        requested_role__in=("officer", "admin")
    ).select_related("user", "college", "program").order_by("user__date_joined", "user__username")
    return render(request, "portal/user_manage.html", {
        "page_obj": page_obj,
        "users": page_obj.object_list,
        "query": query,
        "selected_role": role,
        "selected_status": status,
        "total_users": User.objects.count(),
        "admin_count": Profile.objects.filter(role="admin", user__is_active=True).count(),
        "active_count": User.objects.filter(is_active=True).count(),
        "role_requests": role_requests,
        "role_request_count": role_requests.count(),
    })


def admin_panel_redirect(request):
    return redirect("user_manage")


@role_required("admin")
def user_edit(request, user_id):
    target = get_object_or_404(User.objects.select_related("profile"), pk=user_id)
    form = UserManagementForm(request.POST or None, instance=target)
    target_profile = Profile.objects.filter(user=target).first()
    form.fields["role"].initial = target_profile.role if target_profile else "student"
    if request.method == "POST" and form.is_valid():
        current_role = target_profile.role if target_profile else "student"
        new_role = form.cleaned_data["role"]
        removing_active_admin = (
            current_role == "admin"
            and target.is_active
            and (not form.cleaned_data["is_active"] or new_role != "admin")
        )
        if target.pk == request.user.pk and new_role != "admin":
            form.add_error("role", "You cannot change your own administrator role.")
        elif removing_active_admin:
            active_admins = Profile.objects.filter(role="admin", user__is_active=True).count()
            if active_admins <= 1:
                form.add_error(None, "The last active administrator cannot be deactivated or demoted.")
        if form.errors:
            return render(request, "portal/user_edit.html", {"form": form, "target": target})

        form.save()
        target_profile, _ = Profile.objects.get_or_create(user=target)
        target_profile.role = new_role
        target_profile.requested_role = ""
        target_profile.first_name = target.first_name
        target_profile.last_name = target.last_name
        target_profile.save(update_fields=["role", "requested_role", "first_name", "last_name"])

        if form.cleaned_data["new_password"]:
            target.set_password(form.cleaned_data["new_password"])
            target.save(update_fields=["password"])
            AuditLog.objects.create(
                user=request.user,
                action="RESET_USER_PASSWORD",
                details=f"Reset password for {target.username}",
            )
        if current_role != new_role:
            AuditLog.objects.create(
                user=request.user,
                action="UPDATE_USER_ROLE",
                details=f"Changed {target.username}'s role from {dict(Profile.ROLE_CHOICES).get(current_role)} to {dict(Profile.ROLE_CHOICES).get(new_role)}",
            )
        AuditLog.objects.create(user=request.user, action="EDIT_USER", details=f"Updated account: {target.username}")
        messages.success(request, f"Account for {target.username} was updated.")
        return redirect("user_manage")
    return render(request, "portal/user_edit.html", {"form": form, "target": target})


@role_required("admin")
@require_POST
def user_promote(request, user_id):
    target = get_object_or_404(User.objects.select_related("profile"), pk=user_id)
    profile, _ = Profile.objects.get_or_create(user=target)
    if profile.role == "admin":
        messages.info(request, f"{target.username} already has administrator access.")
    else:
        profile.role = "admin"
        profile.requested_role = ""
        profile.save(update_fields=["role", "requested_role"])
        AuditLog.objects.create(user=request.user, action="PROMOTE_USER", details=f"Promoted {target.username} to administrator")
        messages.success(request, f"{target.username} was promoted to administrator.")
    return redirect("user_manage")


@role_required("admin")
@require_POST
def user_demote(request, user_id):
    target = get_object_or_404(User.objects.select_related("profile"), pk=user_id)
    profile = getattr(target, "profile", None)
    if not profile or profile.role != "admin":
        messages.info(request, f"{target.username} does not have administrator access.")
    elif target.pk == request.user.pk:
        messages.error(request, "You cannot remove your own administrator access.")
    elif target.is_active and Profile.objects.filter(role="admin", user__is_active=True).count() <= 1:
        messages.error(request, "The last active administrator cannot be demoted.")
    else:
        profile.role = "student"
        profile.save(update_fields=["role"])
        AuditLog.objects.create(
            user=request.user,
            action="DEMOTE_USER",
            details=f"Removed administrator access from {target.username}; set role to student",
        )
        messages.success(request, f"{target.username} was demoted to student.")
    return redirect("user_manage")


@role_required("admin")
@require_POST
def user_role_request(request, user_id):
    profile = get_object_or_404(Profile.objects.select_related("user"), user_id=user_id)
    requested_role = profile.requested_role
    action = request.POST.get("role_action")
    if requested_role not in ("officer", "admin"):
        messages.info(request, f"{profile.user.username} has no pending role request.")
    elif action == "approve":
        profile.role = requested_role
        profile.requested_role = ""
        profile.save(update_fields=["role", "requested_role"])
        AuditLog.objects.create(
            user=request.user,
            action="APPROVE_ROLE_REQUEST",
            details=f"Approved {profile.user.username} for {profile.get_role_display()} access",
        )
        messages.success(request, f"{profile.user.username} was approved for {profile.get_role_display()} access.")
    elif action == "reject":
        profile.requested_role = ""
        profile.save(update_fields=["requested_role"])
        AuditLog.objects.create(
            user=request.user,
            action="REJECT_ROLE_REQUEST",
            details=f"Rejected {profile.user.username}'s {dict(Profile.ROLE_CHOICES).get(requested_role)} access request",
        )
        messages.success(request, f"{profile.user.username}'s role request was declined.")
    else:
        messages.error(request, "Choose whether to approve or decline the role request.")
    return redirect("user_manage")


@role_required("admin")
@require_POST
def user_delete(request, user_id):
    target = get_object_or_404(User.objects.select_related("profile"), pk=user_id)
    if target.pk == request.user.pk:
        messages.error(request, "You cannot delete your own account.")
        return redirect("user_manage")

    profile = Profile.objects.filter(user=target).first()
    if profile and profile.role == "admin":
        active_admins = Profile.objects.filter(role="admin", user__is_active=True).count()
        if target.is_active and active_admins <= 1:
            messages.error(request, "The last active administrator cannot be deleted.")
            return redirect("user_manage")

    if profile and (
        profile.attendance.exists()
        or profile.points.exists()
        or profile.fines.exists()
        or profile.clearance_records.exists()
    ):
        messages.error(request, "This account has attendance, fine, or clearance records and cannot be deleted. Deactivate it instead.")
        return redirect("user_manage")

    username = target.username
    try:
        with transaction.atomic():
            target.delete()
    except ProtectedError:
        messages.error(request, "This account is linked to portal records and cannot be deleted. Deactivate it instead.")
        return redirect("user_manage")

    AuditLog.objects.create(user=request.user, action="DELETE_USER", details=f"Deleted account: {username}")
    messages.success(request, f"Account for {username} was deleted.")
    return redirect("user_manage")

def sign_up(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            user = User.objects.create_user(
                username=cd["username"],
                password=cd["password"],
                first_name=cd["first_name"],
                last_name=cd["last_name"],
                email=cd["email"]
            )
            prog = cd["program"]
            col = prog.college
            requested_role = cd["requested_role"] if cd["requested_role"] in ("officer", "admin") else ""
            student_no = cd.get("student_no") or f"2026-{1000 + user.id:04d}"
            p = Profile.objects.create(
                user=user,
                role="student",
                requested_role=requested_role,
                student_no=student_no,
                first_name=cd["first_name"],
                middle_name=cd.get("middle_name", ""),
                last_name=cd["last_name"],
                college=col,
                program=prog,
                year_level=cd["year_level"]
            )
            for req in ClearanceRequirement.objects.all():
                ClearanceRecord.objects.get_or_create(student=p, requirement=req, defaults={"status": "pending"})
            AuditLog.objects.create(
                user=user,
                action="STUDENT_SIGNUP",
                details=f"New account registered: {user.username}; requested role: {requested_role or 'student'}",
            )
            if requested_role:
                messages.success(request, f"Account created. Your {p.get_requested_role_display()} access request is pending administrator approval.")
            else:
                messages.success(request, "Account created successfully! You can now log in.")
            return redirect("login")
    else:
        form = SignUpForm()
    return render(request, "registration/signup.html", {"form": form})

def system_showcase(request):
    events = Event.objects.all().order_by("event_date", "start_time")[:10]
    requirements = ClearanceRequirement.objects.all()
    recent_scans = AttendanceRecord.objects.select_related("student", "event").order_by("-scanned_at")[:10]
    demo_student = Profile.objects.filter(role="student").first()
    return render(request, "portal/showcase.html", {
        "events": events,
        "requirements": requirements,
        "recent_scans": recent_scans,
        "demo_student": demo_student,
    })
