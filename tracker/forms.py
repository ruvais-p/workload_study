from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import SUB_DEPARTMENT_CHOICES, User, Employee, DepartmentHead, Timesheet

DEPARTMENT_CHOICES = [
    ('ADM', 'Adminstrative Office'),
    ('SOE', 'School of Engineering'),
    ('SLS', 'School of Life Sciences'),
    # Add more as needed
]

class EmployeeSignUpForm(UserCreationForm):
    employee_id = forms.CharField(max_length=20)
    department = forms.ChoiceField(choices=DEPARTMENT_CHOICES)
    sub_department = forms.ChoiceField(choices=[], required=False)

    class Meta:
        model = User
        fields = ['username', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'department' in self.data:
            try:
                department = self.data.get('department')
                self.fields['sub_department'].choices = SUB_DEPARTMENT_CHOICES.get(department, [])
            except (ValueError, TypeError):
                pass

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            # Create Employee instance with default allocated_post
            Employee.objects.create(
                user=user,
                employee_id=self.cleaned_data['employee_id'],
                department=self.cleaned_data['department'],
                sub_department=self.cleaned_data.get('sub_department'),  # Using get() to be safe
                allocated_post=None  # This is correct for a nullable ForeignKey
            )
        return user
class EmployeePostAllocationForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['allocated_post']
        widgets = {
            'allocated_post': forms.TextInput(attrs={
                'placeholder': 'Enter employee post/position'
            })
        }

class EmployeeSignInForm(forms.Form):
    employee_id = forms.CharField(max_length=20)
    password = forms.CharField(widget=forms.PasswordInput)

class DepartmentHeadSignUpForm(UserCreationForm):
    employee_id = forms.CharField(max_length=20)
    department = forms.ChoiceField(choices=DEPARTMENT_CHOICES)
    sub_department = forms.ChoiceField(choices=[], required=False)

    class Meta:
        model = User
        fields = ['username', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'department' in self.data:
            try:
                department = self.data.get('department')
                self.fields['sub_department'].choices = SUB_DEPARTMENT_CHOICES.get(department, [])
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and hasattr(self.instance, 'departmenthead'):
            self.fields['sub_department'].choices = SUB_DEPARTMENT_CHOICES.get(
                self.instance.departmenthead.department, []
            )

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            # Create DepartmentHead instance
            DepartmentHead.objects.create(
                user=user,
                employee_id=self.cleaned_data['employee_id'],
                department=self.cleaned_data['department'],
                sub_department=self.cleaned_data['sub_department']
            )
        return user

class DepartmentHeadSignInForm(forms.Form):
    employee_id = forms.CharField(max_length=20)
    password = forms.CharField(widget=forms.PasswordInput)
    
class TimesheetForm(forms.Form):
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    
    def __init__(self, *args, **kwargs):
        employee = kwargs.pop('employee', None)
        super().__init__(*args, **kwargs)
        
        if employee:
            duties = employee.duties.all()
            for duty in duties:
                self.fields[f'duty_{duty.id}'] = forms.DecimalField(
                    label=duty.duty_name.name,
                    required=False,
                    max_digits=4,
                    decimal_places=2,
                    min_value=0,
                    widget=forms.NumberInput(attrs={'step': '0.25', 'placeholder': '0.00'})
                )