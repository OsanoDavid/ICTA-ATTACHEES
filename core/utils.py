import datetime
from django.db import transaction
from core.models import AttacheeProfile, ShiftAssignment

def generate_weekly_shifts(department_id, week_start_date):
    """
    Fetches active attachées in a specific department, splits them by gender,
    and assigns them equally from Monday to Friday (excluding weekends).
    """
    # 1. Fetch active attachées mapped strictly to this single department
    attachees = AttacheeProfile.objects.filter(department_id=department_id, status='ACTIVE')
    
    # Isolate into two lists to enforce gender balancing
    males = list(attachees.filter(gender='M'))
    females = list(attachees.filter(gender='F'))
    
    days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    
    # Initialize dictionary buckets for each working day
    daily_allocations = {day: [] for day in days_of_week}
    
    # 2. Distribute males evenly across the 5 days
    day_idx = 0
    while males:
        current_day = days_of_week[day_idx % 5]
        daily_allocations[current_day].append(males.pop(0))
        day_idx += 1
        
    # 3. Distribute females evenly across the 5 days
    day_idx = 0
    while females:
        current_day = days_of_week[day_idx % 5]
        daily_allocations[current_day].append(females.pop(0))
        day_idx += 1

    # 4. Save allocations to the database cleanly inside a transaction block
    with transaction.atomic():
        # Clear any existing shifts for this department for the specific week to avoid overlaps
        ShiftAssignment.objects.filter(
            attachee__department_id=department_id, 
            week_start_date=week_start_date
        ).delete()
        
        # Write new assignments
        for day, students in daily_allocations.items():
            for student in students:
                ShiftAssignment.objects.create(
                    attachee=student,
                    assigned_day=day,
                    week_start_date=week_start_date
                )