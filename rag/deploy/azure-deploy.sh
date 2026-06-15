#!/usr/bin/env bash
set -euo pipefail

# ========================================
# Azure VM Deployment Script
# ========================================
# Prerequisites:
#   - Azure CLI installed and logged in
#   - SSH key pair generated
# ========================================

RESOURCE_GROUP="sql-lecture-rg"
LOCATION="eastus"
VM_NAME="sql-lecture-vm"
VM_SIZE="Standard_D4s_v3"  # 4 vCPU, 16 GB RAM
ADMIN_USER="azureuser"

echo "Creating Resource Group..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION"

echo "Creating VM..."
az vm create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$VM_NAME" \
    --image Ubuntu2204 \
    --size "$VM_SIZE" \
    --admin-username "$ADMIN_USER" \
    --generate-ssh-keys \
    --public-ip-sku Standard

echo "Opening ports..."
az vm open-port --resource-group "$RESOURCE_GROUP" --name "$VM_NAME" --port 80 --priority 100
az vm open-port --resource-group "$RESOURCE_GROUP" --name "$VM_NAME" --port 3000 --priority 101
az vm open-port --resource-group "$RESOURCE_GROUP" --name "$VM_NAME" --port 8000 --priority 102
az vm open-port --resource-group "$RESOURCE_GROUP" --name "$VM_NAME" --port 443 --priority 103

echo "Getting VM IP..."
IP=$(az vm show -d -g "$RESOURCE_GROUP" -n "$VM_NAME" --query publicIps -o tsv)
echo "VM IP: $IP"

echo ""
echo "========================================="
echo "Azure VM deployed at: $IP"
echo ""
echo "Deploy application:"
echo "  ssh $ADMIN_USER@$IP"
echo "  git clone <your-repo>"
echo "  cd sqlvideos_sample"
echo "  bash deploy/setup.sh"
echo "  docker-compose up -d"
echo "========================================="
