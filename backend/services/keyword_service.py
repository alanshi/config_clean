import json
from typing import List
import ahocorasick
import re
from sqlalchemy.orm import Session
from .. import models, schemas, crud


class ConfigKeywordMatcher:
    # 保持之前的完整单词匹配逻辑不变
    def __init__(self, keywords):
        self.automaton = ahocorasick.Automaton()
        self.keyword_map = {word.lower(): word for word in keywords if word.strip()}
        for idx, word_lower in enumerate(self.keyword_map.keys()):
            self.automaton.add_word(word_lower, (idx, word_lower))
        self.automaton.make_automaton()

    def _is_full_word_match(self, line_lower: str, start_idx: int, end_idx: int) -> bool:
        start_ok = (start_idx == 0) or (not line_lower[start_idx - 1].isalnum() and line_lower[start_idx - 1] != '_')
        end_ok = (end_idx == len(line_lower) - 1) or (not line_lower[end_idx + 1].isalnum() and line_lower[end_idx + 1] != '_')
        return start_ok and end_ok

    def search_in_lines(self, lines: List[str]) -> List[dict]:
        matches = []
        for line_num, line in enumerate(lines, 1):
            line_lower = line.lower()
            for end_idx, (_, word_lower) in self.automaton.iter(line_lower):
                word_len = len(word_lower)
                start_idx = end_idx - word_len + 1
                if self._is_full_word_match(line_lower, start_idx, end_idx):
                    original_keyword = self.keyword_map[word_lower]
                    matches.append({
                        "line": line_num,
                        "keyword": original_keyword,
                        "content": line.strip()
                    })
        return matches

    def search_config_data(self, config_data: dict) -> dict:
        file_results = {}
        for section, value in config_data.items():
            if section == "vendor":
                continue
            if isinstance(value, str):
                lines = value.splitlines()
            elif isinstance(value, list):
                section_text = "\n".join([str(v).strip() for v in value if str(v).strip()])
                lines = section_text.splitlines()
            elif isinstance(value, dict):
                section_text = json.dumps(value, indent=2, ensure_ascii=False)
                lines = section_text.splitlines()
            else:
                continue
            section_matches = self.search_in_lines(lines)
            if section_matches:
                file_results[section] = section_matches
        return {
            "vendor": config_data.get("vendor", "unknown"),
            "matches": file_results
        }


def perform_keyword_check(
    db: Session,
    batch_id: int,
    keyword_set_id: int
):
    """
    执行关键词检查：自动检测该批次下所有二次清洗文件
    :param db: 数据库会话
    :param batch_id: 批次ID
    :param keyword_set_id: 关键词组ID
    :return: 匹配结果列表
    """
    # 1. 验证关键词组存在
    keyword_set = crud.get_keyword_set(db, keyword_set_id)
    if not keyword_set:
        raise ValueError("关键词组不存在")
    keywords = [k.strip() for k in keyword_set.keywords.split(",") if k.strip()]
    if not keywords:
        raise ValueError("关键词组不能为空")

    # 2. 自动获取该批次下的所有二次清洗文件（核心修改）
    cleaned_files = crud.get_cleaned_files_2_by_batch(db, batch_id=batch_id)
    if not cleaned_files:
        raise ValueError(f"批次 {batch_id} 没有二次清洗文件，无法执行关键词检查")

    # 3. 初始化匹配器
    matcher = ConfigKeywordMatcher(keywords)
    results = []

    # 4. 遍历所有二次清洗文件执行检测
    for file in cleaned_files:
        try:
            # 读取二次清洗文件内容（JSON格式）
            with open(file.file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            # 执行关键词匹配
            match_result = matcher.search_config_data(config_data)

            # 保存结果到数据库
            db_result = crud.create_keyword_match_result(db, schemas.KeywordMatchResultCreate(
                batch_id=batch_id,
                file_id=file.id,  # 自动关联当前文件ID
                keyword_set_id=keyword_set_id,
                match_data=match_result
            ))
            results.append(db_result)

        except Exception as e:
            print(f"处理文件 {file.filename} 时出错: {str(e)}")
            continue  # 跳过错误文件，继续处理其他文件

    return results