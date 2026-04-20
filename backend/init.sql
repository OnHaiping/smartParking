-- 智能停车场数据库初始化SQL文件
-- 使用MySQL数据库

-- 创建数据库
CREATE DATABASE IF NOT EXISTS `smartpark` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 使用数据库
USE `smartpark`;

-- 删除已存在的表（如果存在）
DROP TABLE IF EXISTS `billing_records`;
DROP TABLE IF EXISTS `parking_records`;
DROP TABLE IF EXISTS `parking_spots`;

-- 车位表
CREATE TABLE `parking_spots` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
  `spot_id` VARCHAR(10) NOT NULL UNIQUE COMMENT '车位编号',
  `occupied` TINYINT(1) DEFAULT 0 COMMENT '是否被占用',
  `plate` VARCHAR(20) DEFAULT NULL COMMENT '车牌号',
  `entry_time` DATETIME DEFAULT NULL COMMENT '进入时间',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='车位表';

-- 停车记录表
CREATE TABLE `parking_records` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
  `record_id` VARCHAR(50) NOT NULL UNIQUE COMMENT '记录ID',
  `plate_number` VARCHAR(20) NOT NULL COMMENT '车牌号',
  `spot_id` VARCHAR(10) NOT NULL COMMENT '车位编号',
  `entry_time` DATETIME NOT NULL COMMENT '入场时间',
  `exit_time` DATETIME DEFAULT NULL COMMENT '出场时间',
  `duration` VARCHAR(50) DEFAULT NULL COMMENT '停车时长',
  `amount` DECIMAL(10, 2) DEFAULT 0.00 COMMENT '应付金额',
  `paid` TINYINT(1) DEFAULT 0 COMMENT '是否已支付',
  `paid_time` DATETIME DEFAULT NULL COMMENT '支付时间',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='停车记录表';

-- 计费记录表
CREATE TABLE `billing_records` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
  `order_id` VARCHAR(50) NOT NULL UNIQUE COMMENT '订单ID',
  `plate_number` VARCHAR(20) NOT NULL COMMENT '车牌号',
  `amount` DECIMAL(10, 2) NOT NULL COMMENT '支付金额',
  `payment_method` VARCHAR(20) DEFAULT 'wechat' COMMENT '支付方式',
  `paid` TINYINT(1) DEFAULT 1 COMMENT '是否已支付',
  `paid_time` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '支付时间',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='计费记录表';

-- 初始化数据
INSERT INTO `parking_spots` (`spot_id`, `occupied`, `created_at`, `updated_at`) VALUES
('A', 0, NOW(), NOW()),
('B', 0, NOW(), NOW());

-- 创建索引（注意：MySQL的CREATE INDEX不支持IF NOT EXISTS）
CREATE INDEX `idx_parking_records_plate_number` ON `parking_records`(`plate_number`);
CREATE INDEX `idx_parking_records_entry_time` ON `parking_records`(`entry_time`);
