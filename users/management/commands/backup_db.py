"""
NFR 4.2 / OR 2.8: Daily Database Backup Management Command

Usage:
    python manage.py backup_db          # Creates a timestamped backup
    python manage.py backup_db --clean  # Backup and remove backups older than 30 days

Can be scheduled via cron job or Windows Task Scheduler for daily execution.
"""

import shutil
import os
from datetime import datetime, timedelta
from pathlib import Path

from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Create a backup of the SQLite database (NFR 4.2 / OR 2.8)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Remove backups older than 30 days after creating new backup',
        )
        parser.add_argument(
            '--retention-days',
            type=int,
            default=30,
            help='Number of days to retain backups (default: 30)',
        )

    def handle(self, *args, **options):
        # Source database
        db_path = settings.DATABASES['default']['NAME']
        if not os.path.exists(db_path):
            self.stderr.write(self.style.ERROR(f'Database file not found: {db_path}'))
            return

        # Backup directory
        backup_dir = Path(settings.BASE_DIR) / 'backups'
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Create timestamped backup
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'feedbackflow_backup_{timestamp}.sqlite3'
        backup_path = backup_dir / backup_filename

        try:
            shutil.copy2(db_path, backup_path)
            file_size = os.path.getsize(backup_path)
            size_mb = file_size / (1024 * 1024)
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Backup created successfully: {backup_filename} ({size_mb:.2f} MB)'
                )
            )

            # Log the backup
            import logging
            logger = logging.getLogger('feedbackflow')
            logger.info(f'Database backup created: {backup_filename} ({size_mb:.2f} MB)')

        except Exception as e:
            self.stderr.write(self.style.ERROR(f'❌ Backup failed: {e}'))
            return

        # Clean old backups if requested
        if options['clean']:
            retention_days = options['retention_days']
            cutoff = datetime.now() - timedelta(days=retention_days)
            removed_count = 0

            for f in backup_dir.glob('feedbackflow_backup_*.sqlite3'):
                if f == backup_path:
                    continue
                # Parse timestamp from filename
                try:
                    fname = f.stem  # feedbackflow_backup_20260514_123456
                    ts_str = fname.replace('feedbackflow_backup_', '')
                    file_date = datetime.strptime(ts_str, '%Y%m%d_%H%M%S')
                    if file_date < cutoff:
                        f.unlink()
                        removed_count += 1
                except (ValueError, OSError):
                    continue

            if removed_count > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f'🗑️ Removed {removed_count} backup(s) older than {retention_days} days'
                    )
                )
            else:
                self.stdout.write('No old backups to clean.')

        # Show all current backups
        backups = sorted(backup_dir.glob('feedbackflow_backup_*.sqlite3'), reverse=True)
        self.stdout.write(f'\n📁 Total backups: {len(backups)}')
        for b in backups[:5]:
            size = os.path.getsize(b) / (1024 * 1024)
            self.stdout.write(f'   • {b.name} ({size:.2f} MB)')
        if len(backups) > 5:
            self.stdout.write(f'   ... and {len(backups) - 5} more')
