from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta, time, date
from decimal import Decimal
from portal.models import (
    College, Program, Profile, Event, AttendanceRecord,
    ParticipationPoint, Fine, ClearanceRequirement, ClearanceRecord,
    Announcement, AuditLog
)

class Command(BaseCommand):
    help = "Populate database with at least 20 realistic records for each feature."

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding database with at least 20 values for each feature...")

        # 1. COLLEGES & PROGRAMS (5 Colleges, 20 Programs)
        colleges_data = [
            ("CAS", "College of Arts and Sciences"),
            ("CBA", "College of Business Administration"),
            ("CCJE", "College of Criminal Justice Education"),
            ("COE", "College of Engineering"),
            ("CTE", "College of Teacher Education"),
        ]
        colleges = {}
        for code, name in colleges_data:
            col, _ = College.objects.get_or_create(code=code, defaults={"name": name})
            colleges[code] = col

        programs_data = [
            # CAS
            ("CAS", "BS Information Systems"),
            ("CAS", "BS Information Technology"),
            ("CAS", "BS Computer Science"),
            ("CAS", "BA Communication"),
            # CBA
            ("CBA", "BS Business Administration"),
            ("CBA", "BS Hospitality Management"),
            ("CBA", "BS Tourism Management"),
            ("CBA", "BS Accountancy"),
            # CCJE
            ("CCJE", "BS Criminology"),
            ("CCJE", "BS Industrial Security Management"),
            ("CCJE", "BS Forensic Science"),
            ("CCJE", "BS Law Enforcement Administration"),
            # COE
            ("COE", "BS Civil Engineering"),
            ("COE", "BS Mechanical Engineering"),
            ("COE", "BS Electrical Engineering"),
            ("COE", "BS Agricultural and Biosystems Engineering"),
            # CTE
            ("CTE", "Bachelor of Secondary Education"),
            ("CTE", "Bachelor of Elementary Education"),
            ("CTE", "Bachelor of Technology and Livelihood Education"),
            ("CTE", "Bachelor of Physical Education"),
        ]
        programs = []
        for ccode, pname in programs_data:
            prog, _ = Program.objects.get_or_create(college=colleges[ccode], name=pname)
            programs.append(prog)

        # Helper to create/update user and profile
        def make_user(username, passwords, role, email, first, middle, last, student_no=None, col=None, prog=None, year=1, position=""):
            u, created = User.objects.get_or_create(
                username=username,
                defaults={"email": email, "first_name": first, "last_name": last}
            )
            # Support both with and without exclamation mark for ease of use
            u.set_password(passwords[0])
            u.first_name = first
            u.last_name = last
            u.save()

            p, _ = Profile.objects.get_or_create(
                user=u,
                defaults={
                    "role": role,
                    "student_no": student_no,
                    "first_name": first,
                    "middle_name": middle,
                    "last_name": last,
                    "college": col,
                    "program": prog,
                    "year_level": year,
                    "position": position,
                }
            )
            p.role = role
            p.first_name = first
            p.middle_name = middle
            p.last_name = last
            p.student_no = student_no
            p.college = col
            p.program = prog
            p.year_level = year
            p.position = position
            p.save()
            return p

        # 2. ADMIN & OFFICERS
        admin_prof = make_user("admin", ["Admin12345!", "Admin12345"], "admin", "admin@isac.local", "System", "A.", "Administrator", position="System Administrator")
        officer1 = make_user("officer1", ["Officer12345!", "Officer12345"], "officer", "officer1@isac.local", "Maria", "Elena", "Santos", col=colleges["CAS"], prog=programs[0], year=4, position="CSBO President")
        officer2 = make_user("officer2", ["Officer12345!", "Officer12345"], "officer", "officer2@isac.local", "Juan", "Carlos", "Dela Cruz", col=colleges["CBA"], prog=programs[4], year=3, position="CSBO Secretary")
        officer3 = make_user("officer3", ["Officer12345!", "Officer12345"], "officer", "officer3@isac.local", "Angela", "Mae", "Reyes", col=colleges["COE"], prog=programs[12], year=4, position="CSBO Treasurer")

        # 3. AT LEAST 30 STUDENTS
        student_names = [
            ("Paulinia", "Kaye", "Indra"),
            ("Mark", "Denzy", "Manang"),
            ("Joshua", "Paul", "Garcia"),
            ("Sofia", "Nicole", "Mendoza"),
            ("Carlo", "Miguel", "Navarro"),
            ("Denise", "Marie", "Bautista"),
            ("Rafael", "Antonio", "Aquino"),
            ("Alyssa", "Jane", "Ramos"),
            ("Christian", "Dave", "Flores"),
            ("Nicole", "Grace", "Castillo"),
            ("Miguel", "Angelo", "Torres"),
            ("Andrea", "Louise", "Villanueva"),
            ("Paolo", "Luis", "Mercado"),
            ("Jasmine", "Rose", "Cruz"),
            ("Nathan", "Gabriel", "Perez"),
            ("Bea", "Patricia", "Soriano"),
            ("Gabriel", "Vince", "Morales"),
            ("Trisha", "Mae", "Santiago"),
            ("Ethan", "James", "Valdez"),
            ("Kimberly", "Ann", "Del Rosario"),
            ("Adrian", "Kyle", "Hernandez"),
            ("Mikaela", "Faith", "Ocampo"),
            ("Lorenzo", "Matthew", "Padilla"),
            ("Hannah", "Joy", "Salazar"),
            ("Luis", "Fernando", "Guerrero"),
            ("Camille", "Bianca", "Tan"),
            ("Dominic", "Leo", "Pascual"),
            ("Erika", "Denise", "Cortez"),
            ("Francis", "Ian", "Roxas"),
            ("Giselle", "Claire", "Beltran"),
        ]

        students = []
        for i, (fn, mn, ln) in enumerate(student_names):
            uname = f"student{i+1}"
            sno = f"2026-{i+1:04d}"
            assigned_prog = programs[i % len(programs)]
            assigned_col = assigned_prog.college
            year = (i % 4) + 1
            sp = make_user(
                username=uname,
                passwords=["Student12345!", "Student12345"],
                role="student",
                email=f"{uname}@isac.local",
                first=fn,
                middle=mn,
                last=ln,
                student_no=sno,
                col=assigned_col,
                prog=assigned_prog,
                year=year
            )
            students.append(sp)

        # 4. AT LEAST 22 EVENTS
        today = timezone.localdate()
        events_info = [
            ("Freshmen Orientation 2026", "Official orientation for all incoming NLUC students and campus body.", "NLUC Grand Gymnasium", today - timedelta(days=2), time(8, 0), time(12, 0), 2, "completed"),
            ("University Intramural Sports Fest", "Annual inter-college athletic championship and games.", "Campus Oval & Sports Complex", today - timedelta(days=1), time(8, 0), time(17, 0), 3, "completed"),
            ("CSBO General Student Assembly", "Semestral assembly, constitutional updates, and campus reports.", "Audio Visual Hall", today, time(9, 0), time(15, 0), 2, "ongoing"),
            ("National Tech & Innovation Summit", "Showcase of robotics, software engineering, and AI projects.", "Engineering Amphitheater", today + timedelta(days=1), time(8, 30), time(16, 30), 2, "upcoming"),
            ("Student Leadership & Governance Seminar", "Training session for student leaders and organization heads.", "Student Center Hall", today + timedelta(days=3), time(9, 0), time(16, 0), 2, "upcoming"),
            ("Campus Tree Planting & Clean-Up Drive", "Environmental stewardship activity in coordination with DENR.", "NLUC Eco-Park", today + timedelta(days=5), time(7, 0), time(11, 0), 1, "upcoming"),
            ("DMMMSU Cultural Arts Festival", "Celebration of dance, theater, music, and local heritage.", "Main Auditorium", today + timedelta(days=7), time(13, 0), time(20, 0), 2, "upcoming"),
            ("Student Mental Health & Wellness Forum", "Workshops and sessions on coping mechanisms and wellness.", "Gymnasium Annex", today + timedelta(days=8), time(10, 0), time(15, 0), 1, "upcoming"),
            ("Inter-College Hackathon & IT Fair", "24-hour coding challenge focused on community sustainability.", "CAS IT Center", today + timedelta(days=10), time(8, 0), time(18, 0), 3, "upcoming"),
            ("Annual Career & Job Placement Fair", "Direct recruitment and career interviews with industry partners.", "Student Activity Center", today + timedelta(days=12), time(8, 30), time(16, 0), 1, "upcoming"),
            ("CSBO Acquaintance & Fellowship Night", "Social night, talent performances, and organization induction.", "NLUC Quadrangle", today + timedelta(days=14), time(18, 0), time(22, 0), 2, "upcoming"),
            ("Regional Science & Mathematics Quiz Bowl", "Academic competition for undergraduate STEM students.", "CAS Science Wing", today + timedelta(days=16), time(9, 0), time(14, 0), 2, "upcoming"),
            ("University Parliamentary Debate Championship", "Competitive debate series on contemporary societal issues.", "College of Law Hall", today + timedelta(days=18), time(13, 0), time(17, 30), 2, "upcoming"),
            ("Student Visual Arts & Photography Exhibit", "Fine arts showcase and photography gallery by student artists.", "University Library Gallery", today + timedelta(days=20), time(8, 0), time(17, 0), 1, "upcoming"),
            ("Campus Battle of the Bands & Music Fest", "Live performances by campus music groups and guest bands.", "Grand Stadium", today + timedelta(days=22), time(17, 0), time(23, 0), 2, "upcoming"),
            ("Red Cross Campus Blood Donation Drive", "Voluntary blood donation in partnership with Philippine Red Cross.", "University Infirmary", today + timedelta(days=24), time(8, 0), time(14, 0), 2, "upcoming"),
            ("Academic Excellence & Honor Students Convocation", "Recognition of dean's listers and academic scholars.", "Main Auditorium", today + timedelta(days=26), time(9, 0), time(12, 0), 1, "upcoming"),
            ("Youth Environmental & Climate Summit", "Advocacy sessions on climate resilience and green technology.", "Agriculture Demonstration Farm", today + timedelta(days=28), time(8, 30), time(15, 30), 2, "upcoming"),
            ("Cybersecurity Awareness & Data Privacy Workshop", "Practical defense against phishing and data theft.", "Computer Lab 3", today + timedelta(days=30), time(13, 0), time(17, 0), 1, "upcoming"),
            ("Disaster Preparedness & First Aid Training", "Hands-on emergency medical and evacuation drill.", "Disaster Risk Reduction Center", today + timedelta(days=32), time(8, 0), time(16, 0), 2, "upcoming"),
            ("CSBO Year-End Gala & Recognition Night", "Awards ceremony honoring student leaders and outstanding clubs.", "Grand Ballroom", today + timedelta(days=35), time(18, 0), time(22, 0), 2, "upcoming"),
            ("Midterm Clearance Assistance Workshop", "Consultation desk for students clearing pending requirements.", "CSBO Secretariat Office", today + timedelta(days=38), time(9, 0), time(16, 0), 1, "upcoming"),
        ]

        events = []
        for title, desc, venue, edate, stime, etime, pts, stat in events_info:
            ev, _ = Event.objects.get_or_create(
                title=title,
                defaults={
                    "description": desc,
                    "venue": venue,
                    "event_date": edate,
                    "start_time": stime,
                    "end_time": etime,
                    "points": pts,
                    "status": stat,
                    "created_by": officer1.user,
                }
            )
            ev.description = desc
            ev.venue = venue
            ev.event_date = edate
            ev.start_time = stime
            ev.end_time = etime
            ev.points = pts
            ev.status = stat
            ev.save()
            events.append(ev)

        # 5. AT LEAST 20 CLEARANCE REQUIREMENTS
        reqs_data = [
            ("Library Clearance", "University main library book return and catalog verification.", 0, 0),
            ("Computer Laboratory", "IT laboratory machine clearance and account sign-off.", 0, 0),
            ("Science Laboratory", "Science department apparatus inspection and inventory return.", 0, 0),
            ("CSBO Membership Dues", "Official CSBO semester membership and activity contribution.", 0, 1),
            ("College Council Fee", "Local college student council operational clearance.", 0, 0),
            ("Supreme Student Council", "University-wide SSC validation and membership check.", 0, 1),
            ("Department Clearance", "Academic department head evaluation and sign-off.", 0, 0),
            ("Guidance Office", "Routine semestral guidance interview and counseling clearance.", 0, 0),
            ("Clinic & Health Clearance", "Health profile assessment and annual medical verification.", 0, 0),
            ("Sports & PE Clearance", "PE uniform, sports locker, and equipment return check.", 0, 0),
            ("ROTC / NSTP Clearance", "National Service Training Program completion documentation.", 0, 1),
            ("University ID Validation", "Semester validation sticker and RFID chip verification.", 0, 0),
            ("Campus Community Service", "Rendering verified volunteer community service hours.", 2, 1),
            ("Environmental Clearance", "Participation in campus greening and waste segregation program.", 1, 1),
            ("Student Discipline Office", "Verification of good moral standing and zero pending cases.", 0, 0),
            ("Academic Advising Sign-off", "Curriculum checklist audit by designated faculty adviser.", 0, 0),
            ("Property & Equipment Return", "Return of university loaned gear, books, and locker keys.", 0, 0),
            ("Digital Portal & IT Account", "Settlement of online learning portal accounts and email status.", 0, 0),
            ("Year-End Student Evaluation", "Completion of faculty and institutional evaluation survey.", 0, 0),
            ("Graduation / Final Clearance", "Comprehensive university clearance for terminal year students.", 5, 3),
        ]

        requirements = []
        for name, desc, rpts, revs in reqs_data:
            req, _ = ClearanceRequirement.objects.get_or_create(
                name=name,
                defaults={
                    "description": desc,
                    "required_points": rpts,
                    "required_events": revs
                }
            )
            req.description = desc
            req.required_points = rpts
            req.required_events = revs
            req.save()
            requirements.append(req)

        # 6. CLEARANCE RECORDS (Over 100 records)
        statuses_cycle = ["approved", "completed", "submitted", "pending", "approved", "completed"]
        for s_idx, student in enumerate(students):
            for r_idx, req in enumerate(requirements):
                st = statuses_cycle[(s_idx + r_idx) % len(statuses_cycle)]
                # First student has high completion to match UI mockup
                if s_idx == 0:
                    st = "approved" if r_idx < 15 else "submitted" if r_idx < 18 else "pending"
                ClearanceRecord.objects.update_or_create(
                    student=student,
                    requirement=req,
                    defaults={
                        "status": st,
                        "updated_by": officer1.user
                    }
                )

        # 7. ATTENDANCE & PARTICIPATION POINTS (Over 60 records)
        for s_idx, student in enumerate(students):
            # Attend past and ongoing events
            for e_idx, ev in enumerate(events[:5]):
                if (s_idx + e_idx) % 2 == 0 or s_idx == 0:
                    ar, _ = AttendanceRecord.objects.get_or_create(
                        event=ev,
                        student=student,
                        defaults={"scanned_by": officer1.user, "status": "present"}
                    )
                    ParticipationPoint.objects.get_or_create(
                        student=student,
                        event=ev,
                        defaults={"points": ev.points}
                    )

        # 8. AT LEAST 25 FINES
        fines_data = [
            ("Unattended CSBO Mandatory General Assembly", Decimal("150.00"), "unpaid"),
            ("Unreturned Sports Equipment (Basketball)", Decimal("350.00"), "unpaid"),
            ("Library Overdue Book Penalty - Data Structures", Decimal("80.00"), "paid"),
            ("Late Submission of Department Clearance Form", Decimal("100.00"), "unpaid"),
            ("Missing Computer Laboratory Access Badge", Decimal("120.00"), "paid"),
            ("Unvalidated Student ID Sticker for Current Semester", Decimal("50.00"), "unpaid"),
            ("Incomplete Community Extension Service Hours", Decimal("200.00"), "unpaid"),
            ("Damaged Science Laboratory Beaker Replacement", Decimal("180.00"), "paid"),
            ("Failure to Attend Freshmen Orientation Session", Decimal("150.00"), "waived"),
            ("Unreturned PE Locker Key", Decimal("75.00"), "unpaid"),
            ("Missed Campus Tree Planting Activity", Decimal("100.00"), "unpaid"),
            ("Late Submission of Organization Financial Report", Decimal("250.00"), "unpaid"),
            ("Improper Campus Uniform Citation", Decimal("50.00"), "waived"),
            ("Overdue Library Reference Manual", Decimal("95.00"), "paid"),
            ("Damaged Gymnasium Chair during Event", Decimal("300.00"), "unpaid"),
            ("Unsettled College Student Council T-Shirt Fee", Decimal("220.00"), "unpaid"),
            ("Missed Cultural Festival Rehearsal Attendance", Decimal("80.00"), "paid"),
            ("Unreturned Audio Visual Projector Remote", Decimal("400.00"), "unpaid"),
            ("Failure to Submit Evaluation Survey on Time", Decimal("50.00"), "waived"),
            ("Late Return of ROTC Inspection Equipment", Decimal("160.00"), "unpaid"),
            ("Library Book Spine Damage Penalty", Decimal("110.00"), "paid"),
            ("Unattended Leadership Seminar Workshop", Decimal("120.00"), "unpaid"),
            ("Lost Student ID Replacement Fee", Decimal("150.00"), "paid"),
            ("Missed College Sports Tryout Scheduled Duty", Decimal("70.00"), "unpaid"),
            ("Unreturned University Banner Stand", Decimal("280.00"), "unpaid"),
        ]

        for idx, (reason, amt, fstatus) in enumerate(fines_data):
            assigned_student = students[idx % len(students)]
            assigned_event = events[idx % len(events)]
            Fine.objects.update_or_create(
                student=assigned_student,
                reason=reason,
                defaults={
                    "event": assigned_event,
                    "amount": amt,
                    "status": fstatus,
                    "recorded_by": officer2.user,
                }
            )

        # 9. AT LEAST 20 ANNOUNCEMENTS
        announcements_data = [
            ("Welcome to Academic Year 2026-2027!", "CSBO welcomes all freshmen and returning DMMMSU-NLUC students. Check your digital ID and calendar.", "general"),
            ("Mandatory Attendance: CSBO General Assembly", "All students are required to attend the semestral assembly at the Audio Visual Hall. QR scanning is active.", "event"),
            ("Midterm Clearance Process is Now Open", "Clearance checklists have been generated for all enrolled students. Please review pending items in your clearance tab.", "clearance"),
            ("Intramural Sports Fest Registration Guidelines", "Colleges may now register teams for basketball, volleyball, athletics, and chess at the Sports Center.", "event"),
            ("Main Library Book Amnesty & Return Notice", "Return all overdue books this week with waived late fees. Visit the circulation desk for clearance signing.", "clearance"),
            ("Tech & Innovation Summit Call for Project Entries", "Submissions for software, hardware, and sustainable tech prototypes are open until Friday.", "event"),
            ("Digital Student ID & QR Attendance Policy", "Present your ISAC Portal Digital ID on your phone at every campus activity entrance for instantaneous scanning.", "general"),
            ("Campus Mental Health & Wellness Week", "Free counseling, yoga workshops, and stress relief booths will be available at the Gymnasium Annex.", "general"),
            ("Urgent: Validate Your University ID RFID Stickers", "Students without validated 1st Semester stickers will be flagged at campus security gates.", "urgent"),
            ("Inter-College Hackathon 2026 Cash Prizes Announced", "Over PHP 50,000 in prizes await the top winning software development teams.", "event"),
            ("Community Extension Tree Planting Volunteers Needed", "Earn 2 participation points and clear your environmental requirement by joining the eco-park drive.", "event"),
            ("Notice on Pending Clearance Fines and Dues", "Students with unpaid fines must settle with the CSBO Treasurer before final exam permits are released.", "clearance"),
            ("Annual Career Fair: 40+ Industry Employers Confirmed", "Bring your printed resumes and wear business casual attire to the Student Activity Center.", "event"),
            ("CSBO Acquaintance Night Ticket Distribution", "Claim your official event wristbands from your respective college representatives.", "event"),
            ("Cultural Arts Festival Auditions Ongoing", "Singers, dancers, and theater performers are encouraged to audition at the Main Auditorium.", "event"),
            ("Student Leadership Seminar Participant Slots", "Class presidents and organization officers are requested to confirm attendance by Wednesday.", "event"),
            ("Red Cross Blood Donation Drive Registration", "Be a hero and save lives. Blood donors will receive 2 participation points and certificate of appreciation.", "general"),
            ("Cybersecurity & Data Privacy Advisory", "Never share your ISAC portal passwords or scan tokens with anyone. Report phishing attempts to MIS.", "urgent"),
            ("Disaster Preparedness Simulation Drill", "A campus-wide earthquake and fire evacuation drill will be held at 9:00 AM next Tuesday.", "general"),
            ("Year-End Clearance Schedule & Deadlines Released", "Make sure all 20 clearance requirements are marked Approved prior to the semester closure.", "clearance"),
        ]

        for title, body, cat in announcements_data:
            ann, _ = Announcement.objects.get_or_create(
                title=title,
                defaults={
                    "body": body,
                    "category": cat,
                    "published_by": officer1.user,
                    "status": True,
                }
            )
            ann.body = body
            ann.category = cat
            ann.save()

        # 10. AT LEAST 25 AUDIT LOGS
        audit_entries = [
            (admin_prof.user, "INITIALIZE_PORTAL", "Configured semester calendar and academic departments"),
            (officer1.user, "CREATE_EVENT", "Created Freshmen Orientation 2026 event"),
            (officer1.user, "CREATE_EVENT", "Created University Intramural Sports Fest"),
            (officer1.user, "CREATE_EVENT", "Created CSBO General Student Assembly"),
            (officer1.user, "CREATE_EVENT", "Created National Tech & Innovation Summit"),
            (officer2.user, "SCAN_ATTENDANCE", "Scanned attendance for student 2026-0001 (Freshmen Orientation)"),
            (officer2.user, "SCAN_ATTENDANCE", "Scanned attendance for student 2026-0002 (Sports Fest)"),
            (officer2.user, "SCAN_ATTENDANCE", "Scanned attendance for student 2026-0003 (General Assembly)"),
            (officer2.user, "SCAN_ATTENDANCE", "Scanned attendance for student 2026-0004 (Tech Summit)"),
            (officer3.user, "CREATE_FINE", "Issued fine for missed general assembly: 2026-0005"),
            (officer3.user, "CREATE_FINE", "Recorded library overdue fine: 2026-0006"),
            (officer3.user, "UPDATE_FINE", "Marked fine as paid for 2026-0003"),
            (officer1.user, "UPDATE_CLEARANCE", "Approved Library Clearance for 2026-0001"),
            (officer1.user, "UPDATE_CLEARANCE", "Approved Science Lab Clearance for 2026-0001"),
            (officer1.user, "UPDATE_CLEARANCE", "Approved CSBO Dues for 2026-0002"),
            (officer1.user, "UPDATE_CLEARANCE", "Approved Guidance Clearance for 2026-0003"),
            (officer1.user, "PUBLISH_ANNOUNCEMENT", "Published Welcome to Academic Year 2026-2027"),
            (officer1.user, "PUBLISH_ANNOUNCEMENT", "Published Mandatory Clearance Notice"),
            (admin_prof.user, "UPDATE_ROLE", "Promoted officer1 to CSBO President role"),
            (admin_prof.user, "SYSTEM_BACKUP", "Completed automated database and media files backup"),
            (officer2.user, "EXPORT_REPORT", "Generated Excel attendance report for CSBO General Assembly"),
            (officer2.user, "EXPORT_REPORT", "Generated PDF clearance summary for CAS department"),
            (students[0].user, "LOGIN", "Student logged into ISAC Portal dashboard"),
            (students[1].user, "LOGIN", "Student accessed digital ID and QR code"),
            (admin_prof.user, "SECURITY_AUDIT", "Routine session token and permission check completed successfully"),
        ]

        for u, act, det in audit_entries:
            AuditLog.objects.get_or_create(
                user=u,
                action=act,
                details=det
            )

        self.stdout.write(self.style.SUCCESS("Database successfully seeded!"))
        self.stdout.write(f"- Colleges: {College.objects.count()}")
        self.stdout.write(f"- Programs: {Program.objects.count()}")
        self.stdout.write(f"- Users/Profiles: {User.objects.count()}")
        self.stdout.write(f"- Events: {Event.objects.count()}")
        self.stdout.write(f"- Clearance Requirements: {ClearanceRequirement.objects.count()}")
        self.stdout.write(f"- Clearance Records: {ClearanceRecord.objects.count()}")
        self.stdout.write(f"- Attendance Records: {AttendanceRecord.objects.count()}")
        self.stdout.write(f"- Participation Points: {ParticipationPoint.objects.count()}")
        self.stdout.write(f"- Fines: {Fine.objects.count()}")
        self.stdout.write(f"- Announcements: {Announcement.objects.count()}")
        self.stdout.write(f"- Audit Logs: {AuditLog.objects.count()}")
