from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
# CHÚ Ý: Đã bổ sung Category vào đây
from .models import Product, Order, OrderItem, News, Wishlist, UserProfile, Category
from .forms import RegistrationForm
from django.db.models import F, FloatField, ExpressionWrapper, Sum, Q
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
import json

# --- THƯ VIỆN CẦN THIẾT ĐỂ TẢI ẢNH TỪ BÊN NGOÀI ---
import requests
from django.core.files.base import ContentFile

# 1. TRANG CHỦ
def index(request):
    # Khởi tạo QuerySet cơ bản lấy toàn bộ sản phẩm theo danh mục
    phones = Product.objects.filter(category__name__icontains='thoại')
    tablets = Product.objects.filter(category__name__icontains='bảng')
    laptops = Product.objects.filter(category__name__icontains='laptop')
    accessories = Product.objects.filter(category__name__icontains='phụ kiện')
    watches = Product.objects.filter(category__name__icontains='đồng hồ')
    earphones = Product.objects.filter(category__name__icontains='tai nghe')
    
    search_query = request.GET.get('q')
    
    # NẾU CÓ TÌM KIẾM: Lọc từ khóa trước khi cắt số lượng (Tránh lỗi Slice của Django)
    if search_query:
        phones = phones.filter(name__icontains=search_query)
        tablets = tablets.filter(name__icontains=search_query)
        laptops = laptops.filter(name__icontains=search_query)
        accessories = accessories.filter(name__icontains=search_query)
        watches = watches.filter(name__icontains=search_query)
        earphones = earphones.filter(name__icontains=search_query)

    # TRỘN NGẪU NHIÊN & GIỚI HẠN HIỂN THỊ 20 SẢN PHẨM (Thực hiện cuối cùng)
    phones = phones.order_by('?')[:20]
    tablets = tablets.order_by('?')[:20]
    laptops = laptops.order_by('?')[:20]
    accessories = accessories.order_by('?')[:20]
    watches = watches.order_by('?')[:20]
    earphones = earphones.order_by('?')[:20]

    # Khối đề xuất "Dành cho bạn" lấy ngẫu nhiên 20 sản phẩm tổng hợp
    recommended_products = Product.objects.all().order_by('?')[:20]
    
    cartItems = 0
    wishlist_product_ids = []
    
    if request.user.is_authenticated:
        order, created = Order.objects.get_or_create(customer=request.user, complete=False)
        cartItems = order.get_cart_items
        wishlist_product_ids = Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)
    
    context = {
        'phones': phones, 
        'tablets': tablets, 
        'laptops': laptops, 
        'accessories': accessories, 
        'watches': watches,
        'earphones': earphones,
        'recommended_products': recommended_products,
        'cartItems': cartItems,
        'wishlist_product_ids': wishlist_product_ids
    }
          
    return render(request, 'home/index.html', context)


# 2. TRANG KHUYẾN MÃI HOT
def hot_promotions(request):
    discounted_products = Product.objects.filter(old_price__gt=F('price')).annotate(
        discount_percent=ExpressionWrapper(
            (F('old_price') - F('price')) * 100.0 / F('old_price'),
            output_field=FloatField()
        )
    ).order_by('-discount_percent')

    phones = discounted_products.filter(category__name__icontains='thoại')
    tablets = discounted_products.filter(category__name__icontains='bảng')
    
    cartItems = 0
    wishlist_product_ids = []
    
    if request.user.is_authenticated:
        order, created = Order.objects.get_or_create(customer=request.user, complete=False)
        cartItems = order.get_cart_items
        wishlist_product_ids = Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)
        
    context = {
        'phones': phones,
        'tablets': tablets,
        'cartItems': cartItems,
        'wishlist_product_ids': wishlist_product_ids,
    }
    return render(request, 'home/hot_promotions.html', context)


# 3. CHI TIẾT SẢN PHẨM
def detail(request, id):
    product = get_object_or_404(Product, id=id)
    cartItems = 0
    if request.user.is_authenticated:
        order, created = Order.objects.get_or_create(customer=request.user, complete=False)
        cartItems = order.get_cart_items
    
    news_list = News.objects.all()[:5]
    context = {'product': product, 'cartItems': cartItems, 'news_list': news_list}
    return render(request, 'home/detail.html', context)


# 4. THÊM GIỎ HÀNG BÊN NGOÀI GIAO DIỆN (NÚT ADD TO CART)
@login_required(login_url='/login/')
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    order, created = Order.objects.get_or_create(customer=request.user, complete=False)
    order_item, created = OrderItem.objects.get_or_create(order=order, product=product)
    
    order_item.quantity += 1
    order_item.save()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'message': f'Đã thêm {product.name} vào giỏ',
            'cart_items': order.get_cart_items 
        })
    
    return redirect('cart')


# 5. THANH TOÁN
@login_required(login_url='/login/')
def checkout(request):
    order, created = Order.objects.get_or_create(customer=request.user, complete=False)
    cartItems = order.get_cart_items

    if request.method == 'POST':
        selected_items_post = request.POST.get('selected_items', '')
        if selected_items_post:
            selected_product_ids = selected_items_post.split(',')
            unselected_items = order.orderitem_set.exclude(product__id__in=selected_product_ids)
            if unselected_items.exists():
                new_order = Order.objects.create(customer=request.user, complete=False)
                for item in unselected_items:
                    item.order = new_order
                    item.save()

        order.complete = True
        order.save()
        return render(request, 'home/success.html')

    selected_items_param = request.GET.get('selected_items', '')
    if selected_items_param:
        selected_product_ids = selected_items_param.split(',')
        items = order.orderitem_set.filter(product__id__in=selected_product_ids)
    else:
        items = order.orderitem_set.all()

    custom_cart_total = sum([item.get_total for item in items])

    context = {
        'items': items,
        'order': order,
        'custom_cart_total': custom_cart_total,
        'selected_items_param': selected_items_param,
        'cartItems': cartItems,
    }
    return render(request, 'home/checkout.html', context)


# 6. ĐĂNG KÝ
def register(request):
    form = RegistrationForm()
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect('/')
    return render(request, 'home/register.html', {'form': form})


# 7. GIỎ HÀNG
@login_required(login_url='/login/')
def cart(request):
    order, created = Order.objects.get_or_create(customer=request.user, complete=False)
    return render(request, 'home/cart.html', {'items': order.orderitem_set.all(), 'order': order, 'cartItems': order.get_cart_items})


# 8. TRANG CÁ NHÂN (PROFILE)
@login_required(login_url='login')
def profile(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_info':
            request.user.last_name = request.POST.get('last_name')
            request.user.first_name = request.POST.get('first_name')
            request.user.email = request.POST.get('email')
            request.user.save()

            profile_obj, created = UserProfile.objects.get_or_create(user=request.user)
            profile_obj.phone = request.POST.get('phone')
            profile_obj.gender = request.POST.get('gender')
            profile_obj.address = request.POST.get('address')
            
            dob = request.POST.get('dob')
            if dob:
                profile_obj.dob = dob
                
            profile_obj.save()

            messages.success(request, 'Cập nhật thông tin cá nhân thành công!')
            return redirect('profile')
            
        elif action == 'change_password':
            old_pass = request.POST.get('old_password')
            new_pass = request.POST.get('new_password')
            confirm_pass = request.POST.get('confirm_password')
            
            if new_pass != confirm_pass:
                messages.error(request, 'Mật khẩu xác nhận không khớp!')
            elif request.user.check_password(old_pass):
                request.user.set_password(new_pass)
                request.user.save()
                from django.utils import timezone
                profile_obj, created = UserProfile.objects.get_or_create(user=request.user)
                profile_obj.password_updated_at = timezone.now()
                profile_obj.save()
                update_session_auth_hash(request, request.user) 
                messages.success(request, 'Đổi mật khẩu thành công!')
            else:
                messages.error(request, 'Mật khẩu hiện tại không chính xác!')
                
            return redirect('profile')

        elif action == 'update_address':
            profile_obj, created = UserProfile.objects.get_or_create(user=request.user)
            profile_obj.address = request.POST.get('address')
            profile_obj.save()
            messages.success(request, 'Cập nhật sổ địa chỉ thành công!')
            return redirect('profile')

    cartItems = 0
    if request.user.is_authenticated:
        order, created = Order.objects.get_or_create(customer=request.user, complete=False)
        cartItems = order.get_cart_items

    orders = Order.objects.filter(customer=request.user, complete=True).order_by('-date_ordered')
    total_orders = orders.count()
    total_spent = sum(order.get_cart_total for order in orders)
    wishlist_items = Wishlist.objects.filter(user=request.user)
    
    context = { 
        'orders': orders,
        'total_orders': total_orders,
        'total_spent': total_spent,
        'wishlist_items': wishlist_items,
        'cartItems': cartItems,
    }
    return render(request, 'home/profile.html', context)


# 9. THÊM VÀO YÊU THÍCH
@login_required(login_url='login')
def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    wishlist_item = Wishlist.objects.filter(user=request.user, product=product).first()
    
    if wishlist_item:
        wishlist_item.delete()
        return JsonResponse({'status': 'removed', 'message': f'Đã xóa {product.name} khỏi yêu thích'})
    else:
        Wishlist.objects.create(user=request.user, product=product)
        return JsonResponse({'status': 'added', 'message': f'Đã thêm {product.name} vào yêu thích'})


# 10. CẬP NHẬT GIỎ HÀNG TRONG TRANG CART BẰNG AJAX
@login_required(login_url='/login/')
def update_item(request):
    data = json.loads(request.body)
    product_id = data['productId']
    action = data['action']

    customer = request.user
    product = Product.objects.get(id=product_id)
    order, created = Order.objects.get_or_create(customer=customer, complete=False)
    order_item, created = OrderItem.objects.get_or_create(order=order, product=product)

    if action == 'add':
        order_item.quantity += 1
    elif action == 'remove':
        order_item.quantity -= 1
    elif action == 'delete':
        order_item.quantity = 0 

    order_item.save()

    if order_item.quantity <= 0:
        order_item.delete()

    return JsonResponse({
        'item_quantity': order_item.quantity if order_item.id else 0,
        'item_total': order_item.get_total if order_item.id else 0,
        'cart_total': order.get_cart_total,
        'cart_items': order.get_cart_items 
    }, safe=False)


# 11. TRANG DANH MỤC ĐIỆN THOẠI
def phone(request):
    phones = Product.objects.filter(category__name__icontains='thoại')
    
    brand = request.GET.get('brand')
    if brand:
        if brand.lower() == 'apple' or brand.lower() == 'iphone':
            phones = phones.filter(Q(name__icontains='iPhone') | Q(name__icontains='Apple'))
        else:
            phones = phones.filter(name__icontains=brand)

    price = request.GET.get('price')
    if price == 'duoi-2t':
        phones = phones.filter(price__lt=2000000)
    elif price == '2t-4t':
        phones = phones.filter(price__gte=2000000, price__lt=4000000)
    elif price == '4t-7t':
        phones = phones.filter(price__gte=4000000, price__lt=7000000)
    elif price == '7t-13t':
        phones = phones.filter(price__gte=7000000, price__lt=13000000)
    elif price == '13t-20t':
        phones = phones.filter(price__gte=13000000, price__lt=20000000)
    elif price == 'tren-20t':
        phones = phones.filter(price__gte=20000000)

    need = request.GET.get('need')
    if need == 'game' or need == 'cau-hinh-cao':
        phones = phones.filter(Q(specifications__icontains='Snapdragon 8') | Q(specifications__icontains='Apple A') | Q(specifications__icontains='Dimensity 9'))
    elif need == 'pin':
        phones = phones.filter(Q(specifications__icontains='5000') | Q(specifications__icontains='6000') | Q(specifications__icontains='7000') | Q(specifications__icontains='8000') | Q(specifications__icontains='9000'))
    elif need == 'camera' or need == 'livestream':
        phones = phones.filter(Q(specifications__icontains='OIS') | Q(specifications__icontains='4K'))
    elif need == 'fold':
        phones = phones.filter(Q(specifications__icontains='gập') | Q(name__icontains='Fold') | Q(name__icontains='Flip'))

    chip = request.GET.get('chip')
    if chip == 'apple_a':
        phones = phones.filter(Q(specifications__icontains='Apple A') | Q(name__icontains='iPhone'))
    elif chip == 'snapdragon':
        phones = phones.filter(specifications__icontains='Snapdragon')
    elif chip == 'mediatek':
        phones = phones.filter(Q(specifications__icontains='MediaTek') | Q(specifications__icontains='Dimensity'))
    elif chip == 'exynos':
        phones = phones.filter(specifications__icontains='Exynos')

    phone_type = request.GET.get('type')
    if phone_type == 'android':
        phones = phones.filter(specifications__icontains='Android')
    elif phone_type == 'iphone':
        phones = phones.filter(Q(specifications__icontains='iOS') | Q(name__icontains='iPhone'))
    elif phone_type == 'feature_phone':
        phones = phones.filter(price__lt=1500000)

    ram = request.GET.get('ram')
    if ram:
        r = ram.replace('gb', '').strip()
        phones = phones.filter(Q(name__icontains=f' {r}GB') | Q(specifications__icontains=f'RAM {r}') | Q(specifications__icontains=f'RAM: {r}') | Q(specifications__icontains=f' {r}GB') | Q(specifications__icontains=f' {r} GB'))

    rom = request.GET.get('rom')
    if rom:
        r = rom.replace('gb', '').replace('tb', '').strip()
        if 'tb' in rom:
            phones = phones.filter(Q(specifications__icontains=f'{r} TB') | Q(specifications__icontains=f'{r}TB') | Q(name__icontains=f'{r}TB'))
        else:
            phones = phones.filter(Q(specifications__icontains=f'{r} GB') | Q(specifications__icontains=f'{r}GB') | Q(name__icontains=f'{r}GB'))

    special = request.GET.get('special')
    if special == '5g':
        phones = phones.filter(Q(name__icontains='5G') | Q(specifications__icontains='5G'))
    elif special == 'wireless_charge':
        phones = phones.filter(specifications__icontains='không dây')
    elif special == 'waterproof':
        phones = phones.filter(Q(specifications__icontains='IP68') | Q(specifications__icontains='kháng nước'))
    elif special == 'fingerprint':
        phones = phones.filter(specifications__icontains='vân tay')
    elif special == 'faceid':
        phones = phones.filter(Q(specifications__icontains='Face ID') | Q(specifications__icontains='khuôn mặt'))

    nfc = request.GET.get('nfc')
    if nfc == 'yes':
        phones = phones.filter(specifications__icontains='NFC')

    camera = request.GET.get('camera')
    if camera == 'portrait':
        phones = phones.filter(specifications__icontains='xóa phông')
    elif camera == 'video4k':
        phones = phones.filter(specifications__icontains='4K')
    elif camera == 'ois':
        phones = phones.filter(Q(specifications__icontains='OIS') | Q(specifications__icontains='chống rung'))
    elif camera == 'zoom':
        phones = phones.filter(specifications__icontains='zoom')

    hz = request.GET.get('hz')
    if hz:
        h = hz.replace('hz', '').strip()
        phones = phones.filter(Q(specifications__icontains=f'{h}Hz') | Q(specifications__icontains=f'{h} Hz'))

    screen_size = request.GET.get('screen_size')
    if screen_size == 'under6':
        phones = phones.filter(Q(specifications__icontains='4.') | Q(specifications__icontains='5.'))
    elif screen_size == 'over6':
        phones = phones.filter(Q(specifications__icontains='6.') | Q(specifications__icontains='7.'))

    screen_type = request.GET.get('screen_type')
    if screen_type == 'notch':
        phones = phones.filter(specifications__icontains='tai thỏ')
    elif screen_type == 'waterdrop':
        phones = phones.filter(specifications__icontains='giọt nước')
    elif screen_type == 'punchhole':
        phones = phones.filter(Q(specifications__icontains='đục lỗ') | Q(specifications__icontains='nốt ruồi'))
    elif screen_type == 'bezelless':
        phones = phones.filter(specifications__icontains='tràn viền')

    new_arrival = request.GET.get('new_arrival')
    if new_arrival == 'true':
        phones = phones.order_by('-id') 

    sort = request.GET.get('sort')
    if sort == 'price_asc':
        phones = phones.order_by('price')
    elif sort == 'price_desc':
        phones = phones.order_by('-price')
    elif sort == 'hot':
        phones = phones.order_by('-discount') 
        
    cartItems = 0
    wishlist_product_ids = [] 
    
    if request.user.is_authenticated:
        order, created = Order.objects.get_or_create(customer=request.user, complete=False)
        cartItems = order.get_cart_items
        wishlist_product_ids = Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)
        
    context = {'phones': phones, 'cartItems': cartItems, 'wishlist_product_ids': wishlist_product_ids}
    return render(request, 'home/phone.html', context)


# 12. TRANG DANH MỤC MÁY TÍNH BẢNG
def tablet(request):
    tablets = Product.objects.filter(category__name__icontains='bảng')
    
    brand = request.GET.get('brand')
    if brand:
        if brand.lower() == 'ipad' or brand.lower() == 'apple':
            tablets = tablets.filter(Q(name__icontains='iPad') | Q(name__icontains='Apple'))
        else:
            tablets = tablets.filter(name__icontains=brand)

    price = request.GET.get('price')
    if price == 'duoi-2t':
        tablets = tablets.filter(price__lt=2000000)
    elif price == '2t-5t':
        tablets = tablets.filter(price__gte=2000000, price__lt=5000000)
    elif price == '5t-8t':
        tablets = tablets.filter(price__gte=5000000, price__lt=8000000)
    elif price == '8t-15t':
        tablets = tablets.filter(price__gte=8000000, price__lt=15000000)
    elif price == 'tren-15t':
        tablets = tablets.filter(price__gte=15000000)

    need = request.GET.get('need')
    if need == 'game':
        tablets = tablets.filter(Q(specifications__icontains='Snapdragon') | Q(specifications__icontains='Apple M') | Q(specifications__icontains='Apple A'))
    elif need == 've-do-hoa':
        tablets = tablets.filter(Q(name__icontains='Pro') | Q(specifications__icontains='Bút') | Q(specifications__icontains='Pencil'))
    elif need == 'doc-sach':
        tablets = tablets.filter(Q(name__icontains='Kindle') | Q(name__icontains='Boox') | Q(specifications__icontains='E-ink') | Q(specifications__icontains='Đọc sách'))
    elif need == 'tre-em':
        tablets = tablets.filter(Q(price__lt=4000000) | Q(specifications__icontains='Kids') | Q(name__icontains='Lite'))
    elif need == 'hoc-tap':
        tablets = tablets.filter(Q(specifications__icontains='10.') | Q(specifications__icontains='11.') | Q(specifications__icontains='Bàn phím'))

    screen = request.GET.get('screen')
    if screen == 'mini':
        tablets = tablets.filter(Q(specifications__icontains='7.') | Q(specifications__icontains='8.') | Q(specifications__icontains='9.'))
    elif screen == 'standard':
        tablets = tablets.filter(Q(specifications__icontains='10.') | Q(specifications__icontains='11.'))
    elif screen == 'large':
        tablets = tablets.filter(Q(specifications__icontains='12.') | Q(specifications__icontains='13.') | Q(specifications__icontains='14.'))

    ram = request.GET.get('ram')
    if ram:
        r = ram.replace('gb', '').strip()
        tablets = tablets.filter(Q(name__icontains=f' {r}GB') | Q(specifications__icontains=f'RAM {r}') | Q(specifications__icontains=f'RAM: {r}') | Q(specifications__icontains=f' {r}GB') | Q(specifications__icontains=f' {r} GB'))

    rom = request.GET.get('rom')
    if rom:
        r = rom.replace('gb', '').replace('tb', '').strip()
        if 'tb' in rom:
            tablets = tablets.filter(Q(specifications__icontains=f'{r} TB') | Q(specifications__icontains=f'{r}TB'))
        else:
            tablets = tablets.filter(Q(specifications__icontains=f'{r} GB') | Q(specifications__icontains=f'{r}GB'))

    new_arrival = request.GET.get('new_arrival')
    if new_arrival == 'true':
        tablets = tablets.order_by('-id') 

    sort = request.GET.get('sort')
    if sort == 'price_asc':
        tablets = tablets.order_by('price')
    elif sort == 'price_desc':
        tablets = tablets.order_by('-price')
    elif sort == 'hot':
        tablets = tablets.order_by('-discount')

    cartItems = 0
    wishlist_product_ids = [] 
    
    if request.user.is_authenticated:
        order, created = Order.objects.get_or_create(customer=request.user, complete=False)
        cartItems = order.get_cart_items
        wishlist_product_ids = Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)
        
    context = {'tablets': tablets, 'cartItems': cartItems, 'wishlist_product_ids': wishlist_product_ids}
    return render(request, 'home/tablet.html', context)


# ==============================================================
# HÀM CÀO DỮ LIỆU TỰ ĐỘNG CỦA EM ĐÂY (Đã sửa lỗi Import Category)
# ==============================================================
def import_real_data(request):
    # 1. Danh sách dữ liệu THỰC TẾ
    real_data = [
        {
            'cat': 'Điện thoại', 'name': 'iPhone 15 Pro Max 256GB', 'price': 29590000, 'old_price': 34990000, 
            'specs': 'Apple A17 Pro\nRAM 8GB\nROM 256GB\n6.7 inches\nPin 4422 mAh',
            'img_url': 'https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/ce:true/plain/https://cellphones.com.vn/media/catalog/product/i/p/iphone-15-pro-max_3.png'
        },
        {
            'cat': 'Điện thoại', 'name': 'Samsung Galaxy S24 Ultra 12GB 256GB', 'price': 27490000, 'old_price': 33990000, 
            'specs': 'Snapdragon 8 Gen 3 For Galaxy\nRAM 12GB\nROM 256GB\n6.8 inches\nPin 5000 mAh',
            'img_url': 'https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/ce:true/plain/https://cellphones.com.vn/media/catalog/product/s/s/ss-s24-ultra-xam-222.png'
        },
        {
            'cat': 'Điện thoại', 'name': 'Xiaomi 14 5G 12GB 256GB', 'price': 19990000, 'old_price': 22990000, 
            'specs': 'Snapdragon 8 Gen 3\nRAM 12GB\nROM 256GB\n6.36 inches\nSạc siêu nhanh 90W',
            'img_url': 'https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/ce:true/plain/https://cellphones.com.vn/media/catalog/product/x/i/xiaomi-14-den_2.png'
        },
        {
            'cat': 'Laptop', 'name': 'Laptop Apple MacBook Air M1 8GB 256GB', 'price': 18490000, 'old_price': 22990000, 
            'specs': 'Apple M1\nRAM 8GB\nSSD 256GB\n13.3 inches\nMac OS',
            'img_url': 'https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/ce:true/plain/https://cellphones.com.vn/media/catalog/product/m/a/macbook-air-m1-2020-gray-600x600_1.png'
        },
        {
            'cat': 'Đồng hồ', 'name': 'Apple Watch Series 9 41mm (GPS)', 'price': 9490000, 'old_price': 10490000, 
            'specs': 'Màn hình OLED\nChống nước 5 ATM\nĐo nhịp tim, SpO2',
            'img_url': 'https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/ce:true/plain/https://cellphones.com.vn/media/catalog/product/a/p/apple-watch-series-9-1.png'
        },
        {
            'cat': 'Tai nghe', 'name': 'Tai nghe Bluetooth AirPods Pro 2', 'price': 5890000, 'old_price': 6990000, 
            'specs': 'Bluetooth 5.3\nChống ồn chủ động ANC\nPin 30 giờ (kèm hộp)',
            'img_url': 'https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/ce:true/plain/https://cellphones.com.vn/media/catalog/product/a/p/airpods-pro-2-type-c_2.png'
        }
    ]

    count = 0
    # 2. Vòng lặp duyệt qua từng sản phẩm để xử lý
    for item in real_data:
        # Tạo danh mục nếu chưa có
        category, created = Category.objects.get_or_create(name=item['cat'])
        
        # Nếu sản phẩm này chưa có trong Database thì mới tạo
        if not Product.objects.filter(name=item['name']).exists():
            product = Product(
                category=category,
                name=item['name'],
                price=item['price'],
                old_price=item['old_price'],
                discount=int(((item['old_price'] - item['price']) / item['old_price']) * 100),
                specifications=item['specs']
            )

            # Tự động tải ảnh từ URL
            try:
                # Đóng giả làm trình duyệt để web không chặn
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                response = requests.get(item['img_url'], headers=headers)
                
                if response.status_code == 200:
                    # Lấy tên file ảnh từ URL (VD: iphone-15-pro-max_3.png)
                    file_name = item['img_url'].split('/')[-1]
                    # Lưu ảnh thẳng vào trường image của model Product
                    product.image.save(file_name, ContentFile(response.content), save=False)
            except Exception as e:
                print(f"Không thể tải ảnh cho {item['name']}: {e}")
            
            # Cuối cùng mới lưu sản phẩm vào Database
            product.save()
            count += 1

    return HttpResponse(f"<h1 style='color:green; font-family:sans-serif;'>THÀNH CÔNG!</h1> <p>Đã nạp tự động <b>{count}</b> sản phẩm THẬT (kèm ảnh gốc) vào Database.</p>")

def laptop(request):
    # Lấy toàn bộ sản phẩm thuộc danh mục "Laptop"
    laptops = Product.objects.filter(category__name__icontains='Laptop')
    
    # BẮT CÁC TỪ KHÓA TỪ MENU THẢ XUỐNG ĐỂ LỌC (BRAND, CHIP, NEED...)
    brand = request.GET.get('brand')
    if brand:
        laptops = laptops.filter(name__icontains=brand)
        
    chip = request.GET.get('chip')
    if chip:
        laptops = laptops.filter(specifications__icontains=chip)
        
    need = request.GET.get('need')
    if need:
        # Tìm trong mô tả ngắn hoặc tên xem có chữ Văn phòng, Gaming... không
        laptops = laptops.filter(short_description__icontains=need) 

    # --- (Phần xử lý giỏ hàng mặc định của em - Nếu em đang dùng hàm logic giỏ hàng nào thì copy xuống đây nhé, thầy ví dụ cấu trúc cơ bản) ---
    cartItems = 0
    if request.user.is_authenticated:
        customer = request.user
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        cartItems = order.get_cart_items
    # -------------------------------------------------------------------------

    context = {
        'laptops': laptops,
        'cartItems': cartItems,
    }
    return render(request, 'home/laptop.html', context)

def earphone(request):
    # Lấy sản phẩm có tên hoặc mô tả chứa "Tai nghe"
    earphones = Product.objects.filter(name__icontains='Tai nghe') 
    
    # Lọc thương hiệu (Brand)
    brand = request.GET.get('brand')
    if brand: earphones = earphones.filter(name__icontains=brand)
    
    # Lọc nhu cầu (Need)
    need = request.GET.get('need')
    if need: earphones = earphones.filter(short_description__icontains=need)
    
    cartItems = 0
    if request.user.is_authenticated:
        order = Order.objects.filter(customer=request.user, complete=False).first()
        cartItems = order.get_cart_items if order else 0
        
    context = {'earphones': earphones, 'cartItems': cartItems}
    return render(request, 'home/earphone.html', context)

def watch(request):
    watches = Product.objects.filter(category__name__icontains='Đồng hồ')
    cartItems = 0
    if request.user.is_authenticated:
        order = Order.objects.filter(customer=request.user, complete=False).first()
        cartItems = order.get_cart_items if order else 0
    return render(request, 'home/watch.html', {'watches': watches, 'cartItems': cartItems})

def camera(request):
    cameras = Product.objects.filter(category__name__icontains='Camera')
    cartItems = 0
    if request.user.is_authenticated:
        order = Order.objects.filter(customer=request.user, complete=False).first()
        cartItems = order.get_cart_items if order else 0
    return render(request, 'home/camera.html', {'cameras': cameras, 'cartItems': cartItems})