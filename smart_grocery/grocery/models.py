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
    role = models.CharField(max_length=50, choices=ROLE_CHOICES)
    phone_number = models.CharField(max_length=10, blank=True, null=True)
    address = models.TextField(blank=True, null=True) 

    def __str__(self):
        return f"{self.user.username} - {self.role}"

    def is_complete(self):
        return all([self.address, self.phone_number])

    def update_assigned_orders(self):
        assigned_orders_count = Delivery.objects.filter(
            delivery_partner=self,
            created_at__date=timezone.now().date()
        ).count()

        print(f"Assigned orders updated to {assigned_orders_count}")
        return assigned_orders_count

class Admin(models.Model):
    profile = models.OneToOneField('Profile', on_delete=models.CASCADE)  
    permission_level = models.CharField(max_length=50, choices=[
        ('Super Admin', 'Super Admin'),
        ('Admin', 'Admin'),
        ('Manager', 'Manager')
    ]) 

    def __str__(self):
        return f"Admin: {self.profile.user.username} - {self.permission_level}"

    class Meta:
        permissions = [
            ("can_manage_system", "Can manage the system"),
            ("can_edit_own_profile", "Can edit own profile"),
        ]

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
    stock = models.PositiveIntegerField(default=0)
    category = models.ForeignKey('Category', on_delete=models.CASCADE, related_name='products', db_index=True)
    subcategory = models.ForeignKey('Subcategory', null=True, blank=True, on_delete=models.SET_NULL, related_name='products', db_index=True)
    vendor = models.ForeignKey('Vendor', on_delete=models.CASCADE, related_name='products', db_index=True)
    
    def average_rating(self):
        reviews = self.reviews.all()  
        if reviews.exists():
            return reviews.aggregate(models.Avg('rating'))['rating__avg']
        return None
    
class Cart(models.Model):
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE, null=True, blank=True)
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(null=True, blank=True)
    
    class Meta:
        unique_together = ('customer', 'product')

    def total_price(self):
        return self.product.price if self.product.price else Decimal('0.00')

class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    address = models.TextField()
    phone_number = models.CharField(max_length=10)

    def __str__(self):
        return self.user.username
 

class Order(models.Model):
    STATUS_CHOICES = [
        ('Placed', 'Placed'),
        ('Processing', 'Processing'),
        ('Shipped', 'Shipped'),
        ('Out for Delivery', 'Out for Delivery'),
        ('Delivered', 'Delivered'),
        ('Canceled', 'Canceled'),
    ]

    customer = models.ForeignKey('Customer', null=True, on_delete=models.CASCADE, related_name='customer_orders')
    delivery_partner = models.ForeignKey('Profile', null=True, related_name='delivery_personnel_orders', on_delete=models.SET_NULL)
    vendor = models.ForeignKey('Vendor', on_delete=models.CASCADE, related_name='vendor_orders')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, default=Decimal('0.00'))
    ordered_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Placed')
    razorpay_order_id = models.CharField(max_length=255, blank=True, null=True)  

    def get_delivered_at(self):
        delivery = self.deliveries.last()  
        if delivery:
            return delivery.delivered_at
        return None

    get_delivered_at.short_description = 'Delivered At'


class OrderItem(models.Model):
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Order #{self.order.id}"


class Delivery(models.Model):
    STATUS_CHOICES = [
        ('Placed', 'Placed'),
        ('Processing', 'Processing'),
        ('Shipped', 'Shipped'),
        ('Out for Delivery', 'Out for Delivery'),
        ('Delivered', 'Delivered'),
        ('Canceled', 'Canceled'),
    ]

    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='deliveries')
    delivery_partner = models.ForeignKey('Profile', null=True, related_name='deliveries', on_delete=models.SET_NULL)
    address = models.CharField(max_length=255, null=True, blank=True) 
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Placed')
    scheduled_at = models.DateTimeField(default=timezone.now)  # Set manually when scheduling
    delivered_at = models.DateTimeField(null=True, blank=True)  # Set when delivered
    created_at = models.DateTimeField(auto_now_add=True,null=True,blank=True)  # Automatically set when the delivery record is created

    def save(self, *args, **kwargs):
        super(Delivery, self).save(*args, **kwargs)
        # Update assigned orders count after saving a delivery
        if self.delivery_partner:
            delivery_personnel = self.delivery_partner.deliverypersonnel
            delivery_personnel.update_assigned_orders()

    def update_status(self):
        """Update the status of the delivery based on the current conditions."""
        if self.delivered_at:
            self.status = 'Delivered'
        elif self.status == 'Placed':
            self.status = 'Placed'
        elif self.status == 'Processing':
            self.status = 'Processing'
        elif self.status == 'Shipped':
            self.status = 'Shipped'
        self.save()
        
    def mark_as_delivered(self):
        """Mark the delivery as delivered and update the status."""
        self.delivered_at = timezone.now()
        self.status = 'Delivered'
        self.save()
    
    def __str__(self):
        return f"Delivery for Order #{self.order.id} - Status: {self.status}"


class DeliveryPersonnel(models.Model):
    profile = models.OneToOneField('Profile', on_delete=models.CASCADE)
    vehicle_type = models.CharField(max_length=50, blank=True, null=True) 
    vehicle_number = models.CharField(max_length=20, blank=True, null=True)
    phone = models.CharField(max_length=10, null=True, blank=True) 
    address = models.TextField(blank=True, null=True)
    max_daily_assignments = models.PositiveIntegerField(default=10)  # Max orders assignable per day
    assigned_orders = models.PositiveIntegerField(default=0)  # Current assigned orders for the day

    def update_assigned_orders(self):
        today = timezone.now().date()
        # Fetch deliveries assigned to this delivery personnel
        assigned_count = Delivery.objects.filter(
            delivery_partner=self.profile,
            created_at__date=today
        ).count()
        print(f"Assigned count for {self.profile.user.username}: {assigned_count}")  # Debug output
        self.assigned_orders = assigned_count
        self.save()
        

    def can_assign_more_orders(self):
        """Check if the delivery partner can take more orders for the day."""
        return self.assigned_orders < self.max_daily_assignments

    def __str__(self):
        return f"Delivery Personnel: {self.profile.user.username} - {self.vehicle_type or 'Unknown vehicle'}"

    class Meta:
        permissions = [
            ("can_manage_deliveries", "Can manage deliveries"),
            ("can_edit_own_profile", "Can edit own profile"),
        ]

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
    
    def __str__(self):
        customer_username = self.order.customer.user.username if self.order.customer and self.order.customer.user else 'Unknown Customer'
        return f"Invoice {self.id} - Customer: {customer_username}"


class SalesReport(models.Model):
    product_name = models.CharField(max_length=255)
    units_sold = models.IntegerField()
    total_sales = models.DecimalField(max_digits=10, decimal_places=2)
    sale_date = models.DateTimeField()

    def __str__(self):
        return  f"{self.product_name} - {self.units_sold} units sold -c{self.total_sales} - {self.sale_date}"


class UserActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=255)
    order = models.ForeignKey('Order', on_delete=models.CASCADE, null=True, blank=True)  
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.action} on {self.timestamp}"
    

class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)], default=5)
    comment = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('product', 'customer')

    def __str__(self):
        return f'Review for {self.product} by {self.customer}'