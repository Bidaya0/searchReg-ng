# 反思机制设计文档

## 问题分析

当前实现的问题：
1. **缺少真正的反思**：只是简单生成新问题，没有对已有结果进行深度分析
2. **没有质量反馈循环**：无法基于搜索结果质量来优化问题策略
3. **缺少自我改进**：系统无法识别和修正自己的不足
4. **没有知识积累**：每轮迭代都是独立的，没有利用历史经验

## 反思机制设计

### 1. 反思节点 (Reflection Node)

#### 1.1 反思触发条件
- 每轮迭代完成后
- 质量分数变化超过阈值
- 时间策略调整时
- 用户手动触发

#### 1.2 反思内容
```python
class ReflectionAnalysis:
    """反思分析结果"""
    # 质量分析
    quality_assessment: Dict[str, Any]
    improvement_potential: float
    
    # 问题分析
    question_effectiveness: List[Dict[str, Any]]
    weak_areas: List[str]
    missing_angles: List[str]
    
    # 搜索分析
    search_coverage: Dict[str, Any]
    result_diversity: float
    information_gaps: List[str]
    
    # 改进建议
    optimization_directions: List[str]
    next_iteration_strategy: Dict[str, Any]
```

### 2. 问题优化器 (Question Optimizer)

#### 2.1 优化策略
- **问题深化**：基于反思结果将浅层问题转化为深层问题
- **角度补充**：识别缺失的研究角度并生成相应问题
- **质量提升**：改进低效问题的表达和聚焦度
- **关联强化**：增强问题之间的逻辑关联

#### 2.2 优化方法
```python
def optimize_questions(self, questions: List[Question], reflection: ReflectionAnalysis) -> List[Question]:
    """基于反思结果优化问题"""
    optimized_questions = []
    
    for question in questions:
        # 1. 评估问题质量
        quality_score = self._evaluate_question_quality(question, reflection)
        
        # 2. 根据质量决定优化策略
        if quality_score < 0.6:
            # 低质量问题：重新设计
            optimized = self._redesign_question(question, reflection)
        elif quality_score < 0.8:
            # 中等质量：深化优化
            optimized = self._deepen_question(question, reflection)
        else:
            # 高质量：微调优化
            optimized = self._refine_question(question, reflection)
        
        optimized_questions.append(optimized)
    
    # 3. 补充缺失角度的问题
    missing_questions = self._generate_missing_angle_questions(reflection)
    optimized_questions.extend(missing_questions)
    
    return optimized_questions
```

### 3. 知识积累机制

#### 3.1 经验库
```python
class ExperienceDatabase:
    """经验数据库"""
    question_patterns: Dict[str, List[Question]]  # 问题模式库
    search_strategies: Dict[str, Dict[str, Any]]  # 搜索策略库
    quality_indicators: Dict[str, float]  # 质量指标库
    improvement_history: List[Dict[str, Any]]  # 改进历史
```

#### 3.2 学习机制
- **模式识别**：识别高效的问题模式和搜索策略
- **经验提取**：从成功案例中提取可复用的经验
- **策略优化**：基于历史数据优化搜索和问题生成策略

### 4. 反思工作流

#### 4.1 完整反思流程
```python
def reflection_workflow(self, state: Dict[str, Any]) -> Dict[str, Any]:
    """反思工作流"""
    # 1. 收集反思数据
    reflection_data = self._collect_reflection_data(state)
    
    # 2. 执行反思分析
    reflection_analysis = self._perform_reflection_analysis(reflection_data)
    
    # 3. 生成改进建议
    improvement_suggestions = self._generate_improvement_suggestions(reflection_analysis)
    
    # 4. 更新经验库
    self._update_experience_database(reflection_analysis, improvement_suggestions)
    
    # 5. 优化下一轮策略
    next_strategy = self._optimize_next_iteration_strategy(reflection_analysis)
    
    return {
        "reflection_analysis": reflection_analysis,
        "improvement_suggestions": improvement_suggestions,
        "next_strategy": next_strategy
    }
```

## 实现计划

### 阶段1：基础反思节点
- 实现反思数据收集
- 实现基础质量分析
- 实现简单改进建议生成

### 阶段2：问题优化器
- 实现问题质量评估
- 实现问题优化算法
- 实现缺失角度识别

### 阶段3：知识积累
- 实现经验数据库
- 实现模式识别
- 实现策略优化

### 阶段4：集成测试
- 集成到时间策略中
- 端到端测试
- 性能优化

## 预期效果

通过反思机制，系统将能够：
1. **自我诊断**：识别当前搜索的不足和盲点
2. **持续改进**：每轮迭代都比上一轮更精准
3. **知识积累**：从每次搜索中学习并应用经验
4. **智能优化**：基于反思结果智能调整搜索策略
5. **质量提升**：在时间限制内最大化搜索质量
