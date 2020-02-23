from subprocess import PIPE, run as s_run
from time import sleep

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
        operation: str) -> [int, bool]:
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
        virt_conn: libvirt.virConnect, domain_name: str) -> [int, bool]:
    """ Stop a domain by name
    Returns a list with:
    * an integer return code,
    * a boolean saying if the machine was already stopped.
"""

    virt_conn = reassureConnection(virt_conn)

    return _machineOperation(virt_conn, domain_name, "stop")


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
