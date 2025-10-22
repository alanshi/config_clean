import os
import re
import json
from collections import defaultdict


# ------------------ 基础函数 ------------------

def clean_line(line: str):
    """清洗一行文本（保留Cisco分段!）"""
    line = line.rstrip()
    # 跳过注释行
    if not line or line.strip().startswith(("#", "*")):
        return ''
    return line


def detect_vendor(lines):
    """根据关键字检测配置厂商"""
    text = "\n".join(lines[:50])
    if "config system global" in text:
        return "fortinet"
    elif re.search(r"^set (interface|clienv)", text, re.M):
        return "checkpoint"
    elif "host-name" in text or "interfaces {" in text:
        return "juniper"
    elif re.search(r"ASA Version", text, re.I):
        return "cisco_asa"
    elif re.search(r"^hostname\s+\S+", text, re.M):
        return "cisco"
    else:
        return "unknown"


# ------------------ Cisco (含 IOS / NX-OS / Catalyst / ASA) ------------------

def parse_cisco(lines):
    data = defaultdict(list)
    block_type = None
    block_lines = []
    bgp_blocks = []

    for raw in lines:
        line = clean_line(raw)
        if not line:
            continue

        # hostname
        if re.match(r"^hostname\s+\S+", line):
            data["hostname"] = line.split()[1]
            continue

        # 版本号
        if re.match(r"^(ASA\s+Version|version)\s+\S+", line):
            version = line.split()[-1]
            data["version"] = version
            continue

        # interface 块
        if re.match(r"^interface\s+\S+", line):
            if block_type and block_lines:
                data[block_type].append("\n".join(block_lines))
            block_type = "interfaces"
            block_lines = [line]
            continue

        # router bgp 块
        if re.match(r"^router\s+bgp\s+\d+", line, re.I):
            if block_type and block_lines:
                data[block_type].append("\n".join(block_lines))
            block_type = "router_bgp"
            block_lines = [line]
            continue

        # router ospf 块
        if re.match(r"^router\s+ospf\s+\d+", line, re.I):
            if block_type and block_lines:
                data[block_type].append("\n".join(block_lines))
            block_type = "router_ospf"
            block_lines = [line]
            continue

        # 其他类型块（如policy-map、class-map等）
        if re.match(r"^(policy-map|class-map|service-policy)\s+", line):
            if block_type and block_lines:
                data[block_type].append("\n".join(block_lines))
            block_type = line.split()[0]
            block_lines = [line]
            continue

        # 段落结束
        if line.strip() in ("!", "end"):
            if block_type and block_lines:
                block_content = "\n".join(block_lines)
                if block_type == "router_bgp":
                    bgp_info = parse_bgp_block(block_content)
                    bgp_blocks.append(bgp_info)
                else:
                    data[block_type].append(block_content)
                block_type = None
                block_lines = []
            continue

        # 当前块内内容
        if block_type:
            block_lines.append(line)

    # 最后块提交
    if block_type and block_lines:
        block_content = "\n".join(block_lines)
        if block_type == "router_bgp":
            bgp_info = parse_bgp_block(block_content)
            bgp_blocks.append(bgp_info)
        else:
            data[block_type].append(block_content)

    if bgp_blocks:
        data["bgp_details"] = bgp_blocks

    return dict(data)


def parse_bgp_block(block_text: str):
    """解析 router bgp 块，提取AS号、router-id、neighbor、address-family"""
    bgp_data = {"neighbors": [], "address_family": {}}
    lines = block_text.splitlines()
    header = lines[0]

    # 提取 autonomous-system
    match_as = re.search(r"router\s+bgp\s+(\d+)", header, re.I)
    if match_as:
        bgp_data["autonomous_system"] = match_as.group(1)

    current_af = None
    af_lines = []

    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        # router-id
        if re.match(r"bgp\s+router-id\s+", line):
            bgp_data["router_id"] = line.split()[-1]
        # neighbor
        elif re.match(r"neighbor\s+\S+", line):
            bgp_data["neighbors"].append(line)
        # address-family 开始
        elif line.startswith("address-family "):
            current_af = line.split("address-family ")[1]
            af_lines = []
        # 退出 address-family
        elif line.startswith("exit-address-family"):
            if current_af:
                bgp_data["address_family"][current_af] = af_lines[:]
                current_af = None
        # address-family 内容
        elif current_af:
            af_lines.append(line)
        # 其他配置
        elif line.lower().startswith("bgp "):
            bgp_data.setdefault("bgp_settings", []).append(line)
        else:
            bgp_data.setdefault("misc", []).append(line)

    return bgp_data


# ------------------ Fortinet ------------------

def parse_fortinet(lines):
    data = defaultdict(list)
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

    return dict(data)


# ------------------ Checkpoint ------------------

def parse_checkpoint(lines):
    data = defaultdict(list)
    for raw in lines:
        line = clean_line(raw)
        if not line:
            continue

        if line.startswith("set hostname"):
            data["hostname"] = line.split("set hostname")[1].strip()
        elif line.startswith("set interface"):
            data["interfaces"].append(line)
        elif line.startswith("set bgp"):
            data["bgp"].append(line)
        elif line.startswith("set ospf"):
            data["ospf"].append(line)
        elif line.startswith("set as "):
            data["as"] = line.split("set as")[1].strip()
        elif line.startswith("set router-id"):
            data["router_id"] = line.split("set router-id")[1].strip()
    return dict(data)


# ------------------ Juniper ------------------

def parse_juniper(lines):
    data = defaultdict(list)
    key_stack = []

    for raw in lines:
        line = clean_line(raw)
        if not line:
            continue

        if line.startswith("version"):
            data["version"] = line.split("version")[1].strip("; ")
        elif "host-name" in line:
            hostname = line.split("host-name")[1].strip("; ")
            data["hostname"] = hostname
        elif line.endswith("{"):
            key_stack.append(line.split("{")[0].strip())
        elif line == "}":
            if key_stack:
                key_stack.pop()
        else:
            path = " > ".join(key_stack)
            if path.startswith("interfaces"):
                data["interfaces"].append(line)
            elif path.startswith("protocols ospf"):
                data["ospf"].append(line)
            elif path.startswith("protocols bgp"):
                data["bgp"].append(line)
            elif path.startswith("system"):
                data["system"].append(line)
            elif path.startswith("routing-options"):
                data["routing"].append(line)
    return dict(data)


# ------------------ 统一入口 ------------------

def parse_config_file(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    vendor = detect_vendor(lines)

    if vendor in ("cisco", "cisco_asa"):
        result = parse_cisco(lines)
    elif vendor == "fortinet":
        result = parse_fortinet(lines)
    elif vendor == "checkpoint":
        result = parse_checkpoint(lines)
    elif vendor == "juniper":
        result = parse_juniper(lines)
    else:
        result = {"unknown_format": True}

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
                    print(f"⚠️ 解析 {f} 失败: {e}")
    with open(output_json, "w", encoding="utf-8") as out:
        json.dump(results, out, indent=4, ensure_ascii=False)
    print(f"✅ 已完成解析，结果写入 {output_json}")


# 示例用法
if __name__ == "__main__":
    folder = "./configs"
    parse_multiple_configs(folder)
