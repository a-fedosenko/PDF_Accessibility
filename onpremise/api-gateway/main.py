#!/usr/bin/env python3
"""
API Gateway for PDF Accessibility Solutions (On-Premises)
FastAPI backend that replaces AWS API Gateway and orchestrates PDF processing
"""
import os
import json
import uuid
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import boto3
from botocore.client import Config
import redis
import psycopg2
from psycopg2.extras import RealDictCursor
import jwt
from jwt import PyJWKClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
S3_ENDPOINT = os.getenv('S3_ENDPOINT', 'http://minio:9000')
S3_ACCESS_KEY = os.getenv('S3_ACCESS_KEY', 'minioadmin')
S3_SECRET_KEY = os.getenv('S3_SECRET_KEY', 'minioadmin123')
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'pdfaccessibility')

POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'postgres')
POSTGRES_PORT = int(os.getenv('POSTGRES_PORT', '5432'))
POSTGRES_USER = os.getenv('POSTGRES_USER', 'pdfuser')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'pdfpassword')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'pdf_accessibility')

REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379')

JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-me')
KEYCLOAK_URL = os.getenv('KEYCLOAK_URL', 'http://keycloak:8080')
KEYCLOAK_REALM = os.getenv('KEYCLOAK_REALM', 'pdf-accessibility')

# Initialize FastAPI app
app = FastAPI(
    title="PDF Accessibility API Gateway",
    description="On-premises API gateway for PDF accessibility remediation",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Initialize services
def get_s3_client():
    """Get MinIO/S3 client"""
    return boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        config=Config(signature_version='s3v4'),
        region_name='us-east-1'
    )

def get_redis_client():
    """Get Redis client"""
    return redis.from_url(REDIS_URL, decode_responses=True)

def get_db_connection():
    """Get PostgreSQL database connection"""
    return psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        database=POSTGRES_DB,
        cursor_factory=RealDictCursor
    )

# Pydantic models
class JobStatus(BaseModel):
    job_id: str
    status: str
    filename: str
    created_at: str
    updated_at: str
    progress: Optional[float] = 0.0
    error_message: Optional[str] = None
    result_url: Optional[str] = None

class UploadResponse(BaseModel):
    job_id: str
    filename: str
    message: str
    status: str

class UserInfo(BaseModel):
    user_id: str
    email: str
    username: str
    upload_quota: int
    uploads_used: int

# Authentication dependency
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token from Keycloak"""
    token = credentials.credentials
    try:
        # For development, allow a simple JWT secret verification
        # In production, verify with Keycloak's public key
        if JWT_SECRET_KEY != 'your-secret-key-change-me':
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        else:
            # Use Keycloak JWKS for production
            jwks_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"
            jwks_client = PyJWKClient(jwks_url)
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience="account"
            )

        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

# Routes
@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "PDF Accessibility API Gateway",
        "status": "operational",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health_check():
    """Detailed health check for all services"""
    health_status = {
        "api": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }

    # Check MinIO/S3
    try:
        s3_client = get_s3_client()
        s3_client.list_buckets()
        health_status["s3"] = "healthy"
    except Exception as e:
        health_status["s3"] = f"unhealthy: {str(e)}"

    # Check Redis
    try:
        redis_client = get_redis_client()
        redis_client.ping()
        health_status["redis"] = "healthy"
    except Exception as e:
        health_status["redis"] = f"unhealthy: {str(e)}"

    # Check PostgreSQL
    try:
        conn = get_db_connection()
        conn.close()
        health_status["postgres"] = "healthy"
    except Exception as e:
        health_status["postgres"] = f"unhealthy: {str(e)}"

    return health_status

@app.post("/upload", response_model=UploadResponse)
async def upload_pdf(
    file: UploadFile = File(...),
    user: dict = Depends(verify_token)
):
    """Upload PDF for processing"""

    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # Check user quota
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        user_id = user.get('sub') or user.get('user_id')

        # Get user's current usage
        cursor.execute(
            "SELECT upload_quota, uploads_used FROM users WHERE user_id = %s",
            (user_id,)
        )
        user_data = cursor.fetchone()

        if not user_data:
            # Create user record
            cursor.execute(
                "INSERT INTO users (user_id, email, upload_quota, uploads_used) VALUES (%s, %s, %s, %s)",
                (user_id, user.get('email', 'unknown'), 100, 0)
            )
            conn.commit()
            uploads_used = 0
            upload_quota = 100
        else:
            uploads_used = user_data['uploads_used']
            upload_quota = user_data['upload_quota']

        # Check quota
        if uploads_used >= upload_quota:
            raise HTTPException(status_code=429, detail="Upload quota exceeded")

        # Generate job ID
        job_id = str(uuid.uuid4())

        # Upload to MinIO
        s3_client = get_s3_client()
        s3_key = f"pdf/{job_id}/{file.filename}"

        # Read and upload file
        file_content = await file.read()
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            Body=file_content,
            ContentType='application/pdf'
        )

        logger.info(f"Uploaded file to S3: {s3_key}")

        # Create job record
        cursor.execute(
            """
            INSERT INTO jobs (job_id, user_id, filename, s3_key, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (job_id, user_id, file.filename, s3_key, 'pending', datetime.utcnow(), datetime.utcnow())
        )

        # Update user's usage
        cursor.execute(
            "UPDATE users SET uploads_used = uploads_used + 1 WHERE user_id = %s",
            (user_id,)
        )

        conn.commit()

        # Add to Redis queue for processing
        redis_client = get_redis_client()
        redis_client.rpush('pdf_processing_queue', json.dumps({
            'job_id': job_id,
            'filename': file.filename,
            's3_key': s3_key,
            'user_id': user_id
        }))

        logger.info(f"Created job {job_id} for user {user_id}")

        return UploadResponse(
            job_id=job_id,
            filename=file.filename,
            message="PDF uploaded successfully and queued for processing",
            status="pending"
        )

    except Exception as e:
        conn.rollback()
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    finally:
        cursor.close()
        conn.close()

@app.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(
    job_id: str,
    user: dict = Depends(verify_token)
):
    """Get job processing status"""

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        user_id = user.get('sub') or user.get('user_id')

        cursor.execute(
            """
            SELECT job_id, status, filename, created_at, updated_at,
                   progress, error_message, result_s3_key
            FROM jobs
            WHERE job_id = %s AND user_id = %s
            """,
            (job_id, user_id)
        )

        job = cursor.fetchone()

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        result_url = None
        if job['result_s3_key'] and job['status'] == 'completed':
            # Generate presigned URL for result download
            s3_client = get_s3_client()
            result_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': S3_BUCKET_NAME, 'Key': job['result_s3_key']},
                ExpiresIn=3600  # 1 hour
            )

        return JobStatus(
            job_id=job['job_id'],
            status=job['status'],
            filename=job['filename'],
            created_at=job['created_at'].isoformat(),
            updated_at=job['updated_at'].isoformat(),
            progress=job.get('progress', 0.0),
            error_message=job.get('error_message'),
            result_url=result_url
        )

    finally:
        cursor.close()
        conn.close()

@app.get("/jobs", response_model=List[JobStatus])
async def list_jobs(
    user: dict = Depends(verify_token),
    limit: int = 50,
    offset: int = 0
):
    """List user's jobs"""

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        user_id = user.get('sub') or user.get('user_id')

        cursor.execute(
            """
            SELECT job_id, status, filename, created_at, updated_at,
                   progress, error_message, result_s3_key
            FROM jobs
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """,
            (user_id, limit, offset)
        )

        jobs = cursor.fetchall()

        result = []
        s3_client = get_s3_client()

        for job in jobs:
            result_url = None
            if job['result_s3_key'] and job['status'] == 'completed':
                result_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': S3_BUCKET_NAME, 'Key': job['result_s3_key']},
                    ExpiresIn=3600
                )

            result.append(JobStatus(
                job_id=job['job_id'],
                status=job['status'],
                filename=job['filename'],
                created_at=job['created_at'].isoformat(),
                updated_at=job['updated_at'].isoformat(),
                progress=job.get('progress', 0.0),
                error_message=job.get('error_message'),
                result_url=result_url
            ))

        return result

    finally:
        cursor.close()
        conn.close()

@app.get("/user/info", response_model=UserInfo)
async def get_user_info(user: dict = Depends(verify_token)):
    """Get user information and quota"""

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        user_id = user.get('sub') or user.get('user_id')

        cursor.execute(
            "SELECT user_id, email, username, upload_quota, uploads_used FROM users WHERE user_id = %s",
            (user_id,)
        )

        user_data = cursor.fetchone()

        if not user_data:
            # Create user if not exists
            email = user.get('email', 'unknown')
            username = user.get('preferred_username', email.split('@')[0])

            cursor.execute(
                "INSERT INTO users (user_id, email, username, upload_quota, uploads_used) VALUES (%s, %s, %s, %s, %s) RETURNING *",
                (user_id, email, username, 100, 0)
            )
            conn.commit()
            user_data = cursor.fetchone()

        return UserInfo(
            user_id=user_data['user_id'],
            email=user_data['email'],
            username=user_data['username'],
            upload_quota=user_data['upload_quota'],
            uploads_used=user_data['uploads_used']
        )

    finally:
        cursor.close()
        conn.close()

@app.post("/user/update-quota")
async def update_user_quota(
    user_id: str,
    new_quota: int,
    user: dict = Depends(verify_token)
):
    """Update user quota (admin only)"""

    # Check if user is admin (implement your admin check logic)
    if not user.get('realm_access', {}).get('roles', []).count('admin'):
        raise HTTPException(status_code=403, detail="Admin access required")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "UPDATE users SET upload_quota = %s WHERE user_id = %s",
            (new_quota, user_id)
        )
        conn.commit()

        return {"message": "Quota updated successfully", "user_id": user_id, "new_quota": new_quota}

    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
