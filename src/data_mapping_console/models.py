from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from pdf.models import BaseModel


class DMCConfigurations(BaseModel):
    STATUS_CHOICES = [
        ('draft', 'draft'),
        ('published', 'published')
    ]

    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, default=None)
    version = models.CharField(max_length=255)
    user_email = models.EmailField()
    template_id = models.BigIntegerField()
    config = models.JSONField(null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    class Meta:
        db_table = 'dmc_configurations'
        verbose_name = "dmc_configurations"
        verbose_name_plural = "dmc_configurations"
        app_label = 'data_mapping_console'

    def serialize(self):
        __dict__ = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "version": self.version,
            "user_email": self.user_email,
            "template_id": self.template_id,
            "config": self.config,
            "status": self.status,
            "created": self.created,
            "updated": self.updated,
        }
        return __dict__
