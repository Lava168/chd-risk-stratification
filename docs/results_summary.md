# 冠心病风险评估模型——项目结果汇总

> 本文件整合仓库内全部模型验证结果，标注**最优/部署模型**。数据截至 2026-08-04。
> 所有结果为研究/试点原型输出，**不是临床验证结论**；正式使用前须完成伦理审查、真实队列验证、校准与上线审批。

## 1. 最优部署模型（生产用）

| 项目 | 内容 |
|---|---|
| 模型 | **XGBoost**（最终部署，模型包 `models/trained_model_bundle.joblib`） |
| 训练数据 | 宝山本地 246 例去标识化研究宽表（22 个特征，结局：是否住院，154/246=62.6%） |
| 评估方式 | 10×5 重复分层交叉验证（均值＋95%CI）＋ 时间外验证（前209训练/后37验证） |
| CV AUC | **0.871**（95%CI：0.780～0.960） |
| Brier | 0.143 |
| 时间外 AUC | **0.835** |
| 分层切点 | 训练分数分位数 0.29 / 0.58 / 0.87（低危/中危/高危相对风险带） |
| 分层验证（部署评分路径） | 低危62 / 中危61 / 高危61 / 极高危62 人；实际住院率 9.7% → 54.1% → 88.5% → **98.4%**（单调一致） |
| SHAP 主要因素 | 心电图异常、年龄、收缩压/脉压、肌酐（肾功能）、糖尿病 |

## 2. 本地研究队列全部模型对比（246 例）

### 2.1 Stage C3 诚实评估（10×5 重复分层 CV + 时间外）

| 模型 | CV AUC | 95% CI | Brier | 时间外 AUC |
|---|---|---|---|---|
| logistic_regression | 0.859 | 0.753-0.963 | 0.153 | 0.747 |
| random_forest | 0.868 | 0.755-0.957 | 0.153 | 0.859 |
| **xgboost（部署）** | **0.871** | **0.780-0.960** | **0.143** | **0.835** |
| lightgbm | 0.862 | 0.768-0.962 | 0.148 | 0.843 |
| 集成(XGB+LGBM+RF) | 0.871 | 0.771-0.959 | 0.146 | — |

### 2.2 Stage C2（随机/时间外划分，带最优阈值）

| 划分 | logistic | random_forest | xgboost | lightgbm |
|---|---|---:|---:|---:|
| 随机划分 AUC | 0.876 | 0.904 | **0.953** | 0.932 |
| 时间外 AUC | 0.703 | **0.838** | 0.791 | 0.776 |

### 2.3 严重结局（19 例，7.7%，事件过少仅供参考）

| 模型 | AUC |
|---|---:|
| random_forest | 0.735 |
| xgboost | 0.725 |
| logistic_regression | 0.696 |
| lightgbm | 0.608 |

## 3. 公共数据集验证（4 个，流水线复现性检查）

| 数据集 | 样本 | 阳性率 | 最优模型 | 测试集 AUC | 5折CV AUC(Logistic) |
|---|---:|---:|---|---:|---:|
| UCI Cleveland | 303 | 45.9% | random_forest | **0.958** | 0.911 |
| UCI Statlog | 270 | 44.4% | logistic_regression | 0.896 | 0.898 |
| UCI Hungarian | 294 | 36.0% | random_forest | 0.886 | 0.902 |
| ESL SAheart | 462 | 34.6% | logistic_regression | 0.821 | 0.776 |

> 每个数据集均输出 4 模型完整指标（AUC/Brier/灵敏度/特异度/F1）、5折CV、校准与 SHAP，见 `docs/stage_public_datasets_validation.md` 与图7-9。
> ⚠️ 公开数据为诊断性病例集（阳性率 34%～46%），**仅用于验证流水线可复现，不混入本地训练、不能作为社区风险结论**。

## 4. 辅助测试

- **合成数据**（`training_report_synthetic.json`，200例）：标签由原型模型自生成，属循环论证，**无评估意义**，仅验证软件流程可跑通。
- **单元测试**：21 个全部通过（数据质量、评分、分层、训练管线）。

## 5. 相关图表

| 图 | 内容 | 位置 |
|---|---|---|
| 图1 | 本地队列人群基线特征 | `outputs/figures/fig1_cohort.png` |
| 图2 | 公共数据集概况（样本量/事件率） | `outputs/figures/fig2_public_overview.png` |
| 图3 | 公共数据集模型 AUC 对比 | `outputs/figures/fig3_public_auc_compare.png` |
| 图4 | 公共数据集 ROC 曲线 | `outputs/figures/fig4_public_roc.png` |
| 图5 | 本地模型时间外验证 ROC | `outputs/figures/fig5_roc_temporal.png` |
| 图6 | 校准曲线 | `outputs/figures/fig6_calibration.png` |
| 图7 | SHAP 特征重要性 | `outputs/figures/fig7_shap.png` |
| 图8 | 多模型性能对比 | `outputs/figures/fig8_model_compare.png` |
| 图9 | 四级风险分层 | `outputs/figures/fig9_tiers.png` |

## 6. 结论

1. **最优可部署模型为本地 XGBoost**：CV AUC 0.871（95%CI 0.780～0.960）、时间外 AUC 0.835，分层排序可靠（9.7%→98.4%）。
2. 4 个公开数据集证明训练-评估-报告流水线可跨库复现（测试 AUC 0.82～0.96）。
3. **边界**：本地队列仅 246 例且事件率 62.6%，只能作相对风险带；公开数据为诊断基准，不能外推中国社区人群。下一步需 ≥2 万人本地队列、非 CHD 对照、DCA/NRI/IDI/Cox 与外部验证。

## 7. 复现命令

```bash
# 本地最优模型（部署）
python scripts/stage_c3_strongest_model.py --input data/processed/research_table_local.csv \
  --outcome-col outcome_hospitalized --output-dir outputs/stage_c3 --save-model models/trained_model_bundle.joblib

# 公共数据集验证
python scripts/stage_public_multi_validation.py --output-dir outputs/stage_public

# 图表
python scripts/make_figures.py && python scripts/make_public_figures.py
```
