"""
单文件实验版本
实现问题分解和搜索增强的功能
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_community.utilities import SearxSearchWrapper
import os
from dotenv import load_dotenv
import json
import requests
import hashlib
import time
from urllib.parse import urlparse

# 尝试导入goose3（网页内容提取库）
try:
    from goose3 import Goose
    GOOSE3_AVAILABLE = True
    goose = Goose()
except ImportError:
    print("警告: goose3 未安装，将无法提取网页内容")
    print("请运行: pip install goose3")
    GOOSE3_AVAILABLE = False
    goose = None

# 加载环境变量
load_dotenv()

# 配置
API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
MODEL = os.getenv("MODEL", "Pro/THUDM/glm-4-9b-chat")
SEARX_HOST = os.getenv("SEARX_HOST", "http://127.0.0.1:8080")

# 邮件配置
TO_EMAIL = os.getenv("TO_EMAIL")
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@example.com")

# 请求间隔配置（秒）
SEARCH_DELAY = float(os.getenv("SEARCH_DELAY", "5"))  # 搜索间隔
WEB_EXTRACT_DELAY = float(os.getenv("WEB_EXTRACT_DELAY", "5"))  # 网页爬取间隔


class WebContentCache:
    """网页内容缓存管理器"""
    
    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(cache_dir, "web_content_cache.json")
        self.cache = {}
        self._load_cache()
    
    def _get_url_hash(self, url: str) -> str:
        """生成URL的哈希值"""
        return hashlib.md5(url.encode('utf-8')).hexdigest()
    
    def _load_cache(self):
        """从文件加载缓存"""
        os.makedirs(self.cache_dir, exist_ok=True)
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
            except Exception as e:
                print(f"加载缓存失败: {str(e)}")
                self.cache = {}
    
    def _save_cache(self):
        """保存缓存到文件"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存缓存失败: {str(e)}")
    
    def get(self, url: str) -> Optional[str]:
        """从缓存获取内容"""
        url_hash = self._get_url_hash(url)
        if url_hash in self.cache:
            print(f"    [缓存命中] {url}")
            return self.cache[url_hash].get('content')
        return None
    
    def set(self, url: str, content: str):
        """缓存内容"""
        url_hash = self._get_url_hash(url)
        self.cache[url_hash] = {
            'url': url,
            'content': content,
            'cached_at': datetime.now().isoformat()
        }
        self._save_cache()


class TreeNode:
    """问题树节点"""
    def __init__(self, question: str, parent=None, depth=0):
        self.question = question
        self.parent = parent
        self.depth = depth
        self.children = []
        self.search_results = []
        self.summary = ""
        self.rationale = ""  # 拆分子问题的依据
        self.asked = False  # 是否已经提出过
        self.is_leaf = False  # 是否是最终叶子节点（无法再分解）
        self.final_summary = ""  # 最终总结（叶子节点的完整总结）
        self.search_query = ""  # 实际使用的搜索查询词
        
    def add_child(self, child):
        """添加子节点"""
        self.children.append(child)
        child.parent = self
        
    def to_dict(self):
        """转换为字典"""
        return {
            "question": self.question,
            "depth": self.depth,
            "summary": self.summary,
            "rationale": self.rationale,
            "children": [c.to_dict() for c in self.children]
        }


class QuestionDecomposer:
    """问题分解和搜索系统"""
    
    def __init__(self):
        # 初始化LLM
        self.llm = ChatOpenAI(
            model=MODEL,
            api_key=API_KEY,
            base_url=BASE_URL,
            temperature=0.7,
            max_tokens=128000
        )
        
        # 初始化搜索工具
        self.searcher = SearxSearchWrapper(searx_host=SEARX_HOST)
        
        # 记录所有已提出的问题
        self.asked_questions = set()
        
        # 中断标志
        self.interrupted = False
        
        # 初始化网页内容缓存
        self.web_cache = WebContentCache()
        
    def process_question(self, root_question: str, max_depth: int = 3):
        """处理问题，进行分解和搜索（支持优雅中断）"""
        print(f"\n开始处理问题: {root_question}")
        
        # 创建根节点
        root = TreeNode(root_question, depth=0)
        self.asked_questions.add(root_question)
        
        try:
            # 第一轮：搜索原问题
            print("\n[第0层] 对原问题进行搜索增强...")
            root.search_results, root.summary, root.search_query = self._search_and_summarize(root_question)
            
            # 递归分解和处理
            self._process_node(root, max_depth, current_depth=1)
            
        except KeyboardInterrupt:
            print("\n\n⚠️  检测到中断信号 (Ctrl+C)")
            self.interrupted = True
            print("正在保存已完成的搜索结果...")
        
        return root
    
    def _process_node(self, node: TreeNode, max_depth: int, current_depth: int):
        """递归处理节点"""
        # 检查是否中断
        if self.interrupted:
            return
            
        if current_depth > max_depth:
            # 到达最大深度，标记为叶子节点并生成最终总结
            if not node.is_leaf:
                print(f"  到达最大深度，生成最终总结")
                node.is_leaf = True
                node.final_summary = self._generate_final_summary(node)
            return
        
        # 如果节点已经搜索过（在第0层），就不再重复搜索
        if node.asked:
            return
        
        try:
            # 分解问题
            print(f"\n[第{current_depth}层] 分解问题: {node.question}")
            sub_questions = self._decompose_question(node.question, node.search_results, node.summary)
            
            # 检查中断
            if self.interrupted:
                return
            
            if not sub_questions:
                print(f"  未生成子问题，生成最终总结")
                # 无法继续分解，标记为叶子节点并生成最终总结
                node.is_leaf = True
                node.final_summary = self._generate_final_summary(node)
                return
            
            # 对每个子问题进行处理
            for sub_q in sub_questions:
                # 再次检查中断
                if self.interrupted:
                    return
                    
                if sub_q['question'] in self.asked_questions:
                    print(f"  跳过重复问题: {sub_q['question']}")
                    continue
                    
                # 标记为已提出
                self.asked_questions.add(sub_q['question'])
                
                # 创建子节点
                child = TreeNode(sub_q['question'], parent=node, depth=current_depth)
                child.rationale = sub_q.get('rationale', '需要进一步分析')
                node.add_child(child)
                
                # 搜索和总结子问题
                print(f"  搜索子问题: {sub_q['question']}")
                child.search_results, child.summary, child.search_query = self._search_and_summarize(sub_q['question'])
                
                # 检查中断
                if self.interrupted:
                    return
                
                # 递归处理子节点
                if current_depth < max_depth:
                    self._process_node(child, max_depth, current_depth + 1)
                else:
                    # 达到最大深度，标记为叶子节点并生成最终总结
                    if not child.is_leaf:
                        child.is_leaf = True
                        child.final_summary = self._generate_final_summary(child)
                        
        except KeyboardInterrupt:
            print("\n\n⚠️  检测到中断信号")
            self.interrupted = True
    
    def _decompose_question(self, question: str, search_results: List, summary: str) -> List[Dict]:
        """分解问题，生成子问题（带重试和反射机制）"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # 第一次尝试：正常请求
                if attempt == 0:
                    prompt = f"""原问题: {question}

已搜索到的内容总结:
{summary if summary else "暂无搜索结果"}

请你分析原问题，并将其分解为2-4个相关子问题。每个子问题应该：
1. 具体、可执行
2. 有助于深入理解原问题
3. 避免重复已经搜索过的内容

请以JSON格式返回，格式：
{{
  "sub_questions": [
    {{
      "question": "子问题内容",
      "rationale": "为什么需要分解这个子问题的理由"
    }}
  ]
}}

只返回JSON，不要其他解释。"""
                else:
                    # 重试时：给出反馈，要求改进
                    prompt = f"""之前的回答格式不正确，请重新分析。

原问题: {question}

已搜索到的内容总结:
{summary if summary else "暂无搜索结果"}

你之前返回的格式可能缺少必需的字段。请确保每个子问题都包含：
- "question": 子问题内容（必需的字符串）
- "rationale": 分解理由（必需的字符串）

请严格以JSON格式返回：
{{
  "sub_questions": [
    {{
      "question": "子问题内容",
      "rationale": "为什么需要分解这个子问题的理由"
    }}
  ]
}}

只返回JSON，不要其他解释。"""
                
                response = self.llm.invoke([
                    SystemMessage(content="你是一个问题分析专家，擅长将复杂问题分解为可执行的子问题。"),
                    HumanMessage(content=prompt)
                ])
                
                content = response.content.strip()
                
                # 移除可能的代码块标记
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                # 尝试解析JSON
                result = json.loads(content)
                sub_questions_raw = result.get("sub_questions", [])
                
                # 验证并规范化子问题
                sub_questions = []
                for sq in sub_questions_raw:
                    if isinstance(sq, dict):
                        # 确保必需的字段存在
                        question_text = sq.get("question", "").strip()
                        rationale_text = sq.get("rationale", "需要进一步分析").strip()
                        
                        if question_text:  # 只添加有效的问题
                            sub_questions.append({
                                "question": question_text,
                                "rationale": rationale_text if rationale_text else "需要进一步分析"
                            })
                
                if sub_questions:
                    print(f"  生成了 {len(sub_questions)} 个子问题")
                    return sub_questions
                else:
                    if attempt < max_retries - 1:
                        print(f"  第{attempt + 1}次尝试未生成有效子问题，重试中...")
                        continue
                    else:
                        print(f"  无法生成有效子问题，放弃")
                        return []
                
            except json.JSONDecodeError as e:
                if attempt < max_retries - 1:
                    print(f"  JSON解析失败（尝试 {attempt + 1}/{max_retries}）: {str(e)}")
                    continue
                else:
                    print(f"  JSON解析失败，已达到最大重试次数")
                    return []
            except Exception as e:
                print(f"  分解问题失败: {str(e)}")
                if attempt < max_retries - 1:
                    print(f"  重试中... ({attempt + 1}/{max_retries})")
                    continue
                else:
                    return []
        
        return []
    
    def _search_and_summarize(self, question: str) -> tuple[List, str, str]:
        """搜索并总结（带重试机制和质量评估），返回 (results, summary, search_query)"""
        max_retries = 3  # 增加重试次数
        search_query = self._generate_search_query(question)
        print(f"    优化后的搜索查询: {search_query}")
        import time
        time.sleep(5)
        
        previous_feedback = []  # 记录之前的反馈理由
        
        for attempt in range(max_retries):
            # 如果是重试，尝试生成不同的搜索查询
            if attempt > 0:
                print(f"    第{attempt + 1}次重试，基于反馈调整搜索策略...")
                alternative_query = self._generate_alternative_search_query(question, attempt, previous_feedback)
                if alternative_query and alternative_query != search_query:
                    search_query = alternative_query
                    print(f"    新的搜索查询: {search_query}")
            
            try:
                # 添加搜索延迟（避免被封禁）
                if attempt > 0:
                    print(f"    等待 {SEARCH_DELAY} 秒后重试搜索...")
                    time.sleep(SEARCH_DELAY)
                
                # 使用优化后的搜索查询进行搜索
                results = self.searcher.results(search_query, engines=['bing'], num_results=40)
                if not results or len(results) <= 1:
                    if attempt < max_retries - 1:
                        print(f"    搜索结果不足，重试中... (尝试 {attempt + 1}/{max_retries})")
                        continue
                    else:
                        return [], "", search_query
                
                # 步骤2：评估搜索结果质量
                print(f"    评估搜索结果质量...")
                is_satisfactory, reason = self._evaluate_search_quality(question, results, search_query)
                
                if not is_satisfactory:
                    if attempt < max_retries - 1:
                        # 记录反馈理由
                        previous_feedback.append({
                            "attempt": attempt + 1,
                            "query": search_query,
                            "reason": reason
                        })
                        print(f"    搜索结果不相关，重试中... (尝试 {attempt + 1}/{max_retries})")
                        continue
                    else:
                        # 达到最大重试次数，生成一个标记为"搜索结果质量不佳"的summary
                        print(f"    ⚠️  已达到最大重试次数，搜索结果质量仍然不佳，暂缓处理此问题")
                        summary = self._generate_fallback_summary(question, previous_feedback)
                        return [], summary, search_query
                
                # 总结搜索结果
                summary = self._summarize_results(question, results)
                
                return results, summary, search_query
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"    搜索失败，重试中... (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                    continue
                else:
                    print(f"    搜索失败: {str(e)}")
                    # 生成fallback summary
                    summary = self._generate_fallback_summary(question, previous_feedback)
                    return [], summary, search_query
        
        # 最终fallback
        summary = self._generate_fallback_summary(question, previous_feedback)
        return [], summary, search_query
    
    def _generate_alternative_search_query(self, question: str, attempt: int, previous_feedback: List) -> str:
        """生成备选搜索查询（基于反馈优化）"""
        # 构建之前的失败记录
        feedback_context = ""
        if previous_feedback:
            feedback_context = "\n\n之前的尝试记录：\n"
            for fb in previous_feedback:
                feedback_context += f"- 尝试{fb['attempt']}: 查询「{fb['query']}」，原因：{fb['reason']}\n"
        
        prompt = f"""原问题: {question}

这是第{attempt + 1}次尝试搜索，之前的搜索结果不相关。
这是之前尝试的过程
{feedback_context}

这是具体的要求，请根据以下要求结合原问题生成。
请基于上述反馈，重新优化搜索查询，要求：
1. 避免之前失败的原因
2. 使用不同的关键词组合
3. 总长度不要超过10个字。

只返回搜索查询词，不要任何解释。"""
        
        try:
            response = self.llm.invoke([
                SystemMessage(content="你是一个搜索查询优化专家，能基于失败反馈生成更好的搜索查询策略。"),
                HumanMessage(content=prompt)
            ])
            
            search_query = response.content.strip()
            if len(search_query) > 200:
                return question
            
            return search_query if search_query else question
            
        except Exception as e:
            print(f"    生成备选查询失败: {str(e)}")
            return question
    
    def _evaluate_search_quality(self, question: str, results: List, search_query: str) -> tuple[bool, str]:
        """评估搜索结果质量，判断是否与问题相关，返回 (是否合格, 反馈理由)"""
        if not results:
            return False, "无搜索结果"
        
        # 构建评估提示
        results_preview = "\n".join([
            f"{i+1}. {r.get('title', '')}: {r.get('snippet', '')[:100]}..."
            for i, r in enumerate(results[:10], 0)
        ])
        
        prompt = f"""问题: {question}
搜索词：{search_query}

请评估以下搜索结果是否与问题相关：

搜索结果:
{results_preview}

请判断：
1. 搜索结果是否与问题主题相关？
2. 搜索结果是否为问题提供了有用的信息？
3. 是否存在大量无关或低质量内容？

注意：
1. 只要足够有5条以上能够满足即可，不需要全部都覆盖。

请以JSON格式返回：
{{
  "satisfactory": true/false,
  "reason": "评估理由（简短）"
}}

只返回JSON，不要其他解释。"""
        
        try:
            response = self.llm.invoke([
                SystemMessage(content="你是一个搜索结果质量评估专家，能准确判断搜索结果与问题的相关性和有用性。"),
                HumanMessage(content=prompt)
            ])
            
            content = response.content.strip()
            # 移除代码块标记
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            result = json.loads(content)
            satisfactory = result.get("satisfactory", False)
            reason = result.get("reason", "")
            
            if satisfactory:
                print(f"    ✓ 搜索结果质量合格")
            else:
                print(f"    ✗ 搜索结果质量不合格: {reason}")
            
            return satisfactory, reason
            
        except Exception as e:
            print(f"    质量评估失败: {str(e)}")
            # 评估失败时默认认为结果可用（避免阻塞）
            return True, "评估失败"
    
    def _generate_fallback_summary(self, question: str, previous_feedback: List) -> str:
        """生成fallback总结（当搜索结果质量不佳时）"""
        feedback_info = ""
        if previous_feedback:
            feedback_info = "\n之前的尝试反馈：\n" + "\n".join([
                f"- 尝试{i}: {fb['reason']}"
                for i, fb in enumerate(previous_feedback, 1)
            ])
        
        return f"""【搜索结果质量不佳，暂缓处理】

问题: {question}

说明: 经过多次搜索尝试，搜索结果与问题主题相关性不足，无法获取有效信息。

原因分析:
{feedback_info if feedback_info else "搜索结果与问题主题不相关，或提供的信息质量不佳。"}

建议: 可以尝试：
1. 重新表述问题，使其更加具体
2. 使用不同的搜索关键词
3. 缩小问题范围
4. 在后续的深度学习中再次处理此问题
"""
    
    def _generate_search_query(self, question: str) -> str:
        """使用大模型生成更适合搜索引擎的搜索查询词"""
        prompt = f"""原问题: {question}

请将这个问题转换为一个简洁、准确的搜索查询词，要求：
1. 保留核心关键词
2. 适合搜索引擎检索
3. 总长度不要超过10个字

只返回搜索查询词，不要任何解释。"""
        
        try:
            response = self.llm.invoke([
                SystemMessage(content="你是一个搜索查询优化专家，能将自然语言问题转换为高效的搜索关键词。"),
                HumanMessage(content=prompt)
            ])
            
            search_query = response.content.strip()
            # 如果返回了意外的格式，使用原问题
            if len(search_query) > 200:
                return question
            
            return search_query if search_query else question
            
        except Exception as e:
            print(f"    生成搜索查询失败: {str(e)}，使用原问题")
            return question
    
    def _rerank_search_results(self, question: str, results: List) -> List[Dict]:
        """根据与问题的相关性对搜索结果进行重排"""
        if not results:
            return []
        
        # 构建提示，让LLM重排结果
        results_info = []
        for i, r in enumerate(results, 1):
            results_info.append({
                "index": i,
                "title": r.get('title', ''),
                "snippet": r.get('snippet', ''),
                "link": r.get('link', '')
            })
        
        prompt = f"""问题: {question}

请根据与问题的相关性，对以下搜索结果进行评分（0-100分），并返回最相关的Top10结果。
请以JSON格式返回，格式：
{{
  "top_results": [
    {{
      "index": 结果编号,
      "relevance_score": 相关性评分,
      "reason": "评分理由（简短）"
    }}
  ]
}}

搜索结果:
{json.dumps(results_info, ensure_ascii=False, indent=2)}

只返回JSON，不要其他解释。"""
        
        try:
            response = self.llm.invoke([
                SystemMessage(content="你是一个搜索结果相关性评估专家，能够准确判断搜索结果与问题的相关程度。"),
                HumanMessage(content=prompt)
            ])
            
            content = response.content.strip()
            # 移除代码块标记
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            result = json.loads(content)
            top_results = result.get('top_results', [])
            
            # 按relevance_score降序排序
            sorted_results = sorted(top_results, key=lambda x: x.get('relevance_score', 0), reverse=True)
            
            # 取Top5（如果用户要求Top10，也应该限制为5，因为我们只需要5个用于网页提取）
            top5_sorted = sorted_results[:5]
            
            # 按相关性排序重组结果
            reranked = []
            for item in top5_sorted:
                idx = item['index']
                if 1 <= idx <= len(results):
                    reranked.append(results[idx - 1])
            
            return reranked
            
        except Exception as e:
            print(f"    重排失败，使用原顺序: {str(e)}")
            return results[:5]  # 失败时返回前5个
    
    def _extract_webpage_content(self, url: str) -> Optional[str]:
        """使用goose3提取网页内容（带缓存）"""
        # 先检查缓存
        cached_content = self.web_cache.get(url)
        if cached_content is not None:
            return cached_content
        
        if not GOOSE3_AVAILABLE or not goose:
            return None
            
        try:
            # 使用goose3提取网页内容
            article = goose.extract(url=url)
            content = article.cleaned_text
            if not content:
                # 将description keywords title进行拼接
                meta = article.infos.get("meta", {})
                content_parts = []
                if meta.get('description'):
                    content_parts.append(meta['description'])
                if meta.get('keywords'):
                    content_parts.append(meta['keywords'])
                if article.title:
                    content_parts.append(article.title)
                content = ' '.join(content_parts)
            # 存入缓存
            if content:
                self.web_cache.set(url, content)
            
            return content
        except Exception as e:
            print(f"    网页提取失败 ({url}): {str(e)}")
            return None
    
    def _summarize_results(self, question: str, results: List) -> str:
        """总结搜索结果（带相关性重排和网页内容提取）"""
        if not results:
            return "暂无搜索结果"
        
        # 步骤1：按相关性重排搜索结果
        print("    正在按相关性重排搜索结果...")
        reranked_results = self._rerank_search_results(question, results)
        
        if not reranked_results:
            # 如果重排失败，使用原始结果前5个
            reranked_results = results[:5]
        
        # 步骤2：对Top5结果进行网页内容提取
        enhanced_results = []
        for i, result in enumerate(reranked_results[:5], 1):
            url = result.get('link', '')
            if url:
                print(f"    提取网页内容 ({i}/5): {url}")
                # 添加爬取延迟（避免被封禁）
                if i > 1:  # 第一个不需要延迟
                    time.sleep(WEB_EXTRACT_DELAY)
                
                web_content = self._extract_webpage_content(url)
                print(f"{url}\n {web_content}")
                enhanced_result = {
                    'title': result.get('title', ''),
                    'snippet': result.get('snippet', ''),
                    'link': url,
                    'web_content': web_content if web_content else None
                }
                enhanced_results.append(enhanced_result)
            else:
                enhanced_results.append(result)
        
        # 步骤3：构建用于总结的内容
        context = f"问题: {question}\n\n搜索到的信息:\n\n"
        
        for i, result in enumerate(enhanced_results, 1):
            context += f"{i}. 标题: {result.get('title', '无标题')}\n"
            context += f"   URL: {result.get('link', '无链接')}\n"
            
            # 如果有网页内容，使用它；否则使用摘要
            if result.get('web_content'):
                # 限制网页内容长度，尽量控制在合理范围内
                web_content = result['web_content']
                # 如果内容太长，截取前5000字符（模型支持128k，这里留够余量）
                if len(web_content) > 10000:
                    web_content = web_content[:10000] + "\n\n[内容已截断]"
                context += f"   内容:\n{web_content}\n\n"
            elif result.get('snippet'):
                context += f"   摘要: {result['snippet']}\n\n"
            else:
                context += "   内容: 无可用内容\n\n"
        
        # 步骤4：使用LLM提取关键信息
        prompt = f"""请基于以下搜索到的信息，提取与问题相关的关键信息，用中文总结：

{context}

请提供：
1. 问题的核心答案
2. 关键事实和数据
3. 重要的细节信息
4. 相关的建议或注意事项

以清晰、有条理的方式呈现总结。"""
        
        try:
            response = self.llm.invoke([
                SystemMessage(content="你是一个信息总结专家，能从搜索结果和网页内容中提取关键信息，并能清晰、有条理地呈现总结。"),
                HumanMessage(content=prompt)
            ])
            return response.content
        except Exception as e:
            print(f"    总结生成失败: {str(e)}")
            return f"总结生成失败: {str(e)}"
    
    def _generate_final_summary(self, node: TreeNode) -> str:
        """为叶子节点生成最终总结（包含所有相关信息）"""
        if not node.summary:
            return node.question
        
        # 如果有搜索结果，生成更详细的最终总结
        if node.search_results:
            # 提取完整信息
            info_parts = [
                f"问题: {node.question}",
                f"搜索结果摘要: {node.summary}",
            ]
            
            # 如果有答案链接，添加到总结中
            if node.search_results:
                links = [r.get('link', '') for r in node.search_results[:3] if r.get('link')]
                if links:
                    info_parts.append(f"\n参考资源: {' | '.join(links)}")
            
            return "\n".join(info_parts)
        
        return node.summary
    
    def visualize_tree(self, root: TreeNode) -> str:
        """可视化树结构（标记叶子节点）"""
        lines = []
        
        def traverse(node: TreeNode, prefix: str = "", is_last: bool = True):
            # 绘制当前节点（如果是叶子节点，标记为 *）
            connector = "└── " if is_last else "├── "
            leaf_marker = "🔍" if node.is_leaf else ""
            lines.append(f"{prefix}{connector}{leaf_marker} {node.question}")
            
            if not node.children:
                return
            
            # 更新前缀
            extension = "    " if is_last else "│   "
            new_prefix = prefix + extension
            
            # 遍历子节点
            for i, child in enumerate(node.children):
                is_last_child = (i == len(node.children) - 1)
                traverse(child, new_prefix, is_last_child)
        
        traverse(root)
        return "\n".join(lines)
    
    def generate_email(self, root: TreeNode) -> str:
        """生成邮件内容（按层次遍历顺序）"""
        # 收集所有问题、答案和叶子节点（按层次分组）
        data_by_depth = {}  # {depth: [nodes]}
        all_nodes = []
        leaf_nodes = []  # 叶子节点列表
        all_urls = set()  # 所有访问过的URL
        
        def collect_data(node: TreeNode):
            all_nodes.append(node)
            
            # 收集URL
            if node.search_results:
                for result in node.search_results:
                    url = result.get('link', '')
                    if url:
                        all_urls.add(url)
            
            if node.summary:
                if node.depth not in data_by_depth:
                    data_by_depth[node.depth] = []
                data_by_depth[node.depth].append({
                    "question": node.question,
                    "summary": node.summary,
                    "depth": node.depth,
                    "search_query": node.search_query if node.search_query else node.question,
                    "urls": [r.get('link', '') for r in node.search_results if r.get('link', '')]
                })
            
            # 如果是叶子节点，记录详细信息
            if node.is_leaf:
                leaf_nodes.append({
                    "question": node.question,
                    "final_summary": node.final_summary if node.final_summary else node.summary,
                    "depth": node.depth,
                    "search_results": node.search_results,
                    "search_query": node.search_query if node.search_query else node.question
                })
            
            for child in node.children:
                collect_data(child)
        
        collect_data(root)
        
        # 按host归类URL
        host_urls = {}  # {host: [urls]}
        for url in all_urls:
            try:
                parsed = urlparse(url)
                host = parsed.netloc
                if host not in host_urls:
                    host_urls[host] = []
                host_urls[host].append(url)
            except Exception:
                # URL解析失败，单独存放
                if 'unknown' not in host_urls:
                    host_urls['unknown'] = []
                host_urls['unknown'].append(url)
        
        # 生成邮件头部
        email = f"""问题: {root.question}
批次号: {datetime.now().strftime('%Y%m%d_%H%M%S')}
{"⚠️  注意：此报告因中断而未完成，仅包含部分结果" if self.interrupted else ""}

搜索关键词
{root.search_query if root.search_query else root.question}
"""
        
        # 0. 展示访问过的网站host归类（新增）
        if host_urls:
            email += f"\n{'='*60}\n访问过的网站归类\n{'='*60}\n"
            sorted_hosts = sorted(host_urls.keys())
            for host in sorted_hosts:
                urls = host_urls[host]
                email += f"\n📌 {host} (共{len(urls)}个页面)\n"
            email += f"\n{'='*60}\n"
        
        # 1. 先展示问题树结构
        email += f"\n{'='*60}\n问题树结构\n{'='*60}\n"
        email += f"{self.visualize_tree(root)}\n"
        email += f"{'='*60}\n"
        
        # 2. 按层次遍历展示内容
        email += f"\n{'='*60}\n按层次分解和搜索过程\n{'='*60}\n"
        
        # 按深度从浅到深排序
        sorted_depths = sorted(data_by_depth.keys())
        
        for depth in sorted_depths:
            nodes_at_depth = data_by_depth[depth]
            email += f"\n【第{depth}层】共{len(nodes_at_depth)}个问题\n"
            email += "─" * 60 + "\n"
            
            for i, item in enumerate(nodes_at_depth, 1):
                email += f"\n{i}. {item['question']}\n"
                email += f"   搜索词: {item['search_query']}\n"
                email += f"   总结:\n   {item['summary']}\n"
                email += "─" * 40 + "\n"
        
        # 3. 添加叶子节点的最终总结
        if leaf_nodes:
            email += f"\n\n{'='*60}\n最终搜索结果总结（叶子节点答案）\n{'='*60}\n"
            for i, leaf in enumerate(leaf_nodes, 1):
                email += f"\n【最终答案 {i}】第{leaf['depth']}层: {leaf['question']}\n"
                email += f"搜索词: {leaf['search_query']}\n"
                email += f"{leaf['final_summary']}\n"
                email += "─" * 60 + "\n"
        
        # 4. 添加引用URL列表
        if all_urls:
            email += f"\n\n{'='*60}\n引用来源\n{'='*60}\n"
            sorted_url_list = sorted(list(all_urls))
            for i, url in enumerate(sorted_url_list, 1):
                email += f"{i}. {url}\n"
            email += f"\n{'='*60}\n"
        
        email += f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return email
    
    def save_and_send_email(self, email_content: str):
        """保存邮件并尝试发送"""
        # 保存到文件
        os.makedirs("data/results", exist_ok=True)
        filename = f"data/results/report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(email_content)
        
        print(f"\n报告已保存到: {filename}")
        
        # 如果有配置，尝试发送邮件
        if TO_EMAIL:
            try:
                import requests
                domain = os.getenv("MAILGUN_DOMAIN")
                api_key = os.getenv("MAILGUN_API_KEY")
                
                if domain and api_key:
                    response = requests.post(
                        f"https://api.mailgun.net/v3/{domain}/messages",
                        auth=('api', api_key),
                        data={
                            "from": FROM_EMAIL,
                            "to": TO_EMAIL,
                            "subject": "问题分析报告",
                            "text": email_content
                        }
                    )
                    if response.status_code == 200:
                        print(f"报告已发送到邮箱: {TO_EMAIL}")
                    else:
                        print(f"邮件发送失败: {response.status_code}")
                else:
                    print("邮件配置不完整，跳过发送")
            except Exception as e:
                print(f"发送邮件失败: {str(e)}")


def main():
    """主函数"""
    import sys
    
    if len(sys.argv) > 1:
        question = sys.argv[1]
    else:
        question = input("请输入要分析的问题: ")
    
    if not question:
        print("问题不能为空")
        return
    
    # 创建分解器
    decomposer = QuestionDecomposer()
    
    # 处理问题
    root = decomposer.process_question(question, max_depth=15)
    
    # 生成邮件
    email_content = decomposer.generate_email(root)
    
    # 保存并发送
    decomposer.save_and_send_email(email_content)
    
    print("\n处理完成！")


if __name__ == "__main__":
    main()
