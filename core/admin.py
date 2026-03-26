from django.contrib import admin
from .models import Product, Customer, Order, UserProfile, Feedback

admin.site.register(Product)
admin.site.register(Customer)
admin.site.register(Order)
admin.site.register(UserProfile)
admin.site.register(Feedback)