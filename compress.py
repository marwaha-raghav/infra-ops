import os
import datetime
from datetime import datetime, timedelta
import tarfile
from cryptography.fernet import Fernet
import boto3
from botocore.exceptions import NoCredentialsError
import hashlib

# path for creating the backups as described in task 3-b
backup_path = "/var/log/archives"


# get current time
def get_one_hour_prior():
    """Gets Hours(dd) -1 hour from current Hour.

    This function uses datetime.now and generates current hour minus 1 in 12h format
    Args:
        None

    Returns:
        int current_time: (dd) current hour - 1
    """
    raw_current_time = datetime.now()
    one_hour_prior = raw_current_time - timedelta(hours=1)
    current_time = one_hour_prior.strftime("%Y%m%d.%H")
    # print(current_time)
    return current_time


# define the path for the log files
def logs_directory():
    """Returns the path for the log files

    This function returns the log files path.
        None

    Returns:
        str path_logs
    """
    path_logs = "/var/log/events"
    return path_logs


def search_log_directory(hour, file_path):
    # ls_output = os.system(f'ls {file_path}')
    file_of_interest = f"syslog.{hour}".strip()

    for file in os.listdir(file_path):
        if file_of_interest in file:
            print(f"Success: {file_of_interest} found in the {file_path}")

        else:
            print("Searching...")


# perform the compression of the log files in the file_path
def compress_logs(hour, file_path):
    """Creates the tar.gz compressed version of the specified logfile

    This function creates the tar.gz file of the specified log file.
    args:
       a. hour(int): The previous hour value
       b. file_path (str): The path of the log files.

    Returns:
        None
    """
    search_log_directory(hour, file_path)
    file_of_interest = f"syslog.{hour}".strip()
    with tarfile.open(f"{file_path}/{file_of_interest}.tar.gz", "w:gz") as tarball:
        tarball.add(f"{file_path}/{file_of_interest}")
        tarball_name = f"{file_path}/{file_of_interest}.tar.gz"
        print(f"Successfully Created {tarball_name}")


def generate_encryption_key():
    """Generates encryption key using Fernet Class

    This function creates encryption key
    args:
       None

    Returns:
        None;
    """
    key = Fernet.generate_key()
    with open("encryption.key", "wb") as enc_key:
        enc_key.write(key)


def encrypt_tarball(file_path, hour):
    """Encrypts the tarball

    This function encrypts the tarball
    args:
       a. hour(int): The previous hour value
       b. file_path (str): The path of the log files.

    Returns:
        None
    """
    generate_encryption_key()
    file_of_interest = f"syslog.{hour}".strip()
    with open("encryption.key", "rb") as key_file:
        key = key_file.read()
        # generate instance of Fernet class with the key
        fernet = Fernet(key)
        # encrypting the file
        tarball_name = f"{file_path}/{file_of_interest}.tar.gz"
        with open(f"{tarball_name}", "rb") as file:
            tar_contents = file.read()
        # Encrypt the file data
        encrypted_tar_contents = fernet.encrypt(tar_contents)
        with open(f"{tarball_name}.encrypted", "wb") as encrypted_file:
            encrypted_file.write(encrypted_tar_contents)
    print("Encryption performed. Key also saved'.")


def generate_log_name(hour):
    logname = f"syslog.{hour}".strip()
    return logname


def generate_tarball_name(file_path, file_of_interest):
    tarball_name = f"{file_path}/{file_of_interest}.tar.gz.encrypted"
    return tarball_name


def create_local_backup(back_path, file_path, file_of_interest):
    """Creates a Local Backup

    This copies the tarball to another folder
    args:
       a. hour(int): The previous hour value
       b. file_path (str): The path of the log files.
       c. back_path (str): New Path for backup

    Returns:
        None
    """
    result = os.system(
        f"cp {generate_tarball_name(file_path, file_of_interest)} {back_path}"
    )
    if result == 0:
        print("encrypted tar copied successfully \n")
    else:
        print("Not copied")


# uploading tarball on aws
def upload_to_s3(tar_ball, bucket, s3_file):
    """CUploads the file to s3 bucket

    This uploads the file to an s3 bucket
    args:
       a. tarball(str): local file to upload
       b. bucket (str): bucket name
       c. s3_file: filename/trags in s3 bucket

    Returns:
        response
    """
    s3_bucket = boto3.client("s3")

    try:
        response = s3_bucket.upload_file(f"{tar_ball}", bucket, s3_file)
        print("Uploaded")
        return response
    except FileNotFoundError:
        print("tarball not found")
        return False
    except NoCredentialsError:
        print("Credentials not provided in any manner")
        return False


def local_md5_check(tarball):
    # Calculate the Hash of the local file

    # by catching the response in upload_to_s3, capturing the etag from the response
    # if the etag and the local md5 digest match the upload was successful
    # since that means that the file integrity was mantained.
    hash_md5 = hashlib.md5()
    with open(tarball, "rb") as file:
        for chunk in iter(lambda: file.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


if __name__ == "__main__":
    bucket_name = "kyk-infraops-test"
    current_date = datetime.now()
    # Task 3-a Compress
    compress_logs(get_one_hour_prior(), logs_directory())
    # Tasl 3-a Encrypt
    encrypt_tarball(logs_directory(), get_one_hour_prior())
    # Task 3-b Create a Backup
    create_local_backup(
        backup_path, logs_directory(), generate_log_name(get_one_hour_prior())
    )
    reply = input(
        "----  Do you want to proceed with the s3 upload? Make sure creds are steup [Y/N]-------"
    )
    if reply.lower() == "y":
        s3_file_suffix = generate_log_name(get_one_hour_prior())
        s3_file_name = f"type=events/year={current_date.year}/month={current_date.month:02d}/day={current_date.day:02d}/{s3_file_suffix}"
        local_tarball_name = generate_tarball_name(
            logs_directory(), generate_log_name(get_one_hour_prior)
        )
        # Task 3-c Upload to S3
        s3_upload_response = upload_to_s3(local_tarball_name, bucket_name, s3_file_name)
        local_md5_digest = local_md5_check(local_tarball_name)
        # Task 3-d md5 Check
        if s3_upload_response is not None:
            etags = s3_upload_response["ETag"].strip('"')
            if etags == local_md5_check:
                print("Hashes match, upload went through")
            else:
                print("hashes do not match")
    else:
        print("You Chose not to upload to S3")
        exit(0)
