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

import errno
import os
import shutil
import signal

import six
from six.moves import configparser

from poorbmc import config as pbmc_config
from poorbmc import exception
from poorbmc import log
from poorbmc.pbmc import PoorBMC
from poorbmc import utils

LOG = log.get_logger()

# BMC status
RUNNING = 'running'
DOWN = 'down'

DEFAULT_SECTION = 'PoorBMC'

CONF = pbmc_config.get_config()


class PoorBMCManager(object):

    def __init__(self):
        super(PoorBMCManager, self).__init__()
        self.config_dir = CONF['default']['config_dir']

    def _parse_config(self, bmc_name):
        config_path = os.path.join(self.config_dir, bmc_name, 'config')
        if not os.path.exists(config_path):
            raise exception.BMCNotFound(bmc=bmc_name)

        config = configparser.ConfigParser()
        config.read(config_path)

        bmc = {}
        for item in ('username', 'password', 'address', 'bmc_name',
                     'snmp_address', 'snmp_outlet', 'snmp_community',
                     'snmp_port'):
            try:
                value = config.get(DEFAULT_SECTION, item)
            except configparser.NoOptionError:
                value = None

            bmc[item] = value

        # Port needs to be int
        bmc['port'] = config.getint(DEFAULT_SECTION, 'port')

        return bmc

    def _show(self, bmc_name):
        running = False
        try:
            pidfile_path = os.path.join(self.config_dir, bmc_name, 'pid')
            with open(pidfile_path, 'r') as f:
                pid = int(f.read())

            running = utils.is_pid_running(pid)
        except (IOError, ValueError):
            pass

        bmc_config = self._parse_config(bmc_name)
        bmc_config['status'] = RUNNING if running else DOWN

        # mask the passwords if requested
        if not CONF['default']['show_passwords']:
            bmc_config = utils.mask_dict_password(bmc_config)

        return bmc_config

    def add(self, username, password, port, address, bmc_name,
            snmp_address, snmp_outlet, snmp_community, snmp_port):

        bmc_path = os.path.join(self.config_dir, bmc_name)
        try:
            os.makedirs(bmc_path)
        except OSError as e:
            if e.errno == errno.EEXIST:
                raise exception.BMCAlreadyExists(bmc=bmc_name)
            raise exception.PoorBMCError(
                'Failed to create bmc %(bmc_name)s. Error: %(error)s' %
                {'bmc_name': bmc_name, 'error': e})

        config_path = os.path.join(bmc_path, 'config')
        with open(config_path, 'w') as f:
            config = configparser.ConfigParser()
            config.add_section(DEFAULT_SECTION)
            config.set(DEFAULT_SECTION, 'username', username)
            config.set(DEFAULT_SECTION, 'password', password)
            config.set(DEFAULT_SECTION, 'port', six.text_type(port))
            config.set(DEFAULT_SECTION, 'address', address)
            config.set(DEFAULT_SECTION, 'bmc_name', bmc_name)
            config.set(DEFAULT_SECTION, 'snmp_address', snmp_address)
            config.set(DEFAULT_SECTION, 'snmp_outlet', snmp_outlet)
            config.set(DEFAULT_SECTION, 'snmp_community', snmp_community)
            config.set(DEFAULT_SECTION, 'snmp_port', snmp_port)

            config.write(f)

    def delete(self, bmc_name):
        bmc_path = os.path.join(self.config_dir, bmc_name)
        if not os.path.exists(bmc_path):
            raise exception.BMCNotFound(bmc=bmc_name)
        shutil.rmtree(bmc_path)

    def start(self, bmc_name):
        bmc_path = os.path.join(self.config_dir, bmc_name)
        if not os.path.exists(bmc_path):
            raise exception.BMCNotFound(bmc=bmc_name)

        bmc_config = self._parse_config(bmc_name)

        # mask the passwords if requested
        log_config = bmc_config.copy()
        if not CONF['default']['show_passwords']:
            log_config = utils.mask_dict_password(bmc_config)

        LOG.debug('Starting a Poor BMC for bmc %(bmc_name)s with the '
                  'following configuration options: %(config)s',
                  {'bmc_name': bmc_name,
                   'config': ' '.join(['%s="%s"' % (k, log_config[k])
                                       for k in log_config])})

        with utils.detach_process() as pid_num:
            try:
                pbmc = PoorBMC(**bmc_config)
            except Exception as e:
                msg = ('Error starting a Poor BMC for bmc %(bmc_name)s. '
                       'Error: %(error)s' % {'bmc_name': bmc_name,
                                             'error': e})
                LOG.error(msg)
                raise exception.PoorBMCError(msg)

            # Save the PID number
            pidfile_path = os.path.join(bmc_path, 'pid')
            with open(pidfile_path, 'w') as f:
                f.write(str(pid_num))

            LOG.info('Poor BMC %s started', bmc_name)
            pbmc.listen(timeout=CONF['ipmi']['session_timeout'])

    def stop(self, bmc_name):
        LOG.debug('Stopping Poor BMC %s', bmc_name)
        bmc_path = os.path.join(self.config_dir, bmc_name)
        if not os.path.exists(bmc_path):
            raise exception.BMCNotFound(bmc=bmc_name)

        pidfile_path = os.path.join(bmc_path, 'pid')
        pid = None
        try:
            with open(pidfile_path, 'r') as f:
                pid = int(f.read())
        except (IOError, ValueError):
            raise exception.PoorBMCError(
                'Error stopping the bmc %s: PID file not '
                'found' % bmc_name)
        else:
            os.remove(pidfile_path)

        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass

    def list(self):
        bmcs = []
        try:
            for bmc in os.listdir(self.config_dir):
                if os.path.isdir(os.path.join(self.config_dir, bmc)):
                    bmcs.append(self._show(bmc))
        except OSError as e:
            if e.errno == errno.EEXIST:
                return bmcs

        return bmcs

    def show(self, bmc_name):
        return self._show(bmc_name)
