from pathlib import Path
from shutil import copy2

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Copy the repository's licensed demo product images into MEDIA_ROOT."

    def add_arguments(self, parser):
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Replace demo image files that already exist.",
        )

    def handle(self, *args, **options):
        source_directory = Path(settings.BASE_DIR) / "demo_assets" / "images"
        destination_directory = Path(settings.MEDIA_ROOT) / "images"
        if not source_directory.is_dir():
            raise CommandError(f"Demo image directory not found: {source_directory}")

        destination_directory.mkdir(parents=True, exist_ok=True)
        copied = 0
        skipped = 0
        for source in sorted(source_directory.iterdir()):
            if not source.is_file():
                continue
            destination = destination_directory / source.name
            if destination.exists() and not options["overwrite"]:
                skipped += 1
                continue
            copy2(source, destination)
            copied += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Installed {copied} demo image(s); skipped {skipped} existing file(s)."
            )
        )
