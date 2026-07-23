from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from shop.models import Category, Design, ProductVariant


class BasketViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        creator = get_user_model().objects.create_user(
            email="designer@example.com",
            user_name="designer",
            password="StrongPass123",
            is_active=True,
        )
        category = Category.objects.create(name="Galaxy", slug="galaxy")
        cls.design = Design.objects.create(
            category=category,
            created_by=creator,
            name="Galaxy Shirt",
            image="images/galaxy.jpg",
            slug="galaxy-shirt",
            price=Decimal("25.00"),
        )
        cls.medium_variant = ProductVariant.objects.create(
            design=cls.design,
            size="M",
            fabric="cotton",
            color="cosmic-black",
            stock_quantity=10,
        )
        cls.large_variant = ProductVariant.objects.create(
            design=cls.design,
            size="L",
            fabric="cotton",
            color="cosmic-black",
            stock_quantity=10,
        )
        cls.updated_variant = ProductVariant.objects.create(
            design=cls.design,
            size="XL",
            fabric="polyblend",
            color="galaxy-blue",
            stock_quantity=10,
        )

    def add_design(self, **overrides):
        data = {
            "action": "post",
            "designid": str(self.design.pk),
            "size": "M",
            "fabric": "cotton",
            "color": "cosmic-black",
        }
        data.update(overrides)
        return self.client.post(reverse("basket:basket_add"), data)

    def test_add_design_stores_valid_options_in_session(self):
        response = self.add_design()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"cart_count": 1, "subtotal": "25.00"})
        cart_item = next(iter(self.client.session["cart"].values()))
        self.assertEqual(cart_item, {"variant_id": self.medium_variant.pk})

    def test_add_rejects_invalid_options(self):
        response = self.add_design(size="invalid")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Selected product combination is unavailable.")
        self.assertEqual(self.client.session.get("cart", {}), {})

    def test_add_rejects_inactive_or_out_of_stock_design(self):
        self.design.is_active = False
        self.design.save(update_fields=["is_active"])
        response = self.add_design()
        self.assertEqual(response.status_code, 404)

        self.design.is_active = True
        self.design.save(update_fields=["is_active"])
        self.medium_variant.stock_quantity = 0
        self.medium_variant.save(update_fields=["stock_quantity"])
        response = self.add_design()
        self.assertEqual(response.status_code, 400)

    def test_update_changes_options(self):
        self.add_design()
        item_key = next(iter(self.client.session["cart"]))

        response = self.client.post(
            reverse("basket:basket_update"),
            {
                "action": "post",
                "itemkey": item_key,
                "size": "XL",
                "fabric": "polyblend",
                "color": "galaxy-blue",
            },
        )

        self.assertEqual(response.status_code, 200)
        updated_item = self.client.session["cart"][item_key]
        self.assertEqual(updated_item, {"variant_id": self.updated_variant.pk})

    def test_subtotal_uses_current_database_price(self):
        self.add_design()
        self.design.price = Decimal("31.50")
        self.design.save(update_fields=["price"])

        response = self.client.get(reverse("basket:basket_summary"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "31.50")

    def test_summary_options_are_unique_and_follow_choice_order(self):
        self.add_design()

        response = self.client.get(reverse("basket:basket_summary"))
        item = list(response.context["basket"])[0]

        self.assertEqual(item["valid_sizes"], ["M", "L", "XL"])
        self.assertEqual(item["valid_fabrics"], ["cotton", "polyblend"])
        self.assertEqual(item["valid_colors"], ["cosmic-black", "galaxy-blue"])

    def test_delete_removes_only_requested_item(self):
        self.add_design(size="M")
        self.add_design(size="L")
        item_keys = list(self.client.session["cart"])

        response = self.client.post(
            reverse("basket:basket_delete"),
            {"action": "post", "itemkey": item_keys[0]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["cart_count"], 1)
        self.assertNotIn(item_keys[0], self.client.session["cart"])
        self.assertIn(item_keys[1], self.client.session["cart"])

    def test_mutation_endpoints_reject_get(self):
        for url_name in ("basket_add", "basket_update", "basket_delete"):
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(f"basket:{url_name}"))
                self.assertEqual(response.status_code, 400)
