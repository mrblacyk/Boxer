from django.urls import path

from . import views

urlpatterns = [
    # Dashboards
    path('', views.index, name='index'),
    path('news/', views.news, name='news'),

    # Machine related URLs
    path('machines/', views.machines, name='machines'),
    path('machines/start/<int:machine_id>/', views.start_machine,
         name='start_machine'),
    path('machines/stop/<int:machine_id>/', views.stop_machine,
         name='stop_machine'),
    path('machines/reset/<int:machine_id>/', views.reset_machine,
         name='reset_machine'),
    path('machines/flag/<int:machine_id>/', views.send_flag,
         name='send_flag'),

    # User handling URLs
    path('login/', views.login_view, name='login_view'),
    path('logout/', views.logout_view, name='logout_view'),
]
