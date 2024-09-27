from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Authentication and Profile
    path('home/', views.home, name='home'),
    path('profile/', views.profile, name='profile'),
    path('create-customer-profile/',views.create_customer_profile, name='create_customer_profile'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login_view'),
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # Dashboards
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('vendor_dashboard/', views.vendor_dashboard, name='vendor_dashboard'),
    path('delivery_personnel_dashboard/', views.delivery_personnel_dashboard, name='delivery_personnel_dashboard'),
    path('customer_dashboard/', views.customer_dashboard, name='customer_dashboard'),

    # Vendor Management
    path('vendors/', views.vendor_list, name='vendor_list'),
    path('vendor/<int:vendor_id>/', views.vendor_detail, name='vendor_detail'),
    path('vendor/create/', views.create_vendor, name='create_vendor'),

    # Product Management
    path('products/', views.product_list, name='product_list'),
    path('add/', views.add_product, name='add_product'),
    path('update/<int:product_id>/', views.update_product, name='update_product'),
    path('delete/<int:product_id>/', views.delete_product, name='delete_product'),
    path('products/<int:product_id>/', views.product_detail, name='product_detail'),
    path('categories/', views.categories_view, name='categories'),
    path('category/<int:category_id>/', views.category_detail, name='category_detail'),
    path('subcategory/<int:subcategory_id>/', views.subcategory_products, name='subcategory_products'),

    # Cart and Order Management
    path('browse/', views.browse_products, name='browse_products'),
    path('update-cart-button/', views.update_cart_button, name='update_cart_button'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('view_cart/', views.view_cart, name='view_cart'),
    path('remove-from-cart/<int:cart_item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('place_order/', views.place_order, name='place_order'),
    path('order_success/<int:order_id>/', views.order_success, name='order_success'),
    path('order_detail/<int:order_id>/', views.order_detail, name='order_detail'),
    path('order_list/', views.order_list, name='order_list'),
    path('order_history/', views.order_history, name='order_history'),
    path('order/<int:order_id>/', views.order_tracking, name='order_tracking'),
    path('update-order-status/<int:order_id>/', views.update_order_status, name='update_order_status'),

    # Delivery Management
    path('delivery-management/', views.delivery_management, name='delivery_management'),
    path('assign_delivery_partner/<int:order_id>/', views.assign_delivery_partner, name='assign_delivery_partner'),
    path('update_delivery_status/<int:delivery_id>/', views.update_delivery_status, name='update_delivery_status'),

    # Payment Management
    path('grocery/order/<int:order_id>/proceed_to_payment/', views.proceed_to_payment, name='proceed_to_payment'),
    path('payment_success/', views.payment_success, name='payment_success'),
    path('payment_failure/', views.payment_failure, name='payment_failure'),

    # Access Denied
    path('access-denied/', views.access_denied, name='access_denied'),

    #
    path('sales-report/', views.sales_report, name='sales_report'),
    path('user-list/', views.user_list, name='user_list'),
    path('add-user/', views.add_user, name='add_user'),
    path('delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
    path('update-user/<int:user_id>/', views.update_user, name='update_user'),
    path('user-activity-report/', views.user_activity_report, name='user_activity_report'),
    path('delivery-performance-report/', views.delivery_performance_report, name='delivery_performance_report'),
   
    
    #
    path('leave-review/<str:product_ids>/', views.leave_review, name='leave_review'),

   

]
