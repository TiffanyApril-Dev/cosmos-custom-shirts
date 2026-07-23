from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from shop.models import Design, ProductVariant

from .basket import Basket

# This helper function is used to return a consistent JSON error response for invalid requests in the AJAX views. It takes an error message and an optional HTTP status code (defaulting to 400 Bad Request) and returns a JsonResponse with the error message.
def _invalid_request(message, status=400):
    return JsonResponse({"error": message}, status=status)


def cart_summary(request):
    basket = Basket(request)
    return render(
        request,
        "shop/basket/summary.html",
        {"basket": basket},
    )

# The following views are designed to be called via AJAX from the cart summary page. They return JSON responses with the updated cart state or error messages.

def cart_add(request):
    basket = Basket(request)

    if request.method != "POST" or request.POST.get("action") != "post":
        return _invalid_request("Invalid request.")

    try:
        design_id = int(request.POST.get("designid", ""))
    except ValueError:
        return _invalid_request("Invalid design id.")

    size = request.POST.get("size", "")
    fabric = request.POST.get("fabric", "")
    color = request.POST.get("color", "")

    design = get_object_or_404(Design, id=design_id, is_active=True)
    variant = ProductVariant.objects.filter(
        design=design,
        size=size,
        fabric=fabric,
        color=color,
        is_active=True,
        stock_quantity__gt=0,
    ).first()
    if variant is None:
        return _invalid_request("Selected product combination is unavailable.")
    basket.add(variant=variant)

    return JsonResponse(
        {
            "cart_count": len(basket),
            "subtotal": f"{basket.get_total_price():.2f}",
        }
    )

# The cart_update and cart_delete views follow a similar pattern: they validate the request, perform the requested action on the basket, and return a JSON response with the updated cart state or an error message if something goes wrong.
def cart_update(request):
    basket = Basket(request)

    if request.method != "POST" or request.POST.get("action") != "post":
        return _invalid_request("Invalid request.")

    item_key = request.POST.get("itemkey", "")
    size = request.POST.get("size", "")
    fabric = request.POST.get("fabric", "")
    color = request.POST.get("color", "")

    if not item_key:
        return _invalid_request("Missing cart item key.")
    current_item = basket.cart.get(item_key)
    if current_item is None:
        return _invalid_request("Cart item not found.", status=404)
    current_variant = ProductVariant.objects.filter(pk=current_item.get("variant_id")).first()
    if current_variant is None:
        return _invalid_request("Cart item is no longer available.", status=404)
    variant = ProductVariant.objects.filter(
        design_id=current_variant.design_id,
        size=size,
        fabric=fabric,
        color=color,
        is_active=True,
        stock_quantity__gt=0,
    ).first()
    if variant is None:
        return _invalid_request("Selected product combination is unavailable.")

    was_updated = basket.update(item_key=item_key, variant=variant)
    if not was_updated:
        return _invalid_request("Cart item not found.", status=404)

    return JsonResponse(
        {
            "cart_count": len(basket),
            "subtotal": f"{basket.get_total_price():.2f}",
        }
    )

# The cart_delete view validates the request and attempts to delete the specified item from the basket. If the item is not found, it returns a 404 error. Otherwise, it returns the updated cart count and subtotal.
def cart_delete(request):
    basket = Basket(request)

    if request.method != "POST" or request.POST.get("action") != "post":
        return _invalid_request("Invalid request.")

    item_key = request.POST.get("itemkey", "")
    if not item_key:
        return _invalid_request("Missing cart item key.")

    was_deleted = basket.delete(item_key=item_key)
    if not was_deleted:
        return _invalid_request("Cart item not found.", status=404)

    return JsonResponse(
        {
            "cart_count": len(basket),
            "subtotal": f"{basket.get_total_price():.2f}",
        }
    )
