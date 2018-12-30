# -*- coding: utf-8 -*-
# Copyright: (c) 2018, Mikhail Yohman (@fragmentedpacket) <mikhail.yohman@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

ANSIBLE_METADATA = {"metadata_version": "1.1",
                    "status": ["preview"],
                    "supported_by": "community"}

DOCUMENTATION = r"""
---
module: netbox_prefix
short_description: Creates or removes prefixes from Netbox
description:
  - Creates or removes prefixes from Netbox
notes:
  - Tags should be defined as a YAML list
  - This should be ran with connection C(local) and hosts C(localhost)
author:
  - Mikhail Yohman (@FragmentedPacket)
requirements:
  - pynetbox
version_added: "2.8"
options:
  netbox_url:
    description:
      - URL of the Netbox instance resolvable by Ansible control host
    required: true
  netbox_token:
    description:
      - The token created within Netbox to authorize API access
    required: true
  data:
    description:
      - Defines the prefix configuration
    suboptions:
      family:
        description:
          - Specifies which address family the prefix prefix belongs to
        choices:
          - 4
          - 6
      prefix:
        description:
          - Required if state is C(present)
      site:
        description:
          - Site that prefix is associated with
      vrf:
        description:
          - VRF that prefix is associated with
      tenant:
        description:
          - The tenant that the prefix will be assigned to
      vlan:
        description:
          - The VLAN the prefix will be assigned to
      status:
        description:
          - The status of the prefix
        choices:
          - Active
          - Container
          - Deprecated
          - Reserved
      role:
        description:
          - The role of the prefix
      is_pool:
        description:
          - All IP Addresses within this prefix are considered usable
        type: bool
      description:
        description:
          - The description of the prefix
      tags:
        description:
          - Any tags that the prefix may need to be associated with
      custom_fields:
        description:
          - Must exist in Netbox and in key/value format
    required: true
  state:
    description:
      - Use C(present) or C(absent) for adding or removing.
    choices: [ absent, present ]
    default: present
  validate_certs:
    description:
      - If C(no), SSL certificates will not be validated. This should only be used on personally controlled sites using self-signed certificates.
    default: "yes"
    type: bool
"""

EXAMPLES = r"""
- name: "Test Netbox prefix module"
  connection: local
  hosts: localhost
  gather_facts: False
  tasks:
    - name: Create prefix within Netbox with only required information
      netbox_prefix:
        netbox_url: http://netbox.local
        netbox_token: thisIsMyToken
        data:
          prefix: 10.156.0.0/19
        state: present

    - name: Delete prefix within netbox
      netbox_prefix:
        netbox_url: http://netbox.local
        netbox_token: thisIsMyToken
        data:
          prefix: 10.156.0.0/19
        state: absent

    - name: Create prefix with several specified options
      netbox_prefix:
        netbox_url: http://netbox.local
        netbox_token: thisIsMyToken
        data:
          family: 4
          prefix: 10.156.32.0/19
          site: NOC - Test
          vrf: Guest
          tenant: Test Tenant
          vlan:
            name: Test VLAN
            site: Test Site
            tenant: Test Tenant
            vlan_group: Test Vlan Group
          status: Reserved
          role: Backup
          description: Test description
          is_pool: true
          tags:
            - Schnozzberry
        state: present

    - name: Remove prefix
      netbox_prefix:
        netbox_url: http://netbox.local
        netbox_token: thisIsMyToken
        data:
          prefix: 10.156.32.0/19
        state: absent
"""

RETURN = r"""
meta:
  description: Message indicating failure or success and returns results with the object created within Netbox
  returned: always
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.net_tools.netbox.netbox_utils import find_ids, normalize_data, PREFIX_STATUS
import json
try:
    import pynetbox
    HAS_PYNETBOX = True
except ImportError:
    HAS_PYNETBOX = False


def netbox_create_prefix(nb, nb_endpoint, data):
    result = {}
    prefix_list = data["prefix"].split('/')
    network = prefix_list[0]
    mask = prefix_list[1]
    if data.get("vrf"):
        norm_data = normalize_data(data)
        if norm_data.get("status"):
            norm_data["status"] = PREFIX_STATUS.get(norm_data["status"].lower())

        data = find_ids(nb, norm_data)

        if data.get("failed"):
            result.update(data)
            return result
        try:
            endpoint = nb_endpoint.get(q=network,mask_length=mask,vrf_id=data["vrf"])
        except ValueError:
            result.update({"failed": "Returned more than one result"})
            return result

        if not endpoint:
            try:
                resp = nb_endpoint.create(data)
                resp_ser = resp.serialize()
                result.update({'success': resp_ser})
            except pynetbox.RequestError as e:
                return json.loads(e.error)
        else:
            result.update({"failed": "%s already exists in Netbox" % (data["prefix"])})
    
    else:
        try:
            endpoint = nb_endpoint.get(q=network,mask_length=mask,vrf="null")
        except ValueError:
            result.update({"failed": "Returned more than one result. Try specifying VRF."})
            return result
        if not endpoint:
            norm_data = normalize_data(data)

            if norm_data.get("status"):
                norm_data["status"] = PREFIX_STATUS.get(norm_data["status"].lower())

            data = find_ids(nb, norm_data)

            if data.get("failed"):
                result.update(data)
                return result

            try:
                resp = nb_endpoint.create(data)
                resp_ser = resp.serialize()
                result.update({'success': resp_ser})
            except pynetbox.RequestError as e:
                return json.loads(e.error)
        else:
            result.update({"failed": "%s already exists in Netbox" % (data["prefix"])})

    return result


def netbox_delete_prefix(nb, nb_endpoint, data):
    norm_data = normalize_data(data)
    prefix_list = data["prefix"].split("/")
    network = prefix_list[0]
    mask = prefix_list[1]
    result = {}
    if data.get("vrf"):
        data = find_ids(nb, norm_data)
        try:
            endpoint = nb_endpoint.get(q=network,mask_length=mask,vrf_id=data["vrf"])
        except ValueError:
            result.update({"failed": "Returned more than one result"})
            return result

        try:
            if endpoint.delete():
                result.update({"success": "%s deleted from Netbox" % (norm_data["prefix"])})
        except AttributeError:
            result.update({"failed": "%s not found" % (norm_data["prefix"])})
    else:
        try:
            endpoint = nb_endpoint.get(q=network,mask_length=mask,vrf="null")
        except ValueError:
            result.update({"failed": "Returned more than one result. Try specifying VRF"})
            return result
        try:
            if endpoint.delete():
                result.update({"success": "%s deleted from Netbox" % (norm_data["prefix"])})
        except AttributeError:
            result.update({"failed": "%s not found" % (norm_data["prefix"])})
    return result


def main():
    """
    Main entry point for module execution
    """
    argument_spec = dict(
        netbox_url=dict(type="str", required=True),
        netbox_token=dict(type="str", required=True, no_log=True),
        data=dict(type="dict", required=True),
        state=dict(required=False, default="present", choices=["present", "absent"]),
        validate_certs=dict(type="bool", default=True)
    )
    module = AnsibleModule(argument_spec=argument_spec,
                           supports_check_mode=False)
    # Fail module if pynetbox is not installed
    if not HAS_PYNETBOX:
        module.fail_json(msg="pynetbox is required for this module")
    # Assign variables to be used with module
    changed = False
    app = "ipam"
    endpoint = "prefixes"
    url = module.params["netbox_url"]
    token = module.params["netbox_token"]
    data = module.params["data"]
    state = module.params["state"]
    validate_certs = module.params["validate_certs"]
    # Attempt to create Netbox API object
    try:
        nb = pynetbox.api(url, token=token, ssl_verify=validate_certs)
    except Exception:
        module.fail_json(msg="Failed to establish connection to Netbox API")
    try:
        nb_app = getattr(nb, app)
    except AttributeError:
        module.fail_json(msg="Incorrect application specified: %s" % (app))
    nb_endpoint = getattr(nb_app, endpoint)
    if "present" in state:
        response = netbox_create_prefix(nb, nb_endpoint, data)
        if response.get("success"):
            changed = True
    else:
        response = netbox_delete_prefix(nb, nb_endpoint, data)
        if response.get("success"):
            changed = True
    module.exit_json(changed=changed, meta=response)


if __name__ == "__main__":
    main()

