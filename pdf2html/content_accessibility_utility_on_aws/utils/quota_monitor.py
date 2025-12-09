"""
Quota Monitor for tracking API usage against limits and sending alerts.
"""
import boto3
import logging
import os
from typing import Optional, Dict
from datetime import datetime, timezone
from .cloudwatch_metrics import CloudWatchMetricsPublisher

logger = logging.getLogger(__name__)


class QuotaMonitor:
    """Monitors API usage against quota limits and sends alerts."""

    def __init__(
        self,
        api_name: str,
        quota_limit: Optional[int] = None,
        warning_threshold: float = 0.8,
        critical_threshold: float = 0.95
    ):
        """
        Initialize quota monitor.

        Args:
            api_name: Name of the API being monitored
            quota_limit: Maximum allowed API calls (None = no limit)
            warning_threshold: Percentage to trigger warning (0.0-1.0)
            critical_threshold: Percentage to trigger critical alert (0.0-1.0)
        """
        self.api_name = api_name
        self.quota_limit = quota_limit
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.metrics_publisher = CloudWatchMetricsPublisher()

        try:
            self.sns_client = boto3.client('sns')
            self.sns_topic_arn = os.environ.get('QUOTA_ALERT_SNS_TOPIC_ARN')
        except Exception as e:
            logger.warning(f"Failed to initialize SNS client: {e}")
            self.sns_client = None
            self.sns_topic_arn = None

        try:
            self.dynamodb = boto3.resource('dynamodb')
            self.usage_table_name = os.environ.get('USAGE_TRACKING_TABLE', 'pdf-accessibility-usage')
            self.usage_table = self.dynamodb.Table(self.usage_table_name)
        except Exception as e:
            logger.warning(f"Failed to initialize DynamoDB: {e}")
            self.usage_table = None

    def track_api_call(
        self,
        operation: str,
        success: bool = True,
        error_type: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Track an API call and check against quota limits.

        Args:
            operation: Operation name (e.g., "AutotagPDF", "ExtractPDF")
            success: Whether the call succeeded
            error_type: Type of error if failed

        Returns:
            Dictionary with usage info and alert status
        """
        result = {
            "success": success,
            "usage_count": 0,
            "quota_limit": self.quota_limit,
            "usage_percentage": 0.0,
            "alert_sent": False,
            "quota_exceeded": False
        }

        # Publish metrics to CloudWatch
        self.metrics_publisher.put_api_call_metric(
            api_name=self.api_name,
            success=success,
            operation=operation
        )

        if error_type:
            self.metrics_publisher.put_error_metric(
                api_name=self.api_name,
                error_type=error_type,
                operation=operation
            )

        # Track usage in DynamoDB if available
        if success and self.usage_table:
            try:
                usage_count = self._increment_usage_counter(operation)
                result["usage_count"] = usage_count

                # Check quota limits
                if self.quota_limit and self.quota_limit > 0:
                    usage_percentage = usage_count / self.quota_limit
                    result["usage_percentage"] = usage_percentage

                    # Publish quota usage metrics
                    self.metrics_publisher.put_quota_usage_metric(
                        api_name=self.api_name,
                        usage_count=usage_count,
                        quota_limit=self.quota_limit
                    )

                    # Check thresholds and send alerts
                    if usage_percentage >= 1.0:
                        result["quota_exceeded"] = True
                        result["alert_sent"] = self._send_alert(
                            level="CRITICAL",
                            message=f"QUOTA EXCEEDED: {self.api_name} has reached 100% of quota limit ({usage_count}/{self.quota_limit})",
                            usage_count=usage_count,
                            usage_percentage=usage_percentage
                        )
                    elif usage_percentage >= self.critical_threshold:
                        result["alert_sent"] = self._send_alert(
                            level="CRITICAL",
                            message=f"CRITICAL: {self.api_name} is at {usage_percentage*100:.1f}% of quota limit ({usage_count}/{self.quota_limit})",
                            usage_count=usage_count,
                            usage_percentage=usage_percentage
                        )
                    elif usage_percentage >= self.warning_threshold:
                        result["alert_sent"] = self._send_alert(
                            level="WARNING",
                            message=f"WARNING: {self.api_name} is at {usage_percentage*100:.1f}% of quota limit ({usage_count}/{self.quota_limit})",
                            usage_count=usage_count,
                            usage_percentage=usage_percentage
                        )

            except Exception as e:
                logger.error(f"Failed to track usage in DynamoDB: {e}")

        return result

    def _increment_usage_counter(self, operation: str) -> int:
        """
        Increment usage counter in DynamoDB and return current count.

        Args:
            operation: Operation name

        Returns:
            Current usage count
        """
        if not self.usage_table:
            return 0

        # Use current month as the tracking period
        period_key = datetime.now(timezone.utc).strftime("%Y-%m")

        try:
            response = self.usage_table.update_item(
                Key={
                    'api_name': self.api_name,
                    'period': period_key
                },
                UpdateExpression='ADD usage_count :inc SET last_updated = :timestamp, last_operation = :operation',
                ExpressionAttributeValues={
                    ':inc': 1,
                    ':timestamp': datetime.now(timezone.utc).isoformat(),
                    ':operation': operation
                },
                ReturnValues='ALL_NEW'
            )
            return int(response['Attributes'].get('usage_count', 0))
        except Exception as e:
            logger.error(f"Failed to increment usage counter: {e}")
            return 0

    def get_current_usage(self) -> Dict[str, any]:
        """
        Get current usage statistics.

        Returns:
            Dictionary with usage statistics
        """
        if not self.usage_table:
            return {"error": "Usage tracking not available"}

        period_key = datetime.now(timezone.utc).strftime("%Y-%m")

        try:
            response = self.usage_table.get_item(
                Key={
                    'api_name': self.api_name,
                    'period': period_key
                }
            )

            if 'Item' in response:
                item = response['Item']
                usage_count = int(item.get('usage_count', 0))
                usage_percentage = (usage_count / self.quota_limit) if self.quota_limit else 0

                return {
                    "api_name": self.api_name,
                    "period": period_key,
                    "usage_count": usage_count,
                    "quota_limit": self.quota_limit,
                    "usage_percentage": usage_percentage,
                    "last_updated": item.get('last_updated'),
                    "last_operation": item.get('last_operation')
                }
            else:
                return {
                    "api_name": self.api_name,
                    "period": period_key,
                    "usage_count": 0,
                    "quota_limit": self.quota_limit,
                    "usage_percentage": 0.0
                }

        except Exception as e:
            logger.error(f"Failed to get current usage: {e}")
            return {"error": str(e)}

    def _send_alert(
        self,
        level: str,
        message: str,
        usage_count: int,
        usage_percentage: float
    ) -> bool:
        """
        Send alert via SNS.

        Args:
            level: Alert level (WARNING, CRITICAL)
            message: Alert message
            usage_count: Current usage count
            usage_percentage: Usage percentage

        Returns:
            True if alert sent successfully
        """
        if not self.sns_client or not self.sns_topic_arn:
            logger.warning(f"SNS not configured, skipping alert: {message}")
            return False

        try:
            subject = f"[{level}] PDF Accessibility - {self.api_name} Quota Alert"

            detailed_message = f"""
{message}

Details:
- API: {self.api_name}
- Usage: {usage_count} / {self.quota_limit} calls
- Percentage: {usage_percentage*100:.2f}%
- Timestamp: {datetime.now(timezone.utc).isoformat()}

{"Action Required: The quota limit has been reached. The application may stop working until the quota resets." if usage_percentage >= 1.0 else "Action Recommended: Monitor usage closely. Consider upgrading your plan or reducing API calls."}

View CloudWatch Dashboard: https://console.aws.amazon.com/cloudwatch/
"""

            self.sns_client.publish(
                TopicArn=self.sns_topic_arn,
                Subject=subject,
                Message=detailed_message
            )

            logger.info(f"Alert sent: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send SNS alert: {e}")
            return False

    def check_quota_available(self) -> bool:
        """
        Check if quota is available for making API calls.

        Returns:
            True if quota is available, False if exceeded
        """
        if not self.quota_limit:
            return True  # No limit set

        usage_info = self.get_current_usage()
        if "error" in usage_info:
            logger.warning("Could not check quota, allowing call")
            return True

        usage_count = usage_info.get("usage_count", 0)
        return usage_count < self.quota_limit
