#!/bin/bash

# 多微服务并行开发 Pre-commit Hook
# 自动检测变更域并执行相应的验证

echo "🔍 检测变更域..."

# 获取变更文件
changed_files=$(git diff --cached --name-only)
frontend_files=""
backend_files=""
infra_files=""

# 分类变更文件
for file in $changed_files; do
    if [[ $file == apps/* ]]; then
        frontend_files="$frontend_files $file"
    elif [[ $file == services/* || $file == packages/* ]]; then
        backend_files="$backend_files $file"
    elif [[ $file == infrastructure/* || $file == scripts/* || $file == .github/* ]]; then
        infra_files="$infra_files $file"
    fi
done

# 执行域特定检查
if [[ -n "$frontend_files" ]]; then
    echo "📱 检测前端变更，执行前端检查..."
    # 前端语法检查
    for file in $frontend_files; do
        if [[ $file == *.vue || $file == *.ts || $file == *.js ]]; then
            # 简单语法检查
            node -c "$file" 2>/dev/null || echo "⚠️  语法错误: $file"
        fi
    done
fi

if [[ -n "$backend_files" ]]; then
    echo "🔧 检测后端变更，执行后端检查..."
    # Python语法检查
    for file in $backend_files; do
        if [[ $file == *.py ]]; then
            python -m py_compile "$file" 2>/dev/null || echo "⚠️  Python语法错误: $file"
        fi
    done
fi

if [[ -n "$infra_files" ]]; then
    echo "🏗️ 检测基础设施变更，执行配置检查..."
    # YAML语法检查
    for file in $infra_files; do
        if [[ $file == *.yml || $file == *.yaml ]]; then
            python -c "import yaml; yaml.safe_load(open('$file'))" 2>/dev/null || echo "⚠️  YAML语法错误: $file"
        fi
    done
fi

echo "✅ Pre-commit检查完成"
exit 0