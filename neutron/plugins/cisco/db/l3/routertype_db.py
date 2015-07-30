# Copyright 2014 Cisco Systems, Inc.  All rights reserved.
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

from oslo_config import cfg
from oslo_db import exception as db_exc
from oslo_log import log as logging
from oslo_utils import excutils
from sqlalchemy import exc as sql_exc
from sqlalchemy.orm import exc

from neutron.i18n import _LE
from neutron.openstack.common import uuidutils
from neutron.plugins.cisco.db.l3 import l3_models
import neutron.plugins.cisco.extensions.routertype as routertype
from neutron.plugins.cisco.common import cisco_constants

LOG = logging.getLogger(__name__)


class RoutertypeDbMixin(routertype.RoutertypePluginBase):
    """Mixin class for Router types."""

    def create_routertype(self, context, routertype):
        """Creates a router type.

        Also binds it to the specified hosting device template.
        """
        LOG.debug("create_routertype() called. Contents %s", routertype)
        rt = routertype['routertype']
        tenant_id = self._get_tenant_id_for_create(context, rt)
        with context.session.begin(subtransactions=True):
            routertype_db = l3_models.RouterType(
                id=self._get_id(rt),
                tenant_id=tenant_id,
                name=rt['name'],
                description=rt['description'],
                template_id=rt['template_id'],
                shared=rt['shared'],
                slot_need=rt['slot_need'],
                scheduler=rt['scheduler'],
                driver=rt['driver'],
                cfg_agent_service_helper=rt['cfg_agent_service_helper'],
                cfg_agent_driver=rt['cfg_agent_driver'])
            context.session.add(routertype_db)
        return self._make_routertype_dict(routertype_db)

    def update_routertype(self, context, id, routertype):
        LOG.debug("update_routertype() called")
        rt = routertype['routertype']
        with context.session.begin(subtransactions=True):
            rt_query = context.session.query(l3_models.RouterType)
            if not rt_query.filter_by(id=id).update(rt):
                raise routertype.RouterTypeNotFound(id=id)
        return self.get_routertype(context, id)

    def delete_routertype(self, context, id):
        LOG.debug("delete_routertype() called")
        try:
            with context.session.begin(subtransactions=True):                
                routertype_query = context.session.query(l3_models.RouterType)
                routertype_query = routertype_query.filter_by(id=id)
                if not routertype_query:
                    raise routertype.RouterTypeNotFound(id=id)
                else:
                    if cfg.CONF.routing.hardware_router_type_name == \
                       routertype_query.first().name:
                        router_query = context.session.query(l3_models.RouterHostingDeviceBinding)
                        router_query.filter_by(router_type_id=id)
                        global_ids = []
                        if router_query:
                            for router in router_query:
                                if router.role != cisco_constants.ROUTER_ROLE_GLOBAL and \
                                   router.role != cisco_constants.ROUTER_ROLE_LOGICAL_GLOBAL:
                                    raise routertype.RouterTypeInUse(id=id)
                                else:
                                    global_ids.append(router.router_id)

                            for router_id in global_ids:
                                self.delete_router(context, router_id)
                                        
                routertype_query.delete()
                                            
                #if not routertype_query.filter_by(id=id).delete():
                #    raise routertype.RouterTypeNotFound(id=id)
        except db_exc.DBError as e:
            with excutils.save_and_reraise_exception() as ctxt:
                if isinstance(e.inner_exception, sql_exc.IntegrityError):
                    ctxt.reraise = False
                    raise routertype.RouterTypeInUse(id=id)

    def get_routertype(self, context, id, fields=None):
        LOG.debug("get_routertype() called")
        rt_db = self._get_routertype(context, id)
        return self._make_routertype_dict(rt_db, fields)

    def get_routertypes(self, context, filters=None, fields=None,
                        sorts=None, limit=None, marker=None,
                        page_reverse=False):
        LOG.debug("get_routertypes() called")
        return self._get_collection(context, l3_models.RouterType,
                                    self._make_routertype_dict,
                                    filters=filters, fields=fields,
                                    sorts=sorts, limit=limit,
                                    marker_obj=marker,
                                    page_reverse=page_reverse)

    def get_routertype_by_id_name(self, context, id_or_name):
        query = context.session.query(l3_models.RouterType)
        # for q_obj in query:
        #     LOG.debug("ROUTERTYPE QUERY, OBJ: %s" % q_obj)
        query = query.filter(l3_models.RouterType.id == id_or_name)
        try:
            return query.one()
        except exc.MultipleResultsFound:
            with excutils.save_and_reraise_exception():
                LOG.error(_LE('Database inconsistency: Multiple router types '
                              'with same id %s'), id_or_name)
                raise routertype.RouterTypeNotFound(router_type=id_or_name)
        except exc.NoResultFound:
            query = context.session.query(l3_models.RouterType)
            query = query.filter(l3_models.RouterType.name == id_or_name)
            try:
                return query.one()
            except exc.MultipleResultsFound:
                with excutils.save_and_reraise_exception():
                    LOG.debug('Multiple router types with name %s found. '
                              'Id must be specified to allow arbitration.',
                              id_or_name)
                    raise routertype.MultipleRouterTypes(name=id_or_name)
            except exc.NoResultFound:
                with excutils.save_and_reraise_exception():
                    LOG.error(_LE('No router type with name %s found.'),
                              id_or_name)
                    raise routertype.RouterTypeNotFound(id=id_or_name)

    def _get_routertype(self, context, id):
        try:
            return self._get_by_id(context, l3_models.RouterType, id)
        except exc.NoResultFound:
            raise routertype.RouterTypeNotFound(id=id)

    def _make_routertype_dict(self, routertype, fields=None):
        res = {'id': routertype['id'],
               'tenant_id': routertype['tenant_id'],
               'name': routertype['name'],
               'description': routertype['description'],
               'template_id': routertype['template_id'],
               'shared': routertype['shared'],
               'slot_need': routertype['slot_need'],
               'scheduler': routertype['scheduler'],
               'driver': routertype['driver'],
               'cfg_agent_service_helper': routertype[
                   'cfg_agent_service_helper'],
               'cfg_agent_driver': routertype['cfg_agent_driver']}
        return self._fields(res, fields)

    def _get_id(self, res):
        uuid = res.get('id')
        if uuid:
            return uuid
        return uuidutils.generate_uuid()
