from celery import Celery
from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import render
from django.template import loader,RequestContext
from django.views.generic import View
from django_redis import get_redis_connection
#from apps.goods.models import GoodsType,IndexGoodsBanner,IndexPromotionBanner,IndexTypeGoodsBanner
#在任务处理者一端加入初始化
import os
import io
import sys
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'daily.settings')
django.setup()
from apps.goods.models import GoodsType,IndexGoodsBanner,IndexPromotionBanner,IndexTypeGoodsBanner

# 1创建一个Celery对象，第一个函数为对象名字
app = Celery('celery_tasks.tasks', broker='redis://127.0.0.1:6379/8')

# 2定义任务函数
@app.task
def celery_send_email(to_email, username, token):
    # 组织文件信息
    subject = '天天生鲜'
    message = ''
    sender = settings.EMAIL_FROM
    receiver = [to_email]
    html_message = """<h1>天天生鲜会员%s,欢迎您</h1>请点击以下链接激活账户<br/><a href="http://127.0.0.1:8000/user/active/%s">http://127.0.0.1:8000/user/active/%s</a>""" % (
    username, token, token)
    send_mail(subject, message, sender, receiver, html_message=html_message)

@app.task
def static_index():
    # 1.获取全部商品分类信息
    types = GoodsType.objects.all()
    # 2.获取首页轮播商品信息
    goods_banner = IndexGoodsBanner.objects.all().order_by('index')

    # 3.获取活动商品信息
    promotion_banner = IndexPromotionBanner.objects.all().order_by('index')
    # 4.获取首页分类商品展示信息cd
    # type_goods_banners = IndexTypeGoodsBanner.objects.all()
    for type in types:
        # 获取某一类商品下的图片展示信息
        image_baners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1).order_by('index')
        # 获取某一类商品下的文字展示信息
        title_baners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by('index')
        # 动态给type增加属性，保存某类商品的图片展示信息和文字展示信息
        type.image_baners = image_baners
        type.title_baners = title_baners
    # 5.获取用户购物车中商品信息
    # user = request.user
    # cart_count = 0
    # if user.is_authenticated:
    #     conn = get_redis_connection('default')
    #     cart_key = 'cart_%d' % user.id
    #     cart_count = conn.hlen(cart_key)
    # sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='gb18030')
    # 组织模板上下文
    context = {'types': types,
               'goods_banner': goods_banner,
               'promotion_banner': promotion_banner}
               # 'type_goods_banners':type_goods_banners,
               # 'cart_count': cart_count}
    # 使用模板
    #1.加载模板文件
    temp = loader.get_template('static_index.html')
    #2.定义模板上下文
    #context = RequestContext(context)
    #3.模板渲染
    static_index_html = temp.render(context)
    # 生成首页静态文件
    save_path = os.path.join(settings.BASE_DIR, 'static/index.html')
    with open(save_path,'w',encoding='utf-8') as f:
        f.write(static_index_html)


