"""Routes contributed by Task 3."""

from django.urls import path

from portfolio.views import performance_history

urlpatterns = [
    path(
        "portfolios/<str:portfolio_id>/performance-history",
        performance_history,
        name="performance-history",
    ),
]
