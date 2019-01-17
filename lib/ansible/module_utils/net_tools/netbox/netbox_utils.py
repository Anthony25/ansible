# -*- coding: utf-8 -*-
# Copyright: (c) 2018, Mikhail Yohman (@fragmentedpacket) <mikhail.yohman@gmail.com>
# Copyright: (c) 2018, David Gomez (@amb1s1) <david.gomez@networktocode.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

__metaclass__ = type

API_APPS_ENDPOINTS = dict(
    circuits=[],
    dcim=["device_roles", "device_types", "devices", "interfaces", "platforms", "racks", "sites"],
    extras=[],
    ipam=["ip_addresses", "prefixes", "roles", "vlans", "vlan_grups", "vrfs"],
    secrets=[],
    tenancy=["tenants", "tenant_groups"],
    virtualization=["clusters"]
)

QUERY_TYPES = dict(
    cluster="name",
    device_role="slug",
    device_type="slug",
    manufacturer="slug",
    nat_inside="address",
    nat_outside="address",
    platform="slug",
    primary_ip="address",
    primary_ip4="address",
    primary_ip6="address",
    rack="slug",
    region="slug",
    role="slug",
    site="slug",
    tenant="slug",
    tenant_group="slug",
    vlan="name",
    vlan_group="slug",
    vrf="name"
)

CONVERT_TO_ID = dict(
    cluster="clusters",
    device_role="device_roles",
    device_type="device_types",
    interface="interfaces",
    nat_inside="ip_addresses",
    nat_outside="ip_addresses",
    platform="platforms",
    primary_ip="ip_addresses",
    primary_ip4="ip_addresses",
    primary_ip6="ip_addresses",
    rack="racks",
    role="roles",
    site="sites",
    tenant="tenants",
    tenant_group="tenant_groups",
    vlan="vlans",
    vlan_group="vlan_groups",
    vrf="vrfs"
)

FACE_ID = dict(
    front=0,
    rear=1
)

NO_DEFAULT_ID = set([
    "primary_ip",
    "primary_ip4",
    "primary_ip6",
    "role",
    "vlan",
    "vrf",
    "nat_inside",
    "nat_outside"
])

DEVICE_STATUS = dict(
    offline=0,
    active=1,
    planned=2,
    staged=3,
    failed=4,
    inventory=5
)

IP_ADDRESS_STATUS = dict(
    active=1,
    reserved=2,
    deprecated=3,
    dhcp=5
)

IP_ADDRESS_ROLE = dict(
    loopback=10,
    secondary=20,
    anycast=30,
    vip=40,
    vrrp=41,
    hsrp=42,
    glbp=43,
    carp=44
)

PREFIX_STATUS = dict(
    container=0,
    active=1,
    reserved=2,
    deprecated=3
)

VLAN_STATUS = dict(
    active=1,
    reserved=2,
    deprecated=3
)


def find_app(endpoint):
    for k, v in API_APPS_ENDPOINTS.items():
        if endpoint in v:
            nb_app = k
    return nb_app


def find_ids(nb, data):
    for k, v in data.items():
        if k in CONVERT_TO_ID:
            endpoint = CONVERT_TO_ID[k]
            search = v
            app = find_app(endpoint)
            nb_app = getattr(nb, app)
            nb_endpoint = getattr(nb_app, endpoint)

            if k == "interface":
                query_id = nb_endpoint.get(**{"name": v["name"], "device": v["device"]})
            elif k == "nat_inside":
                if v.get("vrf"):
                    vrf_id = nb.ipam.vrfs.get(**{"name": v["vrf"]})
                    if vrf_id:
                        query_id = nb_endpoint.get(**{"address": v["address"], "vrf_id": vrf_id.id})
                    else:
                        raise ValueError("%s does not exist - Please create VRF" % (data["vrf"]))
                else:
                    try:
                        query_id = nb_endpoint.get(**{"address": v["address"]})
                    except ValueError:
                        raise ValueError("Multiple results found while searching for %s: %s - Specify a VRF within %s" % (k, v["address"], k))
            elif k == "vlan":
                vlan_dict = {}
                if v.get("name"):
                    vlan_dict.update({"name": v["name"]})
                if v.get("site"):
                    site_id = nb.dcim.sites.get(**{"slug": v["site"]})
                    try:
                        vlan_dict.update({"site_id": site_id.id})
                    except AttributeError:
                        return AttributeError("Did not find any results for site")
                if v.get("vlan_group"):
                    vlan_group_id = nb.ipam.vlan_groups.get(**{"slug": v["vlan_group"]})
                    try:
                        vlan_dict.update({"group_id": vlan_group_id.id})
                    except AttributeError:
                        return AttributeError("Did not find any results for vlan_group")
                if v.get("tenant"):
                    tenant_id = nb.tenancy.tenants.get(**{"slug": v["tenant"]})
                    try:
                        vlan_dict.update({"tenant_id": tenant_id.id})
                    except AttributeError:
                        return AttributeError("Did not find any results for tenant")

                try:
                    query_id = nb_endpoint.get(**vlan_dict)
                except ValueError:
                    return ValueError("Multiple results found while searching for key: %s" % (k))

            else:
                try:
                    query_id = nb_endpoint.get(**{QUERY_TYPES.get(k, "q"): search})
                except ValueError:
                    return ValueError("Multiple results found while searching for key: %s" % (k))

            if query_id:
                data[k] = query_id.id
            elif k in NO_DEFAULT_ID:
                pass
            else:
                data[k] = 1

    return data


def normalize_data(data):
    for k, v in data.items():
        if isinstance(v, dict):
            for subk, subv in v.items():
                sub_data_type = QUERY_TYPES.get(subk, "q")
                if sub_data_type == "slug":
                    if "-" in subv:
                        data[k][subk] = subv.replace(" ", "").lower()
                    elif " " in subv:
                        data[k][subk] = subv.replace(" ", "-").lower()
                    else:
                        data[k][subk] = subv.lower()
        else:
            data_type = QUERY_TYPES.get(k, "q")
            if data_type == "slug":
                if "-" in v:
                    data[k] = v.replace(" ", "").lower()
                elif " " in v:
                    data[k] = v.replace(" ", "-").lower()
                else:
                    data[k] = v.lower()
    return data
