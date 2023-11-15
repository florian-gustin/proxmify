    ██████╗ ██████╗  ██████╗ ██╗  ██╗███╗   ███╗██╗███████╗██╗   ██╗
    ██╔══██╗██╔══██╗██╔═══██╗╚██╗██╔╝████╗ ████║██║██╔════╝╚██╗ ██╔╝
    ██████╔╝██████╔╝██║   ██║ ╚███╔╝ ██╔████╔██║██║█████╗   ╚████╔╝ 
    ██╔═══╝ ██╔══██╗██║   ██║ ██╔██╗ ██║╚██╔╝██║██║██╔══╝    ╚██╔╝  
    ██║     ██║  ██║╚██████╔╝██╔╝ ██╗██║ ╚═╝ ██║██║██║        ██║   
    ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝╚═╝╚═╝        ╚═╝   


[![PyPI version](https://img.shields.io/pypi/v/readmeai?color=blueviolet)](https://badge.fury.io/py/readmeai)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/readmeai.svg?color=blueviolet)](https://pypi.python.org/pypi/readmeai/)
![GitHub last commit](https://img.shields.io/github/last-commit/eli64s/readme-ai.svg?color=blueviolet)
![License: MIT](https://img.shields.io/github/license/eli64s/readme-ai?color=blueviolet)

---

## 🔗 Quick Links
* [Introduction](#introduction)
* [Prerequisites](#prerequisites)
* [Installation](#installation)
* [Running](#running)
* [Configuration and Workspace Files](#configuration-and-workspace-files)
    * [YAML Configuration File](#yaml-configuration-file)
    * [JSON Workspace File](#json-workspace-file)
        * [Cloud Init Virtual Machine Template](#cloud-init-virtual-machine-template)
        * [Cloud Init Virtual Machine](#cloud-init-virtual-machine)
        * [Virtual Machine](#virtual-machine)
        * [Container](#container)
    * [Explanation of Fields](#explanation-of-fields)
* [Script Output](#script-output)
* [Additional Notes](#additional-notes)
* [Disclaimer](#disclaimer)
* [License](#license)

---

# Introduction

This script is designed to automate the creation, modification, and deletion of containers and virtual machines on a Proxmox server using SSH. It reads configuration information from YAML and JSON files and executes the necessary commands on the Proxmox server.

---

# Prerequisites

Before using this script, ensure the following:

- Proxmox server is set up and accessible over SSH.
- Python and required libraries (paramiko, argparse, json, yaml, shlex) are installed.

---

# Installation

1. Clone the repository:

```bash
git clone https://github.com/florian-gustin/proxmify.git
```

2. Install the required Python libraries:

```bash
pip install paramiko
```
---

# Running

```bash
python script_name.py -c path/to/config.yaml -w path/to/workspace.json
```

- -c or --config: Path to the YAML configuration file.
- -w or --workspace: Path to the JSON workspace file.

---

# Configuration and Workspace Files

## YAML Configuration File

The YAML configuration file contains information about Proxmox servers and their connection details. An example structure is as follows:

```yaml
servers:
  server1:
    ip: "X.X.X.X"
    user: "your_user"
    port: 'your_port'
    password: "your_password"
    ssh_authorized_keys:
      - "your_ssh_key"
  server2:
    ip: "X.X.X.X"
    user: "your_user"
    port: 'your_port'
    password: "your_password"
    ssh_authorized_keys:
      - "your_ssh_key"
```

## JSON Workspace File

The JSON workspace file contains information about the containers or virtual machines to be created or modified. An example structure is as follows:

### Supported Operations

The script supports the following operations:

- Create Cloud Init Virtual Machine Template (type: "vm_ci_template")
- Create Virtual Machine with Cloud Init (type: "vm_ci")
- Create Virtual Machine (type: "vm")
- Create Container (type: "ct")

---

#### Cloud Init Virtual Machine Template

```json
[
  {
    "server": "server1",
    "type": "vm_ci_template",
    "image_path": "/mnt/pve/data-iso/template/cloud-init/AlmaLinux-8-GenericCloud-latest.x86_64.qcow2",
    "os_type": "l26",
    "id": 10000,
    "hostname": "alma8-ci-template",
    "sockets": 1,
    "cores": 2,
    "mem": 2048,
    "storage": "local-zfs",
    "storage_qty": 20,
    "bridge": "vmbr2"
  }
]
```

---


#### Cloud Init Virtual Machine

```json
[
  {
    "server": "server1",
    "type": "vm_ci",
    "initial_id": 10000,
    "id": 101,
    "hostname": "alma8-ci-vm",
    "sockets": 1,
    "cores": 2,
    "mem": 2048,
    "ipv4_cicdr": "192.168.9.2/24",
    "gateway": "192.168.9.254",
    "storage_qty": 25,
    "user": "admin",
    "password": "password",
    "use_ssh_keys": true
  }
]
```

---


#### Virtual Machine

```json
[
  {
    "server": "server1",
    "type": "vm",
    "image_path": "/mnt/pve/data-iso/template/iso/ubuntu-22.04.3-live-server-amd64.iso",
    "os_type": "l26",
    "id": 101,
    "hostname": "ubuntu-vm",
    "sockets": 1,
    "cores": 2,
    "mem": 512,
    "ipv4_cicdr": "192.168.9.2/24",
    "gateway": "192.168.9.254",
    "storage": "local-zfs",
    "storage_qty": 20,
    "bridge": "vmbr2"
  }
]
```

---

#### Container

```json
[
  {
    "server":  "server1",
    "type": "ct",
    "image_path": "/mnt/pve/data-iso/template/cache/ubuntu-22.04-standard_22.04-1_amd64.tar.zst",
    "os_type": "ubuntu",
    "init_cmd": "apt-get update -y",
    "id": 101,
    "hostname": "ubuntu-container",
    "cores": 2,
    "mem": 1024,
    "swap": 0,
    "ipv4_cicdr": "192.168.9.2/24",
    "gateway": "192.168.9.254",
    "storage": "local-zfs",
    "storage_qty": 25,
    "bridge": "vmbr2",
    "privileged": 1
  }
]
```

---

### Explanation of Fields

- server: Name of the Proxmox server.
- type: Type of operation (vm_ci_template, vm_ci, vm, ct).
- image_path: Path to the image or template.
- os_type: Operating system type.
- id: Identifier for the container or virtual machine.
- hostname: Hostname for the container or virtual machine.
- sockets: Number of CPU sockets.
- cores: Number of CPU cores.
- mem: Memory size in megabytes.
- swap: Swap size in megabytes.
- ipv4_cicdr: IPv4 address with CIDR notation.
- gateway: Gateway IP address.
- storage_qty: Storage quantity in gigabytes.
- bridge: Bridge for networking.
- privileged: Whether the container is privileged (1 for true, 0 for false).
- init_cmd: Initialization command for containers.
- user: Cloud-init user for virtual machines.
- password: Cloud-init password for virtual machines.
- use_ssh_keys: Whether to use SSH keys for virtual machines (true for true, false for false).

---

# Script Output

The script will output messages indicating the progress and status of each task. Successful tasks will be marked with a success message, and any errors will be displayed in red.

```bash
   ERROR : <error_message>
```

---

# Additional Notes

- The script uses ANSI color codes for a visually informative output.
- The provided SSH keys are stored in temporary files during the execution of the script.

---

# Disclaimer

Use this script responsibly and ensure that you have proper backups before making any changes to your Proxmox environment. The script comes with no warranty, and the user is responsible for any consequences of its usage.

---

# License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
