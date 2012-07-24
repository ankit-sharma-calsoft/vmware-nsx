# vim: tabstop=4 shiftwidth=4 softtabstop=4
# Copyright 2011 Nicira Networks, Inc.
# All Rights Reserved.
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
# @author: Aaron Rosen, Nicira Networks, Inc.

from sqlalchemy.orm import exc

import quantum.db.api as db
from quantum.plugins.openvswitch import ovs_models_v2


def get_vlans():
    session = db.get_session()
    try:
        bindings = (session.query(ovs_models_v2.VlanBinding).
                    all())
    except exc.NoResultFound:
        return []
    return [(binding.vlan_id, binding.network_id) for binding in bindings]


def get_vlan(net_id):
    session = db.get_session()
    try:
        binding = (session.query(ovs_models_v2.VlanBinding).
                   filter_by(network_id=net_id).
                   one())
    except exc.NoResultFound:
        return
    return binding.vlan_id


def add_vlan_binding(vlan_id, net_id):
    session = db.get_session()
    binding = ovs_models_v2.VlanBinding(vlan_id, net_id)
    session.add(binding)
    session.flush()
    return binding


def remove_vlan_binding(net_id):
    session = db.get_session()
    try:
        binding = (session.query(ovs_models_v2.VlanBinding).
                   filter_by(network_id=net_id).
                   one())
        session.delete(binding)
    except exc.NoResultFound:
        pass
    session.flush()
