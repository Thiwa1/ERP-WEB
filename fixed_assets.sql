CREATE TABLE IF NOT EXISTS `fixed_assets_register` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `asset_class` VARCHAR(100) NULL,
  `description` VARCHAR(255) NULL,
  `brand_name` VARCHAR(100) NULL,
  `quantity` INT DEFAULT 1,
  `serial_no` VARCHAR(100) NULL,
  `location` VARCHAR(100) NULL,
  `cost_value` DOUBLE DEFAULT 0,
  `purchasing_date` DATE NULL,
  `depreciable_life_months` INT DEFAULT 0,
  `asset_account_id` INT NULL,
  `expense_account_id` INT NULL,
  `accumulated_dep_account_id` INT NULL,
  `status` VARCHAR(20) DEFAULT 'Active',
  `supplier_id` BIGINT NULL,
  `write_off_amount` DOUBLE DEFAULT 0,
  `is_written_off` TINYINT DEFAULT 0,
  `jv_id` BIGINT NULL,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `fk_asset_acc_idx` (`asset_account_id` ASC),
  INDEX `fk_exp_acc_idx` (`expense_account_id` ASC),
  INDEX `fk_acc_dep_acc_idx` (`accumulated_dep_account_id` ASC),
  INDEX `fk_supplier_idx` (`supplier_id` ASC),
  CONSTRAINT `fk_asset_acc`
    FOREIGN KEY (`asset_account_id`)
    REFERENCES `new_account_table` (`id`)
    ON DELETE SET NULL
    ON UPDATE CASCADE,
  CONSTRAINT `fk_exp_acc`
    FOREIGN KEY (`expense_account_id`)
    REFERENCES `new_account_table` (`id`)
    ON DELETE SET NULL
    ON UPDATE CASCADE,
  CONSTRAINT `fk_acc_dep_acc`
    FOREIGN KEY (`accumulated_dep_account_id`)
    REFERENCES `new_account_table` (`id`)
    ON DELETE SET NULL
    ON UPDATE CASCADE,
  CONSTRAINT `fk_supplier_fa`
    FOREIGN KEY (`supplier_id`)
    REFERENCES `suppliers` (`sup_id`)
    ON DELETE SET NULL
    ON UPDATE CASCADE
) ENGINE = InnoDB DEFAULT CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `asset_depreciation_history` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `asset_id` INT NOT NULL,
  `depreciation_date` DATE NULL,
  `amount` DOUBLE DEFAULT 0,
  `jv_id` BIGINT NULL,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `fk_asset_hist_idx` (`asset_id` ASC),
  INDEX `fk_jv_hist_idx` (`jv_id` ASC),
  CONSTRAINT `fk_asset_hist`
    FOREIGN KEY (`asset_id`)
    REFERENCES `fixed_assets_register` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `fk_jv_hist`
    FOREIGN KEY (`jv_id`)
    REFERENCES `jv_numbers` (`jv_id`)
    ON DELETE SET NULL
    ON UPDATE CASCADE
) ENGINE = InnoDB DEFAULT CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci;
