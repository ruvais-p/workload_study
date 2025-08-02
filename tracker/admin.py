from django.contrib import admin

# Register your models here.
from .models import *

admin.site.register(Timesheet)
admin.site.register(TimesheetEntry)
admin.site.register(Employee)
admin.site.register(DepartmentHead)
admin.site.register(AllocatedPost)

@admin.register(DepartmentPostName)
class DepartmentPostNameAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)
    ordering = ('name',)

@admin.register(DutyName)
class DutyNameAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)
    ordering = ('name',)