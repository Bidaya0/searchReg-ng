"""
长时间运行工作流控制器 - 支持几小时运行的智能搜索系统
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import traceback

from storage_models import LongRunningWorkflowState, QuestionItem, SearchResult
from checkpoint_manager import CheckpointManager
from resource_monitor import ResourceMonitor
from long_running_memory_manager import LongRunningMemoryManager
from progress_tracker import ProgressTracker
from integrated_workflow import IntegratedWorkflowController
from config import get_config
from logger import workflow_logger
from contextual_reflection_analyzer import ContextualReflectionAnalyzer, ContextualReflection, SearchContext
from contextual_question_optimizer import ContextualQuestionOptimizer


class LongRunningWorkflowController(IntegratedWorkflowController):
    """长时间运行工作流控制器"""
    
    def __init__(self, config: Dict[str, Any], deadline: Optional[datetime] = None, time_strategy: str = "adaptive"):
        # 初始化基础配置
        super().__init__(config)
        
        # 长时间运行配置
        self.long_running_config = config.get('long_running', {})
        self.deadline = deadline or (datetime.now() + timedelta(hours=self.long_running_config.get('max_duration_hours', 8)))
        self.time_strategy = time_strategy
        
        # 初始化长时间运行组件
        self.checkpoint_manager = CheckpointManager(
            self.long_running_config.get('checkpoints_dir', './data/checkpoints')
        )
        self.resource_monitor = ResourceMonitor(self.long_running_config)
        self.memory_manager = LongRunningMemoryManager(self.long_running_config)
        self.progress_tracker = ProgressTracker(self.long_running_config)
        
        # 初始化反思机制组件
        self.contextual_reflection_analyzer = ContextualReflectionAnalyzer(config)
        self.contextual_question_optimizer = ContextualQuestionOptimizer(config)
        
        # 更新配置以适应长时间运行
        self._update_config_for_long_running()
        
        # 创建长时间运行的工作流
        self.workflow = self._create_long_running_workflow()
    
    def _update_config_for_long_running(self):
        """更新配置以适应长时间运行"""
        # 更新搜索配置
        self.search_timeout = self.long_running_config.get('search_timeout', 300)
        self.max_workers = self.long_running_config.get('max_concurrent_searches', 3)
        self.retry_count = self.long_running_config.get('search_retry_count', 5)
        
        # 更新LLM配置
        self.llm = ChatOpenAI(
            model=self.config.get("model"),
            api_key=self.config.get("api_key"),
            base_url=self.config.get("base_url"),
            temperature=self.config.get("temperature", 0.7),
            max_tokens=self.config.get("max_tokens", 2000)
        )
    
    def _create_long_running_workflow(self) -> StateGraph:
        """创建长时间运行的工作流"""
        workflow = StateGraph(LongRunningWorkflowState)
        
        # 添加长时间运行特定节点
        workflow.add_node("resource_monitor", self._resource_monitor_node)
        workflow.add_node("checkpoint_saver", self._checkpoint_saver_node)
        workflow.add_node("memory_cleaner", self._memory_cleaner_node)
        workflow.add_node("progress_reporter", self._progress_reporter_node)
        
        # 原有节点（带长时间运行支持）
        workflow.add_node("question_generation", self._long_running_question_generation_node)
        workflow.add_node("parallel_search", self._long_running_parallel_search_node)
        workflow.add_node("result_processing", self._long_running_result_processing_node)
        workflow.add_node("summary_generator", self._long_running_summary_generator_node)
        workflow.add_node("report_generation", self._long_running_report_generation_node)
        
        # 设置入口点
        workflow.set_entry_point("resource_monitor")
        
        # 添加边
        workflow.add_edge("resource_monitor", "question_generation")
        workflow.add_edge("question_generation", "checkpoint_saver")
        workflow.add_edge("checkpoint_saver", "parallel_search")
        workflow.add_edge("parallel_search", "memory_cleaner")
        workflow.add_edge("memory_cleaner", "result_processing")
        workflow.add_edge("result_processing", "progress_reporter")
        workflow.add_edge("summary_generator", "report_generation")
        
        # 条件边
        workflow.add_conditional_edges(
            "progress_reporter",
            self._should_continue_long_running,
            {
                "continue": "question_generation",
                "finalize": "summary_generator",
                "timeout": "report_generation"
            }
        )
        
        return workflow.compile()
    
    def _resource_monitor_node(self, state: LongRunningWorkflowState) -> LongRunningWorkflowState:
        """资源监控节点"""
        workflow_logger.log_node_start("resource_monitor", state)
        
        try:
            # 检查系统资源
            resource_status = self.resource_monitor.check_resources()
            
            # 检查内存使用
            memory_usage_mb = resource_status.get('system', {}).get('memory_usage_mb', 0)
            max_memory_mb = self.long_running_config.get('max_memory_usage_mb', 2048)
            
            if memory_usage_mb > max_memory_mb * 0.8:
                state['memory_pressure'] = True
                workflow_logger.log_warning(f"内存使用过高: {memory_usage_mb:.1f}MB")
            else:
                state['memory_pressure'] = False
            
            # 检查磁盘使用
            disk_usage_mb = resource_status.get('system', {}).get('disk_usage_mb', 0)
            max_disk_mb = self.long_running_config.get('max_disk_usage_mb', 10240)
            
            if disk_usage_mb > max_disk_mb * 0.8:
                state['disk_pressure'] = True
                workflow_logger.log_warning(f"磁盘使用过高: {disk_usage_mb:.1f}MB")
            else:
                state['disk_pressure'] = False
            
            # 检查运行时间
            elapsed_time = (datetime.now() - state['start_time']).total_seconds()
            remaining_time = (self.deadline - datetime.now()).total_seconds()
            
            state['elapsed_time'] = elapsed_time
            state['remaining_time'] = remaining_time
            state['resource_status'] = resource_status
            
            # 如果资源不足，触发清理
            if state['memory_pressure'] or state['disk_pressure']:
                state['trigger_cleanup'] = True
            
            workflow_logger.log_info(f"资源监控完成 - 内存: {memory_usage_mb:.1f}MB, 剩余时间: {remaining_time/3600:.1f}小时")
            
        except Exception as e:
            workflow_logger.log_error(f"资源监控异常: {str(e)}", "resource_monitor")
            state['resource_status'] = {"error": str(e)}
        
        workflow_logger.log_node_end("resource_monitor", {
            "memory_pressure": state.get('memory_pressure', False),
            "disk_pressure": state.get('disk_pressure', False)
        })
        
        return state
    
    def _checkpoint_saver_node(self, state: LongRunningWorkflowState) -> LongRunningWorkflowState:
        """检查点保存节点"""
        workflow_logger.log_node_start("checkpoint_saver", state)
        
        try:
            # 检查是否需要保存检查点
            last_checkpoint = state.get('last_checkpoint_time', state['start_time'])
            time_since_checkpoint = (datetime.now() - last_checkpoint).total_seconds()
            checkpoint_interval = self.long_running_config.get('checkpoint_interval_minutes', 15) * 60
            
            if (time_since_checkpoint >= checkpoint_interval or 
                state.get('force_checkpoint', False)):
                
                # 保存检查点
                custom_checkpoint_id = f"checkpoint_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                checkpoint_path = self.checkpoint_manager.save_checkpoint(state, custom_checkpoint_id)
                
                if checkpoint_path:
                    state['last_checkpoint_time'] = datetime.now()
                    state['checkpoint_path'] = checkpoint_path
                    state['custom_checkpoint_id'] = custom_checkpoint_id
                    state['force_checkpoint'] = False
                    workflow_logger.log_info(f"检查点已保存: {checkpoint_path}")
                else:
                    workflow_logger.log_warning("检查点保存失败")
            else:
                workflow_logger.log_debug(f"跳过检查点保存，距离上次保存: {time_since_checkpoint/60:.1f}分钟")
            
        except Exception as e:
            workflow_logger.log_error(f"检查点保存异常: {str(e)}", "checkpoint_saver")
        
        workflow_logger.log_node_end("checkpoint_saver", {
            "checkpoint_saved": state.get('checkpoint_path') is not None
        })
        
        return state
    
    def _memory_cleaner_node(self, state: LongRunningWorkflowState) -> LongRunningWorkflowState:
        """内存清理节点"""
        workflow_logger.log_node_start("memory_cleaner", state)
        
        try:
            # 检查是否需要清理内存
            if (state.get('trigger_cleanup', False) or 
                self.memory_manager.should_cleanup(state)):
                
                # 执行内存清理
                cleanup_result = self.memory_manager.cleanup_memory(state)
                
                state['trigger_cleanup'] = False
                state['memory_cleanup_count'] = state.get('memory_cleanup_count', 0) + 1
                
                workflow_logger.log_info(f"内存清理完成: 释放 {cleanup_result.get('freed_mb', 0):.1f}MB")
            else:
                workflow_logger.log_debug("跳过内存清理")
            
        except Exception as e:
            workflow_logger.log_error(f"内存清理异常: {str(e)}", "memory_cleaner")
        
        workflow_logger.log_node_end("memory_cleaner", {
            "cleanup_performed": state.get('trigger_cleanup', False)
        })
        
        return state
    
    def _progress_reporter_node(self, state: LongRunningWorkflowState) -> LongRunningWorkflowState:
        """进度报告节点"""
        workflow_logger.log_node_start("progress_reporter", state)
        
        try:
            # 计算进度
            progress = self.progress_tracker.calculate_progress(state)
            state['progress'] = progress
            
            # 生成进度报告
            progress_report = {
                "iteration": state.get('current_iteration', 0),
                "elapsed_time": state['elapsed_time'],
                "remaining_time": state['remaining_time'],
                "completion_percentage": progress['completion_percentage'],
                "quality_score": progress.get('quality_metrics', {}).get('current_score', 0),
                "results_count": len(state.get('search_results', [])),
                "memory_usage": state['resource_status'].get('system', {}).get('memory_usage_mb', 0),
                "converged": progress.get('convergence_status', {}).get('converged', False)
            }
            
            # 保存进度报告
            self.progress_tracker.save_progress_report(progress_report)
            
            # 检查是否应该继续
            should_continue = self._should_continue_long_running(state)
            state['should_continue'] = should_continue
            
            workflow_logger.log_info(f"进度报告: {progress['completion_percentage']:.1f}% 完成, 质量分数: {progress.get('quality_metrics', {}).get('current_score', 0):.3f}")
            
        except Exception as e:
            workflow_logger.log_error(f"进度报告异常: {str(e)}", "progress_reporter")
            state['should_continue'] = "continue"
        
        workflow_logger.log_node_end("progress_reporter", {
            "progress": state.get('progress', {}),
            "should_continue": state.get('should_continue', 'continue')
        })
        
        return state
    
    def _should_continue_long_running(self, state: LongRunningWorkflowState) -> str:
        """决定是否继续长时间运行"""
        try:
            # 检查时间条件
            remaining_time = state.get('remaining_time', 0)
            if remaining_time <= 0:
                return "timeout"
            
            # 检查迭代次数
            current_iteration = state.get('current_iteration', 0)
            max_iterations = self.long_running_config.get('max_iterations', 100)
            if current_iteration >= max_iterations:
                return "finalize"
            
            # 检查质量收敛
            progress = state.get('progress', {})
            if progress.get('convergence_status', {}).get('converged', False):
                return "finalize"
            
            # 检查资源压力
            if (state.get('memory_pressure', False) and 
                state.get('memory_cleanup_count', 0) > 3):
                return "finalize"
            
            # 检查最小剩余时间
            min_remaining_time = self.long_running_config.get('min_iteration_time_seconds', 30)
            if remaining_time < min_remaining_time:
                return "finalize"
            
            # 时间策略检查
            return self._check_time_strategy_conditions(state)
            
        except Exception as e:
            workflow_logger.log_error(f"继续判断异常: {str(e)}")
            return "finalize"
    
    def _check_time_strategy_conditions(self, state: LongRunningWorkflowState) -> str:
        """检查时间策略条件"""
        remaining_time = state.get('remaining_time', 0)
        current_iteration = state.get('current_iteration', 0)
        
        if self.time_strategy == "hard":
            # 硬截止时间策略：严格按照截止时间执行
            if remaining_time < 300:  # 5分钟缓冲
                workflow_logger.log_info(f"硬截止时间策略：剩余时间不足5分钟，准备结束")
                return "finalize"
            return "continue"
            
        elif self.time_strategy == "soft":
            # 软截止时间策略：在截止时间前预留缓冲时间
            buffer_time = 1800  # 30分钟缓冲
            if remaining_time < buffer_time:
                workflow_logger.log_info(f"软截止时间策略：进入缓冲期，减少迭代强度")
                # 在缓冲期内，每轮迭代间隔更长
                if current_iteration % 2 == 0:  # 每隔一轮执行一次
                    return "continue"
                else:
                    return "finalize"
            return "continue"
            
        else:  # adaptive
            # 自适应策略：根据进度和质量动态调整
            return self._adaptive_time_strategy(state)
    
    def _adaptive_time_strategy(self, state: LongRunningWorkflowState) -> str:
        """自适应时间策略"""
        remaining_time = state.get('remaining_time', 0)
        current_iteration = state.get('current_iteration', 0)
        progress = state.get('progress', {})
        quality_metrics = progress.get('quality_metrics', {})
        current_quality = quality_metrics.get('current_score', 0)
        
        # 如果质量已经很高（>0.8），减少迭代频率
        if current_quality > 0.8:
            if remaining_time > 3600:  # 还有1小时以上
                if current_iteration % 3 == 0:  # 每3轮执行一次
                    workflow_logger.log_info(f"自适应策略：高质量状态，减少迭代频率")
                    return "continue"
                else:
                    return "finalize"
            else:
                workflow_logger.log_info(f"自适应策略：高质量且时间紧张，准备结束")
                return "finalize"
        
        # 如果质量较低，增加迭代频率
        elif current_quality < 0.5:
            workflow_logger.log_info(f"自适应策略：质量较低，继续迭代提升")
            return "continue"
        
        # 中等质量，正常迭代
        else:
            workflow_logger.log_info(f"自适应策略：中等质量，正常迭代")
            return "continue"
    
    def _long_running_question_generation_node(self, state: LongRunningWorkflowState) -> LongRunningWorkflowState:
        """长时间运行问题生成节点"""
        workflow_logger.log_node_start("long_running_question_generation", state)
        
        try:
            # 检查时间
            if state.get('remaining_time', 0) <= 0:
                state['status'] = "timeout"
                return state
            
            # 根据剩余时间调整问题数量
            remaining_ratio = state['remaining_time'] / (self.deadline - state['start_time']).total_seconds()
            
            if remaining_ratio < 0.3:  # 时间紧急，减少问题数量
                max_questions = 5
            elif remaining_ratio < 0.6:  # 时间紧张，中等问题数量
                max_questions = 15
            else:  # 时间充足，正常问题数量
                max_questions = 25
            
            # 调用问题生成
            result = self.question_workflow.generate_questions(state['topic'])
            
            if result.get("status") == "completed":
                # 限制问题数量
                questions = result.get('questions', [])[:max_questions]
                state['questions'] = questions
                state['question_generation_completed'] = True
                
                workflow_logger.log_info(f"问题生成完成: {len(questions)}个问题（限制：{max_questions}）")
            else:
                state['question_generation_completed'] = False
                state['question_generation_error'] = result.get('error', '问题生成失败')
            
        except Exception as e:
            state['question_generation_completed'] = False
            state['question_generation_error'] = str(e)
            workflow_logger.log_error(f"问题生成异常: {str(e)}", "long_running_question_generation")
        
        workflow_logger.log_node_end("long_running_question_generation", {
            "completed": state['question_generation_completed'],
            "remaining_time": state.get('remaining_time', 0)
        })
        
        return state
    
    def _long_running_parallel_search_node(self, state: LongRunningWorkflowState) -> LongRunningWorkflowState:
        """长时间运行并行搜索节点"""
        workflow_logger.log_node_start("long_running_parallel_search", state)
        
        try:
            # 检查时间
            if state.get('remaining_time', 0) <= 0:
                state['status'] = "timeout"
                return state
            
            questions = state.get('questions', [])
            if not questions:
                state['search_completed'] = False
                state['search_errors'] = ["没有问题需要搜索"]
                return state
            
            # 根据剩余时间调整搜索策略
            remaining_time = state['remaining_time']
            if remaining_time < 60:  # 剩余时间少于1分钟
                questions = questions[:3]
                max_workers = 1
                search_timeout = min(10, remaining_time * 0.8)
            elif remaining_time < 300:  # 剩余时间少于5分钟
                questions = questions[:10]
                max_workers = 2
                search_timeout = min(20, remaining_time * 0.6)
            else:
                max_workers = self.max_workers
                search_timeout = self.search_timeout
            
            workflow_logger.log_info(f"开始时间控制搜索：{len(questions)}个问题，{max_workers}个并发，{search_timeout}秒超时")
            
            # 创建搜索任务
            search_tasks = []
            for i, question in enumerate(questions):
                task = {
                    "question_id": f"q_{i+1}",
                    "question": question.question if hasattr(question, 'question') else str(question),
                    "original_topic": state['topic'],
                    "priority": i,
                    "status": "pending",
                    "created_at": datetime.now(),
                    "completed_at": None,
                    "search_result": None,
                    "error": None
                }
                search_tasks.append(task)
            
            state['search_tasks'] = search_tasks
            state['search_results'] = []
            state['search_errors'] = []
            
            # 执行并发搜索
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_task = {
                    executor.submit(self._execute_timed_search, task, search_timeout): task
                    for task in search_tasks
                }
                
                # 收集结果
                overall_timeout = min(remaining_time * 0.8, 300)  # 最多5分钟
                for future in as_completed(future_to_task, timeout=overall_timeout):
                    task = future_to_task[future]
                    try:
                        result = future.result()
                        if result:
                            state['search_results'].append(result)
                            task['status'] = "completed"
                            task['completed_at'] = datetime.now()
                            task['search_result'] = result
                        else:
                            task['status'] = "failed"
                            task['error'] = "搜索返回空结果"
                            state['search_errors'].append(f"任务 {task['question_id']}: 搜索返回空结果")
                    except Exception as e:
                        task['status'] = "failed"
                        task['error'] = str(e)
                        state['search_errors'].append(f"任务 {task['question_id']}: {str(e)}")
                        workflow_logger.log_error(f"搜索任务失败: {task['question_id']} - {str(e)}")
            
            state['search_completed'] = True
            workflow_logger.log_info(f"并行搜索完成，成功 {len(state['search_results'])} 个，失败 {len(state['search_errors'])} 个")
            
        except Exception as e:
            state['search_completed'] = False
            state['search_errors'].append(str(e))
            workflow_logger.log_error(f"并行搜索异常: {str(e)}", "long_running_parallel_search")
        
        workflow_logger.log_node_end("long_running_parallel_search", {
            "completed": state['search_completed'],
            "remaining_time": state.get('remaining_time', 0)
        })
        
        return state
    
    def _execute_timed_search(self, task: Dict[str, Any], timeout: float) -> Optional[SearchResult]:
        """执行带时间限制的搜索"""
        try:
            # 使用信号量或线程超时机制
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("搜索超时")
            
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(int(timeout))
            
            try:
                result = self.search_workflow.process_topic(task['question'])
                return result
            finally:
                signal.alarm(0)  # 取消超时
                
        except TimeoutError:
            workflow_logger.log_warning(f"搜索任务超时: {task['question']}")
            return None
        except Exception as e:
            workflow_logger.log_error(f"搜索任务异常: {task['question']} - {str(e)}")
            return None
    
    def _long_running_result_processing_node(self, state: LongRunningWorkflowState) -> LongRunningWorkflowState:
        """长时间运行结果处理节点"""
        # 复用原有的结果处理逻辑，但添加时间检查
        if not state.get('search_completed', False):
            state['result_processing_completed'] = False
            state['result_processing_error'] = "搜索未完成"
            return state
        
        # 调用原有的结果处理逻辑
        return self._result_processing_node(state)
    
    def _long_running_summary_generator_node(self, state: LongRunningWorkflowState) -> LongRunningWorkflowState:
        """长时间运行总结生成节点"""
        # 复用原有的总结生成逻辑
        return self._integrated_summary_node(state)
    
    def _long_running_report_generation_node(self, state: LongRunningWorkflowState) -> LongRunningWorkflowState:
        """长时间运行报告生成节点"""
        # 复用原有的报告生成逻辑，但添加长时间运行统计
        result = self._report_generation_node(state)
        
        # 添加长时间运行统计
        if state.get('final_report'):
            state['final_report']['long_running_stats'] = {
                "total_iterations": state.get('current_iteration', 0),
                "elapsed_hours": state.get('elapsed_time', 0) / 3600,
                "memory_cleanup_count": state.get('memory_cleanup_count', 0),
                "checkpoint_count": len(self.checkpoint_manager.list_checkpoints()),
                "final_quality_score": state.get('progress', {}).get('quality_metrics', {}).get('current_score', 0),
                "converged": state.get('progress', {}).get('convergence_status', {}).get('converged', False)
            }
        
        return result
    
    def process_topic(self, topic: str) -> Dict[str, Any]:
        """处理主题的长时间运行工作流"""
        workflow_logger.log_workflow_start("LongRunningWorkflow", topic)
        
        try:
            # 生成工作流ID
            workflow_id = f"long_running_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # 初始化状态
            initial_state: LongRunningWorkflowState = {
                "topic": topic,
                "status": "running",
                "error": None,
                "start_time": datetime.now(),
                "end_time": None,
                "workflow_id": workflow_id,
                
                # 时间控制
                "deadline": self.deadline,
                "elapsed_time": 0.0,
                "remaining_time": (self.deadline - datetime.now()).total_seconds(),
                "time_warnings": [],
                "time_strategy": self.time_strategy,
                
                # 迭代控制
                "current_iteration": 0,
                "max_iterations": self.long_running_config.get('max_iterations', 100),
                "iteration_budget": 0.0,
                "quality_threshold": 0.8,
                "convergence_threshold": self.long_running_config.get('quality_convergence_threshold', 0.02),
                
                # 质量评估
                "quality_scores": [],
                "improvement_directions": [],
                "convergence_metrics": {},
                
                # 结果累积
                "accumulated_results": [],
                "best_results": {},
                "improvement_history": [],
                
                # 资源管理
                "resource_status": {},
                "memory_pressure": False,
                "disk_pressure": False,
                "trigger_cleanup": False,
                "memory_cleanup_count": 0,
                
                # 检查点管理
                "last_checkpoint_time": None,
                "checkpoint_path": None,
                "custom_checkpoint_id": None,
                "force_checkpoint": False,
                
                # 进度跟踪
                "progress": {},
                "should_continue": "continue",
                
                # 原有工作流状态字段
                "questions": [],
                "question_directions": [],
                "question_generation_completed": False,
                "question_generation_error": None,
                
                "search_tasks": [],
                "search_results": [],
                "search_progress": {},
                "search_completed": False,
                "search_errors": [],
                
                "processed_results": None,
                "result_processing_completed": False,
                "result_processing_error": None,
                
                "integrated_summary": None,
                "summary_completed": False,
                "summary_error": None,
                
                "final_report": None,
                "report_generated": False,
                
                "workflow_record": None,
                "search_rounds": []
            }
            
            # 运行工作流
            final_state = self.workflow.invoke(initial_state)
            
            # 构建最终结果
            result_dict = final_state.get('final_report', {})
            result_dict['status'] = final_state.get('status', 'unknown')
            result_dict['error'] = final_state.get('error')
            
            workflow_logger.log_workflow_end("LongRunningWorkflow", final_state.get('status', 'unknown'), result_dict)
            
            return result_dict
            
        except Exception as e:
            error_result = {
                "topic": topic,
                "status": "error",
                "error": str(e),
                "generated_at": datetime.now().isoformat()
            }
            workflow_logger.log_error(f"长时间运行工作流执行失败: {str(e)}", "process_topic")
            return error_result
    
    def execute_time_based_iterations(self, topic: str, duration_hours: int = 2) -> Dict[str, Any]:
        """执行基于时间的迭代搜索"""
        workflow_logger.log_workflow_start("TimeBasedIterations", topic)
        
        try:
            start_time = datetime.now()
            deadline = start_time + timedelta(hours=duration_hours)
            
            # 初始化状态
            state = self._initialize_iteration_state(topic, deadline)
            
            iteration_count = 0
            while self._should_continue_iteration_with_reflection(state):
                iteration_count += 1
                state['current_iteration'] = iteration_count
                state['iteration_start_time'] = datetime.now()
                
                workflow_logger.log_info(f"开始第 {iteration_count} 轮迭代（集成反思机制）")
                
                # 执行单次迭代
                iteration_result = self._execute_single_iteration(state)
                
                # 更新状态
                state = self._update_iteration_state(state, iteration_result)
                
                # 检查时间策略
                if self._check_time_strategy_conditions(state) == "finalize":
                    workflow_logger.log_info(f"时间策略条件满足，结束迭代")
                    break
                
                # 更新剩余时间
                state['remaining_time'] = (deadline - datetime.now()).total_seconds()
                
                # 记录上下文反馈信息
                contextual_info = ""
                if iteration_result.get('contextual_reflection'):
                    contextual_reflection = iteration_result['contextual_reflection']
                    contextual_info = f", 搜索效果: {contextual_reflection.search_effectiveness.get('effectiveness_score', 0):.3f}, 结果质量: {contextual_reflection.result_quality_assessment.get('quality_score', 0):.3f}"
                
                workflow_logger.log_info(f"第 {iteration_count} 轮迭代完成，剩余时间: {state['remaining_time']/3600:.1f}小时{contextual_info}")
            
            return self._finalize_iteration_results(state)
            
        except Exception as e:
            workflow_logger.log_error(f"时间迭代搜索失败: {str(e)}", "execute_time_based_iterations")
            return {
                "topic": topic,
                "status": "error",
                "error": str(e),
                "generated_at": datetime.now().isoformat()
            }
    
    def _initialize_iteration_state(self, topic: str, deadline: datetime) -> Dict[str, Any]:
        """初始化迭代状态"""
        return {
            "topic": topic,
            "start_time": datetime.now(),
            "deadline": deadline,
            "current_iteration": 0,
            "remaining_time": (deadline - datetime.now()).total_seconds(),
            "time_strategy": self.time_strategy,
            "quality_scores": [],
            "accumulated_results": [],
            "search_results": [],
            "questions": [],
            "status": "running"
        }
    
    def _perform_contextual_reflection_analysis(self, state: Dict[str, Any]) -> ContextualReflection:
        """执行基于上下文反馈的反思分析"""
        try:
            workflow_logger.log_info("开始执行基于上下文反馈的反思分析", "LongRunningWorkflow")
            
            # 使用上下文反思分析器进行分析
            contextual_reflection = self.contextual_reflection_analyzer.analyze_with_context(state)
            
            # 记录反思分析结果
            state['contextual_reflection_history'] = state.get('contextual_reflection_history', [])
            state['contextual_reflection_history'].append({
                "iteration": state.get('current_iteration', 0),
                "reflection": contextual_reflection,
                "timestamp": datetime.now().isoformat()
            })
            
            workflow_logger.log_info(f"上下文反思分析完成: 搜索效果 {contextual_reflection.search_effectiveness.get('effectiveness_score', 0):.3f}, "
                                   f"结果质量 {contextual_reflection.result_quality_assessment.get('quality_score', 0):.3f}")
            
            return contextual_reflection
            
        except Exception as e:
            workflow_logger.log_error(f"上下文反思分析失败: {str(e)}", "LongRunningWorkflow")
            # 返回默认分析结果
            return self.contextual_reflection_analyzer._create_default_reflection(state)
    
    def _extract_search_context(self, state: Dict[str, Any]) -> SearchContext:
        """提取搜索上下文"""
        try:
            workflow_logger.log_info("开始提取搜索上下文", "LongRunningWorkflow")
            
            # 使用上下文反思分析器提取搜索上下文
            search_context = self.contextual_reflection_analyzer._extract_search_context(state)
            
            workflow_logger.log_info(f"搜索上下文提取完成: {len(search_context.search_queries)}个查询, "
                                   f"{len(search_context.search_results)}个结果")
            
            return search_context
            
        except Exception as e:
            workflow_logger.log_error(f"搜索上下文提取失败: {str(e)}", "LongRunningWorkflow")
            # 返回默认上下文
            return SearchContext(
                search_queries=[], search_results=[], search_errors=[],
                search_timing={}, result_relevance_scores=[], result_diversity_score=0.0,
                result_completeness_score=0.0, problem_solving_steps=[], knowledge_gaps_identified=[],
                successful_patterns=[], failed_attempts=[], iteration_number=0, topic="", timestamp=datetime.now()
            )
    
    def _optimize_questions_with_contextual_feedback(self, state: Dict[str, Any], 
                                                   contextual_reflection: ContextualReflection,
                                                   search_context: SearchContext) -> List[Dict[str, Any]]:
        """基于上下文反馈优化问题"""
        try:
            workflow_logger.log_info("开始基于上下文反馈优化问题", "LongRunningWorkflow")
            
            # 获取当前问题
            current_questions = state.get('questions', [])
            topic = state['topic']
            
            if not current_questions:
                # 如果没有当前问题，生成基础问题
                return self._generate_iteration_questions(state)
            
            # 使用上下文问题优化器优化问题
            optimized_questions = self.contextual_question_optimizer.optimize_questions_with_context(
                current_questions, contextual_reflection, search_context, topic
            )
            
            # 记录优化效果
            state['contextual_optimization_history'] = state.get('contextual_optimization_history', [])
            state['contextual_optimization_history'].append({
                "iteration": state.get('current_iteration', 0),
                "original_count": len(current_questions),
                "optimized_count": len(optimized_questions),
                "contextual_reflection_confidence": contextual_reflection.confidence_score,
                "search_context_richness": len(search_context.search_results),
                "timestamp": datetime.now().isoformat()
            })
            
            workflow_logger.log_info(f"上下文问题优化完成: {len(current_questions)} -> {len(optimized_questions)}, "
                                   f"反思置信度: {contextual_reflection.confidence_score:.3f}")
            
            return optimized_questions
            
        except Exception as e:
            workflow_logger.log_error(f"上下文问题优化失败: {str(e)}", "LongRunningWorkflow")
            # 返回原问题
            return state.get('questions', [])
    
    def _should_continue_iteration(self, state: Dict[str, Any]) -> bool:
        """判断是否应该继续迭代（基础版本）"""
        remaining_time = state.get('remaining_time', 0)
        current_iteration = state.get('current_iteration', 0)
        max_iterations = self.long_running_config.get('max_iterations', 100)
        
        # 检查时间条件
        if remaining_time <= 0:
            workflow_logger.log_info("时间已用完，结束迭代")
            return False
        
        # 检查迭代次数
        if current_iteration >= max_iterations:
            workflow_logger.log_info(f"达到最大迭代次数 {max_iterations}，结束迭代")
            return False
        
        return True
    
    def _should_continue_iteration_with_reflection(self, state: Dict[str, Any]) -> bool:
        """基于反思结果判断是否应该继续迭代"""
        try:
            # 基础条件检查
            if not self._should_continue_iteration(state):
                return False
            
            # 反思分析检查
            reflection_history = state.get('reflection_history', [])
            if not reflection_history:
                return True  # 第一轮，继续
            
            # 获取最新的反思分析
            latest_reflection = reflection_history[-1].get('analysis')
            if not latest_reflection:
                return True
            
            # 基于反思结果决定是否继续
            current_iteration = state.get('current_iteration', 0)
            
            # 如果质量已经很高且改进潜力很小，考虑减少迭代频率
            if (latest_reflection.overall_quality_score > 0.85 and 
                latest_reflection.improvement_potential < 0.1):
                
                # 高质量状态，每3轮执行一次
                if current_iteration % 3 != 0:
                    workflow_logger.log_info("高质量状态，跳过本轮迭代")
                    return False
            
            # 如果质量很低但改进潜力很大，继续迭代
            elif (latest_reflection.overall_quality_score < 0.5 and 
                  latest_reflection.improvement_potential > 0.3):
                workflow_logger.log_info("低质量高潜力状态，继续迭代")
                return True
            
            # 如果发现重要缺失角度，继续迭代
            if latest_reflection.missing_angles:
                workflow_logger.log_info(f"发现 {len(latest_reflection.missing_angles)} 个缺失角度，继续迭代")
                return True
            
            # 默认继续
            return True
            
        except Exception as e:
            workflow_logger.log_error(f"反思迭代判断失败: {str(e)}")
            return True  # 出错时默认继续
    
    def _execute_single_iteration(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行单次迭代（集成基于上下文反馈的反思机制）"""
        try:
            iteration_start_time = datetime.now()
            current_iteration = state.get('current_iteration', 0)
            
            workflow_logger.log_info(f"开始第 {current_iteration} 轮迭代（集成上下文反馈反思机制）")
            
            # 1. 上下文反思分析（除了第一轮）
            contextual_reflection = None
            search_context = None
            if current_iteration > 0:
                contextual_reflection = self._perform_contextual_reflection_analysis(state)
                search_context = self._extract_search_context(state)
                workflow_logger.log_info(f"上下文反思分析完成，置信度: {contextual_reflection.confidence_score:.3f}")
            
            # 2. 生成或优化问题
            if contextual_reflection and search_context:
                # 基于上下文反馈优化问题
                questions = self._optimize_questions_with_contextual_feedback(state, contextual_reflection, search_context)
            else:
                # 第一轮：生成基础问题
                questions = self._generate_iteration_questions(state)
            
            # 3. 执行搜索
            search_results = self._execute_iteration_search(questions, state)
            
            # 4. 结果处理
            processed_results = self._process_iteration_results(search_results, state)
            
            # 5. 质量评估
            quality_score = self._evaluate_iteration_quality(processed_results, state)
            
            # 6. 学习更新
            self._update_iteration_learning(state, processed_results, quality_score)
            
            # 7. 上下文反馈结果记录
            iteration_result = {
                "questions": questions,
                "search_results": search_results,
                "processed_results": processed_results,
                "quality_score": quality_score,
                "iteration_time": (datetime.now() - iteration_start_time).total_seconds(),
                "contextual_reflection": contextual_reflection,
                "search_context": search_context,
                "contextual_optimization_applied": contextual_reflection is not None
            }
            
            workflow_logger.log_info(f"第 {current_iteration} 轮迭代完成，质量分数: {quality_score:.3f}")
            return iteration_result
            
        except Exception as e:
            workflow_logger.log_error(f"单次迭代执行失败: {str(e)}")
            return {"error": str(e)}
    
    def _generate_iteration_questions(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成迭代问题"""
        try:
            current_iteration = state.get('current_iteration', 0)
            topic = state['topic']
            
            # 根据迭代次数调整问题策略
            if current_iteration == 0:
                # 第一轮：生成基础问题
                result = self.question_workflow.generate_questions(topic)
                if result.get("status") == "completed":
                    return result.get('questions', [])[:25]  # 限制25个问题
            else:
                # 后续轮次：基于历史结果生成深化问题
                return self._generate_deepening_questions(state)
            
            return []
            
        except Exception as e:
            workflow_logger.log_error(f"问题生成失败: {str(e)}")
            return []
    
    def _generate_deepening_questions(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成深化问题"""
        try:
            # 基于历史搜索结果生成更深入的问题
            accumulated_results = state.get('accumulated_results', [])
            topic = state['topic']
            
            # 构建深化问题的提示词
            deepening_prompt = f"""
            基于以下搜索结果，为主题"{topic}"生成5个更深入的问题：
            
            历史搜索结果：
            {self._format_results_for_prompt(accumulated_results)}
            
            请生成：
            1. 更深入的技术细节问题
            2. 跨领域的关联问题
            3. 未来发展趋势问题
            4. 实际应用场景问题
            5. 挑战和解决方案问题
            """
            
            # 调用LLM生成深化问题
            messages = [
                SystemMessage(content="你是一个专业的研究问题生成器，能够基于已有信息生成更深入的研究问题。"),
                HumanMessage(content=deepening_prompt)
            ]
            
            response = self.llm.invoke(messages)
            questions_text = response.content
            
            # 解析生成的问题
            questions = self._parse_generated_questions(questions_text)
            return questions
            
        except Exception as e:
            workflow_logger.log_error(f"深化问题生成失败: {str(e)}")
            return []
    
    def _execute_iteration_search(self, questions: List[Dict[str, Any]], state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """执行迭代搜索"""
        try:
            search_results = []
            
            # 根据剩余时间调整搜索策略
            remaining_time = state.get('remaining_time', 0)
            if remaining_time > 7200:  # 2小时以上
                max_workers = 5
                search_timeout = 60
            elif remaining_time > 3600:  # 1-2小时
                max_workers = 3
                search_timeout = 45
            else:  # 1小时以内
                max_workers = 2
                search_timeout = 30
            
            # 限制问题数量
            max_questions = min(len(questions), 15 if remaining_time > 3600 else 8)
            questions_to_search = questions[:max_questions]
            
            workflow_logger.log_info(f"开始搜索 {len(questions_to_search)} 个问题")
            
            # 执行并发搜索
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_question = {
                    executor.submit(self._search_single_question, question, search_timeout): question
                    for question in questions_to_search
                }
                
                for future in as_completed(future_to_question, timeout=remaining_time * 0.8):
                    question = future_to_question[future]
                    try:
                        result = future.result()
                        if result:
                            search_results.append(result)
                    except Exception as e:
                        workflow_logger.log_error(f"搜索问题失败: {question} - {str(e)}")
            
            return search_results
            
        except Exception as e:
            workflow_logger.log_error(f"迭代搜索执行失败: {str(e)}")
            return []
    
    def _search_single_question(self, question: Dict[str, Any], timeout: float) -> Optional[Dict[str, Any]]:
        """搜索单个问题"""
        try:
            question_text = question.get('question', '') if isinstance(question, dict) else str(question)
            result = self.search_workflow.process_topic(question_text)
            
            if result.get("status") == "completed":
                return {
                    "question": question_text,
                    "results": result.get("search_results", []),
                    "summaries": result.get("summaries", []),
                    "key_points": result.get("key_points", [])
                }
            
            return None
            
        except Exception as e:
            workflow_logger.log_error(f"单个问题搜索失败: {question_text} - {str(e)}")
            return None
    
    def _process_iteration_results(self, search_results: List[Dict[str, Any]], state: Dict[str, Any]) -> Dict[str, Any]:
        """处理迭代结果"""
        try:
            # 合并到累积结果中
            accumulated_results = state.get('accumulated_results', [])
            accumulated_results.extend(search_results)
            
            # 去重处理
            unique_results = self._deduplicate_results(accumulated_results)
            
            return {
                "total_results": len(accumulated_results),
                "unique_results": len(unique_results),
                "new_results": len(search_results),
                "processed_results": unique_results
            }
            
        except Exception as e:
            workflow_logger.log_error(f"结果处理失败: {str(e)}")
            return {"error": str(e)}
    
    def _evaluate_iteration_quality(self, processed_results: Dict[str, Any], state: Dict[str, Any]) -> float:
        """评估迭代质量"""
        try:
            # 简单的质量评估：基于结果数量和多样性
            total_results = processed_results.get('total_results', 0)
            unique_results = processed_results.get('unique_results', 0)
            
            # 计算质量分数
            diversity_score = unique_results / max(total_results, 1)
            quantity_score = min(total_results / 100, 1.0)  # 100个结果为满分
            
            quality_score = (diversity_score + quantity_score) / 2
            
            return quality_score
            
        except Exception as e:
            workflow_logger.log_error(f"质量评估失败: {str(e)}")
            return 0.0
    
    def _update_iteration_learning(self, state: Dict[str, Any], processed_results: Dict[str, Any], quality_score: float):
        """更新迭代学习"""
        try:
            # 更新质量分数历史
            quality_scores = state.get('quality_scores', [])
            quality_scores.append({
                "iteration": state.get('current_iteration', 0),
                "score": quality_score,
                "timestamp": datetime.now().isoformat()
            })
            state['quality_scores'] = quality_scores
            
            # 更新累积结果
            state['accumulated_results'] = processed_results.get('processed_results', [])
            
        except Exception as e:
            workflow_logger.log_error(f"学习更新失败: {str(e)}")
    
    def _update_iteration_state(self, state: Dict[str, Any], iteration_result: Dict[str, Any]) -> Dict[str, Any]:
        """更新迭代状态"""
        try:
            # 更新搜索结果
            if 'search_results' in iteration_result:
                state['search_results'] = iteration_result['search_results']
            
            # 更新问题
            if 'questions' in iteration_result:
                state['questions'] = iteration_result['questions']
            
            # 更新处理结果
            if 'processed_results' in iteration_result:
                state['processed_results'] = iteration_result['processed_results']
            
            return state
            
        except Exception as e:
            workflow_logger.log_error(f"状态更新失败: {str(e)}")
            return state
    
    def _finalize_iteration_results(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """完成迭代结果（包含反思信息）"""
        try:
            # 生成最终报告
            final_report = {
                "topic": state['topic'],
                "status": "completed",
                "total_iterations": state.get('current_iteration', 0),
                "total_results": len(state.get('accumulated_results', [])),
                "quality_scores": state.get('quality_scores', []),
                "final_quality_score": state.get('quality_scores', [{}])[-1].get('score', 0) if state.get('quality_scores') else 0,
                "time_strategy": state.get('time_strategy', 'adaptive'),
                "elapsed_time": (datetime.now() - state['start_time']).total_seconds(),
                "generated_at": datetime.now().isoformat(),
                
                # 上下文反馈机制统计
                "contextual_reflection_stats": self._generate_contextual_reflection_stats(state),
                "contextual_optimization_stats": self._generate_contextual_optimization_stats(state),
                "contextual_feedback_enabled": True
            }
            
            return final_report
            
        except Exception as e:
            workflow_logger.log_error(f"结果完成失败: {str(e)}")
            return {"error": str(e)}
    
    def _generate_contextual_reflection_stats(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """生成基于上下文反馈的反思统计信息"""
        try:
            contextual_reflection_history = state.get('contextual_reflection_history', [])
            
            if not contextual_reflection_history:
                return {"contextual_reflection_count": 0, "avg_confidence_score": 0.0}
            
            # 统计上下文反思信息
            confidence_scores = []
            search_effectiveness_scores = []
            result_quality_scores = []
            knowledge_gaps_count = []
            
            for reflection_record in contextual_reflection_history:
                reflection = reflection_record.get('reflection')
                if reflection:
                    confidence_scores.append(reflection.confidence_score)
                    search_effectiveness_scores.append(reflection.search_effectiveness.get('effectiveness_score', 0))
                    result_quality_scores.append(reflection.result_quality_assessment.get('quality_score', 0))
                    knowledge_gaps_count.append(len(reflection.knowledge_gap_analysis.get('knowledge_gaps', [])))
            
            return {
                "contextual_reflection_count": len(contextual_reflection_history),
                "avg_confidence_score": np.mean(confidence_scores) if confidence_scores else 0.0,
                "max_confidence_score": np.max(confidence_scores) if confidence_scores else 0.0,
                "avg_search_effectiveness": np.mean(search_effectiveness_scores) if search_effectiveness_scores else 0.0,
                "avg_result_quality": np.mean(result_quality_scores) if result_quality_scores else 0.0,
                "total_knowledge_gaps_identified": sum(knowledge_gaps_count),
                "avg_knowledge_gaps_per_iteration": np.mean(knowledge_gaps_count) if knowledge_gaps_count else 0.0,
                "contextual_learning_efficiency": self._calculate_contextual_learning_efficiency(contextual_reflection_history)
            }
            
        except Exception as e:
            workflow_logger.log_error(f"上下文反思统计生成失败: {str(e)}")
            return {"error": str(e)}
    
    def _generate_contextual_optimization_stats(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """生成基于上下文反馈的优化统计信息"""
        try:
            contextual_optimization_history = state.get('contextual_optimization_history', [])
            
            if not contextual_optimization_history:
                return {"contextual_optimization_count": 0, "avg_context_richness": 0.0}
            
            # 统计上下文优化信息
            context_richness_scores = []
            confidence_scores = []
            
            for opt_record in contextual_optimization_history:
                context_richness_scores.append(opt_record.get('search_context_richness', 0))
                confidence_scores.append(opt_record.get('contextual_reflection_confidence', 0))
            
            return {
                "contextual_optimization_count": len(contextual_optimization_history),
                "avg_context_richness": np.mean(context_richness_scores) if context_richness_scores else 0.0,
                "avg_optimization_confidence": np.mean(confidence_scores) if confidence_scores else 0.0,
                "total_questions_contextually_optimized": sum(opt.get('optimized_count', 0) for opt in contextual_optimization_history),
                "contextual_optimization_efficiency": self._calculate_contextual_optimization_efficiency(contextual_optimization_history)
            }
            
        except Exception as e:
            workflow_logger.log_error(f"上下文优化统计生成失败: {str(e)}")
            return {"error": str(e)}
    
    def _calculate_contextual_learning_efficiency(self, reflection_history: List[Dict[str, Any]]) -> float:
        """计算上下文学习效率"""
        try:
            if len(reflection_history) < 2:
                return 0.0
            
            # 基于置信度提升计算学习效率
            confidence_scores = []
            for record in reflection_history:
                reflection = record.get('reflection')
                if reflection:
                    confidence_scores.append(reflection.confidence_score)
            
            if len(confidence_scores) < 2:
                return 0.0
            
            # 计算置信度提升趋势
            improvement = confidence_scores[-1] - confidence_scores[0]
            efficiency = improvement / len(confidence_scores)
            
            return max(0.0, min(1.0, efficiency + 0.5))
            
        except Exception as e:
            return 0.0
    
    def _calculate_contextual_optimization_efficiency(self, optimization_history: List[Dict[str, Any]]) -> float:
        """计算上下文优化效率"""
        try:
            if not optimization_history:
                return 0.0
            
            # 基于优化次数和置信度计算效率
            total_optimizations = len(optimization_history)
            avg_confidence = np.mean([opt.get('contextual_reflection_confidence', 0) for opt in optimization_history])
            
            efficiency = (total_optimizations * avg_confidence) / 10.0  # 标准化
            return max(0.0, min(1.0, efficiency))
            
        except Exception as e:
            return 0.0
    
    def _generate_optimization_stats(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """生成优化统计信息"""
        try:
            optimization_history = state.get('optimization_history', [])
            
            if not optimization_history:
                return {"optimization_count": 0, "avg_effectiveness": 0.0}
            
            # 统计优化信息
            effectiveness_scores = []
            optimization_types = {}
            
            for opt_record in optimization_history:
                effectiveness_scores.append(opt_record.get('effectiveness_score', 0))
                
                opt_types = opt_record.get('optimization_types', {})
                for opt_type, count in opt_types.items():
                    optimization_types[opt_type] = optimization_types.get(opt_type, 0) + count
            
            return {
                "optimization_count": len(optimization_history),
                "avg_effectiveness": np.mean(effectiveness_scores) if effectiveness_scores else 0.0,
                "max_effectiveness": np.max(effectiveness_scores) if effectiveness_scores else 0.0,
                "optimization_types": optimization_types,
                "total_questions_optimized": sum(opt.get('optimized_count', 0) for opt in optimization_history)
            }
            
        except Exception as e:
            workflow_logger.log_error(f"优化统计生成失败: {str(e)}")
            return {"error": str(e)}
    
    def _calculate_quality_trend(self, quality_scores: List[float]) -> str:
        """计算质量趋势"""
        try:
            if len(quality_scores) < 3:
                return "insufficient_data"
            
            # 使用线性回归计算趋势
            x = np.arange(len(quality_scores))
            y = np.array(quality_scores)
            slope = np.polyfit(x, y, 1)[0]
            
            if slope > 0.02:
                return "improving"
            elif slope < -0.02:
                return "declining"
            else:
                return "stable"
                
        except Exception as e:
            workflow_logger.log_error(f"质量趋势计算失败: {str(e)}")
            return "unknown"
    
    def _format_results_for_prompt(self, results: List[Dict[str, Any]]) -> str:
        """格式化结果用于提示词"""
        try:
            formatted = []
            for i, result in enumerate(results[:10], 1):  # 只取前10个结果
                question = result.get('question', '')
                summaries = result.get('summaries', [])
                summary = summaries[0] if summaries else "无总结"
                formatted.append(f"{i}. 问题：{question}\n   总结：{summary[:200]}...")
            
            return "\n".join(formatted)
            
        except Exception as e:
            workflow_logger.log_error(f"结果格式化失败: {str(e)}")
            return "格式化失败"
    
    def _parse_generated_questions(self, questions_text: str) -> List[Dict[str, Any]]:
        """解析生成的问题"""
        try:
            questions = []
            lines = questions_text.split('\n')
            
            for line in lines:
                line = line.strip()
                if line and (line.startswith(('1.', '2.', '3.', '4.', '5.')) or 
                           line.startswith(('1)', '2)', '3)', '4)', '5)'))):
                    # 提取问题文本
                    question_text = line.split('.', 1)[-1].split(')', 1)[-1].strip()
                    if question_text:
                        questions.append({
                            "question": question_text,
                            "direction": "deepening",
                            "iteration_generated": True
                        })
            
            return questions[:5]  # 限制5个问题
            
        except Exception as e:
            workflow_logger.log_error(f"问题解析失败: {str(e)}")
            return []
    
    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重结果"""
        try:
            seen_questions = set()
            unique_results = []
            
            for result in results:
                question = result.get('question', '')
                if question not in seen_questions:
                    seen_questions.add(question)
                    unique_results.append(result)
            
            return unique_results
            
        except Exception as e:
            workflow_logger.log_error(f"结果去重失败: {str(e)}")
            return results
