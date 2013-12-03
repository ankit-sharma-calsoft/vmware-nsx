# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2012 Cisco Systems, Inc.  All rights reserved.
#
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
#
# @author: Sumit Naiksatam, Cisco Systems, Inc.

from abc import ABCMeta, abstractmethod
import inspect

import six


@six.add_metaclass(ABCMeta)
class L2DevicePluginBase(object):
    """Base class for a device-specific plugin.

    An example of a device-specific plugin is a Nexus switch plugin.
    The network model relies on device-category-specific plugins to perform
    the configuration on each device.
    """

    @abstractmethod
    def get_all_networks(self, tenant_id, **kwargs):
        """Get newtorks.

        :returns:
        :raises:
        """
        pass

    @abstractmethod
    def create_network(self, tenant_id, net_name, net_id, vlan_name, vlan_id,
                       **kwargs):
        """Create network.

        :returns:
        :raises:
        """
        pass

    @abstractmethod
    def delete_network(self, tenant_id, net_id, **kwargs):
        """Delete network.

        :returns:
        :raises:
        """
        pass

    @abstractmethod
    def update_network(self, tenant_id, net_id, name, **kwargs):
        """Update network.

        :returns:
        :raises:
        """
        pass

    @abstractmethod
    def get_all_ports(self, tenant_id, net_id, **kwargs):
        """Get ports.

        :returns:
        :raises:
        """
        pass

    @abstractmethod
    def create_port(self, tenant_id, net_id, port_state, port_id, **kwargs):
        """Create port.

        :returns:
        :raises:
        """
        pass

    @abstractmethod
    def delete_port(self, tenant_id, net_id, port_id, **kwargs):
        """Delete port.

        :returns:
        :raises:
        """
        pass

    @abstractmethod
    def update_port(self, tenant_id, net_id, port_id, **kwargs):
        """Update port.

        :returns:
        :raises:
        """
        pass

    @abstractmethod
    def get_port_details(self, tenant_id, net_id, port_id, **kwargs):
        """Get port details.

        :returns:
        :raises:
        """
        pass

    @abstractmethod
    def plug_interface(self, tenant_id, net_id, port_id, remote_interface_id,
                       **kwargs):
        """Plug interface.

        :returns:
        :raises:
        """
        pass

    @abstractmethod
    def unplug_interface(self, tenant_id, net_id, port_id, **kwargs):
        """Unplug interface.

        :returns:
        :raises:
        """
        pass

    def create_subnet(self, tenant_id, net_id, ip_version,
                      subnet_cidr, **kwargs):
        """Create subnet.

        :returns:
        :raises:
        """
        pass

    def get_subnets(self, tenant_id, net_id, **kwargs):
        """Get subnets.

        :returns:
        :raises:
        """
        pass

    def get_subnet(self, tenant_id, net_id, subnet_id, **kwargs):
        """Get subnet.

        :returns:
        :raises:
        """
        pass

    def update_subnet(self, tenant_id, net_id, subnet_id, **kwargs):
        """Update subnet.

        :returns:
        :raises:
        """
        pass

    def delete_subnet(self, tenant_id, net_id, subnet_id, **kwargs):
        """Delete subnet.

        :returns:
        :raises:
        """
        pass

    @classmethod
    def __subclasshook__(cls, klass):
        """Check plugin class.

        The __subclasshook__ method is a class method
        that will be called every time a class is tested
        using issubclass(klass, Plugin).
        In that case, it will check that every method
        marked with the abstractmethod decorator is
        provided by the plugin class.
        """
        if cls is L2DevicePluginBase:
            for method in cls.__abstractmethods__:
                method_ok = False
                for base in klass.__mro__:
                    if method in base.__dict__:
                        fn_obj = base.__dict__[method]
                        if inspect.isfunction(fn_obj):
                            abstract_fn_obj = cls.__dict__[method]
                            arg_count = fn_obj.func_code.co_argcount
                            expected_arg_count = \
                                abstract_fn_obj.func_code.co_argcount
                            method_ok = arg_count == expected_arg_count
                if method_ok:
                    continue
                return NotImplemented
            return True
        return NotImplemented
