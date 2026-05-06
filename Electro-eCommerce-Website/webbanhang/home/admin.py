from django.contrib import admin
from .models import Category, Product, Order, OrderItem, ProductImage, Review

# --- TẠO KHUNG (INLINE) ĐỂ NHÚNG VÀO TRANG SẢN PHẨM ---
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 4 # Hiển thị sẵn 4 ô trống để up ảnh phụ

class ReviewInline(admin.TabularInline):
    model = Review
    extra = 0 # Mặc định không hiện sẵn ô review trống nào (khi nào cần thêm thì bấm nút "Add another")

# 1. Cấu hình hiển thị cho Sản phẩm
class ProductAdmin(admin.ModelAdmin):
    # NHÚNG 2 KHUNG VỪA TẠO VÀO DƯỚI CÙNG TRANG SỬA SẢN PHẨM
    inlines = [ProductImageInline, ReviewInline]
    
    # Các cột hiển thị ở danh sách ngoài trang Admin
    list_display = ('name', 'get_price', 'get_old_price', 'discount', 'category')
    
    # Cho phép tìm kiếm nhanh theo tên
    search_fields = ('name',)
    
    # Bộ lọc nhanh bên phải trang
    list_filter = ('category',)

    # Định dạng hiển thị giá bán hiện tại: 10.000.000đ
    def get_price(self, obj):
        return "{:,.0f}đ".format(obj.price).replace(',', '.')
    get_price.short_description = 'Giá bán hiện tại'

    # Định dạng hiển thị giá gốc: 12.000.000đ
    def get_old_price(self, obj):
        return "{:,.0f}đ".format(obj.old_price).replace(',', '.')
    get_old_price.short_description = 'Giá niêm yết (Gốc)'

# 2. Cấu hình hiển thị cho Đơn hàng
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'date_ordered', 'complete', 'transaction_id')
    list_filter = ('complete', 'date_ordered')

# 3. Đăng ký các Model vào hệ thống Admin
admin.site.register(Category)
admin.site.register(Product, ProductAdmin) # Sử dụng ProductAdmin để tùy biến
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem)

# Quản lý Review độc lập (nếu muốn xem toàn bộ review của tất cả sản phẩm)
admin.site.register(Review)