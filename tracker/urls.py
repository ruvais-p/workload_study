# urls.py
from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView

urlpatterns = [
    
    path('', views.landing_page, name='landing_page'),
    # Employee URLs
    path('employee/signin/', views.employee_signin_view, name='employee_signin'),
    path('employee/dashboard/', views.employee_dashboard, name='employee_dashboard'),
    
    # Department Head URLs
    path('department-head/signup/', views.department_head_signup_view, name='department_head_signup'),
    path('department-head/signin/', views.department_head_signin_view, name='department_head_signin'),
    path('department-head/dashboard/', views.department_head_dashboard, name='department_head_dashboard'),
    
    # Logout
    path('logout/', LogoutView.as_view(next_page='employee_signin'), name='logout'),
    
    path('employee-timesheets/', views.employee_timesheets_report, name='employee_timesheets_report'),
    path('api/sub-departments/', views.get_sub_departments, name='get_sub_departments'),
    path('download-timesheets/', views.download_timesheets_excel, name='download_timesheets_excel'),
]