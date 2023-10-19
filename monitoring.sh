#!/usr/bin/bash
#
# Some basic monitoring functionality; Tested on Amazon Linux 2.
#

INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
MEMORYUSAGE=$(free -m | awk 'NR==2{printf "%.2f%%", $3*100/$2 }')
PROCESSES=$(expr $(ps -A | grep -c .) - 1)
HTTPD_PROCESSES=$(ps -A | grep -c httpd)
CPU_USAGE=$(mpstat 1 1 | awk '$12 ~ /[0-9.]+/ {print 100 - $12"%"}')
DISK_USAGE=$(df -h | awk '$NF=="/"{printf "%s", $5}') #DISK SPACE UTILIZATION
UPTIME=$(uptime -p) #INSTANCE RUNNING UPTIME
OS_INFO=$(cat /etc/os-release) #OS INFORMATION
KERNEL_VERSION=$(uname -r) #KERNEL INFORMATION


echo "Instance ID: $INSTANCE_ID"
echo "Memory utilisation: $MEMORYUSAGE"
echo "No of processes: $PROCESSES"
echo "CPU utilization: $CPU_USAGE"
echo "Disk utilization: $DISK_USAGE"
echo "System uptime: $UPTIME"
echo "Operating System: $OS_INFO"
echo "Kernel Version: $KERNEL_VERSION"


if [ $HTTPD_PROCESSES -ge 1 ]
then
    echo "Web server is running"
else
    echo "Web server is NOT running"
fi
