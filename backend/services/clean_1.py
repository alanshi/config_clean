import os
import re

def clean_config_file(file_path, keep_bang_blocks=True, output_path=None):
    """
    清理配置文件：
    - 去掉空行、注释行(#, *)；
    - 移除行首被[]包裹的内容（如[任意内容]）；
    - 按需保留或移除 '!'；
    - 支持另存或原地覆盖。
    """

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    cleaned_lines = []
    # 匹配行首的[任意内容]（非贪婪匹配，避免跨越多行）
    bracket_pattern = r'^\[.*?\]'  # ^表示行首，\[匹配[，.*?匹配任意内容（非贪婪），\]匹配]

    for line in lines:
        # 先移除行首被[]包裹的内容
        line = re.sub(bracket_pattern, '', line)
        stripped = line.strip()

        # 跳过空行（移除内容后可能变成空行）
        if not stripped:
            continue

        # 跳过注释行
        if stripped.startswith('#') or stripped.startswith('*'):
            continue

        # 特殊处理 "!" 行
        if stripped == '!':
            if keep_bang_blocks:
                # 避免连续重复的 "!"
                if not (cleaned_lines and cleaned_lines[-1].strip() == '!'):
                    cleaned_lines.append('!\n')
            continue  # 不保留多余的 !
        elif stripped.startswith('!') and len(stripped) > 1:
            # 像 "! interface ..." 这样的行要保留
            cleaned_lines.append(line)
        else:
            cleaned_lines.append(line)

    # 输出文件路径处理
    if not output_path:
        suffix = os.path.splitext(file_path)[1]
        output_path = file_path + '_cleaned' + suffix

    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(cleaned_lines)

    print(f"cleaned: {file_path} -> {output_path}")


def clean_multiple_configs(file_paths, keep_bang_blocks=False):
    for path in file_paths:
        if os.path.isfile(path):
            clean_config_file(path, keep_bang_blocks=keep_bang_blocks)
        else:
            print(f"cannot find file: {path}")


# 示例使用
if __name__ == "__main__":
    config_files = [
        "configs/Catalyst9500-S3.cfg",
    ]
    clean_multiple_configs(config_files, keep_bang_blocks=True)