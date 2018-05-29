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

import sys

from cliff.app import App
from cliff.command import Command
from cliff.commandmanager import CommandManager
from cliff.lister import Lister

import poorbmc
from poorbmc.manager import PoorBMCManager


class AddCommand(Command):
    """Create a new BMC for a virtual machine instance"""

    def get_parser(self, prog_name):
        parser = super(AddCommand, self).get_parser(prog_name)

        parser.add_argument('bmc_name',
                            help='The name of the bmc')
        parser.add_argument('--username',
                            dest='username',
                            default='admin',
                            help='The BMC username; defaults to "admin"')
        parser.add_argument('--password',
                            dest='password',
                            default='password',
                            help='The BMC password; defaults to "password"')
        parser.add_argument('--port',
                            dest='port',
                            type=int,
                            default=623,
                            help='Port to listen on; defaults to 623')
        parser.add_argument('--address',
                            dest='address',
                            default='::',
                            help=('The address to bind to (IPv4 and IPv6 '
                                  'are supported); defaults to ::'))
        parser.add_argument('--snmp_address',
                            dest='snmp_address')
        parser.add_argument('--snmp_outlet',
                            dest='snmp_outlet')
        parser.add_argument('--snmp_community',
                            dest='snmp_community',
                            default='private')
        parser.add_argument('--snmp_port',
                            type=int,
                            default=161,
                            dest='snmp_port')
        return parser

    def take_action(self, args):

        self.app.manager.add(username=args.username, password=args.password,
                             port=args.port, address=args.address,
                             bmc_name=args.bmc_name,
                             snmp_address=args.snmp_address,
                             snmp_outlet=args.snmp_outlet,
                             snmp_community=args.snmp_community,
                             snmp_port=str(args.snmp_port))


class DeleteCommand(Command):
    """Delete a virtual BMC for a virtual machine instance"""

    def get_parser(self, prog_name):
        parser = super(DeleteCommand, self).get_parser(prog_name)

        parser.add_argument('bmc_names', nargs='+',
                            help='A list of bmc names')

        return parser

    def take_action(self, args):
        for bmc in args.bmc_names:
            self.app.manager.delete(bmc)


class StartCommand(Command):
    """Start a virtual BMC for a virtual machine instance"""

    def get_parser(self, prog_name):
        parser = super(StartCommand, self).get_parser(prog_name)

        parser.add_argument('bmc_name',
                            help='The name of the bmc')

        return parser

    def take_action(self, args):
        self.app.manager.start(args.bmc_name)


class StopCommand(Command):
    """Stop a virtual BMC for a virtual machine instance"""

    def get_parser(self, prog_name):
        parser = super(StopCommand, self).get_parser(prog_name)

        parser.add_argument('bmc_names', nargs='+',
                            help='A list of bmc names')

        return parser

    def take_action(self, args):
        for bmc_name in args.bmc_names:
            self.app.manager.stop(bmc_name)


class ListCommand(Lister):
    """List all virtual BMC instances"""

    def take_action(self, args):
        header = ('BMC name', 'Status', 'Address', 'Port')
        rows = []

        for bmc in self.app.manager.list():
            rows.append(
                ([bmc['bmc_name'], bmc['status'],
                  bmc['address'], bmc['port']])
            )

        return header, sorted(rows)


class ShowCommand(Lister):
    """Show virtual BMC properties"""

    def get_parser(self, prog_name):
        parser = super(ShowCommand, self).get_parser(prog_name)

        parser.add_argument('bmc_name',
                            help='The name of the bmc')

        return parser

    def take_action(self, args):
        header = ('Property', 'Value')
        rows = []

        bmc = self.app.manager.show(args.bmc_name)

        for key, val in bmc.items():
            rows.append((key, val))

        return header, sorted(rows)


class PoorBMCApp(App):

    def __init__(self):
        super(PoorBMCApp, self).__init__(
            description='Poor Baseboard Management Controller (BMC)',
            version=poorbmc.__version__,
            command_manager=CommandManager('poorbmc'),
            deferred_help=True,
        )

    def initialize_app(self, argv):
        self.manager = PoorBMCManager()

    def clean_up(self, cmd, result, err):
        self.LOG.debug('clean_up %s', cmd.__class__.__name__)
        if err:
            self.LOG.debug('got an error: %s', err)


def main(argv=sys.argv[1:]):
    pbmc_app = PoorBMCApp()
    return pbmc_app.run(argv)


if __name__ == '__main__':
    sys.exit(main())
