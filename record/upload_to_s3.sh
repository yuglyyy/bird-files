export AWS_ACCESS_KEY_ID=e938a0fb2164c511cb75eedeff17df1c
export AWS_SECRET_ACCESS_KEY=d80c095836a421c2852c69605a799eb9575f5038f73a0da3fe92a8d7f02cab95
export AWS_REGION=auto              
export S3_BUCKET=birdsound
export S3_ENDPOINT=https://a13e34d2c3a3a3a2a67b55a8afc26e5f.r2.cloudflarestorage.com

python upload_to_s3.py --dir data --delete