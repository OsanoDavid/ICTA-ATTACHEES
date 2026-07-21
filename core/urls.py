from django.urls import path
from . import views

urlpatterns = [
    # Core/Auth URLs
    path('', views.home_view, name='home'),
    path('login/', views.login_view, name='login_view'),
    path('logout/', views.logout_view, name='logout_view'),
    path('register/', views.register_view, name='register_view'),

    # Password Reset
    path('password-reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),

    # Attachee Dashboard & Actions
    path('dashboard/', views.attachee_dashboard, name='attachee_dashboard'),
    path('submit-log/', views.submit_weekly_log, name='submit_weekly_log'),
    path('logbook-history/', views.logbook_history, name='logbook_history'),
    path('upload-report/', views.upload_final_report, name='upload_final_report'),

    # Supervisor Dashboard & Actions
    path('supervisor/', views.supervisor_dashboard, name='supervisor_dashboard'),
    path('approve/<int:profile_id>/', views.approve_attachee, name='approve_attachee'),
    path('reject/<int:profile_id>/', views.reject_attachee, name='reject_attachee'),
    path('review-logbook/<int:log_id>/', views.review_logbook, name='review_logbook'),
    path('evaluate-submission/<int:assessment_id>/', views.evaluate_final_submission, name='evaluate_final_submission'),
    path('final-reports/', views.view_final_reports, name='view_final_reports'),
    path('all-attachees/', views.all_attachees_view, name='all_attachees'),
    path('change-password/', views.change_password_view, name='change_password'),

    # HR Dashboard & Actions
    path('hr/', views.hr_dashboard, name='hr_dashboard'),
    path('hr/approve/<int:profile_id>/', views.hr_approve_attachee, name='hr_approve_attachee'),
    path('hr/reject/<int:profile_id>/', views.hr_reject_attachee, name='hr_reject_attachee'),
    path('hr/add-attachee/', views.hr_add_attachee, name='hr_add_attachee'),
    path('hr/add-supervisor/', views.hr_add_supervisor, name='hr_add_supervisor'),
    path('hr/edit-attachee/<int:profile_id>/', views.hr_edit_attachee, name='hr_edit_attachee'),
    path('hr/delete-attachee/<int:profile_id>/', views.hr_delete_attachee, name='hr_delete_attachee'),
    path('hr/issue-certificate/<int:profile_id>/', views.hr_issue_certificate, name='hr_issue_certificate'),
    path('hr/export-certified/', views.hr_export_certified_excel, name='hr_export_certified_excel'),
    path('hr/registration-config/', views.hr_save_registration_config, name='hr_save_registration_config'),
    path('attachee/certificate/', views.attachee_certificate, name='attachee_certificate'),
    path('attachee/certificate/pdf/', views.certificate_pdf, name='certificate_pdf'),

    # Roster Management
    path('roster/trigger/', views.trigger_roster_engine, name='trigger_roster_engine'),
    path('roster/assign/<int:attachee_id>/', views.assign_and_reschedule_roster, name='assign_and_reschedule_roster'),
    path('roster/bulk-assign/', views.bulk_assign_roster, name='bulk_assign_roster'),
    path('roster/clear/<int:attachee_id>/', views.clear_all_shifts, name='clear_all_shifts'),

    # API endpoint for admin badge
    path('api/admin/pending-count/', views.admin_pending_count_view, name='admin_pending_count'),
]