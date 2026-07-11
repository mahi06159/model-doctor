import pandas as pd
import joblib
import os
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import transaction
from django.core.exceptions import ValidationError
from django.http import HttpResponse

from .models import AuditJob
from .serializers import AuditJobSerializer
from .tasks import run_data_quality_audit


class PreviewDatasetView(APIView):
    """
    API endpoint that accepts a CSV dataset file and returns a list of its column headers.
    Used by the frontend to dynamically render feature selection lists.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        dataset_file = request.FILES.get('dataset_file')
        
        if not dataset_file:
            return Response(
                {"error": "No dataset file was uploaded."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate file extension
        ext = os.path.splitext(dataset_file.name)[1].lower()
        if ext != '.csv':
            return Response(
                {"error": "Invalid file format. Only CSV datasets (.csv) are supported."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Read only first row to extract column names quickly
            df = pd.read_csv(dataset_file, nrows=0)
            columns = list(df.columns)
            return Response({"columns": columns})
        except Exception as e:
            return Response(
                {"error": f"Failed to parse CSV dataset. Ensure the file is not corrupted: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )


class AuditJobViewSet(viewsets.ModelViewSet):
    """
    ViewSet for creating, listing, and retrieving Audit Jobs.
    On creation, validates files and triggers Celery background worker audit.
    """
    serializer_class = AuditJobSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Users can only view their own audit jobs
        return AuditJob.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        model_file = request.FILES.get('model_file')
        dataset_file = request.FILES.get('dataset_file')
        target_column = request.data.get('target_column')
        protected_attribute = request.data.get('protected_attribute')

        # 1. Check for files presence
        if not model_file or not dataset_file:
            return Response(
                {"error": "Both model_file (.pkl/.joblib) and dataset_file (.csv) are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Validate model file extension and integrity
        model_ext = os.path.splitext(model_file.name)[1].lower()
        if model_ext not in ['.pkl', '.joblib']:
            return Response(
                {"error": "Invalid model format. Only joblib (.joblib) or pickle (.pkl) files are supported."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Basic local loading validation of model to ensure it is not corrupted
        # NOTE: Loading serialized models via joblib can execute arbitrary code (Known vulnerability, accepted for demo)
        try:
            # We temporarily write/read model file to verify it loads without crashing
            joblib.load(model_file)
            # Reset pointer after reading
            model_file.seek(0)
        except Exception as e:
            return Response(
                {"error": f"Failed to load model file. Verify it is a valid scikit-learn model: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. Validate dataset file format and column existence
        dataset_ext = os.path.splitext(dataset_file.name)[1].lower()
        if dataset_ext != '.csv':
            return Response(
                {"error": "Invalid dataset format. Only CSV datasets (.csv) are supported."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            df = pd.read_csv(dataset_file, nrows=5)
            if target_column not in df.columns:
                return Response(
                    {"error": f"Target column '{target_column}' was not found in the dataset features."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if protected_attribute and protected_attribute not in df.columns:
                return Response(
                    {"error": f"Protected attribute '{protected_attribute}' was not found in the dataset features."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            dataset_file.seek(0)
        except Exception as e:
            return Response(
                {"error": f"Failed to read dataset file: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Perform save and run worker
        with transaction.atomic():
            audit_job = serializer.save()
            # Register delayed celery task after transaction commits
            transaction.on_commit(lambda: run_data_quality_audit.delay(str(audit_job.id)))

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=['post'], url_path='upload-production')
    def upload_production(self, request, pk=None):
        """
        Endpoint to upload a production dataset and trigger data drift analysis.
        """
        audit_job = self.get_object()
        
        # Check if job is completed or failed
        if audit_job.status not in (AuditJob.STATUS_COMPLETED, AuditJob.STATUS_FAILED):
            return Response(
                {"error": "Production dataset can only be uploaded for a completed or failed audit job."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        production_file = request.FILES.get('production_dataset_file')
        if not production_file:
            return Response(
                {"error": "production_dataset_file is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Validate CSV format
        ext = os.path.splitext(production_file.name)[1].lower()
        if ext != '.csv':
            return Response(
                {"error": "Invalid format. Only CSV datasets (.csv) are supported."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Validate that features match training data schema
        try:
            train_df = pd.read_csv(audit_job.dataset_file.path, nrows=5)
            prod_df = pd.read_csv(production_file, nrows=5)
            
            # Exclude target
            train_features = [c for c in train_df.columns if c != audit_job.target_column]
            missing_features = [c for c in train_features if c not in prod_df.columns]
            
            if missing_features:
                return Response(
                    {"error": f"Production dataset is missing features present in training data: {missing_features}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Reset pointer
            production_file.seek(0)
        except Exception as e:
            return Response(
                {"error": f"Failed to parse production dataset: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Save production file and trigger Celery task
        audit_job.production_dataset_file = production_file
        audit_job.save(update_fields=['production_dataset_file'])
        
        # Trigger Celery task
        from .tasks import run_drift_analysis
        run_drift_analysis.delay(str(audit_job.id))
        
        return Response(
            {"message": "Production dataset uploaded successfully. Drift analysis started in background."},
            status=status.HTTP_202_ACCEPTED
        )


class ReportDownloadView(APIView):
    """
    Generate and stream an audit report for a completed job.

    GET /api/audits/<id>/report/?filetype=pdf   → PDF file download
    GET /api/audits/<id>/report/?filetype=html  → HTML in-browser view

    Returns 404 if the job belongs to another user.
    Returns 400 if the job is not yet completed (no results to report).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        # Allow anyone to download demo reports
        job_id = self.kwargs.get("job_id", "")
        if isinstance(job_id, str) and job_id.startswith("demo-"):
            return [permissions.AllowAny()]
        return super().get_permissions()

    def get(self, request, job_id, *args, **kwargs):
        # Check if requesting a pre-computed system demo job
        if isinstance(job_id, str) and job_id.startswith("demo-"):
            from analysis.demo_data import DEMO_JOBS
            demo_job_dict = DEMO_JOBS.get(job_id)
            if not demo_job_dict:
                return Response(
                    {"error": "Demo audit job not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Wrap in mock object to mimic Django DB model instance
            class MockJob:
                def __init__(self, d):
                    self.id = d["id"]
                    self.target_column = d["target_column"]
                    self.protected_attribute = d.get("protected_attribute")
                    self.results = d["results"]
                    self._leakage_list = d["leakage_results"]

                @property
                def leakage_results(self):
                    return self._leakage_list

            job = MockJob(demo_job_dict)
        else:
            try:
                job = AuditJob.objects.get(id=job_id, user=request.user)
            except (AuditJob.DoesNotExist, ValidationError):
                return Response(
                    {"error": "Audit job not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            if job.status not in (AuditJob.STATUS_COMPLETED, AuditJob.STATUS_FAILED):
                return Response(
                    {"error": "Report is only available for completed or failed jobs."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        report_format = request.query_params.get("filetype", "pdf").lower()
        health_score_result = (job.results or {}).get("health_score")

        from analysis.report_generator import generate_html_report, generate_pdf_report, generate_docx_report

        if report_format == "html":
            html_content = generate_html_report(job, health_score_result)
            return HttpResponse(html_content, content_type="text/html; charset=utf-8")

        if report_format == "docx":
            docx_bytes = generate_docx_report(job, health_score_result)
            response = HttpResponse(
                docx_bytes,
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
            safe_id = str(job.id)[:8]
            response["Content-Disposition"] = (
                f'attachment; filename="modeldoctor_report_{safe_id}.docx"'
            )
            return response

        # Default: PDF
        pdf_bytes = generate_pdf_report(job, health_score_result)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        safe_id = str(job.id)[:8]
        response["Content-Disposition"] = (
            f'attachment; filename="modeldoctor_report_{safe_id}.pdf"'
        )
        return response


class DemoAuditsView(APIView):
    """
    Publicly accessible API endpoints for exploring pre-run demo audits without logging in.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, job_id=None, *args, **kwargs):
        from analysis.demo_data import DEMO_JOBS
        
        if job_id:
            job = DEMO_JOBS.get(job_id)
            if not job:
                return Response(
                    {"error": "Demo audit job not found."},
                    status=status.HTTP_404_NOT_FOUND
                )
            return Response(job)
            
        # Return list of demo audits
        summary_list = []
        for j_id, details in DEMO_JOBS.items():
            summary_list.append({
                "id": details["id"],
                "username": details["username"],
                "target_column": details["target_column"],
                "protected_attribute": details["protected_attribute"],
                "status": details["status"],
                "created_at": details["created_at"],
                "results": {
                    "health_score": details["results"]["health_score"]
                }
            })
        return Response(summary_list)