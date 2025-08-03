import logging
from django.contrib import messages  # Add this import
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.db import transaction
from .models import AllocatedPost, DepartmentPostName, DutyName, EmployeeDuty, TimesheetEntry, User, Employee, DepartmentHead, Timesheet
from .forms import (
    EmployeePostAllocationForm, EmployeeSignUpForm, EmployeeSignInForm, 
    DepartmentHeadSignUpForm, DepartmentHeadSignInForm, TimesheetForm
)

logger = logging.getLogger(__name__)


# Employee Views
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
    
# Department Head Views
def department_head_signup_view(request):
    if request.method == 'POST':
        form = DepartmentHeadSignUpForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('department_head_signin')
    else:
        form = DepartmentHeadSignUpForm()
    return render(request, 'department_head_signup.html', {'form': form})

def department_head_signin_view(request):
    if request.method == 'POST':
        form = DepartmentHeadSignInForm(request.POST)
        if form.is_valid():
            employee_id = form.cleaned_data.get('employee_id')
            password = form.cleaned_data.get('password')
            try:
                dept_head = DepartmentHead.objects.get(employee_id=employee_id)
                user = authenticate(request, username=dept_head.user.username, password=password)
                if user is not None:
                    login(request, user)
                    return redirect('department_head_dashboard')
            except DepartmentHead.DoesNotExist:
                form.add_error(None, "Invalid employee ID or password")
    else:
        form = DepartmentHeadSignInForm()
    return render(request, 'department_head_signin.html', {'form': form})

@login_required
@csrf_protect
def department_head_dashboard(request):
    # Verify user is authenticated and is a department head
    if not request.user.is_authenticated:
        messages.error(request, 'Please login to continue')
        return redirect('department_head_signin')
    
    try:
        dept_head = DepartmentHead.objects.get(user=request.user)
    except DepartmentHead.DoesNotExist:
        messages.error(request, 'Department head profile not found. Please contact admin.')
        logout(request)
        return redirect('department_head_signin')
    
    selected_employee = None
    employee_timesheets = []
    
    # Handle form submissions
    if request.method == 'POST':
        try:
            # Existing timesheet approval handling
            ts_id = request.POST.get('ts_id')
            action = request.POST.get('action')
            remark = request.POST.get('department_head_remark', '')
            
            # Post allocation handling
            employee_id = request.POST.get('employee_id')
            allocated_post_id = request.POST.get('allocated_post')
            
            # New post handling
            new_post_name_id = request.POST.get('new_post_name')
            new_post_description = request.POST.get('new_post_description')
            
            # Duty assignment to employee
            assign_duty_employee_id = request.POST.get('assign_duty_employee')
            assign_duty_name_id = request.POST.get('assign_duty_name')
            assign_duty_description = request.POST.get('assign_duty_description')
            
            # Remove duty from employee
            remove_duty_id = request.POST.get('remove_duty_id')
            
            # New employee creation handling
            new_employee_id = request.POST.get('new_employee_id')
            new_employee_username = request.POST.get('new_employee_username')
            new_employee_post_id = request.POST.get('new_employee_post')

            if ts_id and action in ['Approved', 'Rejected', 'Rework']:
                try:
                    timesheet = Timesheet.objects.get(id=ts_id, department=dept_head.department)
                    timesheet.status = action
                    timesheet.department_head_remark = remark
                    timesheet.save()
                    messages.success(request, f'Timesheet {action.lower()} successfully!')
                except Timesheet.DoesNotExist:
                    messages.error(request, 'Timesheet not found.')
            
            if employee_id and allocated_post_id:
                try:
                    employee = Employee.objects.get(employee_id=employee_id, department=dept_head.department)
                    post = AllocatedPost.objects.get(id=allocated_post_id)
                    employee.allocated_post = post
                    employee.save()
                    selected_employee = employee
                    messages.success(request, f'Post allocated to {employee.user.username} successfully!')
                except (Employee.DoesNotExist, AllocatedPost.DoesNotExist):
                    messages.error(request, 'Employee or post not found.')
                    
            if new_post_name_id:
                try:
                    post_name = DepartmentPostName.objects.get(id=new_post_name_id)
                    post = AllocatedPost.objects.create(
                        department=dept_head.department,
                        sub_department=dept_head.sub_department,
                        post_name=post_name,
                        description=new_post_description,
                        created_by=dept_head
                    )
                    messages.success(request, f'New post "{post_name.name}" created successfully!')
                except DepartmentPostName.DoesNotExist:
                    messages.error(request, 'Post name not found.')
            
            if assign_duty_employee_id and assign_duty_name_id:
                try:
                    employee = Employee.objects.get(employee_id=assign_duty_employee_id, department=dept_head.department)
                    duty_name = DutyName.objects.get(id=assign_duty_name_id)
                    EmployeeDuty.objects.create(
                        employee=employee,
                        duty_name=duty_name,
                        description=assign_duty_description
                    )
                    messages.success(request, f'Duty "{duty_name.name}" assigned to {employee.user.username} successfully!')
                except (Employee.DoesNotExist, DutyName.DoesNotExist):
                    messages.error(request, 'Employee or duty name not found.')
            
            if remove_duty_id:
                try:
                    duty = EmployeeDuty.objects.get(id=remove_duty_id)
                    duty.delete()
                    messages.success(request, 'Duty removed successfully!')
                except EmployeeDuty.DoesNotExist:
                    messages.error(request, 'Duty not found.')
            
            if new_employee_id and new_employee_username and new_employee_post_id:
                try:
                    # Check if employee ID or username already exists
                    if User.objects.filter(username=new_employee_username).exists():
                        messages.error(request, 'Username already exists')
                    elif Employee.objects.filter(employee_id=new_employee_id).exists():
                        messages.error(request, 'Employee ID already exists')
                    else:
                        # Create user with default password
                        user = User.objects.create_user(
                            username=new_employee_username,
                            password='test@123'  # Set initial password
                        )
                        
                        # Get the post
                        post = AllocatedPost.objects.get(id=new_employee_post_id)
                        
                        # Create employee
                        Employee.objects.create(
                            user=user,
                            employee_id=new_employee_id,
                            department=dept_head.department,
                            sub_department=dept_head.sub_department,
                            allocated_post=post
                        )
                        
                        messages.success(request, 
                            f'Employee {new_employee_username} created successfully! '
                            f'Initial password: test@123. Please instruct the employee to change their password after first login.'
                        )
                except AllocatedPost.DoesNotExist:
                    messages.error(request, 'Post not found')
                except Exception as e:
                    logger.error(f'Error creating employee: {str(e)}')
                    messages.error(request, 'Error creating employee')

        except Exception as e:
            logger.error(f'Error in department head dashboard for user {request.user.id}: {str(e)}')
            messages.error(request, 'An error occurred while processing your request.')
    
    # Get department employees
    department_employees = Employee.objects.filter(department=dept_head.department)
    
    # Get selected employee if specified
    employee_id = request.GET.get('employee_id')
    if employee_id:
        try:
            selected_employee = Employee.objects.get(employee_id=employee_id, department=dept_head.department)
            employee_timesheets = Timesheet.objects.filter(employee=selected_employee).order_by('-submitted_at')
        except Employee.DoesNotExist:
            messages.error(request, 'Employee not found.')
    
    # Get posts for this department
    department_posts = AllocatedPost.objects.filter(department=dept_head.department)
    if dept_head.sub_department:
        department_posts = department_posts.filter(sub_department=dept_head.sub_department)
    
    # Get standard post names and duty names for dropdowns
    post_names = DepartmentPostName.objects.all().order_by('name')
    duty_names = DutyName.objects.all().order_by('name')
    
    # Get employee duties for the department
    employee_duties = EmployeeDuty.objects.filter(employee__department=dept_head.department).select_related('employee', 'duty_name')
    
    # Get statistics for right panel
    pending_timesheets = Timesheet.objects.filter(
        department=dept_head.department,
        status__in=['Open', 'Submitted', 'Rework']
    )
    approved_timesheets = Timesheet.objects.filter(
        department=dept_head.department,
        status='Approved'
    )
    
    return render(request, 'department_head_dashboard.html', {
        'department_employees': department_employees,
        'selected_employee': selected_employee,
        'employee_timesheets': employee_timesheets,
        'pending_timesheets': pending_timesheets,
        'approved_timesheets': approved_timesheets,
        'department': dept_head.department,
        'sub_department': dept_head.sub_department,
        'employee_name': dept_head.user.username,
        'dept_head': dept_head,
        'department_posts': department_posts,
        'post_names': post_names,
        'duty_names': duty_names,
        'employee_duties': employee_duties,
    })
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

from django.shortcuts import render
from django.core.paginator import Paginator
from tracker.models import Employee, Timesheet, SUB_DEPARTMENT_CHOICES
from tracker.forms import DEPARTMENT_CHOICES
from django.http import JsonResponse
from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment

def employee_timesheets_report(request):
    # Get filter parameters from request
    selected_department = request.GET.get('department', '')
    selected_sub_department = request.GET.get('sub_department', '')
    selected_status = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Get all employees with their timesheets
    employees = Employee.objects.select_related(
        'user', 'allocated_post__post_name'
    ).prefetch_related(
        'duties__duty_name', 'timesheet_set__entries__duty__duty_name'
    ).order_by('employee_id')
    
    # Apply filters
    if selected_department:
        employees = employees.filter(department=selected_department)
    
    if selected_sub_department:
        employees = employees.filter(sub_department=selected_sub_department)
    
    # Prepare the data structure for template
    employees_timesheets = {}
    for employee in employees:
        timesheets = employee.timesheet_set.all()
        
        # Apply additional filters to timesheets
        if selected_status:
            timesheets = timesheets.filter(status=selected_status)
        
        if date_from:
            timesheets = timesheets.filter(date__gte=date_from)
        
        if date_to:
            timesheets = timesheets.filter(date__lte=date_to)
        
        if timesheets.exists():
            employees_timesheets[employee] = timesheets
    
    # Pagination
    paginator = Paginator(list(employees_timesheets.items()), 20)  # Show 20 employees per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Convert page object back to dictionary for template
    paginated_data = dict(page_obj.object_list)
    
    context = {
        'employees_timesheets': paginated_data,
        'departments': DEPARTMENT_CHOICES,
        'sub_departments': SUB_DEPARTMENT_CHOICES.get(selected_department, []),
        'statuses': Timesheet.STATUS_CHOICES,
        'selected_department': selected_department,
        'selected_sub_department': selected_sub_department,
        'selected_status': selected_status,
        'date_from': date_from,
        'date_to': date_to,
        'page_obj': page_obj,
        'is_paginated': paginator.num_pages > 1,
    }
    
    return render(request, 'employee_timesheets_report.html', context)

def get_sub_departments(request):
    department = request.GET.get('department', '')
    sub_departments = SUB_DEPARTMENT_CHOICES.get(department, [])
    return JsonResponse(sub_departments, safe=False)

def download_timesheets_excel(request):
    # Get filter parameters from request
    selected_department = request.POST.get('department', '')
    selected_sub_department = request.POST.get('sub_department', '')
    selected_status = request.POST.get('status', '')
    date_from = request.POST.get('date_from', '')
    date_to = request.POST.get('date_to', '')
    
    # Get filtered data (similar to the report view)
    employees = Employee.objects.select_related(
        'user', 'allocated_post__post_name'
    ).prefetch_related(
        'duties__duty_name', 'timesheet_set__entries__duty__duty_name'
    ).order_by('employee_id')
    
    if selected_department:
        employees = employees.filter(department=selected_department)
    
    if selected_sub_department:
        employees = employees.filter(sub_department=selected_sub_department)
    
    # Create Excel workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Timesheets Report"
    
    # Add headers
    headers = [
        'Employee ID', 'Name', 'Department', 'Sub-Department', 
        'Post', 'Duty', 'Date', 'Hours', 'Status'
    ]
    ws.append(headers)
    
    # Style headers
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')
    
    # Add data
    for employee in employees:
        timesheets = employee.timesheet_set.all()
        
        if selected_status:
            timesheets = timesheets.filter(status=selected_status)
        
        if date_from:
            timesheets = timesheets.filter(date__gte=date_from)
        
        if date_to:
            timesheets = timesheets.filter(date__lte=date_to)
        
        for timesheet in timesheets:
            for entry in timesheet.entries.all():
                ws.append([
                    employee.employee_id,
                    employee.user.username,
                    employee.department,
                    employee.sub_department or '-',
                    employee.allocated_post.post_name.name if employee.allocated_post else '-',
                    entry.duty.duty_name.name,
                    timesheet.date,
                    entry.hours,
                    timesheet.status
                ])
    
    # Create response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=timesheets_report.xlsx'
    wb.save(response)
    
    return response

def landing_page(request):
    """Render the base landing page with portal options"""
    return render(request, 'base.html')