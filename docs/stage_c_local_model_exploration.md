# Stage C 本地数据模型探索报告（草案）

> **状态：探索性原型，不是临床验证。** 本报告基于 246 名患者的本地冠心病业务库导出，
> 用于演示"研究宽表 → 特征派生 → 多模型训练 → 时间外验证 → SHAP 解释"的完整软件流程，
> 并给出当前数据下的诚实结论与缺口。

## 1. 数据与队列

- 来源：`冠心病2_xinneiyewu0001_20260803154226(3).xlsx`（30,471 行长表）→ 患者级宽表 `data/processed/research_table_local.csv`
- 队列：246 名患者（女 137 / 男 109），年龄 24-98 岁（中位 72）
- 提取规则见 `docs/research_table_extraction.md`
- **关键事实：246/246 患者带 CHD 信号 → 无对照人群，不能做"发病风险"预测，只能做冠心病患者内部分层探索**

## 2. 可用特征（7 个）

年龄、性别(male)、收缩压(sbp)、脉压(pulse_pressure)、糖尿病、高血压、心电图异常(ecg_abnormal)

**不可用**：BMI、血脂(TC/LDL/HDL)、空腹血糖、吸烟（本导出无结构化 LIS 检验列；吸烟提取后缺失率 28%）

## 3. 结局定义

| 结局 | 定义 | 阳性率 |
|---|---|---|
| outcome_hospitalized | 任一住院记录（住院利用/严重度代理） | 154/246 = 62.6% |
| outcome_severe_chd | 心梗/PCI/支架/CABG 记录（重症标记） | 19/246 = 7.7% |
| outcome_chd | 任意 CHD 信号 | 246/246 = 100%（不可建模） |

## 4. 模型结果（Logistic / RF / XGBoost / LightGBM，阈值 0.10）

### 4.1 outcome_hospitalized（随机划分）

| 模型 | AUC | Brier | 灵敏度 | 特异度 | F1 |
|---|---|---|---|---|---|

| logistic_regression | 0.851 | 0.162 | 1.00 | 0.21 | 0.81 | |
| random_forest | 0.854 | 0.166 | 1.00 | 0.00 | 0.77 | |
| xgboost | 0.885 | 0.139 | 1.00 | 0.29 | 0.82 | |
| lightgbm | 0.898 | 0.131 | 1.00 | 0.14 | 0.79 | |

### 4.2 outcome_hospitalized（时间外验证：按 index_date 前 209 / 后 37）

| 模型 | AUC | Brier | 灵敏度 | 特异度 | F1 |
|---|---|---|---|---|---|

| logistic_regression | 0.635 | 0.303 | 0.70 | 0.47 | 0.65 | |
| random_forest | 0.838 | 0.188 | 1.00 | 0.00 | 0.70 | |
| xgboost | 0.762 | 0.226 | 0.90 | 0.53 | 0.78 | |
| lightgbm | 0.788 | 0.223 | 0.90 | 0.53 | 0.78 | |

### 4.3 outcome_severe_chd（随机划分，探索性，阳性仅 19 例）

| 模型 | AUC | Brier | 灵敏度 | 特异度 | F1 |
|---|---|---|---|---|---|

| logistic_regression | 0.696 | 0.199 | 1.00 | 0.09 | 0.16 | |
| random_forest | 0.735 | 0.176 | 1.00 | 0.00 | 0.15 | |
| xgboost | 0.725 | 0.076 | 0.33 | 0.79 | 0.18 | |
| lightgbm | 0.608 | 0.083 | 0.33 | 0.82 | 0.20 | |

## 5. SHAP 主要贡献因素

### outcome_hospitalized（随机）

1. ecg_abnormal（1.006）
2. age（0.781）
3. sbp（0.750）
4. pulse_pressure（0.660）
5. diabetes（0.318）
6. hypertension（0.170）
7. male（0.145）

### outcome_hospitalized（时间外）

1. ecg_abnormal（1.554）
2. age（0.780）
3. pulse_pressure（0.771）
4. sbp（0.760）
5. hypertension（0.451）
6. diabetes（0.295）
7. male（0.161）

### outcome_severe_chd

1. age（0.929）
2. male（0.706）
3. sbp（0.508）
4. pulse_pressure（0.299）
5. ecg_abnormal（0.234）
6. diabetes（0.130）
7. hypertension（0.044）

## 6. 解读与结论

1. **住院结局在随机划分下 AUC 0.85-0.90，时间外验证降至 0.64-0.84**：随机划分高估了泛化能力，
   时间外划分更接近真实部署表现，是必须保留的评价方式。
2. **SHAP 一致指向**：心电图异常、年龄、收缩压/脉压、糖尿病是住院/重症的主要贡献因素，
   与冠心病风险常识一致（可作为临床专家复核的起点）。
3. **重症结局（7.7%）样本太少**，模型不稳定，只作探索。
4. **当前 AUC 偏高需谨慎**：样本小（n=246）、住院结局与"检测频率/就诊强度"存在相关性，
   可能包含信息偏差；正式研究需要外部验证队列。

## 7. 必须补齐后才能临床使用

- [ ] 伦理审查与数据使用授权
- [ ] 数据科按 `data/stage_b_research_table_schema.csv` 导出**含 LIS 检验、结构化血压/血脂/血糖、非 CHD 对照**的宽表
- [ ] 文本提取规则 ≥5% 人工抽样复核
- [ ] 样本量扩大（当前 246 人远不够）
- [ ] DCA、NRI/IDI、Cox 生存分析、校准曲线图
- [ ] 临床专家复核与上线审批

## 8. 复现命令

```bash
# 可行性审计
python scripts/stage_b_local_data_feasibility.py --workbook "/path/to.xlsx" --sheet 冠心病21 --output-dir outputs/stage_b_local_data_v3
# 构建研究宽表
python scripts/build_research_table.py --workbook "/path/to.xlsx" --sheet 冠心病21 --output data/processed/research_table_local.csv
# 训练（随机 / 时间外）
python -m chd_risk.cli train-tabular data/processed/research_table_local.csv --outcome-col outcome_hospitalized --output-report outputs/stage_c_hosp_random.json
python -m chd_risk.cli train-tabular data/processed/research_table_local.csv --outcome-col outcome_hospitalized --split temporal --output-report outputs/stage_c_hosp_temporal.json
```
