from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from .models import Category, Product, Order, OrderItem, ProductImage, Review, ProductColor, News, RevenueReport
from django.db.models import Sum, Count, Avg
from django.db.models.functions import TruncDate
from django.template.response import TemplateResponse

# Cấu hình Header
admin.site.site_header = "Hệ thống quản trị Electro"
admin.site.site_title = "Quản trị Electro"
admin.site.index_title = "Bảng điều khiển Electro"

# Đăng ký User/Group
admin.site.unregister(User) 
admin.site.unregister(Group) 
admin.site.register(User, UserAdmin)
admin.site.register(Group, GroupAdmin)

# Các Inlines
class ProductColorInline(admin.TabularInline):
    model = ProductColor
    extra = 0 

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 4 

class ReviewInline(admin.TabularInline):
    model = Review
    extra = 0 

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'get_total')
    can_delete = False

# Các Admins
@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'date_added')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductColorInline, ProductImageInline, ReviewInline]
    list_display = ('name', 'price', 'so_luong', 'is_available', 'category', 'date_added')
    list_editable = ('so_luong', 'is_available',)
    
    search_fields = ('name',)
    
    list_filter = ('category', 'is_available')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'status', 'get_total_price', 'date_ordered')
    list_filter = ('complete', 'status', 'date_ordered')
    inlines = [OrderItemInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).filter(complete=True)
    
    def get_total_price(self, obj):
        return "{:,.0f}đ".format(obj.get_cart_total).replace(',', '.')
    
#báo cáo doanh thu
@admin.register(RevenueReport)
class RevenueReportAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def changelist_view(self, request, extra_context=None):
        completed_orders = Order.objects.filter(status='Completed')
        total_orders = completed_orders.count()
        total_revenue = sum([order.get_cart_total for order in completed_orders])

        avg_rating = Review.objects.aggregate(Avg('rating'))['rating__avg'] or 0

        total_customers = User.objects.filter(is_superuser=False).count()

        daily_orders = completed_orders.annotate(
            date=TruncDate('date_ordered')
        ).values('date').order_by('date').distinct()

        dates = []
        revenues = []
        for entry in daily_orders:
            day_orders = completed_orders.filter(date_ordered__date=entry['date'])
            day_sum = sum([o.get_cart_total for o in day_orders])
            dates.append(entry['date'].strftime("%d/%m/%Y"))
            revenues.append(day_sum)

        context = dict(
            self.admin_site.each_context(request),
            title="Phân Tích Doanh Thu Chi Tiết",
            total_orders=total_orders,
            total_revenue=total_revenue,
            avg_rating=round(avg_rating, 1),
            total_customers=total_customers,
            chart_dates=dates,
            chart_revenues=revenues,
        )
        return TemplateResponse(request, "admin/revenue_report.html", context)

admin.site.register(Category)
admin.site.register(Review)

