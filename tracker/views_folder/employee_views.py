import logging
from pyexpat.errors import messages
from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from tracker.forms import EmployeeSignInForm, EmployeeSignUpForm, TimesheetForm
from tracker.models import Employee, Timesheet, TimesheetEntry

logger = logging.getLogger(__name__)

def employee_signup_view(request):
    if request.method == 'POST':
        form = EmployeeSignUpForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('employee_signin')
    else:
        form = EmployeeSignUpForm()
    return render(request, 'employee_signup.html', {'form': form})

def employee_signin_view(request):
    if request.user.is_authenticated:
        try:
            Employee.objects.get(user=request.user)
            return redirect('employee_dashboard')
        except Employee.DoesNotExist:
            logout(request)
            return redirect('employee_signin')

    if request.method == 'POST':
        form = EmployeeSignInForm(request.POST)
        if form.is_valid():
            employee_id = form.cleaned_data.get('employee_id')
            password = form.cleaned_data.get('password')
            try:
                employee = Employee.objects.get(employee_id=employee_id)
                user = authenticate(request, username=employee.user.username, password=password)
                
                if user is not None:
                    login(request, user)
                    # Explicitly save the session after login
                    request.session.save()
                    request.session.set_expiry(1209600)  # 2 weeks
                    if employee.allocated_post is None:
                        return render(request, 'employee_pending.html')
                    return redirect('employee_dashboard')
                else:
                    form.add_error(None, "Invalid credentials")
            except Employee.DoesNotExist:
                form.add_error(None, "Invalid credentials")
    else:
        form = EmployeeSignInForm()
    
    return render(request, 'employee_signin.html', {'form': form})

@login_required
@csrf_protect
def employee_dashboard(request):
    # Verify user is authenticated and is an employee
    if not request.user.is_authenticated:
        messages.error(request, 'Please login to continue')
        return redirect('employee_signin')
    
    try:
        employee = Employee.objects.get(user=request.user)
    except Employee.DoesNotExist:
        messages.error(request, 'Employee profile not found. Please contact admin.')
        logout(request)
        return redirect('employee_signin')

    # Check if employee has an allocated post
    if not employee.allocated_post:
        messages.warning(request, 'Your account is pending approval')
        return render(request, 'employee_pending.html')

    # Handle form submission
    if request.method == 'POST':
        form = TimesheetForm(request.POST, employee=employee)
        if form.is_valid():
            try:
                # Create Timesheet
                timesheet = Timesheet.objects.create(
                    employee=employee,
                    date=form.cleaned_data['date'],
                    department=employee.department,
                    status='Submitted'
                )
                
                # Create Timesheet entries for each of the employee's duties
                for duty in employee.duties.all():
                    hours = form.cleaned_data.get(f'duty_{duty.id}')
                    if hours and float(hours) > 0:
                        TimesheetEntry.objects.create(
                            timesheet=timesheet,
                            duty=duty,
                            hours=hours
                        )
                
                messages.success(request, 'Timesheet submitted successfully!')
                return redirect('employee_dashboard')
            except Exception as e:
                logger.error(f'Error submitting timesheet for user {request.user.id}: {str(e)}')
                messages.error(request, f'Error submitting timesheet: {str(e)}')
        else:
            messages.error(request, 'Please correct the form errors.')
    else:
        form = TimesheetForm(employee=employee)
    
    previous_timesheets = Timesheet.objects.filter(
        employee=employee
    ).prefetch_related('entries').order_by('-submitted_at')
    
    return render(request, 'employee_dashboard.html', {
        'form': form,
        'previous_timesheets': previous_timesheets,
        'employee': employee,
    })
    