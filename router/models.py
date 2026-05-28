
from django.db import models


class QueryHistory(models.Model):
    query = models.TextField()
    intent = models.CharField(max_length=100)
    response = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.query[:50]