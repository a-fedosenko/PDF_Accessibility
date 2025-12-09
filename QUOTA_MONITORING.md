# Adobe API Quota Monitoring

This document explains how to configure and use the quota monitoring system for Adobe API calls.

## Overview

The PDF Accessibility application now includes comprehensive quota monitoring for Adobe PDF Services API. When your Adobe API usage approaches or exceeds your quota limits, the system will:

1. **Send email alerts** via Amazon SNS
2. **Log errors** with clear messages
3. **Prevent API calls** when quota is exceeded
4. **Track usage** in DynamoDB
5. **Display metrics** in CloudWatch Dashboard

## Features

### 1. Real-time Quota Tracking
- Monitors every Adobe API call (Autotag PDF and Extract PDF operations)
- Tracks usage against your configured monthly quota
- Stores usage data in DynamoDB for historical tracking

### 2. Multi-level Alerts
- **Warning Alert (80%)**: Sent when usage reaches 80% of quota
- **Critical Alert (95%)**: Sent when usage reaches 95% of quota
- **Quota Exceeded Alert**: Sent immediately when quota is exceeded

### 3. Automatic Prevention
- Checks quota availability before making API calls
- Prevents calls when quota is exceeded
- Returns clear error messages to users

### 4. CloudWatch Integration
- Custom metrics for quota usage percentage
- Metrics for API call success/failure rates
- Dashboard widgets showing real-time usage
- CloudWatch alarms for automatic notifications

## Configuration

### Step 1: Set Your Adobe API Quota Limit

Edit your `.env` file and set your Adobe API monthly quota:

```bash
# For Adobe free tier (typically 500 document transactions/month)
ADOBE_API_QUOTA_LIMIT=500

# For paid plans, set according to your subscription
ADOBE_API_QUOTA_LIMIT=10000
```

**Note**: If you set `ADOBE_API_QUOTA_LIMIT=0`, quota enforcement is disabled but usage is still tracked.

### Step 2: Configure Email Alerts

Set the email address where you want to receive quota alerts:

```bash
QUOTA_ALERT_EMAIL=your-email@example.com
```

After deployment, you'll receive a confirmation email from AWS SNS. **You must click the confirmation link** to start receiving alerts.

### Step 3: Deploy the Infrastructure

Deploy the CDK stack with the new quota monitoring resources:

```bash
# Export environment variables
export ADOBE_API_QUOTA_LIMIT=500
export QUOTA_ALERT_EMAIL=your-email@example.com

# Deploy
cdk deploy
```

This will create:
- SNS Topic: `pdf-accessibility-quota-alerts`
- DynamoDB Table: `pdf-accessibility-usage`
- CloudWatch Alarms: 3 alarms for monitoring quota usage
- CloudWatch Dashboard: Updated with quota metrics

## How It Works

### Architecture

```
┌─────────────────┐
│  ECS Task       │
│  (autotag.py)   │
└────────┬────────┘
         │
         ├─── Check quota before API call
         │
         ├─── Call Adobe API
         │
         └─── Track usage after call
                 │
                 ├──► CloudWatch Metrics
                 ├──► DynamoDB Usage Table
                 └──► SNS Alerts (if threshold reached)
```

### Workflow

1. **Before API Call**:
   - QuotaMonitor checks current usage in DynamoDB
   - If quota exceeded, raises exception and prevents call
   - User sees clear error message

2. **After Successful Call**:
   - Increments usage counter in DynamoDB
   - Publishes metrics to CloudWatch
   - Checks if threshold reached (80%, 95%, 100%)
   - Sends SNS alert if threshold crossed

3. **After Failed Call**:
   - Detects if failure was due to quota exceeded
   - Publishes error metrics to CloudWatch
   - Sends quota exceeded alert via SNS

## Monitoring Usage

### CloudWatch Dashboard

View your quota usage in the CloudWatch Dashboard:

1. Open AWS Console → CloudWatch → Dashboards
2. Select `PDF_Processing_Dashboard-{timestamp}`
3. Scroll to the quota monitoring widgets:
   - **Adobe API Quota Usage**: Line graph showing percentage used
   - **Adobe API Call Status**: Success vs. Failure counts

### DynamoDB Table

Query usage history in the DynamoDB table:

```bash
aws dynamodb get-item \
  --table-name pdf-accessibility-usage \
  --key '{"api_name": {"S": "AdobeAPI"}, "period": {"S": "2025-01"}}'
```

Response includes:
- `usage_count`: Total API calls this period
- `last_updated`: Timestamp of last call
- `last_operation`: Last operation type (AutotagPDF or ExtractPDF)

### CloudWatch Metrics

Query metrics using AWS CLI:

```bash
# Get current quota usage percentage
aws cloudwatch get-metric-statistics \
  --namespace PDFAccessibility \
  --metric-name QuotaUsagePercentage \
  --dimensions Name=APIName,Value=AdobeAPI Name=Period,Value=Monthly \
  --start-time 2025-01-01T00:00:00Z \
  --end-time 2025-01-31T23:59:59Z \
  --period 3600 \
  --statistics Maximum

# Get API call counts
aws cloudwatch get-metric-statistics \
  --namespace PDFAccessibility \
  --metric-name APICallCount \
  --dimensions Name=APIName,Value=AdobeAPI \
  --start-time 2025-01-01T00:00:00Z \
  --end-time 2025-01-31T23:59:59Z \
  --period 3600 \
  --statistics Sum
```

## Alert Examples

### Warning Alert (80% Usage)

```
Subject: [WARNING] PDF Accessibility - AdobeAPI Quota Alert

WARNING: AdobeAPI is at 82.4% of quota limit (412/500 calls)

Details:
- API: AdobeAPI
- Usage: 412 / 500 calls
- Percentage: 82.40%
- Timestamp: 2025-01-15T10:30:00Z

Action Recommended: Monitor usage closely. Consider upgrading your plan or reducing API calls.

View CloudWatch Dashboard: https://console.aws.amazon.com/cloudwatch/
```

### Critical Alert (95% Usage)

```
Subject: [CRITICAL] PDF Accessibility - AdobeAPI Quota Alert

CRITICAL: AdobeAPI is at 96.2% of quota limit (481/500 calls)

Details:
- API: AdobeAPI
- Usage: 481 / 500 calls
- Percentage: 96.20%
- Timestamp: 2025-01-15T14:45:00Z

Action Recommended: Monitor usage closely. Consider upgrading your plan or reducing API calls.

View CloudWatch Dashboard: https://console.aws.amazon.com/cloudwatch/
```

### Quota Exceeded Alert

```
Subject: [CRITICAL] PDF Accessibility - AdobeAPI Quota Alert

QUOTA EXCEEDED: AdobeAPI has reached 100% of quota limit (500/500)

Details:
- API: AdobeAPI
- Usage: 500 / 500 calls
- Percentage: 100.00%
- Timestamp: 2025-01-15T16:20:00Z

Action Required: The quota limit has been reached. The application may stop working until the quota resets.

View CloudWatch Dashboard: https://console.aws.amazon.com/cloudwatch/
```

## Error Messages

When quota is exceeded, users will see clear error messages:

### In Application Logs

```
ERROR - Filename : sample.pdf | Adobe API quota limit reached: Service usage limit exceeded
ERROR - Adobe API quota limit exceeded. Cannot process sample.pdf.
```

### In CloudWatch Logs

```
{
  "timestamp": "2025-01-15T16:20:00Z",
  "level": "ERROR",
  "message": "Adobe API quota limit exceeded. Please check your Adobe account or wait for quota reset.",
  "filename": "sample.pdf",
  "api_name": "AdobeAPI",
  "usage_count": 500,
  "quota_limit": 500
}
```

## Troubleshooting

### Not Receiving Email Alerts

1. **Check SNS Subscription**:
   ```bash
   aws sns list-subscriptions-by-topic \
     --topic-arn $(aws cloudformation describe-stacks \
       --stack-name PDFAccessibility \
       --query "Stacks[0].Outputs[?OutputKey=='QuotaAlertTopicArn'].OutputValue" \
       --output text)
   ```

2. **Confirm Subscription**: Check your email for SNS confirmation and click the link

3. **Check Spam Folder**: AWS SNS emails may be filtered as spam

### Quota Monitor Not Working

1. **Verify Environment Variables**:
   ```bash
   # In ECS task, check environment variables
   aws ecs describe-task-definition \
     --task-definition MyFirstTaskDef \
     --query 'taskDefinition.containerDefinitions[0].environment'
   ```

2. **Check IAM Permissions**: Ensure ECS task role has:
   - `cloudwatch:PutMetricData`
   - `sns:Publish` on quota alert topic
   - `dynamodb:GetItem`, `dynamodb:UpdateItem` on usage table

3. **Check DynamoDB Table**: Verify table exists:
   ```bash
   aws dynamodb describe-table --table-name pdf-accessibility-usage
   ```

### Usage Count Incorrect

The usage counter resets monthly. The period key format is `YYYY-MM`:
- January 2025: `2025-01`
- February 2025: `2025-02`

To manually reset usage (for testing):

```bash
aws dynamodb delete-item \
  --table-name pdf-accessibility-usage \
  --key '{"api_name": {"S": "AdobeAPI"}, "period": {"S": "2025-01"}}'
```

## Best Practices

1. **Set Realistic Limits**: Configure `ADOBE_API_QUOTA_LIMIT` according to your Adobe plan
2. **Monitor Proactively**: Check CloudWatch dashboard regularly
3. **Plan for Growth**: Upgrade Adobe plan before reaching limits
4. **Test Alerts**: Manually trigger alerts by setting a low quota limit temporarily
5. **Archive Old Data**: DynamoDB table uses PAY_PER_REQUEST billing, old periods persist

## Cost Considerations

The quota monitoring system adds minimal AWS costs:

- **SNS**: ~$0.50 per million notifications (alerts are rare)
- **DynamoDB**: Pay-per-request, ~$1.25 per million writes (one write per API call)
- **CloudWatch Metrics**: First 10 custom metrics free, then $0.30/metric/month
- **CloudWatch Alarms**: $0.10 per alarm per month (3 alarms = $0.30/month)

**Total estimated cost**: < $1/month for typical usage

## Future Enhancements

Potential improvements for the quota monitoring system:

- [ ] Per-user quota limits
- [ ] Weekly/daily quota tracking (in addition to monthly)
- [ ] Slack/Teams integration for alerts
- [ ] Automatic quota reset at month boundaries
- [ ] Quota usage predictions based on historical data
- [ ] Rate limiting (calls per minute/hour)
- [ ] Integration with Adobe's official quota API (when available)

## Support

For issues or questions about quota monitoring:

1. Check CloudWatch Logs for error details
2. Review this documentation
3. Check DynamoDB table for usage data
4. Verify environment variables are set correctly

## Related Documentation

- [Adobe PDF Services API Documentation](https://developer.adobe.com/document-services/apis/pdf-services/)
- [AWS CloudWatch Documentation](https://docs.aws.amazon.com/cloudwatch/)
- [AWS SNS Documentation](https://docs.aws.amazon.com/sns/)
- [AWS DynamoDB Documentation](https://docs.aws.amazon.com/dynamodb/)
