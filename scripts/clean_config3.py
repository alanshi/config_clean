import re
import os
from typing import List, Dict, Tuple, Optional
import argparse
import json


class NetworkConfigProcessor:
    def __init__(self, config_text: str):
        self.original_lines = config_text.splitlines()
        self.cleaned_lines = []
        self.blocks = []
        self.keywords = {
            "aaa", "access-list", "access-group", "access-class", "acl", "acl-filter",
            "action", "accept", "admin", "administrator", "admin-role", "allow", "any",
            "anyconnect", "application", "application-group", "audit", "authentication",
            "authentication-algorithm", "authentication-method", "authentication-order",
            "authorization", "accounting", "address", "address-book", "address-group",
            "address-set", "banner", "ca-certificate", "captive-portal", "certificate",
            "class", "class-map", "community", "config", "configure", "console", "count",
            "crypto", "crypto-map", "dead-peer-detection", "default-group-policy", "deny",
            "destination", "destination-address", "destination-ip", "destination-port",
            "dh-group", "disable", "dns", "domain", "drop", "enable", "enable-password",
            "encrypted", "encryption", "encryption-algorithm", "entry", "established",
            "extended", "failover", "filter", "firewall", "from-zone", "ftp", "globalprotect",
            "gateway", "group", "group-alias", "group-policy", "group-lock", "hashing", "host",
            "host-inbound-traffic", "http", "https", "ike", "ike-gateway", "ike-policy", "ikev1",
            "ikev2", "inbound", "include", "interface", "interzone", "intrazone", "ip",
            "ip-address", "ip-local-pool", "ipsec", "isakmp", "key", "key-string", "keychain",
            "ldap", "line", "local", "local-user", "log", "logging", "login", "mac", "management",
            "map", "match", "md5", "motd", "nat", "network", "no-access", "object", "object-group",
            "on-demand", "outbound", "palo-alto", "passphrase", "password", "pan-os", "permit",
            "permissions", "pfs", "phase-1", "phase-2", "policy", "policy-map", "policy-rules",
            "portal", "port-mirror", "prefix", "pre-shared-key", "pre-share-key", "privilege",
            "profile", "proposal", "protocol", "public-key", "radius", "radius-server", "reject",
            "remote-access", "root", "root-password", "route", "routing", "rule", "saml", "secret",
            "security", "security-level", "security-policy", "security-zone", "serial", "service",
            "service-type", "session-close", "session-init", "set", "sha", "sha1", "sha256", "shell",
            "snmp", "snmp-community", "snmp-server", "source", "source-address", "source-ip",
            "source-port", "split-tunnel", "split-tunnel-policy", "ssh", "ssl", "ssl-client",
            "ssl-clientless", "st0", "standard", "superuser", "syslog", "system", "tacacs",
            "tacacs+", "tacacs-server", "tag", "telnet", "tftp", "to-zone", "trap", "trust",
            "tunnel", "tunnel-group", "tunnel-interface", "untrust", "url-filtering", "user",
            "username", "vlan", "vty", "vpn", "vpn-group", "vpn-tunnel-protocol", "vrf", "web-ui",
            "webvpn", "wildfire", "zone", "zone-pair"
        }
        self.style = self.detect_config_style()

    def detect_config_style(self) -> str:
        """检测配置文件风格"""
        line_text = ' '.join(self.original_lines).lower()

        if re.search(r'\{.*\}', line_text):
            return "braced"  # Paloalto等带大括号的风格
        if re.search(r'^set\s', line_text, re.MULTILINE):
            return "set"     # Checkpoint等带set命令的风格
        if re.search(r'^!', line_text, re.MULTILINE):
            return "cisco"   # Cisco IOS等带!分隔符的风格
        return "asa"        # 默认ASA风格（兼容Cisco其他变体）

    def clean_config(self) -> None:
        """清洗配置文件：移除空行、注释符等"""
        for line in self.original_lines:
            stripped = line.strip()

            # 跳过空行
            if not stripped:
                continue

            # 处理Cisco风格的!分隔符（仅移除单独的!行）
            if self.style in ["cisco", "asa"] and stripped == "!":
                continue

            # 处理#注释行（仅移除#开头的注释）
            if stripped.startswith('#'):
                continue

            self.cleaned_lines.append(line)

    def parse_blocks(self) -> None:
        """根据配置风格解析配置块"""
        if self.style == "braced":
            self._parse_braced_blocks()
        elif self.style == "set":
            self._parse_set_blocks()
        else:
            self._parse_cisco_blocks()

    def _parse_braced_blocks(self) -> None:
        """解析带大括号的配置块（如Paloalto）"""
        blocks = []
        current_block = []
        brace_stack = 0

        for line in self.cleaned_lines:
            current_block.append(line)
            # 统计大括号数量判断块边界
            brace_stack += line.count('{')
            brace_stack -= line.count('}')

            if brace_stack == 0 and current_block:
                blocks.append('\n'.join(current_block))
                current_block = []

        # 处理剩余未闭合的块
        if current_block:
            blocks.append('\n'.join(current_block))

        self.blocks = blocks

    def _parse_set_blocks(self) -> None:
        """解析set风格配置块（如Checkpoint）"""
        blocks = []
        current_group = None
        current_block = []

        for line in self.cleaned_lines:
            stripped = line.strip().lower()
            if not stripped.startswith('set'):
                if current_block:
                    blocks.append('\n'.join(current_block))
                    current_block = []
                continue

            # 提取set后的第一级分组作为块标识
            parts = re.split(r'\s+', stripped, 2)
            if len(parts) >= 2:
                group = parts[1]
                if group != current_group:
                    if current_block:
                        blocks.append('\n'.join(current_block))
                    current_group = group
                    current_block = [line]
                else:
                    current_block.append(line)

        if current_block:
            blocks.append('\n'.join(current_block))

        self.blocks = blocks

    def _parse_cisco_blocks(self) -> None:
        """解析Cisco/ASA风格配置块（基于缩进）"""
        blocks = []
        current_block = []
        base_indent = None

        for line in self.cleaned_lines:
            # 计算当前行缩进
            indent = len(line) - len(line.lstrip())
            stripped = line.strip()

            if not stripped:
                continue

            # 确定基准缩进（非缩进行为块起始）
            if base_indent is None:
                base_indent = indent

            # 非缩进行作为新块起始
            if indent <= base_indent:
                if current_block:
                    blocks.append('\n'.join(current_block))
                current_block = [line]
                base_indent = indent
            else:
                current_block.append(line)

        if current_block:
            blocks.append('\n'.join(current_block))

        self.blocks = blocks

    def filter_keyword_blocks(self) -> List[str]:
        """过滤包含关键词的配置块"""
        filtered = []
        keyword_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(k) for k in self.keywords) + r')\b',
            re.IGNORECASE
        )

        for block in self.blocks:
            if keyword_pattern.search(block):
                filtered.append(block)

        return filtered

    def process(self) -> str:
        """执行完整处理流程并返回结果"""
        self.clean_config()
        self.parse_blocks()
        relevant_blocks = self.filter_keyword_blocks()
        return '\n\n'.join(relevant_blocks)


def process_directory(input_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    stats = {"total": 0, "success": 0, "fail": 0}

    for root_dir, _, files in os.walk(input_dir):
        for f in files:
            if not f.endswith((".cfg", ".conf", ".txt")):
                continue
            stats["total"] += 1
            in_path = os.path.join(root_dir, f)
            out_path = os.path.join(output_dir, os.path.splitext(f)[0] + ".json")

            try:
                with open(in_path, "r", encoding="utf-8", errors="ignore") as fin:
                    config_content = fin.read()
                processor = NetworkConfigProcessor(config_content)
                result = processor.process()
                with open(out_path, "w", encoding="utf-8") as fout:
                    json.dump(result, fout, indent=2, ensure_ascii=False)
                print(f"✅ {f} -> {out_path}")
                stats["success"] += 1
            except Exception as e:
                print(f"❌ {f}: {e}")
                stats["fail"] += 1

    print("\n=== 处理完成 ===")
    print(f"共: {stats['total']}, 成功: {stats['success']}, 失败: {stats['fail']}")
    print(f"输出目录: {output_dir}")



def main():
    parser = argparse.ArgumentParser(description="通用网络配置自动解析工具 (Cisco / Braced / Set)")
    parser.add_argument("input", help="输入目录或文件")
    parser.add_argument("-o", "--output", default="./parsed_json", help="输出目录")
    args = parser.parse_args()

    if os.path.isfile(args.input):
        os.makedirs(args.output, exist_ok=True)
        with open(args.input, "r", encoding="utf-8", errors="ignore") as f:
            config_content = f.read()
        processor = NetworkConfigProcessor(config_content)
        result = processor.process()
        # parsed = parse_universal_config(raw)
        out_file = os.path.join(args.output, os.path.splitext(os.path.basename(args.input))[0] + ".cfg")
        with open(out_file, "w", encoding="utf-8") as fout:
            fout.write(result)
        print(f"✅ 输出文件: {out_file}")
    else:
        process_directory(args.input, args.output)


if __name__ == "__main__":
    main()



# # 使用示例
# if __name__ == "__main__":
#     # 读取配置文件（实际使用时替换为文件读取）
#     with open("device_config.txt", "r") as f:
#         config_content = f.read()

#     # 处理配置
#     processor = NetworkConfigProcessor(config_content)
#     result = processor.process()

#     # 输出结果
#     print("处理后的配置：")
#     print(result)

#     # 保存结果到文件
#     with open("cleaned_config.txt", "w") as f:
#         f.write(result)