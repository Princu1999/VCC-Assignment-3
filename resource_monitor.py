import psutil
import time
from google.cloud import compute_v1
from google.protobuf.json_format import MessageToDict
#from googleapiclient import discovery
from google.oauth2 import service_account


UPPER_THRESHOLD = 75  # percent: When exceeded, create remote VM
LOWER_THRESHOLD = 60  # percent: When all metrics fall below, delete remote VM
PROJECT_ID = "handy-cathode-452406-f1" 
ZONE = "asia-south2-c"
INSTANCE_NAME = "processing-instance"

DOCKER_IMAGE = "princu999/image-processing-service:latest"

instance_client = compute_v1.InstancesClient()

def instance_exists():
    """Returns True if the remote VM instance exists."""
    try:
        instance_client.get(project=PROJECT_ID, zone=ZONE, instance=INSTANCE_NAME)
        return True
    except Exception:
        return False

def create_gcp_vm():
    """
    Creates the GCP VM instance using Container-Optimized OS (COS),
    with a startup script that runs your Docker container.
    Returns the external IP of the new VM.
    """
    print("High load detected. Creating GCP VM instance with COS...")

    # COS already has Docker installed. The startup script pulls and runs your container.
    startup_script = f"""#!/bin/bash
docker run -d -p 5000:5000 {DOCKER_IMAGE}
"""

    # Build the metadata items with the startup script
    metadata_items = [
        compute_v1.types.Items(key="startup-script", value=startup_script)
    ]
    
    access_config = compute_v1.AccessConfig(
    	name="External NAT",
    	type_="ONE_TO_ONE_NAT"
    )
    network_interface= compute_v1.NetworkInterface(
        name="nic0" , 
        access_configs=[access_config]
   )
   
    instance = compute_v1.Instance(
        name=INSTANCE_NAME,
        machine_type=f"zones/{ZONE}/machineTypes/e2-medium",
        disks=[
            {
                "initialize_params": {
                    # Use Container-Optimized OS image
                    "source_image": "projects/cos-cloud/global/images/family/cos-stable"
                },
                "boot": True,
                "auto_delete": True,
            }
        ],
        network_interfaces=  [network_interface],
       
        metadata=compute_v1.Metadata(items=metadata_items),
    )

    operation = instance_client.insert(
        project=PROJECT_ID,
        zone=ZONE,
        instance_resource=instance
    )

    print("Instance creation triggered. Waiting for VM to be ready...")
    # Wait for the VM to boot and the container to start.
    time.sleep(60)
   
    # No need to create the firewall rule here since it was created manually.
    return get_external_ip()

def delete_gcp_vm():
    """Deletes the GCP VM instance."""
    print("Resource usage is normal. Deleting the GCP VM instance...")
    operation = instance_client.delete(
        project=PROJECT_ID,
        zone=ZONE,
        instance=INSTANCE_NAME
    )
    print("Instance deletion triggered.")


def get_external_ip():
    try:
        # Build the Compute Engine API client using application default credentials.
        service = discovery.build('compute', 'v1')
        result = service.instances().get(
            project=PROJECT_ID, zone=ZONE, instance=INSTANCE_NAME).execute()
        # The external IP is in networkInterfaces[0]['accessConfigs'][0]['natIP']
        for iface in result.get("networkInterfaces", []):
            for ac in iface.get("accessConfigs", []):
                ip = ac.get("natIP")
                if ip:
                    return ip
    except Exception as e:
        print("Error retrieving external IP:", e)

def check_resources():
    """Check CPU, RAM, and Disk usage and return their values."""
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    print(f"Resource Usage => CPU: {cpu}%, RAM: {ram}%, Disk: {disk}%")
    return cpu, ram, disk

def scaling_controller():
    """
    Checks resource usage and creates or deletes the remote VM based on thresholds.
    Returns the remote VM's external IP if it exists; otherwise, None.
    """
    cpu, ram, disk = check_resources()
    remote_ip = None

    if cpu > UPPER_THRESHOLD or ram > UPPER_THRESHOLD or disk > UPPER_THRESHOLD:
        if not instance_exists():
            remote_ip = create_gcp_vm()
        else:
            remote_ip = get_external_ip()
    elif cpu < LOWER_THRESHOLD and ram < LOWER_THRESHOLD and disk < LOWER_THRESHOLD:
        if instance_exists():
            delete_gcp_vm()
    return remote_ip

if __name__ == '__main__':
    while True:
        remote_ip = scaling_controller()
        time.sleep(10)


