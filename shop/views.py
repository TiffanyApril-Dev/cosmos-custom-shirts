from django.db.models import Exists, OuterRef
from django.shortcuts import render, get_object_or_404


from .models import Category, Design, ProductVariant

# Create your views here.
def categories(request):
    return {'categories': Category.objects.all()}


def available_designs():
    available_variants = ProductVariant.objects.filter(
        design_id=OuterRef("pk"),
        is_active=True,
        stock_quantity__gt=0,
    )
    return Design.objects.filter(is_active=True).annotate(
        has_available_variants=Exists(available_variants)
    ).filter(has_available_variants=True)


def all_designs(request):
    categories = Category.objects.all()
    # Get designs grouped by category
    designs_by_category = []
    for category in categories:
        category_designs = available_designs().filter(category=category)
        if category_designs.exists():
            designs_by_category.append({
                'category': category,
                'designs': category_designs
            })
    return render(request, 'shop/home.html', {
        'designs_by_category': designs_by_category,
        'categories': categories
    })

# Design detail view
def design_detail(request, slug):
    design = get_object_or_404(available_designs(), slug=slug)
    variants = design.variants.filter(is_active=True, stock_quantity__gt=0)
    options = ProductVariant.available_options(variants)
    return render(request, 'shop/detail.html', {
        'design': design,
        **options,
        'has_variants': bool(options['sizes']),
    })
# Category detail view
def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    designs = available_designs().filter(category=category)
    return render(request, 'shop/category.html', {'category': category, 'designs': designs})
