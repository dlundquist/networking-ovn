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

from neutron.agent.ovsdb import impl_idl
from neutron.agent.ovsdb.native import connection

from networking_ovn._i18n import _
from networking_ovn.common import config as cfg
from networking_ovn.ovsdb import commands as cmd
from networking_ovn.ovsdb import ovn_api
from networking_ovn.ovsdb import ovsdb_monitor


def get_connection(trigger):
    # The trigger is the start() method of the NeutronWorker class
    if trigger.im_class == ovsdb_monitor.OvnWorker:
        cls = ovsdb_monitor.OvnConnection
    else:
        cls = connection.Connection
    return cls(cfg.get_ovn_ovsdb_connection(),
               cfg.get_ovn_ovsdb_timeout(), 'OVN_Northbound')


class OvsdbOvnIdl(ovn_api.API):

    ovsdb_connection = None

    def __init__(self, plugin, trigger):
        super(OvsdbOvnIdl, self).__init__()
        if OvsdbOvnIdl.ovsdb_connection is None:
            OvsdbOvnIdl.ovsdb_connection = get_connection(trigger)
        if isinstance(OvsdbOvnIdl.ovsdb_connection,
                      ovsdb_monitor.OvnConnection):
            OvsdbOvnIdl.ovsdb_connection.start(plugin)
        else:
            OvsdbOvnIdl.ovsdb_connection.start()
        self.idl = OvsdbOvnIdl.ovsdb_connection.idl
        self.ovsdb_timeout = cfg.get_ovn_ovsdb_timeout()

    @property
    def _tables(self):
        return self.idl.tables

    def transaction(self, check_error=False, log_errors=True, **kwargs):
        return impl_idl.Transaction(self,
                                    OvsdbOvnIdl.ovsdb_connection,
                                    self.ovsdb_timeout,
                                    check_error, log_errors)

    def create_lswitch(self, lswitch_name, may_exist=True, **columns):
        return cmd.AddLSwitchCommand(self, lswitch_name,
                                     may_exist, **columns)

    def delete_lswitch(self, lswitch_name=None, ext_id=None, if_exists=True):
        if lswitch_name is not None:
            return cmd.DelLSwitchCommand(self, lswitch_name, if_exists)
        else:
            raise RuntimeError(_("Currently only supports delete "
                                 "by lswitch-name"))

    def set_lswitch_ext_id(self, lswitch_id, ext_id, if_exists=True):
        return cmd.LSwitchSetExternalIdCommand(self, lswitch_id,
                                               ext_id[0], ext_id[1],
                                               if_exists)

    def create_lport(self, lport_name, lswitch_name, may_exist=True,
                     **columns):
        return cmd.AddLogicalPortCommand(self, lport_name, lswitch_name,
                                         may_exist, **columns)

    def set_lport(self, lport_name, if_exists=True, **columns):
        return cmd.SetLogicalPortCommand(self, lport_name,
                                         if_exists, **columns)

    def delete_lport(self, lport_name=None, lswitch=None,
                     ext_id=None, if_exists=True):
        if lport_name is not None:
            return cmd.DelLogicalPortCommand(self, lport_name,
                                             lswitch, if_exists)
        else:
            raise RuntimeError(_("Currently only supports "
                                 "delete by lport-name"))

    def get_all_logical_switches_ids(self):
        result = {}
        for row in self._tables['Logical_Switch'].rows.values():
            result[row.name] = row.external_ids
        return result

    def get_all_logical_ports_ids(self):
        result = {}
        for row in self._tables['Logical_Port'].rows.values():
            result[row.name] = row.external_ids
        return result

    def create_lrouter(self, name, may_exist=True, **columns):
        return cmd.AddLRouterCommand(self, name,
                                     may_exist, **columns)

    def update_lrouter(self, name, if_exists=True, **columns):
        return cmd.UpdateLRouterCommand(self, name,
                                        if_exists, **columns)

    def delete_lrouter(self, name, if_exists=True):
        return cmd.DelLRouterCommand(self, name, if_exists)

    def add_lrouter_port(self, name, lrouter, **columns):
        return cmd.AddLRouterPortCommand(self, name, lrouter, **columns)

    def delete_lrouter_port(self, name, lrouter, if_exists=True):
        return cmd.DelLRouterPortCommand(self, name, lrouter,
                                         if_exists)

    def set_lrouter_port_in_lport(self, lport, lrouter_port):
        return cmd.SetLRouterPortInLPortCommand(self, lport, lrouter_port)

    def add_acl(self, lswitch, lport, **columns):
        return cmd.AddACLCommand(self, lswitch, lport, **columns)

    def delete_acl(self, lswitch, lport, if_exists=True):
        return cmd.DelACLCommand(self, lswitch, lport, if_exists)
