from subprocess import PIPE, run as s_run
from time import sleep
from panel.models import Messages, GeneralSettings
from datetime import datetime
from re import search as search_regex
from django.contrib import messages
from os import remove
from paramiko import RSAKey
from io import StringIO

import libvirt

MACHINE_STATE_NOSTATE = libvirt.VIR_DOMAIN_NOSTATE
MACHINE_STATE_RUNNING = libvirt.VIR_DOMAIN_RUNNING
MACHINE_STATE_BLOCKED = libvirt.VIR_DOMAIN_BLOCKED
MACHINE_STATE_PAUSED = libvirt.VIR_DOMAIN_PAUSED
MACHINE_STATE_SHUTDOWN = libvirt.VIR_DOMAIN_SHUTDOWN
MACHINE_STATE_SHUTOFF = libvirt.VIR_DOMAIN_SHUTOFF
MACHINE_STATE_CRASHED = libvirt.VIR_DOMAIN_CRASHED
MACHINE_STATE_SUSPENDED = libvirt.VIR_DOMAIN_PMSUSPENDED


def callCmd(command: str) -> [str, str, int]:
    """ Returns stdout, stderr and returncode"""
    if not isinstance(command, str):
        raise Exception("Command has to be a string")
    cmd = s_run(
        command.split(), stdout=PIPE, stderr=PIPE
    )
    return cmd.stdout.decode(), cmd.stderr.decode(), cmd.returncode


def convertDisk(request, disk_location: str) -> str:
    """ Runs qemu-img info on a file and returns file foramt """

    cmd_stdout, cmd_stderr, cmd_code = callCmd(
        "qemu-img info " + disk_location
    )

    if cmd_code:
        messages.error(
            request,
            "STDOUT: " + cmd_stdout + "\nSTDERR: " + cmd_stderr
        )
    else:
        file_format = search_regex(
            "(?<=file format:\s)(.*)", cmd_stdout).group(0)
        if file_format == "qcow2":
            messages.error(request, "Qcow2 disk already")
        _, _, _ = callCmd("mv " + disk_location + disk_location + ".lock")
        cmd_stdout, cmd_stderr, cmd_code = callCmd(
            "qemu-img convert -f " + file_format + " -O qcow2 " +
            disk_location + ".lock " +
            disk_location.replace(file_format, "qcow2")
        )
        if not cmd_code:
            message = Messages()
            message.content = f"""Disk converted!<br/>
<br/>
It is available under the location of:<br/>
<br/>
<br/>
<b>{disk_location.replace(file_format, "qcow2")}</b><br/><br/>
Previous files was removed.<br/>
--<br/>
Thanks,<br/>
SYSTEM
"""
            message.sender = request.user
            message.receiver = request.user
            message.subject = "Disk conversion to qcow2"
            message.created_at = datetime.now()
            message.save()
            _ = remove(disk_location)
        else:
            messages.error(
                request,
                "STDOUT: " + cmd_stdout + "\nSTDERR: " + cmd_stderr
            )


def connect(URI: str = "qemu:///system") -> libvirt.virConnect:
    """ Simple libvirt connect function """

    return libvirt.open(URI)


def reassureConnection(virt_conn: libvirt.virConnect) -> libvirt.virConnect:
    """ Check libvirt connection. Reconnect if needed """

    if not isinstance(virt_conn, libvirt.virConnect):
        raise Exception("libvirt.virConnect type expected in virt_conn")

    if not virt_conn.isAlive():
        URI = virt_conn.getURI()

        del virt_conn
        virt_conn = libvirt.open(URI)

    if virt_conn.isAlive():
        return virt_conn
    else:
        raise Exception(
            f"Was unable to connect to the libvirt daemon under {URI}"
        )


def listNetworks(virt_conn: libvirt.virConnect) -> list:
    """ Return list of libvirt.virNetwork objects """

    virt_conn = reassureConnection(virt_conn)

    return virt_conn.listAllNetworks()


def addOrUpdateHost(
        virt_conn: libvirt.virConnect,
        network_name: str, mac: str, ip: str) -> bool:
    """ Add or update host static IP assignment in DHCP server

This definition is taken from otherwiseguy repo from github:
https://github.com/otherwiseguy/virt-add-static-dhcp
Adjusted to this repo needs
"""
    virt_conn = reassureConnection(virt_conn)

    virt_network = virt_conn.networkLookupByName(network_name)

    cmd = libvirt.VIR_NETWORK_UPDATE_COMMAND_MODIFY
    section = libvirt.VIR_NETWORK_SECTION_IP_DHCP_HOST
    xml = "<host mac='%s' ip='%s'/>" % (mac, ip)
    flags = (libvirt.VIR_NETWORK_UPDATE_AFFECT_LIVE |
             libvirt.VIR_NETWORK_UPDATE_AFFECT_CONFIG)
    try:
        virt_network.update(cmd, section, -1, xml, flags)
    except:
        cmd = libvirt.VIR_NETWORK_UPDATE_COMMAND_ADD_FIRST
        virt_network.update(cmd, section, -1, xml, flags)

    return True


def _machineOperation(
        virt_conn: libvirt.virConnect,
        domain_name: str,
        operation: str,
        force: bool = False) -> [int, bool]:
    """ Do not export/import this function """

    try:
        vm = virt_conn.lookupByName(domain_name)
    except libvirt.libvirtError:
        raise Exception("No VM found with the provided name")

    ops = {
        'stop': {
            'function': vm.shutdown,
            'state_list': [MACHINE_STATE_SHUTDOWN, MACHINE_STATE_SHUTOFF],
        },
        'start': {
            'function': vm.create,
            'state_list': [MACHINE_STATE_RUNNING, ],
        },
    }

    if operation == "stop" and force:
        ops['stop']['function'] = vm.destroy

    if operation not in ops.keys():
        raise Exception(
            f"Unknown operation. Available operations: {ops.keys()}"
        )

    state = vm.state()[0]

    if state not in ops[operation]['state_list']:

        _ = ops[operation]['function']()
        sleep(1)
        new_state = vm.state()[0]

        if new_state not in ops[operation]['state_list']:
            sleep(5)
            new_state = vm.state()[0]
            if new_state not in ops[operation]['state_list']:
                raise Exception(
                    f"VM refused to perform the {operation} action"
                )
        return [new_state, False]

    elif state in ops[operation]['state_list']:
        # Machine was already in state
        return [state, True]

    raise Exception("VM is blocked")


def startMachine(
        virt_conn: libvirt.virConnect, domain_name: str) -> [int, bool]:
    """ Start a domain by name
    Returns a list with:
    * an integer return code,
    * a boolean saying if the machine was already running.
"""

    virt_conn = reassureConnection(virt_conn)

    return _machineOperation(virt_conn, domain_name, "start")


def stopMachine(
        virt_conn: libvirt.virConnect, domain_name: str,
        force: bool = False) -> [int, bool]:
    """ Stop a domain by name
    Returns a list with:
    * an integer return code,
    * a boolean saying if the machine was already stopped.
"""

    virt_conn = reassureConnection(virt_conn)

    return _machineOperation(virt_conn, domain_name, "stop", force)


def listMachines(virt_conn: libvirt.virConnect) -> list:
    """ Return a list of machines and states
    Returns a list with:
    * a string with the machine name
    * a boolean with machine state
"""

    virt_conn = reassureConnection(virt_conn)

    all_domains = {
        x.name(): x.state()[0] for x in virt_conn.listAllDomains()
    }

    return all_domains


SNAPSHOT_XML_TEMPLATE = """<domainsnapshot>
  <name>{snapshot_name}</name>
</domainsnapshot>"""


def createSnapshot(
        virt_conn: libvirt.virConnect,
        domain_name: str, snapshot_name: str) -> bool:
    """ Make a snapshot of shutoff VM """

    virt_conn = reassureConnection(virt_conn)

    # Make sure VM is shutoff
    _, _ = stopMachine(virt_conn, domain_name)

    vm = virt_conn.lookupByName(domain_name)

    try:
        vm.snapshotCreateXML(
            SNAPSHOT_XML_TEMPLATE.format(snapshot_name=snapshot_name)
        )
    except libvirt.libvirtError:
        return False

    return True


def revertSnapshot(
        virt_conn: libvirt.virConnect,
        domain_name: str, snapshot_name: str) -> bool:
    """ Revert a snapshot of shutoff VM """

    virt_conn = reassureConnection(virt_conn)

    vm = virt_conn.lookupByName(domain_name)
    snapshot = vm.snapshotLookupByName(snapshot_name)

    # Make sure VM is shutoff
    _, _ = stopMachine(virt_conn, domain_name)

    try:
        vm.revertToSnapshot(snapshot)
    except libvirt.libvirtError:
        return False

    return True


def createMachine(virt_conn: libvirt.virConnect, xml: str) -> bool:
    """ Create VM """

    virt_conn = reassureConnection(virt_conn)

    try:
        virt_conn.defineXML(xml)
    except libvirt.libvirtError:
        return False

    return True


def translateMachineState(state: int) -> str:
    if state in [MACHINE_STATE_SHUTOFF, MACHINE_STATE_SHUTDOWN]:
        return "STOPPED"
    elif state == MACHINE_STATE_RUNNING:
        return "RUNNING"
    elif state == MACHINE_STATE_PAUSED:
        return "PAUSED"
    else:
        return "UNKNOWN"


def createNetwork(virt_conn: libvirt.virConnect, xml: str) -> bool:
    """ Define and start a network """

    virt_conn = reassureConnection(virt_conn)

    try:
        network = virt_conn.networkDefineXML(xml)
    except libvirt.libvirtError:
        return False

    network.setAutostart(True)
    network.create()

    return True


def deleteNetwork(virt_conn: libvirt.virConnect, network_name: str) -> bool:
    """ Undefine and destroy a network """

    virt_conn = reassureConnection(virt_conn)

    try:
        network = virt_conn.networkLookupByName(network_name)
    except libvirt.libvirtError:
        return False

    network.destroy()
    network.undefine()

    return True


def checkIfNetworkExists(
        virt_conn: libvirt.virConnect, network_name: str) -> bool:
    """ Check if network exists """

    virt_conn = reassureConnection(virt_conn)

    try:
        virt_conn.networkLookupByName(network_name)
    except libvirt.libvirtError:
        return False

    return True


def createSSHKey(force: False) -> None:
    """ Check if key is present already in the DB. If not, generate it """

    key_from_db = GeneralSettings.objects.filter(key="GS_SSH_KEY")

    if key_from_db and not force:
        raise Exception("They key is already present in the database")

    key = RSAKey.generate(4096)
    pkey = StringIO()
    key.write_private_key(pkey)
    pkey_string = pkey.getvalue()  # Store in DB

    if key_from_db:
        key_db = key_from_db[0]
    else:
        key_db = GeneralSettings()
        key_db.key = "GS_SSH_KEY"
        key_db.save()

    key_db.value = pkey_string
    key_db.save()


def returnSSHKey() -> RSAKey:
    """ Retrieve SSH key from db and return it as paramiko object """

    key_from_db = GeneralSettings.objects.filter(key="GS_SSH_KEY")

    if not key_from_db:
        raise Exception("Not SSH key found in the database")

    else:
        key_string = key_from_db[0].value

    key_stringIO = StringIO(key_string)

    key = RSAKey.from_private_key(key_stringIO)

    return key
