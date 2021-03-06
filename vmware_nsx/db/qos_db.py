# Copyright 2013 VMware, Inc.  All rights reserved.
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

from sqlalchemy.orm import exc

from neutron.db import _model_query as model_query
from neutron.db import _resource_extend as resource_extend
from neutron.db import api as db_api
from neutron.db import models_v2

from neutron_lib.api.definitions import network as net_def
from neutron_lib.api.definitions import port as port_def
from neutron_lib.db import utils as db_utils

from oslo_log import log
from oslo_utils import uuidutils

from vmware_nsx.db import nsx_models
from vmware_nsx.extensions import qos_queue as qos

LOG = log.getLogger(__name__)


@resource_extend.has_resource_extenders
class QoSDbMixin(qos.QueuePluginBase):
    """Mixin class to add queues."""

    def create_qos_queue(self, context, qos_queue):
        q = qos_queue['qos_queue']
        with db_api.context_manager.writer.using(context):
            qos_queue = nsx_models.QoSQueue(
                id=q.get('id', uuidutils.generate_uuid()),
                name=q.get('name'),
                tenant_id=q['tenant_id'],
                default=q.get('default'),
                min=q.get('min'),
                max=q.get('max'),
                qos_marking=q.get('qos_marking'),
                dscp=q.get('dscp'))
            context.session.add(qos_queue)
        return self._make_qos_queue_dict(qos_queue)

    def get_qos_queue(self, context, queue_id, fields=None):
        return self._make_qos_queue_dict(
            self._get_qos_queue(context, queue_id), fields)

    def _get_qos_queue(self, context, queue_id):
        try:
            return model_query.get_by_id(context, nsx_models.QoSQueue,
                                         queue_id)
        except exc.NoResultFound:
            raise qos.QueueNotFound(id=queue_id)

    def get_qos_queues(self, context, filters=None, fields=None, sorts=None,
                       limit=None, marker=None, page_reverse=False):
        marker_obj = db_utils.get_marker_obj(self, context, 'qos_queue',
                                             limit, marker)
        return model_query.get_collection(context, nsx_models.QoSQueue,
                                          self._make_qos_queue_dict,
                                          filters=filters, fields=fields,
                                          sorts=sorts, limit=limit,
                                          marker_obj=marker_obj,
                                          page_reverse=page_reverse)

    def delete_qos_queue(self, context, queue_id):
        with db_api.context_manager.writer.using(context):
            qos_queue = self._get_qos_queue(context, queue_id)
            context.session.delete(qos_queue)

    def _process_port_queue_mapping(self, context, port_data, queue_id):
        port_data[qos.QUEUE] = queue_id
        if not queue_id:
            return
        with db_api.context_manager.writer.using(context):
            context.session.add(nsx_models.PortQueueMapping(
                port_id=port_data['id'],
                                queue_id=queue_id))

    def _get_port_queue_bindings(self, context, filters=None, fields=None):
        return model_query.get_collection(context,
                                          nsx_models.PortQueueMapping,
                                          self._make_port_queue_binding_dict,
                                          filters=filters, fields=fields)

    def _delete_port_queue_mapping(self, context, port_id):
        query = model_query.query_with_hooks(context,
                                             nsx_models.PortQueueMapping)
        try:
            binding = query.filter(
                nsx_models.PortQueueMapping.port_id == port_id).one()
        except exc.NoResultFound:
            # return since this can happen if we are updating a port that
            # did not already have a queue on it. There is no need to check
            # if there is one before deleting if we return here.
            return
        with db_api.context_manager.writer.using(context):
            context.session.delete(binding)

    def _process_network_queue_mapping(self, context, net_data, queue_id):
        net_data[qos.QUEUE] = queue_id
        if not queue_id:
            return
        with db_api.context_manager.writer.using(context):
            context.session.add(
                nsx_models.NetworkQueueMapping(network_id=net_data['id'],
                                               queue_id=queue_id))

    def _get_network_queue_bindings(self, context, filters=None, fields=None):
        return model_query.get_collection(
            context,
            nsx_models.NetworkQueueMapping,
            self._make_network_queue_binding_dict,
            filters=filters, fields=fields)

    def _delete_network_queue_mapping(self, context, network_id):
        query = self._model_query(context, nsx_models.NetworkQueueMapping)
        with db_api.context_manager.writer.using(context):
            binding = query.filter_by(network_id=network_id).first()
            if binding:
                context.session.delete(binding)

    @staticmethod
    @resource_extend.extends([net_def.COLLECTION_NAME])
    @resource_extend.extends([port_def.COLLECTION_NAME])
    def _extend_dict_qos_queue(obj_res, obj_db):
        queue_mapping = obj_db['qos_queue']
        if queue_mapping:
            obj_res[qos.QUEUE] = queue_mapping.get('queue_id')
        return obj_res

    def _make_qos_queue_dict(self, queue, fields=None):
        res = {'id': queue['id'],
               'name': queue.get('name'),
               'default': queue.get('default'),
               'tenant_id': queue['tenant_id'],
               'min': queue.get('min'),
               'max': queue.get('max'),
               'qos_marking': queue.get('qos_marking'),
               'dscp': queue.get('dscp')}
        return db_utils.resource_fields(res, fields)

    def _make_port_queue_binding_dict(self, queue, fields=None):
        res = {'port_id': queue['port_id'],
               'queue_id': queue['queue_id']}
        return db_utils.resource_fields(res, fields)

    def _make_network_queue_binding_dict(self, queue, fields=None):
        res = {'network_id': queue['network_id'],
               'queue_id': queue['queue_id']}
        return db_utils.resource_fields(res, fields)

    def _check_for_queue_and_create(self, context, port):
        """Check for queue and create.

        This function determines if a port should be associated with a
        queue. It works by first querying NetworkQueueMapping to determine
        if the network is associated with a queue. If so, then it queries
        NetworkQueueMapping for all the networks that are associated with
        this queue. Next, it queries against all the ports on these networks
        with the port device_id. Finally it queries PortQueueMapping. If that
        query returns a queue_id that is returned. Otherwise a queue is
        created that is the size of the queue associated with the network and
        that queue_id is returned.

        If the network is not associated with a queue we then query to see
        if there is a default queue in the system. If so, a copy of that is
        created and the queue_id is returned.

        Otherwise None is returned. None is also returned if the port does not
        have a device_id or if the device_owner is network:
        """

        queue_to_create = None
        # If there is no device_id don't create a queue. The queue will be
        # created on update port when the device_id is present. Also don't
        # apply QoS to network ports.
        if (not port.get('device_id') or
            port['device_owner'].startswith('network:')):
            return

        # Check if there is a queue associated with the network
        filters = {'network_id': [port['network_id']]}
        network_queue_id = self._get_network_queue_bindings(
            context, filters, ['queue_id'])
        if network_queue_id:
            # get networks that queue is associated with
            filters = {'queue_id': [network_queue_id[0]['queue_id']]}
            networks_with_same_queue = self._get_network_queue_bindings(
                context, filters)

            # get the ports on these networks with the same_queue and device_id
            filters = {'device_id': [port.get('device_id')],
                       'network_id': [network['network_id'] for
                                      network in networks_with_same_queue]}
            query = model_query.query_with_hooks(context, models_v2.Port.id)
            model_query.apply_filters(query, models_v2.Port,
                                      filters, context)
            ports_ids = [p[0] for p in query]
            if ports_ids:
                # shared queue already exists find the queue id
                queues = self._get_port_queue_bindings(context,
                                                       {'port_id': ports_ids},
                                                       ['queue_id'])
                if queues:
                    return queues[0]['queue_id']

            # get the size of the queue we want to create
            queue_to_create = self.get_qos_queue(
                context, network_queue_id[0]['queue_id'])

        else:
            # check for default queue
            filters = {'default': [True]}
            # context is elevated since default queue is owned by admin
            queue_to_create = self.get_qos_queues(context.elevated(), filters)
            if not queue_to_create:
                return
            queue_to_create = queue_to_create[0]

        # create the queue
        tenant_id = port['tenant_id']
        if port.get(qos.RXTX_FACTOR) and queue_to_create.get('max'):
            queue_to_create['max'] = int(queue_to_create['max'] *
                                         port[qos.RXTX_FACTOR])
        queue = {'qos_queue': {'name': queue_to_create.get('name'),
                               'min': queue_to_create.get('min'),
                               'max': queue_to_create.get('max'),
                               'dscp': queue_to_create.get('dscp'),
                               'qos_marking':
                               queue_to_create.get('qos_marking'),
                               'tenant_id': tenant_id}}
        return self.create_qos_queue(context, queue, False)['id']

    def _validate_qos_queue(self, context, qos_queue):
        if qos_queue.get('default'):
            if context.is_admin:
                if self.get_qos_queues(context, filters={'default': [True]}):
                    raise qos.DefaultQueueAlreadyExists()
            else:
                raise qos.DefaultQueueCreateNotAdmin()
        if qos_queue.get('qos_marking') == 'trusted':
            dscp = qos_queue.pop('dscp')
            if dscp:
                # must raise because a non-zero dscp was provided
                raise qos.QueueInvalidMarking()
            LOG.info("DSCP value (%s) will be ignored with 'trusted' "
                     "marking", dscp)
        max = qos_queue.get('max')
        min = qos_queue.get('min')
        # Max can be None
        if max and min > max:
            raise qos.QueueMinGreaterMax()
