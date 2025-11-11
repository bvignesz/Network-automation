# Network Automation with Ansible

This repository contains Ansible playbooks for automating network device management and ServiceNow integration.

## Contents

### Playbooks
- `playbooks/fortigate_get_interfaces.yml` - Retrieve FortiGate interface information
- `playbooks/servicenow_connection_test.yml` - Test ServiceNow API connectivity

### Inventory
- `inventory/fortigate_hosts.yml` - FortiGate device inventory

## Requirements

Install required collections:
```bash
ansible-galaxy collection install -r requirements.yml
```

## Usage with Semaphore

1. Add this repository to Semaphore
2. Create Task Templates for each playbook
3. Configure survey variables for dynamic inputs

## Supported Devices
- FortiGate Firewalls (API token authentication)
- ServiceNow (ITSM integration)
- Zscaler ZPA/ZIA (future)

## Authentication
- FortiGate: API Token (System > Administrators > REST API Admin)
- ServiceNow: Username/Password or OAuth

## Author
Network Automation Team
