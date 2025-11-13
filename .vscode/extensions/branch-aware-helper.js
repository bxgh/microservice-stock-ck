const vscode = require('vscode');
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

/**
 * 分支感知的VSCode助手扩展
 * 自动检测当前Git分支并调整工作区配置
 */
class BranchAwareHelper {
    constructor() {
        this.currentBranch = '';
        this.workspaceFolder = '';
    }

    /**
     * 获取当前Git分支
     */
    getCurrentBranch() {
        try {
            const branch = execSync('git rev-parse --abbrev-ref HEAD', {
                encoding: 'utf8',
                cwd: this.workspaceFolder
            }).trim();
            return branch;
        } catch (error) {
            console.error('无法获取Git分支:', error);
            return 'unknown';
        }
    }

    /**
     * 检测分支类型并应用相应配置
     */
    applyBranchSpecificConfig(branch) {
        const config = vscode.workspace.getConfiguration();

        // 根据分支类型应用不同配置
        if (branch.includes('frontend')) {
            this.applyFrontendConfig(config);
        } else if (branch.includes('task-scheduler')) {
            this.applyTaskSchedulerConfig(config);
        } else if (branch.includes('cross')) {
            this.applyCrossDomainConfig(config);
        } else if (branch === 'main' || branch === 'master') {
            this.applyMainBranchConfig(config);
        }
    }

    /**
     * 应用前端开发配置
     */
    applyFrontendConfig(config) {
        // 更新文件排除规则
        config.update('files.exclude', {
            '**/services': true,
            '**/node_modules': true,
            '**/.git': false
        }, vscode.ConfigurationTarget.Workspace);

        // 更新工作台颜色
        config.update('workbench.colorCustomizations', {
            'titleBar.activeBackground': '#42b883',
            'statusBar.background': '#35495e'
        }, vscode.ConfigurationTarget.Workspace);
    }

    /**
     * 应用Task Scheduler配置
     */
    applyTaskSchedulerConfig(config) {
        config.update('files.exclude', {
            '**/apps/frontend-web': true,
            '**/services/data-collector': true,
            '**/services/data-processor': true,
            '**/services/data-storage': true,
            '**/services/notification': true,
            '**/services/monitor': true,
            '**/services/api-gateway': true,
            '**/services/stock-data': true,
            '**/.git': false
        }, vscode.ConfigurationTarget.Workspace);

        config.update('workbench.colorCustomizations', {
            'titleBar.activeBackground': '#e74c3c',
            'statusBar.background': '#c0392b'
        }, vscode.ConfigurationTarget.Workspace);
    }

    /**
     * 应用跨域开发配置
     */
    applyCrossDomainConfig(config) {
        config.update('files.exclude', {
            '**/node_modules': true,
            '**/__pycache__': true,
            '**/.venv': true,
            '**/venv': true,
            '**/.git': false
        }, vscode.ConfigurationTarget.Workspace);

        config.update('workbench.colorCustomizations', {
            'titleBar.activeBackground': '#9b59b6',
            'statusBar.background': '#8e44ad'
        }, vscode.ConfigurationTarget.Workspace);
    }

    /**
     * 应用主分支配置
     */
    applyMainBranchConfig(config) {
        config.update('files.exclude', {
            '**/node_modules': true,
            '**/__pycache__': true,
            '**/.venv': true,
            '**/venv': true,
            '**/.git': false
        }, vscode.ConfigurationTarget.Workspace);

        config.update('workbench.colorCustomizations', {
            'titleBar.activeBackground': '#2c3e50',
            'statusBar.background': '#34495e'
        }, vscode.ConfigurationTarget.Workspace);
    }

    /**
     * 监听分支变更
     */
    startBranchMonitoring() {
        setInterval(() => {
            const newBranch = this.getCurrentBranch();
            if (newBranch !== this.currentBranch) {
                this.currentBranch = newBranch;
                this.applyBranchSpecificConfig(newBranch);

                vscode.window.showInformationMessage(
                    `已切换到分支: ${newBranch}`,
                    'OK'
                );
            }
        }, 5000); // 每5秒检查一次分支状态
    }

    /**
     * 激活扩展
     */
    activate(context) {
        // 获取工作区文件夹
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (workspaceFolders && workspaceFolders.length > 0) {
            this.workspaceFolder = workspaceFolders[0].uri.fsPath;
        }

        // 初始化当前分支
        this.currentBranch = this.getCurrentBranch();
        this.applyBranchSpecificConfig(this.currentBranch);

        // 注册命令
        const switchBranchCommand = vscode.commands.registerCommand(
            'branchAware.switchBranch',
            async () => {
                const branch = await vscode.window.showInputBox({
                    prompt: '输入要切换的分支名称',
                    placeHolder: this.currentBranch
                });

                if (branch) {
                    try {
                        execSync(`git checkout ${branch}`, {
                            encoding: 'utf8',
                            cwd: this.workspaceFolder
                        });

                        this.currentBranch = branch;
                        this.applyBranchSpecificConfig(branch);

                        vscode.window.showInformationMessage(
                            `已切换到分支: ${branch}`
                        );
                    } catch (error) {
                        vscode.window.showErrorMessage(
                            `切换分支失败: ${error.message}`
                        );
                    }
                }
            }
        );

        const createWorkspaceCommand = vscode.commands.registerCommand(
            'branchAware.createWorkspace',
            async () => {
                const workspaceType = await vscode.window.showQuickPick([
                    { label: 'Frontend', value: 'frontend' },
                    { label: 'Backend', value: 'backend' },
                    { label: 'Task Scheduler', value: 'task-scheduler' },
                    { label: 'Cross Domain', value: 'cross-domain' }
                ], {
                    placeHolder: '选择工作区类型'
                });

                if (workspaceType) {
                    const currentBranch = this.getCurrentBranch();
                    const workspaceName = `${currentBranch}-${workspaceType.value}`;

                    vscode.window.showInformationMessage(
                        `创建工作区: ${workspaceName}`,
                        'OK'
                    );
                }
            }
        );

        // 开始监听分支变更
        this.startBranchMonitoring();

        context.subscriptions.push(switchBranchCommand, createWorkspaceCommand);
    }
}

module.exports = BranchAwareHelper;