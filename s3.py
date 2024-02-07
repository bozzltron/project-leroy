import boto3

aws_access_key_id = 'your_access_key_id'
aws_secret_access_key = 'your_secret_access_key'
aws_region = 'us-east-1'
s3_bucket_name = 'project-leroy'
image_file_path = 'path_to_your_image.jpg'  # Replace with the actual image file path
s3_object_key = 'destination/path/image.jpg'  # Replace with the desired S3 object key


def sync_files_to_s3():
    s3_client = boto3.client(
        's3',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=aws_region
    )

    s3_client.upload_file(image_file_path, s3_bucket_name, s3_object_key)