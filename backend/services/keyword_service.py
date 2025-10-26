import json
from typing import List, Tuple, Dict
import ahocorasick
import re
from sqlalchemy.orm import Session
from .. import models, schemas, crud


class ConfigKeywordMatcher:
    def __init__(self, keywords):
        self.automaton = ahocorasick.Automaton()
        self.keyword_map = {word.lower(): word for word in keywords if word.strip()}
        for idx, word_lower in enumerate(self.keyword_map.keys()):
            self.automaton.add_word(word_lower, (idx, word_lower))
        self.automaton.make_automaton()

    def _is_full_word_match(self, line_lower: str, start_idx: int, end_idx: int) -> bool:
        """保持完整单词匹配逻辑"""
        start_ok = (start_idx == 0) or (not line_lower[start_idx - 1].isalnum() and line_lower[start_idx - 1] != '_')
        end_ok = (end_idx == len(line_lower) - 1) or (not line_lower[end_idx + 1].isalnum() and line_lower[end_idx + 1] != '_')
        return start_ok and end_ok

    def search_in_lines(self, lines_with_original_numbers: List[Tuple[str, int]]) -> List[dict]:
        """
        在带原始行号的行列表中搜索关键词
        :param lines_with_original_numbers: 元素为 (行内容, 原始行号) 的列表
        :return: 包含原始行号的匹配结果
        """
        matches = []
        for line_content, original_line_num in lines_with_original_numbers:
            line_lower = line_content.lower()
            matched_positions = set()  # 去重：(关键词, 起始位置, 结束位置)

            for end_idx, (_, word_lower) in self.automaton.iter(line_lower):
                word_len = len(word_lower)
                start_idx = end_idx - word_len + 1

                # 校验完整单词匹配
                if not self._is_full_word_match(line_lower, start_idx, end_idx):
                    continue

                # 去重处理
                match_key = (word_lower, start_idx, end_idx)
                if match_key in matched_positions:
                    continue
                matched_positions.add(match_key)

                # 记录原始行号（核心修改）
                matches.append({
                    "line": original_line_num,  # 使用原始文件的绝对行号
                    "keyword": self.keyword_map[word_lower],
                    "content": line_content.strip()
                })
        return matches

    def search_config_data(self, raw_data: str, vendor: str = "unknown") -> dict:
        """
        从原始文本提取区块并匹配关键词，使用原始文件行号
        :param raw_data: 原始配置文本
        :param vendor: 设备厂商
        :return: 包含原始行号的匹配结果
        """
        # 1. 预处理原始数据，保留每行的原始内容和绝对行号（核心步骤）
        raw_lines = raw_data.splitlines()  # 按换行分割，保留空行（确保行号准确）
        # 生成 (行内容, 原始行号) 列表（行号从1开始）
        lines_with_numbers = [(line, idx + 1) for idx, line in enumerate(raw_lines)]
        # 生成带位置索引的全文（用于定位区块在原始文本中的位置）
        full_text = '\n'.join(raw_lines)
        text_length = len(full_text)

        # 2. 定义配置区块正则（适配网络设备配置）
        section_pattern = re.compile(
            r'(?P<section>interface\s+\S+|router\s+\S+\s*\d*|ip\s+vrf\s+\S+|line\s+\S+|redundancy|mpls\s+\S+|hostname)\s*'
            r'(?P<content>.*?)(?=\n(interface|router|ip\s+vrf|line|redundancy|mpls|hostname|$))',
            re.DOTALL | re.IGNORECASE
        )

        # 3. 计算每行在全文中的起始索引（用于定位区块对应的原始行）
        line_start_indices = []
        current_pos = 0
        for line in raw_lines:
            line_start_indices.append(current_pos)
            current_pos += len(line) + 1  # +1 是换行符的长度（\n）
        line_start_indices.append(text_length)  # 最后一行的结束位置

        # 4. 提取区块并映射到原始行号
        sections = {}
        # 提取区块内容和对应的原始行号范围
        for match in section_pattern.finditer(full_text):
            section_name = match.group('section').strip().lower()
            section_content = match.group('content').strip()
            section_start = match.start()  # 区块在全文中的起始位置
            section_end = match.end()      # 区块在全文中的结束位置

            # 找到区块起始行（第一个包含区块起始位置的行）
            start_line = None
            for idx, pos in enumerate(line_start_indices):
                if pos <= section_start < line_start_indices[idx + 1]:
                    start_line = idx + 1  # 行号从1开始
                    break

            # 找到区块结束行（最后一个包含区块结束位置的行）
            end_line = None
            for idx, pos in enumerate(line_start_indices):
                if pos <= section_end < line_start_indices[idx + 1]:
                    end_line = idx + 1
                    break

            # 提取区块内的行（带原始行号）
            if start_line is not None and end_line is not None:
                # 截取 (行内容, 原始行号) 列表中属于当前区块的部分
                section_lines = lines_with_numbers[start_line - 1:end_line]  # 切片是左闭右开
                sections[section_name] = section_lines

        # 5. 提取全局配置（未被区块包含的行）
        covered_lines = set()
        for section_lines in sections.values():
            covered_lines.update([line_num for _, line_num in section_lines])
        # 全局行 = 所有行号 - 区块覆盖的行号
        global_lines = [ln for ln in lines_with_numbers if ln[1] not in covered_lines]
        if global_lines:
            sections['global'] = global_lines

        # 6. 对每个区块执行关键词匹配（使用原始行号）
        section_matches = {}
        for section, lines in sections.items():
            if not lines:
                continue
            # 调用匹配方法时传入带原始行号的行列表
            matches = self.search_in_lines(lines)
            if matches:
                section_matches[section] = matches

        return {
            "vendor": vendor,
            "matches": section_matches
        }


def perform_keyword_check(
    db: Session,
    batch_id: int,
    keyword_set_id: int
):
    """执行关键词检查，确保行号为原始文件行号"""
    # 1. 验证关键词组
    keyword_set = crud.get_keyword_set(db, keyword_set_id)
    if not keyword_set:
        raise ValueError("关键词组不存在")
    keywords = [k.strip() for k in keyword_set.keywords.split(",") if k.strip()]
    if not keywords:
        raise ValueError("关键词组不能为空")

    # 2. 获取清洗文件（原始文本格式）
    cleaned_files = crud.get_cleaned_files_1_by_batch(db, batch_id=batch_id)
    if not cleaned_files:
        raise ValueError(f"批次 {batch_id} 没有初次清洗文件")

    # 3. 初始化匹配器
    matcher = ConfigKeywordMatcher(keywords)
    results = []

    # 4. 处理文件（保留原始行号，不合并/去重行）
    for file in cleaned_files:
        try:
            # 读取原始文本（保留所有行，包括空行，确保行号准确）
            with open(file.file_path, 'r', encoding='utf-8') as f:
                raw_data = f.read()  # 不做任何行去重或合并，保持原始结构

            # 获取厂商信息（示例）
            vendor = "cisco"  # 实际可从文件名/内容提取

            # 执行匹配（行号为原始文件行号）
            match_result = matcher.search_config_data(raw_data, vendor=vendor)

            # 保存结果
            filename = file.filename.replace('.cfg', '_matches.json').replace('.txt', '_matches.json')
            match_file_path = file.file_path.replace('cleaned_1', 'match').replace(file.filename, filename)
            with open(match_file_path, 'w', encoding='utf-8') as f:
                json.dump(match_result, f, ensure_ascii=False, indent=2)

            db_result = crud.create_keyword_match_result(db, schemas.KeywordMatchResultCreate(
                batch_id=batch_id,
                file_id=file.id,
                filename=filename,
                file_path=match_file_path,
                keyword_set_id=keyword_set_id,
                match_data=match_result
            ))
            db.commit()
            results.append(db_result)

        except Exception as e:
            print(f"处理文件 {file.filename} 时出错: {str(e)}")
            continue

    return results