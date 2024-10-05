from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User,Admin, Profile, Product, OrderItem,Order,SalesReport,UserActivity, Delivery,DeliveryPersonnel, Category, Subcategory, Cart, Vendor, Customer, Invoice, Review, Order


class UserAdmin(BaseUserAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2'),
        }),
    )
    
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ('username', 'password')
        return self.readonly_fields

# Unregister the default User admin and register the customized one
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

# Registering other models
admin.site.register(Admin)
admin.site.register(DeliveryPersonnel)
admin.site.register(Profile)
admin.site.register(Product)
admin.site.register(OrderItem)
admin.site.register(Category)
admin.site.register(Subcategory)
admin.site.register(UserActivity)
admin.site.register(Vendor)
admin.site.register(Customer)
admin.site.register(Delivery)
admin.site.register(Review)

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    fields = ['product', 'quantity', 'price']

class DeliveryInline(admin.TabularInline):
    model = Delivery
    extra = 1
    fields = ['delivery_partner', 'status', 'scheduled_at', 'delivered_at']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'vendor', 'total_amount', 'status', 'delivery_partner', 'ordered_at','get_delivered_at')
    actions = ['assign_delivery_partner']
    inlines = [OrderItemInline, DeliveryInline] 

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by('-ordered_at')  # Display orders in descending order

    def assign_delivery_partner(self, request, queryset):
        for order in queryset:
            available_partners = Profile.objects.filter(role='Delivery Personnel')  
            if available_partners.exists():
                order.delivery_partner = available_partners.first()  
                order.save()
                Delivery.objects.create(order=order, delivery_personnel=order.delivery_partner, address=order.delivery_address)
                self.message_user(request, f"Assigned delivery partner to Order #{order.id}.")
            else:
                self.message_user(request, "No delivery partners available.")

    assign_delivery_partner.short_description = "Assign selected orders to a delivery partner"


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'customer_name', 'invoice_date', 'amount', 'email_sent') 

    def customer_name(self, obj):
        return obj.order.customer  

    customer_name.short_description = 'Customer'  


class SalesReportAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'units_sold', 'total_sales', 'sale_date')
    readonly_fields = ('units_sold', 'total_sales') 

    def save_model(self, request, obj, form, change):
        # Prevent automatic update of units_sold and total_sales in the admin
        if not change:
            # If it's a new object, proceed with saving
            super().save_model(request, obj, form, change)
        else:
            # If it's an existing object, do not modify units_sold or total_sales
            old_obj = SalesReport.objects.get(pk=obj.pk)
            obj.units_sold = old_obj.units_sold
            obj.total_sales = old_obj.total_sales
            super().save_model(request, obj, form, change)

admin.site.register(SalesReport, SalesReportAdmin)

class CartAdmin(admin.ModelAdmin):
    list_display = ('customer', 'product', 'quantity')
    search_fields = ('customer__user__username', 'product__name') 

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs  

admin.site.register(Cart,CartAdmin)