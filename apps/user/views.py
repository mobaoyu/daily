from django.shortcuts import render,redirect
from django.urls import reverse
from django.views.generic import View
from apps.user.models import User, Address
from django.conf import settings
from django.core.mail import send_mail
from celery import Celery
from django.contrib.auth import authenticate, login, logout
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
import re
from celery_tasks.tasks import celery_send_email
from utils.mixin import LoginRequiredMixin
from django_redis import get_redis_connection
from apps.goods.models import GoodsSKU
# Create your views here.


class RegisterView(View):
    def get(self, request):
        return render(request, 'register.html')

    def post(self, request):
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')
        allo = request.POST.get('allow')
        if not all([username, password ,email]):
            return render(request, 'register.html', {'err':'数据不完整'})
        if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'err':'邮箱格式不正确'})
        if allo != 'on':
            return render(request, 'register.html', {'err': '需要确认协议'})
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = None
        if user:
            return render(request, 'register.html', {'err':'用户名已存在'})
        user = User.objects.create_user(username, email, password)
        user.is_active = 0
        user.save()

        serializer = Serializer(settings.SECRET_KEY, 3600)
        info = {'confirm': user.id}
        token = serializer.dumps(info)
        token = token.decode('utf-8')

        # subject = '天天生鲜'
        # message = ''
        # sender = settings.EMAIL_FROM
        # receiver =[email]
        # html_message = """<h1>天天生鲜会员%s,欢迎您</h1>请点击以下链接激活账户<br/><a href="http://127.0.0.1:8000/user/active/%s">http://127.0.0.1:8000/user/active/%s</a>""" % (username, token, token)
        # send_mail(subject, message, sender, receiver, html_message=html_message)
        celery_send_email.delay(email, username, token)
        return redirect((reverse('goods:index')))

class ActiveView(View):
    def get(self, request, token):
        print('aa')
        serializer = Serializer(settings.SECRET_KEY, 3600)
        try:
            info = serializer.loads(token)
            user_id = info['confirm']
            user = User.objects.get(id=user_id)
            user.is_active = 1
            user.save()
            return redirect((reverse('goods:index')))
        except SignatureExpired as e:
            return render(request, 'register.html', {'err': '链接已过期'})

class LoginView(View):
    def get(self, request):
        if 'username' in request.COOKIES:
            username = request.COOKIES.get('username')
            password = request.COOKIES.get('password')
            checked = 'checked'
        else:
            username = ''
            checked = ''
            password = ''
        return render(request, 'login.html', {'username':username,'checked':checked,'password':password})

    def post(self, request):
        # 1.获取数据
        username = request.POST.get('username')
        pwd = request.POST.get('pwd')

        # 2.数据校验
        if not all([username, pwd]):
            return render(request, 'login.html', {'err': '数据不完整'})

        user = authenticate(username=username, password=pwd)
        # 好像已经默认检测了is_active标识,is_active为1，且用户名密码正确，则返回对象，is_active为0统统返回None
        # if user is None:
            # return redirect((reverse('goods:index')))
        if user is not None:
            # 保存用户的session信息
            login(request, user)
            # 获取next后的地址，没有则默认跳到首页
            next_url = request.GET.get('next', reverse('goods:index'))
            response = redirect(next_url)
            rem = request.POST.get('remember')
            if rem =='on':
                response.set_cookie('username', username, max_age=3600)
                response.set_cookie('password', pwd, max_age=3600)
            else:
                response.delete_cookie('username')
            return response

        else:
            return render(request, 'login.html', {'err': '账户或密码不正确，或者尚未激活'})
        # No backend authenticated the credentials


class LoginOut(View):
    def get(self, request):

        logout(request)

        return redirect(reverse('goods:index'))


# /user/
class UserInfoView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        address = Address.objects.get_default_address(user)
        #获取用户历史浏览记录
        conn = get_redis_connection('default')

        history_key = 'history_%d' % user.id
        #获取用户最新浏览的5条商品ID
        sku_ids = conn.lrange(history_key, 0, 4)
        #从数据库中查询出商品的具体信息
        #goods_li = GoodsSKU.objects.filter(id__in=sku_ids)
        goods_li=[]
        for id in sku_ids:
            goods = GoodsSKU.objects.get(id=id)
            goods_li.append(goods)
        #组织上下文
        context = {'page':'user',
                   'address':address,
                   'goods_li':goods_li}
        return render(request, 'user_center_info.html',context)


class UserOrderView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'user_center_order.html', {'page':'order'})


class UserSiteView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user
        # try:
        #     address = Address.objects.get(user=user, is_default=True)
        # except Address.DoesNotExist:
        #     address = None
        address = Address.objects.get_default_address(user)
        return render(request, 'user_center_site.html', {'page':'address', 'address': address})

    def post(self, request):
        receiver = request.POST.get('receiver')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')

        if not all([receiver, addr, phone]):
            return render(request, 'user_center_site.html', {'err': '数据不完整'})
        user = request.user
        # try:
        #     address = Address.objects.get(user=user, is_default=True)
        # except Address.DoesNotExist:
        #     address = None
        address = Address.objects.get_default_address(user)

        if address:
            is_default = False
        else:
            is_default = True

        Address.objects.create(user=user,
                               receiver=receiver,
                               addr=addr,
                               zip_code=zip_code,
                               phone=phone,
                               is_default=is_default)
        return redirect(reverse('user:address'))

