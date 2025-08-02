# urls.py
from django.urls import path
from tracker.views_folder.employee_views import employee_signin_view, employee_dashboard
from tracker.views_folder.department_head_views import department_head_dashboard, department_head_signin_view, department_head_signup_view
from tracker.views_folder.timesheet_views import employee_timesheets_report, get_sub_departments, download_timesheets_excel
from . import views
from django.contrib.auth.views import LogoutView

urlpatterns = [
    
    path('', views.landing_page, name='landing_page'),
    # Employee URLs
    path('employee/signin/', employee_signin_view, name='employee_signin'),
    path('employee/dashboard/', employee_dashboard, name='employee_dashboard'),
    
    # Department Head URLs
    path('department-head/signup/', department_head_signup_view, name='department_head_signup'),
    path('department-head/signin/', department_head_signin_view, name='department_head_signin'),
    path('department-head/dashboard/', department_head_dashboard, name='department_head_dashboard'),
    
    # Logout
    path('logout/', LogoutView.as_view(next_page='employee_signin'), name='logout'),
    
    path('employee-timesheets/', employee_timesheets_report, name='employee_timesheets_report'),
    path('api/sub-departments/', get_sub_departments, name='get_sub_departments'),
    path('download-timesheets/', download_timesheets_excel, name='download_timesheets_excel'),
]