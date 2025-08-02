from django.contrib.auth.models import AbstractUser
from django.db import models

# Add this at the top of models.py
SUB_DEPARTMENT_CHOICES = {
    'ADM': [
        ('Sessional-Head', 'Sessional Head'),
        ('ADM-Research', 'ADM Research'),
        ('B-Employee', 'B Employee'),
    ],
    'SOE': [
        ('CSE', 'Department of Computer Science'),
        ('CE', 'Department of Civil'),
        ('ECE', 'Department of Electronics'),
        ('ME', 'Department of Mechanical'),
        ('EE', 'Department of Electrical'),
    ],
    'SLS': [
        ('xxxxx', 'xxxx'),
        ('yyyyy', 'yyyy'),
    ],
    # Add more departments and their sub-departments as needed
}

class User(AbstractUser):
    """Base user class for admin functionality"""
    is_admin = models.BooleanField(default=False)
    employee_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    
class DepartmentHead(models.Model):
    """Department Head model for department heads"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    employee_id = models.CharField(max_length=20, unique=True)
    department = models.CharField(max_length=100, default="Unknown")
    sub_department = models.CharField(max_length=100, blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.department} Head"


# Add these new models to models.py
class DepartmentPostName(models.Model):
    """Model to store standard post names that can be selected when creating posts"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class DutyName(models.Model):
    """Model to store standard duty names that can be selected when creating duties"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

# Modify the AllocatedPost model to reference DepartmentPostName
class AllocatedPost(models.Model):
    department = models.CharField(max_length=100, default="ADM")
    sub_department = models.CharField(max_length=100, blank=True, null=True)
    post_name = models.ForeignKey(DepartmentPostName, on_delete=models.PROTECT)  # Changed from CharField
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(DepartmentHead, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('department', 'sub_department', 'post_name')
        ordering = ['post_name']

    def __str__(self):
        return f"{self.post_name.name} ({self.department})"

# Modify the PostDuty model to reference DutyName

class Employee(models.Model):
    """Employee model for regular employees"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    employee_id = models.CharField(max_length=20, unique=True)
    department = models.CharField(max_length=100, default="Unknown")
    sub_department = models.CharField(max_length=100, blank=True, null=True)
    allocated_post = models.ForeignKey(AllocatedPost, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.employee_id}"

class EmployeeDuty(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='duties')
    duty_name = models.ForeignKey(DutyName, on_delete=models.PROTECT)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Employee Duties"
        ordering = ['duty_name']

    def __str__(self):
        return f"{self.duty_name.name} ({self.employee.user.username})"

    
class Timesheet(models.Model):
    STATUS_CHOICES = [
        ('Open', 'Open'),
        ('Submitted', 'Submitted'),
        ('Approved', 'Approved'),
        ('Rework', 'Rework'),
        ('Rejected', 'Rejected'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, null=True)
    date = models.DateField()
    department = models.CharField(max_length=100, default="Unknown")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Open')
    submitted_at = models.DateTimeField(auto_now_add=True)
    admin_remark = models.TextField(blank=True, null=True)
    department_head_remark = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-submitted_at']

class TimesheetEntry(models.Model):
    timesheet = models.ForeignKey(Timesheet, on_delete=models.CASCADE, related_name='entries')
    duty = models.ForeignKey(EmployeeDuty, on_delete=models.CASCADE)
    hours = models.DecimalField(max_digits=4, decimal_places=2)

    def __str__(self):
        return f"{self.duty.duty_name.name} - {self.hours} hours"