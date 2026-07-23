from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse
from PIL import Image


MAX_IMAGE_SIZE = 5 * 1024 * 1024
MAX_IMAGE_DIMENSION = 6000


def validate_design_image(image):
    if image.size > MAX_IMAGE_SIZE:
        raise ValidationError("Product images must be 5 MB or smaller.")

    try:
        image.file.seek(0)
        with Image.open(image.file) as uploaded_image:
            width, height = uploaded_image.size
            if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
                raise ValidationError(
                    "Product images cannot exceed 6000 × 6000 pixels."
                )
            uploaded_image.verify()
        image.file.seek(0)
    except ValidationError:
        raise
    except (OSError, SyntaxError, ValueError) as exc:
        raise ValidationError("Upload a valid JPEG, PNG, or WebP image.") from exc

# Create your models here.
class Category(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, unique=True)

    class Meta:
        verbose_name_plural = 'categories'

    def get_absolute_url(self):
        return reverse('shop:category_detail', args=[self.slug])

    def __str__(self):
        return self.name

class Design(models.Model):
    category = models.ForeignKey(Category, related_name='design', on_delete=models.PROTECT)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='design_creator',
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    image = models.ImageField(
        upload_to='images/',
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"]),
            validate_design_image,
        ],
        help_text="JPEG, PNG, or WebP. Maximum 5 MB and 6000 × 6000 pixels.",
    )
    slug = models.SlugField(max_length=255, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    # Retained for compatibility with the original demo fixture. Variant
    # inventory is authoritative and this field is not exposed in the admin.
    in_stock = models.BooleanField(default=True, editable=False)
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    # Make the ordering for this model be the updated field in descending order
    class Meta:
        ordering = ['-updated']

    # Add a dunder method to return the name field
    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('shop:design_detail', args=[self.slug])

    @property
    def is_available(self):
        return self.is_active and self.variants.filter(
            is_active=True,
            stock_quantity__gt=0,
        ).exists()


class ProductVariant(models.Model):
    class Size(models.TextChoices):
        SMALL = "S", "Small (S)"
        MEDIUM = "M", "Medium (M)"
        LARGE = "L", "Large (L)"
        EXTRA_LARGE = "XL", "Extra Large (XL)"
        TWO_X = "2XL", "2X Large (2XL)"
        THREE_X = "3XL", "3X Large (3XL)"

    class Fabric(models.TextChoices):
        COTTON = "cotton", "100% Cotton"
        POLYESTER = "polyester", "Polyester"
        POLYBLEND = "polyblend", "Poly-Blend"

    class Color(models.TextChoices):
        BLACK = "cosmic-black", "Cosmic Black"
        WHITE = "stardust-white", "Stardust White"
        PURPLE = "nebula-purple", "Nebula Purple"
        BLUE = "galaxy-blue", "Galaxy Blue"

    design = models.ForeignKey(Design, related_name="variants", on_delete=models.CASCADE)
    size = models.CharField(max_length=4, choices=Size.choices)
    fabric = models.CharField(max_length=20, choices=Fabric.choices)
    color = models.CharField(max_length=20, choices=Color.choices)
    price_override = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["design", "size", "fabric", "color"],
                name="unique_design_variant",
            ),
            models.CheckConstraint(
                condition=models.Q(price_override__isnull=True) | models.Q(price_override__gt=0),
                name="variant_price_override_positive",
            ),
        ]
        ordering = ["design", "size", "fabric", "color"]

    @property
    def price(self):
        return self.price_override if self.price_override is not None else self.design.price

    @classmethod
    def available_options(cls, variants):
        """Return unique option values in the deliberate TextChoices order."""
        rows = list(variants.values_list("size", "fabric", "color"))
        available_sizes = {row[0] for row in rows}
        available_fabrics = {row[1] for row in rows}
        available_colors = {row[2] for row in rows}
        return {
            "sizes": [value for value in cls.Size.values if value in available_sizes],
            "fabrics": [value for value in cls.Fabric.values if value in available_fabrics],
            "colors": [value for value in cls.Color.values if value in available_colors],
        }

    def __str__(self):
        return f"{self.design.name} / {self.size} / {self.fabric} / {self.color}"
