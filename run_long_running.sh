#!/bin/bash

# 长时间运行工作流快速启动脚本

echo "长时间运行智能搜索系统"
echo "========================"

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3"
    exit 1
fi

# 检查依赖
echo "检查依赖..."
python3 -c "import psutil, numpy" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "安装依赖..."
    pip install psutil numpy
fi

# 显示使用说明
echo ""
echo "使用方法:"
echo "  $0 [主题] [选项]"
echo ""
echo "选项:"
echo "  --duration HOURS    设置运行时间（小时）"
echo "  --deadline TIME     设置截止时间 (YYYY-MM-DD HH:MM:SS)"
echo "  --strategy STRATEGY 设置时间策略 (hard/soft/adaptive)"
echo "  --time-iterations   启用时间迭代搜索模式"
echo ""
echo "示例:"
echo "  $0 \"人工智能在医疗领域的应用\" --duration 6"
echo "  $0 \"量子计算研究\" --deadline \"2024-01-01 18:00:00\""
echo "  $0 \"区块链技术\" --duration 2 --time-iterations --strategy adaptive"
echo ""

# 解析参数
TOPIC=""
DURATION=""
DEADLINE=""
STRATEGY="adaptive"
TIME_ITERATIONS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --duration)
            DURATION="$2"
            shift 2
            ;;
        --deadline)
            DEADLINE="$2"
            shift 2
            ;;
        --strategy)
            STRATEGY="$2"
            shift 2
            ;;
        --time-iterations)
            TIME_ITERATIONS="--time-iterations"
            shift
            ;;
        --help|-h)
            echo "长时间运行智能搜索系统"
            echo ""
            echo "使用方法: $0 [主题] [选项]"
            echo ""
            echo "选项:"
            echo "  --duration HOURS    设置运行时间（小时）"
            echo "  --deadline TIME     设置截止时间 (YYYY-MM-DD HH:MM:SS)"
            echo "  --strategy STRATEGY 设置时间策略 (hard/soft/adaptive)"
            echo "  --time-iterations   启用时间迭代搜索模式"
            echo "  --help, -h          显示此帮助信息"
            echo ""
            echo "示例:"
            echo "  $0 \"人工智能在医疗领域的应用\" --duration 6"
            echo "  $0 \"量子计算研究\" --deadline \"2024-01-01 18:00:00\""
            echo "  $0 \"区块链技术\" --duration 2 --time-iterations --strategy adaptive"
            exit 0
            ;;
        *)
            if [ -z "$TOPIC" ]; then
                TOPIC="$1"
            fi
            shift
            ;;
    esac
done

# 检查主题
if [ -z "$TOPIC" ]; then
    echo "错误: 请提供搜索主题"
    echo "使用 --help 查看帮助信息"
    exit 1
fi

# 构建命令
CMD="python3 main.py --long-running --topic \"$TOPIC\" --time-strategy $STRATEGY"

if [ -n "$DURATION" ]; then
    CMD="$CMD --duration $DURATION"
fi

if [ -n "$DEADLINE" ]; then
    CMD="$CMD --deadline \"$DEADLINE\""
fi

if [ -n "$TIME_ITERATIONS" ]; then
    CMD="$CMD $TIME_ITERATIONS"
fi

# 显示执行信息
echo "执行命令: $CMD"
echo ""
echo "主题: $TOPIC"
if [ -n "$DURATION" ]; then
    echo "运行时间: $DURATION 小时"
fi
if [ -n "$DEADLINE" ]; then
    echo "截止时间: $DEADLINE"
fi
echo "时间策略: $STRATEGY"
if [ -n "$TIME_ITERATIONS" ]; then
    echo "模式: 时间迭代搜索"
else
    echo "模式: 长时间运行"
fi
echo ""

# 确认执行
echo "是否开始执行？(y/n): "
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    echo "开始执行..."
    echo ""
    eval $CMD
else
    echo "已取消执行"
    exit 0
fi



