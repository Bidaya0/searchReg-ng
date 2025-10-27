"""
邮件格式输出器
将集成工作流的结果格式化为邮件格式
"""

from typing import Dict, Any, List
from datetime import datetime
from storage_models import IntegratedWorkflowRecord, SearchRoundRecord, RoundReport, EndlessModeResult


class EmailFormatter:
    """邮件格式输出器"""
    
    def __init__(self):
        self.template = self._get_email_template()
    
    def _get_email_template(self) -> str:
        """获取邮件模板"""
        return """
主题：{subject}

尊敬的{recipient}，

您好！

以下是关于"{topic}"的深度分析报告，基于{total_questions}个专业问题的全面搜索和智能分析。

## 📋 分析概览
- **分析主题**：{topic}
- **分析维度**：{analysis_dimensions}个方向
- **搜索问题**：{total_questions}个
- **有效结果**：{successful_searches}个
- **分析时间**：{generated_time}

## 🔍 核心发现

{core_findings}

## 📊 分方向详细分析

{directional_analysis}

## 💡 关键洞察与建议

{key_insights}

## 🎯 后续行动建议

{action_recommendations}

---
此报告由智能分析系统自动生成
生成时间：{generated_time}

如有任何问题，请随时联系。

此致
敬礼！

智能分析系统
        """
    
    def format_workflow_result(self, result: Dict[str, Any], recipient: str = "用户") -> str:
        """格式化工作流结果为邮件"""
        try:
            # 提取基本信息
            topic = result.get('topic', '未知主题')
            questions = result.get('questions', [])
            search_rounds = result.get('search_rounds', [])
            comprehensive_summary = result.get('comprehensive_summary', {})
            execution_stats = result.get('execution_stats', {})
            
            # 计算统计数据
            total_questions = len(questions)
            successful_rounds = [r for r in search_rounds if r.success]
            successful_searches = len(successful_rounds)
            
            # 按方向分组搜索轮次
            directional_rounds = self._group_rounds_by_direction(successful_rounds)
            analysis_dimensions = len(directional_rounds)
            
            # 生成核心发现
            core_findings = self._format_core_findings(successful_rounds, comprehensive_summary)
            
            # 生成分方向详细分析
            directional_analysis = self._format_directional_analysis(directional_rounds)
            
            # 生成关键洞察
            key_insights = self._format_key_insights(comprehensive_summary, successful_rounds)
            
            # 生成行动建议
            action_recommendations = self._format_action_recommendations(comprehensive_summary, successful_rounds)
            
            # 填充模板
            email_content = self.template.format(
                subject=f"深度分析报告：{topic}",
                recipient=recipient,
                topic=topic,
                total_questions=total_questions,
                analysis_dimensions=analysis_dimensions,
                successful_searches=successful_searches,
                generated_time=datetime.now().strftime('%Y年%m月%d日 %H:%M:%S'),
                core_findings=core_findings,
                directional_analysis=directional_analysis,
                key_insights=key_insights,
                action_recommendations=action_recommendations
            )
            
            return email_content.strip()
            
        except Exception as e:
            return f"邮件格式化失败：{str(e)}"
    
    def _format_search_details(self, search_results: List[Any]) -> str:
        """格式化搜索详情"""
        if not search_results:
            return "暂无搜索结果"
        
        details = []
        for i, result in enumerate(search_results[:10], 1):  # 只显示前10个结果
            if hasattr(result, 'query'):
                query = result.query
                results_count = len(result.results) if hasattr(result, 'results') else 0
                details.append(f"**{i}. 搜索查询：{query}**")
                details.append(f"   - 获得{results_count}个搜索结果")
                
                # 显示搜索结果摘要
                if hasattr(result, 'summaries') and result.summaries:
                    summary = result.summaries[0][:200] + "..." if len(result.summaries[0]) > 200 else result.summaries[0]
                    details.append(f"   - 总结：{summary}")
                
                # 显示关键点
                if hasattr(result, 'key_points') and result.key_points:
                    key_points = ", ".join(result.key_points[:3])
                    details.append(f"   - 关键点：{key_points}")
                
                # 显示部分搜索结果
                if hasattr(result, 'results') and result.results:
                    details.append(f"   - 主要结果：")
                    for j, item in enumerate(result.results[:2], 1):
                        if hasattr(item, 'title'):
                            title = item.title[:80] + "..." if len(item.title) > 80 else item.title
                            details.append(f"     {j}) {title}")
                        elif isinstance(item, dict):
                            title = item.get('title', '无标题')[:80] + "..." if len(item.get('title', '')) > 80 else item.get('title', '无标题')
                            details.append(f"     {j}) {title}")
                
                details.append("")  # 空行分隔
            else:
                details.append(f"{i}. 搜索结果：{str(result)[:100]}...")
        
        if len(search_results) > 10:
            details.append(f"... 还有{len(search_results) - 10}个搜索结果")
        
        return "\n".join(details)
    
    def _format_comprehensive_analysis(self, summary: Dict[str, Any]) -> str:
        """格式化综合分析"""
        if not summary:
            return "暂无综合分析"
        
        analysis_parts = []
        
        # 执行摘要
        if summary.get('executive_summary'):
            analysis_parts.append(f"**执行摘要：**\n{summary['executive_summary']}")
        
        # 详细分析
        detailed_analysis = summary.get('detailed_analysis', {})
        if detailed_analysis:
            analysis_parts.append("**详细分析：**")
            for direction, content in detailed_analysis.items():
                analysis_parts.append(f"- {direction}：{content}")
        
        # 跨方向发现
        cross_cutting = summary.get('cross_cutting_findings', [])
        if cross_cutting:
            analysis_parts.append("**跨方向关联发现：**")
            for finding in cross_cutting:
                analysis_parts.append(f"- {finding}")
        
        return "\n\n".join(analysis_parts) if analysis_parts else "暂无详细分析"
    
    def _format_key_insights(self, summary: Dict[str, Any]) -> str:
        """格式化关键洞察"""
        insights = summary.get('key_insights', [])
        if not insights:
            return "暂无关键洞察"
        
        formatted_insights = []
        for i, insight in enumerate(insights, 1):
            formatted_insights.append(f"{i}. {insight}")
        
        return "\n".join(formatted_insights)
    
    def _format_recommendations(self, summary: Dict[str, Any]) -> str:
        """格式化建议和后续行动"""
        recommendations = summary.get('recommendations', [])
        if not recommendations:
            return "暂无具体建议"
        
        formatted_recommendations = []
        for i, rec in enumerate(recommendations, 1):
            formatted_recommendations.append(f"{i}. {rec}")
        
        return "\n".join(formatted_recommendations)
    
    def _format_technical_stats(self, stats: Dict[str, Any]) -> str:
        """格式化技术统计"""
        if not stats:
            return "暂无技术统计"
        
        tech_stats = []
        tech_stats.append(f"- 总处理时间：{stats.get('total_time', 0):.2f}秒")
        tech_stats.append(f"- 问题生成数：{stats.get('questions_generated', 0)}")
        tech_stats.append(f"- 搜索完成数：{stats.get('searches_completed', 0)}")
        tech_stats.append(f"- 搜索错误数：{stats.get('search_errors', 0)}")
        tech_stats.append(f"- 成功率：{stats.get('success_rate', 0):.1%}")
        
        return "\n".join(tech_stats)
    
    def save_email_to_file(self, email_content: str, filename: str = None) -> str:
        """保存邮件内容到文件"""
        if not filename:
            filename = f"email_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        filepath = f"./data/results/{filename}"
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(email_content)
            return filepath
        except Exception as e:
            return f"保存邮件文件失败：{str(e)}"
    
    def format_search_rounds(self, search_rounds: List[SearchRoundRecord]) -> str:
        """格式化搜索轮次详情"""
        if not search_rounds:
            return "暂无搜索轮次记录"
        
        rounds_details = []
        for round_record in search_rounds:
            status = "✅ 成功" if round_record.success else "❌ 失败"
            rounds_details.append(
                f"**第{round_record.round_number}轮搜索** ({status})\n"
                f"- **问题**：{round_record.question}\n"
                f"- **方向**：{round_record.direction}\n"
                f"- **查询**：{round_record.search_query}\n"
                f"- **结果数**：{len(round_record.search_results)}\n"
                f"- **处理时间**：{round_record.processing_time:.2f}秒\n"
                f"- **时间**：{round_record.timestamp.strftime('%H:%M:%S')}\n"
            )
            
            # 显示搜索结果摘要
            if round_record.summary:
                summary = round_record.summary[:300] + "..." if len(round_record.summary) > 300 else round_record.summary
                rounds_details.append(f"- **摘要**：{summary}\n")
            
            # 显示关键点
            if round_record.key_points:
                key_points = ", ".join(round_record.key_points[:5])
                rounds_details.append(f"- **关键点**：{key_points}\n")
            
            # 显示部分搜索结果
            if round_record.search_results and len(round_record.search_results) > 0:
                rounds_details.append(f"- **主要搜索结果**：\n")
                for i, result in enumerate(round_record.search_results[:3], 1):
                    if hasattr(result, 'title'):
                        title = result.title[:100] + "..." if len(result.title) > 100 else result.title
                        rounds_details.append(f"  {i}) {title}\n")
                    elif isinstance(result, dict):
                        title = result.get('title', '无标题')[:100] + "..." if len(result.get('title', '')) > 100 else result.get('title', '无标题')
                        rounds_details.append(f"  {i}) {title}\n")
                
                if len(round_record.search_results) > 3:
                    rounds_details.append(f"  ... 还有{len(round_record.search_results) - 3}个结果\n")
            
            # 显示错误信息
            if round_record.error_message:
                rounds_details.append(f"- **错误信息**：{round_record.error_message}\n")
            
            rounds_details.append("---\n")
        
        return "\n".join(rounds_details)
    
    def _group_rounds_by_direction(self, search_rounds: List[SearchRoundRecord]) -> Dict[str, List[SearchRoundRecord]]:
        """按方向分组搜索轮次"""
        directional_rounds = {}
        for round_record in search_rounds:
            direction = round_record.direction
            if direction not in directional_rounds:
                directional_rounds[direction] = []
            directional_rounds[direction].append(round_record)
        return directional_rounds
    
    def _format_core_findings(self, search_rounds: List[SearchRoundRecord], comprehensive_summary: Dict[str, Any]) -> str:
        """格式化核心发现"""
        if not search_rounds:
            return "暂无核心发现"
        
        findings = []
        
        # 直接提取所有成功的搜索轮次的实际内容
        successful_rounds = [r for r in search_rounds if r.success and (r.summary or r.key_points)]
        
        if not successful_rounds:
            # 如果没有成功的轮次，尝试从失败的轮次中提取问题信息
            failed_rounds = [r for r in search_rounds if not r.success]
            if failed_rounds:
                findings.append("**分析问题概览**：")
                for i, round_record in enumerate(failed_rounds[:10], 1):  # 显示前10个问题
                    findings.append(f"{i}. {round_record.question}")
                findings.append(f"\n注：共分析了{len(failed_rounds)}个问题，但搜索过程中遇到技术问题")
            return "\n".join(findings) if findings else "暂无核心发现"
        
        # 从成功的轮次中提取内容
        all_summaries = [r.summary for r in successful_rounds if r.summary]
        all_key_points = []
        for r in successful_rounds:
            if r.key_points:
                all_key_points.extend(r.key_points)
        
        # 生成执行摘要
        if all_summaries:
            combined_summary = " ".join(all_summaries)
            if len(combined_summary) > 300:
                combined_summary = combined_summary[:300] + "..."
            findings.append(f"**核心发现摘要**：\n{combined_summary}")
        
        # 显示关键发现
        if all_key_points:
            # 去重并取前8个
            unique_key_points = list(dict.fromkeys(all_key_points))[:8]
            findings.append(f"\n**关键发现**：")
            for i, point in enumerate(unique_key_points, 1):
                findings.append(f"{i}. {point}")
        
        # 显示分析的问题范围
        questions_covered = [r.question for r in successful_rounds]
        if questions_covered:
            findings.append(f"\n**已分析的问题**：")
            for i, question in enumerate(questions_covered[:5], 1):  # 显示前5个问题
                findings.append(f"{i}. {question}")
            if len(questions_covered) > 5:
                findings.append(f"... 还有{len(questions_covered) - 5}个问题")
        
        return "\n".join(findings) if findings else "暂无核心发现"
    
    def _format_directional_analysis(self, directional_rounds: Dict[str, List[SearchRoundRecord]]) -> str:
        """格式化分方向详细分析"""
        if not directional_rounds:
            return "暂无分方向分析"
        
        analysis_parts = []
        
        for direction, rounds in directional_rounds.items():
            # 只处理有实际内容的轮次
            content_rounds = [r for r in rounds if r.summary or r.key_points or r.search_results]
            
            if not content_rounds:
                continue
                
            analysis_parts.append(f"### {direction}")
            analysis_parts.append("")
            
            # 该方向的问题统计
            analysis_parts.append(f"**问题数量**：{len(content_rounds)}个")
            
            # 该方向的摘要汇总
            summaries = [r.summary for r in content_rounds if r.summary]
            if summaries:
                # 合并摘要，去重
                combined_summary = self._combine_summaries(summaries)
                analysis_parts.append(f"**核心内容**：{combined_summary}")
            
            # 该方向的关键点
            all_key_points = []
            for round_record in content_rounds:
                if round_record.key_points:
                    all_key_points.extend(round_record.key_points)
            
            if all_key_points:
                # 去重并取前5个
                unique_key_points = list(dict.fromkeys(all_key_points))[:5]
                analysis_parts.append(f"**关键要点**：")
                for i, point in enumerate(unique_key_points, 1):
                    analysis_parts.append(f"{i}. {point}")
            
            # 该方向的主要搜索结果
            all_results = []
            for round_record in content_rounds:
                if round_record.search_results:
                    all_results.extend(round_record.search_results[:2])  # 每轮取前2个结果
            
            if all_results:
                analysis_parts.append(f"**主要信息来源**：")
                for i, result in enumerate(all_results[:5], 1):  # 总共显示前5个结果
                    title = result.title[:80] + "..." if len(result.title) > 80 else result.title
                    analysis_parts.append(f"{i}. {title}")
            
            # 显示该方向分析的具体问题
            questions = [r.question for r in content_rounds]
            if questions:
                analysis_parts.append(f"**分析的问题**：")
                for i, question in enumerate(questions[:3], 1):  # 显示前3个问题
                    analysis_parts.append(f"{i}. {question}")
                if len(questions) > 3:
                    analysis_parts.append(f"... 还有{len(questions) - 3}个问题")
            
            analysis_parts.append("")  # 空行分隔
        
        return "\n".join(analysis_parts) if analysis_parts else "暂无分方向分析"
    
    def _combine_summaries(self, summaries: List[str]) -> str:
        """合并多个摘要"""
        if not summaries:
            return ""
        
        # 简单合并，去重相似内容
        combined = " ".join(summaries)
        # 截断到合理长度
        if len(combined) > 500:
            combined = combined[:500] + "..."
        return combined
    
    def _format_key_insights(self, comprehensive_summary: Dict[str, Any], search_rounds: List[SearchRoundRecord]) -> str:
        """格式化关键洞察"""
        insights = []
        
        # 从综合总结中提取洞察
        if comprehensive_summary.get('key_insights'):
            insights.extend(comprehensive_summary['key_insights'])
        
        # 直接从问题内容中提取洞察
        question_insights = self._extract_insights_from_questions(search_rounds)
        insights.extend(question_insights)
        
        # 从搜索轮次中提取跨方向洞察
        cross_direction_insights = self._extract_cross_direction_insights(search_rounds)
        insights.extend(cross_direction_insights)
        
        # 去重并限制数量
        unique_insights = list(dict.fromkeys(insights))[:8]
        
        if not unique_insights:
            return "暂无关键洞察"
        
        formatted_insights = []
        for i, insight in enumerate(unique_insights, 1):
            formatted_insights.append(f"{i}. {insight}")
        
        return "\n".join(formatted_insights)
    
    def _extract_insights_from_questions(self, search_rounds: List[SearchRoundRecord]) -> List[str]:
        """从问题内容中提取洞察"""
        insights = []
        
        # 收集所有问题
        all_questions = [r.question for r in search_rounds if r.question]
        
        if not all_questions:
            return insights
        
        # 分析问题模式
        question_patterns = self._analyze_question_patterns(all_questions)
        
        # 基于问题模式生成洞察
        if "如何" in question_patterns:
            insights.append("学习新技能需要系统性的方法和策略指导")
        
        if "什么" in question_patterns or "哪些" in question_patterns:
            insights.append("学习者需要了解具体的学习资源和工具")
        
        if "为什么" in question_patterns:
            insights.append("动机和目的对学习成功至关重要")
        
        if "时间" in question_patterns or "进度" in question_patterns:
            insights.append("时间管理和进度规划是学习成功的关键因素")
        
        if "评估" in question_patterns or "效果" in question_patterns:
            insights.append("学习效果评估和反馈机制对持续改进很重要")
        
        if "挑战" in question_patterns or "问题" in question_patterns:
            insights.append("学习过程中会遇到各种挑战，需要有效的应对策略")
        
        if "平衡" in question_patterns or "关系" in question_patterns:
            insights.append("学习与工作生活的平衡是成功学习的重要条件")
        
        return insights
    
    def _analyze_question_patterns(self, questions: List[str]) -> Dict[str, int]:
        """分析问题模式"""
        patterns = {}
        keywords = ["如何", "什么", "哪些", "为什么", "时间", "进度", "评估", "效果", "挑战", "问题", "平衡", "关系"]
        
        for question in questions:
            for keyword in keywords:
                if keyword in question:
                    patterns[keyword] = patterns.get(keyword, 0) + 1
        
        return patterns
    
    def _extract_cross_direction_insights(self, search_rounds: List[SearchRoundRecord]) -> List[str]:
        """提取跨方向洞察"""
        insights = []
        
        # 按方向分组
        directional_rounds = self._group_rounds_by_direction(search_rounds)
        directions = list(directional_rounds.keys())
        
        if len(directions) >= 2:
            # 分析不同方向间的关联性
            insights.append(f"发现{directions[0]}和{directions[1]}之间存在重要关联")
            
            # 分析各方向的重要性
            direction_importance = {}
            for direction, rounds in directional_rounds.items():
                total_key_points = sum(len(r.key_points) for r in rounds if r.key_points)
                direction_importance[direction] = total_key_points
            
            if direction_importance:
                most_important = max(direction_importance, key=direction_importance.get)
                insights.append(f"{most_important}方向包含最丰富的信息内容")
        
        return insights
    
    def _format_action_recommendations(self, comprehensive_summary: Dict[str, Any], search_rounds: List[SearchRoundRecord]) -> str:
        """格式化行动建议"""
        recommendations = []
        
        # 从综合总结中提取建议
        if comprehensive_summary.get('recommendations'):
            recommendations.extend(comprehensive_summary['recommendations'])
        
        # 基于实际问题内容生成具体建议
        question_based_recommendations = self._generate_recommendations_from_questions(search_rounds)
        recommendations.extend(question_based_recommendations)
        
        # 基于搜索结果生成具体建议
        specific_recommendations = self._generate_specific_recommendations(search_rounds)
        recommendations.extend(specific_recommendations)
        
        # 去重并限制数量
        unique_recommendations = list(dict.fromkeys(recommendations))[:6]
        
        if not unique_recommendations:
            return "暂无具体建议"
        
        formatted_recommendations = []
        for i, rec in enumerate(unique_recommendations, 1):
            formatted_recommendations.append(f"{i}. {rec}")
        
        return "\n".join(formatted_recommendations)
    
    def _generate_recommendations_from_questions(self, search_rounds: List[SearchRoundRecord]) -> List[str]:
        """基于问题内容生成建议"""
        recommendations = []
        
        # 收集所有问题
        all_questions = [r.question for r in search_rounds if r.question]
        
        if not all_questions:
            return recommendations
        
        # 基于问题类型生成建议
        question_text = " ".join(all_questions)
        
        if "如何开始" in question_text or "如何让人开始" in question_text:
            recommendations.append("设计个性化的学习计划，帮助学习者设定具体、可衡量的学习目标")
        
        if "学习资源" in question_text or "学习工具" in question_text:
            recommendations.append("提供多样化的学习资源和工具，满足不同学习者的需求")
        
        if "学习社群" in question_text or "学习伙伴" in question_text:
            recommendations.append("促进学习者之间的交流，构建学习社群")
        
        if "时间管理" in question_text or "学习时间" in question_text:
            recommendations.append("教授时间管理技巧，帮助学习者合理分配学习时间")
        
        if "学习效果" in question_text or "评估" in question_text:
            recommendations.append("建立有效的反馈机制，确保学习者能够及时获得改进意见")
        
        if "学习动机" in question_text or "学习动力" in question_text:
            recommendations.append("帮助学习者找到内在动机，建立持续学习的动力")
        
        if "学习挑战" in question_text or "学习困难" in question_text:
            recommendations.append("提供心理支持和应对策略，帮助学习者克服学习障碍")
        
        if "学习进度" in question_text or "学习计划" in question_text:
            recommendations.append("制定灵活的学习进度安排，适应不同学习者的节奏")
        
        if "学习环境" in question_text:
            recommendations.append("创造良好的学习环境，减少干扰因素")
        
        if "学习目标" in question_text:
            recommendations.append("帮助学习者设定SMART学习目标（具体、可衡量、可实现、相关、有时限）")
        
        return recommendations

    # =====================
    # 子问题报告生成
    # =====================
    def format_sub_question_report(self, question: str, search_round: Any, batch_id: str) -> str:
        """为单个子问题生成报告"""
        try:
            # 提取该问题的调研链接
            links = []
            if hasattr(search_round, 'search_results') and search_round.search_results:
                for item in search_round.search_results:
                    if hasattr(item, 'link') and item.link:
                        links.append(item.link)
                    elif isinstance(item, dict) and item.get('link'):
                        links.append(item['link'])
            
            # 去重
            unique_links = list(dict.fromkeys(links))
            
            # 获取该问题的总结
            summary_text = ''
            if hasattr(search_round, 'summary') and search_round.summary:
                summary_text = search_round.summary
            else:
                summary_text = '（该问题未能获取有效摘要）'
            
            # 生成子问题报告
            report_lines = [
                '问题:',
                question,
                '',
                f'批次号: {batch_id}',
                '',
                '搜索关键词',
                search_round.search_query if hasattr(search_round, 'search_query') else question,
                '',
                '调研过的资料链接:'
            ]
            
            # 添加调研链接
            if unique_links:
                for url in unique_links:
                    report_lines.append(f'- {url}')
            else:
                report_lines.append('- （无可用链接）')
            
            report_lines.extend([
                '',
                '总结:',
                summary_text,
                '',
                '问题的汇总:',
                f'- {question}'
            ])
            
            return '\n'.join(report_lines)
            
        except Exception as e:
            return f"子问题报告生成失败：{str(e)}"
    
    def save_sub_question_report(self, report_content: str, question_index: int, batch_id: str) -> str:
        """保存子问题报告到文件"""
        filename = f"sub_question_{question_index:02d}_{batch_id}.txt"
        filepath = f"./data/results/{filename}"
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report_content)
            return filepath
        except Exception as e:
            return f"保存子问题报告失败：{str(e)}"
    
    def format_summary_report(self, result: Dict[str, Any]) -> str:
        """生成汇总报告"""
        try:
            topic = result.get('topic', '')
            workflow_id = result.get('workflow_id', 'unknown')
            search_rounds = result.get('search_rounds', [])
            comprehensive_summary = result.get('comprehensive_summary', {})
            questions = result.get('questions', [])
            
            # 简化批次号
            batch_id = workflow_id.replace('integrated_', '') if workflow_id.startswith('integrated_') else workflow_id
            
            # 收集所有调研链接
            all_links = []
            for round_record in search_rounds:
                if hasattr(round_record, 'search_results') and round_record.search_results:
                    for item in round_record.search_results:
                        if hasattr(item, 'link') and item.link:
                            all_links.append(item.link)
                        elif isinstance(item, dict) and item.get('link'):
                            all_links.append(item['link'])
            
            # 去重并限制数量
            unique_links = list(dict.fromkeys(all_links))[:30]
            
            # 获取综合总结
            summary_text = ''
            if comprehensive_summary.get('executive_summary'):
                summary_text = comprehensive_summary['executive_summary']
            else:
                # 合并所有子问题的总结
                round_summaries = []
                for round_record in search_rounds:
                    if hasattr(round_record, 'summary') and round_record.summary:
                        round_summaries.append(round_record.summary)
                
                if round_summaries:
                    summary_text = self._combine_summaries(round_summaries)
                else:
                    summary_text = '（本次过程未能提取有效摘要）'
            
            # 生成汇总报告
            report_lines = [
                '问题:',
                topic if topic else '（未提供具体问题）',
                '',
                f'批次号: {batch_id}',
                '',
                '搜索关键词'
            ]
            
            # 添加所有搜索关键词
            search_keywords = []
            for round_record in search_rounds:
                if hasattr(round_record, 'search_query') and round_record.search_query:
                    search_keywords.append(round_record.search_query)
            
            unique_keywords = list(dict.fromkeys(search_keywords))[:15]
            if unique_keywords:
                for keyword in unique_keywords:
                    report_lines.append(keyword)
            else:
                report_lines.append('（无搜索关键词）')
            
            report_lines.extend([
                '',
                '调研过的资料链接:'
            ])
            
            # 添加所有调研链接
            if unique_links:
                for url in unique_links:
                    report_lines.append(f'- {url}')
            else:
                report_lines.append('- （无可用链接）')
            
            report_lines.extend([
                '',
                '总结:',
                summary_text,
                '',
                '问题的汇总:'
            ])
            
            # 添加所有问题
            question_list = []
            for q in questions:
                if isinstance(q, str):
                    question_list.append(q)
                elif isinstance(q, dict) and 'question' in q:
                    question_list.append(q['question'])
                elif hasattr(q, 'question'):
                    question_list.append(q.question)
            
            if question_list:
                for q in question_list:
                    report_lines.append(f'- {q}')
            else:
                report_lines.append('- （无问题数据）')
            
            return '\n'.join(report_lines)
            
        except Exception as e:
            return f"汇总报告生成失败：{str(e)}"
    
    def save_summary_report(self, report_content: str, batch_id: str) -> str:
        """保存汇总报告到文件"""
        filename = f"summary_report_{batch_id}.txt"
        filepath = f"./data/results/{filename}"
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report_content)
            return filepath
        except Exception as e:
            return f"保存汇总报告失败：{str(e)}"
    
    # =====================
    # 简洁过程报告（符合样例）- 保持向后兼容
    # =====================
    def format_simple_report(self, result: Dict[str, Any]) -> str:
        """生成符合样例的简洁过程报告
        严格按照样例格式：问题、批次号、搜索关键词、调研过的资料链接、总结、问题的汇总
        """
        try:
            # 从结果中提取基本信息
            topic = result.get('topic', '')
            workflow_id = result.get('workflow_id', 'unknown')
            search_rounds = result.get('search_rounds', [])
            comprehensive_summary = result.get('comprehensive_summary', {})
            questions = result.get('questions', [])
            
            # 1. 问题（主题）
            problem_text = topic if topic else '（未提供具体问题）'
            
            # 2. 批次号（简化格式）
            batch_id = workflow_id.replace('integrated_', '') if workflow_id.startswith('integrated_') else workflow_id
            
            # 3. 搜索关键词（从搜索轮次中提取实际的搜索查询）
            search_keywords = []
            for round_record in search_rounds:
                if hasattr(round_record, 'search_query') and round_record.search_query:
                    # 如果search_query与question不同，使用search_query
                    if round_record.search_query != round_record.question:
                        search_keywords.append(round_record.search_query)
                    else:
                        # 如果相同，使用问题作为关键词
                        search_keywords.append(round_record.question)
                elif hasattr(round_record, 'question') and round_record.question:
                    search_keywords.append(round_record.question)
            
            # 去重并限制数量
            unique_keywords = list(dict.fromkeys(search_keywords))[:10]
            
            # 4. 调研过的资料链接（从搜索轮次中提取）
            links = []
            for round_record in search_rounds:
                if hasattr(round_record, 'search_results') and round_record.search_results:
                    for item in round_record.search_results:
                        if hasattr(item, 'link') and item.link:
                            links.append(item.link)
                        elif isinstance(item, dict) and item.get('link'):
                            links.append(item['link'])
            
            # 去重并限制数量
            unique_links = list(dict.fromkeys(links))[:20]
            
            # 5. 总结（优先使用综合摘要，其次合并轮次摘要）
            summary_text = ''
            if comprehensive_summary.get('executive_summary'):
                summary_text = comprehensive_summary['executive_summary']
            else:
                # 从搜索轮次中提取摘要
                round_summaries = []
                for round_record in search_rounds:
                    if hasattr(round_record, 'summary') and round_record.summary:
                        round_summaries.append(round_record.summary)
                
                if round_summaries:
                    summary_text = self._combine_summaries(round_summaries)
                else:
                    summary_text = '（本次过程未能提取有效摘要）'
            
            # 6. 问题的汇总（从问题列表中提取）
            question_list = []
            for q in questions:
                if isinstance(q, str):
                    question_list.append(q)
                elif isinstance(q, dict) and 'question' in q:
                    question_list.append(q['question'])
                elif hasattr(q, 'question'):
                    question_list.append(q.question)
            
            # 严格按照样例格式拼装
            report_lines = [
                '问题:',
                problem_text,
                '',
                f'批次号: {batch_id}',
                '',
                '搜索关键词'
            ]
            
            # 添加搜索关键词
            if unique_keywords:
                for keyword in unique_keywords:
                    report_lines.append(keyword)
            else:
                report_lines.append('（无搜索关键词）')
            
            report_lines.extend([
                '',
                '调研过的资料链接:'
            ])
            
            # 添加调研链接
            if unique_links:
                for url in unique_links:
                    report_lines.append(f'- {url}')
            else:
                report_lines.append('- （无可用链接，可能因搜索异常未获取）')
            
            report_lines.extend([
                '',
                '总结:',
                summary_text,
                '',
                '问题的汇总:'
            ])
            
            # 添加问题汇总
            if question_list:
                for q in question_list:
                    report_lines.append(f'- {q}')
            else:
                report_lines.append('- （无问题数据）')
            
            return '\n'.join(report_lines)
            
        except Exception as e:
            return f"简洁报告生成失败：{str(e)}"

    def save_simple_report_to_file(self, report_content: str, filename: str = None) -> str:
        """保存简洁过程报告到文件"""
        if not filename:
            filename = f"simple_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = f"./data/results/{filename}"
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report_content)
            return filepath
        except Exception as e:
            return f"保存简洁报告失败：{str(e)}"
    
    def _generate_specific_recommendations(self, search_rounds: List[SearchRoundRecord]) -> List[str]:
        """基于搜索结果生成具体建议"""
        recommendations = []
        
        # 分析搜索结果的完整性
        total_rounds = len(search_rounds)
        successful_rounds = len([r for r in search_rounds if r.success])
        
        if successful_rounds < total_rounds:
            recommendations.append("建议补充完善相关信息的搜索，提高分析完整性")
        
        # 分析各方向的信息丰富度
        directional_rounds = self._group_rounds_by_direction(search_rounds)
        for direction, rounds in directional_rounds.items():
            avg_key_points = sum(len(r.key_points) for r in rounds if r.key_points) / len(rounds)
            if avg_key_points < 2:
                recommendations.append(f"建议深入挖掘{direction}方向的相关信息")
        
        # 基于关键点生成建议
        all_key_points = []
        for round_record in search_rounds:
            if round_record.key_points:
                all_key_points.extend(round_record.key_points)
        
        if all_key_points:
            # 分析关键词频率
            from collections import Counter
            word_freq = Counter()
            for point in all_key_points:
                words = point.split()
                word_freq.update(words)
            
            # 基于高频词生成建议
            if word_freq:
                top_words = word_freq.most_common(3)
                for word, count in top_words:
                    if count > 1:
                        recommendations.append(f"重点关注'{word}'相关领域的发展动态")
        
        return recommendations
    
    def _generate_executive_summary(self, search_rounds: List[SearchRoundRecord]) -> str:
        """从搜索轮次生成执行摘要"""
        if not search_rounds:
            return ""
        
        # 收集所有摘要
        all_summaries = [r.summary for r in search_rounds if r.summary]
        if not all_summaries:
            return ""
        
        # 合并摘要并提取关键信息
        combined_text = " ".join(all_summaries)
        
        # 简单的摘要生成：取前200字并添加总结
        if len(combined_text) > 200:
            summary = combined_text[:200] + "..."
        else:
            summary = combined_text
        
        # 添加分析维度信息
        directions = list(set(r.direction for r in search_rounds))
        direction_info = f"本次分析覆盖了{len(directions)}个维度：{', '.join(directions)}"
        
        return f"{summary}\n\n{direction_info}"
    
    def _analyze_direction_quality(self, search_rounds: List[SearchRoundRecord]) -> Dict[str, Dict[str, Any]]:
        """分析各方向的质量"""
        direction_stats = {}
        
        for round_record in search_rounds:
            direction = round_record.direction
            if direction not in direction_stats:
                direction_stats[direction] = {
                    'count': 0,
                    'total_key_points': 0,
                    'total_summary_length': 0,
                    'success_rate': 0
                }
            
            stats = direction_stats[direction]
            stats['count'] += 1
            stats['total_key_points'] += len(round_record.key_points) if round_record.key_points else 0
            stats['total_summary_length'] += len(round_record.summary) if round_record.summary else 0
            stats['success_rate'] += 1 if round_record.success else 0
        
        # 计算质量评级
        for direction, stats in direction_stats.items():
            avg_key_points = stats['total_key_points'] / stats['count']
            avg_summary_length = stats['total_summary_length'] / stats['count']
            success_rate = stats['success_rate'] / stats['count']
            
            # 质量评级逻辑
            if avg_key_points >= 3 and avg_summary_length >= 100 and success_rate >= 0.8:
                quality = "高"
            elif avg_key_points >= 2 and avg_summary_length >= 50 and success_rate >= 0.6:
                quality = "中"
            else:
                quality = "低"
            
            stats['quality'] = quality
        
        return direction_stats
    
    def _categorize_key_findings(self, search_rounds: List[SearchRoundRecord]) -> Dict[str, List[str]]:
        """将关键发现按类别分组"""
        all_key_points = []
        for round_record in search_rounds:
            if round_record.key_points:
                all_key_points.extend(round_record.key_points)
        
        if not all_key_points:
            return {}
        
        # 简单的关键词分类
        categories = {
            "技术趋势": [],
            "市场动态": [],
            "政策法规": [],
            "发展机遇": [],
            "挑战风险": [],
            "其他发现": []
        }
        
        # 关键词匹配规则
        tech_keywords = ["技术", "创新", "发展", "趋势", "AI", "数字化", "智能化"]
        market_keywords = ["市场", "需求", "竞争", "价格", "销售", "用户", "客户"]
        policy_keywords = ["政策", "法规", "标准", "监管", "合规", "法律"]
        opportunity_keywords = ["机遇", "机会", "潜力", "前景", "增长", "发展"]
        risk_keywords = ["风险", "挑战", "问题", "困难", "威胁", "危机"]
        
        for point in all_key_points:
            categorized = False
            point_lower = point.lower()
            
            for keyword in tech_keywords:
                if keyword in point_lower:
                    categories["技术趋势"].append(point)
                    categorized = True
                    break
            
            if not categorized:
                for keyword in market_keywords:
                    if keyword in point_lower:
                        categories["市场动态"].append(point)
                        categorized = True
                        break
            
            if not categorized:
                for keyword in policy_keywords:
                    if keyword in point_lower:
                        categories["政策法规"].append(point)
                        categorized = True
                        break
            
            if not categorized:
                for keyword in opportunity_keywords:
                    if keyword in point_lower:
                        categories["发展机遇"].append(point)
                        categorized = True
                        break
            
            if not categorized:
                for keyword in risk_keywords:
                    if keyword in point_lower:
                        categories["挑战风险"].append(point)
                        categorized = True
                        break
            
            if not categorized:
                categories["其他发现"].append(point)
        
        # 过滤空类别
        return {k: v for k, v in categories.items() if v}
    
    def format_endless_mode_report(self, endless_result: Dict[str, Any]) -> str:
        """格式化无尽模式报告"""
        try:
            topic = endless_result.get("topic", "未知主题")
            endless_mode_id = endless_result.get("endless_mode_id", "unknown")
            execution_stats = endless_result.get("execution_stats", {})
            
            # 构建邮件内容
            email_parts = [
                f"主题：{topic}",
                f"无尽模式探索报告",
                f"",
                f"=== 执行概览 ===",
                f"总迭代次数：{execution_stats.get('total_iterations', 0)}",
                f"完成迭代次数：{execution_stats.get('completed_iterations', 0)}",
                f"失败迭代次数：{execution_stats.get('failed_iterations', 0)}",
                f"成功率：{execution_stats.get('success_rate', 0) * 100:.1f}%",
                f"平均评分：{execution_stats.get('average_score', 0.0):.1f}分",
                f"总耗时：{execution_stats.get('total_time', 0) / 60:.1f}分钟",
                f""
            ]
            
            # 前N个完整报告
            top_reports = endless_result.get("top_reports", [])
            if top_reports:
                email_parts.extend([
                    f"=== 高质量完整报告（前{len(top_reports)}个）===",
                    f""
                ])
                
                for i, report in enumerate(top_reports, 1):
                    email_parts.extend([
                        f"【第{report.get('round_number', i)}轮报告】",
                        f"评分：{report.get('scores', {}).get('comprehensive_score', 0.0):.1f}分 ({report.get('quality_level', '未知')})",
                        f"最佳方向：{report.get('best_direction', '未知')}",
                        f"关键发现：",
                    ])
                    
                    key_findings = report.get('key_findings', [])
                    for finding in key_findings[:5]:
                        email_parts.append(f"  • {finding}")
                    
                    email_parts.append("")
            
            # 其余轮次摘要
            summary_reports = endless_result.get("summary_reports", [])
            if summary_reports:
                email_parts.extend([
                    f"=== 其余轮次摘要 ===",
                    f""
                ])
                
                for summary in summary_reports:
                    if summary.get("status") == "success":
                        email_parts.extend([
                            f"【第{summary.get('round_number', '未知')}轮摘要】",
                            f"{summary.get('summary', '摘要生成失败')}",
                            f""
                        ])
            
            # 总结
            email_parts.extend([
                f"=== 总结 ===",
                f"本次无尽模式探索共完成{execution_stats.get('completed_iterations', 0)}轮迭代，",
                f"发现了{len(endless_result.get('all_round_reports', []))}个有价值的探索方向，",
                f"平均评分{execution_stats.get('average_score', 0.0):.1f}分。",
                f"",
                f"报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ])
            
            return "\n".join(email_parts)
            
        except Exception as e:
            return f"无尽模式报告格式化失败: {str(e)}"
    
    def format_top_round_report(self, report: Dict[str, Any]) -> str:
        """格式化单个完整轮次报告"""
        try:
            round_number = report.get("round_number", 0)
            topic = report.get("topic", "未知主题")
            scores = report.get("scores", {})
            best_direction = report.get("best_direction", "未知")
            key_findings = report.get("key_findings", [])
            
            report_parts = [
                f"【第{round_number}轮完整报告】",
                f"主题：{topic}",
                f"综合评分：{scores.get('comprehensive_score', 0.0):.1f}分",
                f"质量等级：{report.get('quality_level', '未知')}",
                f"最佳方向：{best_direction}",
                f"",
                f"=== 详细评分 ===",
                f"搜索质量：{scores.get('search_quality_score', 0.0):.1f}分",
                f"内容深度：{scores.get('content_depth_score', 0.0):.1f}分",
                f"技术指标：{scores.get('technical_metrics_score', 0.0):.1f}分",
                f"新颖性：{scores.get('novelty_score', 0.0):.1f}分",
                f"",
                f"=== 关键发现 ===",
            ]
            
            for i, finding in enumerate(key_findings[:10], 1):
                report_parts.append(f"{i}. {finding}")
            
            return "\n".join(report_parts)
            
        except Exception as e:
            return f"轮次报告格式化失败: {str(e)}"
    
    def format_round_summary(self, summary: Dict[str, Any]) -> str:
        """格式化轮次摘要"""
        try:
            round_number = summary.get("round_number", 0)
            topic = summary.get("topic", "未知主题")
            summary_text = summary.get("summary", "摘要生成失败")
            key_directions = summary.get("key_directions", [])
            core_findings = summary.get("core_findings", [])
            important_insights = summary.get("important_insights", [])
            
            summary_parts = [
                f"【第{round_number}轮摘要】",
                f"主题：{topic}",
                f"",
                f"=== 摘要内容 ===",
                f"{summary_text}",
                f""
            ]
            
            if key_directions:
                summary_parts.extend([
                    f"=== 关键方向 ===",
                    f"{', '.join(key_directions)}",
                    f""
                ])
            
            if core_findings:
                summary_parts.extend([
                    f"=== 核心发现 ===",
                ])
                for finding in core_findings[:5]:
                    summary_parts.append(f"• {finding}")
                summary_parts.append("")
            
            if important_insights:
                summary_parts.extend([
                    f"=== 重要洞察 ===",
                ])
                for insight in important_insights[:3]:
                    summary_parts.append(f"• {insight}")
                summary_parts.append("")
            
            return "\n".join(summary_parts)
            
        except Exception as e:
            return f"轮次摘要格式化失败: {str(e)}"
    
    def save_endless_mode_report(self, endless_result: Dict[str, Any], filename: str = None) -> str:
        """保存无尽模式报告到文件"""
        try:
            if not filename:
                endless_mode_id = endless_result.get("endless_mode_id", "unknown")
                filename = f"endless_mode_report_{endless_mode_id}.txt"
            
            # 格式化报告
            email_content = self.format_endless_mode_report(endless_result)
            
            # 保存到文件
            filepath = self.save_email_to_file(email_content, filename)
            
            return filepath
            
        except Exception as e:
            raise Exception(f"保存无尽模式报告失败: {str(e)}")
    
    def save_top_reports(self, top_reports: List[Dict[str, Any]], endless_mode_id: str) -> List[str]:
        """保存前N个完整报告到文件"""
        try:
            filepaths = []
            
            for i, report in enumerate(top_reports, 1):
                # 格式化报告
                report_content = self.format_top_round_report(report)
                
                # 保存到文件
                filename = f"top_report_{i}_{endless_mode_id}.txt"
                filepath = self.save_email_to_file(report_content, filename)
                filepaths.append(filepath)
            
            return filepaths
            
        except Exception as e:
            raise Exception(f"保存前N个报告失败: {str(e)}")
    
    def save_round_summaries(self, summaries: List[Dict[str, Any]], endless_mode_id: str) -> List[str]:
        """保存轮次摘要到文件"""
        try:
            filepaths = []
            
            for summary in summaries:
                if summary.get("status") == "success":
                    # 格式化摘要
                    summary_content = self.format_round_summary(summary)
                    
                    # 保存到文件
                    round_number = summary.get("round_number", 0)
                    filename = f"round_summary_{round_number}_{endless_mode_id}.txt"
                    filepath = self.save_email_to_file(summary_content, filename)
                    filepaths.append(filepath)
            
            return filepaths
            
        except Exception as e:
            raise Exception(f"保存轮次摘要失败: {str(e)}")
