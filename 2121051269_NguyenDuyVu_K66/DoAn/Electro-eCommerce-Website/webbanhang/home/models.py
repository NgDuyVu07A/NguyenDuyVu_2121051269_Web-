from django.db import models
from django.contrib.auth.models import User
from ckeditor.fields import RichTextField  
from django.db.models.signals import post_save
from django.dispatch import receiver

# 1. Bảng Danh mục 
class Category(models.Model):
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name
        
    class Meta:
        verbose_name = 'Danh mục'
        verbose_name_plural = 'Danh mục'
    
# 2. Bảng Sản phẩm 
class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE) 
    name = models.CharField(max_length=200)      
    price = models.IntegerField(default=0, verbose_name="Giá bán hiện tại")
    
    old_price = models.IntegerField(default=0, verbose_name="Giá gốc (chưa giảm)")
    discount = models.IntegerField(default=0, verbose_name="Giảm giá (%)")
    
    specifications = models.TextField(blank=True, null=True, verbose_name="Thông số kỹ thuật (Trang chủ)")
    
    detailed_specifications = RichTextField(blank=True, null=True, verbose_name="Bảng Thông số kỹ thuật (Tab Thông số)")
    
    short_description = models.TextField(blank=True, null=True, verbose_name="Mô tả ngắn (Cạnh giá tiền)")
    
    description = RichTextField(blank=True, null=True, verbose_name="Bài viết giới thiệu (Tab Mô tả chi tiết)")
    
    image = models.ImageField(upload_to='products/')
    date_added = models.DateTimeField(auto_now_add=True) 

    is_available = models.BooleanField(default=True, verbose_name="Còn hàng")

    so_luong = models.IntegerField(default=50, verbose_name="Số lượng tồn kho")

    def __str__(self):
        return self.name  

    class Meta:
        verbose_name = 'Sản phẩm'
        verbose_name_plural = 'Sản phẩm'

# 3. Đơn hàng 
class Order(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Chờ xác nhận'),
        ('Shipping', 'Đang giao hàng'),
        ('Completed', 'Hoàn thành (Đã nhận)'),
        ('Cancelled', 'Đã hủy'),
    )

    customer = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    date_ordered = models.DateTimeField(auto_now_add=True)
    complete = models.BooleanField(default=False, null=True, blank=False) 
    transaction_id = models.CharField(max_length=200, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')

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
        
    class Meta:
        verbose_name = 'Đơn hàng'
        verbose_name_plural = 'Đơn hàng'

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
        
    class Meta:
        verbose_name = 'Chi tiết đơn hàng'
        verbose_name_plural = 'Chi tiết đơn hàng'

# 5. Bảng chứa nhiều ảnh phụ cho 1 sản phẩm
class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/gallery/', verbose_name="Ảnh phụ")

    def __str__(self):
        return f"Ảnh phụ của {self.product.name}"
        
    class Meta:
        verbose_name = 'Ảnh phụ sản phẩm'
        verbose_name_plural = 'Ảnh phụ sản phẩm'

# 6. Bảng chứa Review của khách hàng
class Review(models.Model):
    product = models.ForeignKey(Product, related_name='reviews', on_delete=models.CASCADE)
    user_name = models.CharField(max_length=100, verbose_name="Tên người đánh giá")
    rating = models.IntegerField(default=5, verbose_name="Số sao (1-5)")
    comment = models.TextField(verbose_name="Nội dung đánh giá")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review của {self.user_name} cho {self.product.name}"
        
    class Meta:
        verbose_name = 'Đánh giá khách hàng'
        verbose_name_plural = 'Đánh giá khách hàng'
    
class News(models.Model):
    title = models.CharField(max_length=255, verbose_name="Tiêu đề tin tức")
    image = models.ImageField(upload_to='news/', verbose_name="Ảnh tin tức")
    date_added = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Tin tức'
        verbose_name_plural = "Tin tức sản phẩm"

class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE) 
    added_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"
        
    class Meta:
        verbose_name = 'Danh sách yêu thích'
        verbose_name_plural = 'Danh sách yêu thích'
    
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15, null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True)
    dob = models.DateField(null=True, blank=True) # Ngày sinh
    address = models.CharField(max_length=255, null=True, blank=True)
    password_updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.user.username
        
    class Meta:
        verbose_name = 'Hồ sơ người dùng'
        verbose_name_plural = 'Hồ sơ người dùng'

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    # Kiểm tra nếu user đã có profile thì mới lưu, tránh bị lỗi crash
    if hasattr(instance, 'userprofile'):
        instance.userprofile.save()

class ProductColor(models.Model):
    product = models.ForeignKey(Product, related_name='colors', on_delete=models.CASCADE)
    name = models.CharField(max_length=50, verbose_name="Tên màu (VD: Cam, Xám, Tím)")
    image = models.ImageField(upload_to='products/colors/', null=True, blank=True, verbose_name="Ảnh thu nhỏ màu này")
    price = models.IntegerField(default=0, verbose_name="Giá bán của màu này")

    class Meta:
        verbose_name = 'Màu sắc sản phẩm'
        verbose_name_plural = 'Màu sắc sản phẩm'

    def __str__(self):
        return f"{self.name} - {self.product.name}"
    
    @property
    def get_avg_rating(self):
        from django.db.models import Avg
        avg = self.reviews.aggregate(Avg('rating'))['rating__avg']
        return round(avg, 1) if avg else 0

    @property
    def get_rating_stars(self):
        return round(self.get_avg_rating)
    
class RevenueReport(Order):
    class Meta:
        proxy = True 
        verbose_name = 'Báo cáo doanh thu'
        verbose_name_plural = 'Báo cáo doanh thu'