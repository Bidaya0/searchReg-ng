from typing import List, Dict, Any
import autogen
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
import json
import os
from datetime import datetime
import requests
from langchain_community.utilities import SearxSearchWrapper
import yaml
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class SearchAgentSystem:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.llm_config = {
            "config_list": [
                {
                    "model": config.get("model"),
                    "api_key": config.get("api_key"),
                    "base_url": config.get("base_url")
                }
            ],
            "temperature": 0.7,
            "max_tokens": 1000,
        }
        
        # 初始化 Searx 搜索
        self.search = SearxSearchWrapper(searx_host=config.get("searx_host", "http://127.0.0.1:8080"))
        
        # 初始化代理
        self.topic_analyzer = AssistantAgent(
            name="topic_analyzer",
            system_message="""你是一个主题分析专家，负责分析用户输入的主题，提取关键词和生成搜索建议。
            你不需要对前文做出总结和附和，只需要关注你手中的任务即可， 避免重复你的上一个人的话语，从而基于上下文不断提出新观点。
            你需要：
            1. 分析主题的核心概念
            2. 评估主题的搜索结果，当还没有进行过搜索时，不需要执行。
            3. 当前文中有搜索的结果之后，根据搜索结果及总结的内容，生成的主题并深入讨论。
            4. 给其他人提供搜索建议，强调你还需要的资料内容。
            """,
            llm_config=self.llm_config
        )
        
        # 创建搜索执行器
        self.search_executor = AssistantAgent(
            name="search_executor",
            system_message="""你是一个搜索执行专家，负责执行搜索请求并管理搜索结果。
            你不需要对前文做出总结和附和，只需要创造性的向下进行新的搜索即可。
            你也不需要给出搜索建议，只需要想办法尽可能地调用工具执行搜索。
            
            你必须：
            1. 在每次对话中至少执行一次搜索工具调用
            2. 如果无法执行搜索，必须明确说明原因
            3. 根据搜索结果生成新的搜索查询
            4. 评估搜索结果的相关性
            
            你可以使用 get_search_page 函数来执行搜索。每次对话必须尝试执行搜索，除非：
            - 已经获取到足够的相关结果
            - 遇到明确的错误提示
            - 需要等待其他代理的输入
            
            如果搜索失败，你需要：
            1. 明确说明失败原因
            2. 建议可能的解决方案
            3. 请求其他代理的帮助
            
            搜索执行流程：
            1. 接收主题分析结果
            2. 构建搜索查询
            3. 执行搜索
            4. 评估结果
            5. 决定是否需要继续搜索
            """,
            llm_config=self.llm_config
        )
        
        # 添加消息历史记录
        self.message_history = []
        self.similarity_threshold = 0.8  # 相似度阈值
        self.max_repeats = 2  # 最大重复次数
        
        # 创建内容记录器
        self.content_recorder = AssistantAgent(
            name="content_recorder",
            system_message="""你是一个内容记录专家，负责记录和总结搜索结果。
            你需要：
            1. 对搜索结果进行分类和标记
            2. 生成结构化摘要
            3. 评估内容完整性
            4. 提取关键点
            5. 避免重复之前已经讨论过的内容
            """,
            llm_config=self.llm_config
        )
        
        # 创建用户代理
        self.user_proxy = UserProxyAgent(
            name="user_proxy",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=10,
        )
        
        # 注册搜索函数
        @self.user_proxy.register_for_execution()
        @self.search_executor.register_for_llm(description="执行搜索并返回结果， 请试图使用自然语言查找合适的文本")
        def get_search_page(query: str, max_results: int = 20) -> str:
            """执行搜索并返回格式化的结果"""
            try:
                results = self.search.results(
                    query,
                    engines=['presearch'],
                    num_results=max_results
                )
                
                if len(results) == 1:
                    return "搜索失败，请重试或尝试其他查询。"
                
                # 格式化搜索结果
                search_result = [
                    {
                        "title": i.get("title", ""),
                        "snippet": i.get("snippet", ""),
                        "link": i.get("link", "")
                    } for i in results
                ]
                
                # 保存搜索结果
                self._save_to_file(
                    {"query": query, "results": search_result},
                    "cache",
                    f"search_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )
                
                return yaml.dump(search_result, allow_unicode=True)
            except Exception as e:
                raise Exception(f"搜索执行失败: {str(e)}")
        
        # 创建群组聊天
        self.groupchat = GroupChat(
            agents=[self.user_proxy, self.topic_analyzer, self.search_executor, self.content_recorder],
            messages=[],
            max_round=50,
            speaker_selection_method=self._state_transition,
        )
        
        self.manager = GroupChatManager(groupchat=self.groupchat, llm_config=self.llm_config)
        
        # 初始化本地存储
        self._init_storage()
    
    def _init_storage(self):
        """初始化本地存储目录"""
        storage_dirs = [
            "./data/cache",
            "./data/results",
            "./data/logs"
        ]
        
        for dir_path in storage_dirs:
            os.makedirs(dir_path, exist_ok=True)
    
    def _save_to_file(self, data: Dict, file_type: str, filename: str):
        """保存数据到本地文件"""
        file_path = f"./data/{file_type}/{filename}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _calculate_message_similarity(self, message1: str, message2: str) -> float:
        """计算两条消息的相似度"""
        vectorizer = TfidfVectorizer()
        try:
            tfidf_matrix = vectorizer.fit_transform([message1, message2])
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            return similarity
        except:
            return 0.0

    def _check_message_repetition(self, new_message: str) -> bool:
        """检查新消息是否与历史消息重复"""
        if not self.message_history:
            return False
            
        # 计算与最近5条消息的相似度
        recent_messages = self.message_history[-5:]
        similarities = [self._calculate_message_similarity(new_message, msg) for msg in recent_messages]
        
        # 如果与任何一条消息的相似度超过阈值，则认为重复
        return any(sim > self.similarity_threshold for sim in similarities)

    def _evaluate_dialogue_quality(self, messages: List[Dict]) -> bool:
        """评估对话质量"""
        if not messages:
            return True
            
        # 获取最近的5条消息
        recent_messages = messages[-5:]
        contents = [msg.get("content", "") for msg in recent_messages if msg.get("content")]
        
        # 检查重复
        for i in range(len(contents)):
            for j in range(i+1, len(contents)):
                similarity = self._calculate_message_similarity(contents[i], contents[j])
                print("相似度",similarity)
                if similarity > self.similarity_threshold:
                    return False
                    
        return True

    def _state_transition(self, last_speaker, groupchat):
        """改进的对话状态转换逻辑"""
        # 获取最近的对话消息
        recent_messages = groupchat.messages[-5:] if len(groupchat.messages) > 5 else groupchat.messages
        
        # 更新消息历史
        if recent_messages:
            self.message_history.append(recent_messages[-1].get("content", ""))
            
        # 检查对话质量
        if not self._evaluate_dialogue_quality(recent_messages):
            print("对话质量不佳，结束对话",)
            return None  # 如果质量不佳，结束对话
        
        # 默认的第二个接话的是topic_analyzer
        if len(groupchat.messages) < 2:
            return self.topic_analyzer
        if last_speaker is self.topic_analyzer:
            # 检查是否需要继续搜索
            if self._should_continue_search(recent_messages):
                return self.search_executor
            else:
                return self.content_recorder
        elif last_speaker is self.search_executor:
            # 检查是否有工具调用请求
            if self._has_tool_call_request(recent_messages):
                return self.user_proxy
            else:
                return None
        elif last_speaker is self.content_recorder:
            # 检查是否需要继续对话
            if self._should_continue_dialogue(recent_messages):
                return self.topic_analyzer
            else:
                return None
        else:
            return self.topic_analyzer

    def _should_continue_search(self, messages: List[Dict]) -> bool:
        """评估是否需要继续搜索"""
        # 检查是否有足够的搜索结果
        search_results = [msg for msg in messages if msg.get("role") == "assistant" and "search_results" in msg.get("content", "")]
        if len(search_results) >= 3:  # 如果已经有3次搜索结果，可能不需要继续
            return False
            
        # 检查是否有明确的停止信号
        last_message = messages[-1] if messages else {}
        if "停止搜索" in last_message.get("content", ""):
            return False
            
        return True

    def _has_tool_call_request(self, messages: List[Dict]) -> bool:
        """检查是否有工具调用请求"""
        last_message = messages[-1] if messages else {}
        tool_calls = last_message.get("tool_calls", "")
        
        # 检查是否包含工具调用请求
        if tool_calls:
            return True
            
        return False

    def _was_search_successful(self, messages: List[Dict]) -> bool:
        """评估搜索是否成功"""
        last_message = messages[-1] if messages else {}
        content = last_message.get("content", "")
        
        # 检查是否有搜索结果
        if "search_results" in content:
            return True
            
        # 检查是否有错误信息
        if "搜索失败" in content or "错误" in content:
            return False
            
        return False

    def _should_continue_dialogue(self, messages: List[Dict]) -> bool:
        """评估是否需要继续对话"""
        # 检查对话轮次
        if len(messages) >= 20:  # 最大对话轮次
            return False
            
        # 检查是否有明确的结束信号
        last_message = messages[-1] if messages else {}
        if "结束对话" in last_message.get("content", ""):
            return False
            
        # 检查对话质量
        if not self._evaluate_dialogue_quality(messages):
            return False
            
        return True

    def process_topic(self, topic: str) -> Dict:
        """处理完整的工作流程"""
        try:
            # 开始群组对话
            chat_result = self.user_proxy.initiate_chat(
                self.manager,
                message=f"""主题：{topic}
                请分析这个主题，执行搜索，并总结结果。"""
            )
            
            # 保存对话历史
            self._save_to_file(
                chat_result.chat_history,
                "logs",
                f"chat_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            
            return {
                "status": "success",
                "chat_history": chat_result.chat_history
            }
            
        except Exception as e:
            # 错误处理
            error_log = {
                "error": str(e),
                "topic": topic,
                "timestamp": datetime.now().isoformat()
            }
            self._save_to_file(error_log, "logs", f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            
            return {
                "status": "error",
                "error": str(e)
            } 