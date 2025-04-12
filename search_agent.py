from typing import List, Dict, Any
import autogen
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
import json
import os
from datetime import datetime
import requests
from langchain_community.utilities import SearxSearchWrapper

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
            你需要：
            1. 分析主题的核心概念
            2. 提取3-5个核心关键词
            3. 生成2-3个相关子主题
            4. 评估主题的搜索难度
            """,
            llm_config=self.llm_config
        )
        
        # 创建搜索执行器
        self.search_executor = AssistantAgent(
            name="search_executor",
            system_message="""你是一个搜索执行专家，负责执行搜索请求并管理搜索结果。
            你可以使用 get_search_page 函数来执行搜索。如果你发现当前场景不适合调用工具，请进行详细说明原因。
            你需要：
            1. 根据分析结果构建合适的搜索查询
            2. 执行搜索并获取结果
            """,
            llm_config=self.llm_config
        )
        
        # 创建内容记录器
        self.content_recorder = AssistantAgent(
            name="content_recorder",
            system_message="""你是一个内容记录专家，负责记录和总结搜索结果。
            你需要：
            1. 对搜索结果进行分类和标记
            2. 生成结构化摘要
            3. 评估内容完整性
            4. 提取关键点
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
                
                return json.dumps(search_result, ensure_ascii=False, indent=2)
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
    
    def _state_transition(self, last_speaker, groupchat):
        """定义对话状态转换"""
        if last_speaker is self.topic_analyzer:
            return self.search_executor
        elif last_speaker is self.search_executor:
            return self.user_proxy
        elif last_speaker is self.user_proxy:
            return self.content_recorder
        elif last_speaker is self.content_recorder:
            return self.topic_analyzer
        else:
            return self.topic_analyzer
    
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