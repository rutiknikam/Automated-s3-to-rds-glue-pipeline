# Automated-s3-to-rds-glue-pipeline
# 📘 Automated Data Ingestion from Amazon S3 to RDS with AWS Glue Fallback (Dockerized Python App)

---

## 🎯 Objective

Develop a Dockerized Python application that automates:

✅ Reading a CSV file from an S3 bucket  
✅ Pushing it into an RDS (MySQL) database  
✅ If the RDS insert fails, fallback to:  
- Create a Glue table in the Glue Data Catalog  
- Register the dataset from the S3 location  

> This project teaches data flow, fault tolerance, and multi-service integration using AWS + Docker + Python.

---

## 🧰 Technologies Used

- **AWS S3** – Storage for source CSV  
- **AWS RDS (MySQL)** – Main database  
- **AWS Glue** – Fallback for failed data ingestion  
- **IAM** – Permissions and access management  
- **EC2** – Docker runtime environment  
- **Docker** – Containerize the Python app  
- **Python Libraries** – boto3, pandas, sqlalchemy, pymysql  

---

## 🛠️ Step-by-Step Implementation

### 🔹 Step 1: Launch EC2 Instance
- Launch Amazon Linux 2  
- Open ports in Security Group:  
  - SSH (22)  
  - HTTP (80) – optional  
  - MySQL/Aurora (3306)  

✅ Install Docker:
```bash
sudo yum update -y  
sudo yum install docker -y  
sudo service docker start  
sudo usermod -aG docker ec2-user  

### 🔹 Step 2: Setup IAM User
Go to IAM → Users → Create user

User name: s3-rds-glue-user

Enable programmatic access (Access Key + Secret)

Attach these policies:

AmazonS3FullAccess

AmazonRDSFullAccess

AWSGlueConsoleFullAccess

Download the Access Key ID and Secret Access Key

### 🔹 Step 3: Create RDS (MySQL) Database
Go to RDS → Create database

Engine: MySQL

DB Identifier: rds-mysql

DB Name: mydb

Master username: admin

Password: yourpassword

Public access: Yes

Port: 3306

Add EC2 Security Group to RDS inbound rules

### ✅ Create Database and Table in RDS (via EC2):

bash
Copy code
sudo yum install mariadb105-server -y
mysql -h <RDS-endpoint> -u admin -p

CREATE DATABASE mydb;
USE mydb;
CREATE TABLE students ( id INT, name VARCHAR(50));
### 🔹 Step 4: Upload CSV File to S3
Create a new S3 bucket (e.g., my-data-bucket)

Upload a file named data.csv

Example content:

csv
Copy code
id,name
1,Kishor
2,Kiran
3,Bharat
4,Yogesh
5,Prathmesh
🔹 Step 5: Create Python Script (main.py)
🎯 What it does:
✅ Reads CSV from S3
✅ Pushes data to RDS
✅ Falls back to Glue if RDS fails

🔧 main.py:
python
Copy code
import boto3
import pandas as pd
import os
import pymysql
from sqlalchemy import create_engine
from botocore.exceptions import NoCredentialsError

def read_csv_from_s3():
    print("📥 Reading CSV from S3...")
    s3 = boto3.client('s3',
        aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
        region_name=os.environ['AWS_DEFAULT_REGION']
    )
    try:
        s3.download_file(os.environ['S3_BUCKET'], os.environ['CSV_KEY'], 'data.csv')
        print("✅ CSV loaded")
        return pd.read_csv('data.csv')
    except Exception as e:
        print(f"❌ Failed to download CSV: {e}")
        raise

def upload_to_rds(df):
    print("📤 Trying to upload data to RDS...")
    try:
        engine = create_engine(
            f"mysql+pymysql://{os.environ['RDS_USER']}:{os.environ['RDS_PASSWORD']}@"
            f"{os.environ['RDS_HOST']}:{os.environ['RDS_PORT']}/{os.environ['RDS_DB']}"
        )
        df.to_sql(os.environ['RDS_TABLE'], con=engine, if_exists='replace', index=False)
        print("✅ Data uploaded to RDS")
        return True
    except Exception as e:
        print(f"❌ Upload to RDS failed: {e}")
        return False

def fallback_to_glue():
    print("🔁 Fallback to Glue triggered...")
    glue = boto3.client('glue',
        aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
        region_name=os.environ['AWS_DEFAULT_REGION']
    )
    try:
        glue.create_database(DatabaseInput={'Name': os.environ['GLUE_DATABASE']})
    except glue.exceptions.AlreadyExistsException:
        pass
    try:
        glue.create_table(
            DatabaseName=os.environ['GLUE_DATABASE'],
            TableInput={
                'Name': os.environ['GLUE_TABLE'],
                'StorageDescriptor': {
                    'Columns': [
                        {'Name': 'id', 'Type': 'int'},
                        {'Name': 'name', 'Type': 'string'},
                    ],
                    'Location': os.environ['GLUE_S3_LOCATION'],
                    'InputFormat': 'org.apache.hadoop.mapred.TextInputFormat',
                    'OutputFormat': 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat',
                    'SerdeInfo': {
                        'SerializationLibrary': 'org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe',
                        'Parameters': {'field.delim': ','}
                    }
                },
                'TableType': 'EXTERNAL_TABLE'
            }
        )
        print("✅ Glue table created")
    except glue.exceptions.AlreadyExistsException:
        print("⚠️ Glue table already exists")

if __name__ == "__main__":
    df = read_csv_from_s3()
    success = upload_to_rds(df)
    if not success:
        fallback_to_glue()
🔹 Step 6: Create Dockerfile
dockerfile
Copy code
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
CMD ["python", "main.py"]
🔹 Step 7: Create requirements.txt
nginx
Copy code
boto3
pandas
sqlalchemy
pymysql
🔹 Step 8: Create .env File
env
Copy code
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_DEFAULT_REGION=ap-south-1

S3_BUCKET=my-data-bucket
CSV_KEY=data.csv

RDS_HOST=rds-endpoint.rds.amazonaws.com
RDS_PORT=3306
RDS_USER=admin
RDS_PASSWORD=yourpassword
RDS_DB=mydb
RDS_TABLE=students

GLUE_DATABASE=glue_fallback_db
GLUE_TABLE=students_glue
GLUE_S3_LOCATION=s3://my-data-bucket/
🔹 Step 9: Build Docker Image
bash
Copy code
docker build -t s3-rds-glue-app .
🔹 Step 10: Run the App
bash
Copy code
docker run --env-file .env s3-rds-glue-app
🔍 Output Scenarios
✅ Successful RDS upload:

css
Copy code
📥 Reading CSV from S3...
✅ CSV loaded
📤 Trying to upload data to RDS...
✅ Data uploaded to RDS
🔁 Fallback to Glue:

css
Copy code
📥 Reading CSV from S3...
✅ CSV loaded
📤 Trying to upload data to RDS...
❌ Upload to RDS failed
🔁 Fallback to Glue triggered...
✅ Glue table created
📝 Project Summary
This project shows a fault-tolerant data pipeline using AWS and Docker.
It reads data from S3, pushes it to RDS, and if that fails, falls back to AWS Glue.
All logic is packaged into a Dockerized Python app for easy deployment.

✅ Key Features
Automated data ingestion from S3 to RDS

Fallback to Glue if RDS fails

Secure access using IAM roles and access keys

Implemented using Python 3.9

Portable via Docker

📚 Learning Outcomes
Learn AWS service integration (S3, RDS, Glue, IAM, EC2)

Build a fault-tolerant data pipeline

Understand Docker + Python application structure

Apply DevOps + Data Engineering concepts

👨‍💻 Author
Rutik Nikam
🔗 LinkedIn Profile




