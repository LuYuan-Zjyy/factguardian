# -*- coding: utf-8 -*-
import requests
import json
import time
import os

BASE_URL = "http://127.0.0.1:8000"

# ANSI 颜色代码（Windows 终端支持）
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

def print_header(text):
    """打印加粗的标题"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(80)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}\n")

def print_step(step_num, text):
    """打印步骤信息"""
    print(f"{Colors.BOLD}{Colors.BLUE}[步骤 {step_num}] {text}{Colors.RESET}")

def print_success(text):
    """打印成功信息"""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")

def print_error(text):
    """打印错误信息"""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")

def print_warning(text):
    """打印警告信息"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")

def test_automated_flow(file_path):
    print_header(f"FactGuardian 自动化测试")
    print(f"测试文件: {Colors.CYAN}{file_path}{Colors.RESET}\n")
    
    # 1. 检查文件是否存在
    if not os.path.exists(file_path):
        print_error(f"文件不存在: {file_path}")
        return

    # 2. 上传文档
    print_step(1, "上传文档")
    files = {'file': (os.path.basename(file_path), open(file_path, 'rb'), 'text/plain')}
    response = requests.post(f"{BASE_URL}/api/upload", files=files)
    if response.status_code != 200:
        print_error(f"上传失败: {response.text}")
        return
    
    data = response.json()
    doc_id = data.get("document_id")
    print_success(f"文档上传成功！文档ID: {Colors.BOLD}{doc_id}{Colors.RESET}")
    
    # 3. 提取事实
    print_step(2, "提取关键事实")
    response = requests.post(f"{BASE_URL}/api/documents/{doc_id}/extract-facts")
    if response.status_code != 200:
        print_error(f"事实提取失败: {response.text}")
        return
    facts_data = response.json()
    total_facts = facts_data.get('total_facts', 0)
    print_success(f"成功提取 {Colors.BOLD}{total_facts}{Colors.RESET} 条事实")
    
    # 显示提取的事实列表
    if total_facts > 0:
        print(f"\n{Colors.BOLD}提取的事实列表:{Colors.RESET}")
        facts_list = facts_data.get('facts', [])
        for i, fact in enumerate(facts_list, 1):
            fact_type = fact.get('type', '未知')
            content = fact.get('content', '')
            print(f"  {i}. [{fact_type}] {content}")

    # 4. 验证事实
    print_step(3, "溯源验证（联网查证）")
    response = requests.post(f"{BASE_URL}/api/documents/{doc_id}/verify-facts?only_errors=true")
    
    if response.status_code != 200:
        print_error(f"验证失败: {response.text}")
        return

    verify_data = response.json()
    results = verify_data.get("verifications", [])
    statistics = verify_data.get("statistics", {})
    print_success(f"验证完成！\n")
    
    # 5. 生成详细报告
    print_header("事实验证报告")
    
    # 显示统计摘要
    print(f"  {Colors.GREEN}✓ 验证通过: {statistics.get('supported', 0)}{Colors.RESET}")
    print(f"  {Colors.RED}✗ 验证失败: {statistics.get('unsupported', 0)}{Colors.RESET}")
    print(f"  {Colors.YELLOW}⊙ 跳过验证: {statistics.get('skipped', 0)}{Colors.RESET} (内部数据)")
    print()
    
    # 只显示验证失败的事实（API 已过滤）
    if len(results) > 0:
        print(f"{Colors.BOLD}发现 {len(results)} 条需要修正的事实：{Colors.RESET}\n")
        
        for idx, res in enumerate(results, 1):
            confidence = res.get('confidence_level', 'Unknown')
            original_fact = res.get('original_fact', {})
            content = original_fact.get('content', '')
            fact_type = original_fact.get('type', '未知')
            fact_index = res.get('fact_index', idx)
            
            # 置信度颜色
            if confidence == "High":
                conf_color = Colors.RED
            elif confidence == "Medium":
                conf_color = Colors.YELLOW
            else:
                conf_color = Colors.RED
            
            print(f"{Colors.BOLD}【错误 {idx}】原事实 #{fact_index}{Colors.RESET}")
            print(f"  类型: {fact_type}")
            print(f"  内容: {content}")
            print(f"  状态: {Colors.RED}✗ 错误{Colors.RESET}")
            print(f"  置信度: {conf_color}{confidence}{Colors.RESET}")
            
            correction = res.get('correction', 'N/A')
            assessment = res.get('assessment', '')
            
            if correction and correction != 'N/A' and correction.strip():
                print(f"  {Colors.YELLOW}建议修正:{Colors.RESET} {correction}")
            print(f"  {Colors.YELLOW}原因分析:{Colors.RESET} {assessment}")
            print()
    else:
        print(f"{Colors.GREEN}所有可验证事实均通过验证！{Colors.RESET}\n")
    
    # 4. 内部冲突检测（不依赖搜索）
    print_step(4, "内部冲突检测（不依赖搜索）")
    conflict_resp = requests.post(f"{BASE_URL}/api/detect-conflicts/{doc_id}")
    if conflict_resp.status_code != 200:
        print_error(f"冲突检测失败: {conflict_resp.text}")
        return

    conflict_data = conflict_resp.json()
    conflicts = conflict_data.get("conflicts", [])
    conflicts_found = conflict_data.get("conflicts_found", len(conflicts))
    total_comparisons = conflict_data.get("total_comparisons", 0)
    print_success(f"冲突检测完成！发现 {conflicts_found} 个冲突\n")

    print_header("冲突检测报告")
    if not conflicts:
        print(f"  {Colors.GREEN}未发现内部冲突{Colors.RESET}\n")
    else:
        for idx, c in enumerate(conflicts, 1):
            severity = c.get("severity", "中")
            conflict_type = c.get("conflict_type", "未知")
            explanation = c.get("explanation", "")
            fact_a = c.get("fact_a", {})
            fact_b = c.get("fact_b", {})

            # 颜色映射
            sev_color = Colors.YELLOW if severity == "中" else (Colors.RED if severity == "高" else Colors.GREEN)

            print(f"{Colors.BOLD}【冲突 {idx}】{Colors.RESET}")
            print(f"  冲突类型: {conflict_type}")
            print(f"  严重程度: {sev_color}{severity}{Colors.RESET}")
            print(f"  说明: {explanation}")
            print(f"  事实A: [{fact_a.get('type', '未知')}] {fact_a.get('content', '')}")
            print(f"    位置: {fact_a.get('location', '')}")
            print(f"  事实B: [{fact_b.get('type', '未知')}] {fact_b.get('content', '')}")
            print(f"    位置: {fact_b.get('location', '')}\n")



import sys

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_file = sys.argv[1]
    else:
        # 使用更简单、更具代表性的测试用例
        target_file = "test_data_simple.txt"
        
    test_automated_flow(target_file)
