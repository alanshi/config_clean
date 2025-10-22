import os
import re
import json
from collections import defaultdict


def parse_config_file(file_path):
    """
    通用网络配置文件解析器：
    兼容 Cisco / Juniper / PaloAlto / Fortinet / CheckPoint
    输出结构化 JSON
    """

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]

    config_data = defaultdict(list)
    current_block = None
    block_lines = []

    def commit_block(block_type, block_data):
        """将当前区块内容存入结果"""
        if block_type and block_data.strip():
            config_data[block_type].append(block_data.strip())

    for line in lines:
        # 跳过注释
        if line.startswith('#') or line.startswith('*'):
            continue

        # ========== 通用 hostname ==========
        if re.match(r"^(hostname|set hostname|set deviceconfig system hostname|host-name)\b", line, re.I):
            hostname = line.split()[-1].strip('"')
            config_data["hostname"] = hostname
            continue
        if re.match(r"^config system global", line, re.I):
            current_block = "system"
            block_lines = [line]
            continue

        # ========== Cisco 风格 ==========
        if re.match(r"^interface\s+\S+", line, re.I):
            commit_block(current_block, "\n".join(block_lines))
            current_block = "interfaces"
            block_lines = [line]
            continue
        if re.match(r"^router\s+(ospf|bgp)\b", line, re.I):
            commit_block(current_block, "\n".join(block_lines))
            proto = re.findall(r"^router\s+(\S+)", line, re.I)[0].lower()
            current_block = f"router_{proto}"
            block_lines = [line]
            continue
        if line.lower().startswith("mpls"):
            commit_block(current_block, "\n".join(block_lines))
            current_block = "mpls"
            block_lines = [line]
            continue
        if re.match(r"^(address-family|vpn)\b", line, re.I):
            commit_block(current_block, "\n".join(block_lines))
            current_block = "vpn"
            block_lines = [line]
            continue

        # ========== Fortinet 风格 ==========
        if re.match(r"^config\s+system\s+interface", line, re.I):
            commit_block(current_block, "\n".join(block_lines))
            current_block = "interfaces"
            block_lines = [line]
            continue
        if re.match(r"^config\s+router\s+ospf", line, re.I):
            commit_block(current_block, "\n".join(block_lines))
            current_block = "router_ospf"
            block_lines = [line]
            continue
        if re.match(r"^config\s+router\s+bgp", line, re.I):
            commit_block(current_block, "\n".join(block_lines))
            current_block = "router_bgp"
            block_lines = [line]
            continue
        if re.match(r"^config\s+vpn", line, re.I):
            commit_block(current_block, "\n".join(block_lines))
            current_block = "vpn"
            block_lines = [line]
            continue

        # Fortinet 结束符
        if line.lower() == "end":
            block_lines.append(line)
            commit_block(current_block, "\n".join(block_lines))
            current_block = None
            block_lines = []
            continue

        # ========== CheckPoint 风格 ==========
        if re.match(r"^set hostname\b", line, re.I):
            config_data["hostname"] = line.split()[-1]
            continue
        if re.match(r"^set interface\b", line, re.I):
            commit_block(current_block, "\n".join(block_lines))
            current_block = "interfaces"
            block_lines = [line]
            continue
        if re.match(r"^set bgp\b", line, re.I):
            commit_block(current_block, "\n".join(block_lines))
            current_block = "router_bgp"
            block_lines = [line]
            continue
        if re.match(r"^set ospf\b", line, re.I):
            commit_block(current_block, "\n".join(block_lines))
            current_block = "router_ospf"
            block_lines = [line]
            continue

        # 其他行 -> 属于当前块
        if current_block:
            block_lines.append(line)

    # 提交最后一个块
    commit_block(current_block, "\n".join(block_lines))

    # 清理空数据
    clean_data = {k: v for k, v in config_data.items() if v}
    return clean_data


def parse_multiple_configs(folder_path, output_json="configs_summary.json"):
    """
    批量解析配置文件 (.cfg/.conf/.txt)
    输出为 JSON 文件
    """
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


# 示例运行
if __name__ == "__main__":
    folder = "./configs"
    parse_multiple_configs(folder)
