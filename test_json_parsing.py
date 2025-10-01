#!/usr/bin/env python3
"""
测试JSON解析功能
"""

import json
import re
from typing import Dict, Any

def _extract_json_from_text(text: str) -> Dict[str, Any]:
    """从文本中提取JSON，支持多种格式"""
    if not text:
        print("文本为空，返回空字典")
        return {}
    
    print(f"开始提取JSON，文本长度: {len(text)}")
    
    # 1. 去除常见代码围栏 ```json ... ``` 或 ``` ... ```
    fenced_match = re.search(r"```[a-zA-Z]*\n([\s\S]*?)```", text)
    if fenced_match:
        candidate = fenced_match.group(1).strip()
        print(f"找到代码围栏，尝试解析: {candidate[:100]}...")
        try:
            result = json.loads(candidate)
            print("代码围栏解析成功")
            return result
        except Exception as e:
            print(f"代码围栏解析失败: {str(e)}")
    
    # 2. 直接尝试整体解析
    try:
        result = json.loads(text.strip())
        print("直接解析成功")
        return result
    except Exception as e:
        print(f"直接解析失败: {str(e)}")
    
    # 3. 查找JSON对象边界（支持嵌套）
    start = text.find("{")
    if start != -1:
        brace_count = 0
        in_string = False
        escape_next = False
        
        for i in range(start, len(text)):
            char = text[i]
            
            if escape_next:
                escape_next = False
                continue
                
            if char == '\\':
                escape_next = True
                continue
                
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
                
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        fragment = text[start:i + 1]
                        print(f"找到JSON片段，尝试解析: {fragment[:100]}...")
                        try:
                            result = json.loads(fragment)
                            print("JSON片段解析成功")
                            return result
                        except Exception as e:
                            print(f"JSON片段解析失败: {str(e)}")
                            break
    
    print("所有解析方法都失败，返回空字典")
    return {}

def test_json_parsing():
    """测试JSON解析"""
    print("=== 测试JSON解析功能 ===")
    
    # 测试用例1：正常的JSON
    test_json = """{
  "directions": [
    {
      "direction": "背景/现状",
      "rationale": "理解多agent工作流创作的背景和现状有助于更好地设计适合需求的工作流。",
      "questions": [
        {"question": "当前多agent工作流的主要应用领域有哪些？"},
        {"question": "多agent工作流的发展历程是怎样的？"},
        {"question": "目前多agent工作流面临的主要挑战是什么？"},
        {"question": "多agent工作流与传统工作流的区别是什么？"},
        {"question": "多agent工作流的技术栈有哪些？"}
      ]
    }
  ]
}"""
    
    print("\n测试用例1：正常JSON")
    result = _extract_json_from_text(test_json)
    print(f"解析结果: {result}")
    
    # 测试用例2：带代码围栏的JSON
    test_json_fenced = """```json
{
  "directions": [
    {
      "direction": "背景/现状",
      "rationale": "理解多agent工作流创作的背景和现状有助于更好地设计适合需求的工作流。",
      "questions": [
        {"question": "当前多agent工作流的主要应用领域有哪些？"}
      ]
    }
  ]
}
```"""
    
    print("\n测试用例2：带代码围栏的JSON")
    result = _extract_json_from_text(test_json_fenced)
    print(f"解析结果: {result}")
    
    # 测试用例3：不完整的JSON
    test_json_incomplete = """{
  "directions": [
    {
      "direction": "背景/现状",
      "rationale": "理解多agent工作流创作的背景和现状有助于更好地设计适合需求的工作流。",
      "questions": [
        {"question": "当前多agent工作流的主要应用领域有哪些？"}
      ]
    }
  ]
"""
    
    print("\n测试用例3：不完整的JSON")
    result = _extract_json_from_text(test_json_incomplete)
    print(f"解析结果: {result}")

if __name__ == "__main__":
    test_json_parsing()
