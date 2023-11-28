import time

import paramiko
import argparse
import json
import yaml
import shlex

# Codes ANSI d'échappement de couleur
RESET = "\033[0m"  # Réinitialiser les styles
RED = "\033[91m"  # Texte rouge
GREEN = "\033[92m"  # Texte vert
BLUE = "\033[94m"  # Texte bleu
GREY = "\033[90m"  # Texte en gris
BLACK = "\033[30m"  # Texte en noir
WHITE = "\033[97m"  # Texte en blanc
AMBER = "\033[38;2;255;191;0m"  # Texte en ambre
BOLD = "\033[1m"  # Texte en gras


def parse_args():
    """
    parse the arguments
    :return:
    """
    parser = argparse.ArgumentParser(description='Your script description here')

    parser.add_argument('-c', '--config', required=True, help='Path to the YAML configuration file')
    parser.add_argument('-w', '--workspace', required=True, help='Path to the JSON workspace file')

    args = parser.parse_args()
    return args


def load_yaml_config(yaml_file):
    """
    load the yaml config file
    :param yaml_file:
    :return:
    """
    with open(yaml_file, 'r') as file:
        config = yaml.safe_load(file)
    return config


def load_json_workspace(json_file):
    """
    load the json workspace file
    :param json_file:
    :return:
    """
    with open(json_file, 'r') as file:
        workspace = json.load(file)
    return workspace


def print_error(msg):
    """
    print an error message
    :param msg:
    :return:
    """
    print(f"   {RED}ERROR : {msg}{RESET}")


def print_success():
    """
    print a success message
    :return:
    """
    print(f"   {GREEN}Task succeeded{RESET}\n")


def has_error(stderr):
    """
    check if there is an error
    :param stderr:
    :return:
    """
    return len(stderr.read().decode()) > 0


def ssh_connect(config):
    """
    connect to the proxmox server by ssh
    :param config:
    :return:
    """
    ssh_client = paramiko.SSHClient()
    print(f"{BOLD}{AMBER}----- >  [TASK] - Connecting by SSH to the Proxmox server ip : {config['ip']}{RESET}\n")

    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(hostname=config["ip"], port=config["port"], username=config["user"],
                       password=config["password"])
    print_success()
    return ssh_client


def process_stop(ssh_client, meta, password):
    """"
    stop the old process if exists
    :param ssh_client:
    :param meta:
    :param password:
    """
    error = False

    print(f"{BOLD}{AMBER}----- >  [TASK] - Stopping existing process id : {meta['id']}{RESET}\n")

    cmd_pct_stop = f"sudo -S /usr/sbin/pct stop {meta['id']}"
    error = sudo_cmd(cmd_pct_stop, error, password, ssh_client)

    cmd_qm_stop = f"sudo -S /usr/sbin/qm stop {meta['id']}"
    error = sudo_cmd(cmd_qm_stop, error, password, ssh_client)

    ssh_client.exec_command(f"sleep 3")

    if error is not True:
        print_success()


def process_destroy(ssh_client, meta, password):
    """"
    delete the old process if exists
    :param ssh_client:
    :param meta:
    :param password:
    """
    error = False

    print(f"{BOLD}{AMBER}----- >  [TASK] - Deleting existing process id : {meta['id']}{RESET}\n")

    cmd1 = f"sudo -S /usr/sbin/pct destroy {meta['id']}"
    error = sudo_cmd(cmd1, error, password, ssh_client)

    cmd2 = f"sudo -S /usr/sbin/qm destroy {meta['id']}"
    error = sudo_cmd(cmd2, error, password, ssh_client)

    if error is not True:
        print_success()


def process_create_container(ssh_client, meta, config, password):
    """
    create a new container
    :param ssh_client:
    :param meta:
    :param config:
    :param password:
    :return:
    """
    error = False

    print(f"{BOLD}{AMBER}----- >  [TASK] - Creating container process id : {meta['id']}{RESET}\n")
    cmd_ssh_tmp = "echo '' > /tmp/ssh_temp_file"
    error = sudo_cmd(cmd_ssh_tmp, error, password, ssh_client)

    for key in config['ssh_authorized_keys']:
        tmp = f"echo {key} >> /tmp/ssh_temp_file"
        error = sudo_cmd(tmp, error, password, ssh_client)

    complex_cmd = prepare_complex_command([
        "sudo",
        "-S",
        "/usr/sbin/pct",
        "create",
        str(meta['id']),
        str(meta['image_path']),
        "--cores", str(meta['cores']),
        "--hostname", str(meta['hostname']),
        "--memory", str(meta['mem']),
        "--swap", str(meta['swap']),
        "--net0",
        f"name=eth0,bridge={meta['bridge']},firewall=1,gw={meta['gateway']},ip={meta['ipv4_cicdr']},type=veth",
        "--storage", str(meta['storage']),
        "--rootfs", f"{meta['storage']}:{meta['storage_qty']}",
        "--unprivileged", str(meta['privileged']),
        "--features", "keyctl=1,nesting=1,fuse=1",
        "--ostype", str(meta['os_type']),
        "--password", str(password),
        "--start", "1",
        "--onboot", "1",
        "--ssh-public-keys", "/tmp/ssh_temp_file"
    ])
    error = sudo_cmd(complex_cmd, error, password, ssh_client)

    cmd_rm = "rm /tmp/ssh_temp_file"
    ssh_client.exec_command(cmd_rm)

    cmd1 = f"echo 'lxc.cgroup2.devices.allow: c 10:200 rwm' | sudo tee -a /etc/pve/lxc/{meta['id']}.conf"
    error = sudo_cmd(cmd1, error, password, ssh_client)

    cmd2 = f"echo 'lxc.mount.entry: /dev/net/tun dev/net/tun none bind,create=file' | sudo tee -a /etc/pve/lxc/{meta['id']}.conf"
    error = sudo_cmd(cmd2, error, password, ssh_client)

    ssh_client.exec_command("rm /tmp/temp_file")

    cmd3 = f"sudo -S /usr/sbin/pct exec {meta['id']} -- bash -c '{meta['init_cmd']}'"
    error = sudo_cmd(cmd3, error, password, ssh_client)

    if error is not True:
        print_success()


def process_create_vm(ssh_client, meta, password):
    """
    create a new virtual machine
    :param ssh_client:
    :param meta:
    :param password:
    :return:
    """
    error = False

    print(f"{BOLD}{AMBER}----- >  [TASK] - Creating virtual machine process id : {meta['id']}{RESET}\n")
    complex_cmd = prepare_complex_command([
        "sudo",
        "-S",
        "/usr/sbin/qm",
        "create",
        str(meta['id']),
        "--name", str(meta['hostname']),
        "--memory", str(meta['mem']),
        "--sockets", str(meta['sockets']),
        "--cores", str(meta['cores']),
        "--net0", f"virtio,bridge={meta['bridge']}",
        "--virtio0", f"{meta['storage']}:{meta['storage_qty']},cache=writeback",
        "--ostype", str(meta['os_type']),
        "--ide0", f"{meta['image_path']},media=cdrom",
        "--bootdisk", "virtio0",
        "--onboot", "1",
    ])
    error = sudo_cmd(complex_cmd, error, password, ssh_client)

    cmd1 = f"sudo -S /usr/sbin/qm start {meta['id']}"
    error = sudo_cmd(cmd1, error, password, ssh_client)

    if error is not True:
        print_success()


def process_create_vm_ci(ssh_client, meta, config, password):
    """
    create a new virtual machine with cloud init
    :param ssh_client:
    :param meta:
    :param config:
    :param password:
    :return:
    """
    error = False
    print(f"{BOLD}{AMBER}----- >  [TASK] - Creating cloud init virtual machine process id : {meta['id']}{RESET}\n")

    cmd_clone = f"sudo -S /usr/sbin/qm clone {meta['initial_id']} {meta['id']} --name {meta['hostname']}"
    error = sudo_cmd(cmd_clone, error, password, ssh_client)

    cmd_create = prepare_complex_command([
        "sudo",
        "-S",
        "/usr/sbin/qm",
        "set",
        str(meta['id']),
        "--memory", str(meta['mem']),
        "--sockets", str(meta['sockets']),
        "--cores", str(meta['cores']),
        "--ipconfig0", f"ip={meta['ipv4_cicdr']},gw={meta['gateway']}",
    ])
    error = sudo_cmd(cmd_create, error, password, ssh_client)

    cmd_storage_qty = f"sudo -S /usr/sbin/qm resize {meta['id']} scsi0 {meta['storage_qty']}G"
    error = sudo_cmd(cmd_storage_qty, error, password, ssh_client)

    # if user is specified
    if 'user' in meta and meta['user'] is not None and meta['user'] != "":
        cmd_user = f"sudo -S /usr/sbin/qm set {meta['id']} --ciuser {meta['user']}"
        error = sudo_cmd(cmd_user, error, password, ssh_client)

    if 'user' in meta and meta['user'] == "":
        cmd_user = f"sudo -S sed -i '/^ciuser:/d' /etc/pve/qemu-server/104.conf"
        error = sudo_cmd(cmd_user, error, password, ssh_client)

    # if password is specified
    if 'password' in meta and meta['password'] is not None and meta['password'] != "":
        cmd_password = f"sudo -S /usr/sbin/qm set {meta['id']} --cipassword {meta['password']}"
        error = sudo_cmd(cmd_password, error, password, ssh_client)

    if 'password' in meta and meta['password'] == "":
        cmd_password = f"sudo -S sed -i '/^cipassword:/d' /etc/pve/qemu-server/104.conf"
        error = sudo_cmd(cmd_password, error, password, ssh_client)

    if 'use_ssh_keys' in meta and meta['use_ssh_keys'] and meta['use_ssh_keys'] != "" and True:
        cmd_ssh_file = "echo '' > /tmp/ssh_temp_file"
        error = sudo_cmd(cmd_ssh_file, error, password, ssh_client)

        for key in config['ssh_authorized_keys']:
            tmp = f"echo {key} >> /tmp/ssh_temp_file"
            error = sudo_cmd(tmp, error, password, ssh_client)

        cmd_ssh_keys = f"sudo -S /usr/sbin/qm set {meta['id']} --sshkey /tmp/ssh_temp_file"
        error = sudo_cmd(cmd_ssh_keys, error, password, ssh_client)

        cmd_rm = "rm /tmp/ssh_temp_file"
        ssh_client.exec_command(cmd_rm)

    if 'use_ssh_keys' in meta and meta['use_ssh_keys'] == "":
        cmd_ssh_file = "echo '' > /tmp/ssh_temp_file"
        error = sudo_cmd(cmd_ssh_file, error, password, ssh_client)

        cmd_ssh_keys = f"sudo -S /usr/sbin/qm set {meta['id']} --sshkey /tmp/ssh_temp_file"
        error = sudo_cmd(cmd_ssh_keys, error, password, ssh_client)

        cmd_rm = "rm /tmp/ssh_temp_file"
        ssh_client.exec_command(cmd_rm)

    cmd_start = f"sudo -S /usr/sbin/qm start {meta['id']}"
    error = sudo_cmd(cmd_start, error, password, ssh_client)

    if error is not True:
        print_success()


def process_create_vm_ci_template(ssh_client, meta, config, password):
    """
    create a new cloud init virtual machine template
    :param config:
    :param ssh_client:
    :param meta:
    :param password:
    :return:
    """
    error = False
    print(
        f"{BOLD}{AMBER}----- >  [TASK] - Creating cloud init virtual machine template process id : {meta['id']}{RESET}\n")

    cmd_create = prepare_complex_command([
        "sudo",
        "-S",
        "/usr/sbin/qm",
        "create",
        str(meta['id']),
        "--name", str(meta['hostname']),
        "--memory", str(meta['mem']),
        "--sockets", str(meta['sockets']),
        "--cores", str(meta['cores']),
        "--net0", f"virtio,bridge={meta['bridge']}",
    ])
    error = sudo_cmd(cmd_create, error, password, ssh_client)

    cmd_cloudinit = f"sudo -S /usr/sbin/qm importdisk {meta['id']} {meta['image_path']} {meta['storage']}"
    error = sudo_cmd(cmd_cloudinit, error, password, ssh_client)

    cmd_update = prepare_complex_command([
        "sudo",
        "-S",
        "/usr/sbin/qm",
        "set",
        str(meta['id']),
        "--scsihw", "virtio-scsi-pci",
        "--scsi0", f"{meta['storage']}:vm-{meta['id']}-disk-0",
        "--ide2", f"{meta['storage']}:cloudinit",
        "--boot", "c", "--bootdisk", "scsi0",
        "--serial0", "socket", "--vga", "serial0",
    ])
    error = sudo_cmd(cmd_update, error, password, ssh_client)

    cmd_storage_qty = f"sudo -S /usr/sbin/qm resize {meta['id']} scsi0 {meta['storage_qty']}G"
    error = sudo_cmd(cmd_storage_qty, error, password, ssh_client)

    # if user is specified
    if 'user' in meta and meta['user'] is not None and meta['user'] != "":
        cmd_user = f"sudo -S /usr/sbin/qm set {meta['id']} --ciuser {meta['user']}"
        error = sudo_cmd(cmd_user, error, password, ssh_client)

    # if password is specified
    if 'password' in meta and meta['password'] is not None and meta['password'] != "":
        cmd_password = f"sudo -S /usr/sbin/qm set {meta['id']} --cipassword {meta['password']}"
        error = sudo_cmd(cmd_password, error, password, ssh_client)

    if 'use_ssh_keys' in meta and meta['use_ssh_keys'] and meta['use_ssh_keys'] != "" and True:
        cmd_ssh_file = "echo '' > /tmp/ssh_temp_file"
        error = sudo_cmd(cmd_ssh_file, error, password, ssh_client)

        for key in config['ssh_authorized_keys']:
            tmp = f"echo {key} >> /tmp/ssh_temp_file"
            error = sudo_cmd(tmp, error, password, ssh_client)

        cmd_ssh_keys = f"sudo -S /usr/sbin/qm set {meta['id']} --sshkey /tmp/ssh_temp_file"
        error = sudo_cmd(cmd_ssh_keys, error, password, ssh_client)

        cmd_rm = "rm /tmp/ssh_temp_file"
        ssh_client.exec_command(cmd_rm)

    cmd_template = f"sudo -S /usr/sbin/qm template {meta['id']}"
    error = sudo_cmd(cmd_template, error, password, ssh_client)

    if error is not True:
        print_success()


def sudo_cmd(cmd4, error, password, ssh_client):
    """
    execute a sudo command
    :param cmd4:
    :param error:
    :param password:
    :param ssh_client:
    :return:
    """
    stdin, stdout, stderr = ssh_client.exec_command(cmd4, get_pty=True)
    stdin.write(password)
    stdin.flush()
    stdout.channel.recv_exit_status()
    if has_error(stderr):
        error = True
        print_error(stderr.read().decode())
    return error


def prepare_complex_command(cmd):
    """
    prepare a complex command with several arguments
    :param cmd:
    :return:
    """
    command_string = " ".join(map(shlex.quote, cmd))
    return command_string


def main():
    # Parse command-line arguments
    args = parse_args()

    # Load files
    config = load_yaml_config(args.config)['servers']
    workspace = load_json_workspace(args.workspace)

    print(''''\n   

    ██████╗ ██████╗  ██████╗ ██╗  ██╗███╗   ███╗██╗███████╗██╗   ██╗
    ██╔══██╗██╔══██╗██╔═══██╗╚██╗██╔╝████╗ ████║██║██╔════╝╚██╗ ██╔╝
    ██████╔╝██████╔╝██║   ██║ ╚███╔╝ ██╔████╔██║██║█████╗   ╚████╔╝ 
    ██╔═══╝ ██╔══██╗██║   ██║ ██╔██╗ ██║╚██╔╝██║██║██╔══╝    ╚██╔╝  
    ██║     ██║  ██║╚██████╔╝██╔╝ ██╗██║ ╚═╝ ██║██║██║        ██║   
    ╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝╚═╝╚═╝        ╚═╝   
                                                                

    ┓     ┏┓┓    •      ┏┓    •  
    ┣┓┓┏  ┣ ┃┏┓┏┓┓┏┓┏┓  ┃┓┓┏┏╋┓┏┓
    ┗┛┗┫  ┻ ┗┗┛┛ ┗┗┻┛┗  ┗┛┗┻┛┗┗┛┗
       ┛                         
        ''')

    for meta in workspace:

        password = config[meta['server']]['password'] + "\n"
        meta_config = config[meta['server']]

        # Connect to the proxmox server
        ssh_client = ssh_connect(meta_config)

        # Stopping the old process if exists
        process_stop(ssh_client, meta, password)

        # Deleting the old process if exists
        process_destroy(ssh_client, meta, password)

        if meta["type"] == "ct":

            process_create_container(ssh_client, meta, meta_config, password)

        elif meta["type"] == "vm":

            process_create_vm(ssh_client, meta, password)

        elif meta["type"] == "vm_ci":

            process_create_vm_ci(ssh_client, meta, meta_config, password)

        elif meta["type"] == "vm_ci_template":

            process_create_vm_ci_template(ssh_client, meta, meta_config, password)

        else:

            print("Type not found !")

        print(f"{BOLD}{AMBER}----- >  [TASK] - Closing SSH connection{RESET}\n")
        ssh_client.close()
        time.sleep(1)
        print_success()


if __name__ == "__main__":
    main()
