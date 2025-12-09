"""
Start Remediation Lambda Function
Manually triggers Step Functions workflow for approved PDFs.
"""
import json
import boto3
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger()
logger.setLevel(logging.INFO)

stepfunctions_client = boto3.client('stepfunctions')
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

PENDING_JOBS_TABLE = os.environ.get('PENDING_JOBS_TABLE', 'pdf-accessibility-pending-jobs')
STATE_MACHINE_ARN = os.environ.get('STATE_MACHINE_ARN')
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME')


def lambda_handler(event, context):
    """
    Manually start remediation for an analyzed PDF.

    Request body:
    {
        "job_id": "test1-en.pdf_1733752800",
        "user_approved": true
    }
    """
    try:
        logger.info(f"Event: {json.dumps(event)}")

        # Parse request body
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event

        job_id = body.get('job_id')
        user_approved = body.get('user_approved', False)

        if not job_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': False,
                    'error': 'job_id is required'
                })
            }

        if not user_approved:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': False,
                    'error': 'user_approved must be true'
                })
            }

        # Get job details from DynamoDB
        table = dynamodb.Table(PENDING_JOBS_TABLE)
        response = table.get_item(Key={'job_id': job_id})

        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': False,
                    'error': f'Job {job_id} not found'
                })
            }

        job = response['Item']

        # Check if already processing
        if job.get('status') == 'processing':
            return {
                'statusCode': 409,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': False,
                    'error': 'Job is already processing'
                })
            }

        # Update status to processing
        table.update_item(
            Key={'job_id': job_id},
            UpdateExpression='SET #status = :status, approved_at = :timestamp',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': 'processing',
                ':timestamp': datetime.now(timezone.utc).isoformat()
            }
        )

        logger.info(f"Starting remediation for job {job_id}, file: {job['file_key']}")

        # Copy file from pdf-upload/ to pdf/ to trigger the workflow
        source_key = job['file_key']
        file_name = job['file_name']
        destination_key = f"pdf/{file_name}"

        try:
            # Copy the file to pdf/ prefix to trigger split_pdf Lambda
            logger.info(f"Copying {source_key} to {destination_key}")
            s3_client.copy_object(
                Bucket=S3_BUCKET_NAME,
                CopySource={'Bucket': S3_BUCKET_NAME, 'Key': source_key},
                Key=destination_key
            )
            logger.info(f"Successfully copied file to {destination_key}")

            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': True,
                    'job_id': job_id,
                    'message': 'Remediation started - file copied to processing folder',
                    'source_key': source_key,
                    'destination_key': destination_key,
                    'estimated_transactions': job['estimated_transactions']
                })
            }

        except Exception as copy_error:
            logger.error(f"Error copying file: {copy_error}", exc_info=True)

            # Revert status back to pending_approval
            table.update_item(
                Key={'job_id': job_id},
                UpdateExpression='SET #status = :status',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={':status': 'pending_approval'}
            )

            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': False,
                    'error': f'Failed to start processing: {str(copy_error)}'
                })
            }

    except Exception as e:
        logger.error(f"Error starting remediation: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }
