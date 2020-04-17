#!/usr/bin/env python3
import libvirt
import sys
import os

IFACE_EXCLUDE = ['lo']
LIBVIRT = "qemu+ssh://kvm-local/system"

class suppress_stdout_stderr(object):
    def __enter__(self):
        self.outnull_file = open(os.devnull, 'w')
        self.errnull_file = open(os.devnull, 'w')

        self.old_stdout_fileno_undup    = sys.stdout.fileno()
        self.old_stderr_fileno_undup    = sys.stderr.fileno()

        self.old_stdout_fileno = os.dup ( sys.stdout.fileno() )
        self.old_stderr_fileno = os.dup ( sys.stderr.fileno() )

        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr

        os.dup2 ( self.outnull_file.fileno(), self.old_stdout_fileno_undup )
        os.dup2 ( self.errnull_file.fileno(), self.old_stderr_fileno_undup )

        sys.stdout = self.outnull_file
        sys.stderr = self.errnull_file
        return self

    def __exit__(self, *_):
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr

        os.dup2 ( self.old_stdout_fileno, self.old_stdout_fileno_undup )
        os.dup2 ( self.old_stderr_fileno, self.old_stderr_fileno_undup )

        os.close ( self.old_stdout_fileno )
        os.close ( self.old_stderr_fileno )

        self.outnull_file.close()
        self.errnull_file.close()

class ansible_inventory:
    """Build an ansible inventory"""
    inventory = {'_meta':{'hostvars':{}},'all': {'children':[]}}

    def __init__(self, lower=True):
        self.lower = lower

    def add_host(self, hostname, ip, groups):
        if self.lower:
            hostname = hostname.lower()
        if ip is not None:
            self.inventory['_meta']['hostvars'][hostname] = {'ansible_host': ip}

        if len(groups) == 0:
            groups.append('ungrouped')

        for group in groups:
            if self.lower:
                group = group.lower()
            if group not in self.inventory['all']['children']:
                self.inventory['all']['children'].append(group)
            try:
                self.inventory[group]['hosts'].append(hostname)
            except Exception:
                hosts = []
                hosts.append(hostname)
                self.inventory[group] = {}
                self.inventory[group]['hosts'] = hosts
    def dump(self):
        return self.inventory

try:
    conn = libvirt.open(LIBVIRT)
except libvirt.libvirtError:
    print(libvirt.libvirtError)
    sys.exit(1)

inventory = ansible_inventory()

for vm in conn.listAllDomains():
    ifaces = {}
    no_output = suppress_stdout_stderr()
    if vm.isActive():
        no_output.__enter__()
        try:
            ifaces = vm.interfaceAddresses(libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_AGENT)
        except:
            continue
        finally:
            no_output.__exit__()
            for iface in ifaces:
                if iface and iface not in IFACE_EXCLUDE:
                    inventory.add_host(vm.name(),ifaces[iface]['addrs'][0]['addr'],[vm.name().rsplit('-', 1)[0]])
print(inventory.dump())

sys.exit(0)