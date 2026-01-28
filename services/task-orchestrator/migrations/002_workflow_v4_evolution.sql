-- Migration: Workflow 4.0 Evolution
-- Adds workflow support to task_commands and introduces workflow tracking tables.

-- 1. Upgrade task_commands table
ALTER TABLE `alwaysup`.`task_commands`
ADD COLUMN `run_id` CHAR(36) DEFAULT NULL AFTER `id`,
ADD COLUMN `step_id` VARCHAR(100) DEFAULT NULL AFTER `run_id`,
ADD COLUMN `input_context` JSON DEFAULT NULL AFTER `params`,
ADD COLUMN `output_context` JSON DEFAULT NULL AFTER `result`;

CREATE INDEX idx_run_id ON `alwaysup`.`task_commands`(run_id);

-- 2. Create workflow_definitions table
CREATE TABLE IF NOT EXISTS `alwaysup`.`workflow_definitions` (
    `id` VARCHAR(100) PRIMARY KEY,
    `name` VARCHAR(255) NOT NULL,
    `version` INT DEFAULT 1,
    `definition` JSON NOT NULL COMMENT 'The DAG definition in JSON/YAML format',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) COMMENT='Workflow definition templates';

-- 3. Create workflow_runs table
CREATE TABLE IF NOT EXISTS `alwaysup`.`workflow_runs` (
    `run_id` CHAR(36) PRIMARY KEY,
    `workflow_id` VARCHAR(100) NOT NULL,
    `status` ENUM('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED') DEFAULT 'PENDING',
    `context` JSON DEFAULT NULL COMMENT 'Global runtime context',
    `start_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `end_time` DATETIME DEFAULT NULL,
    INDEX idx_workflow_status (workflow_id, status)
) COMMENT='Workflow instance execution tracking';
