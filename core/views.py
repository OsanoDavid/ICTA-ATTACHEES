import datetime
from datetime import timedelta
from django.http import JsonResponse
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse_lazy
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetView

from .models import (
    AttacheeProfile, 
    ShiftAssignment, 
    Task, 
    Department, 
    FinalAssessment, 
    GeneratedShift, 
    WeeklyLog,
    RosterConfiguration
)
from .forms import WeeklyLogForm, AttacheeRegistrationForm
from .utils import generate_weekly_shifts


User = get_user_model()


# =========================================================================
# CORE CORE/AUTHENTICATION VIEWS
# =========================================================================


def home_view(request):
    current_year = timezone.now().year
    
    # Calculate real-time metrics for the landing page statistics
    # current_cohort_count: Students placed this year
    # Now includes APPROVED (verified but not started) and ACTIVE
    current_cohort_count = AttacheeProfile.objects.filter(
        status__in=['APPROVED', 'ACTIVE'], 
        created_at__year=current_year
    ).count()
    
    # total_placed_count: All students ever placed or currently active
    total_placed_count = AttacheeProfile.objects.filter(
        status__in=['APPROVED', 'ACTIVE', 'COMPLETED']
    ).count()
    
    # department_count: Total verified ICTA departments
    department_count = Department.objects.filter(is_verified=True).count()
    
    context = {
        'current_cohort_count_display': current_cohort_count,
        'total_placed_count_display': total_placed_count,
        'department_count_display': department_count,
        'current_year': current_year,
    }
    return render(request, 'core/home.html', context)


def login_view(request):
    if request.method == 'POST':
        user_in = request.POST.get('username')
        pass_in = request.POST.get('password')
        
        # Check if user_in is a registration number
        username_to_auth = user_in
        try:
            profile = AttacheeProfile.objects.get(registration_number__iexact=user_in)
            username_to_auth = profile.user.username
        except AttacheeProfile.DoesNotExist:
            pass

        user = authenticate(request, username=username_to_auth, password=pass_in)

        
        if user is not None:
            # Django superusers must always be able to access the Django admin,
            # even if their optional portal role was set incorrectly.
            if user.is_superuser or user.role == 'ADMIN':
                login(request, user)
                messages.success(request, f"Admin portal accessed securely as {user.username}.")
                return redirect('/admin/')

            # Enforce business rule: Check if an ATTACHEE is still PENDING verification
            if user.role == 'ATTACHEE':
                try:
                    profile = AttacheeProfile.objects.get(user=user)
                    if profile.status == 'PENDING':
                        messages.error(request, 'Your application is pending supervisor verification. Please check back later.')
                        return render(request, 'core/login.html')
                except AttacheeProfile.DoesNotExist:
                    messages.error(request, 'No associate profiles are assigned to this account structure.')
                    return render(request, 'core/login.html')

            # Complete standard authentication process
            login(request, user)
            
            # Route based explicitly on role with customized success messages
            if user.role == 'SUPERVISOR':
                messages.success(request, f"Welcome back, {user.username}! Supervisor login successful.")
                return redirect('supervisor_dashboard')
                
            elif user.role == 'ATTACHEE':
                messages.success(request, "Login successful! Welcome to your Attachée Dashboard.")
                return redirect('attachee_dashboard')
                
        else:
            messages.error(request, 'Invalid username or password credentials.')
            
    return render(request, 'core/login.html')


def logout_view(request):
    logout(request)
    return redirect('login_view')


def register_view(request):
    # Fetch only verified departments for the initial dropdown select choices
    departments = Department.objects.filter(is_verified=True)
    
    if request.method == 'POST':
        form = AttacheeRegistrationForm(request.POST, departments=departments)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Registration successful! Wait for supervisor verification to log in.')
                return redirect('login_view')
            except Department.DoesNotExist:
                messages.error(request, 'The selected department could not be found. Please choose a valid department.')
            except Exception as e:
                messages.error(request, f'An unexpected error occurred during registration: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below and resubmit your registration.')
    else:
        form = AttacheeRegistrationForm(departments=departments)

    return render(request, 'core/register.html', {
        'departments': departments,
        'form': form,
    })

@login_required
def admin_pending_count_view(request):
    """
    An API endpoint for the admin sidebar to fetch the number of pending attachees.
    """
    if not request.user.is_staff:
        return JsonResponse({'error': 'Not authorized'}, status=403)
    count = AttacheeProfile.objects.filter(status='PENDING').count()
    return JsonResponse({'pending_count': count})


class CustomPasswordResetView(PasswordResetView):
    template_name = 'registration/password_reset_form.html'

    def post(self, request, *args, **kwargs):
        email = request.POST.get('email', '').strip()
        user = User.objects.filter(email__iexact=email).first()
        
        if not user:
            messages.error(request, f"No registered account was found with the email address: {email}")
            return render(request, self.template_name, {'email': email})
        
        # Generate a strong temporary password
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        temp_password = ''.join(secrets.choice(alphabet) for i in range(12))
        
        # Set the new password
        user.set_password(temp_password)
        user.save()
        
        # Send the email
        try:
            subject = "Your New ICTA Portal Password"
            message = f"Hello {user.username},\n\nYour password has been reset as requested.\n\n" \
                      f"New Strong Password: {temp_password}\n\n" \
                      f"Please log in and change this password immediately from your profile.\n\n" \
                      f"Best Regards,\nICTA Technical Support"
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            messages.success(request, f"A new strong password has been generated and dispatched to {email}. Check your inbox.")
            return redirect('login_view')
        except Exception as e:
            messages.error(request, f"Email delivery failed: {str(e)}. Please contact support.")
            return render(request, self.template_name, {'email': email})


@login_required
def change_password_view(request):
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not request.user.check_password(old_password):
            messages.error(request, "The old password you entered is incorrect.")
        elif new_password != confirm_password:
            messages.error(request, "The new password and confirmation do not match.")
        elif len(new_password) < 8:
            messages.error(request, "Your new password must be at least 8 characters long.")
        else:
            request.user.set_password(new_password)
            request.user.save()
            # Update session to prevent logout
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, request.user)
            messages.success(request, "Your password has been updated successfully in our secure database.")
            return redirect('attachee_dashboard' if request.user.role == 'ATTACHEE' else 'supervisor_dashboard')
            
    return render(request, 'core/change_password.html')


# =========================================================================
# ATTACHÉE DASHBOARD & ACTIONS
# =========================================================================

@login_required
def attachee_dashboard(request):
    profile = getattr(request.user, 'attachee_profile', None)
    if profile:
        profile.update_status()
    
    # Calculate Attachment Progress
    progress_percent = 0
    if profile and profile.attachment_start_date and profile.attachment_end_date:
        today = timezone.now().date()
        total_days = (profile.attachment_end_date - profile.attachment_start_date).days
        elapsed_days = (today - profile.attachment_start_date).days
        
        if elapsed_days < 0: progress_percent = 0
        elif elapsed_days > total_days: progress_percent = 100
        else: progress_percent = int((elapsed_days / total_days) * 100) if total_days > 0 else 0

    # Handle Navigation Offsets
    try:
        week_offset = int(request.GET.get('week_offset', 0))
    except ValueError:
        week_offset = 0

    today = timezone.now().date()
    now_timestamp = timezone.now()
    current_day_str = today.strftime('%A')
    
    # Calculate target week boundaries
    target_monday = (today - timedelta(days=today.weekday())) + timedelta(weeks=week_offset)
    target_friday = target_monday + timedelta(days=4)
    
    week_modes = {'Monday': 'REMOTE', 'Tuesday': 'REMOTE', 'Wednesday': 'REMOTE', 'Thursday': 'REMOTE', 'Friday': 'REMOTE'}
    has_schedule = False
    is_on_physical_shift = False

    if profile:
        # 1. Fetch Manual Shifts (ShiftAssignment) - Highest Priority
        manual_shifts = ShiftAssignment.objects.filter(
            attachee=profile,
            week_start_date=target_monday
        )
        
        if manual_shifts.exists():
            has_schedule = True
            # Build the map from existing manual assignments
            for shift in manual_shifts:
                week_modes[shift.assigned_day] = shift.work_mode
                if shift.assigned_day == current_day_str and shift.work_mode == 'PHYSICAL' and week_offset == 0:
                    is_on_physical_shift = True
        else:
            # 2. Fallback to Algorithmic Shifts (GeneratedShift)
            # Standardize Monday/Friday range for algorithmic search
            weekly_shifts = GeneratedShift.objects.filter(
                attachee=profile,
                date__range=[target_monday, target_friday]
            )

            if weekly_shifts.exists():
                has_schedule = True
                for shift in weekly_shifts:
                    # day_name should match 'Monday', 'Tuesday', etc.
                    week_modes[shift.day_name] = shift.work_mode
                    if shift.date == today and shift.work_mode == 'PHYSICAL' and week_offset == 0:
                        is_on_physical_shift = True
        
        # FINAL GUARD: Ensure all weekdays are present in week_modes (default to REMOTE if missing)
        # This prevents the 'showing nothing' issue if some days are missing in the DB
        standard_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        for day in standard_days:
            if day not in week_modes:
                week_modes[day] = 'REMOTE'

    # Process tasks to accurately inject calculation attributes
    raw_tasks = Task.objects.filter(department=profile.department).order_by('-posted_at') if profile else []
    processed_tasks = []
    
    for task in raw_tasks:
        is_overdue = False
        overdue_days = 0
        
        if task.deadline:
            if task.deadline < now_timestamp:
                is_overdue = True
                delta = now_timestamp - task.deadline
                overdue_days = delta.days

        # Attach calculated parameters directly to a dictionary wrapper
        processed_tasks.append({
            'deadline': task.deadline,
            'title': task.title,
            'description': task.description,
            'is_overdue': is_overdue,
            'overdue_days': overdue_days,
            'target_work_mode_display': task.get_target_work_mode_display()
        })

    context = {
        'profile': profile,
        'progress_percent': progress_percent,
        'has_schedule': has_schedule,
        'is_on_physical_shift': is_on_physical_shift,
        'week_modes': week_modes,
        'active_tasks': processed_tasks,
        'current_weekday': current_day_str,
        'week_start': target_monday,
        'week_end': target_friday,
        'prev_offset': week_offset - 1,
        'next_offset': week_offset + 1,
        'week_offset': week_offset,
    }

    # If the request is an AJAX/Fetch request, render ONLY the partial matrix container
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'core/matrix_card.html', context)
        
    return render(request, 'core/attachee_dashboard.html', context)


@login_required
def submit_weekly_log(request):
    if request.user.role != 'ATTACHEE':
        return redirect('login_view')
        
    profile = get_object_or_404(AttacheeProfile, user=request.user)
    
    # Calculate current week's Monday
    today_date = timezone.now().date()
    week_start = today_date - timedelta(days=today_date.weekday())
    
    # Get existing log for this week or create an unsaved placeholder instance
    weekly_log, created = WeeklyLog.objects.get_or_create(
        attachee=profile,
        week_start_date=week_start,
        defaults={'status': 'PENDING'}
    )
    
    # Block updates if the supervisor has already signed off / approved it
    if weekly_log.status == 'APPROVED':
        messages.warning(request, "This week's logbook record has already been approved and signed off. Changes are locked.")
        return redirect('attachee_dashboard')

    if request.method == 'POST':
        form = WeeklyLogForm(request.POST, instance=weekly_log)
        if form.is_valid():
            log_instance = form.save(commit=False)
            log_instance.status = 'PENDING'  # Reset to pending on revision save
            log_instance.save()
            messages.success(request, "Your daily logbook entry updates have been securely compiled and saved.")
            return redirect('attachee_dashboard')
    else:
        form = WeeklyLogForm(instance=weekly_log)
        
    context = {
        'form': form,
        'weekly_log': weekly_log,
        'week_start': week_start,
        'profile': profile,
    }
    return render(request, 'core/submit_weekly_log.html', context)


@login_required
def logbook_history(request):
    if request.user.role != 'ATTACHEE':
        return redirect('login_view')
        
    profile = get_object_or_404(AttacheeProfile, user=request.user)
    
    # Retrieve all historical log entries for this attachée
    all_logs = WeeklyLog.objects.filter(attachee=profile).order_by('-week_start_date')
    
    # Calculate some quick metrics for the student's motivation
    total_weeks = all_logs.count()
    approved_weeks = all_logs.filter(status='APPROVED').count()
    pending_weeks = all_logs.filter(status='PENDING').count()
    revision_weeks = all_logs.filter(status='REVISION').count()
    
    context = {
        'profile': profile,
        'all_logs': all_logs,
        'total_weeks': total_weeks,
        'approved_weeks': approved_weeks,
        'pending_weeks': pending_weeks,
        'revision_weeks': revision_weeks,
    }
    return render(request, 'core/logbook_history.html', context)


@login_required
def upload_final_report(request):
    if request.user.role != 'ATTACHEE':
        return redirect('login_view')
        
    profile = get_object_or_404(AttacheeProfile, user=request.user)
    assessment, created = FinalAssessment.objects.get_or_create(attachee=profile)
    
    if request.method == 'POST':
        if not request.FILES.get('report_file'):
            messages.error(request, "No file selected. Please choose a PDF and ensure your form has enctype='multipart/form-data'.")
            return redirect('upload_final_report')
            
        uploaded_file = request.FILES['report_file']
        
        # Simple extension check guardrail
        if not uploaded_file.name.endswith('.pdf'):
            messages.error(request, "Invalid file format. Please upload your final report as a verified PDF document.")
            return redirect('upload_final_report')
            
        assessment.report_file = uploaded_file
        assessment.report_uploaded_at = timezone.now()
        assessment.report_status = 'PENDING'
        assessment.save()
        
        messages.success(request, "Your industrial attachment final report has been uploaded successfully for evaluation.")
        return redirect('attachee_dashboard')
        
    return render(request, 'core/upload_final_report.html', {'assessment': assessment})


# =========================================================================
# SUPERVISOR ACTIONS & DASHBOARD VIEWS
# =========================================================================

@login_required
def supervisor_dashboard(request):
    if request.user.role != 'SUPERVISOR':
        return redirect('login_view')
        
    dept = request.user.department
    if not dept:
        return render(request, 'core/supervisor_dashboard.html', {'no_department': True})
        
    # Trigger status updates for all active/approved attachees in this department
    for p in AttacheeProfile.objects.filter(status__in=['APPROVED', 'ACTIVE'], department=dept):
        p.update_status()

    pending_profiles = AttacheeProfile.objects.filter(status='PENDING', department=dept)
    pending_assessments = FinalAssessment.objects.filter(report_status='PENDING', attachee__department=dept).select_related('attachee')
    
    # Fetch logs submitted by attachées that need signature verification
    submitted_logs = WeeklyLog.objects.filter(status='PENDING', attachee__department=dept).select_related('attachee')
    
    today_date = datetime.date.today()
    week_start = today_date - timedelta(days=today_date.weekday())
    active_shifts = ShiftAssignment.objects.filter(week_start_date=week_start, attachee__department=dept)
    
    current_weekday = today_date.strftime('%A')
    on_site_today_count = ShiftAssignment.objects.filter(
        week_start_date=week_start, 
        assigned_day=current_weekday,
        attachee__department=dept
    ).count()
    total_managed_count = AttacheeProfile.objects.filter(status__in=['APPROVED', 'ACTIVE'], department=dept).count()

    context = {
        'no_department': False,
        'department_name': dept.name,
        'pending_profiles': pending_profiles,
        'pending_assessments': pending_assessments,
        'submitted_logs': submitted_logs,
        'active_shifts': active_shifts,
        'on_site_today_count': on_site_today_count,
        'total_managed_count': total_managed_count,
        'current_weekday': current_weekday,
    }
    return render(request, 'core/supervisor_dashboard.html', context)


@login_required
def approve_attachee(request, profile_id):
    if request.user.role != 'SUPERVISOR':
        return redirect('login_view')
        
    dept = request.user.department
    if not dept:
        messages.error(request, "You have not been assigned to a department.")
        return redirect('supervisor_dashboard')
        
    profile = get_object_or_404(AttacheeProfile, id=profile_id)
    if profile.department != dept:
        messages.error(request, "Access Denied: This attachée belongs to another department.")
        return redirect('supervisor_dashboard')
        
    profile.status = 'APPROVED'
    profile.update_status() # Immediately check if they should be ACTIVE today
    profile.save()
    
    messages.success(request, f"Account for {profile.full_name} has been verified and approved successfully.")
    return redirect('supervisor_dashboard')


@login_required
def reject_attachee(request, profile_id):
    if request.user.role != 'SUPERVISOR':
        return redirect('login_view')
        
    dept = request.user.department
    if not dept:
        messages.error(request, "You have not been assigned to a department.")
        return redirect('supervisor_dashboard')
        
    profile = get_object_or_404(AttacheeProfile, id=profile_id)
    if profile.department != dept:
        messages.error(request, "Access Denied: This attachée belongs to another department.")
        return redirect('supervisor_dashboard')
        
    profile.status = 'REJECTED'
    profile.save()
    
    messages.warning(request, f"Application profile for {profile.full_name} has been rejected.")
    return redirect('supervisor_dashboard')


@login_required
def trigger_roster_engine(request):
    if request.user.role != 'SUPERVISOR':
        return redirect('login_view')
        
    dept = request.user.department
    if not dept:
        messages.error(request, "You have not been assigned to a department.")
        return redirect('supervisor_dashboard')
        
    today_date = datetime.date.today()
    week_start = today_date - timedelta(days=today_date.weekday())
    
    try:
        if not dept.is_verified:
            raise Exception("Your department is not verified.")
            
        with transaction.atomic():
            # Automated logic matches ACTIVE students to the weekday matrix of this department only
            generate_weekly_shifts(department_id=dept.id, week_start_date=week_start)
                
        messages.success(request, f"Roster engine executed! Aligned rotations for {dept.name} department for week of {week_start}.")
    except Exception as e:
        messages.error(request, f"Engine execution halted: {str(e)}")
        
    return redirect('supervisor_dashboard')


@login_required
def review_logbook(request, log_id):
    if request.user.role != 'SUPERVISOR':
        return redirect('login_view')
        
    dept = request.user.department
    if not dept:
        messages.error(request, "You have not been assigned to a department.")
        return redirect('supervisor_dashboard')
        
    weekly_log = get_object_or_404(WeeklyLog, id=log_id)
    if weekly_log.attachee.department != dept:
        messages.error(request, "Access Denied: This log belongs to an attachée in another department.")
        return redirect('supervisor_dashboard')
        
    form_error = None

    if request.method == 'POST':
        action = request.POST.get('action', '').strip()
        remarks = request.POST.get('supervisor_remarks', '').strip()

        if action == 'APPROVE':
            weekly_log.supervisor_remarks = remarks
            weekly_log.status = 'APPROVED'
            weekly_log.save()
            messages.success(request, f"Logbook for {weekly_log.attachee.full_name} (week of {weekly_log.week_start_date}) signed off successfully.")
            return redirect('supervisor_dashboard')
        elif action == 'REVISION':
            weekly_log.supervisor_remarks = remarks
            weekly_log.status = 'REVISION'
            weekly_log.save()
            messages.warning(request, f"Logbook sent back to {weekly_log.attachee.full_name} for revision.")
            return redirect('supervisor_dashboard')
        else:
            form_error = "Please click 'Digital Sign-Off / Approve' or 'Send Back for Revision'."

    context = {
        'weekly_log': weekly_log,
        'form_error': form_error,
    }
    return render(request, 'core/review_logbook.html', context)


@login_required
def evaluate_final_submission(request, assessment_id):
    if request.user.role != 'SUPERVISOR':
        return redirect('login_view')
        
    dept = request.user.department
    if not dept:
        messages.error(request, "You have not been assigned to a department.")
        return redirect('supervisor_dashboard')
        
    assessment = get_object_or_404(FinalAssessment, id=assessment_id)
    if assessment.attachee.department != dept:
        messages.error(request, "Access Denied: This submission belongs to an attachée in another department.")
        return redirect('supervisor_dashboard')
        
    attachee_user = assessment.attachee.user  # Fetching the associated User object for the email address
    
    if request.method == 'POST':
        action = request.POST.get('action')
        remarks = request.POST.get('examiner_remarks', '').strip()
        grade = request.POST.get('final_grade', '').strip()
        
        subject = None
        email_body = None
        
        assessment.examiner_remarks = remarks
        assessment.final_grade = grade
        
        if request.FILES.get('evaluation_file'):
            assessment.evaluation_file = request.FILES['evaluation_file']
            assessment.evaluation_uploaded_at = timezone.now()
            
        # Determine status changes and construct structural emails
        if action == 'APPROVE':
            assessment.report_status = 'APPROVED'
            subject = "Attachment Clearance Status: APPROVED & CERTIFIED"
            email_body = f"Hello {assessment.attachee.full_name},\n\n" \
                         f"Congratulations! Your attachment final report has been officially reviewed and approved.\n" \
                         f"Final Letter Grade Assigned: {grade}\n" \
                         f"Supervisor Remarks: {remarks}\n\n" \
                         f"Log into the ICTA portal to review your signed evaluation parameters sheet.\n\n" \
                         f"Best Regards,\nICTA Academic Review Desk"
            messages.success(request, f"Final clearances signed off for {assessment.attachee.full_name}.")
            
        elif action == 'REJECT':
            assessment.report_status = 'REJECTED'
            subject = "Attachment Clearance Status: REVISION REQUIRED"
            email_body = f"Hello {assessment.attachee.full_name},\n\n" \
                         f"Your final attachment report submission requires modifications and has been sent back.\n" \
                         f"Supervisor Feedback: {remarks}\n\n" \
                         f"Please correct your document format and re-upload it via the Student Submission Desk immediately.\n\n" \
                         f"Best Regards,\nICTA Academic Review Desk"
            messages.warning(request, f"Final report rejected for {assessment.attachee.full_name}. Student notified for re-upload.")
        else:
            messages.error(request, "Evaluation failed: No valid action (Approve/Reject) was detected.")
            return redirect('evaluate_final_submission', assessment_id=assessment_id)
            
        assessment.save()
        
        if subject and email_body:
            # Fire off the automated email notification dispatch safely
            try:
                send_mail(
                    subject=subject,
                    message=email_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[attachee_user.email],
                    fail_silently=True,
                )
            except Exception as e:
                # Prevent system crash if email infrastructure drops out
                messages.error(request, f"Notification failed to send, but record updated: {str(e)}")
            
        return redirect('supervisor_dashboard')
        
    return render(request, 'core/evaluate_final_submission.html', {'assessment': assessment})


@login_required
def assign_and_reschedule_roster(request, attachee_id):
    if request.user.role != 'SUPERVISOR':
        messages.error(request, "Access Denied: Supervisor clearance required.")
        return redirect('supervisor_dashboard')

    dept = request.user.department
    if not dept:
        messages.error(request, "You have not been assigned to a department.")
        return redirect('supervisor_dashboard')

    attachee = get_object_or_404(AttacheeProfile, id=attachee_id)
    if attachee.department != dept:
        messages.error(request, "Access Denied: This attachée belongs to another department.")
        return redirect('supervisor_dashboard')
    
    # Calculate target week commencing date (Standardized Monday)
    today = timezone.now().date()
    today_str = today.strftime('%Y-%m-%d')

    if request.method == 'POST':
        # 0. Retrieve anchor date for rotation logic
        anchor_date_str = request.POST.get('anchor_date')
        anchor_date = datetime.datetime.strptime(anchor_date_str, '%Y-%m-%d').date()
        # Pivot the start week to the Monday of THAT anchor date
        start_monday = anchor_date - timedelta(days=anchor_date.weekday())
        
        # 1. Retrieve pattern
        schedule_pattern = request.POST.get('schedule_pattern') # e.g., 'CUSTOM' or 'ALTERNATING'
        physical_days = []

        if schedule_pattern == 'ALTERNATING':
            physical_days = ['Monday', 'Wednesday', 'Friday']
        elif schedule_pattern == 'FULL_WEEK':
            physical_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        elif schedule_pattern.startswith('INTERVAL_'):
            # Interval Logic (Calculated for the current single week)
            gap = int(schedule_pattern.split('_')[1])
            all_weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
            # We assume the pattern resets each Monday for manual assignment
            # (If it needs to roll across weeks, RosterConfiguration is used instead)
            for i, day in enumerate(all_weekdays):
                if i % (gap + 1) == 0:
                    physical_days.append(day)
        else:
            physical_days = request.POST.getlist('physical_days')

        if not physical_days and schedule_pattern == 'CUSTOM':
            messages.error(request, "Please select at least one physical day layout pattern.")
            return redirect('assign_and_reschedule_roster', attachee_id=attachee.id)

        all_weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        
        with transaction.atomic():
            for week_idx in range(12):
                target_mon = start_monday + timedelta(weeks=week_idx)
                
                # Wipe records for the target week to ensure update override
                ShiftAssignment.objects.filter(attachee=attachee, week_start_date=target_mon).delete()
                
                for i, day in enumerate(all_weekdays):
                    # Calculate total workdays elapsed since anchor_date (ignoring weekends)
                    current_date = target_mon + timedelta(days=i)
                    
                    # If the current_date is before our chosen anchor, force REMOTE
                    if current_date < anchor_date:
                        mode = 'REMOTE'
                    else:
                        # Determine pattern for this specific date
                        days_this_week = []
                        if schedule_pattern == 'ALTERNATING':
                            mode = 'PHYSICAL' if day in ['Monday', 'Wednesday', 'Friday'] else 'REMOTE'
                        elif schedule_pattern == 'FULL_WEEK':
                            mode = 'PHYSICAL'
                        elif schedule_pattern.startswith('INTERVAL_'):
                            gap = int(schedule_pattern.split('_')[1])
                            
                            # Calculate effective workdays between anchor and current
                            # We use a loop for precision across weekends
                            workdays_count = 0
                            temp_date = anchor_date
                            while temp_date < current_date:
                                if temp_date.strftime('%A') not in ['Saturday', 'Sunday']:
                                    workdays_count += 1
                                temp_date += timedelta(days=1)
                            
                            if workdays_count % (gap + 1) == 0:
                                mode = 'PHYSICAL'
                            else:
                                mode = 'REMOTE'
                        else:
                            mode = 'PHYSICAL' if day in physical_days else 'REMOTE'

                    ShiftAssignment.objects.create(
                        attachee=attachee,
                        assigned_day=day,
                        week_start_date=target_mon,
                        work_mode=mode
                    )

        messages.success(request, f"Operational rotation schedule for {attachee.full_name} projected for 12 weeks successfully.")
        return redirect('supervisor_dashboard')

    # Standard current Monday for existing shifts view
    current_monday_display = today - timedelta(days=today.weekday())
    existing_shifts = ShiftAssignment.objects.filter(attachee=attachee, week_start_date=current_monday_display)
    current_physical_days = [s.assigned_day for s in existing_shifts if s.work_mode == 'PHYSICAL']

    context = {
        'attachee': attachee,
        'current_monday': current_monday_display,
        'current_physical_days': current_physical_days,
        'today_str': today_str,
    }
    return render(request, 'core/assign_roster_form.html', context)

@login_required
def clear_all_shifts(request, attachee_id):
    if request.user.role != 'SUPERVISOR':
        return redirect('login_view')
    
    attachee = get_object_or_404(AttacheeProfile, id=attachee_id)
    # Complete wipe of all future/current rotation data for this attachee
    ShiftAssignment.objects.filter(attachee=attachee, week_start_date__gte=timezone.now().date() - timedelta(days=7)).delete()
    
    messages.warning(request, f"Rotation matrix cleared and reset to total remote for {attachee.full_name}.")
    return redirect('assign_and_reschedule_roster', attachee_id=attachee.id)


@login_required
def bulk_assign_roster(request):
    """
    Allows supervisors to assign shift patterns to multiple attachées at once.
    Scoped to the supervisor's own department only — no cross-department access.
    """
    if request.user.role != 'SUPERVISOR':
        messages.error(request, "Access Denied: Supervisor clearance required.")
        return redirect('supervisor_dashboard')

    dept = request.user.department
    if not dept:
        messages.error(request, "You have not been assigned to a department yet.")
        return redirect('supervisor_dashboard')

    today = timezone.now().date()
    today_str = today.strftime('%Y-%m-%d')
    current_monday = today - timedelta(days=today.weekday())

    # Supervisor is locked to their own department — no department filter dropdown
    selected_dept_id = str(dept.id)

    # Load all active attachees in the supervisor's department
    attachees = AttacheeProfile.objects.filter(
        department=dept,
        status__in=['APPROVED', 'ACTIVE']
    ).distinct().order_by('full_name')

    if request.method == 'POST':
        attachee_ids = request.POST.getlist('attachee_ids')
        anchor_date_str = request.POST.get('anchor_date')
        anchor_date = datetime.datetime.strptime(anchor_date_str, '%Y-%m-%d').date()
        start_monday = anchor_date - timedelta(days=anchor_date.weekday())

        physical_days = request.POST.getlist('physical_days')
        schedule_pattern = request.POST.get('schedule_pattern')

        if not attachee_ids:
            messages.error(request, "Please select at least one attachée.")
        else:
            if schedule_pattern == 'ALTERNATING':
                physical_days = ['Monday', 'Wednesday', 'Friday']
            elif schedule_pattern == 'FULL_WEEK':
                physical_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

            all_weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

            with transaction.atomic():
                for aid in attachee_ids:
                    profile = get_object_or_404(AttacheeProfile, id=aid)
                    # Security: Prevent cross-department tampering via form injection
                    if profile.department != dept:
                        messages.error(request, f"Access Denied: {profile.full_name} is not in your department.")
                        return redirect('bulk_assign_roster')

                    for week_idx in range(12):
                        target_mon = start_monday + timedelta(weeks=week_idx)
                        ShiftAssignment.objects.filter(attachee=profile, week_start_date=target_mon).delete()

                        for i, day in enumerate(all_weekdays):
                            current_date = target_mon + timedelta(days=i)

                            if current_date < anchor_date:
                                mode = 'REMOTE'
                            else:
                                if schedule_pattern == 'ALTERNATING':
                                    mode = 'PHYSICAL' if day in ['Monday', 'Wednesday', 'Friday'] else 'REMOTE'
                                elif schedule_pattern == 'FULL_WEEK':
                                    mode = 'PHYSICAL'
                                elif schedule_pattern.startswith('INTERVAL_'):
                                    gap = int(schedule_pattern.split('_')[1])
                                    workdays_count = 0
                                    temp_date = anchor_date
                                    while temp_date < current_date:
                                        if temp_date.strftime('%A') not in ['Saturday', 'Sunday']:
                                            workdays_count += 1
                                        temp_date += timedelta(days=1)
                                    mode = 'PHYSICAL' if workdays_count % (gap + 1) == 0 else 'REMOTE'
                                else:
                                    mode = 'PHYSICAL' if day in physical_days else 'REMOTE'

                            ShiftAssignment.objects.create(
                                attachee=profile,
                                assigned_day=day,
                                week_start_date=target_mon,
                                work_mode=mode
                            )

            messages.success(request, f"Batch rotations for {len(attachee_ids)} attachées projected for 12 weeks successfully.")
            return redirect('supervisor_dashboard')

    context = {
        'department_name': dept.name,
        'attachees': attachees,
        'selected_dept_id': selected_dept_id,
        'current_monday': current_monday,
        'today_str': today_str,
    }
    return render(request, 'core/bulk_assign_roster.html', context)


@login_required
def view_final_reports(request):
    if request.user.role != 'SUPERVISOR':
        return redirect('login_view')

    dept = request.user.department
    if not dept:
        messages.error(request, "You have not been assigned to a department yet.")
        return redirect('supervisor_dashboard')

    # Scope final reports to this supervisor's department only
    assessments = FinalAssessment.objects.filter(
        report_file__isnull=False,
        attachee__department=dept
    ).select_related('attachee')

    context = {
        'assessments': assessments,
        'department_name': dept.name,
    }
    return render(request, 'core/view_final_reports.html', context)


@login_required
def all_attachees_view(request):
    if request.user.role != 'SUPERVISOR':
        return redirect('login_view')

    dept = request.user.department
    if not dept:
        messages.error(request, "You have not been assigned to a department yet.")
        return redirect('supervisor_dashboard')

    # Fetch all attachees in this department with their weekly logs prefetched
    from django.db.models import Prefetch
    attachees = AttacheeProfile.objects.filter(
        department=dept
    ).select_related('department', 'user').prefetch_related(
        Prefetch('weekly_logs', queryset=WeeklyLog.objects.order_by('-week_start_date'))
    ).order_by('full_name')

    context = {
        'attachees': attachees,
        'department_name': dept.name,
    }
    return render(request, 'core/all_attachees.html', context)
