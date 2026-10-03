from django.urls import include, path

from . import views

app_name = 'portfolio'

urlpatterns = [
    path('portfolios/<str:portfolio_id>', views.portfolio_detail, name='portfolio-detail'),
    path('', include('portfolio.holdings_urls')),
    path('', include('portfolio.performance_urls')),
]
