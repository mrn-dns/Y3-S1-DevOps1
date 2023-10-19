import boto3
import json
import webbrowser
import requests
import uuid
import subprocess
import time
import logging

#https://docs.python.org/3/howto/logging.html
log_file = 'monitoring.log'
logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(message)s')

# Generate a random string
random_string = str(uuid.uuid4()).split('-')[0][:6]

# Construct the bucket name with the random string
bucket_name = f'{random_string}-dmarincas'

#Specify image link
logo = requests.get('http://devops.witdemo.net/logo.jpg')

website_configuration = {
    'ErrorDocument': {'Key': 'error.html'},
    'IndexDocument': {'Suffix': 'index.html'},
}


user_data_script = """#!/bin/bash
yum update -y
yum install httpd -y
systemctl enable httpd
systemctl start httpd
cd /var/www/html
echo '<html>' > index.html
echo '<a href="index.html">Home</a> | <a href="monitoring.html">Monitoring Stats</a><br><br>' >> index.html
echo '<ul>' >> index.html
echo '<li>Private IP address: ' >> index.html
curl http://169.254.169.254/latest/meta-data/local-ipv4 >> index.html
echo '</li>' >> index.html
echo '<li>Instance AMI: ' >> index.html
curl -s http://169.254.169.254/latest/meta-data/ami-id >> index.html
echo '</li>' >> index.html
echo '<li>Availability Zone: ' >> index.html
curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone >> index.html
echo '</li>' >> index.html
echo '<li>Instance ID: ' >> index.html
curl -s http://169.254.169.254/latest/meta-data/instance-id >> index.html
echo '</li>' >> index.html
echo '<li>Instance Type: ' >> index.html
curl -s http://169.254.169.254/latest/meta-data/instance-type >> index.html
echo '</li>' >> index.html
echo '</ul>' >> index.html
cp index.html /var/www/html/index.html
# Add monitoring information to monitoring.html
echo '<html>' > monitoring.html
echo '<a href="index.html">Home</a> | <a href="monitoring.html">Monitoring Stats</a><br><br>' >> monitoring.html
echo '<ul>' >> monitoring.html
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
MEMORYUSAGE=$(free -m | awk 'NR==2{printf "%.2f%%", $3*100/$2 }')
PROCESSES=$(expr $(ps -A | grep -c .) - 1)
HTTPD_PROCESSES=$(ps -A | grep -c httpd)
UPTIME=$(uptime -p) #EXTRA FUNCTIONALITY
OS_INFO=$(cat /etc/os-release) #OS INFORMATION
KERNEL_VERSION=$(uname -r) #KERNEL INFORMATION
echo '<li>Instance ID: ' $INSTANCE_ID '</li>' >> monitoring.html
echo '<li>Memory utilization: ' $MEMORYUSAGE '</li>' >> monitoring.html
echo '<li>Number of processes: ' $PROCESSES '</li>' >> monitoring.html
echo '<li>System uptime: ' $UPTIME '</li>' >> monitoring.html
echo '<li>OS information: ' $OS_INFO '</li>' >> monitoring.html
echo '<li>Kernel information: ' $KERNEL_VERSION '</li>' >> monitoring.html
if [ $HTTPD_PROCESSES -ge 1 ]
then
    echo '<li>Web server is running</li>' >> monitoring.html
else
    echo '<li>Web server is NOT running</li>' >> monitoring.html
fi
echo '</ul>' >> monitoring.html
cp monitoring.html /var/www/html/monitoring.html"""



#Get Index and Logo local paths for bucket
index_page = 'index.html'
local_image_path = 'logo.jpg'

#Updating logo.jpg
response = requests.get(f'http://devops.witdemo.net/logo.jpg')
if response.status_code == 200:
    with open(local_image_path, 'wb') as image_file:
        image_file.write(response.content)
        logging.info("Image downloaded.")
else:
    print(f"Failed to download the image. Status code: {response.status_code}")
    logging.info("Image failed to download.")

#Create EC2 instance
try:
    ec2 = boto3.resource('ec2')

    instance = ec2.create_instances(
    ImageId='ami-0bb4c991fa89d4b9b',
    InstanceType='t2.nano',
    MinCount=1,
    MaxCount=1,
    KeyName='key12',
    SecurityGroups=['devops'],
    UserData=user_data_script
    )

    instance_id = instance[0].id
    ec2.create_tags(Resources=[instance_id], Tags=[{'Key': 'Web server', 'Value': 'AssignmentInstance'}])
    
    instance[0].wait_until_running()
    instance[0].reload()
    instance_ip = instance[0].public_ip_address
    print(f"Instance {instance_id} is now running.")
    print(f"Instance public ip is: {instance_ip}")
    logging.info("Instance is up and running.")
    logging.info(f"Instance public ip is: {instance_ip}")
except Exception as e:
    print(f"An error occurred while creating the EC2 instance: {e}")
    logging.info("Error occured while launching instance.")

#Creating a bucket
try:
    s3 = boto3.resource("s3")
    response = s3.create_bucket(Bucket=bucket_name)
    s3client = boto3.client("s3")
    s3client.delete_public_access_block(Bucket=bucket_name)

    bucket_policy = {
     "Version": "2012-10-17",
     "Statement": [
    {
     "Sid": "PublicReadGetObject",
    "Effect": "Allow",
    "Principal": "*",
    "Action": ["s3:GetObject"],
    "Resource": f"arn:aws:s3:::{bucket_name}/*"
    }
    ]
    }     
    #Setting Bucket Policy                                       
    s3.Bucket(bucket_name).Policy().put(Policy=json.dumps(bucket_policy))
    #Setting Website Configuration
    bucket_website = s3.BucketWebsite(f'{bucket_name}')
    bucket_website.put(WebsiteConfiguration=website_configuration)
    logging.info("Bucket is online.") 
    #Add index.html and logo.jpg to Bucket
    s3.Object(bucket_name, index_page).put(Body=open(index_page, 'rb'), ContentType = 'text/html')
    logging.info("Added HTML file to bucket.")
    s3.Object(bucket_name, 'logo.jpg').put(Body=open(local_image_path, 'rb'), ContentType = 'image/jpg')
    logging.info("Added image file to bucket.")
    print (f"S3 Bucket Name: {bucket_name}")
    logging.info(f"S3 Bucket Name: {bucket_name}")
except Exception as error:
    print (error)

# Update the link with the new bucket name
s3_website_url = f'http://{bucket_name}.s3-website-us-east-1.amazonaws.com'
logging.info(f"S3 Bucket Website is: http://{bucket_name}.s3-website-us-east-1.amazonaws.com")
# Get instance URL using instance public IPV4 address
ec2_website_url = f'http://{instance_ip}'
logging.info(f"EC2 Instance Website is : http://{instance_ip}")

#Opening the web browser tabs
webbrowser.open_new_tab(s3_website_url)
webbrowser.open_new_tab(ec2_website_url)

#SSH connection and running the monitoring script
try:
	subprocess.run("chmod 400 key12.pem", shell=True)
	subprocess.run("scp -i key12.pem -o StrictHostKeyChecking=no monitoring.sh ec2-user@" +
	str(instance[0].public_ip_address) + ":." , shell=True)
	print("Waiting for instance initialization")
	logging.info("Waiting for instance initialization")
	time.sleep(80)
	print("scp check")
	logging.info("scp check")
	subprocess.run("ssh -i key12.pem -o StrictHostKeyChecking=no ec2-user@" + str(instance[0].public_ip_address) + " 'chmod 700 monitoring.sh'", shell = True)
	print("ssh check")
	logging.info("ssh check")
	subprocess.run("ssh -i key12.pem -o StrictHostKeyChecking=no ec2-user@" + str(instance[0].public_ip_address) + " ' ./monitoring.sh'", shell = True)
	logging.info("Monitoring script is active.")
except Exception as e:
	print(e)
