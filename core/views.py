from decimal import Decimal
import random

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.mail import send_mail

from .models import Product, Customer, Order, UserOTP, UserProfile, Cart, CartItem, Vendor, VendorPurchase

from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from .models import UserProfile


def get_user_role(user):
    if not user.is_authenticated:
        return None
    profile = UserProfile.objects.filter(user=user).first()
    return profile.role if profile else None


def is_staff_or_admin(user):
    role = get_user_role(user)
    return role in {'staff', 'admin'}


def get_customer_for_user(user):
    if not user.is_authenticated:
        return None
    return Customer.objects.filter(email=user.email).first()

# ✅ LANDING PAGE
def landing_page(request):
    return render(request, 'core/landing.html')


# ✅ DASHBOARD (CUSTOMER)
def dashboard(request):
    if not request.user.is_authenticated:
        return redirect('landing')
    
    customer = get_customer_for_user(request.user)
    user_name = request.user.first_name or request.user.username
    products = Product.objects.all()

    user_orders = Order.objects.filter(customer=customer).order_by('-created_at') if customer else Order.objects.none()
    total_orders = user_orders.count()

    if user_orders.exists():
        latest_order = user_orders.first()
        subtotal = latest_order.total_price
        discount_amount = latest_order.discount
        gst_total = latest_order.gst_amount
        final_total = latest_order.final_amount
        
        # Determine discount type
        if subtotal > 1000:
            discount_type = "Bulk Discount"
            discount_percent = 10
        elif latest_order.quantity > 50:
            discount_type = "Wholesale"
            discount_percent = 10
        else:
            discount_type = "Regular"
            discount_percent = 0
    else:
        # Default values for display
        subtotal = 0
        discount_amount = 0
        gst_total = 0
        final_total = 0
        discount_type = "None"
        discount_percent = 0
    
    gst_amount = Decimal('18')
    
    return render(request, 'core/dashboard.html', {
        'user_name': user_name,
        'customer': customer,
        'products': products,
        'customer_orders': user_orders[:5],
        'total_orders': total_orders,
        'subtotal': int(subtotal) if subtotal else 0,
        'discount_amount': int(discount_amount) if discount_amount else 0,
        'discount_type': discount_type,
        'discount_percent': discount_percent,
        'gst_total': int(gst_total) if gst_total else 0,
        'final_total': int(final_total) if final_total else 0,
        'gst_amount': int(gst_amount),
        'delivery_charge': 0,
    })


# ✅ ADD TO CART
def add_to_cart(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        quantity = int(request.POST.get('quantity', 1))
        
        try:
            product = Product.objects.get(id=product_id)
            
            # Get or create cart for user
            cart, created = Cart.objects.get_or_create(user=request.user)
            
            # Check if product already in cart
            cart_item, item_created = CartItem.objects.get_or_create(
                cart=cart,
                product=product
            )
            
            if not item_created:
                # Increase quantity if already in cart
                cart_item.quantity += quantity
            else:
                cart_item.quantity = quantity
            
            cart_item.save()
            
            return redirect('view_cart')
        except Product.DoesNotExist:
            return redirect('dashboard')
    
    return redirect('dashboard')


# ✅ VIEW CART
def view_cart(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    try:
        cart = Cart.objects.get(user=request.user)
    except Cart.DoesNotExist:
        cart = None
    
    cart_items = cart.items.all() if cart else []
    
    # Calculate totals
    subtotal = sum([item.get_total_price() for item in cart_items])
    gst = subtotal * Decimal('0.18')
    total = subtotal + gst
    
    return render(request, 'core/cart.html', {
        'cart': cart,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'gst': gst,
        'total': total,
    })


# ✅ REMOVE FROM CART
def remove_from_cart(request, item_id):
    if not request.user.is_authenticated:
        return redirect('login')
    
    try:
        cart = Cart.objects.get(user=request.user)
        cart_item = CartItem.objects.get(id=item_id, cart=cart)
        cart_item.delete()
    except (Cart.DoesNotExist, CartItem.DoesNotExist):
        pass
    
    return redirect('view_cart')


# ✅ UPDATE CART ITEM QUANTITY
def update_cart_quantity(request, item_id):
    if not request.user.is_authenticated:
        return redirect('login')
    
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        
        try:
            cart = Cart.objects.get(user=request.user)
            cart_item = CartItem.objects.get(id=item_id, cart=cart)
            
            if quantity <= 0:
                cart_item.delete()
            else:
                cart_item.quantity = quantity
                cart_item.save()
        except (Cart.DoesNotExist, CartItem.DoesNotExist):
            pass
    
    return redirect('view_cart')


# ✅ CHECKOUT PAGE
def checkout(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    try:
        cart = Cart.objects.get(user=request.user)
    except Cart.DoesNotExist:
        return redirect('view_cart')
    
    cart_items = cart.items.all()
    if not cart_items.exists():
        return redirect('view_cart')
    
    # Calculate totals
    subtotal = sum([item.get_total_price() for item in cart_items])
    gst = subtotal * Decimal('0.18')
    total = subtotal + gst
    
    customer = get_customer_for_user(request.user)
    
    return render(request, 'core/checkout.html', {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'gst': gst,
        'total': total,
        'customer': customer,
    })


# ✅ PROCESS PAYMENT
def process_payment(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', 'Cash')
        
        try:
            cart = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            return redirect('view_cart')
        
        cart_items = cart.items.all()
        if not cart_items.exists():
            return redirect('view_cart')
        
        customer = get_customer_for_user(request.user)
        if customer:
            customer.name = request.POST.get('name') or customer.name
            customer.phone = request.POST.get('phone', customer.phone)
            customer.address = request.POST.get('address', customer.address)
            customer.email = request.POST.get('email', customer.email)
            customer.save()
        else:
            customer = Customer.objects.create(
                name=request.POST.get('name') or request.user.first_name or request.user.username,
                email=request.POST.get('email') or request.user.email,
                phone=request.POST.get('phone', ''),
                address=request.POST.get('address', '')
            )
        
        # Calculate totals
        subtotal = sum([item.get_total_price() for item in cart_items])
        discount = Decimal('0')
        if subtotal > 1000:
            discount = subtotal * Decimal('0.10')
        
        price_after_discount = subtotal - discount
        gst_amount = price_after_discount * Decimal('0.18')
        final_amount = price_after_discount + gst_amount
        
        # Create orders for each item in cart
        orders = []
        for cart_item in cart_items:
            if cart_item.product.quantity < cart_item.quantity:
                return render(request, 'core/checkout.html', {
                    'error': f"Not enough stock for {cart_item.product.name}"
                })
            
            # Update product stock
            cart_item.product.quantity -= cart_item.quantity
            cart_item.product.save()
            
            # Create order
            order = Order.objects.create(
                customer=customer,
                product=cart_item.product,
                quantity=cart_item.quantity,
                total_price=cart_item.get_total_price(),
                discount=discount * (cart_item.get_total_price() / subtotal),
                gst_amount=gst_amount * (cart_item.get_total_price() / subtotal),
                final_amount=final_amount * (cart_item.get_total_price() / subtotal),
                payment_method=payment_method,
                status='Completed'
            )
            orders.append(order)
        
        # Send invoice email
        send_invoice_email(customer, orders, final_amount, payment_method)
        
        # Clear cart
        cart_items.delete()
        
        # Redirect to order confirmation
        request.session['order_ids'] = [order.id for order in orders]
        return redirect('order_confirmation')
    
    return redirect('view_cart')


# ✅ ORDER CONFIRMATION
def order_confirmation(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    order_ids = request.session.get('order_ids', [])
    customer = get_customer_for_user(request.user)
    orders = Order.objects.filter(id__in=order_ids)
    if get_user_role(request.user) == 'customer' and customer:
        orders = orders.filter(customer=customer)
    
    if not orders.exists():
        return redirect('dashboard')
    
    total_amount = sum([order.final_amount for order in orders])
    
    return render(request, 'core/order_confirmation.html', {
        'orders': orders,
        'total_amount': total_amount,
    })


# ✅ SEND INVOICE EMAIL
def send_invoice_email(customer, orders, total_amount, payment_method):
    """Send professional invoice to customer email"""
    
    # Build order items HTML
    items_html = ""
    for order in orders:
        items_html += f"""
        <tr>
            <td style="border-bottom: 1px solid #ddd; padding: 12px;">{order.product.name}</td>
            <td style="border-bottom: 1px solid #ddd; padding: 12px; text-align: center;">{order.quantity}</td>
            <td style="border-bottom: 1px solid #ddd; padding: 12px; text-align: right;">₹{order.product.price}</td>
            <td style="border-bottom: 1px solid #ddd; padding: 12px; text-align: right;">₹{order.total_price}</td>
        </tr>
        """
    
    invoice_html = f"""
    <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: 'Arial', sans-serif;
                    color: #333;
                    background-color: #f5f5f5;
                    margin: 0;
                    padding: 0;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: white;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }}
                .header {{
                    background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 28px;
                }}
                .content {{
                    padding: 30px;
                }}
                .section {{
                    margin-bottom: 25px;
                }}
                .section h3 {{
                    color: #6366f1;
                    border-bottom: 3px solid #6366f1;
                    padding-bottom: 10px;
                    margin-bottom: 15px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 15px 0;
                }}
                table th {{
                    background-color: #f0f0f0;
                    padding: 12px;
                    text-align: left;
                    font-weight: bold;
                    border-bottom: 2px solid #ddd;
                }}
                .summary {{
                    background-color: #f9fafb;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                }}
                .summary-row {{
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 10px;
                    padding-bottom: 10px;
                    border-bottom: 1px solid #ddd;
                }}
                .summary-row.total {{
                    font-weight: bold;
                    font-size: 18px;
                    color: #6366f1;
                    border-bottom: 2px solid #6366f1;
                    margin-top: 10px;
                    padding-top: 10px;
                }}
                .footer {{
                    background-color: #f5f5f5;
                    padding: 20px;
                    text-align: center;
                    font-size: 12px;
                    color: #666;
                    border-top: 1px solid #ddd;
                }}
                .note {{
                    background-color: #ecfdf5;
                    border-left: 4px solid #10b981;
                    padding: 12px;
                    margin: 15px 0;
                    border-radius: 4px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <!-- Header -->
                <div class="header">
                    <h1>🧾 Invoice</h1>
                    <p style="margin: 10px 0; opacity: 0.9;">Inventory Billing System</p>
                </div>

                <!-- Content -->
                <div class="content">
                    <!-- Greeting -->
                    <p style="font-size: 16px; margin-bottom: 20px;">
                        Hello <strong>{customer.name}</strong>,
                    </p>
                    <p style="color: #666; margin-bottom: 20px;">
                        Thank you for your purchase! Your order has been confirmed and will be processed shortly.
                    </p>

                    <!-- Order Details -->
                    <div class="section">
                        <h3>📦 Order Details</h3>
                        <table>
                            <thead>
                                <tr>
                                    <th>Product</th>
                                    <th>Quantity</th>
                                    <th>Unit Price</th>
                                    <th>Amount</th>
                                </tr>
                            </thead>
                            <tbody>
                                {items_html}
                            </tbody>
                        </table>
                    </div>

                    <!-- Payment Summary -->
                    <div class="section">
                        <h3>💰 Payment Summary</h3>
                        <div class="summary">
                            <div class="summary-row">
                                <span>Subtotal</span>
                                <span>₹{sum([order.total_price for order in orders])}</span>
                            </div>
                            <div class="summary-row">
                                <span>Discount</span>
                                <span>-₹{sum([order.discount for order in orders])}</span>
                            </div>
                            <div class="summary-row">
                                <span>GST (18%)</span>
                                <span>+₹{sum([order.gst_amount for order in orders])}</span>
                            </div>
                            <div class="summary-row total">
                                <span>Total Amount</span>
                                <span>₹{total_amount}</span>
                            </div>
                        </div>
                    </div>

                    <!-- Payment Method -->
                    <div class="section">
                        <h3>🏦 Payment Information</h3>
                        <p><strong>Payment Method:</strong> {payment_method}</p>
                        <p><strong>Status:</strong> <span style="color: #10b981; font-weight: bold;">✓ Confirmed</span></p>
                        <p><strong>Order Date:</strong> {orders[0].created_at.strftime('%d %B %Y, %H:%M')}</p>
                    </div>

                    <!-- Delivery Information -->
                    <div class="note">
                        📦 <strong>Estimated Delivery:</strong> 3-5 business days. You'll receive tracking updates via email.
                    </div>

                    <!-- Contact Information -->
                    <div class="section">
                        <h3>📞 Delivery Address</h3>
                        <p>
                            {customer.name}<br>
                            {customer.phone}<br>
                            {customer.address or 'Address not provided'}<br>
                            Email: {customer.email}
                        </p>
                    </div>

                    <!-- Footer Note -->
                    <div class="section" style="background-color: #f0f9ff; padding: 15px; border-radius: 8px; border-left: 4px solid #6366f1;">
                        <p style="margin: 0; font-size: 13px; color: #666;">
                            If you have any questions about your order, please don't hesitate to contact us. We're here to help! 
                        </p>
                    </div>
                </div>

                <!-- Footer -->
                <div class="footer">
                    <p style="margin: 0 0 10px 0;">✓ This is an automated email. Please do not reply directly.</p>
                    <p style="margin: 0;">Inventory Billing System™ | All Rights Reserved © 2024</p>
                </div>
            </div>
        </body>
    </html>
    """
    
    try:
        send_mail(
            subject=f'Order Invoice - Order #{orders[0].id} | Inventory Billing',
            message=f'Invoice for order {orders[0].id}. Total: ₹{total_amount}',
            from_email='noreply@inventorybilling.com',
            recipient_list=[customer.email],
            html_message=invoice_html,
            fail_silently=False
        )
        print(f"✓ Invoice sent successfully to {customer.email}")
    except Exception as e:
        print(f"✗ Error sending invoice: {e}")

def staff_dashboard(request):
    if not request.user.is_authenticated:
        return redirect('landing')
    
    products = Product.objects.all()
    orders = Order.objects.all().order_by('-created_at')
    customers = Customer.objects.all()
    low_stock = Product.objects.filter(quantity__lt=50)
    recent_orders = orders[:8]
    
    total_products = products.count()
    total_customers = customers.count()
    low_stock_count = low_stock.count()
    
    # Calculate total revenue
    total_revenue = sum([o.final_amount for o in orders])
    
    # Calculate payment method totals
    cash_total = sum([o.final_amount for o in orders.filter(payment_method='Cash')])
    upi_total = sum([o.final_amount for o in orders.filter(payment_method='UPI')])
    card_total = sum([o.final_amount for o in orders.filter(payment_method='Card')])
    
    # Add total orders count and invoice details to customers
    from django.db.models import Count, Sum
    customers_with_orders = []
    for customer in customers:
        order_count = Order.objects.filter(customer=customer).count()
        total_spent = Order.objects.filter(customer=customer).aggregate(Sum('final_amount'))['final_amount__sum'] or 0
        customer.total_orders = order_count
        customer.total_spent = int(total_spent)
        customers_with_orders.append(customer)
    
    # Group orders by payment method for breakdown
    payment_breakdown = {
        'cash': {'count': orders.filter(payment_method='Cash').count(), 'total': int(cash_total)},
        'upi': {'count': orders.filter(payment_method='UPI').count(), 'total': int(upi_total)},
        'card': {'count': orders.filter(payment_method='Card').count(), 'total': int(card_total)},
    }
    
    return render(request, 'core/staff_dashboard.html', {
        'products': products,
        'orders': orders,
        'customers': customers_with_orders[:10],
        'low_stock': low_stock,
        'recent_orders': recent_orders,
        'total_products': total_products,
        'total_customers': total_customers,
        'total_revenue': int(total_revenue),
        'low_stock_count': low_stock_count,
        'payment_breakdown': payment_breakdown,
        'all_orders': orders[:50],  # All orders for bill listing
    })


# ✅ ADMIN DASHBOARD (DYNAMIC)
def admin_dashboard(request):
    if not request.user.is_authenticated:
        return redirect('landing')
    
    from .models import Feedback
    
    orders = Order.objects.all()
    products = Product.objects.all()
    customers = Customer.objects.all()
    pending_staff = UserProfile.objects.filter(role='staff', is_approved=False)
    low_stock = Product.objects.filter(quantity__lt=20)
    feedbacks = Feedback.objects.all()[:4]  # Get latest 4 feedbacks
    
    total_revenue = sum([o.final_amount for o in orders])
    total_orders = orders.count()
    total_products = products.count()
    total_customers = customers.count()
    staff_count = UserProfile.objects.filter(role='staff', is_approved=True).count()
    
    # Get top 5 selling products
    top_products = []
    from django.db.models import Sum, Q
    for product in products:
        total_sold = Order.objects.filter(product=product).aggregate(Sum('quantity'))['quantity__sum'] or 0
        if total_sold > 0:
            top_products.append((product, total_sold))
    top_products = sorted(top_products, key=lambda x: x[1], reverse=True)[:5]
    
    # Calculate average rating
    avg_rating = 0
    total_feedback = feedbacks.count()
    if total_feedback > 0:
        avg_rating = sum([f.rating for f in feedbacks]) / total_feedback

    return render(request, 'core/admin_dashboard.html', {
        'total_revenue': total_revenue,
        'total_orders': total_orders,
        'total_products': total_products,
        'total_customers': total_customers,
        'staff_count': staff_count,
        'pending_staff': pending_staff,
        'low_stock': low_stock,
        'top_products': top_products,
        'orders': orders,
        'feedbacks': feedbacks,
        'avg_rating': avg_rating,
        'total_feedback': total_feedback,
    })


# ✅ ORDER DETAILS PAGE
def order_details(request):
    if not request.user.is_authenticated or not is_staff_or_admin(request.user):
        return redirect('dashboard')
    orders = Order.objects.all().order_by('-created_at')
    return render(request, 'core/order_details.html', {'orders': orders})


# ✅ STAFF DETAILS & APPROVAL PAGE
def staff_details(request):
    if not request.user.is_authenticated or get_user_role(request.user) != 'admin':
        return redirect('dashboard')
    all_staff = UserProfile.objects.filter(role='staff')
    pending_staff = all_staff.filter(is_approved=False)
    approved_staff = all_staff.filter(is_approved=True)
    
    return render(request, 'core/staff_details.html', {
        'all_staff': all_staff,
        'pending_staff': pending_staff,
        'approved_staff': approved_staff
    })


# ✅ LOGOUT
def logout_view(request):
    logout(request)
    return redirect('landing')


# ✅ PRODUCT LIST
def product_list(request):
    products = Product.objects.all()
    return render(request, 'core/products.html', {'products': products})


# ✅ CUSTOMER LIST
def customer_list(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if not is_staff_or_admin(request.user):
        return redirect('dashboard')
    customers = Customer.objects.all()
    return render(request, 'core/customers.html', {'customers': customers})


# ✅ ORDER LIST
def order_list(request):
    if not request.user.is_authenticated:
        return redirect('login')

    role = get_user_role(request.user)
    customer = get_customer_for_user(request.user)

    if role == 'customer':
        orders = Order.objects.filter(customer=customer).order_by('-created_at') if customer else Order.objects.none()
    else:
        orders = Order.objects.all().order_by('-created_at')

    return render(request, 'core/orders.html', {
        'orders': orders,
        'is_customer_view': role == 'customer'
    })


# ✅ CREATE ORDER
def create_order(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if not is_staff_or_admin(request.user):
        return redirect('dashboard')
    
    products = Product.objects.all()
    customers = Customer.objects.all()

    if request.method == "POST":
        # Handle both customer selection and quick add-to-cart scenario
        customer_id = request.POST.get("customer")
        product_id = request.POST.get("product_id") or request.POST.get("product")
        quantity = int(request.POST.get("quantity") or 1)
        payment_method = request.POST.get("payment_method") or "Cash"

        # If customer_id not provided, try to get customer by user email or create one
        if not customer_id:
            try:
                customer = Customer.objects.get(email=request.user.email)
            except Customer.DoesNotExist:
                # Create a customer if one doesn't exist
                customer = Customer.objects.create(
                    name=request.user.get_full_name() or request.user.username,
                    email=request.user.email,
                    phone='0000000000'  # Default phone, can be updated by user later
                )
        else:
            customer = Customer.objects.get(id=customer_id)
        
        product = Product.objects.get(id=product_id)

        if product.quantity < quantity:
            return render(request, 'core/create_order.html', {
                'products': products,
                'customers': customers,
                'error': 'Not enough stock'
            })

        # 💰 CALCULATIONS
        total_price = product.price * quantity

        discount = Decimal('0.00')
        if total_price > Decimal('1000'):
            discount = total_price * Decimal('0.10')

        price_after_discount = total_price - discount
        gst_amount = price_after_discount * Decimal('0.18')
        final_amount = price_after_discount + gst_amount

        # 📦 UPDATE STOCK
        product.quantity -= quantity
        product.save()

        # 🗂 SAVE ORDER
        Order.objects.create(
            customer=customer,
            product=product,
            quantity=quantity,
            total_price=total_price,
            discount=discount,
            gst_amount=gst_amount,
            final_amount=final_amount,
            payment_method=payment_method
        )

        # 📧 EMAIL
        send_mail(
            'Your Order Invoice',
            f"""
Hello {customer.name},

Your order has been placed successfully!

Product: {product.name}
Quantity: {quantity}

Total: ₹{total_price}
Discount: ₹{discount}
GST: ₹{gst_amount}
Final Amount: ₹{final_amount}
Payment: {payment_method}

Thank you!
""",
            'your_email@gmail.com',
            [customer.email],
            fail_silently=True
        )

        return redirect('thank_you')

    return render(request, 'core/create_order.html', {
        'products': products,
        'customers': customers
    })


def vendors_page(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if not is_staff_or_admin(request.user):
        return redirect('dashboard')

    message = None
    error = None

    if request.method == "POST":
        action_type = request.POST.get("action_type")

        if action_type == "create_vendor":
            name = request.POST.get("name", "").strip()
            if not name:
                error = "Vendor name is required."
            else:
                Vendor.objects.create(
                    name=name,
                    company_name=request.POST.get("company_name", "").strip(),
                    email=request.POST.get("email", "").strip(),
                    phone=request.POST.get("phone", "").strip(),
                    address=request.POST.get("address", "").strip(),
                    gst_number=request.POST.get("gst_number", "").strip(),
                )
                message = "Vendor added successfully."

        elif action_type == "record_purchase":
            vendor_id = request.POST.get("vendor")
            product_id = request.POST.get("product")
            invoice_number = request.POST.get("invoice_number", "").strip()
            notes = request.POST.get("notes", "").strip()

            try:
                quantity = int(request.POST.get("quantity", "0"))
                unit_cost = Decimal(request.POST.get("unit_cost", "0"))
            except Exception:
                quantity = 0
                unit_cost = Decimal("0")

            if not vendor_id or not product_id or quantity <= 0 or unit_cost <= 0:
                error = "Vendor, product, quantity, and unit cost are required."
            else:
                vendor = get_object_or_404(Vendor, id=vendor_id)
                product = get_object_or_404(Product, id=product_id)
                total_cost = unit_cost * quantity

                VendorPurchase.objects.create(
                    vendor=vendor,
                    product=product,
                    quantity=quantity,
                    unit_cost=unit_cost,
                    total_cost=total_cost,
                    invoice_number=invoice_number,
                    notes=notes,
                )

                product.quantity += quantity
                product.vendor = vendor
                product.save()
                message = "Purchase bill recorded and stock updated."

    from django.db.models import Count, Sum

    vendors = Vendor.objects.annotate(
        total_products=Count('products', distinct=True),
        total_purchase_value=Sum('purchases__total_cost'),
        total_purchase_orders=Count('purchases')
    ).order_by('name')
    purchases = VendorPurchase.objects.select_related('vendor', 'product').order_by('-purchased_at')[:20]

    total_vendor_spend = VendorPurchase.objects.aggregate(total=Sum('total_cost'))['total'] or 0

    return render(request, 'core/vendors.html', {
        'vendors': vendors,
        'products': Product.objects.all().order_by('name'),
        'purchases': purchases,
        'message': message,
        'error': error,
        'total_vendors': vendors.count(),
        'total_vendor_spend': int(total_vendor_spend),
        'total_purchase_bills': VendorPurchase.objects.count(),
    })


def vendor_purchase_invoice(request, purchase_id):
    if not request.user.is_authenticated:
        return redirect('login')
    if not is_staff_or_admin(request.user):
        return redirect('dashboard')

    purchase = get_object_or_404(
        VendorPurchase.objects.select_related('vendor', 'product'),
        id=purchase_id
    )
    return render(request, 'core/vendor_purchase_invoice.html', {
        'purchase': purchase
    })


# ✅ INVOICE PAGE
def invoice(request, order_id):
    if not request.user.is_authenticated:
        return redirect('login')

    order = get_object_or_404(Order, id=order_id)
    role = get_user_role(request.user)
    customer = get_customer_for_user(request.user)

    if role == 'customer' and (not customer or order.customer_id != customer.id):
        return redirect('orders')

    return render(request, 'core/invoice_page.html', {'order': order})


# ✅ THANK YOU PAGE
def thank_you(request):
    return render(request, 'core/thank_you.html')


# ✅ LOGIN (STEP 1)
def verify_otp(request):
    if request.method == "POST":
        entered_otp = request.POST.get('otp')
        username = request.session.get('username')

        otp_obj = UserOTP.objects.filter(username=username).last()

        if otp_obj and str(otp_obj.otp) == entered_otp:

            user = User.objects.get(username=username)
            login(request, user)

            profile = UserProfile.objects.get(user=user)

            # ❌ block only staff
            if profile.role == 'staff' and not profile.is_approved:
               return render(request, 'core/login.html', {
                    'error': 'Wait for admin approval',
                    'role': 'staff'   # 🔥 THIS LINE FIXES YOUR ISSUE
                })

            # ✅ redirect
            if profile.role == 'admin':
                return redirect('admin_dashboard')

            elif profile.role == 'staff':
                return redirect('staff_dashboard')

            else:
                return redirect('dashboard')

    return render(request, 'core/verify_otp.html')


# ✅ REGISTER
def register(request):
    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role')

        if User.objects.filter(username=username).exists():
            return render(request, 'core/register.html', {
                'error': 'Username already exists'
            })

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        # 🔥 CREATE PROFILE PROPERLY
        if role == 'staff':
            UserProfile.objects.create(
                user=user,
                role='staff',
                is_approved=False
            )
        else:
            UserProfile.objects.create(
                user=user,
                role='customer',
                is_approved=True
            )

        return redirect(f'/login/?role={role}')

    return render(request, 'core/register.html')


# ✅ LOGIN FUNCTION (SIMPLE VERSION)
def user_login(request):
    role = request.GET.get('role','customer')   # 🔥 important

    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:

            # 🔐 SAVE USERNAME FOR OTP
            request.session['username'] = username

            # 🔢 GENERATE OTP
            otp = random.randint(1000, 9999)
            UserOTP.objects.create(username=username, otp=otp)

            # 📧 SEND OTP VIA EMAIL
            try:
                send_mail(
                    subject='Your Login OTP - Inventory Billing System',
                    message=f'Your OTP is: {otp}\n\nThis OTP is valid for 10 minutes.\n\nDo not share this OTP with anyone.',
                    from_email='noreply@inventorybilling.com',
                    recipient_list=[user.email],
                    html_message=f"""
                    <html>
                        <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
                            <div style="background-color: white; border-radius: 10px; padding: 30px; max-width: 500px; margin: 0 auto; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                                <h2 style="color: #6366f1; margin-bottom: 20px;">🔐 Your Login OTP</h2>
                                
                                <p style="color: #333; margin-bottom: 20px;">Hello {user.first_name or user.username},</p>
                                
                                <div style="background-color: #f0f0f0; padding: 20px; border-radius: 8px; text-align: center; margin: 30px 0;">
                                    <p style="color: #666; margin: 0; font-size: 14px;">Your OTP Code:</p>
                                    <p style="color: #6366f1; font-size: 36px; font-weight: bold; margin: 10px 0; letter-spacing: 5px;">{otp}</p>
                                    <p style="color: #999; margin: 0; font-size: 12px;">Valid for 10 minutes</p>
                                </div>

                                <p style="color: #666; margin-bottom: 10px;">Please use this OTP to complete your login:</p>
                                <ul style="color: #666; margin: 20px 0;">
                                    <li>✓ Do not share this OTP with anyone</li>
                                    <li>✓ Inventory Billing will never ask for your OTP</li>
                                    <li>✓ If you didn't request this, ignore this email</li>
                                </ul>

                                <p style="color: #999; margin-top: 30px; font-size: 12px;">Inventory Billing System | All Rights Reserved © 2024</p>
                            </div>
                        </body>
                    </html>
                    """,
                    fail_silently=False
                )
                print(f"✓ OTP sent to {user.email}")
            except Exception as e:
                print(f"✗ Error sending OTP: {e}")
                # OTP created even if email fails
                print(f"OTP (Fallback): {otp}")

            return redirect('verify_otp')

        else:
            return render(request, 'core/login.html', {
                'error': 'Invalid credentials',
                'role': role
            })

    return render(request, 'core/login.html', {'role': role})

# ✅ LOGOUT
def user_logout(request):
    logout(request)
    return redirect('login')

from django.db.models import Sum
from .models import Product, Customer, Order, UserProfile

def admin_dashboard(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if get_user_role(request.user) != 'admin':
        return redirect('dashboard')

    # 📊 Stats
    total_orders = Order.objects.count()
    total_customers = Customer.objects.count()
    total_products = Product.objects.count()

    total_revenue = Order.objects.aggregate(
        total=Sum('final_amount')
    )['total'] or 0

    # 🧑‍💼 Staff
    staff_list = UserProfile.objects.filter(role='staff')
    pending_staff = UserProfile.objects.filter(role='staff', is_approved=False)

    # 📦 Low stock
    low_stock = Product.objects.filter(quantity__lt=5)

    context = {
        'total_orders': total_orders,
        'total_customers': total_customers,
        'total_products': total_products,
        'total_revenue': total_revenue,
        'staff_list': staff_list,
        'pending_staff': pending_staff,
        'low_stock': low_stock,
    }

    return render(request, 'core/admin_dashboard.html', context)


def approve_staff(request, id):
    if not request.user.is_authenticated or get_user_role(request.user) != 'admin':
        return redirect('dashboard')
    staff = UserProfile.objects.get(id=id)
    staff.is_approved = True
    staff.save()
    return redirect('admin_dashboard')

def staff_dashboard(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if not is_staff_or_admin(request.user):
        return redirect('dashboard')

    from django.db.models import Count, Sum, Max

    products = Product.objects.all().order_by('quantity', 'name')
    orders = Order.objects.select_related('customer', 'product').order_by('-created_at')
    customers = Customer.objects.annotate(
        total_orders=Count('order'),
        total_spent=Sum('order__final_amount'),
        last_order_date=Max('order__created_at')
    ).order_by('-total_orders', 'name')
    low_stock = products.filter(quantity__lt=10)

    critical_stock_count = products.filter(quantity__lt=5).count()
    healthy_stock_count = products.filter(quantity__gte=25).count()
    total_revenue = orders.aggregate(total=Sum('final_amount'))['total'] or 0

    return render(request, 'core/staff_dashboard.html', {
        'products': products,
        'orders': orders[:10],
        'customers': customers[:10],
        'low_stock': low_stock[:8],
        'total_products': products.count(),
        'total_customers': customers.count(),
        'total_orders': orders.count(),
        'total_revenue': int(total_revenue),
        'critical_stock_count': critical_stock_count,
        'healthy_stock_count': healthy_stock_count,
    })


