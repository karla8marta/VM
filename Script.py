# Import the needed credential and management objects from the libraries.
from azure.identity import AzureCliCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.compute import ComputeManagementClient
import os

print(f"Provisioning a virtual machine...some operations might take a minute or two.")

# Acquire a credential object using CLI-based authentication.
credential = AzureCliCredential()

# Retrieve subscription ID from environment variable.
subscription_id = "c6c1e493-a28f-4270-a753-8bb16319a722"


# Step 1: Provision a resource group

# Obtain the management object for resources, using the credentials from the CLI login.
resource_client = ResourceManagementClient(credential, subscription_id)

# Constants we need in multiple places: the resource group name and the region
# in which we provision resources. You can change these values however you want.
RESOURCE_GROUP_NAME = "New_group"
LOCATION = "uksouth"

# Provision the resource group.
rg_result = resource_client.resource_groups.create_or_update(RESOURCE_GROUP_NAME,
    {
        "location": LOCATION
    }
)


print(f"Provisioned resource group {rg_result.name} in the {rg_result.location} region")

# For details on the previous code, see Example: Provision a resource group
# at https://docs.microsoft.com/azure/developer/python/azure-sdk-example-resource-group


# Step 2: provision a virtual network

# A virtual machine requires a network interface client (NIC). A NIC requires
# a virtual network and subnet along with an IP address. Therefore we must provision
# these downstream components first, then provision the NIC, after which we
# can provision the VM.

# Network and IP address names
VNET_NAME = "New_group-vnet"
SUBNET_NAME = "New_group-subnet"
IP_NAME = "New_IP"
IP_CONFIG_NAME = "ipconfig1"
NIC_NAME = "New_group-nic"

# Obtain the management object for networks
network_client = NetworkManagementClient(credential, subscription_id)

# Provision the virtual network and wait for completion
poller = network_client.virtual_networks.begin_create_or_update(RESOURCE_GROUP_NAME,
    VNET_NAME,
    {
        "location": LOCATION,
        "address_space": {
            "address_prefixes": ["10.0.0.0/16"]
        }
    }
)

vnet_result = poller.result()

print(f"Provisioned virtual network {vnet_result.name} with address prefixes {vnet_result.address_space.address_prefixes}")

# Step 3: Provision the subnet and wait for completion
poller = network_client.subnets.begin_create_or_update(RESOURCE_GROUP_NAME, 
    VNET_NAME, SUBNET_NAME,
    { "address_prefix": "10.0.0.0/24" }
)
subnet_result = poller.result()

print(f"Provisioned virtual subnet {subnet_result.name} with address prefix {subnet_result.address_prefix}")

# Step 4: Provision an IP address and wait for completion
poller = network_client.public_ip_addresses.begin_create_or_update(RESOURCE_GROUP_NAME,
    IP_NAME,
    {
        "location": LOCATION,
        "sku": { "name": "Basic" },
        "public_ip_allocation_method": "Static",
        "public_ip_address_version" : "IPV4"
    }
)

ip_address_result = poller.result()

print(f"Provisioned public IP address {ip_address_result.name} with address {ip_address_result.ip_address}")

# Step 5: Provision the network interface client
poller = network_client.network_interfaces.begin_create_or_update(RESOURCE_GROUP_NAME,
    NIC_NAME, 
    {
        "location": LOCATION,
        "ip_configurations": [ {
            "name": IP_CONFIG_NAME,
            "subnet": { "id": subnet_result.id },
            "public_ip_address": {"id": ip_address_result.id }
        }]
    }
)

nic_result = poller.result()

print(f"Provisioned network interface client {nic_result.name}")

# Step 6: Provision the virtual machine

# Obtain the management object for virtual machines
compute_client = ComputeManagementClient(credential, subscription_id)

VM_NAME = "NewVM"
USERNAME = "martalozer"
KEY_PATH = "/home/" + USERNAME + "/.ssh/authorized_keys"
PUBLIC_KEY = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQDuytOSj8GCmtE0Xj7dJK5gFyJfakWUoEM8qBMQZpJXh86TPbw/aRvkaCtIJKLsQbqAFxNpt6jU0HuZeE6G+tG1Xql8kgL+XAMc4l8YBE2TfMRE1RTPV6KSQdhobaMERdvmOIUYXThoRJqiH6NI9HPwF/S/74r9AW/KnIEpP1PXOqpD9ig1zF1psvonwEKCwRIQ9o2TRBDKfvTlFGTzsiuoNbO/GyeXXsg4j3tX3Iogbsc+lGdhZw6S7wp5hQTe8aRpHRQ9XTh/WLMlRcbR78UOcPhRO3zeTp74agyv7fUWE4IPhfImLf+LVzCaOIQQAj2/V7OqASjWgCIunYltb5tEh0jfU2qZuXu4rU+J6zO23cz7nYANgU20BfVx8H4ZlANtaR5ECG/LDD4ivdiTd2l2KQXKymhHGr8hGgMMN3T4jxBNkYRSDVBTyoVJdN8AqMZWNZOpkcqdkRU8rDylFx0hVBnLZtERWOfeiBFan0x4KGR2djAcLUjAssTifpHvrys= martalozer@Karlas-MacBook-Air.local"


print(f"Provisioning virtual machine {VM_NAME}; this operation might take a few minutes.")

# Provision the VM specifying only minimal arguments, which defaults to an Ubuntu 18.04 VM
# on a Standard DS1 v2 plan with a public IP address and a default virtual network/subnet.

poller = compute_client.virtual_machines.begin_create_or_update(RESOURCE_GROUP_NAME, VM_NAME,
    {
        "location": LOCATION,
        "storage_profile": {
            "image_reference": {
                "publisher": 'Canonical',
                "offer": "UbuntuServer",
                "sku": "18.04-LTS",
                "version": "latest"
            }
        },
        "hardware_profile": {
            "vm_size": "Standard_DS1_v2"
        },
        "os_profile": {
            "computer_name": VM_NAME,
            "admin_username": USERNAME,
            "secrets": [
                ],
            "linuxConfiguration": {
                "ssh": {
                    "publicKeys": [
                        {
                            "path": KEY_PATH,
                            "keyData": PUBLIC_KEY
                        }
                    ]
                },
                "disablePasswordAuthentication": True
            }
        },
        "network_profile": {
            "network_interfaces": [{
                "id": nic_result.id,
            }]
        }        
    }
)

vm_result = poller.result()

print(f"Provisioned virtual machine {vm_result.name}")