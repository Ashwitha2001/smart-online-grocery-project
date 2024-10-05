from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test, permission_required
from django.http import (HttpResponse, JsonResponse,  HttpResponseNotFound, HttpResponseBadRequest)
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.forms import  UserCreationForm, PasswordResetForm
from .forms import LoginForm
from django.contrib.auth.views import (PasswordResetView, PasswordResetDoneView, 
                                       PasswordResetConfirmView, PasswordResetCompleteView)
from django.core.cache import cache
from django.core.mail import send_mail, EmailMessage
from django.urls import reverse
from django.middleware.csrf import get_token
from django.utils import timezone
from django.db.models import Q, Avg, Sum, F
from django.core.files.base import ContentFile
from django.conf import settings
from decimal import Decimal
import razorpay

from .models import (Profile,Admin, Product, Category, Subcategory, Customer, Order,SalesReport,
                     OrderItem, Cart, Delivery,DeliveryPersonnel, Vendor, Invoice, Review, UserActivity)
from .forms import (UserRegistrationForm,VendorForm, ProductForm, CustomerForm,DeliveryPersonnelForm)
from .utils import generate_invoice
from django.db import models
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from reportlab.lib.pagesizes import letter


@login_required
def home(request):
    try:
        profile = request.user.profile
    except AttributeError:
        return redirect('access-denied')  

    role = profile.role

    if role == 'admin':
        return redirect('admin_dashboard')
    elif role == 'vendor':
        return redirect('vendor_dashboard')
    elif role == 'delivery_personnel':
        return redirect('delivery_personnel_dashboard')
    elif role == 'customer':
        # Ensure the customer profile exists
        try:
            customer = Customer.objects.get(user=request.user)
        except Customer.DoesNotExist:
            # Automatically create a Customer profile if it doesn't exist
            return redirect('create_customer_profile')

        # Fetch products, categories, and cart items
        products = Product.objects.all()

        query = request.GET.get('q')
        if query:
            products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))

        category_id = request.GET.get('category')
        if category_id:
            products = products.filter(category_id=category_id)

        price_min = request.GET.get('price_min')
        price_max = request.GET.get('price_max')

        if price_min:
            products = products.filter(price__gte=price_min)
        if price_max:
            products = products.filter(price__lte=price_max)


        categories = Category.objects.all()
        cart_items = Cart.objects.filter(customer=customer)

        return render(request, 'home.html', {
            'products': products,
            'categories': categories,
            'cart_items': cart_items,
            'customer': customer,
            'query': query,
            'category_id': category_id,
            'price_min': price_min,
            'price_max': price_max,
        })
    else:
        return redirect('access-denied')  


def profile(request):
    return render(request, 'profile.html')


# Admin Registration
@csrf_exempt
def register_admin(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
           
              # Check if profile exists, or create one with role 'vendor'
            profile, created = Profile.objects.get_or_create(user=user, defaults={'role': 'admin'})

            if not created:
                profile.role = 'admin'
                profile.save()

            return redirect('login')
    else:
        form = UserRegistrationForm()

    return render(request, 'registration/register_admin.html', {'form': form})


# Vendor Registration
@csrf_exempt
def register_vendor(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
              # Check if profile exists, or create one with role 'vendor'
            profile, created = Profile.objects.get_or_create(user=user, defaults={'role': 'vendor'})

            if not created:
                profile.role = 'vendor'
                profile.save()

            return redirect('login')  
    else:
        form = UserRegistrationForm()

    return render(request, 'registration/register_vendor.html', {'form': form})


# Delivery Personnel Registration
@csrf_exempt
def register_delivery_personnel(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()

              # Check if profile exists, or create one with role 'vendor'
            profile, created = Profile.objects.get_or_create(user=user, defaults={'role': 'delivery_personnel'})

            if not created:
                profile.role = 'delivery_personnel'
                profile.save()

            return redirect('login')
    else:
        form = UserRegistrationForm()

    return render(request, 'registration/register_delivery_personnel.html', {'form': form})

# Customer Registration
@csrf_exempt
def register_customer(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
           
            
            # Check if a profile already exists for the user
            profile, created = Profile.objects.get_or_create(user=user, defaults={'role': 'customer'})

            if not created:
                # If a profile exists, update the role if necessary
                profile.role = 'customer'
                profile.save()

            return redirect('login')
    else:
        form = UserRegistrationForm()

    return render(request, 'registration/register_customer.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)

                # Access the user profile
                try:
                    profile = user.profile  
                    role = profile.role

                    # Check if user profile is already complete
                    if role == 'vendor' and not hasattr(profile, 'vendor'):
                        return redirect('create_vendor_profile')  
                    elif role == 'delivery_personnel' and not hasattr(profile, 'deliverypersonnel'):
                        return redirect('create_delivery_personnel_profile')  
                    elif role == 'admin' and not hasattr(profile, 'admin'):
                        return redirect('create_admin_profile')
                    elif role == 'customer' and not hasattr(profile, 'customer'):
                        return redirect('create_customer_profile')  
                    else:
                        # If profile already exists, redirect to their respective dashboard
                        if role == 'vendor':
                            return redirect('vendor_dashboard')
                        elif role == 'delivery_personnel':
                            return redirect('delivery_personnel_dashboard')
                        elif role == 'admin':
                            return redirect('admin_dashboard')
                        elif role == 'customer':
                            return redirect('home')
                except Profile.DoesNotExist:
                    messages.error(request, 'No profile found for this user. Please create one.')
                    return redirect('create_profile') 

            else:
                messages.error(request, 'Invalid username or password.')
                return redirect('login') 

    else:
        form = LoginForm()
    
    return render(request, 'registration/login.html', {'form': form})

@csrf_exempt
@login_required
def create_vendor_profile(request):
    if request.method == 'POST':
        business_name = request.POST.get('business_name')
        business_address = request.POST.get('business_address')
        user = request.user

        profile = Profile.objects.get(user=user)
        Vendor.objects.create(
            profile=profile,
            business_name=business_name,
            business_address=business_address
        )
        return redirect('vendor_dashboard')

    return render(request, 'registration/create_vendor_profile.html')

@csrf_exempt
@login_required
def create_delivery_personnel_profile(request):
    if request.method == 'POST':
        address = request.POST.get('address')
        phone = request.POST.get('phone')
        vehicle_type = request.POST.get('vehicle_type')
        vehicle_number = request.POST.get('vehicle_number')
        user = request.user

        profile = Profile.objects.get(user=user)
        DeliveryPersonnel.objects.create(
            profile=profile,
            address=address,
            phone=phone,
            vehicle_type=vehicle_type,
            vehicle_number=vehicle_number
        )
        return redirect('delivery_personnel_dashboard')

    return render(request, 'registration/create_delivery_personnel_profile.html')


@csrf_exempt
@login_required
def create_admin_profile(request):
    user = request.user
    profile = Profile.objects.get(user=user)

    if request.method == 'POST':
        permission_level = request.POST.get('permission_level')
        Admin.objects.create(
            profile=profile,
            permission_level=permission_level
        )
        return redirect('admin_dashboard')

    return render(request, 'registration/create_admin_profile.html')

@csrf_exempt
@login_required
def create_customer_profile(request):
    customer, created = Customer.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Customer profile updated successfully!')
            return redirect('home')
    else:
        form = CustomerForm(instance=customer, user=request.user)

    return render(request, 'registration/create_customer_profile.html', {'form': form})


@login_required
def logout_view(request):
    print("Logout view accessed")
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('login')


def password_reset(request):
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            form.save(request=request, email_template_name='registration/password_reset_email.html')
            messages.success(request, 'Password reset email sent.')
            return redirect('password_reset_done')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordResetForm()
    return render(request, 'registration/password_reset_form.html', {'form': form})

def password_reset_done(request):
    return render(request, 'registration/password_reset_done.html')

def password_reset_confirm(request, uidb64, token):
    return PasswordResetConfirmView.as_view()(request, uidb64=uidb64, token=token)

def password_reset_complete(request):
    return PasswordResetCompleteView.as_view()(request)


def is_admin(user):
    return user.is_authenticated and (user.profile.role == 'admin' or user.is_superuser)

def is_vendor_or_admin(user):
    return user.is_authenticated and (user.profile.role == 'vendor' or user.is_superuser)

def is_delivery_personnel_or_admin(user):
    return user.is_authenticated and (user.profile.role == 'delivery_personnel' or user.is_superuser)

def is_customer_or_admin(user):
    return user.is_authenticated and (user.profile.role == 'customer' or user.is_superuser)

@login_required
@user_passes_test(is_admin, login_url='/grocery/access-denied/')
def admin_dashboard(request):
    products = Product.objects.all()
    vendors = Vendor.objects.all()
    customers = Customer.objects.all()
    delivery_partners = Profile.objects.filter(role='delivery_personnel')
    orders = Order.objects.all()

    # Count total orders
    order_count = orders.count()
    
    # Count total deliveries: all orders that have been delivered
    delivered_orders_count = orders.filter(status='Delivered').count()
    
    # Remaining deliveries: total orders minus delivered orders
    remaining_deliveries = order_count - delivered_orders_count
    
    # Sales report: calculate total sales
    total_sales = sum(order.total_amount for order in orders)

    context = {
        'product_count': products.count(),
        'products': products,
        'total_users': User.objects.count(),
        'total_orders': order_count,
        'total_products': products.count(),
        'vendor_count': vendors.count(),
        'customer_count': customers.count(),
        'delivery_personnel_count': delivery_partners.count(),
        'orders': orders,
        'delivery_count': remaining_deliveries, 
        'delivery_partners': delivery_partners,  
         'total_sales': total_sales
    }

    return render(request, 'admin_dashboard.html', context)
    

@login_required
@user_passes_test(is_vendor_or_admin, login_url='/grocery/access-denied/')
def vendor_dashboard(request):
    if request.user.profile.role == 'vendor':
        vendor = get_object_or_404(Vendor, profile=request.user.profile)
        vendor_products = Product.objects.filter(vendor=vendor)

         # Get orders specific to the vendor
        vendor_orders = Order.objects.filter(vendor=vendor).order_by('-ordered_at')

    else:
        vendor_products = Product.objects.all()  # Admin view all products
    
        vendor_orders = Order.objects.all().order_by('-ordered_at')


    context = {
         'welcome_message': f"Welcome, {request.user.username}", 
        'vendor_products': vendor_products,
        'product_count': vendor_products.count(),
        'orders': vendor_orders,
        'order_count': vendor_orders.count(),
    }
    return render(request, 'vendor_dashboard.html', context)


@login_required
@user_passes_test(is_customer_or_admin, login_url='/grocery/access-denied/')
def customer_dashboard(request):
    # Check if the user is a customer or admin
    if request.user.profile.role == 'customer' or is_admin(request.user):
        if is_admin(request.user):
            # Admin sees all customer orders
            customer_orders = Order.objects.all().order_by('-ordered_at')
        else:
            # Customer sees their own orders
            customer = get_object_or_404(Customer, user=request.user)
            customer_orders = Order.objects.filter(customer=customer).order_by('-ordered_at')

        # Get the total number of orders and deliveries
        order_count = customer_orders.count()
        delivery_count = customer_orders.filter(status='Delivered').count()  # Count deliveries

        context = {
            'orders': customer_orders,
            'order_count': order_count,
            'delivery_count': delivery_count,
        }
        return render(request, 'customer_dashboard.html', context)

    return redirect('admin_dashboard') if is_admin(request.user) else redirect('vendor_dashboard')


@login_required
@user_passes_test(is_delivery_personnel_or_admin, login_url='/grocery/access-denied/')
def delivery_personnel_dashboard(request):
    if request.user.profile.role == 'delivery_personnel' or is_admin(request.user):
        if is_admin(request.user):
            delivery_orders = Order.objects.all().select_related('customer', 'vendor')
        else:
            delivery_orders = Order.objects.filter(delivery_partner=request.user.profile).select_related('customer', 'vendor')

        # Get the total number of orders and deliveries
        order_count = delivery_orders.count()  # Count orders for this specific delivery personnel
        delivery_count = delivery_orders.filter(status='Delivered').count() 

        if request.method == 'POST':
            order_id = request.POST.get('order_id')
            new_status = request.POST.get('status')
            try:
                order = Order.objects.get(id=order_id, delivery_partner=request.user.profile)
                order.status = new_status
                order.save()
                messages.success(request, f'Status updated for Order ID {order_id}.')
            except Order.DoesNotExist:
                messages.error(request, 'Order not found or you do not have permission to update it.')

        context = {
            'welcome_message': f"Welcome, {request.user.username} ",
            'delivery_orders': delivery_orders.order_by('-ordered_at'),
            'order_count': order_count,
            'delivery_count': delivery_count,
        }
        return render(request, 'delivery_personnel_dashboard.html', context)

    return redirect('admin_dashboard') if is_admin(request.user) else redirect('vendor_dashboard')


    
@login_required
@user_passes_test(is_vendor_or_admin, login_url='/grocery/access-denied/')
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('product_list')
    else:
        form = ProductForm()

    return render(request, 'add_product.html', {'form': form})



@login_required
@user_passes_test(is_vendor_or_admin, login_url='/grocery/access-denied/')
def update_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)

    return render(request, 'update_product.html', {'form': form})


@login_required
@user_passes_test(is_vendor_or_admin, login_url='/grocery/access-denied/')
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == "POST":
        product.delete()
        messages.success(request, "Product deleted successfully!")
        return redirect('product_list') 
    
    return render(request, 'delete_product.html', {'product': product})



def categories_view(request):
    categories = Category.objects.all()
    return render(request, 'categories.html', {
        'categories': categories
    })


@login_required
def category_detail(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    products = Product.objects.filter(subcategory__category=category)
    
    return render(request, 'category_detail.html', {
        'category': category,
        'products': products,
    })


@login_required
def category_list(request):
    categories = Category.objects.prefetch_related('subcategories').all()
    return render(request, 'categories.html', {'categories': categories})


@login_required
def subcategory_products(request, subcategory_id):
    subcategory = get_object_or_404(Subcategory, id=subcategory_id)
    products = Product.objects.filter(subcategory=subcategory)
    
    # Get total quantity of items in the cart
    total_quantity = Cart.objects.filter(customer=request.user.customer).aggregate(
        total_quantity=Sum('quantity')
    )['total_quantity'] or 0
    
    return render(request, 'subcategory_products.html', {
        'subcategory': subcategory,
        'products': products,
        'total_cart_quantity': total_quantity,
    })



def product_list(request):
    # Define cache key based on the search and filter parameters
    cache_key = f"product_list_{request.GET.get('q', '')}_{request.GET.get('category', '')}_{request.GET.get('price_min', '')}_{request.GET.get('price_max', '')}"

    # Check if the results are in cache
    products = cache.get(cache_key)

    if not products:
        # Get all products initially if not cached
        products = Product.objects.all()

        # Get the search query
        query = request.GET.get('q')
        if query:
            products = products.filter(name__icontains=query)

        # Get the category filter
        category_id = request.GET.get('category')
        if category_id:
            products = products.filter(category_id=category_id)

        # Get price filters
        price_min = request.GET.get('price_min')
        price_max = request.GET.get('price_max')

        if price_min:
            products = products.filter(price__gte=price_min)
        if price_max:
            products = products.filter(price__lte=price_max)

        # Cache the filtered product list for 15 minutes
        cache.set(cache_key, products, timeout=60*15)

    # Get all categories for the filter dropdown
    categories = Category.objects.all()

    context = {
        'products': products,
        'categories': categories,
        'query': request.GET.get('q', ''),
        'category_id': request.GET.get('category', ''),
        'price_min': request.GET.get('price_min', ''),
        'price_max': request.GET.get('price_max', ''),
    }

    return render(request, 'product_list.html', context)



def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    reviews = product.reviews.all().order_by('-created_at')
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0

    return render(request, 'product_detail.html', {
        'product': product,
        'reviews': reviews,
        'avg_rating': avg_rating,
    })


@login_required
def update_cart_button(request):
    customer = Customer.objects.get(user=request.user)
    cart_items = Cart.objects.filter(customer=customer)
    total_quantity = cart_items.aggregate(total_quantity=models.Sum('quantity'))['total_quantity'] or 0
    total_amount = cart_items.aggregate(total_amount=models.Sum(models.F('quantity') * models.F('product__price')))['total_amount'] or 0
    return JsonResponse({'total_quantity': total_quantity, 'total_amount': total_amount})


@csrf_exempt
@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get('quantity', 1))

    if quantity <= 0:
        return JsonResponse({'message': 'Invalid quantity'}, status=400)
    
    print(f"Adding {quantity} of {product.name} to cart for {request.user.customer}")
    
    # Check if the cart already has this product
    cart_item, created = Cart.objects.get_or_create(
        customer=request.user.customer, product=product, defaults={'quantity': 0}
    )
    
    cart_item.quantity = quantity
    
    cart_item.save()

    print(f"Cart item saved: {cart_item}")

    # Calculate total quantity of products in the cart
    total_quantity = Cart.objects.filter(customer=request.user.customer).aggregate(
        total_quantity=Sum('quantity')
    )['total_quantity'] or 0

    return JsonResponse({'message': 'Product added to your cart', 'total_quantity': total_quantity})


@login_required
def view_cart(request):
    cart_items = Cart.objects.filter(customer=request.user.customer)

    # Calculate total quantity and total amount
    total_quantity = cart_items.aggregate(total_quantity=Sum('quantity'))['total_quantity'] or 0

    # Initialize total amount
    total_amount = 0

    # Calculate total price for each cart item (quantity * price per unit)
    for item in cart_items:
        print(f'Item ID: {item}, Quantity: {item.quantity}, Price: {item.product.price}')
        if item.quantity is not None and item.product.price is not None:
            item.total_price = item.quantity * item.product.price
            total_amount += item.total_price 
        else:
            item.total_price = 0  # Assign zero if quantity or price is None
    
    # Store total amount in session
    request.session['total_amount'] = float(total_amount)

    return render(request, 'view_cart.html', {
        'cart_items': cart_items,
        'total_quantity': total_quantity,
        'total_amount': total_amount
    })


@csrf_exempt
@login_required
@require_POST
def remove_from_cart(request, cart_item_id):
    if request.method == 'POST':
        cart_item = Cart.objects.filter(id=cart_item_id, customer=request.user.customer).first()
        
        if cart_item:
            cart_item.delete()
        return redirect('view_cart')  
    return redirect('view_cart')


@login_required
def checkout(request):
    if request.method == 'POST':
        address = request.POST.get('address')
        phone_number = request.POST.get('phone_number')

        # Validate address and phone number
        if not address or not phone_number:
            return render(request, 'checkout.html', {
                'error': 'Address and phone number are required.',
                'total_amount': request.session.get('total_amount', 0),
                'customer': request.user.customer if request.user.is_authenticated else None
            })

        customer = request.user.customer
        if not customer:
            return redirect('create_customer_profile')
        
        # Update customer's address and phone number
        customer.address = address
        customer.phone_number = phone_number
        customer.save()

        # Fetch cart items
        cart_items = Cart.objects.filter(customer=customer)
        if not cart_items.exists():
            return render(request, 'checkout.html', {
                'error': 'No products found in the cart.',
                'total_amount': request.session.get('total_amount', 0),
                'customer': customer
            })

        vendor = cart_items.first().product.vendor
        
        # Create the order first
        order = Order.objects.create(
            customer=customer,
            vendor=vendor,
            total_amount=request.session.get('total_amount', 0),
            status='Placed',
        )

        print(f"Order created at: {order.ordered_at}")

        # Check stock availability and create order items
        for item in cart_items:
            print(f"Product: {item.product.name}, Stock: {item.product.stock}, Quantity: {item.quantity}")

            # Handle None or invalid quantity
            quantity = item.quantity if item.quantity is not None and item.quantity > 0 else 0
            
            # Ensure stock is checked properly
            stock = item.product.stock or 0
            
            if stock < quantity:
                return render(request, 'checkout.html', {
                    'error': f"Only {stock} units of {item.product.name} are available.",
                    'total_amount': request.session.get('total_amount', 0),
                    'customer': customer
                })

            # Create the order item only if quantity is valid
            if quantity > 0:
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=quantity,
                    price=item.product.price
                )

                # Reduce the stock after order confirmation
                item.product.stock -= quantity
                item.product.save()

                 # **Update the SalesReport here**
                sales_report, created = SalesReport.objects.get_or_create(
                    product_name=item.product.name,
                    sale_date=timezone.now().date(),
                    defaults={'units_sold': 0, 'total_sales': 0}
                )

                # Update the sales report values
                sales_report.units_sold += quantity
                sales_report.total_sales += quantity * item.product.price
                sales_report.save()


            else:
                print(f"Invalid quantity for {item.product.name}, skipping order item creation.")

        # Clear cart after order is placed
        cart_items.delete()

        # Clear the total amount from session
        del request.session['total_amount']
        
        # Log the activity
        UserActivity.objects.create(
            user=request.user,
            action='Placed an order',
            order=order,  
            timestamp=timezone.now()
        )
        print(f"User Activity Logged: {request.user} - Placed an order at {timezone.now()}")

        # Send Notifications after order creation
        send_order_confirmation_email(request.user, order)
        send_order_confirmation_sms(request.user, order)
        send_push_notification(request.user, f'Your order #{order.id} has been placed!')

        return redirect('order_success', order_id=order.id)

    else:
        customer = request.user.customer if request.user.is_authenticated else None
        total_amount = request.session.get('total_amount', 0)
        
        # Convert total_amount back to Decimal
        if isinstance(total_amount, float):
            total_amount = Decimal(str(total_amount))

        return render(request, 'checkout.html', {
            'total_amount': total_amount,
            'customer': customer
        })


def order_success(request, order_id):
    order = Order.objects.get(id=order_id)
    return render(request, 'order_success.html', {'order': order})


@login_required
def order_detail(request, order_id):
    try:
        # Ensure the user has a Customer profile
        customer_profile = request.user.customer
    except Customer.DoesNotExist:
        return redirect('home')  

    try:
        # Fetch the order for the logged-in user's customer
        order = Order.objects.get(id=order_id, customer=customer_profile)
        order_items = OrderItem.objects.filter(order=order)
        
        # Fetch the latest Delivery object related to this order
        delivery = Delivery.objects.filter(order=order).last()  
        delivery_partner = delivery.delivery_partner if delivery else None
        delivered_at = delivery.delivered_at if delivery else None  
    except Order.DoesNotExist:
        return redirect('home')  
    
    # Define the list of past statuses
    statuses = ['Placed', 'Processing', 'Shipped', 'Out for Delivery', 'Delivered', 'Canceled']

    past_statuses = statuses[:statuses.index(order.status) + 1]

    return render(request, 'order_detail.html', {
        'order': order,
        'order_items': order_items,
        'delivery_partner': delivery_partner,  
        'statuses': statuses,
        'past_statuses': past_statuses,
        'delivered_at': delivered_at 
    })

@csrf_exempt
@login_required
def update_order_status(request, order_id):
    if request.method == 'POST':
        try:
            data = request.POST  
            new_status = data.get('status')

            if not new_status:
                return HttpResponseBadRequest('Status not provided')

            # Update order and delivery status
            order = Order.objects.get(id=order_id)
            delivery = Delivery.objects.get(order=order)
            
            delivery.status = new_status
            order.status = new_status
            
            # Update timestamps based on the status change
            if new_status == 'Out for Delivery':
                delivery.scheduled_at = timezone.now()  # Set scheduled_at to current time when scheduled
            elif new_status == 'Delivered':
                delivery.delivered_at = timezone.now()  # Set delivered_at to current time when delivered

            delivery.save()
            order.save()

            print(f"Order {order_id} has been updated to status: {new_status}")
            
            # Send email notification to the customer
            customer = order.customer
            if customer is None or customer.user is None:
                return HttpResponseBadRequest('Customer or associated user not found')


            # Send email notification to the customer
            send_mail(
                subject='Order Status Update',
                message=f'Your order with ID {order} has been updated to "{new_status}".',
                from_email='ashwithar2001@gmail.com', 
                recipient_list=[customer.user.email],  # Send email to customer
                fail_silently=False,
            )
            
            return redirect('delivery_personnel_dashboard')  
        except Order.DoesNotExist:
            return HttpResponseNotFound('Order not found')
        except Delivery.DoesNotExist:
            return HttpResponseNotFound('Delivery not found')
    else:
        return HttpResponseBadRequest('Invalid request method')


@login_required
def order_history(request):
    customer_profile = request.user.customer 
    orders = Order.objects.filter(customer=customer_profile).order_by('-ordered_at')

    return render(request, 'order_history.html', {'orders': orders})


@login_required
@user_passes_test(is_admin, login_url='/grocery/access-denied/')
def delivery_management(request):
    orders = Order.objects.filter(delivery_partner__isnull=True).order_by('-ordered_at')  

    return render(request, 'delivery_management.html', {'orders': orders})


@login_required
@user_passes_test(is_admin, login_url='/grocery/access-denied/')
def assign_delivery_partner(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    delivery_partners = Profile.objects.filter(role='delivery_personnel')

    if request.method == 'POST':
        partner_id = request.POST.get('delivery_partner')
        if partner_id:
            try:
                delivery_partner = Profile.objects.filter(id=partner_id, role='delivery_personnel').last()

                if not delivery_partner:
                    return render(request, 'assign_delivery_partner.html', {
                        'order': order,
                        'delivery_partners': delivery_partners,
                        'error': 'Delivery partner not found.'
                    })

                # Check the number of undelivered orders
                pending_orders_count = Delivery.objects.filter(delivery_partner=delivery_partner, status__in=['Placed', 'Processing', 'Shipped', 'Out for Delivery']).count()

                # Define the max limit of orders a delivery partner can handle (e.g., 10)
                MAX_ORDERS = 10

                if pending_orders_count >= MAX_ORDERS:
                    return render(request, 'assign_delivery_partner.html', {
                        'order': order,
                        'delivery_partners': delivery_partners,
                        'error': f'{delivery_partner.user.get_full_name()} already has {pending_orders_count} pending orders and cannot take more.'
                    })

                # Assign the delivery partner
                order.delivery_partner = delivery_partner
                order.save()  
                
                # Handle delivery creation or update
                delivery, created = Delivery.objects.update_or_create(
                    order=order,
                    defaults={
                        'delivery_partner': delivery_partner,
                        'address': order.customer.address
                    }
                )

                return redirect('order_detail', order_id=order.id) 

            except Profile.DoesNotExist:
                return render(request, 'assign_delivery_partner.html', {
                    'order': order,
                    'delivery_partners': delivery_partners,
                    'error': 'Selected delivery partner does not exist.'
                })

    return render(request, 'assign_delivery_partner.html', {
        'order': order,
        'delivery_partners': delivery_partners
    })


@login_required
def update_delivery_status(request, order_id):
    if request.method == 'POST':
        order = Order.objects.get(id=order_id)
        order.status = request.POST['status']
        order.save()

        # Send WebSocket message
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return HttpResponse('Channel layer is not available.', status=500)
        
        async_to_sync(channel_layer.group_send)(
            'delivery_status',
            {
                'type': 'send_status_update',
                'orderId': order,
                'status': order.status,
            }
        )
        
        return HttpResponse('Delivery status updated successfully.')  
    else:
        return HttpResponse('Invalid request method.', status=400)
    


def order_tracking(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'order_tracking.html', {'order': order})


def access_denied(request):
    return render(request, 'access_denied.html')


@csrf_exempt
@login_required
def proceed_to_payment(request, order_id):
    if request.method == "POST":
        try:
            # Fetch the order for the logged-in user's customer
            order = Order.objects.get(id=order_id, customer=request.user.customer)

            # Ensure the order status is 'Out for Delivery'
            if order.status != 'Out for Delivery':
                return HttpResponse("Payment is only available when the order is 'Out for Delivery'.")

            # Fetch total amount from the existing order (not from the cart)
            total_amount = order.total_amount

            # Check if the total amount is valid (not zero)
            if total_amount <= 0:
                return HttpResponse("Invalid order amount.")

            # Initialize Razorpay client
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_SECRET_KEY))

            # Create an order with Razorpay
            razorpay_order = client.order.create(dict(
                amount=int(total_amount * 100),  # Amount in paise (100 paise = 1 INR)
                currency='INR',
                receipt=str(order),
                payment_capture='1'  
            ))

            # Save the Razorpay order ID in the existing order
            order.razorpay_order_id = razorpay_order['id']
            order.save()

            # Get CSRF token for secure payment request
            csrf_token = get_token(request)

            # Prepare context to pass to the frontend
            context = {
                'key_id': settings.RAZORPAY_KEY_ID,
                'amount': total_amount * 100,  # Amount in paise
                'order_id': razorpay_order['id'],
                'currency': 'INR',
                'receipt': str(order),
                'total_amount': total_amount,
                'csrf_token': csrf_token
            }

            return render(request, 'proceed_to_payment.html', context)
        
        except Order.DoesNotExist:
            return redirect('home') 
        except Exception as e:
            return HttpResponse(f"An error occurred: {str(e)}")

    elif request.method == "GET" and 'razorpay_payment_id' in request.GET:
        razorpay_payment_id = request.GET['razorpay_payment_id']
        try:
            # Fetch the order again
            order = Order.objects.get(id=order_id, customer=request.user.customer)

            # Update order status to 'Delivered' after successful payment
            order.status = 'Delivered'
            order.save()

            return redirect('order_detail', order_id=order) 

        except Order.DoesNotExist:
            return redirect('home')
        except Exception as e:
            return HttpResponse(f"An error occurred during payment confirmation: {str(e)}")
    else:
        return redirect('home')


@csrf_exempt
def payment_success(request):
    if request.method == 'POST':
        razorpay_order_id = request.POST.get('razorpay_order_id')
        razorpay_payment_id = request.POST.get('razorpay_payment_id')
        razorpay_signature = request.POST.get('razorpay_signature')

        # Initialize Razorpay client
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_SECRET_KEY))
        
        # Verify payment signature
        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }
        try:
            client.utility.verify_payment_signature(params_dict)
        except Exception as e:
            return redirect('payment_failure')

        # Retrieve the order and update status
        try:
            order = Order.objects.get(razorpay_order_id=razorpay_order_id)
            order.status = 'Delivered'
            order.save()

            # Update the associated delivery record
            delivery = get_object_or_404(Delivery, order=order)
            delivery.status = 'Delivered'
            delivery.delivered_at = timezone.now() 
            delivery.save()

            # Generate and attach invoice as a PDF
            invoice_pdf = generate_invoice(order)
            invoice = Invoice(
                order=order,
                amount=order.total_amount,
                pdf_file=ContentFile(invoice_pdf, name=f'invoice_{order}.pdf')
            )
            invoice.save()

            # Get customer and ensure user exists
            customer = order.customer
            if not customer or not customer.user:
                messages.error(request, "Customer or User not found.")
                return redirect('home')

            # Send the invoice via email
            customer_email = customer.user.email
            email_subject = 'Your Invoice from Smart Grocery'
            email_body = 'Thank you for your purchase. Please find the attached invoice for your recent order.'
            email = EmailMessage(
                email_subject,
                email_body,
                settings.DEFAULT_FROM_EMAIL,
                [customer_email]
            )
            email.attach(f'invoice_{order}.pdf', invoice_pdf, 'application/pdf')

            if email.send():
                invoice.email_sent = True
                invoice.save()
            else:
                messages.error(request, "Failed to send invoice email.")
            
            # Clear the cart after successful payment
            Cart.objects.filter(customer=customer).delete()

            
            # Render the payment success template with product IDs
            return render(request, 'payment_success.html', {
                 'order': order,
               
            })
        
        except Order.DoesNotExist:
            messages.error(request, 'Order not found.')
            return redirect('home')
    else:
        return redirect('home')


def payment_failure(request):
    return render(request, 'payment_failure.html')


def send_order_confirmation_email(user, order):
    subject = 'Order Confirmation'
    message = f'Dear {user.first_name}, your order #{order.id} has been confirmed!'
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [user.email]  
    
    send_mail(subject, message, from_email, recipient_list)


def send_order_confirmation_sms(user, order):
    phone_number = user.profile.phone_number 
    message = f'Your order #{order.id} has been confirmed!'
    
    # Simulate SMS sending (print to console)
    print(f"Sending SMS to {phone_number}: {message}")


def send_push_notification(user, message):
    # Simulate sending a push notification
    print(f"Sending push notification to {user.username}: {message}") 


@login_required
@user_passes_test(is_admin, login_url='/grocery/access-denied/')
def sales_report(request):
    all_orders = Order.objects.prefetch_related('items__product').order_by('-ordered_at')

    sales_data = []
    total_sales_amount = 0

    for order in all_orders:
        for item in order.items.all():
            if item.product and item.quantity > 0:
                # Prepare the sales data
                product_name = item.product.name
                units_sold = item.quantity
                total_sales = item.price * item.quantity

                # Append to the sales data list for display in template
                sales_data.append({
                    'product_name': product_name,
                    'units_sold': units_sold,
                    'total_sales': total_sales,
                    'sale_date': order.ordered_at
                })

                total_sales_amount += total_sales

                # Check if the report already exists for the product and sale date
                report, created = SalesReport.objects.get_or_create(
                    product_name=product_name,
                    sale_date=order.ordered_at,
                    defaults={'units_sold': units_sold, 'total_sales': total_sales}
                )

                # If the report already exists, update the fields correctly
                if not created:  # The report already existed
                    report.units_sold += units_sold
                    report.total_sales += total_sales
                    report.save()

    # Pass the sales data to the template for display               
    context = {
        'sales_data': sales_data,
        'total_sales_amount': total_sales_amount
    }

    return render(request, 'sales_report.html', context)
    

@login_required
@user_passes_test(is_admin, login_url='/grocery/access-denied/')
def user_list(request):
    users = User.objects.all() 
    return render(request, 'user_list.html', {'users': users})

@login_required
@user_passes_test(is_admin, login_url='/grocery/access-denied/')
def order_list(request):
    orders = Order.objects.all().order_by('-ordered_at') 
    return render(request, 'order_list.html', {'orders': orders})

@login_required
@user_passes_test(is_admin, login_url='/grocery/access-denied/')
def add_user(request):
    if request.method == 'POST':
        pass 
    return render(request, 'add_user.html')
    
@login_required
@user_passes_test(is_admin, login_url='/grocery/access-denied/')
def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user.delete()  
        return redirect('user_list')
    return render(request, 'delete_user.html', {'user': user})
    
@login_required
@user_passes_test(is_admin, login_url='/grocery/access-denied/')
def update_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        pass 
    return render(request, 'update_user.html', {'user': user})

@login_required
@user_passes_test(is_admin, login_url='/grocery/access-denied/')
def user_activity_report(request):
    activities = UserActivity.objects.all().order_by('-timestamp')

    for activity in activities:
        activity.timestamp = timezone.localtime(activity.timestamp)

    return render(request, 'user_activity_report.html', {'activities': activities})
    

@login_required
@user_passes_test(is_admin, login_url='/grocery/access-denied/')
def delivery_performance_report(request):
    deliveries = Delivery.objects.select_related('delivery_partner').all() 
    # Update the status for each delivery based on the delivered_at field
    for delivery in deliveries:
        delivery.update_status()  

    return render(request, 'delivery_performance_report.html', {'deliveries': deliveries})

@login_required
def leave_review(request, order_id):
    print(f"Leaving review for order_id: {order_id}") 
    order = get_object_or_404(Order, id=order_id)
    products = order.items.all()  
    print(f"Products in order: {products}") 
    customer = request.user.customer  

    if request.method == 'POST':
        print(request.POST)
        for product in products:
            rating = request.POST.get(f'rating_{product.product.id}')
            comment = request.POST.get(f'comment_{product.product.id}')
            print(f"Product ID: {product.product.id}, Rating: {rating}, Comment: {comment}")  
            
            if rating or comment: 
                review, created = Review.objects.get_or_create(
                    product=product.product,
                    customer=customer,
                    defaults={'rating': rating, 'comment': comment}
                )
                if not created:
                    review.rating = rating
                    review.comment = comment
                    review.save()

        return redirect(reverse('thank_you'))

    return render(request, 'leave_review.html', {'products': products})


def thank_you(request):
    return render(request, 'thank_you.html')
