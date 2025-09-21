from typing import Dict, Any, List
from datetime import datetime
from autogen import AssistantAgent, UserProxyAgent
from storage import StorageFactory
from storage.models import QuestionsResult, QuestionDirection, QuestionItem


class QuestionAgentSystem:
    """接受主题，基于5个方向生成25个高质量问题的独立流程"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.llm_config = {
            "config_list": [
                {
                    "model": config.get("model"),
                    "api_key": config.get("api_key"),
                    "base_url": config.get("base_url"),
                }
            ],
            "temperature": config.get("temperature", 0.7),
            "max_tokens": config.get("max_tokens", 1500),
        }

        self.storage = StorageFactory.create_storage(
            "file_system",
            {"base_dir": "./data"},
        )

        # 只需要一个负责结构化产出的助手
        self.question_maker = AssistantAgent(
            name="question_maker",
            system_message=(
                "你是一名问题设计专家。\n"
                "- 输入：用户给定的主题\n"
                "- 任务：围绕该主题，从5个互补且覆盖全面的方向提出共计25个高质量问题（每个方向5个）。\n"
                "- 输出：用严格的JSON返回，包含5个方向的名称、每个方向的设计动机（rationale）、以及5条清晰、可执行的问题。\n"
                "- 约束：\n"
                "  1) 问题要具体、可回答，避免空泛；\n"
                "  2) 5个方向之间应有区分度，覆盖视角包括但不限于：背景/现状、目标/价值、方案/实现、风险/挑战、评估/指标 等；\n"
                "  3) 严格输出为JSON，不要自然语言解释；\n"
                "  4) 禁止使用任何代码围栏（例如 ```json 或 ```），直接输出纯JSON文本；\n"
                "  4) 问题使用中文。\n"
                "- JSON模式：\n"
                "{\n"
                "  \"directions\": [\n"
                "    {\n"
                "      \"direction\": \"方向名称\",\n"
                "      \"rationale\": \"该方向为何重要的简述\",\n"
                "      \"questions\": [\n"
                "        {\"question\": \"问题1\"},\n"
                "        {\"question\": \"问题2\"},\n"
                "        {\"question\": \"问题3\"},\n"
                "        {\"question\": \"问题4\"},\n"
                "        {\"question\": \"问题5\"}\n"
                "      ]\n"
                "    }, ... 共5个方向\n"
                "  ]\n"
                "}\n"
            ),
            llm_config=self.llm_config,
        )

        self.user_proxy = UserProxyAgent(
            name="user_proxy",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=0,
            code_execution_config=False,
        )

    @staticmethod
    def _extract_json_from_text(text: str) -> Dict[str, Any]:
        """尽力从可能包含代码围栏或解释文本的内容中提取JSON对象"""
        import json
        import re

        if not text:
            return {}

        # 去除常见代码围栏 ```json ... ``` 或 ``` ... ```
        fenced_match = re.search(r"```[a-zA-Z]*\n([\s\S]*?)```", text)
        if fenced_match:
            candidate = fenced_match.group(1).strip()
            try:
                return json.loads(candidate)
            except Exception:
                pass

        # 直接尝试整体解析
        try:
            return json.loads(text)
        except Exception:
            pass

        # 兜底：提取第一个以 { 开头到对应 } 的片段（简单括号计数）
        start = text.find("{")
        if start != -1:
            brace = 0
            for i in range(start, len(text)):
                if text[i] == '{':
                    brace += 1
                elif text[i] == '}':
                    brace -= 1
                    if brace == 0:
                        fragment = text[start : i + 1]
                        try:
                            return json.loads(fragment)
                        except Exception:
                            break
        return {}

    def generate_questions(self, topic: str) -> Dict[str, Any]:
        """主流程：请求LLM生成结构化JSON并落盘"""
        prompt = (
            f"主题：{topic}\n"
            f"请基于该主题生成5个方向、共25个问题，严格遵守系统消息中的JSON格式返回。"
        )

        # 直接与助手对话，期望其返回JSON字符串
        import pdb; pdb.set_trace()
        response = self.user_proxy.initiate_chat(self.question_maker, message=prompt)
        content = response.chat_history[-1].get("content", "{}") if response and response.chat_history else "{}"

        # 解析并规范化
        parsed = self._extract_json_from_text(content)
        directions_raw = parsed.get("directions", []) if isinstance(parsed, dict) else []

        directions: List[QuestionDirection] = []
        total_questions = 0
        for d in directions_raw:
            direction_name = d.get("direction") or "未命名方向"
            rationale = d.get("rationale")
            questions_list = d.get("questions", [])
            items: List[QuestionItem] = []
            for q in questions_list[:5]:
                q_text = q.get("question") if isinstance(q, dict) else str(q)
                if not q_text:
                    continue
                items.append(QuestionItem(question=q_text))
            total_questions += len(items)
            directions.append(
                QuestionDirection(direction=direction_name, rationale=rationale, questions=items)
            )

        result = QuestionsResult(
            topic=topic,
            directions=directions,
            total_questions=total_questions,
            timestamp=datetime.now(),
        )

        # 保存结果
        self.storage.save(
            result.dict(),
            "results",
            f"questions_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        )

        # 将原始响应也缓存，便于问题定位
        try:
            self.storage.save(
                {"topic": topic, "raw": content},
                "cache",
                f"questions_raw_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            )
        except Exception:
            pass

        return result.dict()


