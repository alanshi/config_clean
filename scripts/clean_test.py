import json
import re

# 读取完整配置文件
with open("configs/S4-7609.cfg") as f:
    config_text = f.read()

# 输出结构化数据
output = {
    "interfaces": [],
    "ospf": [],
    "bgp": []
}


# -----------------------------
# 接口解析
# -----------------------------
iface_blocks = re.findall(r"(?ms)^interface\s+(\S+)(.*?)(?=^!|\Z)", config_text)
for name, block in iface_blocks:
    iface = {"name": name, "desc": "", "ip": "", "mask": "", "state": ""}
    m = re.search(r"^\s*description\s+(.+)", block, re.MULTILINE)
    if m:
        iface["desc"] = m.group(1)
    m = re.search(r"^\s*ip address (\d+\.\d+\.\d+\.\d+) (\d+\.\d+\.\d+\.\d+)", block, re.MULTILINE)
    if m:
        iface["ip"] = m.group(1)
        iface["mask"] = m.group(2)
    m = re.search(r"^\s*(shutdown|no shutdown)", block, re.MULTILINE)
    if m:
        iface["state"] = m.group(1)
    output["interfaces"].append(iface)

# -----------------------------
# OSPF解析
# -----------------------------
ospf_blocks = re.findall(r"(?ms)^router ospf (\d+)(.*?)(?=^!|\Z)", config_text)
for ospf_id, block in ospf_blocks:
    ospf = {"ospf_id": ospf_id, "router_id": "", "networks": []}
    m = re.search(r"^\s*router-id (\d+\.\d+\.\d+\.\d+)", block, re.MULTILINE)
    if m:
        ospf["router_id"] = m.group(1)
    nets = re.findall(r"^\s*network (\d+\.\d+\.\d+\.\d+) (\d+\.\d+\.\d+\.\d+) area (\d+)", block, re.MULTILINE)
    for n in nets:
        ospf["networks"].append({"network": n[0], "wildcard": n[1], "area": n[2]})
    output["ospf"].append(ospf)

# -----------------------------
# BGP解析，支持多address-family和VRF
# -----------------------------
bgp_blocks = re.findall(r"(?ms)^router bgp (\d+)(.*?)(?=^!|\Z)", config_text)
for bgp_as, block in bgp_blocks:
    bgp = {"as": bgp_as, "router_id": "", "neighbors": []}

    # router-id
    m = re.search(r"^\s*bgp router-id (\d+\.\d+\.\d+\.\d+)", block, re.MULTILINE)
    if m:
        bgp["router_id"] = m.group(1)

    # 解析 address-family/VRF块
    af_blocks = re.findall(r"(?ms)^ address-family (\S+)(.*?)(?=^!|\Z)", block)
    for afi, af_block in af_blocks:
        # 如果是 vrf
        vrf_match = re.match(r"(\S+)\s+vrf\s+(\S+)", afi)
        if vrf_match:
            afi_type = vrf_match.group(1)
            vrf = vrf_match.group(2)
        else:
            afi_type = afi
            vrf = None

        # neighbor remote-as
        neigh_blocks = re.findall(
            r"^\s*neighbor (\d+\.\d+\.\d+\.\d+)\s+remote-as\s+(\d+)", af_block, re.MULTILINE
        )
        for n_ip, n_as in neigh_blocks:
            # neighbor update-source
            us_match = re.search(
                rf"^\s*neighbor {re.escape(n_ip)}\s+update-source (\S+)", af_block, re.MULTILINE
            )
            update_source = us_match.group(1) if us_match else None

            bgp["neighbors"].append({
                "neighbor": n_ip,
                "remote_as": n_as,
                "update_source": update_source,
                "address_family": afi_type,
                "vrf": vrf
            })
    output["bgp"].append(bgp)

# -----------------------------
# 输出 JSON
# -----------------------------
print(json.dumps(output, indent=4))