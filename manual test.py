#list providers
python main.py providers

#list status
python main.py config-check

#list S3 files
python main.py list s3://storagedemo221098david

#upload file to S3
python main.py copy ./files/archivo-local.txt s3://storagedemo221098david/file.txt


#Copy file from AWS S3 to Azure Blob Storage
python main.py copy s3://storagedemo221098david/imagen1.png azure://test-container/imagen1.png

#Copy file from Azure Blob Storage to google Cloud Storage
python main.py copy azure://test-container/imagen1.png gcs://multinube-221098-david/imagen1.png

#copy file from Google Cloud Storage to AWS S3
python main.py copy gcs://multinube-221098-david/imagen1.png s3://storagedemo221098david/imagen1.png

#Copy file from local to Google Cloud Storage
python main.py copy ./local-file.txt gcs://multinube-221098-david/file.txt

