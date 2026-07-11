import json
from rest_framework import serializers
from .models import AuditJob, FeatureMetadata, LeakageResult


class FeatureMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeatureMetadata
        fields = ['feature_name', 'known_at_prediction_time']


class LeakageResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeakageResult
        fields = ['feature_name', 'drop_pct', 'shap_ratio', 'known_flag', 'risk_score']


class AuditJobSerializer(serializers.ModelSerializer):
    features = FeatureMetadataSerializer(many=True, read_only=True)
    leakage_results = LeakageResultSerializer(many=True, read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = AuditJob
        fields = [
            'id', 
            'username', 
            'model_file', 
            'dataset_file', 
            'target_column', 
            'protected_attribute',
            'production_dataset_file',
            'status', 
            'results', 
            'error_message', 
            'created_at',
            'features',
            'leakage_results'
        ]
        read_only_fields = ['id', 'status', 'results', 'error_message', 'created_at', 'leakage_results', 'production_dataset_file']

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user if request else None
        
        # Pull features metadata out of raw request data (usually JSON string in multi-part form)
        features_data = []
        if request and 'features' in request.data:
            raw_features = request.data['features']
            if isinstance(raw_features, str):
                try:
                    features_data = json.loads(raw_features)
                except json.JSONDecodeError:
                    raise serializers.ValidationError({
                        "features": "Invalid JSON format for feature configurations."
                    })
            elif isinstance(raw_features, list):
                features_data = raw_features

        validated_data['user'] = user
        audit_job = AuditJob.objects.create(**validated_data)

        # Create child FeatureMetadata
        features_to_create = []
        for feat in features_data:
            features_to_create.append(
                FeatureMetadata(
                    audit_job=audit_job,
                    feature_name=feat.get('feature_name'),
                    known_at_prediction_time=feat.get('known_at_prediction_time', True)
                )
            )
        
        if features_to_create:
            FeatureMetadata.objects.bulk_create(features_to_create)

        return audit_job
