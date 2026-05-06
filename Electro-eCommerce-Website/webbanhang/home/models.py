from django.db import models
from django.contrib.auth.models import User

# 1. Bảng Danh mục 
class Category(models.Model):
    name = models.CharField(max_length=100)
    def __str__(self):
        return self.name
    
# 2. Bảng Sản phẩm (Đảm bảo định nghĩa TRƯỚC OrderItem)
class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE) 
    name = models.CharField(max_length=200)      
    price = models.IntegerField(default=0, verbose_name="Giá bán hiện tại")
    
    # --- CÁC TRƯỜNG MỚI VŨ YÊU CẦU ---
    old_price = models.IntegerField(default=0, verbose_name="Giá gốc (chưa giảm)")
    discount = models.IntegerField(default=0, verbose_name="Giảm giá (%)")
    specifications = models.TextField(blank=True, null=True, verbose_name="Thông số kỹ thuật")
    short_description = models.TextField(blank=True, null=True, verbose_name="Mô tả ngắn (Cạnh giá tiền)")
    description = models.TextField(blank=True, null=True, verbose_name="Bài viết giới thiệu (Tab Description)")
    # --------------------------------
    
    image = models.ImageField(upload_to='products/')
    date_added = models.DateTimeField(auto_now_add=True) 

    def __str__(self):
        return self.name  

# 3. Đơn hàng (Cái giỏ) - PHẢI VIẾT SÁT LỀ TRÁI
class Order(models.Model):
    customer = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    date_ordered = models.DateTimeField(auto_now_add=True)
    complete = models.BooleanField(default=False, null=True, blank=False) 
    transaction_id = models.CharField(max_length=200, null=True)

    def __str__(self):
        return str(self.id)  

    @property
    def get_cart_total(self):
        orderitems = self.orderitem_set.all()
        total = sum([item.get_total for item in orderitems])
        return total

    @property
    def get_cart_items(self):
        orderitems = self.orderitem_set.all()
        total = sum([item.quantity for item in orderitems])
        return total

# 4. Chi tiết đơn hàng
class OrderItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, blank=True, null=True)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, blank=True, null=True)
    quantity = models.IntegerField(default=0, null=True, blank=True)
    date_added = models.DateTimeField(auto_now_add=True)    

    @property
    def get_total(self):
        total = self.product.price * self.quantity
        return total

# 5. Bảng chứa nhiều ảnh phụ cho 1 sản phẩm
class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/gallery/', verbose_name="Ảnh phụ")

    def __str__(self):
        return f"Ảnh phụ của {self.product.name}"

# 6. Bảng chứa Review của khách hàng
class Review(models.Model):
    product = models.ForeignKey(Product, related_name='reviews', on_delete=models.CASCADE)
    user_name = models.CharField(max_length=100, verbose_name="Tên người đánh giá")
    rating = models.IntegerField(default=5, verbose_name="Số sao (1-5)")
    comment = models.TextField(verbose_name="Nội dung đánh giá")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review của {self.user_name} cho {self.product.name}"