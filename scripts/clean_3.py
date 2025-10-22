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
    current_banner = None
    inside_banner = False

    for raw in lines:
        line = clean_line(raw)
        if not line:
            continue

        # hostname
        if re.match(r"^hostname\s+\S+", line):
            data["hostname"] = line.split()[1]
            continue

        # 版本号
        if re.match(r"^(version|ASA Version)\s+\S+", line):
            version = line.split(maxsplit=1)[1]
            data["version"] = version
            continue

        # ACL 规则
        if re.match(r"^access-list\s+", line):
            data["access_list"].append(line)
            continue

        # policy-map / class-map
        if re.match(r"^(policy-map|class-map)\b", line):
            if block_type and block_lines:
                data[block_type].append("\n".join(block_lines))
            block_type = "policy"
            block_lines = [line]
            continue

        # interface 块
        if re.match(r"^interface\s+\S+", line):
            if block_type and block_lines:
                data[block_type].append("\n".join(block_lines))
            block_type = "interfaces"
            block_lines = [line]
            continue

        # router ospf/bgp
        if re.match(r"^router\s+(ospf|bgp)\b", line, re.I):
            if block_type and block_lines:
                data[block_type].append("\n".join(block_lines))
            proto = re.findall(r"^router\s+(\S+)", line, re.I)[0].lower()
            block_type = f"router_{proto}"
            block_lines = [line]
            continue

        # banner（例如 ASA 或 Catalyst）
        if line.lower().startswith("banner "):
            inside_banner = True
            current_banner = [line]
            continue

        if inside_banner:
            current_banner.append(line)
            if line.strip().endswith("^C"):
                inside_banner = False
                data["banner"].append("\n".join(current_banner))
                current_banner = None
            continue

        # MPLS
        if re.match(r"^mpls\s+", line):
            if block_type and block_lines:
                data[block_type].append("\n".join(block_lines))
            block_type = "mpls"
            block_lines = [line]
            continue

        # VRF
        if re.match(r"^ip vrf\s+", line):
            if block_type and block_lines:
                data[block_type].append("\n".join(block_lines))
            block_type = "vrf"
            block_lines = [line]
            continue

        # 段落结束 (! 或 end)
        if line.strip() in ("!", "end"):
            if block_type and block_lines:
                data[block_type].append("\n".join(block_lines))
                block_type = None
                block_lines = []
            continue

        # 当前块内内容
        if block_type:
            block_lines.append(line)
        else:
            # 顶层配置（非块）
            data["global"].append(line)

    # 提交最后的块
    if block_type and block_lines:
        data[block_type].append("\n".join(block_lines))

    return dict(data)


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
