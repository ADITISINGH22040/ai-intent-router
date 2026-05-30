from django.contrib import admin

from router.models import QueryHistory


@admin.register(QueryHistory)
class QueryHistoryAdmin(admin.ModelAdmin):
    list_display = ("id", "intent", "created_at")
    search_fields = ("query", "intent")
    readonly_fields = ("created_at",)
