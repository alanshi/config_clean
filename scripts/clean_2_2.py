import os
import re
import json
from collections import defaultdict


def clean_line(line: str):
    line = line.strip()
    if not line or line.startswith("#") or line.startswith("*"):
        return ""
    return line


def detect_vendor(lines):
    text = "\n".join(lines[:30])
    if "config system global" in text:
        return "fortinet"
    elif re.search(r"^set (interface|clienv|deviceconfig)", text, re.M):
        return "checkpoint" if "set hostname" in text else "paloalto"
    elif "host-name" in text or "interfaces {" in text:
        return "juniper"
    elif re.search(r"^hostname\s+\S+", text, re.M):
        return "cisco"
    elif "deviceconfig {" in text or "set deviceconfig" in text:
        return "paloalto"
    else:
        return "unknown"


# ------------------ Cisco ------------------
def parse_cisco(lines):
    data = defaultdict(list)
    data["global"] = []
    block_type = None
    block_lines = []

    for raw in lines:
        line = clean_line(raw)
        if not line:
            continue
        if re.match(r"^hostname\s+\S+", line):
            data["hostname"] = line.split()[1]
            continue
        if re.match(r"^version\s+\S+", line):
            data["version"] = line.split()[1]
            continue
        if re.match(r"^interface\s+\S+", line):
            if block_type and block_lines:
                data[block_type].append("\n".join(block_lines))
            block_type = "interfaces"
            block_lines = [line]
            continue
        if re.match(r"^router\s+(ospf|bgp)\b", line, re.I):
            if block_type and block_lines:
                data[block_type].append("\n".join(block_lines))
            proto = re.findall(r"^router\s+(\S+)", line, re.I)[0].lower()
            block_type = f"router_{proto}"
            block_lines = [line]
            continue
        if re.match(r"^mpls\s+", line):
            if block_type and block_lines:
                data[block_type].append("\n".join(block_lines))
            block_type = "mpls"
            block_lines = [line]
            continue
        if re.match(r"^(ip vrf|address-family)\b", line, re.I):
            if block_type and block_lines:
                data[block_type].append("\n".join(block_lines))
            block_type = "vrf"
            block_lines = [line]
            continue
        if line.lower().startswith("access-list"):
            data["access_list"].append(line)
            continue
        if line in ("!", "end"):
            if block_type and block_lines:
                data[block_type].append("\n".join(block_lines))
                block_type = None
                block_lines = []
            continue
        if block_type:
            block_lines.append(line)
        else:
            data["global"].append(line)

    if block_type and block_lines:
        data[block_type].append("\n".join(block_lines))

    return dict(data)


# ------------------ Fortinet ------------------
def parse_fortinet(lines):
    data = defaultdict(list)
    data["global"] = []
    current_block = None
    temp_lines = []
    for raw in lines:
        line = clean_line(raw)
        if not line:
            continue
        if line.startswith("config "):
            current_block = line
            temp_lines = []
        elif line.startswith("edit "):
            temp_lines = [line]
        elif line == "next":
            if current_block:
                data[current_block].append("\n".join(temp_lines))
            temp_lines = []
        elif line == "end":
            if current_block and temp_lines:
                data[current_block].append("\n".join(temp_lines))
            current_block = None
        elif line.startswith("set hostname"):
            hostname = re.findall(r'set hostname "?([\w\-]+)"?', line)
            if hostname:
                data["hostname"] = hostname[0]
        elif current_block:
            temp_lines.append(line)
        else:
            data["global"].append(line)
    return dict(data)


# ------------------ CheckPoint ------------------
def parse_checkpoint(lines):
    data = defaultdict(list)
    data["global"] = []
    for raw in lines:
        line = clean_line(raw)
        if not line:
            continue
        if line.startswith("set hostname"):
            data["hostname"] = line.split("set hostname")[1].strip()
        elif line.startswith("set interface"):
            data["interfaces"].append(line)
        elif line.startswith("set bgp"):
            data["router_bgp"].append(line)
        elif line.startswith("set ospf"):
            data["router_ospf"].append(line)
        elif line.startswith("set as "):
            data["as"] = line.split("set as")[1].strip()
        elif line.startswith("set router-id"):
            data["router_id"] = line.split("set router-id")[1].strip()
        else:
            data["global"].append(line)
    return dict(data)


# ------------------ Juniper ------------------
def parse_juniper(lines):
    data = defaultdict(list)
    data["global"] = []
    current_block = None
    block_lines = []

    def commit_block(block_type, lines_list):
        if block_type and lines_list:
            data[block_type].append("\n".join(lines_list))

    for raw in lines:
        line = clean_line(raw)
        if not line:
            continue

        # version
        if line.startswith("version"):
            data["version"] = line.split()[1].rstrip(";")
            continue

        # hostname
        if "host-name" in line:
            hostname = line.split("host-name")[1].strip("; ")
            data["hostname"] = hostname
            continue

        # interface 块
        m_intf = re.match(r"(\S+)\s*{", line)
        if m_intf and m_intf.group(1).startswith(("ge-", "lo", "xe", "et")):
            commit_block(current_block, block_lines)
            current_block = "interfaces"
            block_lines = [f"interface {m_intf.group(1)}"]
            continue

        # routing-options / BGP / OSPF
        if line.startswith("autonomous-system"):
            commit_block(current_block, block_lines)
            current_block = "router_bgp"
            block_lines = [f"router bgp {line.split()[1].rstrip(';')}"]
            continue
        if line.startswith("router-id"):
            block_lines.append(f"bgp router-id {line.split()[1].rstrip(';')}")
            continue
        if line.startswith("local-address"):
            block_lines.append(f"neighbor {line.split()[1].rstrip(';')} local-address")
            continue
        if line.startswith("peer-as"):
            block_lines.append(f"neighbor peer-as {line.split()[1].rstrip(';')}")
            continue

        # OSPF area
        if line.startswith("area"):
            commit_block(current_block, block_lines)
            current_block = "router_ospf"
            block_lines = [f"router ospf {line.split()[1].rstrip(';')}"]
            continue

        # VRF / address-family
        if line.startswith("address-family"):
            commit_block(current_block, block_lines)
            current_block = "vrf"
            block_lines = [line.rstrip(";")]
            continue
        if current_block == "vrf":
            block_lines.append(line.rstrip(";"))
            if line.startswith("exit-address-family"):
                commit_block(current_block, block_lines)
                current_block = None
                block_lines = []
            continue

        # interface内部内容
        if current_block == "interfaces":
            if line.endswith("{") or line.endswith("}"):
                continue
            block_lines.append(line.rstrip(";"))
        else:
            data["global"].append(line)

    commit_block(current_block, block_lines)
    data["vendor"] = "juniper"
    return dict(data)


# ------------------ PaloAlto ------------------
def parse_paloalto(lines):
    data = defaultdict(list)
    data["global"] = []
    key_stack = []
    current_block = None
    bgp_group = None

    for line in lines:
        line = clean_line(line)
        if not line:
            continue
        # hostname
        if "hostname" in line:
            m = re.findall(r"hostname\s+([\w\-]+);?", line)
            if m:
                data["hostname"] = m[0]
            continue
        # block start
        if line.endswith("{"):
            key_stack.append(line[:-1].strip())
            current_block = " > ".join(key_stack)
            continue
        elif line == "}":
            if bgp_group:
                data["router_bgp"].append(bgp_group)
                bgp_group = None
            if key_stack:
                key_stack.pop()
            current_block = " > ".join(key_stack)
            continue
        # interfaces
        if "ethernet" in current_block and "ip" in line:
            ip = re.findall(r"(\d+\.\d+\.\d+\.\d+/\d+)", line)
            if ip:
                data["interfaces"].append(f"{current_block} {ip[0]}")
            continue
        # OSPF
        if current_block.startswith("protocol ospf") or "protocols > ospf" in current_block:
            data["router_ospf"].append(line)
            continue
        # BGP
        if current_block.startswith("protocol bgp") or "protocols > bgp" in current_block:
            m_group = re.match(r"peer-group\s+(\S+)\s*{", line)
            if m_group:
                if bgp_group:
                    data["router_bgp"].append(bgp_group)
                bgp_group = {"group": m_group.group(1)}
                continue
            if bgp_group:
                if "local-as" in line:
                    bgp_group["local-as"] = int(re.findall(r"local-as\s+(\d+);?", line)[0])
                elif "peer" in line:
                    peer = re.findall(r"peer\s+(\S+)\s*{", line)
                    if peer:
                        bgp_group.setdefault("peers", {})[peer[0]] = {}
            continue
        # fallback
        data["global"].append(line)
    if bgp_group:
        data["router_bgp"].append(bgp_group)
    return dict(data)


# ------------------ 通用入口 ------------------
def parse_config_file(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = [line.rstrip() for line in f if line.strip()]

    vendor = detect_vendor(lines)
    if vendor == "cisco":
        result = parse_cisco(lines)
    elif vendor == "fortinet":
        result = parse_fortinet(lines)
    elif vendor == "checkpoint":
        result = parse_checkpoint(lines)
    elif vendor == "juniper":
        result = parse_juniper(lines)
    elif vendor == "paloalto":
        result = parse_paloalto(lines)
    else:
        result = {"unknown_format": True, "global": lines}

    result["vendor"] = vendor
    return result


def parse_multiple_configs(folder_path, output_json="configs_summary.json"):
    results = {}
    for root, _, files in os.walk(folder_path):
        for f in files:
            if f.endswith((".cfg", ".conf", ".txt")):
                path = os.path.join(root, f)
                try:
                    data = parse_config_file(path)
                    results[f] = data
                except Exception as e:
                    print(f"解析 {f} 失败: {e}")

    with open(output_json, "w", encoding="utf-8") as out:
        json.dump(results, out, indent=4, ensure_ascii=False)

    print(f"已完成解析，结果写入 {output_json}")


if __name__ == "__main__":
    folder = "./configs"
    parse_multiple_configs(folder)
