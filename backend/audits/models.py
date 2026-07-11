import uuid
from django.db import models
from django.conf import settings


class AuditJob(models.Model):
    """
    Represents an ML model evaluation and auditing task execution.
    """
    STATUS_PENDING = 'PENDING'
    STATUS_PROCESSING = 'PROCESSING'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_FAILED = 'FAILED'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED, 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='audit_jobs'
    )
    model_file = models.FileField(upload_to='models/')
    dataset_file = models.FileField(upload_to='datasets/')
    target_column = models.CharField(max_length=255)
    protected_attribute = models.CharField(max_length=255, null=True, blank=True)
    production_dataset_file = models.FileField(upload_to='production_datasets/', null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )
    results = models.JSONField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"AuditJob {self.id} ({self.status})"


class FeatureMetadata(models.Model):
    """
    Stores metadata configuration for dataset features involved in an AuditJob evaluation.
    Allows specifying features that are known at prediction time for prediction auditing.
    """
    audit_job = models.ForeignKey(
        AuditJob,
        on_delete=models.CASCADE,
        related_name='features'
    )
    feature_name = models.CharField(max_length=255)
    known_at_prediction_time = models.BooleanField(default=True)

    class Meta:
        unique_together = ('audit_job', 'feature_name')

    def __str__(self):
        return f"{self.feature_name} (Known: {self.known_at_prediction_time})"


class LeakageResult(models.Model):
    """
    Stores leakage check results for a single feature under an AuditJob.
    """
    audit_job = models.ForeignKey(
        AuditJob,
        on_delete=models.CASCADE,
        related_name='leakage_results'
    )
    feature_name = models.CharField(max_length=255)
    drop_pct = models.FloatField()
    shap_ratio = models.FloatField()
    known_flag = models.BooleanField(default=False)
    risk_score = models.FloatField()

    class Meta:
        unique_together = ('audit_job', 'feature_name')
        ordering = ['-risk_score']

    def __str__(self):
        return f"{self.feature_name} (Risk: {self.risk_score:.1f}%)"

