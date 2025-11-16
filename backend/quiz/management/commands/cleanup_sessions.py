from django.core.management.base import BaseCommand
from quiz.services.session_management_service import SessionManagementService


class Command(BaseCommand):
    help = 'Oturum veritabanını temizle ve optimize et'

    def add_arguments(self, parser):
        parser.add_argument(
            '--abandoned',
            action='store_true',
            help='Sadece terk edilmiş oturumları temizle'
        )
        parser.add_argument(
            '--expired',
            action='store_true',
            help='Sadece süresi dolmuş oturumları temizle'
        )
        parser.add_argument(
            '--inactive-users',
            action='store_true',
            help='Sadece inaktif kullanıcıları temizle'
        )
        parser.add_argument(
            '--optimize',
            action='store_true',
            help='Veritabanı optimizasyonu yap'
        )
        parser.add_argument(
            '--full',
            action='store_true',
            help='Tam temizleme ve optimizasyon yap'
        )

    def handle(self, *args, **options):
        if options['full']:
            self.stdout.write('TAM TEMIZLIK BASLATILIYOR...')
            results = SessionManagementService.run_full_cleanup()

            self.stdout.write('\nTEMIZLIK SONUCLARI:')
            self.stdout.write(f"  Terk edilmis oturumlar: {results['abandoned_sessions']}")
            self.stdout.write(f"  Suresi dolmus oturumlar: {results['expired_sessions']}")
            self.stdout.write(f"  Inaktif kullanicilar: {results['inactive_users']}")
            self.stdout.write(f"  Zaman: {results['timestamp']}")

        else:
            if options['abandoned']:
                count = SessionManagementService.cleanup_abandoned_sessions()
                self.stdout.write(f'{count} terk edilmis oturum temizlendi')

            if options['expired']:
                count = SessionManagementService.cleanup_expired_sessions()
                self.stdout.write(f'{count} suresi dolmus oturum temizlendi')

            if options['inactive_users']:
                count = SessionManagementService.cleanup_inactive_users()
                self.stdout.write(f'{count} inaktif kullanici temizlendi')

            if options['optimize']:
                success = SessionManagementService.optimize_database()
                if success:
                    self.stdout.write('Veritabani optimizasyonu tamamlandi')
                else:
                    self.stdout.write('Veritabani optimizasyonu basarisiz')

        # Saglik raporu
        health_report = SessionManagementService.get_session_health_report()
        self.stdout.write('\nOTURUM SAGLIGI:')
        self.stdout.write(f"  Durum: {health_report['health_status']}")
        self.stdout.write(f"  Tamamlanma: %{health_report['statistics']['completion_rate']}")
        self.stdout.write(f"  Abandon: %{health_report['statistics']['abandonment_rate']}")

        if health_report['health_issues']:
            self.stdout.write('\nSAGLIK SORUNLARI:')
            for issue in health_report['health_issues']:
                self.stdout.write(f"  - {issue}")

        if health_report['recommendations']:
            self.stdout.write('\nONERILER:')
            for rec in health_report['recommendations']:
                self.stdout.write(f"  - {rec}")

        self.stdout.write('\nTemizleme tamamlandi!')