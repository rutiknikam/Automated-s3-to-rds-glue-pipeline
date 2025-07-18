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
        glue.create_database(
            DatabaseInput={'Name': os.environ['GLUE_DATABASE']}
        )
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

