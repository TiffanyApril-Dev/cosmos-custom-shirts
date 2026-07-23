from itertools import product

from django.db import migrations, models
import django.db.models.deletion


SIZES = ["S", "M", "L", "XL", "2XL", "3XL"]
FABRICS = ["cotton", "polyester", "polyblend"]
COLORS = ["cosmic-black", "stardust-white", "nebula-purple", "galaxy-blue"]


def create_variants_for_existing_designs(apps, schema_editor):
    Design = apps.get_model("shop", "Design")
    ProductVariant = apps.get_model("shop", "ProductVariant")
    variants = [
        ProductVariant(
            design=design,
            size=size,
            fabric=fabric,
            color=color,
            stock_quantity=100 if design.in_stock else 0,
            is_active=design.is_active,
        )
        for design in Design.objects.all()
        for size, fabric, color in product(SIZES, FABRICS, COLORS)
    ]
    ProductVariant.objects.bulk_create(variants)


class Migration(migrations.Migration):
    dependencies = [("shop", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="ProductVariant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("size", models.CharField(choices=[("S", "Small (S)"), ("M", "Medium (M)"), ("L", "Large (L)"), ("XL", "Extra Large (XL)"), ("2XL", "2X Large (2XL)"), ("3XL", "3X Large (3XL)")], max_length=4)),
                ("fabric", models.CharField(choices=[("cotton", "100% Cotton"), ("polyester", "Polyester"), ("polyblend", "Poly-Blend")], max_length=20)),
                ("color", models.CharField(choices=[("cosmic-black", "Cosmic Black"), ("stardust-white", "Stardust White"), ("nebula-purple", "Nebula Purple"), ("galaxy-blue", "Galaxy Blue")], max_length=20)),
                ("price_override", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("stock_quantity", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("design", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="variants", to="shop.design")),
            ],
            options={"ordering": ["design", "size", "fabric", "color"]},
        ),
        migrations.AddConstraint(
            model_name="productvariant",
            constraint=models.UniqueConstraint(fields=("design", "size", "fabric", "color"), name="unique_design_variant"),
        ),
        migrations.AddConstraint(
            model_name="productvariant",
            constraint=models.CheckConstraint(condition=models.Q(("price_override__isnull", True), ("price_override__gt", 0), _connector="OR"), name="variant_price_override_positive"),
        ),
        migrations.RunPython(create_variants_for_existing_designs, migrations.RunPython.noop),
    ]
