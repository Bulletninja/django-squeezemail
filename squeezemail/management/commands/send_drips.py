from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        from squeezemail.models import Step

        for step in Step.objects.filter(is_active=True):
            step.run()
