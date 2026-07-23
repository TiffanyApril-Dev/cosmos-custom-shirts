from itertools import product

from django.contrib import admin, messages
from django.db.models import Count, Q, Sum
from django.template.defaultfilters import filesizeformat
from django.utils.html import format_html

from .models import Category, Design, ProductVariant


class StockStatusFilter(admin.SimpleListFilter):
    title = "stock status"
    parameter_name = "stock_status"

    def lookups(self, request, model_admin):
        return (
            ("in_stock", "In stock"),
            ("low_stock", "Low stock (1–5)"),
            ("out_of_stock", "Out of stock"),
        )

    def queryset(self, request, queryset):
        if self.value() == "in_stock":
            return queryset.filter(stock_quantity__gt=5, is_active=True)
        if self.value() == "low_stock":
            return queryset.filter(stock_quantity__range=(1, 5), is_active=True)
        if self.value() == "out_of_stock":
            return queryset.filter(Q(stock_quantity=0) | Q(is_active=False))
        return queryset


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = (
        "size",
        "fabric",
        "color",
        "price_override",
        "stock_quantity",
        "is_active",
    )
    ordering = ("size", "fabric", "color")
    verbose_name = "Product variant"
    verbose_name_plural = "Product variants — price override is optional"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "design_count")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_design_count=Count("design"))

    @admin.display(description="Designs", ordering="_design_count")
    def design_count(self, obj):
        return obj._design_count

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions


@admin.register(Design)
class DesignAdmin(admin.ModelAdmin):
    list_display = (
        "thumbnail",
        "name",
        "category",
        "price",
        "availability",
        "variant_count",
        "total_inventory",
        "is_active",
        "updated",
    )
    list_display_links = ("thumbnail", "name")
    list_filter = ("is_active", "category", "created", "updated")
    search_fields = ("name", "description", "slug")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = (
        "created_by",
        "created",
        "updated",
        "image_preview",
        "availability",
        "variant_count",
        "total_inventory",
    )
    inlines = (ProductVariantInline,)
    actions = ("activate_designs", "deactivate_designs", "generate_missing_variants")
    list_select_related = ("category", "created_by")
    fieldsets = (
        (
            "Product information",
            {"fields": ("name", "slug", "category", "description", "is_active")},
        ),
        ("Pricing", {"fields": ("price",)}),
        ("Product image", {"fields": ("image", "image_preview")}),
        (
            "Inventory summary",
            {
                "fields": ("availability", "variant_count", "total_inventory"),
                "description": (
                    "Availability is calculated from active variants with stock."
                ),
            },
        ),
        (
            "Metadata",
            {"classes": ("collapse",), "fields": ("created_by", "created", "updated")},
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(
                _variant_count=Count("variants"),
                _available_variant_count=Count(
                    "variants",
                    filter=Q(variants__is_active=True, variants__stock_quantity__gt=0),
                ),
                _total_inventory=Sum(
                    "variants__stock_quantity",
                    filter=Q(variants__is_active=True),
                    default=0,
                ),
            )
        )

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @admin.display(description="Image")
    def thumbnail(self, obj):
        if not obj.image:
            return "—"
        return format_html(
            '<img src="{}" alt="" style="width:48px;height:48px;'
            'object-fit:cover;border-radius:6px">',
            obj.image.url,
        )

    @admin.display(description="Current image")
    def image_preview(self, obj):
        if not obj or not obj.image:
            return "No image uploaded."
        size = ""
        try:
            size = f" ({filesizeformat(obj.image.size)})"
        except OSError:
            pass
        return format_html(
            '<img src="{}" alt="{}" style="max-width:320px;max-height:240px;'
            'object-fit:contain;border-radius:8px"><br>{}{}',
            obj.image.url,
            obj.name,
            obj.image.name,
            size,
        )

    @admin.display(description="Available", boolean=True, ordering="_available_variant_count")
    def availability(self, obj):
        if not obj:
            return False
        if hasattr(obj, "_available_variant_count"):
            return obj.is_active and obj._available_variant_count > 0
        return obj.is_available

    @admin.display(description="Variants", ordering="_variant_count")
    def variant_count(self, obj):
        if not obj:
            return 0
        return getattr(obj, "_variant_count", obj.variants.count())

    @admin.display(description="Inventory", ordering="_total_inventory")
    def total_inventory(self, obj):
        if not obj:
            return 0
        if hasattr(obj, "_total_inventory"):
            return obj._total_inventory
        return obj.variants.filter(is_active=True).aggregate(
            total=Sum("stock_quantity", default=0)
        )["total"]

    @admin.action(description="Activate selected designs")
    def activate_designs(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Activated {updated} design(s).", messages.SUCCESS)

    @admin.action(description="Deactivate selected designs")
    def deactivate_designs(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {updated} design(s).", messages.SUCCESS)

    @admin.action(description="Generate missing standard variants (stock starts at 0)")
    def generate_missing_variants(self, request, queryset):
        variants_to_create = []
        for design in queryset:
            existing = set(
                design.variants.values_list("size", "fabric", "color")
            )
            for combination in product(
                ProductVariant.Size.values,
                ProductVariant.Fabric.values,
                ProductVariant.Color.values,
            ):
                if combination not in existing:
                    variants_to_create.append(
                        ProductVariant(
                            design=design,
                            size=combination[0],
                            fabric=combination[1],
                            color=combination[2],
                            stock_quantity=0,
                        )
                    )
        ProductVariant.objects.bulk_create(variants_to_create, ignore_conflicts=True)
        self.message_user(
            request,
            f"Created {len(variants_to_create)} missing variant(s) with zero stock.",
            messages.SUCCESS,
        )


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = (
        "design",
        "size",
        "fabric",
        "color",
        "price_override",
        "stock_quantity",
        "stock_status",
        "is_active",
    )
    list_filter = (StockStatusFilter, "size", "fabric", "color", "is_active")
    search_fields = ("design__name", "design__slug")
    list_select_related = ("design",)
    actions = (
        "activate_variants",
        "deactivate_variants",
        "mark_out_of_stock",
    )

    @admin.display(description="Stock status")
    def stock_status(self, obj):
        if not obj.is_active:
            return "Inactive"
        if obj.stock_quantity == 0:
            return "Out of stock"
        if obj.stock_quantity <= 5:
            return "Low stock"
        return "In stock"

    @admin.action(description="Activate selected variants")
    def activate_variants(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Activated {updated} variant(s).", messages.SUCCESS)

    @admin.action(description="Deactivate selected variants")
    def deactivate_variants(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {updated} variant(s).", messages.SUCCESS)

    @admin.action(description="Set selected variants to zero stock")
    def mark_out_of_stock(self, request, queryset):
        updated = queryset.update(stock_quantity=0)
        self.message_user(
            request,
            f"Set {updated} variant(s) to zero stock.",
            messages.SUCCESS,
        )


admin.site.site_header = "Cosmos Administration"
admin.site.site_title = "Cosmos Admin"
admin.site.index_title = "Store Management"
