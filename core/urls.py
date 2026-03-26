from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # Cart URLs
    path('add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.view_cart, name='view_cart'),
    path('remove-from-cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('update-cart/<int:item_id>/', views.update_cart_quantity, name='update_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('process-payment/', views.process_payment, name='process_payment'),
    path('order-confirmation/', views.order_confirmation, name='order_confirmation'),

    path('products/', views.product_list, name='products'),
    path('customers/', views.customer_list, name='customers'),
    path('orders/', views.order_list, name='orders'),
    path('create-order/', views.create_order, name='create_order'),
    path('vendors/', views.vendors_page, name='vendors'),
    path('vendor-purchase-invoice/<int:purchase_id>/', views.vendor_purchase_invoice, name='vendor_purchase_invoice'),

    path('login/', views.user_login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('invoice/<int:order_id>/', views.invoice, name='invoice'),
    path('thank-you/', views.thank_you, name='thank_you'),
   
        
    path('approve-staff/<int:id>/', views.approve_staff, name='approve_staff'),
    path('staff-dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('order-details/', views.order_details, name='order_details'),
    path('staff-details/', views.staff_details, name='staff_details'),
]
