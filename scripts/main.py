import os
import json
import multiprocessing as mp
from typing import List, Dict, Any, Iterable, Callable, Optional

# 全局变量（在每个 worker 进程中初始化）
AUTOMATON = None
AUTOMATON_WORDS = None
LOWER = False


def build_automaton_from_list(words: List[str]):
    import ahocorasick
    A = ahocorasick.Automaton()
    for idx, w in enumerate(words):
        A.add_word(w, (idx, w))
    A.make_automaton()
    return A


def worker_init(dict_path: str, lower: bool):
    """每个子进程初始化自己的 Aho-Corasick 自动机"""
    global AUTOMATON, AUTOMATON_WORDS, LOWER
    LOWER = bool(lower)
    with open(dict_path, "r", encoding="utf-8") as f:
        words = [line.strip() for line in f if line.strip()]
    if LOWER:
        words = [w.lower() for w in words]
    AUTOMATON_WORDS = words
    AUTOMATON = build_automaton_from_list(words)


def match_text_with_automaton(text: str) -> List[Dict[str, Any]]:
    """对单条文本进行字典匹配"""
    global AUTOMATON, LOWER
    if AUTOMATON is None:
        raise RuntimeError("AUTOMATON not initialized in worker.")
    t = text.lower() if LOWER else text

    results: List[Dict[str, Any]] = []
    for end_idx, (idx, word) in AUTOMATON.iter(t):
        start_idx = end_idx - len(word) + 1
        results.append({"word": word, "start": start_idx, "end": end_idx})
    return results


def process_batch(batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """处理一批邮件（JSON 对象列表）"""
    out = []
    for item in batch:
        mid = item.get("id")
        text = item.get("text", "")
        matches = match_text_with_automaton(text)
        out.append({"id": mid, "matches": matches})
    return out


def read_jsonl_in_batches(path: str, batch_size: int) -> Iterable[List[Dict[str, Any]]]:
    """以批次方式读取 JSONL 文件"""
    batch: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            batch.append(obj)
            if len(batch) >= batch_size:
                yield batch
                batch = []
    if batch:
        yield batch


def count_lines(path: str) -> int:
    """统计文件行数"""
    with open(path, "r", encoding="utf-8") as f:
        return sum(1 for _ in f)


def run_bulk_match(
    dict_path: str,
    mails_path: str,
    output_path: Optional[str] = None,
    workers: int = max(1, mp.cpu_count() - 1),
    batch_size: int = 200,
    lower: bool = False,
    progress_callback: Optional[Callable[[int, int, int, str], None]] = None,
) -> Dict[str, Any]:
    """
    执行批量匹配任务（同步），返回汇总结果。
    参数：
        dict_path: 字典文件路径（一行一个词）
        mails_path: 邮件 JSONL 文件路径（{"id":,"text":} 每行一个）
        output_path: 输出文件路径（可选，不传则不落盘）
        workers: 进程数
        batch_size: 每批处理条数
        lower: 是否小写匹配
        progress_callback: 可选进度回调函数 (processed, total, matched, msg)
    返回：
        {
            "total_mails": int,
            "total_matches": int,
            "output_path": str or None
        }
    """
    total_lines = count_lines(mails_path)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True) if output_path else None

    pool = mp.Pool(processes=workers, initializer=worker_init, initargs=(dict_path, lower))
    batch_generator = read_jsonl_in_batches(mails_path, batch_size)

    matches_count = 0
    processed_count = 0

    try:
        out_f = open(output_path, "w", encoding="utf-8") if output_path else None

        for result_batch in pool.imap_unordered(process_batch, batch_generator, chunksize=1):
            for r in result_batch:
                if out_f:
                    out_f.write(json.dumps(r, ensure_ascii=False) + "\n")
                matches_count += len(r["matches"])
                processed_count += 1

            if callable(progress_callback):
                progress_callback(
                    processed_count,
                    total_lines,
                    matches_count,
                    f"已处理 {processed_count}/{total_lines} 封邮件，匹配 {matches_count} 项"
                )

    finally:
        pool.close()
        pool.join()
        if output_path and out_f:
            out_f.close()

    return {
        "total_mails": total_lines,
        "total_matches": matches_count,
        "output_path": output_path,
    }
