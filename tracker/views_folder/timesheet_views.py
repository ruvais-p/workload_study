
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