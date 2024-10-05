from django import forms
from django.contrib.auth.models import User
from .models import Profile, Vendor, Product, Order,OrderItem,Delivery,DeliveryPersonnel, Customer,  Category, Subcategory, Cart, Review
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

class UserRegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()  
        return user

class LoginForm(forms.Form):
    username = forms.CharField(max_length=100)
    password = forms.CharField(widget=forms.PasswordInput)


class VendorForm(forms.ModelForm):
    class Meta:
        model = Vendor
        fields = ['business_name', 'business_address', 'phone']

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name','description', 'price', 'stock', 'category', 'subcategory']

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']

class SubcategoryForm(forms.ModelForm):
    class Meta:
        model = Subcategory
        fields = ['category', 'name']

class CartForm(forms.ModelForm):
    class Meta:
        model = Cart
        fields = ['customer','product', 'quantity']

class DeliveryForm(forms.ModelForm):
    class Meta:
        model = Delivery
        fields = ['order', 'delivery_partner', 'address', 'status', 'scheduled_at', 'delivered_at']

class DeliveryPersonnelForm(forms.ModelForm):
    class Meta:
        model = DeliveryPersonnel
        fields = ['vehicle_type', 'vehicle_number', 'phone', 'address']  
        widgets = {
            'vehicle_type': forms.TextInput(attrs={'placeholder': 'Type of vehicle'}),
            'vehicle_number': forms.TextInput(attrs={'placeholder': 'Vehicle number'}),
            'phone': forms.TextInput(attrs={'placeholder': 'Phone number', 'maxlength': 10}),
            'address': forms.Textarea(attrs={'placeholder': 'Address'}),
        }

class OrderStatusForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['status','delivery_partner']

class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ['order', 'product', 'quantity', 'price']

class CustomerForm(forms.ModelForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'Email'}))  # User's email field

    class Meta:
        model = Customer  
        fields = ['address', 'phone_number']  # Only Customer fields

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)  
        super().__init__(*args, **kwargs)
        
        if self.user:
            self.fields['email'].initial = self.user.email  

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Check if the email already exists for another user
        if User.objects.filter(email=email).exclude(id=self.user.id).exists():
            raise ValidationError("A user with this email already exists.")
        return email


    def save(self, commit=True):
        # Save email field to the User model
        if self.user:
            self.user.email = self.cleaned_data['email']
            self.user.save()

        # Update the Customer instance and save
        customer = super().save(commit=commit)

        # Update the Profile model with the same phone_number and address
        if self.user and hasattr(self.user, 'profile'):
            profile = self.user.profile
            profile.phone_number = self.cleaned_data['phone_number']  # Sync phone number
            profile.address = self.cleaned_data['address']  # Sync address
            profile.save()  # Save the updated profile data

        return customer


class CheckoutForm(forms.Form):
    delivery_address = forms.CharField(widget=forms.Textarea, max_length=500)
    phone_number = forms.CharField(max_length=15)


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.RadioSelect(choices=[(i, str(i)) for i in range(1, 6)]),
            'comment': forms.Textarea(attrs={'rows': 4}),
        }