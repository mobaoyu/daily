from django.shortcuts import render,redirect
from django.urls import reverse
from django.views.generic import View
from django.core.paginator import Paginator
from django_redis import get_redis_connection
from apps.order.models import OrderGoods
from apps.goods.models import Goods,GoodsSKU,GoodsType,IndexGoodsBanner,IndexPromotionBanner,IndexTypeGoodsBanner
# Create your views here.

class IndexView(View):
    def get(self,request):
        '''显示首页'''
        # 1.获取全部商品分类信息
        types = GoodsType.objects.all()
        # 2.获取首页轮播商品信息
        goods_banner = IndexGoodsBanner.objects.all().order_by('index')

        # 3.获取活动商品信息
        promotion_banner = IndexPromotionBanner.objects.all().order_by('index')
        # 4.获取首页分类商品展示信息
        # type_goods_banners = IndexTypeGoodsBanner.objects.all()
        for type in types:
            # 获取某一类商品下的图片展示信息
            image_baners = IndexTypeGoodsBanner.objects.filter(type=type,display_type=1).order_by('index')
            # 获取某一类商品下的文字展示信息
            title_baners = IndexTypeGoodsBanner.objects.filter(type=type,display_type=0).order_by('index')
        # 动态给type增加属性，保存某类商品的图片展示信息和文字展示信息
            type.image_baners = image_baners
            type.title_baners = title_baners
        # 5.获取用户购物车中商品信息
        user = request.user
        cart_count = 0
        if user.is_authenticated:
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' %user.id
            cart_count = conn.hlen(cart_key)




        # 组织模板上下文
        context = {'types':types,
                   'goods_banner':goods_banner,
                   'promotion_banner':promotion_banner,
                   # 'type_goods_banners':type_goods_banners,
                   'cart_count':cart_count}
        return render(request,'index.html',context)

#/goods/商品ID
class DetailView(View):
    def get(self, request, goods_id):
        try:
            sku = GoodsSKU.objects.get(id=goods_id)
        except GoodsSKU.DoesNotExist :
            return redirect(reverse('goods:index'))
        #获取商品分类信息
        types = GoodsType.objects.all()
        #获取商品评论信息
        sku_orders = OrderGoods.objects.filter(sku=sku).exclude(comment='')
        #获取新品信息
        new_skus = GoodsSKU.objects.filter(type=sku.type).order_by('-creat_time')[:2]
        #获取其他同类商品信息
        some_sku = GoodsSKU.objects.filter(goods=sku.goods).exclude(id=sku.id)
        # 5.获取用户购物车中商品信息
        user = request.user
        cart_count = 0
        if user.is_authenticated:
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_count = conn.hlen(cart_key)

            conn = get_redis_connection('default')
            history_key='history_%d' %user.id
            conn.lrem(history_key, 0, goods_id)
            conn.lpush(history_key, goods_id)
            conn.ltrim(history_key, 0, 4)
        # 组织上下文
        context ={'sku':sku,
                  'types':types,
                  'sku_orders':sku_orders,
                  'new_skus':new_skus,
                  'cart_count':cart_count,
                  'some_sku':some_sku}
        return render(request,'detail.html',context)

# /list/分类ID/页码/sort='排序方式'
class ShowDetail(View):
    def get(self, request, type_id, page):
        # 获取该种类下商品信息
        try:
            type = GoodsType.objects.get(id=type_id)
        except GoodsType.DoesNotExist:
        # 种类不存在
            return redirect(reverse('goods:index'))


        # 获取所有商品分类信息
        types = GoodsType.objects.all()
        # 获取排列方式
        sort = request.GET.get('sort')
        # 根据排序方式查找
        if sort == 'price':
            skus = GoodsSKU.objects.filter(type=type).order_by('price')
        elif sort == 'hot':
            skus = GoodsSKU.objects.filter(type=type).order_by('-sales')
        else:
            skus = GoodsSKU.objects.filter(type=type).order_by('-id')

        # 分页
        paginator = Paginator(skus, 1)
        # 获取第 page页的内容
        try:
            page = int(page)
        except Exception as e:
            page = 1
        if page > paginator.num_pages:
            page = 1
        skus_page = paginator.page(page)

        # 控制页码，只显示5页
        total_page = paginator.num_pages
        # 1.总页数小于5页，显示所有页码
        if total_page < 5:
            pages = range(1, total_page+1)
        # 2.当前页是前3页，显示1-5页
        elif page <=3:
            pages = range(1, 6)

        # 3.当前页是倒数后3页，显示后5页
        elif total_page - page <= 2:
            pages = range(total_page-4, total_page+1)
        # 4.其他情况显示当前页前两页后两页和当前页
        else:
            pages = range(page-2, page+3)
        # 获取新品信息
        # print(pages)
        new_skus = GoodsSKU.objects.filter(type=type).order_by('-creat_time')[:2]

        user = request.user
        cart_count = 0
        if user.is_authenticated:
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_count = conn.hlen(cart_key)

        # 组织模板上下文
        context = {
            'type':type,
            'types':types,
            'skus_page':skus_page,
            'new_skus':new_skus,
            'cart_count':cart_count,
            'sort':sort,
            'pages':pages
        }
        return render(request,'list.html', context)