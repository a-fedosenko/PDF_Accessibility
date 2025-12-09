"""
PDF Analyzer Lambda Function
Analyzes PDF files to estimate processing costs before remediation.
"""
import json
import boto3
import logging
import os
from datetime import datetime, timezone
from urllib.parse import unquote_plus
import PyPDF2
from io import BytesIO

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# DynamoDB table for pending jobs
PENDING_JOBS_TABLE = os.environ.get('PENDING_JOBS_TABLE', 'pdf-accessibility-pending-jobs')


def estimate_elements_from_page(page):
    """
    Estimate number of structural elements in a PDF page.
    This is a rough estimate based on text content complexity.
    """
    try:
        text = page.extract_text()

        # Count potential elements
        elements = 0

        # Headings (estimate based on short lines with caps)
        lines = text.split('\n')
        for line in lines:
            stripped = line.strip()
            if stripped:
                # Potential heading (short, capitalized)
                if len(stripped) < 100 and stripped[0].isupper():
                    elements += 1
                # Regular text blocks
                elements += 1

        # Tables (estimate based on consistent spacing patterns)
        # Look for lines with multiple spaces/tabs
        table_indicators = sum(1 for line in lines if line.count('  ') >= 3 or '\t' in line)
        elements += table_indicators * 2  # Table + cells

        # Images (from page objects)
        if '/XObject' in page['/Resources']:
            xobjects = page['/Resources']['/XObject'].get_object()
            images = [obj for obj in xobjects if xobjects[obj]['/Subtype'] == '/Image']
            elements += len(images) * 2  # Image + alt text potential

        # Minimum 5 elements per page (conservative estimate)
        return max(elements, 5)

    except Exception as e:
        logger.warning(f"Error estimating elements: {e}")
        # Default conservative estimate
        return 10


def analyze_pdf(bucket, key):
    """
    Analyze PDF file without processing it.
    Returns statistics about the PDF.
    """
    try:
        # Download PDF from S3
        logger.info(f"Downloading PDF from s3://{bucket}/{key}")
        response = s3_client.get_object(Bucket=bucket, Key=key)
        pdf_content = response['Body'].read()
        pdf_size_bytes = len(pdf_content)

        # Open PDF
        pdf_file = BytesIO(pdf_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)

        # Basic stats
        num_pages = len(pdf_reader.pages)
        pdf_size_mb = pdf_size_bytes / (1024 * 1024)

        # Estimate total elements
        logger.info(f"Analyzing {num_pages} pages...")
        total_elements = 0
        sample_size = min(num_pages, 10)  # Sample first 10 pages for speed

        for i in range(sample_size):
            page = pdf_reader.pages[i]
            page_elements = estimate_elements_from_page(page)
            total_elements += page_elements

        # Extrapolate for all pages
        avg_elements_per_page = total_elements / sample_size
        estimated_total_elements = int(avg_elements_per_page * num_pages)

        # Calculate estimated Adobe transactions
        # Based on observed data: ~10 transactions per page for complex docs
        estimated_transactions = estimated_total_elements

        # Get metadata
        metadata = pdf_reader.metadata
        pdf_title = metadata.get('/Title', 'Unknown') if metadata else 'Unknown'

        analysis_result = {
            'file_key': key,
            'file_name': os.path.basename(key),
            'file_size_bytes': pdf_size_bytes,
            'file_size_mb': round(pdf_size_mb, 2),
            'num_pages': num_pages,
            'estimated_elements': estimated_total_elements,
            'avg_elements_per_page': round(avg_elements_per_page, 1),
            'estimated_adobe_transactions': estimated_transactions,
            'estimated_cost_percentage': round((estimated_transactions / 25000) * 100, 2),
            'pdf_title': pdf_title,
            'analysis_timestamp': datetime.now(timezone.utc).isoformat(),
            'status': 'analyzed',
            'complexity': classify_complexity(avg_elements_per_page)
        }

        logger.info(f"Analysis complete: {num_pages} pages, ~{estimated_transactions} transactions")
        return analysis_result

    except Exception as e:
        logger.error(f"Error analyzing PDF: {e}", exc_info=True)
        raise


def classify_complexity(avg_elements):
    """Classify document complexity based on elements per page."""
    if avg_elements < 5:
        return 'simple'
    elif avg_elements < 10:
        return 'moderate'
    elif avg_elements < 20:
        return 'complex'
    else:
        return 'very_complex'


def save_to_dynamodb(analysis_result):
    """Save analysis result to DynamoDB."""
    try:
        table = dynamodb.Table(PENDING_JOBS_TABLE)

        # Generate job ID
        job_id = f"{analysis_result['file_name']}_{int(datetime.now().timestamp())}"

        item = {
            'job_id': job_id,
            'user_email': analysis_result.get('user_email', 'unknown'),
            'file_key': analysis_result['file_key'],
            'file_name': analysis_result['file_name'],
            'file_size_mb': analysis_result['file_size_mb'],
            'num_pages': analysis_result['num_pages'],
            'estimated_transactions': analysis_result['estimated_adobe_transactions'],
            'complexity': analysis_result['complexity'],
            'status': 'pending_approval',
            'created_at': analysis_result['analysis_timestamp'],
            'ttl': int((datetime.now(timezone.utc).timestamp()) + (7 * 24 * 60 * 60))  # 7 days TTL
        }

        table.put_item(Item=item)
        logger.info(f"Saved analysis to DynamoDB with job_id: {job_id}")

        analysis_result['job_id'] = job_id
        return analysis_result

    except Exception as e:
        logger.error(f"Error saving to DynamoDB: {e}", exc_info=True)
        # Continue even if DynamoDB fails
        return analysis_result


def lambda_handler(event, context):
    """
    Lambda handler for PDF analysis.

    Triggered by S3 upload to pdf/ prefix.
    Analyzes PDF and stores results in DynamoDB.
    """
    try:
        logger.info(f"Event: {json.dumps(event)}")

        # Parse S3 event
        if 'Records' in event:
            # S3 event notification
            record = event['Records'][0]
            bucket = record['s3']['bucket']['name']
            key = unquote_plus(record['s3']['object']['key'])
        else:
            # Direct invocation (for testing)
            bucket = event['bucket']
            key = event['key']

        logger.info(f"Analyzing PDF: s3://{bucket}/{key}")

        # Analyze PDF
        analysis_result = analyze_pdf(bucket, key)

        # Save to DynamoDB
        analysis_result = save_to_dynamodb(analysis_result)

        # Return result (for API Gateway integration)
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True,
                'analysis': analysis_result
            })
        }

    except Exception as e:
        logger.error(f"Error in lambda_handler: {e}", exc_info=True)
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
