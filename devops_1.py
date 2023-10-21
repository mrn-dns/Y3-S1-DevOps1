#-----------------START OF SCRIPT----------------
import boto3
import json
import webbrowser
import requests
import uuid
import subprocess
import time
import logging

log_file = 'monitoring.log' #https://docs.python.org/3/howto/logging.html
logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(message)s')


keyName='key12' # Added global key variable to ease script use


random_string = str(uuid.uuid4()).split('-')[0][:6] # Generate a random string


bucket_name = f'{random_string}-dmarincas' # Construct the bucket name with the random string

#Specify image link
logo = requests.get('http://devops.witdemo.net/logo.jpg')

website_configuration = {
    'ErrorDocument': {'Key': 'error.html'}, #Adding error document to website configuration
    'IndexDocument': {'Suffix': 'index.html'}, #Adding index document to website configuration
}

#----------------USER DATA SCRIPT-----------------
user_data_script = """#!/bin/bash
yum update -y
yum install httpd -y
yum install -y mariadb-server
yum install php -y
sudo yum install php php-mysqli -y

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
cp monitoring.html /var/www/html/monitoring.html

# Create a cron job for the monitoring script
echo '* * * * * /bin/bash monitoring.sh' | crontab -

systemctl enable mariadb 
systemctl start mariadb

sudo mysql -e "CREATE DATABASE IF NOT EXISTS InstanceDB"
sudo mysql -e "CREATE USER 'ec2'@'localhost' IDENTIFIED BY 'secret'"
sudo mysql -e "GRANT ALL PRIVILEGES ON InstanceDB.* TO 'ec2'@'localhost*"
sudo mysql -e "USE InstanceDB";

CREATE TABLE IF NOT EXISTS users ( 
	id INT AUTO_INCREMENT PRIMARY KEY,
	name VARCHAR (255), 
	age INT
);

INSERT INTO users (name, age) VALUES
	('John Doe', 30),
	('Mikey Mike',25),
	('Johnny Joe',55);


# Start the cron service
systemctl start crond
systemctl enable crond
"""
#-----------END OF USER DATA SCRIPT----------------


#Get Index and Logo local paths for bucket
index_page = 'index.html'
local_image_path = 'logo.jpg'

#-----DOWNLOADING IMAGE------
response = requests.get(f'http://devops.witdemo.net/logo.jpg')
if response.status_code == 200: #200 code represents a working link
    with open(local_image_path, 'wb') as image_file:
        image_file.write(response.content)
        logging.info("Image downloaded.")
else:
    print(f"Failed to download the image. Status code: {response.status_code}")
    logging.info("Image failed to download.")
#-----DOWNLOADING IMAGE------

#--------------Creating EC2 instance-----------------
try:
    ec2 = boto3.resource('ec2')

    instance = ec2.create_instances(
    ImageId='ami-03eb6185d756497f8',
    InstanceType='t2.nano',
    MinCount=1,
    MaxCount=1,
    KeyName=keyName,
    SecurityGroups=['devops'],
    UserData=user_data_script
    )

    instance_id = instance[0].id
    ec2.create_tags(Resources=[instance_id], Tags=[{'Key': 'Web server', 'Value': 'AssignmentInstance'}]) #Adding tag
    
    instance[0].wait_until_running() #Wait for the instance to be up and running
    instance[0].reload() #Reload the instance to ensure it reflects the current state
    instance_ip = instance[0].public_ip_address
    

    print(f"Instance {instance_id} is now running.") #Prints the instance state - RUNNING
    print(f"Instance public ip is: {instance_ip}") #Prints the instance IPV4 address
    logging.info("Instance is up and running.") #logging instance state - RUNNING
    logging.info(f"Instance public ip is: {instance_ip}") #logging instance IPV4 address
    
except Exception as e:
    print(f"An error occurred while creating the EC2 instance: {e}")
    logging.info("Error occured while launching instance.")
    
#-----------End of creating EC2 Instance-------------


#-----------Creating a S3 Bucket-------------
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
    
#-----------End of Creating a S3 Bucket-------------


#----------Creating URLs and storing them to a file called dmarincas_websites.txt----------
s3_website_url = f'http://{bucket_name}.s3-website-us-east-1.amazonaws.com' #S3 WEBSITE URL
logging.info(f"S3 Bucket Website is: http://{bucket_name}.s3-website-us-east-1.amazonaws.com")


ec2_website_url = f'http://{instance_ip}' #EC2 WEBSITE URL
logging.info(f"EC2 Instance Website is : http://{instance_ip}")


websites = [s3_website_url, ec2_website_url] # Storing URLs to a list

#--------------Created URLs and stored them at dmarincas_websites.txt---------------------
with open('dmarincas-websites.txt', 'w') as file:
    for website in websites:
        file.write(website + '\n')
#--------------Created URLs and stored them at dmarincas_websites.txt---------------------

try:
	webbrowser.open_new_tab(s3_website_url) #Opening the S3 website
	webbrowser.open_new_tab(ec2_website_url) #Opening the EC2 website
except Exception as e:
	print(e)

#------------SSH connection and running the monitoring script---------------
try:
	subprocess.run("chmod 400 " + str(keyName) + ".pem", shell=True)
	subprocess.run("scp -i " + str(keyName) + ".pem" + " -o StrictHostKeyChecking=no monitoring.sh ec2-user@" +
	str(instance[0].public_ip_address) + ":." , shell=True)
	print("Waiting for instance initialization")
	logging.info("Waiting for instance initialization")
	time.sleep(80)
	print("scp check")
	logging.info("scp check")
	subprocess.run("ssh -i "+ str(keyName) + ".pem" + " ec2-user@" + str(instance[0].public_ip_address) + " 'chmod 700 monitoring.sh'", shell = True)
	print("ssh check")
	logging.info("ssh check")
	subprocess.run("ssh -i " + str(keyName) + ".pem" + " ec2-user@" + str(instance[0].public_ip_address) + " ' ./monitoring.sh'", shell = True)
	logging.info("Monitoring script is active.")
	subprocess.run("ssh -i " + str(keyName) + ".pem" + " ec2-user@" + str(instance[0].public_ip_address) + " echo '* * * * * uptime >> ~/instance_uptime.log' | crontab -", shell=True)
except Exception as e:
	print(e)
#------------SSH connection and running the monitoring script---------------
	
	
#----------END OF SCRIPT----------
