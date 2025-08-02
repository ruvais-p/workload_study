import logging
from django.contrib import messages  # Add this import
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt

from tracker.models import Timesheet


logger = logging.getLogger(__name__)

@csrf_exempt  # Only for testing! Use csrf_token in your template in production.
def admin_dashboard(request):
    # Check if user is admin
    if not request.user.is_authenticated or not request.user.is_admin:
        return redirect('admin_signin')
    
    timesheets = Timesheet.objects.all().order_by('-submitted_at')

    if request.method == 'POST':
        ts_id = request.POST.get('ts_id')
        action = request.POST.get('action')  # 'Approved', 'Rejected', 'Rework'
        remark = request.POST.get('admin_remark', '')
        try:
            timesheet = Timesheet.objects.get(id=ts_id)
            if action in ['Approved', 'Rejected', 'Rework']:
                timesheet.status = action
                timesheet.admin_remark = remark
                timesheet.save()
        except Timesheet.DoesNotExist:
            pass  # handle error if needed

    return render(request, 'admin_dashboard.html', {'timesheets': timesheets})

# Admin signin (you'll need to create this view and template)
def admin_signin_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_admin:
            login(request, user)
            return redirect('admin_dashboard')
    return render(request, 'admin_signin.html')

# Legacy views for backward compatibility (redirect to new views)
def signup_view(request):
    return redirect('employee_signup')

def signin_view(request):
    return redirect('employee_signin')



def landing_page(request):
    """Render the base landing page with portal options"""
    return render(request, 'base.html')