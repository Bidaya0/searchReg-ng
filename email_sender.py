"""
邮件发送模块
使用Mailgun API发送邮件
"""

import requests
from typing import Dict, Any, List, Optional
from datetime import datetime
import os
from logger import workflow_logger


class EmailSender:
    """邮件发送器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.email_config = config.get("email", {})
        
        # Mailgun配置
        self.domain_name = self.email_config.get("mailgun_domain")
        self.api_key = self.email_config.get("mailgun_api_key")
        self.from_email = self.email_config.get("from_email", "noreply@example.com")
        self.to_email = self.email_config.get("to_email")
        self.cc_email = self.email_config.get("cc_email")
        self.bcc_email = self.email_config.get("bcc_email")
        
        # 构建API URL
        if self.domain_name:
            self.api_url = f"https://api.mailgun.net/v3/{self.domain_name}/messages"
        else:
            self.api_url = None
    
    def is_configured(self) -> bool:
        """检查邮件配置是否完整"""
        return bool(self.domain_name and self.api_key and self.to_email)
    
    def send_email(self, subject: str, text_content: str, html_content: str = None) -> Dict[str, Any]:
        """发送邮件"""
        if not self.is_configured():
            workflow_logger.log_warning("邮件配置不完整，跳过邮件发送")
            return {"status": "skipped", "reason": "邮件配置不完整"}
        
        try:
            # 准备邮件数据
            data = {
                "from": self.from_email,
                "to": self.to_email,
                "subject": subject,
                "text": text_content
            }
            
            # 添加抄送和密送
            if self.cc_email:
                data["cc"] = self.cc_email
            if self.bcc_email:
                data["bcc"] = self.bcc_email
            
            # 添加HTML内容
            if html_content:
                data["html"] = html_content
            
            # 发送请求
            workflow_logger.log_info(f"正在发送邮件到：{self.to_email}")
            response = requests.post(
                self.api_url, 
                data=data, 
                auth=('api', self.api_key)
            )
            
            if response.status_code == 200:
                result = response.json()
                workflow_logger.log_info(f"邮件发送成功：{result.get('id', 'unknown')}")
                return {"status": "success", "message_id": result.get("id"), "response": result}
            else:
                error_msg = f"邮件发送失败：{response.status_code} - {response.text}"
                workflow_logger.log_error(error_msg)
                return {"status": "error", "error": error_msg}
                
        except Exception as e:
            error_msg = f"邮件发送异常：{str(e)}"
            workflow_logger.log_error(error_msg)
            return {"status": "error", "error": error_msg}
    
    def send_workflow_report(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """发送工作流报告邮件"""
        try:
            topic = result.get('topic', '未知主题')
            batch_id = result.get('workflow_id', 'unknown').replace('integrated_', '')
            
            # 构建邮件主题
            subject = f"【智能分析报告】{topic} - {batch_id}"
            
            # 构建完整的邮件内容（包含所有报告）
            email_content = self._build_complete_email_content(result)
            
            # 发送邮件（不发送附件）
            return self.send_email(subject, email_content)
            
        except Exception as e:
            error_msg = f"发送工作流报告邮件失败：{str(e)}"
            workflow_logger.log_error(error_msg)
            return {"status": "error", "error": error_msg}
    
    def _build_complete_email_content(self, result: Dict[str, Any]) -> str:
        """构建完整的邮件内容，包含所有报告"""
        try:
            topic = result.get('topic', '未知主题')
            batch_id = result.get('workflow_id', 'unknown').replace('integrated_', '')
            execution_stats = result.get('execution_stats', {})
            sub_question_count = result.get('total_sub_questions', 0)
            
            content_lines = [
                f"主题：{topic}",
                f"批次号：{batch_id}",
                f"生成时间：{datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}",
                "",
                "=== 分析概览 ===",
                f"- 分析主题：{topic}",
                f"- 生成问题：{execution_stats.get('questions_generated', 0)}个",
                f"- 完成搜索：{execution_stats.get('searches_completed', 0)}个",
                f"- 搜索成功率：{execution_stats.get('success_rate', 0):.1%}",
                f"- 总处理时间：{execution_stats.get('total_time', 0):.2f}秒",
                "",
                "=== 综合总结 ===",
                ""
            ]
            
            # 添加汇总报告内容（总结在前）
            summary_report = result.get('summary_report', '')
            if summary_report:
                content_lines.append(summary_report)
            else:
                content_lines.append("（综合总结内容不可用）")
            
            content_lines.extend([
                "",
                "=== 各子问题详细分析 ===",
                ""
            ])
            
            # 添加所有子问题报告
            sub_question_reports = result.get('sub_question_reports', [])
            for i, sub_report in enumerate(sub_question_reports, 1):
                content_lines.extend([
                    f"--- 子问题 {i} ---",
                    "",
                    sub_report,
                    ""
                ])
            
            content_lines.extend([
                "---",
                "此邮件由智能分析系统自动生成",
                "如有任何问题，请随时联系。"
            ])
            
            return "\n".join(content_lines)
            
        except Exception as e:
            return f"构建完整邮件内容失败：{str(e)}"
    
    def _build_workflow_email_content(self, result: Dict[str, Any]) -> str:
        """构建工作流邮件内容"""
        topic = result.get('topic', '未知主题')
        batch_id = result.get('workflow_id', 'unknown').replace('integrated_', '')
        execution_stats = result.get('execution_stats', {})
        sub_question_count = result.get('total_sub_questions', 0)
        
        # 邮件正文
        content_lines = [
            f"主题：{topic}",
            f"批次号：{batch_id}",
            f"生成时间：{datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}",
            "",
            "=== 分析概览 ===",
            f"- 分析主题：{topic}",
            f"- 生成问题：{execution_stats.get('questions_generated', 0)}个",
            f"- 完成搜索：{execution_stats.get('searches_completed', 0)}个",
            f"- 搜索成功率：{execution_stats.get('success_rate', 0):.1%}",
            f"- 总处理时间：{execution_stats.get('total_time', 0):.2f}秒",
            "",
            "=== 报告文件 ===",
            f"- 子问题报告：{sub_question_count}个",
            f"- 汇总报告：1个",
            f"- 邮件报告：1个",
            f"- 简洁报告：1个",
            "",
            "=== 详细内容 ===",
            "请查看附件中的详细报告文件：",
            "",
            "1. 子问题报告（sub_question_*.txt）：",
            "   - 每个问题一份独立报告",
            "   - 包含该问题的调研URL和总结",
            "",
            "2. 汇总报告（summary_report_*.txt）：",
            "   - 包含所有问题的综合信息",
            "   - 所有调研URL和综合总结",
            "",
            "3. 邮件报告（email_report_*.txt）：",
            "   - 格式化的邮件格式报告",
            "",
            "4. 简洁报告（simple_report_*.txt）：",
            "   - 符合样例格式的简洁报告",
            "",
            "---",
            "此邮件由智能分析系统自动生成",
            "如有任何问题，请随时联系。"
        ]
        
        return "\n".join(content_lines)
    
