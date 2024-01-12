# infra-ops

## Code-Overview
This repository contains; code written in python3 that tries to achieve 4 tasks:

- Compress and Encrypt a file
- Create a backup copy of a file
- Upload the file to an S3 bucket
- Compare the MD5 hash


### Libraries Used

- boto3 - for aws uploads.
- datetime - for calculating timestamps
- hashlib - for egenrating md5 digests of file
- os -for running os levels commands (unix specific)
- cryptogrpahy (fernet) for encryption of files.
- tarfile - for generating tar.gz

### Documenting the Code. 
The general workflow of the program is as follows

- get_one_hour_prior: This function uses the datetime library to calculate the current time in a specific manner and then calculate the delta of it by 1.
- we then use this value to generate the file name in the following format syslog.20240112.12 (which has hour-1 value aftet he period)
- using the value we try to match the output returned while looping through the result returned from os.listdir(), which returns all the files specified the log_file path (/var/log/events)
- if a match is found, we proceed with the compression of this file using tarfile library and get a tar.gz file, if not found and exception will be dsiplayed.
- once the tar.gz has been created, we use the fernet library and create a private key to encrypt the file with. 
- the file is read and an encrypted file is written with the same name appended with .encrypted. 
- This file is then also copied to another location /var/log/archive using the os.system(cp filename dest_path), the result is also checked for success or failure and an appropriate message is displayed. 
- An extra step has been added to ask the user for s3 uploads. 
- the file is then uploaded to the s3 bucket by using the boto3 library and the funtion upload_file() and the reponse is captured,and out of this json response, the e3 tags are extracted (md5 for uploaded file)
- md5 hash of the local file is also calculated and then compared with the remote uploaded one, if they match then the upload was successful if not then unsuccessful. 
