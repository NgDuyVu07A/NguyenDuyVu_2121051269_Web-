from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from .models import Product, Order, OrderItem, News, Wishlist, UserProfile, Category
from .forms import RegistrationForm
from django.db.models import F, FloatField, ExpressionWrapper, Sum, Q
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
import json

import requests
from django.core.files.base import ContentFile

# 1. TRANG CHỦ
def index(request):
    phones = Product.objects.filter(category__name__icontains='thoại')
    tablets = Product.objects.filter(category__name__icontains='bảng')
    laptops = Product.objects.filter(category__name__icontains='laptop')
    accessories = Product.objects.filter(category__name__icontains='phụ kiện')
    watches = Product.objects.filter(category__name__icontains='Đồng hồ')
    earphones = Product.objects.filter(category__name__icontains='tai nghe')
    
    search_query = request.GET.get('q')
    
    if search_query:
        phones = phones.filter(name__icontains=search_query)
        tablets = tablets.filter(name__icontains=search_query)
        laptops = laptops.filter(name__icontains=search_query)
        accessories = accessories.filter(name__icontains=search_query)
        watches = watches.filter(name__icontains=search_query)
        earphones = earphones.filter(name__icontains=search_query)

    phones = phones.order_by('?')[:20]
    tablets = tablets.order_by('?')[:20]
    laptops = laptops.order_by('?')[:20]
    accessories = accessories.order_by('?')[:20]
    watches = watches.order_by('?')[:20]
    earphones = earphones.order_by('?')[:20]

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
    hot_products = Product.objects.filter(discount__gt=0).order_by('-discount')

    phones = hot_products.filter(category__name__icontains='Điện thoại')
    tablets = hot_products.filter(category__name__icontains='Máy tính bảng')
    laptops = hot_products.filter(category__name__icontains='Laptop')
    watches = hot_products.filter(category__name__icontains='Đồng hồ')
    cameras = hot_products.filter(Q(category__name__icontains='Camera') | Q(category__name__icontains='Máy ảnh'))
    earphones = hot_products.filter(category__name__icontains='Tai nghe')
    accessories = hot_products.filter(category__name__icontains='Phụ kiện')

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
        'watches': watches,
        'cameras': cameras,
        'earphones': earphones,
        'accessories': accessories,
        'cartItems': cartItems,
        'wishlist_product_ids': wishlist_product_ids
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


# 4. THÊM GIỎ HÀNG BÊN NGOÀI GIAO DIỆN 
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
            items_to_buy = order.orderitem_set.filter(product__id__in=selected_product_ids)
        else:
            items_to_buy = order.orderitem_set.all()

        for item in items_to_buy:
            if item.quantity > item.product.so_luong:
                messages.error(request, f'Thanh toán thất bại! Sản phẩm "{item.product.name}" chỉ còn {item.product.so_luong} chiếc trong kho. Vui lòng giảm số lượng!')
                return redirect('cart')

        if selected_items_post:
            selected_product_ids = selected_items_post.split(',')
            unselected_items = order.orderitem_set.exclude(product__id__in=selected_product_ids)
            if unselected_items.exists():
                new_order = Order.objects.create(customer=request.user, complete=False)
                for item in unselected_items:
                    item.order = new_order
                    item.save()

        for item in order.orderitem_set.all():
            san_pham = item.product
            san_pham.so_luong = san_pham.so_luong - item.quantity
            
            if san_pham.so_luong <= 0:
                san_pham.so_luong = 0
                san_pham.is_available = False 
                
            san_pham.save()

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


# 10. CẬP NHẬT GIỎ HÀNG TRONG TRANG CART 
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

def laptop(request):
    laptops = Product.objects.filter(category__name__icontains='Laptop')
    
    brand = request.GET.get('brand')
    if brand:
        laptops = laptops.filter(name__icontains=brand)

    need = request.GET.get('need')
    if need:
        laptops = laptops.filter(Q(short_description__icontains=need) | Q(name__icontains=need) | Q(specifications__icontains=need))

    price = request.GET.get('price')
    if price == 'duoi-10t': laptops = laptops.filter(price__lt=10000000)
    elif price == '10t-15t': laptops = laptops.filter(price__gte=10000000, price__lt=15000000)
    elif price == '15t-20t': laptops = laptops.filter(price__gte=15000000, price__lt=20000000)
    elif price == '20t-25t': laptops = laptops.filter(price__gte=20000000, price__lt=25000000)
    elif price == '25t-30t': laptops = laptops.filter(price__gte=25000000, price__lt=30000000)
    elif price == 'tren-30t': laptops = laptops.filter(price__gte=30000000)

    cpu = request.GET.get('cpu')
    if cpu:
        laptops = laptops.filter(specifications__icontains=cpu)

    ram = request.GET.get('ram')
    if ram:
        laptops = laptops.filter(Q(specifications__icontains=f'{ram}') | Q(name__icontains=f'{ram}'))

    rom = request.GET.get('rom')
    if rom:
        laptops = laptops.filter(Q(specifications__icontains=f'{rom}') | Q(name__icontains=f'{rom}'))

    vga = request.GET.get('vga')
    if vga == 'Onboard':
        laptops = laptops.filter(Q(specifications__icontains='Onboard') | Q(specifications__icontains='Integrated') | Q(specifications__icontains='Intel Iris') | Q(specifications__icontains='Intel UHD') | Q(specifications__icontains='AMD Radeon Graphics'))
    elif vga:
        laptops = laptops.filter(specifications__icontains=vga)

    sort = request.GET.get('sort')
    if sort == 'price_asc': laptops = laptops.order_by('price')
    elif sort == 'price_desc': laptops = laptops.order_by('-price')
    elif sort == 'hot': laptops = laptops.order_by('-discount')
    elif sort == 'pop': laptops = laptops.order_by('-id')

    cartItems = 0
    wishlist_product_ids = []
    if request.user.is_authenticated:
        order, created = Order.objects.get_or_create(customer=request.user, complete=False)
        cartItems = order.get_cart_items
        wishlist_product_ids = Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)

    context = {
        'laptops': laptops,
        'cartItems': cartItems,
        'wishlist_product_ids': wishlist_product_ids
    }
    return render(request, 'home/laptop.html', context)

def earphone(request):
    earphones = Product.objects.filter(category__name__icontains='Tai nghe')
    
    brand = request.GET.get('brand')
    if brand:
        earphones = earphones.filter(name__icontains=brand)

    need = request.GET.get('need')
    if need:
        if need == 'bluetooth': earphones = earphones.filter(Q(specifications__icontains='Bluetooth') | Q(name__icontains='Bluetooth'))
        elif need == 'co-day': earphones = earphones.filter(Q(specifications__icontains='Có dây') | Q(specifications__icontains='3.5mm'))
        elif need == 'chup-tai': earphones = earphones.filter(Q(specifications__icontains='Chụp tai') | Q(specifications__icontains='Over-ear') | Q(name__icontains='Chụp tai'))
        elif need == 'nhet-tai': earphones = earphones.filter(Q(specifications__icontains='Nhét tai') | Q(specifications__icontains='In-ear'))
        elif need == 'gaming': earphones = earphones.filter(Q(specifications__icontains='Gaming') | Q(name__icontains='Gaming'))
        elif need == 'the-thao': earphones = earphones.filter(Q(specifications__icontains='Thể thao') | Q(specifications__icontains='Sport'))

    price = request.GET.get('price')
    if price == 'duoi-500k': earphones = earphones.filter(price__lt=500000)
    elif price == '500k-1t': earphones = earphones.filter(price__gte=500000, price__lt=1000000)
    elif price == '1t-2t': earphones = earphones.filter(price__gte=1000000, price__lt=2000000)
    elif price == '2t-5t': earphones = earphones.filter(price__gte=2000000, price__lt=5000000)
    elif price == 'tren-5t': earphones = earphones.filter(price__gte=5000000)

    feature = request.GET.get('feature')
    if feature == 'anc': earphones = earphones.filter(Q(specifications__icontains='ANC') | Q(specifications__icontains='Chống ồn'))
    elif feature == 'waterproof': earphones = earphones.filter(Q(specifications__icontains='IPX') | Q(specifications__icontains='Chống nước'))
    elif feature == 'mic': earphones = earphones.filter(specifications__icontains='Mic')

    sort = request.GET.get('sort')
    if sort == 'price_asc': earphones = earphones.order_by('price')
    elif sort == 'price_desc': earphones = earphones.order_by('-price')
    elif sort == 'hot': earphones = earphones.order_by('-discount')
    elif sort == 'pop': earphones = earphones.order_by('-id')

    cartItems = 0
    wishlist_product_ids = []
    if request.user.is_authenticated:
        order, created = Order.objects.get_or_create(customer=request.user, complete=False)
        cartItems = order.get_cart_items
        wishlist_product_ids = Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)

    context = {
        'earphones': earphones,
        'cartItems': cartItems,
        'wishlist_product_ids': wishlist_product_ids
    }
    return render(request, 'home/earphone.html', context)

def watch(request):
    watches = Product.objects.filter(category__name__icontains='Đồng hồ')
    
    brand = request.GET.get('brand')
    if brand:
        if brand.lower() == 'apple' or brand.lower() == 'watch':
            watches = watches.filter(Q(name__icontains='Apple') | Q(name__icontains='Watch'))
        else:
            watches = watches.filter(name__icontains=brand)

    need = request.GET.get('need')
    if need:
        if need == 'smartwatch': watches = watches.filter(Q(specifications__icontains='Smartwatch') | Q(name__icontains='thông minh'))
        elif need == 'smartband': watches = watches.filter(Q(specifications__icontains='Vòng đeo tay') | Q(name__icontains='Vòng đeo tay') | Q(name__icontains='Band'))
        elif need == 'kids': watches = watches.filter(Q(specifications__icontains='Trẻ em') | Q(name__icontains='Trẻ em') | Q(name__icontains='Kids'))
        elif need == 'strap': watches = watches.filter(Q(name__icontains='Dây') | Q(category__name__icontains='Dây'))
        elif need == 'sport': watches = watches.filter(Q(specifications__icontains='Thể thao') | Q(name__icontains='Sport') | Q(name__icontains='Garmin') | Q(name__icontains='Coros'))
        elif need == 'call': watches = watches.filter(Q(specifications__icontains='Nghe gọi') | Q(specifications__icontains='Mic'))
        elif need == 'health': watches = watches.filter(Q(specifications__icontains='Huyết áp') | Q(specifications__icontains='Nhịp tim') | Q(specifications__icontains='SPO2'))

    price = request.GET.get('price')
    if price == 'duoi-1t': watches = watches.filter(price__lt=1000000)
    elif price == '1t-2t': watches = watches.filter(price__gte=1000000, price__lt=2000000)
    elif price == '2t-5t': watches = watches.filter(price__gte=2000000, price__lt=5000000)
    elif price == '5t-10t': watches = watches.filter(price__gte=5000000, price__lt=10000000)
    elif price == 'tren-10t': watches = watches.filter(price__gte=10000000)

    special = request.GET.get('special')
    if special == 'waterproof': watches = watches.filter(Q(specifications__icontains='IP') | Q(specifications__icontains='Chống nước') | Q(specifications__icontains='ATM'))
    elif special == 'esim': watches = watches.filter(Q(specifications__icontains='eSIM') | Q(name__icontains='LTE'))
    elif special == 'gps': watches = watches.filter(specifications__icontains='GPS')

    sort = request.GET.get('sort')
    if sort == 'price_asc': watches = watches.order_by('price')
    elif sort == 'price_desc': watches = watches.order_by('-price')
    elif sort == 'hot': watches = watches.order_by('-discount') # Sắp xếp theo % giảm giá
    elif sort == 'pop': watches = watches.order_by('-id') # Hoặc tiêu chí phổ biến khác của em

    cartItems = 0
    wishlist_product_ids = []
    if request.user.is_authenticated:
        order, created = Order.objects.get_or_create(customer=request.user, complete=False)
        cartItems = order.get_cart_items
        wishlist_product_ids = Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)

    context = {
        'watches': watches,
        'cartItems': cartItems,
        'wishlist_product_ids': wishlist_product_ids
    }
    return render(request, 'home/watch.html', context)


def camera(request):
    cameras = Product.objects.filter(Q(category__name__icontains='Camera') | Q(category__name__icontains='Máy ảnh'))
    
    brand = request.GET.get('brand')
    if brand:
        cameras = cameras.filter(name__icontains=brand)

    need = request.GET.get('need')
    if need:
        if need == 'security': cameras = cameras.filter(Q(specifications__icontains='an ninh') | Q(name__icontains='an ninh') | Q(name__icontains='Ezviz') | Q(name__icontains='Imou'))
        elif need == 'action': cameras = cameras.filter(Q(specifications__icontains='action') | Q(name__icontains='Action') | Q(name__icontains='GoPro'))
        elif need == 'dashcam': cameras = cameras.filter(Q(specifications__icontains='hành trình') | Q(name__icontains='hành trình'))
        elif need == 'digital': cameras = cameras.filter(Q(specifications__icontains='kỹ thuật số') | Q(name__icontains='Máy ảnh'))
        elif need == 'gimbal': cameras = cameras.filter(Q(specifications__icontains='gimbal') | Q(name__icontains='Gimbal') | Q(name__icontains='Chống rung'))
        elif need == 'flycam': cameras = cameras.filter(Q(specifications__icontains='flycam') | Q(name__icontains='Flycam') | Q(name__icontains='Drone'))

    price = request.GET.get('price')
    if price == 'duoi-1t': cameras = cameras.filter(price__lt=1000000)
    elif price == '1t-2t': cameras = cameras.filter(price__gte=1000000, price__lt=2000000)
    elif price == '2t-5t': cameras = cameras.filter(price__gte=2000000, price__lt=5000000)
    elif price == '5t-10t': cameras = cameras.filter(price__gte=5000000, price__lt=10000000)
    elif price == '10t-20t': cameras = cameras.filter(price__gte=10000000, price__lt=20000000)
    elif price == 'tren-20t': cameras = cameras.filter(price__gte=20000000)

    resolution = request.GET.get('resolution')
    if resolution:
        cameras = cameras.filter(specifications__icontains=resolution)

    feature = request.GET.get('feature')
    if feature == 'waterproof': cameras = cameras.filter(Q(specifications__icontains='Chống nước') | Q(specifications__icontains='IP'))
    elif feature == 'stabilization': cameras = cameras.filter(Q(specifications__icontains='Chống rung') | Q(specifications__icontains='OIS') | Q(specifications__icontains='RockSteady'))
    elif feature == 'night_vision': cameras = cameras.filter(Q(specifications__icontains='Hồng ngoại') | Q(specifications__icontains='Quay đêm'))
    elif feature == 'ai_tracking': cameras = cameras.filter(Q(specifications__icontains='AI') | Q(specifications__icontains='Theo dõi chuyển động'))

    sort = request.GET.get('sort')
    if sort == 'price_asc': cameras = cameras.order_by('price')
    elif sort == 'price_desc': cameras = cameras.order_by('-price')
    elif sort == 'hot': cameras = cameras.order_by('-discount')
    elif sort == 'pop': cameras = cameras.order_by('-id')

    cartItems = 0
    wishlist_product_ids = []
    if request.user.is_authenticated:
        order, created = Order.objects.get_or_create(customer=request.user, complete=False)
        cartItems = order.get_cart_items
        wishlist_product_ids = Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)

    context = {
        'cameras': cameras, # Chú ý: Biến truyền ra là 'cameras'
        'cartItems': cartItems,
        'wishlist_product_ids': wishlist_product_ids
    }
    return render(request, 'home/camera.html', context)

def accessory(request):
    accessories = Product.objects.filter(category__name__icontains='Phụ kiện')
    
    brand = request.GET.get('brand')
    if brand:
        accessories = accessories.filter(name__icontains=brand)

    need = request.GET.get('need')
    if need:
        if need == 'powerbank': accessories = accessories.filter(Q(specifications__icontains='Pin') | Q(name__icontains='Sạc dự phòng'))
        elif need == 'charger': accessories = accessories.filter(Q(specifications__icontains='Sạc') | Q(name__icontains='Cáp') | Q(name__icontains='Sạc'))
        elif need == 'case': accessories = accessories.filter(Q(specifications__icontains='Ốp') | Q(name__icontains='Ốp') | Q(name__icontains='Bao da'))
        elif need == 'screen_protector': accessories = accessories.filter(Q(specifications__icontains='Dán') | Q(name__icontains='Dán màn hình') | Q(name__icontains='Kính cường lực'))
        elif need == 'mouse_keyboard': accessories = accessories.filter(Q(name__icontains='Chuột') | Q(name__icontains='Bàn phím') | Q(name__icontains='Mouse') | Q(name__icontains='Keyboard'))
        elif need == 'hub': accessories = accessories.filter(Q(name__icontains='Hub') | Q(name__icontains='Cổng chuyển'))
        elif need == 'network': accessories = accessories.filter(Q(category__name__icontains='Mạng') | Q(name__icontains='Router') | Q(name__icontains='Wifi'))
        elif need == 'smarthome': accessories = accessories.filter(Q(category__name__icontains='Smarthome') | Q(name__icontains='Thông minh'))
        elif need == 'apple_acc': accessories = accessories.filter(Q(name__icontains='Apple') | Q(name__icontains='AirTag') | Q(name__icontains='Pencil') | Q(name__icontains='MagSafe'))

    price = request.GET.get('price')
    if price == 'duoi-100k': accessories = accessories.filter(price__lt=100000)
    elif price == '100k-300k': accessories = accessories.filter(price__gte=100000, price__lt=300000)
    elif price == '300k-500k': accessories = accessories.filter(price__gte=300000, price__lt=500000)
    elif price == '500k-1t': accessories = accessories.filter(price__gte=500000, price__lt=1000000)
    elif price == '1t-2t': accessories = accessories.filter(price__gte=1000000, price__lt=2000000)
    elif price == 'tren-2t': accessories = accessories.filter(price__gte=2000000)

    sort = request.GET.get('sort')
    if sort == 'price_asc': accessories = accessories.order_by('price')
    elif sort == 'price_desc': accessories = accessories.order_by('-price')
    elif sort == 'hot': accessories = accessories.order_by('-discount')
    elif sort == 'pop': accessories = accessories.order_by('-id')

    cartItems = 0
    wishlist_product_ids = []
    if request.user.is_authenticated:
        order, created = Order.objects.get_or_create(customer=request.user, complete=False)
        cartItems = order.get_cart_items
        wishlist_product_ids = Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)

    context = {
        'accessories': accessories, 
        'cartItems': cartItems,
        'wishlist_product_ids': wishlist_product_ids
    }
    return render(request, 'home/accessory.html', context)

# 13. TRANG TÌM KIẾM
def search_view(request):
    query = request.GET.get('q', '')
    products = Product.objects.all()

    if query:
        products = products.filter(
            Q(name__icontains=query) | 
            Q(short_description__icontains=query) |
            Q(category__name__icontains=query)
        )

    sort = request.GET.get('sort')
    if sort == 'price_asc':
        products = products.order_by('price')
    elif sort == 'price_desc':
        products = products.order_by('-price')
    else:
        products = products.order_by('-id')

    cartItems = 0
    wishlist_product_ids = []
    if request.user.is_authenticated:
        order, created = Order.objects.get_or_create(customer=request.user, complete=False)
        cartItems = order.get_cart_items
        wishlist_product_ids = Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)

    context = {
        'products': products,
        'query': query,
        'cartItems': cartItems,
        'wishlist_product_ids': wishlist_product_ids
    }
    
    return render(request, 'home/search.html', context)

# 14. XÁC NHẬN NHẬN HÀNG
@login_required(login_url='login')
def confirm_receipt(request, order_id):
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    
    if order.status == 'Shipping':
        order.status = 'Completed'
        order.save()
        messages.success(request, 'Cảm ơn bạn! Đơn hàng đã được xác nhận giao thành công.')
    else:
        messages.error(request, 'Lỗi: Đơn hàng này không ở trạng thái chờ nhận hàng.')
        
    return redirect('profile')