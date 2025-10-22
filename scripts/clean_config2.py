import re
import os
import json
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path
import logging

@dataclass
class CleaningConfig:
    """清洗配置参数"""
    remove_empty_lines: bool = True
    remove_comment_chars: bool = True
    preserve_original_meaning: bool = True
    extract_keywords: bool = True
    output_encoding: str = 'utf-8'
    preserve_indentation: bool = True

class ConfigCleaner:
    """配置文件清洗器"""

    def __init__(self, log_level=logging.INFO):
        self.setup_logging(log_level)

        # 定义关键词集合
        self.keywords = {
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
            'intrazone', 'ip', 'ip-address', 'ip-local-pool', 'ipsec', 'isakmp', 'key',
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
        }

        # 配置风格识别模式
        self.style_patterns = {
            'CISCO_IOS': [r'^version\s+\d+', r'^hostname\s+\S+', r'^interface\s+\S+', r'^router\s+\S+'],
            'CISCO_IOS_XE': [r'^service\s+timestamps', r'^boot\s+system', r'^license\s+udi'],
            'CISCO_IOS_XR': [r'^!!\s+IOS\s+XR', r'^hostname\s+\S+', r'^interface\s+\S+'],
            'CISCO_NX': [r'^version\s+\d+\.\d+\(\d+\)', r'^feature\s+\S+', r'^vdc\s+\S+'],
            'ARISTA': [r'^!\s+Command:\s+show\s+running-config', r'^transceiver\s+qsfp\s+default-mode'],
            'ASA': [r'^:\s+Saved', r'^ASA\s+Version', r'^nameif\s+\S+'],
            'FORTINET': [r'^config\s+\S+', r'^edit\s+\d+', r'^set\s+\S+\s+\S+'],
            'JUNIPER': [r'^##\s+Last\s+commit:', r'^version\s+\d+', r'^system\s+\{', r'set\s+\S+\s+\S+'],
            'PALOALTO': [r'^deviceconfig\s*\{', r'^network\s*\{', r'^set\s+\S+\s+\S+'],
            'BRACED': [r'\{\s*$', r'^\s*\w+\s*\{', r'^\s*\}'],
            'SET': [r'^set\s+\S+', r'^unset\s+\S+']
        }

        self.logger = logging.getLogger(__name__)

    def setup_logging(self, level=logging.INFO):
        """设置日志"""
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('config_cleaner.log', encoding='utf-8')
            ]
        )

    def detect_config_style(self, content: str) -> str:
        """检测配置文件风格"""
        scores = {}

        for style, patterns in self.style_patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
                    score += 1
            scores[style] = score

        # 返回得分最高的风格
        best_style = max(scores.items(), key=lambda x: x[1])
        return best_style[0] if best_style[1] > 0 else 'UNKNOWN'

    def clean_content(self, content: str, config: CleaningConfig = None) -> Tuple[str, Dict]:
        """清洗配置内容"""
        if config is None:
            config = CleaningConfig()

        original_lines = content.split('\n')
        cleaned_lines = []
        extracted_blocks = []
        current_block = []
        in_block = False
        line_stats = {
            'total_removed': 0,
            'comments_removed': 0,
            'empty_lines_removed': 0
        }

        for line in original_lines:
            original_line = line
            processed_line = line.rstrip()  # 移除行尾空白

            # 检查是否为注释行
            is_comment = self._is_comment_line(processed_line)
            is_empty = not processed_line.strip()

            # 跳过空行
            if config.remove_empty_lines and is_empty:
                line_stats['empty_lines_removed'] += 1
                line_stats['total_removed'] += 1
                continue

            # 处理注释字符
            if config.remove_comment_chars and is_comment:
                line_stats['comments_removed'] += 1
                line_stats['total_removed'] += 1
                continue

            # 处理行内注释
            if config.remove_comment_chars:
                processed_line = self._remove_inline_comments(processed_line)

            # 保留原始缩进
            if config.preserve_indentation:
                # 计算原始缩进
                original_indent = len(line) - len(line.lstrip())
                processed_line = ' ' * original_indent + processed_line.lstrip()

            # 检查是否包含关键词
            if config.extract_keywords:
                if self._contains_keyword(processed_line):
                    if not in_block:
                        in_block = True
                        # 添加上下文行（如果有）
                        if cleaned_lines and len(cleaned_lines) > 0:
                            context_start = max(0, len(cleaned_lines) - 2)
                            current_block.extend(cleaned_lines[context_start:])
                    current_block.append(processed_line)
                else:
                    if in_block and current_block:
                        # 添加后续的上下文行
                        block_content = '\n'.join(current_block)
                        extracted_blocks.append(block_content)
                        current_block = []
                    in_block = False

            cleaned_lines.append(processed_line)

        # 处理最后一个块
        if in_block and current_block:
            block_content = '\n'.join(current_block)
            extracted_blocks.append(block_content)

        # 构建结果
        result = {
            'cleaned_content': '\n'.join(cleaned_lines),
            'extracted_blocks': extracted_blocks,
            'detected_style': self.detect_config_style(content),
            'stats': {
                'original_lines': len(original_lines),
                'cleaned_lines': len(cleaned_lines),
                'extracted_blocks_count': len(extracted_blocks),
                'lines_removed': line_stats['total_removed'],
                'comments_removed': line_stats['comments_removed'],
                'empty_lines_removed': line_stats['empty_lines_removed']
            }
        }

        self.logger.info(f"清洗完成: 原始{len(original_lines)}行 -> 清洗后{len(cleaned_lines)}行")

        return result['cleaned_content'], result

    def _is_comment_line(self, line: str) -> bool:
        """检查是否为注释行"""
        stripped = line.strip()
        return stripped.startswith('!') or (stripped.startswith('#') and not stripped.startswith('set'))

    def _remove_inline_comments(self, line: str) -> str:
        """移除行内注释，但保留配置字符串中的特殊字符"""
        # 保护引号内的内容
        in_quotes = False
        quote_char = None
        result = []
        i = 0

        while i < len(line):
            char = line[i]

            if char in ['"', "'"] and (i == 0 or line[i-1] != '\\'):
                if not in_quotes:
                    in_quotes = True
                    quote_char = char
                elif quote_char == char:
                    in_quotes = False
                    quote_char = None
                result.append(char)

            elif in_quotes:
                result.append(char)

            elif char == '!' and not in_quotes:
                # 遇到!注释，停止处理该行剩余部分
                break

            elif char == '#' and not in_quotes:
                # 遇到#注释，停止处理该行剩余部分
                break

            else:
                result.append(char)

            i += 1

        return ''.join(result).rstrip()

    def _contains_keyword(self, line: str) -> bool:
        """检查行是否包含关键词"""
        line_lower = line.lower()

        # 直接匹配完整单词
        words = re.findall(r'\b\w+\b', line_lower)
        for word in words:
            if word in self.keywords:
                return True

        # 匹配带连字符的配置命令
        hyphen_patterns = [f'\\b{keyword}\\b' for keyword in self.keywords if '-' in keyword]
        for pattern in hyphen_patterns:
            if re.search(pattern, line_lower):
                return True

        return False

    def clean_file(self, file_path: str, config: CleaningConfig = None) -> Dict:
        """清洗单个配置文件"""
        try:
            self.logger.info(f"开始处理文件: {file_path}")

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            cleaned_content, result = self.clean_content(content, config)
            result['file_name'] = os.path.basename(file_path)
            result['file_path'] = file_path

            self.logger.info(f"文件处理完成: {file_path}")
            return result

        except Exception as e:
            self.logger.error(f"处理文件失败 {file_path}: {str(e)}")
            return {
                'error': str(e),
                'file_name': os.path.basename(file_path),
                'file_path': file_path
            }

    def batch_clean_files(self, file_paths: List[str], config: CleaningConfig = None) -> Dict[str, Dict]:
        """批量清洗多个文件"""
        results = {}

        for file_path in file_paths:
            if os.path.exists(file_path):
                results[file_path] = self.clean_file(file_path, config)
            else:
                self.logger.warning(f"文件不存在: {file_path}")
                results[file_path] = {'error': 'File not found'}

        return results

    def save_cleaned_files(self, results: Dict[str, Dict], output_dir: str = "cleaned_output") -> Dict[str, str]:
        """保存清洗后的文件"""
        output_paths = {}
        os.makedirs(output_dir, exist_ok=True)

        for file_path, result in results.items():
            if 'error' in result:
                self.logger.warning(f"跳过有错误的文件: {file_path} - {result['error']}")
                continue

            base_name = os.path.splitext(os.path.basename(file_path))[0]

            # 保存清洗后的完整配置
            cleaned_file = os.path.join(output_dir, f"{base_name}_cleaned.txt")
            with open(cleaned_file, 'w', encoding='utf-8') as f:
                f.write(result['cleaned_content'])
            output_paths['cleaned'] = cleaned_file

            # 保存提取的业务块
            if result['extracted_blocks']:
                blocks_file = os.path.join(output_dir, f"{base_name}_blocks.txt")
                with open(blocks_file, 'w', encoding='utf-8') as f:
                    f.write("=== 提取的业务配置块 ===\n\n")
                    for i, block in enumerate(result['extracted_blocks'], 1):
                        f.write(f"块 {i}:\n")
                        f.write(block)
                        f.write("\n" + "="*50 + "\n\n")
                output_paths['blocks'] = blocks_file

            # 保存清洗报告
            report_file = os.path.join(output_dir, f"{base_name}_report.json")
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'file_info': {
                        'original_file': file_path,
                        'cleaned_file': cleaned_file,
                        'detected_style': result['detected_style']
                    },
                    'cleaning_stats': result['stats'],
                    'processing_time': 'N/A'  # 可以添加时间戳
                }, f, indent=2, ensure_ascii=False)
            output_paths['report'] = report_file

            self.logger.info(f"已保存清洗结果: {cleaned_file}")

        return output_paths

    def process_directory(self, input_dir: str, output_dir: str = "cleaned_output",
                         config: CleaningConfig = None) -> Dict:
        """处理整个目录的配置文件"""
        self.logger.info(f"开始处理目录: {input_dir}")

        if not os.path.exists(input_dir):
            raise ValueError(f"输入目录不存在: {input_dir}")

        # 支持的配置文件扩展名
        config_extensions = {'.txt', '.cfg', '.conf', '.config', '.run'}
        config_files = []

        for root, dirs, files in os.walk(input_dir):
            for file in files:
                if any(file.endswith(ext) for ext in config_extensions):
                    config_files.append(os.path.join(root, file))

        self.logger.info(f"找到 {len(config_files)} 个配置文件")

        # 批量处理文件
        results = self.batch_clean_files(config_files, config)

        # 保存结果
        output_paths = self.save_cleaned_files(results, output_dir)

        # 生成汇总报告
        summary = self._generate_summary_report(results, output_dir)

        self.logger.info(f"目录处理完成: {input_dir} -> {output_dir}")
        return {
            'processed_files': len(config_files),
            'output_directory': output_dir,
            'summary': summary,
            'output_paths': output_paths
        }

    def _generate_summary_report(self, results: Dict[str, Dict], output_dir: str) -> Dict:
        """生成汇总报告"""
        total_files = len(results)
        successful_files = 0
        total_original_lines = 0
        total_cleaned_lines = 0
        total_blocks_found = 0

        for result in results.values():
            if 'error' not in result:
                successful_files += 1
                total_original_lines += result['stats']['original_lines']
                total_cleaned_lines += result['stats']['cleaned_lines']
                total_blocks_found += result['stats']['extracted_blocks_count']

        summary = {
            'total_files_processed': total_files,
            'successful_files': successful_files,
            'failed_files': total_files - successful_files,
            'total_original_lines': total_original_lines,
            'total_cleaned_lines': total_cleaned_lines,
            'total_lines_removed': total_original_lines - total_cleaned_lines,
            'total_blocks_extracted': total_blocks_found,
            'reduction_rate': f"{((total_original_lines - total_cleaned_lines) / total_original_lines * 100):.1f}%" if total_original_lines > 0 else "0%"
        }

        # 保存汇总报告
        summary_file = os.path.join(output_dir, "processing_summary.json")
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        return summary

# 使用示例和主程序
def main():
    """主程序示例"""
    # 创建清洗器实例
    cleaner = ConfigCleaner(log_level=logging.INFO)

    # 配置清洗参数
    config = CleaningConfig(
        remove_empty_lines=True,
        remove_comment_chars=True,
        preserve_original_meaning=True,
        extract_keywords=True,
        output_encoding='utf-8',
        preserve_indentation=True
    )

    # 示例1: 处理单个文件
    # print("=== 示例1: 处理单个文件 ===")
    # sample_config = """
    # ! This is a comment
    # hostname Router1
    # !
    # interface GigabitEthernet0/0
    #  ip address 192.168.1.1 255.255.255.0
    #  no shutdown
    # !
    # router ospf 1
    #  network 192.168.1.0 0.0.0.255 area 0
    # !
    # """

    # cleaned, result = cleaner.clean_content(sample_config, config)
    # print(f"检测到的风格: {result['detected_style']}")
    # print(f"清洗统计: {result['stats']}")
    # print("\n清洗后的配置:")
    # print(cleaned)

    # 示例2: 处理目录（取消注释以使用）
    """
    print("\n=== 示例2: 处理配置文件目录 ===")
    input_directory = "config_files"  # 替换为您的配置文件夹路径
    output_directory = "cleaned_configs"

    try:
        directory_result = cleaner.process_directory(input_directory, output_directory, config)
        print(f"处理完成: {directory_result}")
    except Exception as e:
        print(f"处理目录时出错: {e}")
    """

    # 示例3: 批量处理文件列表

    print("\n=== 示例3: 批量处理文件列表 ===")
    file_list = [
        "S4-7609.cfg",
    ]

    # 过滤存在的文件
    existing_files = [f for f in file_list if os.path.exists(f)]
    if existing_files:
        batch_results = cleaner.batch_clean_files(existing_files, config)
        output_paths = cleaner.save_cleaned_files(batch_results)
        print(f"输出文件: {output_paths}")
    else:
        print("没有找到指定的文件")

if __name__ == "__main__":
    main()