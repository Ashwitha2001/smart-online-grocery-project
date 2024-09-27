from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone
from decimal import Decimal

class Profile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('vendor', 'Vendor'),
        ('delivery_personnel', 'Delivery Personnel'),
        ('customer', 'Customer'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='customer')
    phone_number = models.CharField(max_length=10, blank=True, null=True)
    address = models.TextField(blank=True, null=True) 

    def __str__(self):
        return self.user.username

    def is_complete(self):
        # Check if essential fields are filled
        return all([self.address, self.phone_number])
    
class Category(models.Model):
    name = models.CharField(max_length=100)

class Subcategory(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category, related_name='subcategories', on_delete=models.CASCADE)

    class Meta:
        db_table = 'grocery_subcategory'

class Product(models.Model):
    name = models.CharField(max_length=100, db_index=True)
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    description = models.TextField(default='No description provided')
    price = models.DecimalField(max_digits=10, decimal_places=2, db_index=True)
    stock = models.PositiveIntegerField()
    category = models.ForeignKey('Category', on_delete=models.CASCADE, related_name='products', db_index=True)
    subcategory = models.ForeignKey('Subcategory', null=True, blank=True, on_delete=models.SET_NULL, related_name='products', db_index=True)
    vendor = models.ForeignKey('Vendor', on_delete=models.CASCADE, related_name='products', db_index=True)
    
    def average_rating(self):
        reviews = self.reviews.all()
        if reviews.exists():
            return reviews.aggregate(models.Avg('rating'))['rating__avg']
        return None  # Or return 0.0 if you prefer
    
class Cart(models.Model):
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE, null=True, blank=True)
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(null=True, blank=True)

    def get_price(self):
        return self.product.price if self.product.price else Decimal('0.00')

class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    address = models.TextField()
    phone_number = models.CharField(max_length=10)

class Order(models.Model):
    STATUS_CHOICES = [
        ('Placed','Placed'),
        ('Processing', 'Processing'),
        ('Shipped', 'Shipped'),
        ('Out for Delivery', 'Out for Delivery'),
        ('Delivered', 'Delivered'),
        ('Canceled', 'Canceled'),
    ]

    customer = models.ForeignKey('Customer', null=True, on_delete=models.CASCADE, related_name='customer_orders')
    delivery_partner = models.ForeignKey('Profile', null=True, related_name='delivery_personnel_orders', on_delete=models.SET_NULL)
    vendor = models.ForeignKey('Vendor', on_delete=models.CASCADE, related_name='vendor_orders')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, default=0)
    ordered_at = models.DateTimeField(auto_now_add=True)  # Automatically captures the time the order is placed
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Placed')
    razorpay_order_id = models.CharField(max_length=255, blank=True, null=True)  
    
class OrderItem(models.Model):
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

class Delivery(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('In Transit', 'In Transit'),
        ('Delivered', 'Delivered'),
        ('Canceled', 'Canceled'),
    ]

    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='deliveries')
    delivery_partner= models.ForeignKey('Profile', null=True, related_name='deliveries', on_delete=models.SET_NULL)
    address = models.CharField(max_length=255, null=True, blank=True)  # Address where the delivery is to be made
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    scheduled_at = models.DateTimeField(default=timezone.now)        # Or set manually when scheduling
    delivered_at = models.DateTimeField(null=True, blank=True)        # Set when delivered
    created_at = models.DateTimeField(auto_now_add=True, null=True,blank=True)         # Automatically set when the delivery record is created

    def update_status(self):
        if self.delivered_at:
            self.status = 'Delivered'
        elif self.status == 'In Transit':
            # Optionally, handle other status logic here if needed
            self.status = 'In Transit'
        else:
            self.status = 'Pending'
    
class Vendor(models.Model):
    profile = models.OneToOneField('Profile', on_delete=models.CASCADE)
    business_name = models.CharField(max_length=255)
    business_address = models.TextField()
    phone = models.CharField(max_length=10, null=True, blank=True) 

    class Meta:
        permissions = [
            ("can_manage_business", "Can manage their business"),
            ("can_edit_own_profile", "Can edit own profile"),
            ("can_view_own_profile", "Can view own profile"),
        ]

class Invoice(models.Model):
    order = models.ForeignKey('Order', on_delete=models.CASCADE)
    invoice_date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    pdf_file = models.FileField(upload_to='invoices/', blank=True, null=True)
    email_sent = models.BooleanField(default=False)

class UserActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.action} on {self.timestamp}"
    

class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)], default=5)
    comment = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Review by {self.customer.user.username} for {self.product.name}"

    class Meta:
        unique_together = ['product', 'customer'] 