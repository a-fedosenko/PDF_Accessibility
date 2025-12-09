"""
CloudWatch Metrics Utility for tracking API usage and quota limits.
"""
import boto3
import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class CloudWatchMetricsPublisher:
    """Publishes custom metrics to CloudWatch for monitoring API usage."""

    def __init__(self, namespace: str = "PDFAccessibility"):
        """
        Initialize CloudWatch metrics publisher.

        Args:
            namespace: CloudWatch namespace for metrics
        """
        self.namespace = namespace
        try:
            self.cloudwatch = boto3.client('cloudwatch')
        except Exception as e:
            logger.warning(f"Failed to initialize CloudWatch client: {e}")
            self.cloudwatch = None

    def put_metric(
        self,
        metric_name: str,
        value: float,
        unit: str = "Count",
        dimensions: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Publish a single metric to CloudWatch.

        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: CloudWatch unit (Count, Seconds, Bytes, etc.)
            dimensions: Optional dimensions for filtering

        Returns:
            True if successful, False otherwise
        """
        if not self.cloudwatch:
            logger.warning("CloudWatch client not initialized, skipping metric")
            return False

        try:
            metric_data = {
                'MetricName': metric_name,
                'Value': value,
                'Unit': unit,
                'Timestamp': datetime.utcnow()
            }

            if dimensions:
                metric_data['Dimensions'] = [
                    {'Name': k, 'Value': v} for k, v in dimensions.items()
                ]

            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[metric_data]
            )
            logger.debug(f"Published metric {metric_name}={value} to CloudWatch")
            return True

        except Exception as e:
            logger.error(f"Failed to publish metric {metric_name}: {e}")
            return False

    def put_api_call_metric(
        self,
        api_name: str,
        success: bool = True,
        operation: Optional[str] = None
    ) -> bool:
        """
        Track an API call with success/failure.

        Args:
            api_name: Name of the API (e.g., "AdobeAPI", "BedrockAPI")
            success: Whether the call succeeded
            operation: Specific operation name

        Returns:
            True if metric published successfully
        """
        dimensions = {"APIName": api_name}
        if operation:
            dimensions["Operation"] = operation

        # Track total calls
        self.put_metric(
            metric_name="APICallCount",
            value=1.0,
            unit="Count",
            dimensions=dimensions
        )

        # Track success/failure
        status_dimensions = {**dimensions, "Status": "Success" if success else "Failure"}
        return self.put_metric(
            metric_name="APICallStatus",
            value=1.0,
            unit="Count",
            dimensions=status_dimensions
        )

    def put_quota_usage_metric(
        self,
        api_name: str,
        usage_count: int,
        quota_limit: int,
        period: str = "Monthly"
    ) -> bool:
        """
        Track quota usage against limits.

        Args:
            api_name: Name of the API
            usage_count: Current usage count
            quota_limit: Maximum quota limit
            period: Quota period (Daily, Monthly, etc.)

        Returns:
            True if metrics published successfully
        """
        dimensions = {
            "APIName": api_name,
            "Period": period
        }

        # Track absolute usage
        self.put_metric(
            metric_name="QuotaUsage",
            value=float(usage_count),
            unit="Count",
            dimensions=dimensions
        )

        # Track percentage usage
        percentage = (usage_count / quota_limit * 100) if quota_limit > 0 else 0
        return self.put_metric(
            metric_name="QuotaUsagePercentage",
            value=percentage,
            unit="Percent",
            dimensions=dimensions
        )

    def put_error_metric(
        self,
        api_name: str,
        error_type: str,
        operation: Optional[str] = None
    ) -> bool:
        """
        Track API errors by type.

        Args:
            api_name: Name of the API
            error_type: Type of error (QuotaExceeded, RateLimit, ServiceError, etc.)
            operation: Specific operation name

        Returns:
            True if metric published successfully
        """
        dimensions = {
            "APIName": api_name,
            "ErrorType": error_type
        }
        if operation:
            dimensions["Operation"] = operation

        return self.put_metric(
            metric_name="APIError",
            value=1.0,
            unit="Count",
            dimensions=dimensions
        )
