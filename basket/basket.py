from decimal import Decimal
from uuid import uuid4

from shop.models import ProductVariant


class Basket:
    """Session-backed demo cart containing database-owned product variants."""

    session_key = "cart"

    def __init__(self, request):
        self.session = request.session
        self.cart = self.session.setdefault(self.session_key, {})

    def add(self, variant):
        item_key = uuid4().hex[:12]
        self.cart[item_key] = {"variant_id": variant.id}
        self.save()
        return item_key

    def update(self, item_key, variant):
        item = self.cart.get(item_key)
        if item is None:
            return False

        current_variant = ProductVariant.objects.filter(pk=item.get("variant_id")).first()
        if current_variant is None or current_variant.design_id != variant.design_id:
            return False

        item["variant_id"] = variant.id
        self.save()
        return True

    def delete(self, item_key):
        if item_key not in self.cart:
            return False
        del self.cart[item_key]
        self.save()
        return True

    def __iter__(self):
        variant_ids = [item.get("variant_id") for item in self.cart.values()]
        variants = ProductVariant.objects.select_related("design").filter(
            id__in=variant_ids,
            is_active=True,
            stock_quantity__gt=0,
            design__is_active=True,
        )
        variant_map = {variant.id: variant for variant in variants}

        for item_key, item in self.cart.items():
            variant = variant_map.get(item.get("variant_id"))
            if variant is None:
                continue
            available = ProductVariant.objects.filter(
                design=variant.design,
                is_active=True,
                stock_quantity__gt=0,
            )
            options = ProductVariant.available_options(available)
            price = variant.price
            yield {
                "key": item_key,
                "design": variant.design,
                "variant": variant,
                "price": price,
                "size": variant.size,
                "fabric": variant.fabric,
                "color": variant.color,
                "valid_sizes": options["sizes"],
                "valid_fabrics": options["fabrics"],
                "valid_colors": options["colors"],
                "total_price": price,
            }

    def __len__(self):
        return sum(1 for _ in self)

    def get_total_price(self):
        return sum((item["price"] for item in self), Decimal("0.00"))

    def save(self):
        self.session.modified = True
