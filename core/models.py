from django.db import models


# ✅ PRODUCT MODEL
class Product(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField()
    vendor = models.ForeignKey('Vendor', on_delete=models.SET_NULL, null=True, blank=True, related_name='products')

    def __str__(self):
        return self.name


class Vendor(models.Model):
    name = models.CharField(max_length=120)
    company_name = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    gst_number = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.company_name or self.name


# ✅ CUSTOMER MODEL
class Customer(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


# ✅ ORDER MODEL
class Order(models.Model):

    # 🔗 Relations
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    # 📦 Order details
    quantity = models.IntegerField()

    # 💰 Pricing
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    gst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # 💳 Payment
    PAYMENT_CHOICES = [
        ('Cash', 'Cash'),
        ('UPI', 'UPI'),
        ('Card', 'Card'),
    ]

    payment_method = models.CharField(
        max_length=10,
        choices=PAYMENT_CHOICES,
        default='Cash'
    )

    # 📊 Status
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Completed'
    )

    # 📅 Date
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} - {self.customer.name}"


class VendorPurchase(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='purchases')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='vendor_purchases')
    quantity = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2)
    invoice_number = models.CharField(max_length=60, blank=True)
    purchased_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.vendor} - {self.product} ({self.quantity})"


# ✅ OTP MODEL (for login security)
class UserOTP(models.Model):
    username = models.CharField(max_length=100)
    otp = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username
    
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    ROLE_CHOICES = (
        ('customer', 'Customer'),
        ('staff', 'Staff'),
        ('admin', 'Admin'),
    )

    role = models.CharField(max_length=20)
    is_approved = models.BooleanField(default=False)  # for staff approval

    def __str__(self):
        return self.user.username


# ✅ CUSTOMER FEEDBACK MODEL
class Feedback(models.Model):
    RATING_CHOICES = [
        (1, '⭐'),
        (2, '⭐⭐'),
        (3, '⭐⭐⭐'),
        (4, '⭐⭐⭐⭐'),
        (5, '⭐⭐⭐⭐⭐'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True)
    rating = models.IntegerField(choices=RATING_CHOICES)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback from {self.customer.name} - {self.rating} stars"

    class Meta:
        ordering = ['-created_at']


# ✅ SHOPPING CART MODEL
class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='shopping_cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart - {self.user.username}"

    def get_total_price(self):
        total = sum([item.get_total_price() for item in self.items.all()])
        return total

    def get_gst(self):
        subtotal = self.get_total_price()
        return subtotal * 0.18

    def get_final_total(self):
        return self.get_total_price() + self.get_gst()


# ✅ CART ITEM MODEL
class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    def get_total_price(self):
        return self.product.price * self.quantity
        ordering = ['-created_at']
