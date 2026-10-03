"""Routes supplied by Task 2."""

from django.urls import path

from portfolio.holdings_views import holdings


urlpatterns = [
    path("portfolios/<str:portfolio_id>/holdings", holdings, name="holdings"),
]
