#!/usr/bin/env bash
set -euo pipefail

# ========================================
# AWS EC2 Deployment Script
# ========================================
# Prerequisites:
#   - AWS CLI installed and configured
#   - SSH key pair created in your region
# ========================================

REGION="us-east-1"
INSTANCE_TYPE="t3.xlarge"  # 4 vCPU, 16 GB RAM
AMI_ID="ami-0c7217cdde317cfec"  # Ubuntu 22.04 LTS in us-east-1
KEY_NAME="sql-lecture-key"
SECURITY_GROUP="sql-lecture-sg"
INSTANCE_NAME="sql-lecture-server"

echo "Creating Security Group..."
SG_ID=$(aws ec2 create-security-group \
    --group-name "$SECURITY_GROUP" \
    --description "SQL Lecture Assistant Security Group" \
    --query 'GroupId' \
    --output text \
    --region "$REGION")

echo "Opening ports..."
aws ec2 authorize-security-group-ingress \
    --group-id "$SG_ID" \
    --protocol tcp \
    --port 22 \
    --cidr 0.0.0.0/0 \
    --region "$REGION"

aws ec2 authorize-security-group-ingress \
    --group-id "$SG_ID" \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0 \
    --region "$REGION"

aws ec2 authorize-security-group-ingress \
    --group-id "$SG_ID" \
    --protocol tcp \
    --port 3000 \
    --cidr 0.0.0.0/0 \
    --region "$REGION"

aws ec2 authorize-security-group-ingress \
    --group-id "$SG_ID" \
    --protocol tcp \
    --port 8000 \
    --cidr 0.0.0.0/0 \
    --region "$REGION"

aws ec2 authorize-security-group-ingress \
    --group-id "$SG_ID" \
    --protocol tcp \
    --port 443 \
    --cidr 0.0.0.0/0 \
    --region "$REGION"

echo "Launching EC2 instance..."
INSTANCE_ID=$(aws ec2 run-instances \
    --image-id "$AMI_ID" \
    --instance-type "$INSTANCE_TYPE" \
    --key-name "$KEY_NAME" \
    --security-group-ids "$SG_ID" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$INSTANCE_NAME}]" \
    --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=50,VolumeType=gp3}' \
    --query 'Instances[0].InstanceId' \
    --output text \
    --region "$REGION")

echo "Waiting for instance to be running..."
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID" --region "$REGION"

PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids "$INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text \
    --region "$REGION")

echo ""
echo "========================================="
echo "EC2 Instance deployed!"
echo "  Instance ID: $INSTANCE_ID"
echo "  Public IP:   $PUBLIC_IP"
echo ""
echo "Deploy application:"
echo "  ssh -i ${KEY_NAME}.pem ubuntu@$PUBLIC_IP"
echo "  git clone <your-repo>"
echo "  cd sqlvideos_sample"
echo "  bash deploy/setup.sh"
echo "  docker-compose up -d"
echo "========================================="
