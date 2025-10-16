#!/usr/bin/env python3
"""
Upload a local directory to S3 (or S3-compatible) with:
- "only-missing" behavior (skip if object already exists),
- optional deletion of local files after successful upload,
- env-var defaults so you can just `export ...` then run.

ENV (all optional except AWS creds):
  S3_BUCKET         # e.g., birdsound
  S3_PREFIX         # e.g., uploaded_files
  S3_ENDPOINT       # e.g., https://<r2-or-minio-endpoint>
  AWS_REGION        # e.g., ap-southeast-1 (or AWS_DEFAULT_REGION)

Examples:
  python upload_to_s3.py --dir data --delete
  python upload_to_s3.py --dir data_temp/Audios --workers 4 --dry-run
  python upload_to_s3.py --dir data --prefix uploaded_files/ --endpoint https://<endpoint>
"""


import argparse
import concurrent.futures as cf
import mimetypes
import os
from pathlib import Path
import sys
import time

import boto3
from botocore.config import Config as BotoConfig
from boto3.s3.transfer import TransferConfig
from botocore.exceptions import ClientError

def parse_args():
    p = argparse.ArgumentParser(description="Upload a directory to S3 (only-missing; optional delete).")
    # Now optional flags; fall back to env
    p.add_argument("--bucket", default=os.getenv("S3_BUCKET"), help="S3 bucket name (env S3_BUCKET)")
    p.add_argument("--dir", required=True, help="Local directory to upload")
    p.add_argument("--prefix", default=os.getenv("S3_PREFIX", ""), help="Remote key prefix (env S3_PREFIX)")
    p.add_argument("--endpoint", default=os.getenv("S3_ENDPOINT", ""), help="Custom S3 endpoint URL (env S3_ENDPOINT)")
    p.add_argument("--region", default=os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "ap-southeast-1",
                   help="AWS Region (default from env or ap-southeast-1)")
    # Behavior flags
    p.add_argument("--only-missing", action="store_true", default=True,
                   help="Skip upload if the key already exists (default: True).")
    p.add_argument("--no-only-missing", dest="only_missing", action="store_false",
                   help="Disable the only-missing behavior.")
    p.add_argument("--delete", action="store_true", help="Delete local file after successful upload.")
    p.add_argument("--workers", type=int, default=4, help="Concurrent upload workers (default: 4).")
    p.add_argument("--dry-run", action="store_true", help="Print actions without uploading.")
    return p.parse_args()

def build_s3_client(endpoint: str, region: str):
    cfg = BotoConfig(
        retries={"max_attempts": 6, "mode": "standard"},
        connect_timeout=10,
        read_timeout=300,
        region_name=region,
        s3={"addressing_style": "path"},
    )
    kwargs = {"config": cfg}
    if endpoint:
        kwargs["endpoint_url"] = endpoint
    return boto3.client("s3", **kwargs)

TRANSFER_CFG = TransferConfig(
    multipart_threshold=8 * 1024 * 1024,  # 8 MB
    multipart_chunksize=8 * 1024 * 1024,
    max_concurrency=4,
    use_threads=True,
)

def guess_content_type(path: Path) -> str:
    ctype, _ = mimetypes.guess_type(str(path))
    if not ctype:
        if path.suffix.lower() == ".flac":
            return "audio/flac"
        if path.suffix.lower() == ".wav":
            return "audio/wav"
        return "application/octet-stream"
    return ctype

def key_for(local_base: Path, file_path: Path, prefix: str) -> str:
    rel = file_path.relative_to(local_base).as_posix()
    if prefix and not prefix.endswith("/"):
        prefix += "/"
    return f"{prefix}{rel}"

def object_exists(s3, bucket: str, key: str) -> bool:
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        status = e.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if code in {"404", "NotFound", "NoSuchKey"} or status == 404:
            return False
        raise  # surface permission/auth/endpoint issues

def upload_one(s3, bucket: str, path: Path, key: str, dry_run: bool, delete: bool):
    if dry_run:
        print(f"[DRY] Would upload: {path} -> s3://{bucket}/{key}")
        return "DRY"

    extra_args = {"ContentType": guess_content_type(path)}
    s3.upload_file(
        Filename=str(path),
        Bucket=bucket,
        Key=key,
        ExtraArgs=extra_args,
        Config=TRANSFER_CFG,
    )
    print(f"[OK ] Uploaded: {path} -> s3://{bucket}/{key}")

    if delete:
        try:
            path.unlink()
            print(f"[DEL] Removed local: {path}")
        except Exception as e:
            print(f"[WARN] Uploaded but failed to delete local {path}: {e}", file=sys.stderr)
    return "OK"

def walk_files(root: Path):
    for p in root.rglob("*"):
        if p.is_file():
            yield p

def main():
    args = parse_args()

    if not args.bucket:
        print("ERROR: S3 bucket is not set. Provide --bucket or set env S3_BUCKET.", file=sys.stderr)
        sys.exit(2)

    local_base = Path(args.dir).resolve()
    if not local_base.exists() or not local_base.is_dir():
        print(f"ERROR: directory not found: {local_base}", file=sys.stderr)
        sys.exit(3)

    s3 = build_s3_client(args.endpoint, args.region)

    tasks = []
    for f in walk_files(local_base):
        k = key_for(local_base, f, args.prefix)
        tasks.append((f, k))

    if not tasks:
        print("Nothing to upload.")
        return

    print(f"Found {len(tasks)} files under {local_base}")
    t0 = time.time()

    uploaded = skipped = failed = 0

    def work(item):
        nonlocal uploaded, skipped, failed
        f, k = item
        try:
            if args.only_missing and not args.dry_run:
                if object_exists(s3, args.bucket, k):
                    print(f"[SKP] Exists remotely, skipping: {f}")
                    return "SKIP"
            return upload_one(s3, args.bucket, f, k, args.dry_run, args.delete)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"[ERR] {f} -> s3://{args.bucket}/{k}: {e}", file=sys.stderr)
            return "ERR"

    try:
        with cf.ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
            for result in ex.map(work, tasks):
                if result in ("OK", "DRY"):
                    uploaded += 1
                elif result == "SKIP":
                    skipped += 1
                else:
                    failed += 1
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting early…", file=sys.stderr)

    dt = time.time() - t0
    print(f"\nDone. Uploaded: {uploaded}, Skipped: {skipped}, Failed: {failed}. Elapsed: {dt:.1f}s")

if __name__ == "__main__":
    main()
