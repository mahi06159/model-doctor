import logging
from celery import shared_task
import pandas as pd
from django.db import transaction

from .models import AuditJob
from analysis.data_quality import analyze_data_quality

logger = logging.getLogger(__name__)


def _update_progress(job, stage: str, percent: int, message: str):
    res = job.results or {}
    res["progress"] = {
        "stage": stage,
        "percent": percent,
        "message": message
    }
    job.results = res
    job.save(update_fields=['results'])


@shared_task(bind=True, max_retries=3)
def run_data_quality_audit(self, job_id: str):
    """
    Celery task that runs data quality evaluations asynchronously.
    Updates the AuditJob record and triggers the leakage audit.
    """
    logger.info(f"Starting data quality check for Job ID: {job_id}")
    
    try:
        job = AuditJob.objects.get(id=job_id)
    except AuditJob.DoesNotExist:
        logger.error(f"AuditJob {job_id} not found.")
        return False

    # 1. Update job state to processing
    job.status = AuditJob.STATUS_PROCESSING
    job.save(update_fields=['status'])
    _update_progress(job, "quality", 10, "Evaluating dataset quality...")

    try:
        # 2. Retrieve dataset filepath and parse with Pandas
        file_path = job.dataset_file.path
        df = pd.read_csv(file_path)

        # 3. Perform analysis
        results = analyze_data_quality(df, target_column=job.target_column)

        # 4. Save results to the model (keep status as PROCESSING)
        job.results = results
        job.save(update_fields=['results'])
        _update_progress(job, "leakage", 25, "Quality checks complete. Initiating target leakage checks...")
        
        logger.info(f"Data quality check for Job {job_id} completed. Triggering leakage and diagnostics.")
        
        # 5. Delegate downstream tasks (using transaction.on_commit or directly)
        run_leakage_audit.delay(job_id)
        return True

    except Exception as e:
        logger.error(f"Audit task execution failed for Job {job_id}: {str(e)}", exc_info=True)
        job.status = AuditJob.STATUS_FAILED
        job.error_message = f"Data quality check failed: {str(e)}"
        job.save(update_fields=['status', 'error_message'])
        return False


@shared_task(bind=True, max_retries=3)
def run_leakage_audit(self, job_id: str):
    """
    Celery task that computes leakage results, calibration, overfitting,
    and feature dominance diagnostics. Sets the job status to COMPLETED.
    """
    logger.info(f"Starting leakage and diagnostic checks for Job ID: {job_id}")
    
    try:
        job = AuditJob.objects.get(id=job_id)
    except AuditJob.DoesNotExist:
        logger.error(f"AuditJob {job_id} not found.")
        return False

    try:
        import joblib
        from django.db import transaction
        from analysis.leakage import analyze_leakage
        from analysis.calibration import analyze_calibration
        from analysis.overfitting import analyze_overfitting
        from analysis.feature_dominance import analyze_feature_dominance
        from .models import LeakageResult, FeatureMetadata
        
        # 1. Load files
        df = pd.read_csv(job.dataset_file.path)
        model = joblib.load(job.model_file.path)
        
        X = df.drop(columns=[job.target_column])
        y = df[job.target_column]
        
        # 2. Build map of feature -> known_at_prediction_time from DB configuration
        features_qs = FeatureMetadata.objects.filter(audit_job=job)
        known_map = {f.feature_name: f.known_at_prediction_time for f in features_qs}
        
        # 3. Perform leakage analysis
        _update_progress(job, "leakage", 35, "Running 3-Signal leakage evaluation...")
        leakage_results = analyze_leakage(df, job.target_column, model, known_map)
        
        # 4. Save leakage results to database
        with transaction.atomic():
            # Delete any existing results first to allow idempotency
            LeakageResult.objects.filter(audit_job=job).delete()
            
            leakage_objects = []
            for res in leakage_results:
                leakage_objects.append(
                    LeakageResult(
                        audit_job=job,
                        feature_name=res["feature_name"],
                        drop_pct=res["drop_pct"],
                        shap_ratio=res["shap_ratio"],
                        known_flag=res["known_flag"],
                        risk_score=res["risk_score"]
                    )
                )
            if leakage_objects:
                LeakageResult.objects.bulk_create(leakage_objects)
                
        # 5. Perform calibration check
        _update_progress(job, "calibration", 55, "Assessing probability calibration...")
        calibration_results = analyze_calibration(model, X, y)
        
        # 6. Perform overfitting check
        _update_progress(job, "overfitting", 70, "Plotting learning curves & overfitting...")
        overfitting_results = analyze_overfitting(model, X, y)

        # 7. Perform feature dominance analysis
        _update_progress(job, "dominance", 80, "Calculating feature importances...")
        feature_dominance_results = analyze_feature_dominance(model, X, y)
        
        # 7.5 Perform fairness evaluation
        _update_progress(job, "fairness", 90, "Evaluating demographic parity and equalised odds...")
        from analysis.fairness import analyze_fairness
        fairness_results = analyze_fairness(model, df, job.target_column, job.protected_attribute)

        # 8. Compute composite Health Score
        _update_progress(job, "health", 95, "Compiling composite health score...")
        from analysis.health_score import compute_health_score
        current_results = job.results or {}
        health_score_result = compute_health_score(
            leakage_results=leakage_results,
            calibration_results=calibration_results,
            overfitting_results=overfitting_results,
            data_quality_results=current_results,   # data_quality already in job.results
            fairness_results=fairness_results,
        )
        
        # 9. Merge all diagnostic results back into the job.results JSON
        current_results["calibration"] = calibration_results
        current_results["overfitting"] = overfitting_results
        current_results["feature_dominance"] = feature_dominance_results
        current_results["fairness"] = fairness_results
        current_results["health_score"] = health_score_result
        current_results["progress"] = {
            "stage": "completed",
            "percent": 100,
            "message": "Audit completed successfully."
        }
        
        job.results = current_results
        job.status = AuditJob.STATUS_COMPLETED
        job.save(update_fields=['results', 'status'])
        
        logger.info(
            f"Leakage and diagnostic checks for Job {job_id} completed. "
            f"Health Score: {health_score_result['score']}/100 (Grade {health_score_result['grade']})"
        )

        # 10. Check if production dataset already exists and run drift analysis
        if job.production_dataset_file:
            run_drift_analysis.delay(job_id)

        return True
        
    except Exception as e:
        logger.error(f"Leakage/diagnostic checks failed for Job {job_id}: {str(e)}", exc_info=True)
        job.status = AuditJob.STATUS_FAILED
        job.error_message = f"Leakage and diagnostic analysis failed: {str(e)}"
        job.save(update_fields=['status', 'error_message'])
        return False


@shared_task(bind=True, max_retries=3)
def run_drift_analysis(self, job_id: str):
    """
    Celery task that computes data drift compared to the training dataset.
    Updates the AuditJob results.
    """
    logger.info(f"Starting data drift check for Job ID: {job_id}")
    try:
        job = AuditJob.objects.get(id=job_id)
    except AuditJob.DoesNotExist:
        logger.error(f"AuditJob {job_id} not found.")
        return False

    if not job.production_dataset_file:
        logger.warning(f"No production dataset file found for Job {job_id}.")
        return False

    try:
        from analysis.drift import analyze_drift
        
        train_df = pd.read_csv(job.dataset_file.path)
        prod_df = pd.read_csv(job.production_dataset_file.path)

        drift_results = analyze_drift(train_df, prod_df, job.target_column)

        # Merge drift back into results JSON
        current_results = job.results or {}
        current_results["drift"] = drift_results

        job.results = current_results
        job.save(update_fields=['results'])

        logger.info(f"Data drift check completed for Job {job_id}.")
        return True
    except Exception as e:
        logger.error(f"Drift task execution failed for Job {job_id}: {str(e)}", exc_info=True)
        current_results = job.results or {}
        current_results["drift"] = {
            "supported": False,
            "message": f"Drift analysis failed: {str(e)}"
        }
        job.results = current_results
        job.save(update_fields=['results'])
        return False

