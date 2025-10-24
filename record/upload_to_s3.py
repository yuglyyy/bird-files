import hashlib
import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

import os

def should_upload_by_hash(path: str, rate: int = 200, salt: str = "") -> bool:
    """Select ~1/rate files deterministically using a hash of the basename."""
    name = os.path.basename(path)
    h = hashlib.sha256((salt + name).encode("utf-8")).hexdigest()
    return (int(h[:8], 16) % rate) == 0

def get_s3():
    """Build an S3 client that works for AWS S3, R2, or MinIO via endpoint env."""
    endpoint = os.getenv("S3_ENDPOINT")  # e.g., https://<accountid>.r2.cloudflarestorage.com
    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "auto"
    cfg = Config(signature_version="s3v4", retries={"max_attempts": 3, "mode": "standard"})
    return boto3.client("s3", endpoint_url=endpoint, region_name=region, config=cfg)

def s3_upload(local_path: str, key: str, content_type: str = None) -> bool:
    """Upload a single file; returns True/False."""
    bucket = os.getenv("S3_BUCKET")
    if not bucket:
        print("[s3] S3_BUCKET not set; skipping upload")
        return False
    s3 = get_s3()
    extra = {}
    if content_type:
        extra["ContentType"] = content_type
    try:
        s3.upload_file(local_path, bucket, key, ExtraArgs=extra or None)
        print(f"[s3] Uploaded s3://{bucket}/{key}")
        return True
    except (BotoCoreError, ClientError) as e:
        print(f"[s3] Upload failed for {local_path} -> {key}: {e}")
        return False
