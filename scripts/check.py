import json
import os
import ahocorasick  # pip install pyahocorasick


class ConfigKeywordMatcher:
    def __init__(self, keywords):
        """初始化 Aho–Corasick 自动机"""
        self.automaton = ahocorasick.Automaton()
        for idx, word in enumerate(keywords):
            self.automaton.add_word(word.lower(), (idx, word))
        self.automaton.make_automaton()

    def search_in_lines(self, lines):
        """
        在配置文件的每一行中查找关键词。
        返回 [(行号, 关键词, 匹配行内容), ...]
        """
        matches = []
        for line_num, line in enumerate(lines, 1):
            for _, (_, word) in self.automaton.iter(line.lower()):
                matches.append({
                    "line": line_num,
                    "keyword": word,
                    "content": line.strip()
                })
        return matches

    def search_config_data(self, config_data):
        """
        在解析后的配置数据中搜索关键词，并返回结构化匹配结果。
        """
        results = {}

        for filename, content in config_data.items():
            file_results = {}


            for section, value in content.items():
                if section == "vendor":
                    continue

                if isinstance(value, str):
                    lines = value.splitlines()
                elif isinstance(value, list):
                    section_text = "\n".join(value)
                    lines = section_text.splitlines()
                else:
                    continue
                section_matches = self.search_in_lines(lines)
                if section_matches:
                    file_results[section] = section_matches

            if file_results:
                results[filename] = {
                    "vendor": content.get("vendor", "unknown"),
                    "matches": file_results
                }

        return results


def load_keywords(source):
    """
    支持两种关键词加载方式：
    - 列表
    - 文件路径（每行一个关键字）
    """
    if isinstance(source, list):
        return source
    elif os.path.exists(source):
        with open(source, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    else:
        raise ValueError("无效的关键词输入")


if __name__ == "__main__":
    # ================= 用户自定义区 =================
    keywords = [
        'aaa', 'access-list', 'access-group', 'access-class', 'acl', 'acl-filter',
            'action', 'accept', 'admin', 'administrator', 'admin-role', 'allow', 'any',
            'anyconnect', 'application', 'application-group', 'audit', 'authentication',
            'authentication-algorithm', 'authentication-method', 'authentication-order',
            'authorization', 'accounting', 'address', 'address-book', 'address-group',
            'address-set', 'banner', 'ca-certificate', 'captive-portal', 'certificate',
            'class', 'class-map', 'community', 'config', 'configure', 'console', 'count',
            'crypto', 'crypto-map', 'dead-peer-detection', 'default-group-policy', 'deny',
            'destination', 'destination-address', 'destination-ip', 'destination-port',
            'dh-group', 'disable', 'dns', 'domain', 'drop', 'enable', 'enable-password',
            'encrypted', 'encryption', 'encryption-algorithm', 'entry', 'established',
            'extended', 'failover', 'filter', 'firewall', 'from-zone', 'ftp', 'globalprotect',
            'gateway', 'group', 'group-alias', 'group-policy', 'group-lock', 'hashing',
            'host', 'host-inbound-traffic', 'http', 'https', 'ike', 'ike-gateway',
            'ike-policy', 'ikev1', 'ikev2', 'inbound', 'include', 'interface', 'interzone',
            'intrazone',   'ipsec', 'isakmp', 'key',
            'key-string', 'keychain', 'ldap', 'line', 'local', 'local-user', 'log', 'logging',
            'login', 'mac', 'management', 'map', 'match', 'md5', 'motd', 'nat', 'network',
            'no-access', 'object', 'object-group', 'on-demand', 'outbound', 'palo-alto',
            'passphrase', 'password', 'pan-os', 'permit', 'permissions', 'pfs', 'phase-1',
            'phase-2', 'policy', 'policy-map', 'policy-rules', 'portal', 'port-mirror',
            'prefix', 'pre-shared-key', 'pre-share-key', 'privilege', 'profile', 'proposal',
            'protocol', 'public-key', 'radius', 'radius-server', 'reject', 'remote-access',
            'root', 'root-password', 'route', 'routing', 'rule', 'saml', 'secret', 'security',
            'security-level', 'security-policy', 'security-zone', 'serial', 'service',
            'service-type', 'session-close', 'session-init', 'set', 'sha', 'sha1', 'sha256',
            'shell', 'snmp', 'snmp-community', 'snmp-server', 'source', 'source-address',
            'source-ip', 'source-port', 'split-tunnel', 'split-tunnel-policy', 'ssh', 'ssl',
            'ssl-client', 'ssl-clientless', 'st0', 'standard', 'superuser', 'syslog', 'system',
            'tacacs', 'tacacs+', 'tacacs-server', 'tag', 'telnet', 'tftp', 'to-zone', 'trap',
            'trust', 'tunnel', 'tunnel-group', 'tunnel-interface', 'untrust', 'url-filtering',
            'user', 'username', 'vlan', 'vty', 'vpn', 'vpn-group', 'vpn-tunnel-protocol', 'vrf',
            'web-ui', 'webvpn', 'wildfire', 'zone', 'zone-pair'
    ]

    matcher = ConfigKeywordMatcher(load_keywords(keywords))

    # 读取前一步生成的配置解析文件
    with open("configs_summary.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # 匹配
    matches = matcher.search_config_data(data)

    # 输出结果文件
    with open("config_keyword_detailed.json", "w", encoding="utf-8") as out:
        json.dump(matches, out, indent=4, ensure_ascii=False)

    print("✅ 关键词详细匹配完成，结果已写入 config_keyword_detailed.json")
