# 公共数据集多库验证报告

> 目标：在同一套「数据加载 → 特征处理 → 多模型训练 → 评估 → 校准 → SHAP 解释 → 报告输出」流水线上，对多个公开心血管数据集做复现性验证，不依赖任何本地私有数据。
> **注意：这是流水线复现性检查与基准参考，不是临床验证，也不代表中国基层人群的模型表现。**

## 数据集一览

| 数据集 | 样本 | 事件 | 阳性率 | 特征数 | 说明 |
|---|---:|---:|---:|---:|---|
| UCI Heart Disease (Cleveland) | 303 | 139 | 45.9% | 13 | 结局：冠脉造影 >50% 狭窄（num>0） |
| UCI Statlog (Heart) | 270 | 120 | 44.4% | 13 | 结局：2 = 患病（血管造影阳性） |
| UCI Heart Disease (Hungarian) | 294 | 106 | 36.0% | 13 | 结局：冠脉造影 >50% 狭窄（num>0）；缺失值较多 |
| ESL South African Heart Disease (SAheart) | 462 | 160 | 34.6% | 9 | 结局：chd（冠心病事件 0/1） |

## 图表

![图2 数据集概况](outputs/figures/fig2_public_overview.png)

*图2：各数据集样本量与阳性事件率*

![图3 模型 AUC 对比](outputs/figures/fig3_public_auc_compare.png)

*图3：4 个数据集 × 4 个模型的测试集 AUC*

![图4 ROC 曲线](outputs/figures/fig4_public_roc.png)

*图4：各数据集 ROC 曲线（Logistic 或最优模型）*

## 各数据集模型结果（80/20 分层随机划分）

### UCI Heart Disease (Cleveland)

| 模型 | AUC | Brier | 灵敏度 | 特异度 | F1 |
|---|---|---|---|---|---|
| logistic_regression | 0.950 | 0.096 | 0.93 | 0.82 | 0.87 |
| random_forest | 0.958 | 0.098 | 0.93 | 0.88 | 0.90 |
| xgboost | 0.952 | 0.086 | 0.96 | 0.82 | 0.89 |
| lightgbm | 0.956 | 0.094 | 0.93 | 0.79 | 0.85 |

5 折分层交叉验证 AUC：

| 模型 | AUC 均值 ± 标准差 |
|---|---|
| logistic_regression | 0.911 ± 0.018 |
| random_forest | 0.914 ± 0.020 |

SHAP 主要贡献因素：

1. ca（1.230）
2. thal（0.951）
3. cp（0.935）
4. sex（0.722）
5. age（0.681）
6. slope（0.531）
7. chol（0.481）
8. oldpeak（0.477）

### UCI Statlog (Heart)

| 模型 | AUC | Brier | 灵敏度 | 特异度 | F1 |
|---|---|---|---|---|---|
| logistic_regression | 0.896 | 0.131 | 0.92 | 0.80 | 0.85 |
| random_forest | 0.871 | 0.135 | 0.83 | 0.83 | 0.82 |
| xgboost | 0.863 | 0.162 | 0.83 | 0.77 | 0.78 |
| lightgbm | 0.858 | 0.167 | 0.79 | 0.77 | 0.76 |

5 折分层交叉验证 AUC：

| 模型 | AUC 均值 ± 标准差 |
|---|---|
| logistic_regression | 0.898 ± 0.043 |
| random_forest | 0.887 ± 0.039 |

SHAP 主要贡献因素：

1. ca（1.328）
2. cp（1.160）
3. thal（0.956）
4. sex（0.928）
5. chol（0.725）
6. age（0.554）
7. oldpeak（0.538）
8. slope（0.487）

### UCI Heart Disease (Hungarian)

| 模型 | AUC | Brier | 灵敏度 | 特异度 | F1 |
|---|---|---|---|---|---|
| logistic_regression | 0.882 | 0.110 | 0.90 | 0.89 | 0.86 |
| random_forest | 0.886 | 0.117 | 0.86 | 0.89 | 0.84 |
| xgboost | 0.841 | 0.145 | 0.71 | 0.87 | 0.73 |
| lightgbm | 0.832 | 0.171 | 0.62 | 0.79 | 0.62 |

5 折分层交叉验证 AUC：

| 模型 | AUC 均值 ± 标准差 |
|---|---|
| logistic_regression | 0.902 ± 0.015 |
| random_forest | 0.883 ± 0.031 |

SHAP 主要贡献因素：

1. cp（1.547）
2. oldpeak（1.278）
3. chol（0.980）
4. thalach（0.508）
5. age（0.494）
6. sex（0.451）
7. trestbps（0.342）
8. exang（0.310）

### ESL South African Heart Disease (SAheart)

| 模型 | AUC | Brier | 灵敏度 | 特异度 | F1 |
|---|---|---|---|---|---|
| logistic_regression | 0.821 | 0.197 | 0.88 | 0.57 | 0.65 |
| random_forest | 0.737 | 0.201 | 0.62 | 0.74 | 0.59 |
| xgboost | 0.715 | 0.235 | 0.69 | 0.67 | 0.59 |
| lightgbm | 0.700 | 0.250 | 0.69 | 0.66 | 0.59 |

5 折分层交叉验证 AUC：

| 模型 | AUC 均值 ± 标准差 |
|---|---|
| logistic_regression | 0.776 ± 0.066 |
| random_forest | 0.738 ± 0.047 |

SHAP 主要贡献因素：

1. age（0.897）
2. famhist（0.600）
3. tobacco（0.573）
4. ldl（0.468）
5. typea（0.400）
6. adiposity（0.299）
7. alcohol（0.286）
8. sbp（0.269）

## 跨数据集最优 AUC 对比

| 数据集 | 最优模型 | 测试集 AUC |
|---|---|---|
| UCI Heart Disease (Cleveland) | random_forest | 0.958 |
| UCI Statlog (Heart) | logistic_regression | 0.896 |
| UCI Heart Disease (Hungarian) | random_forest | 0.886 |
| ESL South African Heart Disease (SAheart) | logistic_regression | 0.821 |

## 结论

1. 4 个公开数据集上，Logistic / RF / XGBoost / LightGBM 的 AUC 整体处于 0.80-0.95 区间，说明本项目训练-评估-报告流水线可以跨数据集端到端复现并产出可解释结果。
2. 各数据集阳性率、人群与结局定义差异较大（如 SAheart 为南非人群、Hungarian 缺失较多），跨库 AUC 只用于流水线自洽性检查，不能横向比较「临床水平」。
3. 本地真实世界建模仍须以 `docs/stage_c_local_model_exploration.md` 为准，补齐对照人群、LIS 检验与外部验证。

## 复现命令

```bash
python scripts/stage_public_multi_validation.py --output-dir outputs/stage_public
```
