from decimal import Decimal
from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from account.admin import UserAdminCreationForm

from .models import Category, Design, ProductVariant, validate_design_image


def test_image(name="design.png", size=(100, 100)):
    content = BytesIO()
    Image.new("RGB", size, color="navy").save(content, format="PNG")
    return SimpleUploadedFile(name, content.getvalue(), content_type="image/png")


class DemoFixtureTests(TestCase):
    fixtures = ["shop_fixture.utf8.json"]

    def test_demo_catalog_loads_with_non_login_owner(self):
        self.assertGreater(Category.objects.count(), 0)
        self.assertGreater(Design.objects.count(), 0)
        owner = get_user_model().objects.get(pk=1)
        self.assertFalse(owner.has_usable_password())
        self.assertFalse(owner.is_active)

    def test_demo_variants_can_be_seeded(self):
        call_command("seed_demo_variants", verbosity=0)

        expected_per_design = 6 * 3 * 4
        self.assertEqual(
            ProductVariant.objects.count(),
            Design.objects.count() * expected_per_design,
        )


class ShopViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        creator = get_user_model().objects.create_user(
            email="creator@example.com",
            user_name="creator",
            password="StrongPass123",
            is_active=True,
        )
        category = Category.objects.create(name="Space", slug="space")
        cls.visible_design = Design.objects.create(
            category=category,
            created_by=creator,
            name="Visible Shirt",
            description="A visible sample design",
            image="images/visible.jpg",
            slug="visible-shirt",
            price=Decimal("24.99"),
        )
        ProductVariant.objects.create(
            design=cls.visible_design,
            size="M",
            fabric="cotton",
            color="cosmic-black",
            stock_quantity=10,
        )
        cls.inactive_design = Design.objects.create(
            category=category,
            created_by=creator,
            name="Inactive Shirt",
            image="images/inactive.jpg",
            slug="inactive-shirt",
            price=Decimal("19.99"),
            is_active=False,
        )
        cls.out_of_stock_design = Design.objects.create(
            category=category,
            created_by=creator,
            name="Unavailable Shirt",
            image="images/unavailable.jpg",
            slug="unavailable-shirt",
            price=Decimal("29.99"),
        )

    def test_home_shows_active_design_and_hides_inactive_design(self):
        response = self.client.get(reverse("shop:all_designs"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.visible_design.name)
        self.assertNotContains(response, self.inactive_design.name)

    def test_active_in_stock_design_detail_is_available(self):
        response = self.client.get(self.visible_design.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add to Demo Cart")
        self.assertEqual(response.context["sizes"], ["M"])
        self.assertEqual(response.context["fabrics"], ["cotton"])
        self.assertEqual(response.context["colors"], ["cosmic-black"])

    def test_inactive_and_out_of_stock_design_details_return_404(self):
        for design in (self.inactive_design, self.out_of_stock_design):
            with self.subTest(design=design.slug):
                response = self.client.get(design.get_absolute_url())
                self.assertEqual(response.status_code, 404)


class AdminWorkflowTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls._media_directory = TemporaryDirectory()
        cls._media_override = override_settings(MEDIA_ROOT=cls._media_directory.name)
        cls._media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._media_override.disable()
        cls._media_directory.cleanup()

    @classmethod
    def setUpTestData(cls):
        cls.admin_user = get_user_model().objects.create_superuser(
            email="admin@example.com",
            user_name="admin",
            password="StrongAdminPass123",
        )
        cls.member = get_user_model().objects.create_user(
            email="member-admin-test@example.com",
            user_name="member-admin-test",
            password="StrongPass123",
            is_active=True,
        )
        cls.category = Category.objects.create(name="Admin Space", slug="admin-space")

    def test_admin_requires_staff_access(self):
        url = reverse("admin:index")
        anonymous_response = self.client.get(url)
        self.assertRedirects(
            anonymous_response,
            f"{reverse('admin:login')}?next={url}",
        )

        self.client.force_login(self.member)
        member_response = self.client.get(url)
        self.assertRedirects(
            member_response,
            f"{reverse('admin:login')}?next={url}",
        )

    def test_admin_pages_and_branding_load_for_superuser(self):
        self.client.force_login(self.admin_user)
        for url_name in (
            "admin:index",
            "admin:shop_design_changelist",
            "admin:shop_productvariant_changelist",
            "admin:account_userbase_changelist",
        ):
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)
        self.assertContains(
            self.client.get(reverse("admin:index")),
            "Cosmos Administration",
        )

    def test_admin_add_design_assigns_creator_and_variant(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("admin:shop_design_add"),
            {
                "name": "Admin Created Shirt",
                "slug": "admin-created-shirt",
                "category": self.category.pk,
                "description": "Created through the catalog admin.",
                "price": "34.99",
                "is_active": "on",
                "image": test_image(),
                "variants-TOTAL_FORMS": "1",
                "variants-INITIAL_FORMS": "0",
                "variants-MIN_NUM_FORMS": "0",
                "variants-MAX_NUM_FORMS": "1000",
                "variants-0-size": "M",
                "variants-0-fabric": "cotton",
                "variants-0-color": "cosmic-black",
                "variants-0-price_override": "",
                "variants-0-stock_quantity": "8",
                "variants-0-is_active": "on",
                "_save": "Save",
            },
        )

        self.assertEqual(response.status_code, 302)
        design = Design.objects.get(slug="admin-created-shirt")
        self.assertEqual(design.created_by, self.admin_user)
        self.assertTrue(design.is_available)
        self.assertEqual(design.variants.get().stock_quantity, 8)

    def test_generate_missing_variants_action_is_idempotent(self):
        design = Design.objects.create(
            category=self.category,
            created_by=self.admin_user,
            name="Variant Matrix Shirt",
            image="images/variant-matrix.jpg",
            slug="variant-matrix-shirt",
            price=Decimal("25.00"),
        )
        ProductVariant.objects.create(
            design=design,
            size="S",
            fabric="cotton",
            color="cosmic-black",
            stock_quantity=1,
        )
        self.client.force_login(self.admin_user)
        action_data = {
            "action": "generate_missing_variants",
            "_selected_action": [str(design.pk)],
        }

        self.client.post(reverse("admin:shop_design_changelist"), action_data)
        self.client.post(reverse("admin:shop_design_changelist"), action_data)

        self.assertEqual(design.variants.count(), 6 * 3 * 4)
        self.assertEqual(
            design.variants.exclude(
                size="S", fabric="cotton", color="cosmic-black"
            ).filter(stock_quantity=0).count(),
            (6 * 3 * 4) - 1,
        )

    def test_category_with_design_is_protected_from_deletion(self):
        Design.objects.create(
            category=self.category,
            created_by=self.admin_user,
            name="Protected Shirt",
            image="images/protected.jpg",
            slug="protected-shirt",
            price=Decimal("20.00"),
        )
        with self.assertRaises(ProtectedError):
            self.category.delete()

    def test_deleting_creator_preserves_design(self):
        creator = get_user_model().objects.create_user(
            email="temporary@example.com",
            user_name="temporary",
            password="StrongPass123",
        )
        design = Design.objects.create(
            category=self.category,
            created_by=creator,
            name="Preserved Shirt",
            image="images/preserved.jpg",
            slug="preserved-shirt",
            price=Decimal("20.00"),
        )
        creator.delete()
        design.refresh_from_db()
        self.assertIsNone(design.created_by)

    def test_duplicate_variant_combination_is_rejected(self):
        design = Design.objects.create(
            category=self.category,
            created_by=self.admin_user,
            name="Unique Variant Shirt",
            image="images/unique.jpg",
            slug="unique-variant-shirt",
            price=Decimal("20.00"),
        )
        values = {
            "design": design,
            "size": "M",
            "fabric": "cotton",
            "color": "cosmic-black",
            "stock_quantity": 1,
        }
        ProductVariant.objects.create(**values)
        with self.assertRaises(IntegrityError):
            with self.atomic():
                ProductVariant.objects.create(**values)

    def atomic(self):
        from django.db import transaction

        return transaction.atomic()

    def test_oversized_image_is_rejected(self):
        oversized = SimpleUploadedFile(
            "large.png",
            b"x" * ((5 * 1024 * 1024) + 1),
            content_type="image/png",
        )
        with self.assertRaisesMessage(ValidationError, "5 MB or smaller"):
            validate_design_image(oversized)

    def test_user_admin_creation_form_hashes_password(self):
        form = UserAdminCreationForm(
            data={
                "email": "staff@example.com",
                "user_name": "staff",
                "password1": "AnotherStrongPass123",
                "password2": "AnotherStrongPass123",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertNotEqual(user.password, "AnotherStrongPass123")
        self.assertTrue(user.check_password("AnotherStrongPass123"))
