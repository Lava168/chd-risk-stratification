# Stage A：UCI 公开数据验证报告

> 目标：在公开基准数据集上证明「数据加载 → 特征处理 → 多模型训练 → 评估 → 校准 → SHAP 解释 → 报告输出」全流程可复现，不依赖任何本地私有数据。
> **注意：这是流水线复现性检查与基准参考，不是临床验证。**

## 数据集

- 来源：UCI Machine Learning Repository — Heart Disease（Cleveland），`processed.cleveland.data`
- 样本：303 人；结局为冠脉造影 >50% 狭窄（num>0）
- 阳性率：45.9%
- 特征（13 个）：年龄、性别、胸痛类型、静息血压、胆固醇、空腹血糖、静息心电图、最大心率、运动心绞痛、ST 段压低、ST 斜率、染色血管数、铊负荷试验

## 缺失值

| 特征 | 缺失数 |
|---|---:|
| age | 0 |
| sex | 0 |
| cp | 0 |
| trestbps | 0 |
| chol | 0 |
| fbs | 0 |
| restecg | 0 |
| thalach | 0 |
| exang | 0 |
| oldpeak | 0 |
| slope | 0 |
| ca | 4 |
| thal | 2 |

## 模型结果（80/20 分层随机划分）

| 模型 | AUC | Brier | 灵敏度 | 特异度 | F1 |
|---|---|---|---|---|---|
| logistic_regression | 0.950 | 0.096 | 0.93 | 0.82 | 0.87 |
| random_forest | 0.958 | 0.098 | 0.93 | 0.88 | 0.90 |
| xgboost | 0.952 | 0.086 | 0.96 | 0.82 | 0.89 |
| lightgbm | 0.956 | 0.094 | 0.93 | 0.79 | 0.85 |

## 5 折分层交叉验证 AUC

| 模型 | AUC 均值 ± 标准差 |
|---|---|
| logistic_regression | 0.911 ± 0.018 |
| random_forest | 0.914 ± 0.020 |

## SHAP 主要贡献因素

1. ca（1.230）
2. thal（0.951）
3. cp（0.935）
4. sex（0.722）
5. age（0.681）
6. slope（0.531）
7. chol（0.481）
8. oldpeak（0.477）
9. thalach（0.446）
10. trestbps（0.243）

## 结论

1. UCI Cleveland 上 Logistic / RF / XGBoost / LightGBM 的 AUC 均在 0.80-0.95 区间，说明本项目训练-评估-报告流水线可以端到端复现并产出可解释结果。
2. 该结果只证明**流程可用**，不能外推到中国基层人群；本地真实世界建模仍须以`docs/stage_c_local_model_exploration.md` 为准并补齐对照人群、LIS 检验与外部验证。

## 复现命令

```bash
python scripts/stage_a_uci_validation.py \
  --input data/public/uci_cleveland.data \
  --output-dir outputs/stage_a_uci
```
