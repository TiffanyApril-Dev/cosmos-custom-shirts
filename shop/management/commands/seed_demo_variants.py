from itertools import product

from django.core.management.base import BaseCommand

from shop.models import Design, ProductVariant


class Command(BaseCommand):
    help = "Create all standard shirt variants for designs that have none."

    def handle(self, *args, **options):
        created = 0
        for design in Design.objects.filter(variants__isnull=True):
            variants = [
                ProductVariant(
                    design=design,
                    size=size,
                    fabric=fabric,
                    color=color,
                    stock_quantity=25 if design.in_stock else 0,
                    is_active=design.is_active,
                )
                for size, fabric, color in product(
                    ProductVariant.Size.values,
                    ProductVariant.Fabric.values,
                    ProductVariant.Color.values,
                )
            ]
            ProductVariant.objects.bulk_create(variants)
            created += len(variants)

        self.stdout.write(self.style.SUCCESS(f"Created {created} demo product variants."))
