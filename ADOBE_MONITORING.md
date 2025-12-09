# Adobe API Usage Monitoring Guide

This guide explains how to monitor your Adobe PDF Services API usage and track quota consumption.

## Table of Contents

- [Quick Usage Check](#quick-usage-check)
- [CloudWatch Dashboard](#cloudwatch-dashboard)
- [CloudWatch Metrics Queries](#cloudwatch-metrics-queries)
- [DynamoDB Direct Access](#dynamodb-direct-access)
- [Usage Monitoring Script](#usage-monitoring-script)
- [CloudWatch Alarms Status](#cloudwatch-alarms-status)
- [Log Analysis](#log-analysis)
- [Understanding Usage Data](#understanding-usage-data)
- [Troubleshooting](#troubleshooting)

---

## Quick Usage Check

### Check Current Month's Usage

The fastest way to check your current Adobe API usage:

```bash
aws dynamodb get-item \
  --table-name pdf-accessibility-usage \
  --key '{"api_name": {"S": "AdobeAPI"}, "period": {"S": "2025-12"}}' \
  --region us-east-2 \
  --output json | jq '.Item | {usage_count: .usage_count.N, quota_limit: 25000, percentage: (.usage_count.N | tonumber / 25000 * 100), last_updated: .last_updated.S}'
```

**Example Output:**
```json
{
  "usage_count": "1523",
  "quota_limit": 25000,
  "percentage": 6.092,
  "last_updated": "2025-12-09T11:30:15.234Z"
}
```

### Change Period

To check a different month, update the period key:
```bash
# For January 2025
--key '{"api_name": {"S": "AdobeAPI"}, "period": {"S": "2025-01"}}'

# For February 2025
--key '{"api_name": {"S": "AdobeAPI"}, "period": {"S": "2025-02"}}'
```

---

## CloudWatch Dashboard

### Access the Dashboard

1. Open AWS Console: https://console.aws.amazon.com/cloudwatch/
2. Navigate to: **CloudWatch → Dashboards**
3. Select: `PDF_Processing_Dashboard-{timestamp}`

### Key Widgets to Monitor

#### 1. Adobe API Quota Usage
- **Type**: Line graph
- **Shows**: Percentage of quota used over time
- **Y-axis**: 0-100%
- **Update Frequency**: Every hour

**Interpretation:**
- Green zone (0-80%): Normal usage
- Yellow zone (80-95%): Approaching limit
- Red zone (95-100%): Critical, near quota exhaustion

#### 2. Adobe API Call Status
- **Type**: Stacked area chart
- **Shows**: Successful vs. Failed API calls
- **Colors**:
  - Green: Successful calls
  - Red: Failed calls

**Interpretation:**
- Rising red line: API errors increasing
- Flat green line: Stable, successful processing
- Spikes: Batch processing events

---

## CloudWatch Metrics Queries

### Query Usage Percentage

Get quota usage percentage for the last 24 hours:

```bash
aws cloudwatch get-metric-statistics \
  --namespace PDFAccessibility \
  --metric-name QuotaUsagePercentage \
  --dimensions Name=APIName,Value=AdobeAPI Name=Period,Value=Monthly \
  --start-time $(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Maximum \
  --region us-east-2
```

### Query Total API Calls

Get total API call count for the last 30 days:

```bash
aws cloudwatch get-metric-statistics \
  --namespace PDFAccessibility \
  --metric-name APICallCount \
  --dimensions Name=APIName,Value=AdobeAPI \
  --start-time $(date -u -d '30 days ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Sum \
  --region us-east-2
```

### Query Success vs. Failure Rates

**Successful Calls:**
```bash
aws cloudwatch get-metric-statistics \
  --namespace PDFAccessibility \
  --metric-name APICallStatus \
  --dimensions Name=APIName,Value=AdobeAPI Name=Status,Value=Success \
  --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Sum \
  --region us-east-2
```

**Failed Calls:**
```bash
aws cloudwatch get-metric-statistics \
  --namespace PDFAccessibility \
  --metric-name APICallStatus \
  --dimensions Name=APIName,Value=AdobeAPI Name=Status,Value=Failure \
  --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Sum \
  --region us-east-2
```

### Query Error Types

Check quota exceeded errors:

```bash
aws cloudwatch get-metric-statistics \
  --namespace PDFAccessibility \
  --metric-name APIError \
  --dimensions Name=APIName,Value=AdobeAPI Name=ErrorType,Value=QuotaExceeded \
  --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Sum \
  --region us-east-2
```

---

## DynamoDB Direct Access

### AWS Console Method

1. Go to AWS Console: https://console.aws.amazon.com/dynamodb/
2. Navigate to: **DynamoDB → Tables**
3. Select table: `pdf-accessibility-usage`
4. Click: **"Explore table items"**
5. Look for item with:
   - `api_name`: AdobeAPI
   - `period`: 2025-12 (current month)

### Item Attributes

Each usage record contains:

| Attribute | Type | Description | Example |
|-----------|------|-------------|---------|
| `api_name` | String | API identifier (partition key) | AdobeAPI |
| `period` | String | Usage period YYYY-MM (sort key) | 2025-12 |
| `usage_count` | Number | Total API calls this period | 1523 |
| `last_updated` | String | ISO timestamp of last call | 2025-12-09T11:30:15.234Z |
| `last_operation` | String | Last operation type | AutotagPDF or ExtractPDF |

### Query with AWS CLI

Get full item details:

```bash
aws dynamodb get-item \
  --table-name pdf-accessibility-usage \
  --key '{"api_name": {"S": "AdobeAPI"}, "period": {"S": "2025-12"}}' \
  --region us-east-2
```

### Scan All Periods

Get usage history for all months:

```bash
aws dynamodb scan \
  --table-name pdf-accessibility-usage \
  --filter-expression "api_name = :api" \
  --expression-attribute-values '{":api":{"S":"AdobeAPI"}}' \
  --region us-east-2
```

---

## Usage Monitoring Script

### Automated Usage Report Script

Create `check_adobe_usage.sh`:

```bash
#!/bin/bash

#===========================================
# Adobe API Usage Monitoring Script
#===========================================
# This script checks current Adobe API usage
# against the configured quota limit.
#===========================================

# Configuration
REGION="us-east-2"
TABLE_NAME="pdf-accessibility-usage"
QUOTA_LIMIT=25000
PERIOD=$(date +%Y-%m)

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   Adobe API Usage Report${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo "Period: $PERIOD"
echo "Quota Limit: $QUOTA_LIMIT calls/month"
echo "Region: $REGION"
echo ""

# Query DynamoDB
RESULT=$(aws dynamodb get-item \
  --table-name "$TABLE_NAME" \
  --key "{\"api_name\": {\"S\": \"AdobeAPI\"}, \"period\": {\"S\": \"$PERIOD\"}}" \
  --region "$REGION" \
  --output json 2>/dev/null)

if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Failed to query DynamoDB${NC}"
    echo "Please check:"
    echo "  1. AWS credentials are configured"
    echo "  2. Table 'pdf-accessibility-usage' exists"
    echo "  3. You have read permissions"
    exit 1
fi

# Check if item exists
if [ -z "$RESULT" ] || [ "$RESULT" == "{}" ]; then
    echo -e "${YELLOW}No usage data found for $PERIOD${NC}"
    echo ""
    echo "This is normal if:"
    echo "  - No Adobe API calls have been made this month"
    echo "  - The table was recently created"
    echo ""
    echo "Current Usage: 0 / $QUOTA_LIMIT calls"
    echo "Percentage Used: 0.00%"
    echo "Remaining: $QUOTA_LIMIT calls"
    exit 0
fi

# Extract values
USAGE=$(echo "$RESULT" | jq -r '.Item.usage_count.N // "0"')
LAST_UPDATED=$(echo "$RESULT" | jq -r '.Item.last_updated.S // "N/A"')
LAST_OP=$(echo "$RESULT" | jq -r '.Item.last_operation.S // "N/A"')

# Calculate percentage and remaining
PERCENTAGE=$(echo "scale=2; $USAGE / $QUOTA_LIMIT * 100" | bc)
REMAINING=$((QUOTA_LIMIT - USAGE))

# Display usage information
echo "================================================"
echo "Current Usage: $USAGE / $QUOTA_LIMIT calls"
echo "Percentage Used: $PERCENTAGE%"
echo "Remaining: $REMAINING calls"
echo "================================================"
echo ""
echo "Last Activity:"
echo "  Updated: $LAST_UPDATED"
echo "  Operation: $LAST_OP"
echo ""

# Status assessment
if (( $(echo "$PERCENTAGE >= 100" | bc -l) )); then
    echo -e "${RED}🚨 CRITICAL: Quota limit reached!${NC}"
    echo ""
    echo "Action Required:"
    echo "  1. No more Adobe API calls can be made this month"
    echo "  2. Consider upgrading your Adobe plan"
    echo "  3. Wait for quota reset at month boundary"
    echo ""
elif (( $(echo "$PERCENTAGE >= 95" | bc -l) )); then
    echo -e "${RED}⚠️  CRITICAL: You've used $PERCENTAGE% of your quota!${NC}"
    echo ""
    echo "Action Required:"
    echo "  1. Only $REMAINING calls remaining"
    echo "  2. Upgrade Adobe plan or reduce usage"
    echo "  3. Monitor usage closely"
    echo ""
elif (( $(echo "$PERCENTAGE >= 80" | bc -l) )); then
    echo -e "${YELLOW}⚠️  WARNING: You've used $PERCENTAGE% of your quota${NC}"
    echo ""
    echo "Recommendation:"
    echo "  1. Monitor usage more frequently"
    echo "  2. Plan for potential upgrade"
    echo "  3. $REMAINING calls remaining this month"
    echo ""
else
    echo -e "${GREEN}✅ Usage is within normal range${NC}"
    echo ""
    echo "Status: Healthy"
    echo "Remaining capacity: $REMAINING calls ($PERCENTAGE% used)"
    echo ""
fi

# Display CloudWatch Dashboard link
echo "================================================"
echo "View detailed metrics in CloudWatch Dashboard:"
echo "https://console.aws.amazon.com/cloudwatch/home?region=$REGION#dashboards:"
echo "================================================"
echo ""
```

### Make Script Executable

```bash
chmod +x check_adobe_usage.sh
```

### Run the Script

```bash
./check_adobe_usage.sh
```

### Example Output

```
================================================
   Adobe API Usage Report
================================================

Period: 2025-12
Quota Limit: 25000 calls/month
Region: us-east-2

================================================
Current Usage: 1523 / 25000 calls
Percentage Used: 6.09%
Remaining: 23477 calls
================================================

Last Activity:
  Updated: 2025-12-09T11:30:15.234Z
  Operation: AutotagPDF

✅ Usage is within normal range

Status: Healthy
Remaining capacity: 23477 calls (6.09% used)

================================================
View detailed metrics in CloudWatch Dashboard:
https://console.aws.amazon.com/cloudwatch/home?region=us-east-2#dashboards:
================================================
```

### Schedule Automated Reports

Run the script daily using cron:

```bash
# Edit crontab
crontab -e

# Add daily report at 9 AM
0 9 * * * /path/to/check_adobe_usage.sh >> /var/log/adobe-usage.log 2>&1

# Or send via email
0 9 * * * /path/to/check_adobe_usage.sh | mail -s "Adobe API Usage Report" your-email@example.com
```

---

## CloudWatch Alarms Status

### Check Alarm States

See if any quota alarms have been triggered:

```bash
aws cloudwatch describe-alarms \
  --alarm-names adobe-api-quota-warning adobe-api-quota-critical adobe-api-quota-exceeded \
  --region us-east-2 \
  --query 'MetricAlarms[*].[AlarmName,StateValue,StateReason]' \
  --output table
```

**Example Output:**
```
-------------------------------------------------------------------
|                        DescribeAlarms                           |
+---------------------------+-----------+-------------------------+
|  adobe-api-quota-warning  |  OK       |  Threshold not breached |
|  adobe-api-quota-critical |  OK       |  Threshold not breached |
|  adobe-api-quota-exceeded |  OK       |  Threshold not breached |
+---------------------------+-----------+-------------------------+
```

### Alarm States Explained

| State | Meaning | Action |
|-------|---------|--------|
| **OK** | Below threshold | Normal operation |
| **ALARM** | Threshold breached | Alert sent via SNS |
| **INSUFFICIENT_DATA** | Not enough data | Wait for more API calls |

### Get Alarm History

See when alarms were triggered:

```bash
aws cloudwatch describe-alarm-history \
  --alarm-name adobe-api-quota-warning \
  --start-date $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%S) \
  --region us-east-2
```

---

## Log Analysis

### View ECS Task Logs with Quota Information

Check real-time logs for quota tracking:

```bash
aws logs tail /ecs/MyFirstTaskDef/PythonContainerLogGroup \
  --region us-east-2 \
  --follow \
  --filter-pattern "quota"
```

### Search for Quota Exceeded Errors

```bash
aws logs filter-log-events \
  --log-group-name /ecs/MyFirstTaskDef/PythonContainerLogGroup \
  --region us-east-2 \
  --filter-pattern "quota exceeded" \
  --start-time $(date -u -d '7 days ago' +%s)000
```

### Get Recent Adobe API Operations

```bash
aws logs filter-log-events \
  --log-group-name /ecs/MyFirstTaskDef/PythonContainerLogGroup \
  --region us-east-2 \
  --filter-pattern "AutotagPDF OR ExtractPDF" \
  --start-time $(date -u -d '1 hour ago' +%s)000 \
  --max-items 20
```

### CloudWatch Insights Queries

Use CloudWatch Logs Insights for advanced analysis:

**Query: Quota usage warnings**
```
fields @timestamp, @message
| filter @message like /quota/
| sort @timestamp desc
| limit 100
```

**Query: Failed API calls**
```
fields @timestamp, @message
| filter @message like /Exception encountered while executing operation/
| stats count() by bin(5m)
```

**Query: Operation distribution**
```
fields @timestamp, @message
| filter @message like /AutotagPDF/ or @message like /ExtractPDF/
| parse @message /(?<operation>AutotagPDF|ExtractPDF)/
| stats count() by operation
```

---

## Understanding Usage Data

### How Usage is Tracked

1. **Before API Call**: QuotaMonitor checks if quota is available
2. **After Successful Call**: Usage counter incremented in DynamoDB
3. **Metrics Published**: CloudWatch receives usage percentage
4. **Threshold Check**: If usage exceeds 80%, 95%, or 100%, alert sent

### Usage Counter Reset

- **Period Format**: `YYYY-MM` (e.g., `2025-12`)
- **Reset Behavior**: Automatic at month boundary
- **No Manual Reset**: Usage counter persists for historical tracking

### What Counts as an API Call

Each of these operations counts as 1 API call:
- **AutotagPDF**: PDF accessibility tagging with report generation
- **ExtractPDF**: Text, table, and figure extraction

**Note**: Both operations are called for each PDF processed, so each PDF = 2 API calls.

### Quota Limits by Plan

| Adobe Plan | Monthly Quota | Cost |
|------------|---------------|------|
| Free Tier | 500 calls | Free |
| 25K Pack | 25,000 calls | Paid |
| Enterprise | Custom | Contact Adobe |

---

## Troubleshooting

### Issue: No Usage Data in DynamoDB

**Possible Causes:**
1. No Adobe API calls have been made yet
2. DynamoDB table doesn't exist
3. ECS task doesn't have permissions

**Solutions:**
```bash
# Verify table exists
aws dynamodb describe-table \
  --table-name pdf-accessibility-usage \
  --region us-east-2

# Check ECS task role permissions
aws iam get-role-policy \
  --role-name PDFAccessibility-EcsTaskExecutionRole* \
  --policy-name dynamodb-access
```

### Issue: CloudWatch Metrics Not Appearing

**Possible Causes:**
1. Quota monitor not initialized
2. ECS task doesn't have CloudWatch permissions
3. Environment variables not set

**Solutions:**
```bash
# Check ECS task environment variables
aws ecs describe-task-definition \
  --task-definition MyFirstTaskDef \
  --region us-east-2 \
  --query 'taskDefinition.containerDefinitions[0].environment'

# Verify ADOBE_API_QUOTA_LIMIT is set
# Verify QUOTA_ALERT_SNS_TOPIC_ARN is set
# Verify USAGE_TRACKING_TABLE is set
```

### Issue: Not Receiving Email Alerts

**Possible Causes:**
1. SNS subscription not confirmed
2. Email in spam folder
3. SNS topic not configured

**Solutions:**
```bash
# Check SNS subscription status
aws sns list-subscriptions-by-topic \
  --topic-arn $(aws cloudformation describe-stacks \
    --stack-name PDFAccessibility \
    --region us-east-2 \
    --query "Stacks[0].Outputs[?OutputKey=='QuotaAlertTopicArn'].OutputValue" \
    --output text) \
  --region us-east-2

# Status should be "Confirmed", not "PendingConfirmation"
```

### Issue: Quota Exceeded Errors

**Immediate Actions:**
1. Stop processing PDFs temporarily
2. Check current usage: `./check_adobe_usage.sh`
3. Verify quota limit: `echo $ADOBE_API_QUOTA_LIMIT`

**Long-term Solutions:**
1. Upgrade Adobe plan
2. Optimize processing (batch smaller files)
3. Implement queue system for overflow

### Issue: Inaccurate Usage Count

**Possible Causes:**
1. DynamoDB eventual consistency
2. Failed API calls not tracked
3. Multiple periods overlapping

**Solutions:**
```bash
# Force DynamoDB consistent read
aws dynamodb get-item \
  --table-name pdf-accessibility-usage \
  --key '{"api_name": {"S": "AdobeAPI"}, "period": {"S": "2025-12"}}' \
  --consistent-read \
  --region us-east-2

# Compare with CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace PDFAccessibility \
  --metric-name APICallCount \
  --dimensions Name=APIName,Value=AdobeAPI \
  --start-time $(date -u -d '30 days ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 2592000 \
  --statistics Sum \
  --region us-east-2
```

---

## Best Practices

### Daily Monitoring
1. Run `check_adobe_usage.sh` daily
2. Check CloudWatch Dashboard weekly
3. Review alarm status before large batches

### Proactive Management
1. Set up cron job for automated reports
2. Monitor trends, not just current usage
3. Plan upgrades before reaching 80%

### Cost Optimization
1. Batch process during off-peak hours
2. Optimize PDF sizes before processing
3. Cache results when possible

### Alert Management
1. Confirm SNS email subscription immediately
2. Add multiple notification emails
3. Integrate with Slack/Teams for real-time alerts

---

## Additional Resources

- [AWS CloudWatch Documentation](https://docs.aws.amazon.com/cloudwatch/)
- [AWS DynamoDB Documentation](https://docs.aws.amazon.com/dynamodb/)
- [Adobe PDF Services API Documentation](https://developer.adobe.com/document-services/apis/pdf-services/)
- [QUOTA_MONITORING.md](./QUOTA_MONITORING.md) - Complete quota monitoring setup guide

---

## Support

For issues or questions about Adobe API monitoring:

1. Check CloudWatch Logs for error details
2. Review DynamoDB table for usage data
3. Verify environment variables are set correctly
4. Consult [QUOTA_MONITORING.md](./QUOTA_MONITORING.md) for troubleshooting

**AWS Resources:**
- CloudWatch Dashboard: `PDF_Processing_Dashboard-{timestamp}`
- DynamoDB Table: `pdf-accessibility-usage`
- SNS Topic: `pdf-accessibility-quota-alerts`
- CloudWatch Alarms: `adobe-api-quota-*`
