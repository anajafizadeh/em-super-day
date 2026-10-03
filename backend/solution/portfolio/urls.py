from django.urls import path

from . import views

app_name = 'portfolio'

urlpatterns = [
    path('portfolios/<str:portfolio_id>', views.portfolio_detail, name='portfolio-detail'),
]
