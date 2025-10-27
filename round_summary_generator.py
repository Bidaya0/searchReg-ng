"""
轮次摘要生成器
实现为每个轮次生成摘要的逻辑，提取关键方向、核心发现、重要洞察
"""

from typing import Dict, Any, List, Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from storage_models import RoundReport
from logger import workflow_logger
from datetime import datetime
import json
import re


class RoundSummaryGenerator:
    """轮次摘要生成器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # 初始化LLM
        self.llm = ChatOpenAI(
            model=config.get("model"),
            api_key=config.get("api_key"),
            base_url=config.get("base_url"),
            temperature=config.get("temperature", 0.7),
            max_tokens=config.get("max_tokens", 1000)
        )
        
        # 无尽模式配置
        self.endless_config = config.get("endless_mode", {})
    
    def generate_round_summary(self, round_report: RoundReport) -> Dict[str, Any]:
        """
        为单个轮次生成摘要
        
        Args:
            round_report: 单轮报告
            
        Returns:
            轮次摘要结果
        """
        workflow_logger.log_info(f"开始生成第{round_report.round_number}轮摘要")
        
        try:
            # 构建摘要生成提示词
            prompt = self._build_summary_prompt(round_report)
            
            # 调用LLM生成摘要
            messages = [
                SystemMessage(content=self._get_system_prompt()),
                HumanMessage(content=prompt)
            ]
            
            workflow_logger.log_llm_request(f"生成轮次摘要: 第{round_report.round_number}轮", self.config.get("model"))
            
            response = self.llm.invoke(messages)
            response_content = response.content
            
            # 解析响应
            parsed_result = self._parse_summary_response(response_content, round_report)
            
            if parsed_result.get("status") == "success":
                workflow_logger.log_info(f"第{round_report.round_number}轮摘要生成成功")
                return parsed_result
            else:
                workflow_logger.log_error(f"第{round_report.round_number}轮摘要生成失败: {parsed_result.get('error', '未知错误')}")
                return parsed_result
                
        except Exception as e:
            error_msg = f"生成第{round_report.round_number}轮摘要异常: {str(e)}"
            workflow_logger.log_error(error_msg)
            return {
                "round_number": round_report.round_number,
                "topic": round_report.topic,
                "iteration_id": round_report.iteration_id,
                "summary": "",
                "key_directions": [],
                "core_findings": [],
                "important_insights": [],
                "summary_timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": error_msg
            }
    
    def generate_all_round_summaries(self, round_reports: List[RoundReport]) -> Dict[str, Any]:
        """
        为所有轮次生成摘要
        
        Args:
            round_reports: 所有轮次报告列表
            
        Returns:
            所有轮次摘要结果
        """
        workflow_logger.log_info(f"开始生成{len(round_reports)}个轮次摘要")
        
        try:
            summaries = []
            
            # 为每个报告生成摘要
            for round_report in round_reports:
                summary_result = self.generate_round_summary(round_report)
                summaries.append(summary_result)
            
            # 统计信息
            successful_summaries = [s for s in summaries if s.get("status") == "success"]
            failed_summaries = [s for s in summaries if s.get("status") == "error"]
            
            result = {
                "total_rounds": len(round_reports),
                "successful_summaries": len(successful_summaries),
                "failed_summaries": len(failed_summaries),
                "summaries": summaries,
                "generation_timestamp": datetime.now().isoformat(),
                "status": "completed"
            }
            
            workflow_logger.log_info(f"所有轮次摘要生成完成: 成功{len(successful_summaries)}个, 失败{len(failed_summaries)}个")
            
            return result
            
        except Exception as e:
            error_msg = f"生成所有轮次摘要异常: {str(e)}"
            workflow_logger.log_error(error_msg)
            return {
                "total_rounds": 0,
                "successful_summaries": 0,
                "failed_summaries": 0,
                "summaries": [],
                "generation_timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": error_msg
            }
    
    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """你是一名专业的摘要生成专家，专门负责为探索轮次生成简洁而全面的摘要。

你的任务：
1. 分析单轮探索的完整结果
2. 提取关键方向、核心发现、重要洞察
3. 生成200-300字的轮次摘要
4. 确保摘要准确、简洁、有价值

要求：
- 摘要要突出该轮探索的核心价值
- 包含最重要的发现和洞察
- 语言要专业、简洁
- 结构要清晰、逻辑性强
- 避免重复和冗余信息

输出格式：
{
  "summary": "200-300字的轮次摘要",
  "key_directions": ["方向1", "方向2", "方向3"],
  "core_findings": ["发现1", "发现2", "发现3"],
  "important_insights": ["洞察1", "洞察2", "洞察3"]
}"""
    
    def _build_summary_prompt(self, round_report: RoundReport) -> str:
        """构建摘要生成提示词"""
        prompt_parts = [
            f"轮次：{round_report.round_number}",
            f"主题：{round_report.topic}",
            f"最佳方向：{round_report.best_direction}",
            f"综合评分：{round_report.comprehensive_score:.1f}",
            f"质量等级：{round_report.quality_level}",
            f"处理时间：{round_report.processing_time:.1f}分钟",
            f""
        ]
        
        # 添加关键发现
        if round_report.key_findings:
            prompt_parts.extend([
                f"=== 关键发现 ===",
                f""
            ])
            for i, finding in enumerate(round_report.key_findings[:10], 1):
                prompt_parts.append(f"{i}. {finding}")
            prompt_parts.append("")
        
        # 添加搜索轮次信息
        if round_report.search_rounds:
            prompt_parts.extend([
                f"=== 搜索轮次概览 ===",
                f"总轮次：{len(round_report.search_rounds)}",
                f"成功轮次：{len([r for r in round_report.search_rounds if r.success])}",
                f""
            ])
            
            # 显示前3个搜索轮次的摘要
            successful_rounds = [r for r in round_report.search_rounds if r.success][:3]
            for i, search_round in enumerate(successful_rounds, 1):
                prompt_parts.extend([
                    f"搜索轮次{i}：{search_round.question}",
                    f"摘要：{search_round.summary[:200]}..." if len(search_round.summary) > 200 else f"摘要：{search_round.summary}",
                    f"关键点：{', '.join(search_round.key_points[:3])}",
                    f""
                ])
        
        # 添加优化报告信息
        if round_report.optimized_report and isinstance(round_report.optimized_report, dict):
            optimized_report = round_report.optimized_report
            prompt_parts.extend([
                f"=== 优化报告概览 ===",
                f""
            ])
            
            if "executive_summary" in optimized_report and optimized_report["executive_summary"]:
                summary_text = optimized_report["executive_summary"]
                if len(summary_text) > 200:
                    summary_text = summary_text[:200] + "..."
                prompt_parts.append(f"执行摘要：{summary_text}")
            
            if "key_insights" in optimized_report and optimized_report["key_insights"]:
                insights = optimized_report["key_insights"][:5]
                prompt_parts.extend([
                    f"关键洞察：",
                    f"{', '.join(insights)}"
                ])
            
            prompt_parts.append("")
        
        prompt_parts.extend([
            f"=== 任务要求 ===",
            f"请基于以上信息，生成该轮探索的摘要：",
            f"1. 突出该轮探索的核心价值和贡献",
            f"2. 总结最重要的发现和洞察",
            f"3. 保持200-300字的长度",
            f"4. 使用专业、简洁的语言",
            f"5. 按照系统消息中的JSON格式返回结果"
        ])
        
        return "\n".join(prompt_parts)
    
    def _parse_summary_response(self, response_content: str, round_report: RoundReport) -> Dict[str, Any]:
        """解析摘要响应"""
        try:
            # 清理响应内容
            cleaned_content = self._clean_response_content(response_content)
            
            # 尝试解析JSON
            try:
                parsed_data = json.loads(cleaned_content)
            except json.JSONDecodeError as e:
                workflow_logger.log_error(f"摘要JSON解析失败: {str(e)}")
                # 如果JSON解析失败，尝试提取文本摘要
                return self._extract_text_summary(response_content, round_report)
            
            # 验证数据结构
            if not isinstance(parsed_data, dict):
                return self._extract_text_summary(response_content, round_report)
            
            # 提取摘要内容
            summary = parsed_data.get("summary", "").strip()
            key_directions = parsed_data.get("key_directions", [])
            core_findings = parsed_data.get("core_findings", [])
            important_insights = parsed_data.get("important_insights", [])
            
            # 验证摘要长度
            if len(summary) < 50:
                workflow_logger.log_warning(f"摘要过短: {len(summary)}字符")
                summary = self._generate_fallback_summary(round_report)
            
            return {
                "round_number": round_report.round_number,
                "topic": round_report.topic,
                "iteration_id": round_report.iteration_id,
                "summary": summary,
                "key_directions": key_directions if isinstance(key_directions, list) else [],
                "core_findings": core_findings if isinstance(core_findings, list) else [],
                "important_insights": important_insights if isinstance(important_insights, list) else [],
                "summary_timestamp": datetime.now().isoformat(),
                "status": "success"
            }
            
        except Exception as e:
            workflow_logger.log_error(f"解析摘要响应异常: {str(e)}")
            return self._extract_text_summary(response_content, round_report)
    
    def _extract_text_summary(self, response_content: str, round_report: RoundReport) -> Dict[str, Any]:
        """从文本响应中提取摘要"""
        try:
            # 简单提取：取前300个字符作为摘要
            summary = response_content.strip()[:300]
            if len(response_content) > 300:
                summary += "..."
            
            return {
                "round_number": round_report.round_number,
                "topic": round_report.topic,
                "iteration_id": round_report.iteration_id,
                "summary": summary,
                "key_directions": [round_report.best_direction] if round_report.best_direction else [],
                "core_findings": round_report.key_findings[:3] if round_report.key_findings else [],
                "important_insights": [],
                "summary_timestamp": datetime.now().isoformat(),
                "status": "success",
                "note": "从文本响应中提取摘要"
            }
            
        except Exception as e:
            workflow_logger.log_error(f"提取文本摘要异常: {str(e)}")
            return self._generate_fallback_summary(round_report)
    
    def _generate_fallback_summary(self, round_report: RoundReport) -> Dict[str, Any]:
        """生成备用摘要"""
        try:
            # 基于报告数据生成简单摘要
            summary_parts = [
                f"第{round_report.round_number}轮探索围绕'{round_report.topic}'主题展开。"
            ]
            
            if round_report.best_direction:
                summary_parts.append(f"最佳探索方向为'{round_report.best_direction}'。")
            
            if round_report.key_findings:
                summary_parts.append(f"发现了{len(round_report.key_findings)}个关键点。")
            
            if round_report.search_rounds:
                successful_rounds = len([r for r in round_report.search_rounds if r.success])
                summary_parts.append(f"完成了{successful_rounds}个成功的搜索轮次。")
            
            summary_parts.append(f"综合评分为{round_report.comprehensive_score:.1f}分，质量等级为{round_report.quality_level}。")
            
            summary = " ".join(summary_parts)
            
            return {
                "round_number": round_report.round_number,
                "topic": round_report.topic,
                "iteration_id": round_report.iteration_id,
                "summary": summary,
                "key_directions": [round_report.best_direction] if round_report.best_direction else [],
                "core_findings": round_report.key_findings[:3] if round_report.key_findings else [],
                "important_insights": [],
                "summary_timestamp": datetime.now().isoformat(),
                "status": "success",
                "note": "使用备用摘要生成"
            }
            
        except Exception as e:
            workflow_logger.log_error(f"生成备用摘要异常: {str(e)}")
            return {
                "round_number": round_report.round_number,
                "topic": round_report.topic,
                "iteration_id": round_report.iteration_id,
                "summary": f"第{round_report.round_number}轮探索完成，主题为'{round_report.topic}'。",
                "key_directions": [],
                "core_findings": [],
                "important_insights": [],
                "summary_timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e)
            }
    
    def _clean_response_content(self, content: str) -> str:
        """清理响应内容"""
        # 移除代码围栏
        content = re.sub(r'```json\s*', '', content)
        content = re.sub(r'```\s*$', '', content)
        content = re.sub(r'^```\s*', '', content)
        
        # 移除多余的空白字符
        content = content.strip()
        
        # 查找JSON开始和结束位置
        start_pos = content.find('{')
        end_pos = content.rfind('}')
        
        if start_pos != -1 and end_pos != -1 and end_pos > start_pos:
            content = content[start_pos:end_pos + 1]
        
        return content
