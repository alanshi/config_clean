#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
import json
import argparse


# ========== 1️⃣ Cisco CLI 风格解析 ==========
def clean_cisco_config(text: str) -> str:
    """去除Cisco配置中的空行与注释符号"""
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("!", "#")):
            continue
        lines.append(line.rstrip())
    return "\n".join(lines)


def parse_cisco_config(text: str) -> dict:
    """非常简化的Cisco配置语义解析"""
    data = {"hostname": None, "interfaces": [], "routers": {}}
    current_if = None
    current_router = None

    for line in text.splitlines():
        stripped = line.strip()

        # hostname
        if stripped.startswith("hostname "):
            data["hostname"] = stripped.split(" ", 1)[1]

        # interface block
        elif stripped.startswith("interface "):
            if current_if:
                data["interfaces"].append(current_if)
            current_if = {"name": stripped.split(" ", 1)[1], "config": []}

        elif current_if and line.startswith(" "):
            current_if["config"].append(stripped)

        elif current_if and not line.startswith(" "):
            data["interfaces"].append(current_if)
            current_if = None

        # router block
        elif stripped.startswith("router "):
            current_router = stripped.split(" ", 1)[1]
            data["routers"][current_router] = []

        elif current_router and line.startswith(" "):
            data["routers"][current_router].append(stripped)

        elif current_router and not line.startswith(" "):
            current_router = None

    if current_if:
        data["interfaces"].append(current_if)

    return data


# ========== 2️⃣ Braced 风格解析 ==========
def parse_braced_config(text: str) -> dict:
    """
    改进版：解析带大括号 {} 的层级配置，支持：
    - 多级嵌套
    - 单独键 (如 ethernet1/1;)
    - 普通键值对 (key value;)
    """
    # 预处理：去除注释和空行
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("!", "#")):
            continue
        # 去掉末尾多余分号
        line = line.rstrip(";")
        lines.append(line)

    root = {}
    stack = [root]
    key_stack = []

    for line in lines:
        # 开始一个新块
        if line.endswith("{"):
            key = line[:-1].strip()
            new_obj = {}
            # 允许同层多个相同 key（如多个 interface）
            if key in stack[-1]:
                if isinstance(stack[-1][key], list):
                    stack[-1][key].append(new_obj)
                else:
                    stack[-1][key] = [stack[-1][key], new_obj]
            else:
                stack[-1][key] = new_obj
            stack.append(new_obj)
            key_stack.append(key)

        # 结束一个块
        elif line == "}":
            if len(stack) > 1:
                stack.pop()
                key_stack.pop()

        # 普通键值对 或 单独键
        else:
            tokens = line.split(None, 1)
            if len(tokens) == 2:
                k, v = tokens
                stack[-1][k] = v
            else:
                k = tokens[0]
                stack[-1][k] = None  # 处理单独 key（如 ethernet1/1;）

    return root



# ========== 3️⃣ Set 风格解析 ==========
def set_nested_value(d, keys, value):
    """递归地设置嵌套键"""
    key = keys[0]
    if len(keys) == 1:
        if key in d:
            if isinstance(d[key], list):
                d[key].append(value)
            else:
                d[key] = [d[key], value]
        else:
            d[key] = value
        return
    if key not in d or not isinstance(d[key], dict):
        d[key] = {}
    set_nested_value(d[key], keys[1:], value)


def parse_set_config(text: str) -> dict:
    """解析 Palo Alto / JunOS 'set' 风格配置"""
    root = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(("!", "#")):
            continue
        if not line.startswith("set "):
            continue
        tokens = line.split()
        tokens = tokens[1:]  # remove 'set'
        if len(tokens) > 1:
            value = tokens[-1]
            path = tokens[:-1]
        else:
            path = tokens
            value = None
        set_nested_value(root, path, value)
    return root


# ========== 4️⃣ 自动识别入口 ==========
def detect_config_type(text: str) -> str:
    """简单的自动格式检测"""
    if re.search(r"(?m)^\s*set\s+", text):
        return "set"
    if "{" in text and "}" in text:
        return "braced"
    return "cisco"


def parse_universal_config(text: str) -> dict:
    """根据类型自动调用相应解析器"""
    config_type = detect_config_type(text)
    if config_type == "set":
        return parse_set_config(text)
    elif config_type == "braced":
        return parse_braced_config(text)
    else:
        cleaned = clean_cisco_config(text)
        return parse_cisco_config(cleaned)


# ========== 5️⃣ 批量处理 ==========
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
                    raw = fin.read()
                parsed = parse_universal_config(raw)
                with open(out_path, "w", encoding="utf-8") as fout:
                    json.dump(parsed, fout, indent=2, ensure_ascii=False)
                print(f"✅ {f} -> {out_path}")
                stats["success"] += 1
            except Exception as e:
                print(f"❌ {f}: {e}")
                stats["fail"] += 1

    print("\n=== 处理完成 ===")
    print(f"共: {stats['total']}, 成功: {stats['success']}, 失败: {stats['fail']}")
    print(f"输出目录: {output_dir}")


# ========== 主函数 ==========
def main():
    parser = argparse.ArgumentParser(description="通用网络配置自动解析工具 (Cisco / Braced / Set)")
    parser.add_argument("input", help="输入目录或文件")
    parser.add_argument("-o", "--output", default="./parsed_json", help="输出目录")
    args = parser.parse_args()

    if os.path.isfile(args.input):
        os.makedirs(args.output, exist_ok=True)
        with open(args.input, "r", encoding="utf-8", errors="ignore") as f:
            raw = f.read()
        parsed = parse_universal_config(raw)
        out_file = os.path.join(args.output, os.path.splitext(os.path.basename(args.input))[0] + ".json")
        with open(out_file, "w", encoding="utf-8") as fout:
            json.dump(parsed, fout, indent=2, ensure_ascii=False)
        print(f"✅ 输出文件: {out_file}")
    else:
        process_directory(args.input, args.output)


if __name__ == "__main__":
    main()
