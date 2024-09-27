from django.contrib import admin
from .models import Profile, Product, Order,OrderItem,Delivery, Vendor, Invoice,Customer, Category, Subcategory, Cart, Review
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _


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
    search_fields = ('username','email','first_name', 'last_name' )
    ordering = ('username',)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ('username', 'password')
        return self.readonly_fields

# Unregister the default User admin and register the customized one
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


admin.site.register(Profile)
admin.site.register(Product)

admin.site.register(OrderItem)
admin.site.register(Delivery)
admin.site.register(Category)
admin.site.register(Subcategory)
admin.site.register(Cart)
admin.site.register(Vendor)
admin.site.register(Customer)
admin.site.register(Invoice)
admin.site.register(Review)



@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'total_amount', 'status', 'delivery_partner')
    actions = ['assign_delivery_partner']

    def assign_delivery_partner(self, request, queryset):
        for order in queryset:
            # Logic to assign a delivery partner
            available_partners = Profile.objects.filter(role='Delivery Partner')  # Example query
            if available_partners.exists():
                order.delivery_personnel = available_partners.first()  # Assign first available partner
                order.save()
                # Optionally create a Delivery record
                Delivery.objects.create(order=order, delivery_personnel=order.delivery_personnel, address=order.delivery_address)
            else:
                self.message_user(request, "No delivery partners available.")

    assign_delivery_partner.short_description = "Assign selected orders to a delivery partner"