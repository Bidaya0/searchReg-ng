"""
问题树状结构建模系统
负责将搜索结果构建为层次化的问题树状结构
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import json

from storage_models import SearchRoundRecord
from logger import workflow_logger


class NodeType(str, Enum):
    """节点类型枚举"""
    ROOT = "root"           # 根节点（主题）
    DIRECTION = "direction"  # 方向节点
    QUESTION = "question"    # 问题节点


class QuestionTreeNode:
    """问题树节点"""
    
    def __init__(self, node_id: str, node_type: NodeType, content: str, level: int):
        self.node_id = node_id
        self.node_type = node_type
        self.content = content
        self.level = level
        self.parent_id = None
        self.children_ids = []
        
        # 评分相关
        self.importance_score = 0.0
        self.relevance_score = 0.0
        self.quality_score = 0.0
        
        # 搜索相关
        self.search_results_count = 0
        self.search_success_rate = 0.0
        self.avg_processing_time = 0.0
        
        # 内容相关
        self.summary_length = 0
        self.key_points_count = 0
        self.content_completeness = 0.0
        
        # 元数据
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "content": self.content,
            "level": self.level,
            "parent_id": self.parent_id,
            "children_ids": self.children_ids,
            "importance_score": self.importance_score,
            "relevance_score": self.relevance_score,
            "quality_score": self.quality_score,
            "search_results_count": self.search_results_count,
            "search_success_rate": self.search_success_rate,
            "avg_processing_time": self.avg_processing_time,
            "summary_length": self.summary_length,
            "key_points_count": self.key_points_count,
            "content_completeness": self.content_completeness,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata
        }


class QuestionTree:
    """问题树结构"""
    
    def __init__(self, tree_id: str, root_node: QuestionTreeNode):
        self.tree_id = tree_id
        self.root_node = root_node
        self.nodes = {"root": root_node}
        
        # 结构信息
        self.directions = []
        self.total_questions = 0
        self.tree_depth = 3
        self.max_branching_factor = 0
        
        # 统计信息
        self.total_nodes = 1
        self.leaf_nodes_count = 0
        self.internal_nodes_count = 1
        
        # 质量指标
        self.avg_importance_score = 0.0
        self.avg_relevance_score = 0.0
        self.tree_coherence_score = 0.0
        
        # 时间信息
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def add_node(self, node: QuestionTreeNode):
        """添加节点到树中"""
        self.nodes[node.node_id] = node
        self.total_nodes += 1
        
        if node.node_type == NodeType.QUESTION:
            self.leaf_nodes_count += 1
        else:
            self.internal_nodes_count += 1
        
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "tree_id": self.tree_id,
            "root_node": self.root_node.to_dict(),
            "nodes": {node_id: node.to_dict() for node_id, node in self.nodes.items()},
            "directions": self.directions,
            "total_questions": self.total_questions,
            "tree_depth": self.tree_depth,
            "max_branching_factor": self.max_branching_factor,
            "total_nodes": self.total_nodes,
            "leaf_nodes_count": self.leaf_nodes_count,
            "internal_nodes_count": self.internal_nodes_count,
            "avg_importance_score": self.avg_importance_score,
            "avg_relevance_score": self.avg_relevance_score,
            "tree_coherence_score": self.tree_coherence_score,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class TreeBuilder:
    """树状结构构建器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
    def build_tree(self, search_results: List[SearchRoundRecord], topic: str) -> QuestionTree:
        """构建问题树状结构"""
        try:
            workflow_logger.log_info("开始构建问题树状结构")
            
            # 1. 创建根节点
            root_node = self._create_root_node(topic)
            
            # 2. 创建方向节点
            direction_nodes = self._create_direction_nodes(search_results)
            
            # 3. 创建问题节点
            question_nodes = self._create_question_nodes(search_results)
            
            # 4. 建立节点关系
            self._establish_relationships(root_node, direction_nodes, question_nodes)
            
            # 5. 计算节点评分
            self._calculate_node_scores(question_nodes, search_results)
            
            # 6. 构建树结构
            tree = self._assemble_tree(root_node, direction_nodes, question_nodes)
            
            # 7. 优化树结构
            optimized_tree = self._optimize_tree_structure(tree)
            
            workflow_logger.log_info(f"问题树状结构构建完成，共{optimized_tree.total_nodes}个节点")
            return optimized_tree
            
        except Exception as e:
            workflow_logger.log_error(f"构建问题树状结构失败: {str(e)}")
            raise
    
    def _create_root_node(self, topic: str) -> QuestionTreeNode:
        """创建根节点"""
        return QuestionTreeNode(
            node_id="root",
            node_type=NodeType.ROOT,
            content=topic,
            level=0
        )
    
    def _create_direction_nodes(self, search_results: List[SearchRoundRecord]) -> Dict[str, QuestionTreeNode]:
        """创建方向节点"""
        direction_nodes = {}
        directions = set(record.direction for record in search_results)
        
        for i, direction in enumerate(directions):
            node_id = f"direction_{i+1}"
            direction_nodes[direction] = QuestionTreeNode(
                node_id=node_id,
                node_type=NodeType.DIRECTION,
                content=direction,
                level=1
            )
        
        return direction_nodes
    
    def _create_question_nodes(self, search_results: List[SearchRoundRecord]) -> Dict[str, QuestionTreeNode]:
        """创建问题节点"""
        question_nodes = {}
        
        for i, record in enumerate(search_results):
            node_id = f"question_{i+1}"
            question_nodes[node_id] = QuestionTreeNode(
                node_id=node_id,
                node_type=NodeType.QUESTION,
                content=record.question,
                level=2
            )
            
            # 设置搜索相关属性
            question_nodes[node_id].search_results_count = len(record.search_results) if record.search_results else 0
            question_nodes[node_id].search_success_rate = 1.0 if record.success else 0.0
            question_nodes[node_id].avg_processing_time = record.processing_time
            question_nodes[node_id].summary_length = len(record.summary) if record.summary else 0
            question_nodes[node_id].key_points_count = len(record.key_points) if record.key_points else 0
            question_nodes[node_id].content_completeness = self._calculate_content_completeness(record)
        
        return question_nodes
    
    def _establish_relationships(self, root_node: QuestionTreeNode, 
                               direction_nodes: Dict[str, QuestionTreeNode],
                               question_nodes: Dict[str, QuestionTreeNode]) -> None:
        """建立节点关系"""
        # 建立根节点与方向节点的关系
        root_node.children_ids = list(direction_nodes.keys())
        
        # 建立方向节点与问题节点的关系
        direction_question_map = {}
        for node_id, question_node in question_nodes.items():
            # 根据搜索记录确定方向
            direction = self._get_direction_for_question(question_node.content, question_nodes, question_node)
            if direction not in direction_question_map:
                direction_question_map[direction] = []
            direction_question_map[direction].append(node_id)
        
        # 更新方向节点的子节点
        for direction, node in direction_nodes.items():
            if direction in direction_question_map:
                node.children_ids = direction_question_map[direction]
                # 更新问题节点的父节点
                for question_id in direction_question_map[direction]:
                    question_nodes[question_id].parent_id = node.node_id
    
    def _calculate_node_scores(self, question_nodes: Dict[str, QuestionTreeNode], 
                             search_results: List[SearchRoundRecord]) -> None:
        """计算节点评分"""
        for node_id, node in question_nodes.items():
            # 重要性评分：基于搜索结果数量和质量
            importance_score = self._calculate_importance_score(node)
            node.importance_score = importance_score
            
            # 相关性评分：基于内容相关性
            relevance_score = self._calculate_relevance_score(node)
            node.relevance_score = relevance_score
            
            # 质量评分：综合评分
            quality_score = self._calculate_quality_score(node)
            node.quality_score = quality_score
    
    def _calculate_importance_score(self, node: QuestionTreeNode) -> float:
        """计算重要性评分"""
        # 基于搜索结果数量（权重40%）
        results_score = min(node.search_results_count / 20.0, 1.0) * 0.4
        
        # 基于搜索成功率（权重30%）
        success_score = node.search_success_rate * 0.3
        
        # 基于内容完整性（权重30%）
        completeness_score = node.content_completeness * 0.3
        
        return results_score + success_score + completeness_score
    
    def _calculate_relevance_score(self, node: QuestionTreeNode) -> float:
        """计算相关性评分"""
        # 基于摘要长度（权重50%）
        summary_score = min(node.summary_length / 500.0, 1.0) * 0.5
        
        # 基于关键点数量（权重50%）
        key_points_score = min(node.key_points_count / 10.0, 1.0) * 0.5
        
        return summary_score + key_points_score
    
    def _calculate_quality_score(self, node: QuestionTreeNode) -> float:
        """计算质量评分"""
        return (node.importance_score + node.relevance_score) / 2.0
    
    def _calculate_content_completeness(self, record: SearchRoundRecord) -> float:
        """计算内容完整性"""
        completeness = 0.0
        
        # 有摘要（权重40%）
        if record.summary and len(record.summary.strip()) > 0:
            completeness += 0.4
        
        # 有关键点（权重30%）
        if record.key_points and len(record.key_points) > 0:
            completeness += 0.3
        
        # 有搜索结果（权重30%）
        if record.search_results and len(record.search_results) > 0:
            completeness += 0.3
        
        return completeness
    
    def _get_direction_for_question(self, question: str, question_nodes: Dict[str, QuestionTreeNode], current_node: QuestionTreeNode) -> str:
        """根据问题内容确定方向"""
        # 这里需要根据实际的搜索记录来确定方向
        # 暂时返回默认值，实际实现时需要从搜索记录中获取
        return "unknown"
    
    def _assemble_tree(self, root_node: QuestionTreeNode,
                      direction_nodes: Dict[str, QuestionTreeNode],
                      question_nodes: Dict[str, QuestionTreeNode]) -> QuestionTree:
        """组装树结构"""
        # 创建树
        tree = QuestionTree(f"tree_{datetime.now().strftime('%Y%m%d_%H%M%S')}", root_node)
        
        # 添加所有节点
        for node in direction_nodes.values():
            tree.add_node(node)
        for node in question_nodes.values():
            tree.add_node(node)
        
        # 设置方向列表
        tree.directions = list(direction_nodes.keys())
        tree.total_questions = len(question_nodes)
        
        # 计算平均评分
        if question_nodes:
            tree.avg_importance_score = sum(node.importance_score for node in question_nodes.values()) / len(question_nodes)
            tree.avg_relevance_score = sum(node.relevance_score for node in question_nodes.values()) / len(question_nodes)
        
        return tree
    
    def _optimize_tree_structure(self, tree: QuestionTree) -> QuestionTree:
        """优化树结构"""
        # 重新计算树结构指标
        tree.tree_coherence_score = self._calculate_tree_coherence(tree)
        
        # 更新树结构
        tree.updated_at = datetime.now()
        
        return tree
    
    def _calculate_tree_coherence(self, tree: QuestionTree) -> float:
        """计算树结构一致性评分"""
        # 基于节点评分的方差计算一致性
        question_nodes = [node for node in tree.nodes.values() if node.node_type == NodeType.QUESTION]
        if len(question_nodes) > 1:
            importance_scores = [node.importance_score for node in question_nodes]
            variance = sum((score - tree.avg_importance_score) ** 2 for score in importance_scores) / len(importance_scores)
            coherence = max(0, 1 - variance)
        else:
            coherence = 1.0
        
        return coherence


class NodeAnalyzer:
    """节点分析器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        workflow_logger = workflow_logger
    
    def analyze_node_relationships(self, tree: QuestionTree) -> List[Dict[str, Any]]:
        """分析节点关系"""
        relationships = []
        
        # 分析父子关系
        for node_id, node in tree.nodes.items():
            if node.parent_id:
                parent_relationship = {
                    "from_node_id": node.parent_id,
                    "to_node_id": node_id,
                    "relationship_type": "parent",
                    "strength": 1.0
                }
                relationships.append(parent_relationship)
            
            # 分析兄弟关系
            if node.children_ids:
                for child_id in node.children_ids:
                    child_relationship = {
                        "from_node_id": node_id,
                        "to_node_id": child_id,
                        "relationship_type": "child",
                        "strength": 1.0
                    }
                    relationships.append(child_relationship)
        
        # 分析相关关系（基于内容相似度）
        related_relationships = self._analyze_content_relationships(tree)
        relationships.extend(related_relationships)
        
        return relationships
    
    def _analyze_content_relationships(self, tree: QuestionTree) -> List[Dict[str, Any]]:
        """分析内容相关关系"""
        relationships = []
        question_nodes = [node for node in tree.nodes.values() if node.node_type == NodeType.QUESTION]
        
        for i, node1 in enumerate(question_nodes):
            for j, node2 in enumerate(question_nodes[i+1:], i+1):
                similarity = self._calculate_content_similarity(node1.content, node2.content)
                if similarity > 0.3:  # 相似度阈值
                    relationship = {
                        "from_node_id": node1.node_id,
                        "to_node_id": node2.node_id,
                        "relationship_type": "related",
                        "strength": similarity,
                        "similarity_score": similarity
                    }
                    relationships.append(relationship)
        
        return relationships
    
    def _calculate_content_similarity(self, content1: str, content2: str) -> float:
        """计算内容相似度"""
        # 简单的词汇重叠相似度计算
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def calculate_tree_metrics(self, tree: QuestionTree) -> Dict[str, Any]:
        """计算树结构指标"""
        # 平衡性评分
        balance_score = self._calculate_balance_score(tree)
        
        # 深度合理性评分
        depth_score = self._calculate_depth_score(tree)
        
        # 分支合理性评分
        branching_score = self._calculate_branching_score(tree)
        
        # 一致性评分
        coherence_score = tree.tree_coherence_score
        
        # 总体评分
        overall_score = (balance_score + depth_score + branching_score + coherence_score) / 4.0
        
        return {
            "tree_id": tree.tree_id,
            "balance_score": balance_score,
            "depth_score": depth_score,
            "branching_score": branching_score,
            "coherence_score": coherence_score,
            "overall_score": overall_score,
            "calculated_at": datetime.now().isoformat()
        }
    
    def _calculate_balance_score(self, tree: QuestionTree) -> float:
        """计算平衡性评分"""
        # 检查各方向的问题数量是否均衡
        direction_counts = {}
        for node in tree.nodes.values():
            if node.node_type == NodeType.QUESTION and node.parent_id:
                parent_node = tree.nodes.get(node.parent_id)
                if parent_node and parent_node.node_type == NodeType.DIRECTION:
                    direction = parent_node.content
                    direction_counts[direction] = direction_counts.get(direction, 0) + 1
        
        if not direction_counts:
            return 0.0
        
        counts = list(direction_counts.values())
        avg_count = sum(counts) / len(counts)
        variance = sum((count - avg_count) ** 2 for count in counts) / len(counts)
        
        # 平衡性评分：方差越小，平衡性越好
        balance_score = max(0, 1 - variance / (avg_count ** 2))
        return balance_score
    
    def _calculate_depth_score(self, tree: QuestionTree) -> float:
        """计算深度合理性评分"""
        # 理想的树深度应该是3层（根-方向-问题）
        ideal_depth = 3
        actual_depth = tree.tree_depth
        
        # 深度评分：越接近理想深度，评分越高
        depth_score = max(0, 1 - abs(actual_depth - ideal_depth) / ideal_depth)
        return depth_score
    
    def _calculate_branching_score(self, tree: QuestionTree) -> float:
        """计算分支合理性评分"""
        # 检查根节点的分支数（应该是方向数）
        root_children_count = len(tree.root_node.children_ids)
        expected_directions = len(tree.directions)
        
        if expected_directions == 0:
            return 0.0
        
        # 分支合理性评分
        branching_score = min(root_children_count / expected_directions, 1.0)
        return branching_score


class TreeOptimizer:
    """树状结构优化器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        workflow_logger = workflow_logger
    
    def optimize_tree(self, tree: QuestionTree) -> QuestionTree:
        """优化树状结构"""
        try:
            workflow_logger.log_info("开始优化树状结构")
            
            # 1. 节点重要性排序
            optimized_tree = self._sort_nodes_by_importance(tree)
            
            # 2. 优化节点关系
            optimized_tree = self._optimize_node_relationships(optimized_tree)
            
            # 3. 重新计算评分
            optimized_tree = self._recalculate_scores(optimized_tree)
            
            # 4. 更新树结构信息
            optimized_tree.updated_at = datetime.now()
            
            workflow_logger.log_info("树状结构优化完成")
            return optimized_tree
            
        except Exception as e:
            workflow_logger.log_error(f"优化树状结构失败: {str(e)}")
            return tree
    
    def _sort_nodes_by_importance(self, tree: QuestionTree) -> QuestionTree:
        """按重要性排序节点"""
        # 对问题节点按重要性评分排序
        question_nodes = [node for node in tree.nodes.values() if node.node_type == NodeType.QUESTION]
        sorted_question_nodes = sorted(question_nodes, key=lambda x: x.importance_score, reverse=True)
        
        # 更新节点ID以反映排序
        for i, node in enumerate(sorted_question_nodes):
            node.node_id = f"question_{i+1}"
            node.metadata["original_order"] = i + 1
            node.metadata["importance_rank"] = i + 1
        
        return tree
    
    def _optimize_node_relationships(self, tree: QuestionTree) -> QuestionTree:
        """优化节点关系"""
        # 重新计算节点间的关系强度
        for node_id, node in tree.nodes.items():
            if node.children_ids:
                # 按重要性排序子节点
                child_nodes = [tree.nodes[child_id] for child_id in node.children_ids]
                sorted_children = sorted(child_nodes, key=lambda x: x.importance_score, reverse=True)
                node.children_ids = [child.node_id for child in sorted_children]
        
        return tree
    
    def _recalculate_scores(self, tree: QuestionTree) -> QuestionTree:
        """重新计算评分"""
        # 重新计算平均评分
        question_nodes = [node for node in tree.nodes.values() if node.node_type == NodeType.QUESTION]
        
        if question_nodes:
            tree.avg_importance_score = sum(node.importance_score for node in question_nodes) / len(question_nodes)
            tree.avg_relevance_score = sum(node.relevance_score for node in question_nodes) / len(question_nodes)
        
        # 重新计算树结构一致性
        tree.tree_coherence_score = self._calculate_updated_coherence(tree)
        
        return tree
    
    def _calculate_updated_coherence(self, tree: QuestionTree) -> float:
        """计算更新后的一致性评分"""
        question_nodes = [node for node in tree.nodes.values() if node.node_type == NodeType.QUESTION]
        
        if len(question_nodes) <= 1:
            return 1.0
        
        importance_scores = [node.importance_score for node in question_nodes]
        avg_score = sum(importance_scores) / len(importance_scores)
        
        variance = sum((score - avg_score) ** 2 for score in importance_scores) / len(importance_scores)
        coherence = max(0, 1 - variance)
        
        return coherence


class TreeVisualizer:
    """树状结构可视化器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        workflow_logger = workflow_logger
    
    def generate_tree_diagram(self, tree: QuestionTree) -> str:
        """生成树状结构图表"""
        try:
            # 使用Mermaid语法生成树状图
            mermaid_code = self._generate_mermaid_tree(tree)
            return mermaid_code
            
        except Exception as e:
            workflow_logger.log_error(f"生成树状结构图表失败: {str(e)}")
            return ""
    
    def _generate_mermaid_tree(self, tree: QuestionTree) -> str:
        """生成Mermaid树状图代码"""
        lines = ["graph TD"]
        
        # 添加根节点
        root_id = "root"
        lines.append(f'    {root_id}["{tree.root_node.content}"]')
        
        # 添加方向节点
        for direction in tree.directions:
            direction_node = None
            for node in tree.nodes.values():
                if node.node_type == NodeType.DIRECTION and node.content == direction:
                    direction_node = node
                    break
            
            if direction_node:
                direction_id = direction_node.node_id
                lines.append(f'    {direction_id}["{direction}"]')
                lines.append(f'    {root_id} --> {direction_id}')
                
                # 添加问题节点
                for child_id in direction_node.children_ids:
                    child_node = tree.nodes.get(child_id)
                    if child_node and child_node.node_type == NodeType.QUESTION:
                        question_id = child_node.node_id
                        # 截断过长的内容
                        question_content = child_node.content[:50] + "..." if len(child_node.content) > 50 else child_node.content
                        lines.append(f'    {question_id}["{question_content}"]')
                        lines.append(f'    {direction_id} --> {question_id}')
        
        return "\n".join(lines)
    
    def generate_tree_summary(self, tree: QuestionTree) -> str:
        """生成树状结构摘要"""
        summary_lines = [
            f"# 问题树状结构摘要",
            f"",
            f"**主题**: {tree.root_node.content}",
            f"**树结构ID**: {tree.tree_id}",
            f"**创建时间**: {tree.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"",
            f"## 结构统计",
            f"- 总节点数: {tree.total_nodes}",
            f"- 方向数: {len(tree.directions)}",
            f"- 问题数: {tree.total_questions}",
            f"- 树深度: {tree.tree_depth}",
            f"",
            f"## 质量指标",
            f"- 平均重要性评分: {tree.avg_importance_score:.3f}",
            f"- 平均相关性评分: {tree.avg_relevance_score:.3f}",
            f"- 树结构一致性: {tree.tree_coherence_score:.3f}",
            f"",
            f"## 方向分析"
        ]
        
        # 按方向分析
        for direction in tree.directions:
            direction_node = None
            for node in tree.nodes.values():
                if node.node_type == NodeType.DIRECTION and node.content == direction:
                    direction_node = node
                    break
            
            if direction_node:
                question_count = len(direction_node.children_ids)
                summary_lines.extend([
                    f"",
                    f"### {direction}",
                    f"- 问题数量: {question_count}",
                    f"- 重要性评分: {direction_node.importance_score:.3f}",
                    f"- 相关性评分: {direction_node.relevance_score:.3f}"
                ])
        
        return "\n".join(summary_lines)


class QuestionTreeModeler:
    """问题树状建模器主类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        workflow_logger = workflow_logger
        
        # 初始化子组件
        self.tree_builder = TreeBuilder(config)
        self.node_analyzer = NodeAnalyzer(config)
        self.tree_optimizer = TreeOptimizer(config)
        self.tree_visualizer = TreeVisualizer(config)
    
    def build_question_tree(self, search_results: List[SearchRoundRecord], topic: str) -> Dict[str, Any]:
        """构建问题树状结构"""
        try:
            workflow_logger.log_info(f"开始构建问题树状结构，主题: {topic}")
            
            # 1. 构建基础树结构
            tree = self.tree_builder.build_tree(search_results, topic)
            
            # 2. 分析节点关系
            relationships = self.node_analyzer.analyze_node_relationships(tree)
            
            # 3. 计算树结构指标
            metrics = self.node_analyzer.calculate_tree_metrics(tree)
            
            # 4. 优化树结构
            optimized_tree = self.tree_optimizer.optimize_tree(tree)
            
            # 5. 生成可视化
            tree_diagram = self.tree_visualizer.generate_tree_diagram(optimized_tree)
            tree_summary = self.tree_visualizer.generate_tree_summary(optimized_tree)
            
            # 6. 构建返回结果
            result = {
                "status": "completed",
                "tree": optimized_tree.to_dict(),
                "relationships": relationships,
                "metrics": metrics,
                "visualization": {
                    "diagram": tree_diagram,
                    "summary": tree_summary
                },
                "created_at": datetime.now().isoformat()
            }
            
            workflow_logger.log_info(f"问题树状结构构建完成，共{optimized_tree.total_nodes}个节点")
            return result
            
        except Exception as e:
            error_result = {
                "status": "error",
                "error": str(e),
                "created_at": datetime.now().isoformat()
            }
            workflow_logger.log_error(f"构建问题树状结构失败: {str(e)}")
            return error_result
    
    def get_tree_statistics(self, tree: QuestionTree) -> Dict[str, Any]:
        """获取树结构统计信息"""
        return {
            "total_nodes": tree.total_nodes,
            "directions_count": len(tree.directions),
            "questions_count": tree.total_questions,
            "tree_depth": tree.tree_depth,
            "avg_importance_score": tree.avg_importance_score,
            "avg_relevance_score": tree.avg_relevance_score,
            "tree_coherence_score": tree.tree_coherence_score
        }
    
    def export_tree_data(self, tree: QuestionTree, format: str = "json") -> str:
        """导出树结构数据"""
        if format == "json":
            return json.dumps(tree.to_dict(), indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"不支持的导出格式: {format}")
