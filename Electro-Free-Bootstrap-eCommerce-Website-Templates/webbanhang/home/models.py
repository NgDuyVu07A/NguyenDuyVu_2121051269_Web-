from django.db import models
from django.contrib.auth.models import User

# 1. Bảng Danh mục (Ví dụ: Laptop, Điện thoại...)
class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

# 2. Bảng Sản phẩm
class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE) # Liên kết với danh mục
    name = models.CharField(max_length=200)      # Tên sản phẩm
    price = models.IntegerField(default=0)       # Giá tiền
    image = models.ImageField(upload_to='products/') # Ảnh sản phẩm
    date_added = models.DateTimeField(auto_now_add=True) # Ngày đăng

    def __str__(self):
        return self.name
    
    # 3. Đơn hàng (Cái giỏ)
class Order(models.Model):
    customer = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    date_ordered = models.DateTimeField(auto_now_add=True)
    complete = models.BooleanField(default=False, null=True, blank=False) # False = Giỏ hàng, True = Đã thanh toán
    transaction_id = models.CharField(max_length=200, null=True)

    def __str__(self):
        return str(self.id)

    # Tính tổng tiền của cả giỏ hàng
    @property
    def get_cart_total(self):
        orderitems = self.orderitem_set.all()
        total = sum([item.get_total for item in orderitems])
        return total

    # Tính tổng số lượng sản phẩm trong giỏ
    @property
    def get_cart_items(self):
        orderitems = self.orderitem_set.all()
        total = sum([item.quantity for item in orderitems])
        return total

# 4. Chi tiết đơn hàng (Từng món trong giỏ)
class OrderItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, blank=True, null=True)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, blank=True, null=True)
    quantity = models.IntegerField(default=0, null=True, blank=True)
    date_added = models.DateTimeField(auto_now_add=True)

    # Tính tổng tiền của từng món (Giá x Số lượng)
    @property
    def get_total(self):
        total = self.product.price * self.quantity
        return total