
from django.contrib import admin
from django.urls import path
from django.conf.urls import url, include
from apps.goods.views import IndexView,DetailView, ShowDetail
app_name = 'goods'
urlpatterns = [
    url(r'^$',IndexView.as_view(),name='index'),
    url(r'^goods/(?P<goods_id>\d+)$', DetailView.as_view(),name='detail'),
    url(r'^list/(?P<type_id>\d+)/(?P<page>\d+)$', ShowDetail.as_view(), name='list'),
]
