from django.core.management.base import BaseCommand
from core.models import Department, Section

class Command(BaseCommand):
    help = 'Pre-loads official ICT Authority Departments and Sections'

    def handle(self, *args, **kwargs):
        # Define default verified departments and default sections (if any)
        data = {
            "Standards & Accreditation Dept.": [],
            "Standards Dev. & Enforcement Dept.": [],
            "Programs Dept.": [],
            "E. Government Dept.": [],
            "Infrastructure Dept.": [],
            "IT Security Dept.": [],
            "Technical Support Dept.": [],
            "Innovation & Incubation Dept.": [],
            "Partnerships & Resource Mobilization Dept.": [],
            "Capacity Development Dept.": [],
            "ICT Enterprise Dept.": [],
            "Compliance (Quality Assurance & Risk Mgt. Dept.)": [],
            "Corporate Research, Strategy & Planning Dept.": [],
            "Knowledge Mngt. Unit": [],
            "HR & Administration Dept.": [],
            "Finance Dept.": [],
            "ICT Unit": [],
            "Supply Chain Dept.": [],
            "Procurement & Disposal Div.": [],
            "Store & Inventory Unit": [],
            "Communication Dept.": []
        }

        # Helper mapping for renaming old departments to preserve existing relations
        rename_map = {
            "Networks & Digital Infrastructure": "Infrastructure Dept.",
            "Software Technologies & AI": "Innovation & Incubation Dept.",
            "Information Security (Cybersecurity)": "IT Security Dept.",
            "Corporate Communication": "Communication Dept.",
            "Test Dept": "Programs Dept."
        }

        # First, apply renames to prevent duplicate key errors and preserve relationships
        for old_name, new_name in rename_map.items():
            try:
                dept = Department.objects.get(name=old_name)
                # Check if the target new name already exists
                if Department.objects.filter(name=new_name).exists():
                    # If target exists, merge profiles/supervisors and delete old
                    target_dept = Department.objects.get(name=new_name)
                    # Update AttacheeProfile
                    from core.models import AttacheeProfile
                    AttacheeProfile.objects.filter(department=dept).update(department=target_dept)
                    # Update User (Supervisor department)
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    User.objects.filter(department=dept).update(department=target_dept)
                    dept.delete()
                    self.stdout.write(self.style.WARNING(f"Merged and deleted old department '{old_name}' into '{new_name}'"))
                else:
                    dept.name = new_name
                    dept.save()
                    self.stdout.write(self.style.SUCCESS(f"Renamed department '{old_name}' to '{new_name}'"))
            except Department.DoesNotExist:
                pass

        # Now, create or get the rest
        for dept_name, sections in data.items():
            dept, created = Department.objects.get_or_create(name=dept_name, is_verified=True)
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created Department: {dept_name}"))
            
            for sec_name in sections:
                sec, sec_created = Section.objects.get_or_create(department=dept, name=sec_name)
                if sec_created:
                    self.stdout.write(self.style.SUCCESS(f"  -> Created Section: {sec_name}"))
                    
        self.stdout.write(self.style.SUCCESS("Database seeding completed successfully!"))