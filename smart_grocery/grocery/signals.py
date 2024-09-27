from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from .models import Profile, Order, Vendor, Customer
from django.contrib.auth.models import User

# Signal to create user profile when a User instance is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
        Customer.objects.create(user=instance)  # Create Customer profile as well

# Signal to save user profile whenever User instance is saved
@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

# Signal to send an email when an Order's status changes
@receiver(post_save, sender=Order)
def order_status_changed(sender, instance, created, **kwargs):
    if created:  # Check if the order is newly created
        vendor = instance.vendor
        if vendor and vendor.profile and vendor.profile.user:
            send_mail(
                'Order Status Updated',
                f'Your order {instance.id} status has been updated to {instance.status}.',
                'ashwithar2001@gmail.com',
                [vendor.profile.user.email],
                fail_silently=False,
            )

# Signal to save user customer profile whenever User instance is saved
@receiver(post_save, sender=User)
def save_user_customer(sender, instance, **kwargs):
    try:
        instance.customer.save()  # Save the Customer instance if it exists
    except Customer.DoesNotExist:
        print(f"No Customer profile found for user: {instance.username}")
