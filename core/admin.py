from django.contrib import admin
from django.utils.safestring import mark_safe
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import (
    User, Department, Section, AttacheeProfile, 
    RosterConfiguration, GeneratedShift, Task, 
    WeeklyLog, FinalAssessment, ShiftAssignment
)

# ==========================================
# 1. AUTHENTICATION & USER MANAGEMENT
#    Admin/Supervisor SEPARATED from Attachees
# ==========================================

class StaffUserFilter(admin.SimpleListFilter):
    """
    Custom filter to separate Staff (Admin/Supervisor) from Attachees.
    """
    title = 'User Category'
    parameter_name = 'user_category'

    def lookups(self, request, model_admin):
        return [
            ('staff', '🔐 Staff (Admins & Supervisors)'),
            ('attachees', '🎓 Attachées'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'staff':
            return queryset.filter(role__in=['ADMIN', 'SUPERVISOR'])
        if self.value() == 'attachees':
            return queryset.filter(role='ATTACHEE')
        return queryset


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = (
        ('🔐 Account Credentials', {'fields': ('username', 'password')}),
        ('👤 Personal Details', {'fields': ('first_name', 'last_name', 'email')}),
        ('🎭 System Role Assignment', {'fields': ('role', 'is_staff', 'is_active', 'is_superuser')}),
        ('📅 Important Dates', {'fields': ('last_login', 'date_joined')}),
    )
    list_display = ['get_user_display', 'email', 'get_role_badge', 'get_category_label', 'is_active_badge']
    list_filter = [StaffUserFilter, 'role', 'is_staff', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['role', 'username']
    list_per_page = 25

    def get_user_display(self, obj):
        """Show username with an icon based on role."""
        icons = {
            'ADMIN': '🔴',
            'SUPERVISOR': '🔵',
            'ATTACHEE': '🟢',
        }
        icon = icons.get(obj.role, '⚪')
        full = f"{obj.first_name} {obj.last_name}".strip() or obj.username
        return format_html(
            '<span style="font-weight:700; color:#1a1a2e; font-size:13px;">{} {}</span>',
            icon, full
        )
    get_user_display.short_description = "User"

    def get_category_label(self, obj):
        """Show whether this is a Staff member or Attachee."""
        if obj.role in ['ADMIN', 'SUPERVISOR']:
            return mark_safe(
                '<span style="background:linear-gradient(135deg,#1e3a8a,#3b82f6);color:#fff;'
                'font-weight:700;font-size:11px;padding:4px 10px;border-radius:20px;'
                'letter-spacing:0.5px;text-transform:uppercase;box-shadow:0 2px 6px rgba(59,130,246,0.4);">'
                '🔐 STAFF</span>'
            )
        return mark_safe(
            '<span style="background:linear-gradient(135deg,#065f46,#10b981);color:#fff;'
            'font-weight:700;font-size:11px;padding:4px 10px;border-radius:20px;'
            'letter-spacing:0.5px;text-transform:uppercase;box-shadow:0 2px 6px rgba(16,185,129,0.4);">'
            '🎓 ATTACHÉE</span>'
        )
    get_category_label.short_description = "Category"

    def get_role_badge(self, obj):
        if not obj.role:
            return mark_safe(
                '<span style="background:#6b7280;color:#fff;font-size:11px;'
                'padding:4px 10px;border-radius:5px;font-weight:700;">NO ROLE</span>'
            )
        role_styles = {
            'ADMIN': 'background:linear-gradient(135deg,#7f1d1d,#dc2626);color:#fff;box-shadow:0 2px 6px rgba(220,38,38,0.5);',
            'SUPERVISOR': 'background:linear-gradient(135deg,#1e3a6b,#2563eb);color:#fff;box-shadow:0 2px 6px rgba(37,99,235,0.5);',
            'ATTACHEE': 'background:linear-gradient(135deg,#0f4c4c,#0d9488);color:#fff;box-shadow:0 2px 6px rgba(13,148,136,0.5);',
        }
        role_labels = {
            'ADMIN': '🔴 Administrator',
            'SUPERVISOR': '🔵 Supervisor',
            'ATTACHEE': '🟢 Attachée',
        }
        style = role_styles.get(obj.role.upper(), 'background:#6b7280;color:#fff;')
        label = role_labels.get(obj.role.upper(), obj.role.upper())
        return mark_safe(
            f'<span style="{style}font-weight:700;font-size:11px;'
            f'padding:5px 12px;border-radius:6px;text-transform:uppercase;'
            f'letter-spacing:0.5px;">{label}</span>'
        )

    def is_active_badge(self, obj):
        if obj.is_active:
            return mark_safe(
                '<span style="background:linear-gradient(135deg,#14532d,#22c55e);color:#fff;'
                'font-size:11px;padding:4px 10px;border-radius:5px;font-weight:700;'
                'box-shadow:0 2px 6px rgba(34,197,94,0.4);">✅ ACTIVE</span>'
            )
        return mark_safe(
            '<span style="background:linear-gradient(135deg,#7f1d1d,#dc2626);color:#fff;'
            'font-size:11px;padding:4px 10px;border-radius:5px;font-weight:700;'
            'box-shadow:0 2px 6px rgba(220,38,38,0.4);">❌ INACTIVE</span>'
        )

    get_role_badge.short_description = "System Role"
    is_active_badge.short_description = "Account Status"


# ==========================================
# 2. ORGANIZATIONAL STRUCTURE MANAGEMENT
# ==========================================
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'registered_attachees', 'verification_badge']
    list_filter = ['is_verified']
    search_fields = ['name']
    actions = ['verify_departments']

    def registered_attachees(self, obj):
        count = obj.attachees.count()
        if count == 0:
            return mark_safe('<span style="color:#6b7280;font-weight:600;">0 profiles</span>')
        return mark_safe(
            f'<span style="background:linear-gradient(135deg,#4c1d95,#7c3aed);color:#fff;'
            f'font-weight:700;font-size:11px;padding:5px 12px;border-radius:6px;'
            f'box-shadow:0 2px 6px rgba(124,58,237,0.4);">{count} Profiles</span>'
        )

    def verification_badge(self, obj):
        if obj.is_verified:
            return mark_safe(
                '<span style="background:linear-gradient(135deg,#14532d,#22c55e);color:#fff;'
                'font-weight:700;font-size:11px;padding:5px 12px;border-radius:6px;'
                'box-shadow:0 2px 6px rgba(34,197,94,0.4);">✅ VERIFIED</span>'
            )
        return mark_safe(
            '<span style="background:linear-gradient(135deg,#78350f,#ea580c);color:#fff;'
            'font-weight:700;font-size:11px;padding:5px 12px;border-radius:6px;'
            'box-shadow:0 2px 6px rgba(234,88,12,0.4);">⚠️ PENDING</span>'
        )

    registered_attachees.short_description = "Personnel Count"
    verification_badge.short_description = "Auth Status"

    def verify_departments(self, request, queryset):
        queryset.update(is_verified=True)
    verify_departments.short_description = "✅ Mark selected departments as Verified"


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'get_dept_badge']
    list_filter = ['department']
    search_fields = ['name', 'department__name']

    def get_dept_badge(self, obj):
        return mark_safe(
            f'<span style="background:linear-gradient(135deg,#1e3a8a,#3b82f6);color:#fff;'
            f'font-weight:700;font-size:11px;padding:4px 10px;border-radius:5px;">'
            f'🏢 {obj.department.name}</span>'
        )
    get_dept_badge.short_description = "Department"


# ==========================================
# 3. ATTACHEE PROFILE MANAGEMENT
# ==========================================
@admin.register(AttacheeProfile)
class AttacheeProfileAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'department', 'institution', 'get_status_badge', 'get_progress_display']
    list_filter = ['status', 'department', 'institution']
    search_fields = ['full_name', 'registration_number', 'institution']
    ordering = ['full_name']
    list_per_page = 25
    actions = ['mark_as_completed', 'cancel_registration']
    
    # Inject Custom CSS to beautify the Status and Multi-Select widgets
    class Media:
        css = {
            'all': ('core/css/admin_beautify.css',)
        }

    def get_status_badge(self, obj):
        # First, ensure status is current before rendering badge
        obj.update_status()
        
        styles = {
            'PENDING': ('background:linear-gradient(135deg,#92400e,#f59e0b);', '⏳'),
            'ACTIVE':  ('background:linear-gradient(135deg,#14532d,#22c55e);', '✅'),
            'COMPLETED': ('background:linear-gradient(135deg,#1e3a8a,#3b82f6);', '🎓'),
            'REJECTED': ('background:linear-gradient(135deg,#7f1d1d,#dc2626);', '❌'),
        }
        style, icon = styles.get(obj.status, ('background:#6b7280;', '❔'))
        label = obj.get_status_display()
        return mark_safe(
            f'<span style="{style}color:#fff;font-weight:700;font-size:11px;'
            f'padding:5px 12px;border-radius:6px;box-shadow:0 2px 6px rgba(0,0,0,0.2);'
            f'display:inline-block;min-width:100px;text-align:center;">'
            f'{icon} {label}</span>'
        )

    def get_progress_display(self, obj):
        if not obj.attachment_start_date or not obj.attachment_end_date:
            return "—"
        
        from django.utils import timezone
        today = timezone.now().date()
        total_days = (obj.attachment_end_date - obj.attachment_start_date).days
        elapsed_days = (today - obj.attachment_start_date).days
        
        if elapsed_days < 0: percent = 0
        elif elapsed_days > total_days: percent = 100
        else: percent = int((elapsed_days / total_days) * 100) if total_days > 0 else 0
        
        color = "#22c55e" if percent < 80 else "#3b82f6"
        if percent == 100: color = "#1e3a8a"
        
        return mark_safe(
            f'<div style="width:100px; background:#e2e8f0; border-radius:10px; height:8px; overflow:hidden; margin-top:6px;">'
            f'<div style="width:{percent}%; background:{color}; height:100%;"></div>'
            f'</div>'
            f'<span style="font-size:10px; font-weight:700; color:#64748b;">{percent}% Complete</span>'
        )

    get_status_badge.short_description = "Current Status"
    get_progress_display.short_description = "Completion"

    def mark_as_completed(self, request, queryset):
        queryset.update(status='COMPLETED')
    mark_as_completed.short_description = "🎓 Mark selected as Completed"

    def cancel_registration(self, request, queryset):
        queryset.update(status='PENDING')
    cancel_registration.short_description = "⏳ Cancel / Reset selected registrations"


# ==========================================
# 4. TASK/ASSIGNMENT DISTRIBUTION
# ==========================================
@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'department', 'target_work_mode', 'posted_at', 'deadline_badge']
    list_filter = ['department', 'target_work_mode', 'posted_at']
    search_fields = ['title', 'description']
    ordering = ['-posted_at']
    fields = ['department', 'supervisor', 'title', 'description', 'target_work_mode', 'deadline']

    def deadline_badge(self, obj):
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc) if obj.deadline.tzinfo else datetime.datetime.now()
        if obj.deadline < now:
            return mark_safe(
                '<span style="background:linear-gradient(135deg,#7f1d1d,#dc2626);color:#fff;'
                'font-weight:700;font-size:11px;padding:5px 14px;border-radius:6px;'
                'box-shadow:0 2px 8px rgba(220,38,38,0.5);">🚨 OVERDUE</span>'
            )
        return mark_safe(
            '<span style="background:linear-gradient(135deg,#155e75,#06b6d4);color:#fff;'
            'font-weight:700;font-size:11px;padding:5px 14px;border-radius:6px;'
            'box-shadow:0 2px 8px rgba(6,182,212,0.4);">📅 UPCOMING</span>'
        )

    deadline_badge.short_description = "Timeline Status"


# ==========================================
# 5. ALGORITHMIC ROSTER ENGINE INTERFACE
# ==========================================
@admin.register(RosterConfiguration)
class RosterConfigurationAdmin(admin.ModelAdmin):
    list_display = ('get_attachee_name', 'get_generation_mode_enhanced_badge', 'rotation_start_date')
    list_filter = ('generation_mode', 'rotation_start_date')
    # Use __in to look up values inside the ManyToMany relation
    search_fields = ('attachees__full_name',)
    actions = ['clear_shifts']

    fieldsets = (
        ('Engine Core Config', {
            'fields': ('attachees', 'generation_mode', 'rotation_start_date'),
            'description': 'Define base generation parameters for these attachee shift matrices.'
        }),
        ('Day Selection Match (Fixed Mode Only)', {
            'fields': ('constant_monday', 'constant_tuesday', 'constant_wednesday', 'constant_thursday', 'constant_friday'),
            'classes': ('collapse',),
        }),
    )

    # Allow cleaner styling for handling multiple ManyToMany elements in form selections
    filter_horizontal = ('attachees',)

    def get_attachee_name(self, obj):
        # Join all related attachee names together with commas
        names = ", ".join([a.full_name for a in obj.attachees.all()])
        if not names:
            return mark_safe('<span style="color:#6b7280; font-style:italic;">No attachees assigned</span>')
        
        return mark_safe(
            f'<span style="font-weight:700;color:#1a1a2e;font-size:13px;">👤 {names}</span>'
        )
    get_attachee_name.short_description = "Attachées"

    def get_generation_mode_enhanced_badge(self, obj):
        mode_configs = {
            'CONSTANT':   ('background:linear-gradient(135deg,#155e75,#0ea5e9);',  'fa-anchor',  'Fixed Days'),
            'INTERVAL_1': ('background:linear-gradient(135deg,#4c1d95,#7c3aed);',  'fa-walking', '1-Day Gap'),
            'INTERVAL_2': ('background:linear-gradient(135deg,#134e4a,#14b8a6);',  'fa-running', '2-Day Gap'),
            'INTERVAL_3': ('background:linear-gradient(135deg,#78350f,#f97316);',  'fa-bicycle', '3-Day Gap'),
            'INTERVAL_4': ('background:linear-gradient(135deg,#881337,#f43f5e);',  'fa-car',     '4-Day Gap'),
        }
        style, icon, label = mode_configs.get(obj.generation_mode, ('background:#6b7280;', 'fa-sync', obj.generation_mode))
        return mark_safe(
            f'<span style="{style}color:#fff;font-weight:700;font-size:11px;'
            f'padding:5px 14px;border-radius:6px;min-width:110px;display:inline-block;text-align:center;">'
            f'<i class="fas {icon} me-1"></i> {label}</span>'
        )
    get_generation_mode_enhanced_badge.short_description = "Generation Mode"

    def clear_shifts(self, request, queryset):
        for config in queryset:
            # Safely clear generated shifts for all attachees associated with this configuration rule
            for attachee in config.attachees.all():
                GeneratedShift.objects.filter(attachee=attachee).delete()
        self.message_user(request, "Selected rosters have been cleared/cancelled.")
    clear_shifts.short_description = "🗑️ Clear/Cancel Roster for selected"

@admin.register(GeneratedShift)
class GeneratedShiftAdmin(admin.ModelAdmin):
    list_display = ('attachee', 'date', 'day_name', 'get_work_mode_badge')
    list_filter = ('work_mode', 'day_name', 'date')
    search_fields = ('attachee__full_name',)
    ordering = ['-date']
    list_per_page = 30

    def get_work_mode_badge(self, obj):
        if obj.work_mode == 'PHYSICAL':
            return mark_safe(
                '<span style="background:linear-gradient(135deg,#7f1d1d,#e74c3c);color:#fff;'
                'font-weight:700;font-size:11px;padding:5px 12px;border-radius:6px;'
                'box-shadow:0 2px 6px rgba(231,76,60,0.4);">🏢 ON-SITE</span>'
            )
        return mark_safe(
            '<span style="background:linear-gradient(135deg,#1e3a6b,#3498db);color:#fff;'
            'font-weight:700;font-size:11px;padding:5px 12px;border-radius:6px;'
            'box-shadow:0 2px 6px rgba(52,152,219,0.4);">🏠 REMOTE</span>'
        )

    get_work_mode_badge.short_description = "Work Mode"


# ==========================================
# 6. LOGGING & ASSESSMENTS
#    APPROVED logs are highlighted with glow
# ==========================================

class ApprovedLogFilter(admin.SimpleListFilter):
    """Quick-access filter for approved weekly logs."""
    title = 'Approval State'
    parameter_name = 'approval_state'

    def lookups(self, request, model_admin):
        return [
            ('approved', '✅ Approved / Signed Off'),
            ('pending',  '⏳ Pending Review'),
            ('revision', '🔁 Needs Revision'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'approved':
            return queryset.filter(status='APPROVED')
        if self.value() == 'pending':
            return queryset.filter(status='PENDING')
        if self.value() == 'revision':
            return queryset.filter(status='REVISION')
        return queryset


@admin.register(WeeklyLog)
class WeeklyLogAdmin(admin.ModelAdmin):
    list_display = ('get_attachee_display', 'week_start_date', 'get_status_badge', 'updated_at')
    list_filter = (ApprovedLogFilter, 'status', 'week_start_date')
    search_fields = ('attachee__full_name',)
    ordering = ['-week_start_date']

    def get_attachee_display(self, obj):
        return mark_safe(
            f'<span style="font-weight:700;color:#1a1a2e;font-size:13px;">📋 {obj.attachee.full_name}</span>'
        )
    get_attachee_display.short_description = "Attachée"

    def get_status_badge(self, obj):
        if obj.status == 'APPROVED':
            # APPROVED: Green glow — maximum visibility
            return mark_safe(
                '<span style="'
                'background:linear-gradient(135deg,#065f46,#10b981);'
                'color:#ffffff;'
                'font-weight:800;'
                'font-size:12px;'
                'padding:6px 16px;'
                'border-radius:8px;'
                'box-shadow:0 0 14px rgba(16,185,129,0.7);'
                'text-transform:uppercase;'
                'letter-spacing:0.8px;'
                'border:2px solid #10b981;'
                'animation:none;'
                'display:inline-block;'
                '">✅ APPROVED</span>'
            )
        elif obj.status == 'REVISION':
            return mark_safe(
                '<span style="'
                'background:linear-gradient(135deg,#7f1d1d,#dc2626);'
                'color:#ffffff;'
                'font-weight:700;'
                'font-size:12px;'
                'padding:6px 16px;'
                'border-radius:8px;'
                'box-shadow:0 2px 8px rgba(220,38,38,0.5);'
                'text-transform:uppercase;'
                'letter-spacing:0.8px;'
                'display:inline-block;'
                '">🔁 NEEDS REVISION</span>'
            )
        # PENDING
        return mark_safe(
            '<span style="'
            'background:linear-gradient(135deg,#92400e,#f59e0b);'
            'color:#ffffff;'
            'font-weight:700;'
            'font-size:12px;'
            'padding:6px 16px;'
            'border-radius:8px;'
            'box-shadow:0 2px 8px rgba(245,158,11,0.4);'
            'text-transform:uppercase;'
            'letter-spacing:0.8px;'
            'display:inline-block;'
            '">⏳ PENDING</span>'
        )

    get_status_badge.short_description = "Review Status"


@admin.register(FinalAssessment)
class FinalAssessmentAdmin(admin.ModelAdmin):
    list_display = ('attachee', 'get_report_status_badge', 'final_grade', 'updated_at')
    list_filter = ('report_status', 'final_grade')
    search_fields = ('attachee__full_name',)

    def get_report_status_badge(self, obj):
        if obj.report_status == 'APPROVED':
            return mark_safe(
                '<span style="background:linear-gradient(135deg,#065f46,#10b981);color:#fff;'
                'font-weight:700;font-size:11px;padding:5px 14px;border-radius:6px;'
                'box-shadow:0 2px 8px rgba(16,185,129,0.5);">✅ CLEARED / PASSED</span>'
            )
        elif obj.report_status == 'REJECTED':
            return mark_safe(
                '<span style="background:linear-gradient(135deg,#7f1d1d,#dc2626);color:#fff;'
                'font-weight:700;font-size:11px;padding:5px 14px;border-radius:6px;'
                'box-shadow:0 2px 8px rgba(220,38,38,0.5);">❌ REJECTED</span>'
            )
        return mark_safe(
            '<span style="background:linear-gradient(135deg,#92400e,#f59e0b);color:#fff;'
            'font-weight:700;font-size:11px;padding:5px 14px;border-radius:6px;'
            'box-shadow:0 2px 8px rgba(245,158,11,0.4);">⏳ PENDING REVIEW</span>'
        )

    get_report_status_badge.short_description = "Assessment Status"


@admin.register(ShiftAssignment)
class ShiftAssignmentAdmin(admin.ModelAdmin):
    list_display = ('attachee', 'assigned_day', 'week_start_date', 'get_work_mode_badge')
    list_filter = ('work_mode', 'assigned_day', 'week_start_date')
    search_fields = ('attachee__full_name',)
    actions = ['cancel_assignment']

    def get_work_mode_badge(self, obj):
        if obj.work_mode == 'PHYSICAL':
            return mark_safe(
                '<span style="background:linear-gradient(135deg,#7f1d1d,#e74c3c);color:#fff;'
                'font-weight:700;font-size:11px;padding:5px 12px;border-radius:6px;'
                'box-shadow:0 2px 6px rgba(231,76,60,0.4);">🏢 ON-SITE</span>'
            )
        return mark_safe(
            '<span style="background:linear-gradient(135deg,#1e3a6b,#3498db);color:#fff;'
            'font-weight:700;font-size:11px;padding:5px 12px;border-radius:6px;'
            'box-shadow:0 2px 6px rgba(52,152,219,0.4);">🏠 REMOTE</span>'
        )
    get_work_mode_badge.short_description = "Assignment Mode"

    def cancel_assignment(self, request, queryset):
        queryset.delete()
    cancel_assignment.short_description = "🗑️ Cancel Selected Assignments"
