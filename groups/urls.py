from django.urls import path
from .views import (
    GroupListCreateView,
    GroupDetailView,
    AddMemberView,
    RemoveMemberView
)

urlpatterns = [
    path('', GroupListCreateView.as_view(), name='group-list-create'),
    path('<int:pk>/', GroupDetailView.as_view(), name='group-detail'),
    path('<int:pk>/members/', AddMemberView.as_view(), name='add-member'),
    path('<int:pk>/members/<int:user_id>/', RemoveMemberView.as_view(), name='remove-member'),
]
