# 变量字典草案

| 字段名 | 中文含义 | 类型 | 单位/取值 | 来源 | 说明 |
|---|---|---:|---|---|---|
| patient_id | 去标识化患者ID | string | 哈希或研究编号 | 主索引 | 禁止使用姓名、身份证、手机号 |
| reference_date | 评估日期 | date | YYYY-MM-DD | 研究库 | 风险评估基准日期 |
| age | 年龄 | integer | 岁 | 主索引/EMR | 核心变量 |
| sex | 性别 | string | 男/女 | 主索引/EMR | 核心变量 |
| bmi | 体重指数 | float | kg/m2 | 体检/公卫 | 可由身高体重计算 |
| sbp | 收缩压 | float | mmHg | 体检/随访 | 核心变量 |
| dbp | 舒张压 | float | mmHg | 体检/随访 | 用于脉压计算 |
| total_chol | 总胆固醇 | float | mmol/L | LIS | China-PAR 基线候选变量 |
| ldl_c | 低密度脂蛋白胆固醇 | float | mmol/L | LIS | 风险解释重点 |
| hdl_c | 高密度脂蛋白胆固醇 | float | mmol/L | LIS | 可生成 HDL-C 偏低特征 |
| fasting_glucose | 空腹血糖 | float | mmol/L | LIS | 糖代谢风险 |
| smoker | 吸烟 | boolean | 是/否 | 公卫/问卷 | 传统危险因素 |
| diabetes | 糖尿病 | boolean | 是/否 | 诊断/随访 | 核心变量 |
| hypertension | 高血压 | boolean | 是/否 | 诊断/随访 | 核心变量 |
| ckd | 慢性肾病 | boolean | 是/否 | 诊断/LIS | 共病变量 |
| atrial_fibrillation | 房颤 | boolean | 是/否 | 诊断/心电图 | 共病变量 |
| family_history_chd | 冠心病家族史 | boolean | 是/否 | 问卷/EMR | 传统危险因素 |
| chest_pain_visit_last_year | 近1年胸痛就诊记录 | boolean | 是/否 | HIS/EMR | 诊疗行为特征 |
| ecg_abnormal | 心电图异常 | boolean | 是/否 | PACS/检查报告 | 检查特征 |
| carotid_ultrasound_abnormal | 颈动脉超声异常 | boolean | 是/否 | PACS/检查报告 | 检查特征 |
| antihypertensive_use | 降压药使用 | boolean | 是/否 | 用药记录 | 治疗特征 |
| lipid_lowering_use | 降脂药使用 | boolean | 是/否 | 用药记录 | 治疗特征 |
| antiplatelet_use | 抗血小板药使用 | boolean | 是/否 | 用药记录 | 治疗特征 |
| statin_adherence_gap | 他汀用药不连续 | boolean | 是/否 | 用药记录 | 管理过程特征 |
| follow_up_interrupted | 随访中断 | boolean | 是/否 | 公卫随访 | 管理过程特征 |
| outpatient_visits_12m | 近12个月门诊频次 | integer | 次 | HIS | 诊疗行为特征 |
| emergency_visits_12m | 近12个月急诊频次 | integer | 次 | HIS | 诊疗行为特征 |
| sbp_trend_6m | 6个月收缩压趋势 | float | mmHg/月或总变化 | 随访/LIS | 动态特征，需统一口径 |
| ldl_trend_6m | 6个月LDL-C趋势 | float | mmol/L/月或总变化 | LIS | 动态特征，需统一口径 |
| medication_adherence_rate | 用药依从率 | float | 0-1 | 用药/随访 | 管理过程特征 |
| china_par_score | China-PAR基准风险 | float | 0-1 或 0-100 | 外部计算/适配器 | 推荐由正式公式或再校准模型提供 |
| outcome_chd | 冠心病结局 | boolean | 是/否 | 诊断/住院/专科复核 | 建模标签 |
| outcome_date | 结局日期 | date | YYYY-MM-DD | 诊断/住院 | 生存分析或时间外验证使用 |

## 数据质量目标

- 患者主索引匹配率：力争 95% 以上。
- 年龄、性别完整率：力争 98% 以上。
- 血压、血脂、糖尿病状态等核心建模变量可用率：力争 80% 以上。
- 不少于 5% 样本进行人工抽样复核。
- 所有单位换算、异常值规则、重复记录合并逻辑应保留审计记录。

