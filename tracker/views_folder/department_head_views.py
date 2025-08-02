import logging
from pyexpat.errors import messages
from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from tracker.forms import DepartmentHeadSignInForm, DepartmentHeadSignUpForm
from tracker.models import AllocatedPost, DepartmentHead, DepartmentPostName, DutyName, Employee, EmployeeDuty, Timesheet, User

logger = logging.getLogger(__name__)

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