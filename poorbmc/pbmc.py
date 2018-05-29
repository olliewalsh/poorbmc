#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import pyghmi.ipmi.bmc as bmc

from poorbmc import log

from poorbmc import snmp

snmp_driver = snmp.SNMPDriverAPCMasterSwitch
states = snmp.states

LOG = log.get_logger()

# Power states
POWEROFF = 0
POWERON = 1

# From the IPMI - Intelligent Platform Management Interface Specification
# Second Generation v2.0 Document Revision 1.1 October 1, 2013
# https://www.intel.com/content/dam/www/public/us/en/documents/product-briefs/ipmi-second-gen-interface-spec-v2-rev1-1.pdf
#
# Command failed and can be retried
IPMI_COMMAND_NODE_BUSY = 0xC0
# Invalid data field in request
IPMI_INVALID_DATA = 0xcc

BOOT_DEVICES = [
    'default',
    'network',
    'hd',
    'optical'
]


class PoorBMC(bmc.Bmc):

    def __init__(self, username, password, port, address, bmc_name,
                 snmp_address, snmp_outlet, snmp_community, snmp_port):
        super(PoorBMC, self).__init__(
            {username: password},
            port=port,
            address=address
        )
        self.bmc_name = bmc_name
        self.snmp = snmp_driver({
            'address': snmp_address,
            'outlet': snmp_outlet,
            'community': snmp_community,
            'port': snmp_port,
            'version': 1
        })
        self.current_boot_device = 'default'

    def get_boot_device(self):
        LOG.debug('Get boot device called for %s', self.bmc_name)
        return self.current_boot_device

    def set_boot_device(self, bootdevice):
        LOG.debug('Set boot device called for %(bmc)s with boot '
                  'device "%(bootdev)s"', {'bmc': self.bmc_name,
                                           'bootdev': bootdevice})
        if bootdevice in BOOT_DEVICES:
            self.current_boot_device = bootdevice
        else:
            return IPMI_INVALID_DATA

    def get_power_state(self):
        LOG.debug('Get power state called for bmc %s', self.bmc_name)
        try:
            state = self.snmp.power_state()
            if state == states.POWER_ON:
                return POWERON
            elif state == states.POWEROFF:
                return POWEROFF
            else:
                return IPMI_COMMAND_NODE_BUSY
        except Exception as e:
            LOG.error('Error getting the power state of bmc %(bmc)s. '
                      'Error: %(error)s', {'bmc': self.bmc_name,
                                           'error': e})
            # Command failed, but let client to retry
            return IPMI_COMMAND_NODE_BUSY

        return POWEROFF

    def pulse_diag(self):
        LOG.debug('Power diag called for bmc %s', self.bmc_name)
        return IPMI_COMMAND_NODE_BUSY

    def power_off(self):
        LOG.debug('Power off called for bmc %s', self.bmc_name)
        try:
            self.snmp.power_off()
        except Exception as e:
            LOG.error('Error powering off the bmc %(bmc)s. '
                      'Error: %(error)s' % {'bmc': self.bmc_name,
                                            'error': e})
            # Command failed, but let client to retry
            return IPMI_COMMAND_NODE_BUSY

    def power_on(self):
        LOG.debug('Power on called for bmc %s', self.bmc_name)
        try:
            self.snmp.power_on()
        except Exception as e:
            LOG.error('Error powering on the bmc %(bmc)s. '
                      'Error: %(error)s' % {'bmc': self.bmc_name,
                                            'error': e})
            # Command failed, but let client to retry
            return IPMI_COMMAND_NODE_BUSY

    def power_shutdown(self):
        LOG.debug('Soft power off called for bmc %s', self.bmc_name)
        return IPMI_COMMAND_NODE_BUSY

    def power_reset(self):
        LOG.debug('Power reset called for bmc %s', self.bmc_name)
        try:
            self.snmp.power_reset()
        except Exception as e:
            LOG.error('Error reseting the bmc %(bmc)s. '
                      'Error: %(error)s' % {'bmc': self.bmc_name,
                                            'error': e})
            # Command not supported in present state
            return IPMI_COMMAND_NODE_BUSY
