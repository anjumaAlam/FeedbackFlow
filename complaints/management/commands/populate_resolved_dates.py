from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import models
from django.db.models import Q
from complaints.models import Complaint


class Command(BaseCommand):
    help = 'Populate resolved_at dates and location for resolved complaints that are missing them'

    def handle(self, *args, **options):
        # Get all resolved complaints with null resolved_at
        resolved_no_date = Complaint.objects.filter(status='Resolved', resolved_at__isnull=True)
        count_no_date = resolved_no_date.count()

        if count_no_date > 0:
            self.stdout.write(f'Found {count_no_date} resolved complaints missing resolved_at date')
            # Set resolved_at to updated_at if available, otherwise to now
            for complaint in resolved_no_date:
                complaint.resolved_at = complaint.updated_at or timezone.now()
                complaint.save(update_fields=['resolved_at'])
            self.stdout.write(self.style.SUCCESS(f'✓ Updated {count_no_date} complaints with resolved_at'))
        else:
            self.stdout.write('All resolved complaints already have resolved_at dates')

        # Get all resolved complaints with null/empty location
        resolved_no_location = Complaint.objects.filter(status='Resolved').filter(
            Q(location__isnull=True) | Q(location='')
        )
        count_no_location = resolved_no_location.count()

        if count_no_location > 0:
            self.stdout.write(f'Found {count_no_location} resolved complaints missing location')
            for complaint in resolved_no_location:
                complaint.location = 'General Campus'
                complaint.save(update_fields=['location'])
            self.stdout.write(self.style.SUCCESS(f'✓ Updated {count_no_location} complaints with default location'))
        else:
            self.stdout.write('All resolved complaints already have locations')

        self.stdout.write(self.style.SUCCESS('\n✓ Done! Refresh the page to see changes.'))
