from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from .models import Product, Order, OrderItem
from .forms import RegistrationForm

# 1. TRANG CHỦ
def index(request):
    products = Product.objects.all()
    search_query = request.GET.get('q') # Lấy từ khóa tìm kiếm
    if search_query:
        # Lọc sản phẩm theo tên
        products = products.filter(name__icontains=search_query)

    context = {'products': products}
    return render(request, 'home/index.html', context)

# 2. CHI TIẾT SẢN PHẨM
def detail(request, id):
    product = get_object_or_404(Product, id=id)
    context = {'product': product}
    return render(request, 'home/detail.html', context)

# 3. ĐĂNG KÝ
def register(request):
    form = RegistrationForm()
    
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save() # Lưu tài khoản
            return HttpResponseRedirect('/') # Về trang chủ
            
    context = {'form': form}
    return render(request, 'home/register.html', context)

# 4. THÊM VÀO GIỎ HÀNG
@login_required(login_url='/login/') 
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    # Lấy hoặc tạo đơn hàng
    order, created = Order.objects.get_or_create(customer=request.user, complete=False)
    
    # Lấy hoặc tạo sản phẩm trong đơn
    order_item, created = OrderItem.objects.get_or_create(order=order, product=product)
    
    # Tăng số lượng
    order_item.quantity += 1
    order_item.save()
    
    # Quay lại trang cũ
    return redirect(request.META.get('HTTP_REFERER', '/'))

# 5. XEM GIỎ HÀNG
@login_required(login_url='/login/')
def cart(request):
    if request.user.is_authenticated:
        customer = request.user
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
        items = order.orderitem_set.all()
    else:
        items = []
        order = {'get_cart_total': 0, 'get_cart_items': 0}

    context = {'items': items, 'order': order}
    return render(request, 'home/cart.html', context)

# 6. THANH TOÁN (CHECKOUT)
@login_required(login_url='/login/')
def checkout(request):
    customer = request.user
    order, created = Order.objects.get_or_create(customer=customer, complete=False)
    items = order.orderitem_set.all()

    if request.method == 'POST':
        # Khi bấm nút "Đặt hàng"
        order.complete = True # Đánh dấu đơn hàng đã xong
        order.save()
        return render(request, 'home/success.html') # Chuyển sang trang thành công

    context = {'items': items, 'order': order}
    return render(request, 'home/checkout.html', context)