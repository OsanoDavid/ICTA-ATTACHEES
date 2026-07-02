from django.core.management.base import BaseCommand
from core.models import Department, Section

class Command(BaseCommand):
    help = 'Pre-loads official ICT Authority Departments and Sections'

    def handle(self, *args, **kwargs):
        # Define default verified departments and their sections
        data = {
            "Networks & Digital Infrastructure": [
                "National Optic Fibre Backbone (NOFBI)", 
                "Data Centres / Cloud Infrastructure", 
                "Network Operations Centre (NOC)"
            ],
            "Software Technologies & AI": [
                "Government Applications Development", 
                "Database Administration & Integrations", 
                "System Quality Assurance"
            ],
            "Information Security (Cybersecurity)": [
                "Security Operations Centre (SOC)", 
                "Threat Detection & Incident Response", 
                "Standards & Compliance"
            ],
            "Corporate Communication": [
                "Public Relations & Media Relations",
                "Digital Media & Content Creation",
                "Internal Communications"
            ]
            
        }

        for dept_name, sections in data.items():
            dept, created = Department.objects.get_or_create(name=dept_name, is_verified=True)
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created Department: {dept_name}"))
            
            for sec_name in sections:
                sec, sec_created = Section.objects.get_or_create(department=dept, name=sec_name)
                if sec_created:
                    self.stdout.write(self.style.SUCCESS(f"  -> Created Section: {sec_name}"))
                    
        self.stdout.write(self.style.SUCCESS("Database seeding completed successfully!"))