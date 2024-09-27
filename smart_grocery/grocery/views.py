from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate,logout
from django.contrib.auth.decorators import login_required, user_passes_test, permission_required
from .models import Profile, Product,Category,Subcategory, Customer, Order, OrderItem, Cart, Delivery, Vendor, Invoice, Review
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse, HttpResponseRedirect, HttpResponseNotFound, HttpResponseBadRequest
from .forms import VendorForm, ProductForm,  OrderStatusForm, CartForm, OrderItemForm, UserRegistrationForm, CustomerForm, DeliveryForm,ReviewForm
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.decorators import method_decorator
from django.views.generic import ListView
import razorpay
from django.db.models import Q, Avg
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from .models import UserActivity
from io import BytesIO
from django.core.cache import cache
from django.core.mail import send_mail
from django.core.mail import EmailMessage
from .utils import generate_invoice 
from django.utils import timezone
import json
from django.db.models import Count
from django.db.models import Sum, F,FloatField, ExpressionWrapper
from django.urls import reverse
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.views import PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
from django.views.decorators.http import require_POST
from django.middleware.csrf import get_token
from .forms import CheckoutForm
from decimal import Decimal


@login_required
def home(request):
    try:
        profile = request.user.profile
    except AttributeError:
        return redirect('access-denied')  # Redirect if the user does not have a profile

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
        return redirect('access-denied')  # Redirect if the role is unrecognized


def profile(request):
    # Your view logic here
    return render(request, 'profile.html')

@csrf_exempt
def register_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # Log the user in after registration
            
            # Check if a Customer profile already exists for the user
            if not Customer.objects.filter(user=user).exists():
                # Create a new customer profile only if it doesn't exist
                Customer.objects.create(user=user, address='default address', phone_number='0000000000')

            return redirect('create_customer_profile')  # Redirect to create profile page
    else:
        form = UserRegistrationForm()
    return render(request, 'registration/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # Check if the user's Customer profile is complete
            try:
                customer = Customer.objects.get(user=user)
                if not (customer.address and customer.phone_number):
                    return redirect('create_customer_profile')
            except Customer.DoesNotExist:
                return redirect('create_customer_profile')
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})


@csrf_exempt
@login_required
def create_customer_profile(request):
    # Check the user's role
    if request.user.profile.role != 'customer':
        # Redirect non-customers to their respective dashboard
        if request.user.profile.role == 'admin':
            return redirect('admin_dashboard')
        elif request.user.profile.role == 'vendor':
            return redirect('vendor_dashboard')
        elif request.user.profile.role == 'delivery_personnel':
            return redirect('delivery_dashboard')
        else:
            return redirect('home')  # Fallback in case no specific role is matched

    # If the user is a customer, proceed with profile creation
    customer, created = Customer.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            return redirect('home')
    else:
        form = CustomerForm(instance=customer)
    
    return render(request, 'registration/create_customer_profile.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    return redirect('login_view')


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

    # Count orders and deliveries
    order_count = orders.count()
    delivery_count = Order.objects.filter(delivery_partner__isnull=False).count()
    
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
        'delivery_count': delivery_count, # Add this line to include delivery count
        'delivery_partners': delivery_partners,  # Add delivery partners to context
         'total_sales': total_sales
    }

    return render(request, 'admin_dashboard.html', context)
    

@login_required
@user_passes_test(is_vendor_or_admin, login_url='/grocery/access-denied/')
def vendor_dashboard(request):
    if request.user.profile.role == 'vendor':
        vendor = get_object_or_404(Vendor, profile=request.user.profile)
        vendor_products = Product.objects.filter(vendor=vendor)
    else:
        vendor_products = Product.objects.all()  # Admin view all products
    
    vendor_orders = Order.objects.filter(vendor__profile=request.user.profile)
    context = {
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
        delivery_count = Delivery.objects.filter(order__delivery_partner__isnull=False).count()  # Count deliveries

        context = {
            'orders': customer_orders,
            'order_count': order_count,
            'delivery_count': delivery_count,
        }
        return render(request, 'customer_dashboard.html', context)

    # Redirect to appropriate dashboard if not a customer or admin
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
        order_count = Order.objects.count()
        delivery_count = Order.objects.filter(delivery_partner__isnull=False).count()

        # Handle status updates
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
            'delivery_orders': delivery_orders,
            'order_count': order_count,
            'delivery_count': delivery_count,
        }
        return render(request, 'delivery_personnel_dashboard.html', context)

    # Redirect to admin dashboard if not a delivery personnel or admin
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
        return redirect('product_list')  # Assuming 'product_list' is the view that lists all products
    
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
    reviews = product.reviews.all()
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0

    return render(request, 'product_detail.html', {
        'product': product,
        'reviews': reviews,
        'avg_rating': avg_rating,
    })


def browse_products(request):
    # Your view logic here
    return render(request, 'browse_products.html')

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
    
    # Check if the requested quantity exceeds available stock
    if product.stock < quantity:
        if product.stock == 0:
            return JsonResponse({'message': 'Sorry, this product is out of stock.'}, status=400)
        else:
            return JsonResponse({'message': f'Only {product.stock} units available.'}, status=400)


    # Check if the cart already has this product
    cart_item, created = Cart.objects.get_or_create(
        customer=request.user.customer, product=product
    )
    
    if not created:
        cart_item.quantity += quantity
    else:
        cart_item.quantity = quantity
    
    cart_item.save()

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

    # Calculate total price for each cart item (quantity * price per unit)
    for item in cart_items:
        item.total_price = item.quantity * item.product.price

    # Calculate total cart amount
    total_amount = cart_items.aggregate(total_amount=Sum(F('quantity') * F('product__price')))['total_amount'] or 0
    
     # Store total amount in session
    request.session['total_amount'] = float(total_amount)

    return render(request, 'view_cart.html', {
        'cart_items': cart_items,
        'total_quantity': total_quantity,
        'total_amount': total_amount
    })


    

@csrf_exempt
def update_cart(request, item_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            quantity = data.get('quantity')
            customer = request.user.customer  # Ensure the user has a customer profile

            if quantity is not None:
                cart_item = Cart.objects.get(id=item_id, customer=customer)
                cart_item.quantity = quantity
                cart_item.save()
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'error': 'Quantity not provided'})
        except Cart.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Cart item does not exist'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@login_required
@require_POST
def remove_from_cart(request, cart_item_id):
    if request.method == 'POST':
        cart_item = Cart.objects.filter(id=cart_item_id, customer=request.user.customer).first()
        
        if cart_item:
            cart_item.delete()
        return redirect('view_cart')  # Redirect back to the cart page
    return redirect('view_cart')



@login_required
def checkout(request):
    if request.method == 'POST':
        address = request.POST.get('address')
        phone_number = request.POST.get('phone_number')

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

        # Fetch cart items and determine vendor
        cart_items = Cart.objects.filter(customer=customer)
        if not cart_items.exists():
            return render(request, 'checkout.html', {
                'error': 'No products found in the cart.',
                'total_amount': request.session.get('total_amount', 0),
                'customer': customer
            })

        vendor = cart_items.first().product.vendor
        
        # Check stock availability before creating the order
        for item in cart_items:
            if item.product.stock < item.quantity:
                return render(request, 'checkout.html', {
                    'error': f"Only {item.product.stock} units of {item.product.name} are available.",
                    'total_amount': request.session.get('total_amount', 0),
                    'customer': customer
                })

        # Create the order
        order = Order.objects.create(
            customer=customer,
            vendor=vendor,
            total_amount=request.session.get('total_amount', 0),
            status='Placed',
        )

        # Now ordered_at will be set to the current time in Asia/Kolkata
        print(f"Order created at: {order.ordered_at}")


        # Save order items
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )

            # Reduce the stock after order confirmation
            item.product.stock -= item.quantity
            item.product.save()

        # Clear cart after order is placed
        cart_items.delete()

        # Clear the total amount from session
        del request.session['total_amount']

        # Send Notifications after order creation
        send_order_confirmation_email(request.user, order)
        send_order_confirmation_sms(request.user, order)
        send_push_notification(request.user, f'Your order #{order.id} has been placed!')

        # Redirect to order success page
        return redirect('order_success', order_id=order.id)

    else:
        customer = request.user.customer if request.user.is_authenticated else None
        total_amount = request.session.get('total_amount', 0)
        
        # Convert total_amount back to Decimal if needed
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
        return redirect('home')  # Redirect or handle error if the customer profile is missing

    try:
        # Fetch the order for the logged-in user's customer
        order = Order.objects.get(id=order_id, customer=customer_profile)
        order_items = OrderItem.objects.filter(order=order)
        delivery_partner = order.delivery_partner  # Retrieve delivery partner details
    except Order.DoesNotExist:
        return redirect('home')  # Redirect or handle error if the order is not found
    
     # Define the list of past statuses
    statuses = ['Order Placed', 'Processing', 'Shipped', 'Out for Delivery', 'Delivered', 'Canceled']
    
     # Determine which statuses are past based on the current order status
    past_statuses = statuses[:statuses.index(order.status) + 1]

    return render(request, 'order_detail.html', {
        'order': order,
        'order_items': order_items,
        'delivery_partner': delivery_partner,
        'statuses': statuses,  # Pass delivery partner details to the template
        'past_statuses': past_statuses
    })



def order_list(request):
    orders = Order.objects.filter(customer=request.user.profile)
    return render(request, 'order_list.html', {'orders': orders})


@csrf_exempt
@login_required
def update_order_status(request, order_id):
    if request.method == 'POST':
        try:
            data = request.POST  # Get the POST data
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

            # Debug print statement
            print(f"Order {order_id} has been updated to status: {new_status}")
            
            # Send email notification to the customer
            send_mail(
                subject='Order Status Update',
                message=f'Your order with ID {order.id} has been updated to "{new_status}".',
                from_email='ashwithar2001@gmail.com',  # Update with your sender email
                recipient_list=[order.customer.user.email],  # Send email to customer
                fail_silently=False,
            )
            
            # Redirect back to the dashboard or return a success message
            return redirect('delivery_personnel_dashboard')  # Change this to your desired URL
        except Order.DoesNotExist:
            return HttpResponseNotFound('Order not found')
        except Delivery.DoesNotExist:
            return HttpResponseNotFound('Delivery not found')
    else:
        return HttpResponseBadRequest('Invalid request method')



@login_required
def order_history(request):
    # Fetch all orders for the logged-in customer
    customer_profile = request.user.customer  # Assuming there's a related `Customer` profile
    orders = Order.objects.filter(customer=customer_profile).order_by('-ordered_at')

    return render(request, 'order_history.html', {'orders': orders})


def place_order(request):
    if request.method == 'POST':
        cart_items = Cart.objects.filter(customer=request.user.customer)
        total_amount = sum(item.get_price() * item.quantity for item in cart_items)
        
        # Logic to handle payment (e.g., redirect to payment gateway)
        
        # Clear cart after successful payment
        cart_items.delete()
        
        return redirect('order_confirmation')  # Redirect to order confirmation page or similar

    return redirect('view_cart')  # Handle error if not POST request


@login_required
@user_passes_test(is_admin, login_url='/grocery/access-denied/')
def delivery_management(request):
    # Fetch orders where delivery_partner is null
    orders = Order.objects.filter(delivery_partner__isnull=True).order_by('-ordered_at').select_related('customer')

    # Fetch all deliveries for tracking
    deliveries = Delivery.objects.select_related('order', 'delivery_partner').all()

    return render(request, 'delivery_management.html', {
        'orders': orders,
        'deliveries': deliveries
    })



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

                # Assign the delivery partner
                order.delivery_partner = delivery_partner
                order.save()  # Ensure the order is saved with the delivery partner

                # Handle delivery creation or update
                delivery, created = Delivery.objects.update_or_create(
                    order=order,
                    defaults={
                        'delivery_partner': delivery_partner,
                        'address': order.customer.address
                    }
                )

                return redirect('order_detail', order_id=order.id)  # Redirect to order detail after assignment

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
    # Logic to update the order status
    order = Order.objects.get(id=order_id)
    order.status = request.POST['status']
    order.save()

    # Send WebSocket message
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        'delivery_status',
        {
            'type': 'send_status_update',
            'orderId': order.id,
            'status': order.status,
        }
    )



def delivery_personnel_list(request):
    deliveries = Delivery.objects.all()  # Adjust if needed to get the correct deliveries
    return render(request, 'delivery_personnel_list.html', {'deliveries': deliveries})

def delivery_personnel_detail(request, delivery_id):
    delivery = get_object_or_404(Delivery, id=delivery_id)
    return render(request, 'delivery_personnel_detail.html', {'delivery': delivery})

def order_tracking(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'order_tracking.html', {'order': order})

@login_required
def create_vendor(request):
    if request.method == 'POST':
        form = VendorForm(request.POST)
        if form.is_valid():
            vendor = form.save(commit=False)
            vendor.profile = request.user.profile  # Associate the vendor with the logged-in user
            vendor.save()
            return redirect('vendor_list')
    else:
        form = VendorForm()
    return render(request, 'create_vendor.html', {'form': form})


@login_required
def edit_vendor(request, vendor_id):
    vendor = get_object_or_404(Vendor, pk=vendor_id)
    if vendor.profile.user != request.user:  # Ensure the vendor is associated with the logged-in user
        return redirect('unauthorized')  # Redirect to an unauthorized page or show an error
    if request.method == 'POST':
        form = VendorForm(request.POST, instance=vendor)
        if form.is_valid():
            form.save()
            return redirect('vendor_detail', vendor_id=vendor.id)
    else:
        form = VendorForm(instance=vendor)
    return render(request, 'edit_vendor.html', {'form': form})

@login_required
def delete_vendor(request, vendor_id):
    vendor = get_object_or_404(Vendor, pk=vendor_id)
    if vendor.profile.user != request.user:  # Ensure the vendor is associated with the logged-in user
        return redirect('unauthorized')  # Redirect to an unauthorized page or show an error
    vendor.delete()
    return redirect('vendor_list')


def vendor_list(request):
    vendors = Vendor.objects.all()
    return render(request, 'vendor_list.html', {'vendors': vendors})


def vendor_detail(request, vendor_id):
    vendor = get_object_or_404(Vendor, id=vendor_id)
    return render(request, 'vendor_detail.html', {'vendor': vendor})

@permission_required('grocery.can_manage_business', raise_exception=True)
def manage_business(request):
    # View logic here
    pass

@permission_required('grocery.can_edit_own_profile', raise_exception=True)
def edit_vendor_profile(request, vendor_id):
    # Your view logic here
    pass

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
                receipt=str(order.id),
                payment_capture='1'  # Auto capture payment
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
                'receipt': str(order.id),
                'total_amount': total_amount,
                'csrf_token': csrf_token
            }

            return render(request, 'proceed_to_payment.html', context)
        
        except Order.DoesNotExist:
            return redirect('home')  # Redirect if order is not found
        except Exception as e:
            # Handle any unexpected errors (optional: add logging here)
            return HttpResponse(f"An error occurred: {str(e)}")

    elif request.method == "GET" and 'razorpay_payment_id' in request.GET:
        # Successful payment logic
        razorpay_payment_id = request.GET['razorpay_payment_id']
        try:
            # Fetch the order again
            order = Order.objects.get(id=order_id, customer=request.user.customer)

            # Update order status to 'Delivered' after successful payment
            order.status = 'Delivered'
            order.save()

            # Redirect to customer dashboard or order details page
            return redirect('order_detail', order_id=order.id)  # or to the order details page

        except Order.DoesNotExist:
            return redirect('home')  # Redirect if order is not found
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
            # Redirect to payment failure page if verification fails
            return redirect('payment_failure')
            
        # Retrieve the order and update status
        try:
            order = Order.objects.get(razorpay_order_id=razorpay_order_id)
            order.status = 'Delivered'
            order.save()

            # Generate invoice as a PDF using the generate_invoice function
            invoice_pdf = generate_invoice(order)

            # Send the invoice via email
            customer_email = order.customer.user.email
            email_subject = 'Your Invoice from Smart Grocery'
            email_body = 'Thank you for your purchase. Please find the attached invoice for your recent order.'
            email = EmailMessage(
                email_subject,
                email_body,
                settings.DEFAULT_FROM_EMAIL,
                [customer_email]
            )

            # Attach the PDF invoice
            email.attach(f'invoice_{order.id}.pdf', invoice_pdf, 'application/pdf')
            email.send()

            # Clear the cart after successful payment
            Cart.objects.filter(customer=request.user.customer).delete()

            # Render the success page with order details
         
             # Redirect to leave review page with product IDs from the order
            product_ids = order.items.values_list('product_id', flat=True)  # Adjust based on your OrderItem model
            return redirect('leave_review', product_ids=','.join(map(str, product_ids)))  # Ensure 'leave_review' URL is configured correctly
            
        except Order.DoesNotExist:
            return JsonResponse({'error': 'Order not found'}, status=404)
    else:
        return redirect('home')


def payment_failure(request):
    return render(request, 'payment_failure.html')


def send_order_confirmation_email(user, order):
    subject = 'Order Confirmation'
    message = f'Dear {user.first_name}, your order #{order.id} has been confirmed!'
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [user.email]  # Use the real or dummy email for testing
    
    send_mail(subject, message, from_email, recipient_list)


def send_order_confirmation_sms(user, order):
    phone_number = user.profile.phone_number  # Assuming you have a Profile model with phone_number
    message = f'Your order #{order.id} has been confirmed!'
    
    # Simulate SMS sending (print to console)
    print(f"Sending SMS to {phone_number}: {message}")


def send_push_notification(user, message):
    # Simulate sending a push notification
    print(f"Sending push notification to {user.username}: {message}") 

@login_required
@user_passes_test(is_admin, login_url='/grocery/access-denied/')
def sales_report(request):
    orders = Order.objects.all()
    total_sales = sum(order.total_amount for order in orders)

    context = {
        'orders': orders,
        'total_sales': total_sales,
    }

    return render(request, 'sales_report.html', context)


@login_required
@user_passes_test(is_admin, login_url='/grocery/access-denied/')
def user_list(request):
    users = User.objects.all()  # Fetch all users
    return render(request, 'user_list.html', {'users': users})

@login_required
@user_passes_test(is_admin, login_url='/grocery/access-denied/')
def order_list(request):
    orders = Order.objects.all()  # Fetch all orders
    return render(request, 'order_list.html', {'orders': orders})

@login_required
@user_passes_test(is_admin, login_url='/grocery/access-denied/')
def add_user(request):
    if request.method == 'POST':
        # Handle form submission to create a user
        pass  # Implement user creation logic here
    return render(request, 'add_user.html')
    
@login_required
@user_passes_test(is_admin, login_url='/grocery/access-denied/')
def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user.delete()  # Delete user logic
        return redirect('user_list')
    return render(request, 'delete_user.html', {'user': user})
    
@login_required
@user_passes_test(is_admin, login_url='/grocery/access-denied/')
def update_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        # Update user logic
        pass  # Implement user update logic here
    return render(request, 'update_user.html', {'user': user})

@login_required
@user_passes_test(is_admin, login_url='/grocery/access-denied/')
def user_activity_report(request):
     # Fetch or create the activity data here
    activity_data = UserActivity.objects.all()  # Example, adjust as necessary

    # Implement logic to gather user activity data
    context = {
        'activity_data': activity_data,  # Replace with actual data
    }
    return render(request, 'user_activity_report.html', context)
    


@login_required
@user_passes_test(is_admin, login_url='/grocery/access-denied/')
def delivery_performance_report(request):
    deliveries = Delivery.objects.select_related('delivery_partner').all()  # Optimize the query

     # Update the status for each delivery based on the delivered_at field
    for delivery in deliveries:
        delivery.update_status()  # Call the method to update the status based on delivered_at

    return render(request, 'delivery_performance_report.html', {'deliveries': deliveries})


@login_required
def leave_review(request, product_ids):
    product_ids_list = product_ids.split(',')
    products = Product.objects.filter(id__in=product_ids_list)
    customer = get_object_or_404(Customer, user=request.user)  # Improved error handling

    if request.method == 'POST':
        for product in products:
            rating = request.POST.get(f'rating_{product.id}')
            comment = request.POST.get(f'comment_{product.id}')

            # Check if the customer has purchased this product
            if OrderItem.objects.filter(order__customer=customer, product=product).exists():
                if rating and comment:  # Ensure both rating and comment are provided
                    review, created = Review.objects.get_or_create(
                        product=product,
                        customer=customer,
                        defaults={'rating': rating, 'comment': comment}
                    )
                    if not created:
                        # Update existing review
                        review.rating = rating
                        review.comment = comment
                        review.save()
                        messages.success(request, f"Your review for {product.name} has been updated.")
                    else:
                        messages.success(request, f"Your review for {product.name} has been submitted.")
                else:
                    messages.error(request, f"Please provide both a rating and a comment for {product.name}.")

        return redirect('home')

    return render(request, 'leave_review.html', {'products': products})