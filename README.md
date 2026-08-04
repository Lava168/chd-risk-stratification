# CHD Risk Stratification

面向基层医联体的冠心病风险智能评估与闭环管理原型仓库。

本仓库根据申报书中的建模设计整理为可运行的工程骨架，覆盖“多源数据治理、研究队列构建、三层模型比较、风险解释、四级分层管理、随访与转诊闭环”。仓库不包含真实患者数据，也不包含申报书原文或联系方式。

> 当前代码是研究和试点工具原型，不是已验证医疗器械或临床诊断系统。正式使用前必须完成伦理审查、数据脱敏、模型训练、内部/时间外验证、校准、临床专家复核和上线审批。

## 模型能做什么

这是一个冠心病风险智能评估原型，输入患者的基本信息、危险因素、检验检查与随访管理数据，即可完成「**风险评估 → 四级分层 → 随访/转诊建议**」的闭环流程：

**1. 个体风险评分**
输入一份患者档案（年龄、性别、血压血脂血糖、吸烟、共病、用药依从性、近一年就诊次数等 22 个特征），输出：

```json
{
  "probability": 0.79,        // 预测的心血管事件风险概率
  "tier": "high",             // 风险等级
  "tier_label": "高危",
  "management_plan": {
    "follow_up_days": 90,     // 建议随访周期（天）
    "referral": "建议心血管专科复核",
    "actions": ["纳入重点随访", "开展用药规范性核查", "生成专科复核或上转建议"]
  }
}
```

**2. 四级风险分层**
按风险概率分为低危 / 中危 / 高危 / 极高危，每档绑定管理主体、随访周期和干预重点（见 [四级分层闭环路径](docs/closed_loop_pathway.md)）：

| 等级 | 概率 | 管理主体 | 建议随访 |
|---|---:|---|---:|
| 低危 | <5% | 社区卫生服务中心/家庭医生团队 | 365 天 |
| 中危 | 5%–10% | 社区卫生服务中心/家庭医生团队 | 180 天 |
| 高危 | 10%–20% | 家庭医生团队+牵头医院专科协同 | 90 天 |
| 极高危 | ≥20% | 牵头医院心血管专科+家庭医生团队 | 30 天 |

**3. 多模型训练与对比**
对 Logistic 回归、随机森林、XGBoost、LightGBM 一键训练，自动做交叉验证 + 时间外验证，输出 AUC、Brier、灵敏度、特异度、F1、校准分箱等指标，并保存最优模型供评分链路复用（当前部署模型 XGBoost：CV AUC 0.871，时间外 AUC 0.835）。

**4. 风险解释**
输出 SHAP 特征重要性排序，说明该患者的主要风险来源，便于医生向患者解释和制定干预方案。

**5. 批量评估与数据质量**
支持 CSV 批量评分（自动附上风险概率、等级、随访天数和转诊建议），并生成数据完整性与范围违例质量报告。

**6. 多种使用方式**

- 命令行 CLI：`score-one` 单例评分 / `score-csv` 批量评分 / `train-tabular` 训练 / `quality-report` 质量报告
- HTTP API：`/assess` 评估接口、`/health` 健康检查（`uvicorn chd_risk.api:app`）
- 网页 UI：`/ui` 医生端界面，含患者列表、新建评估、分层结果展示

**7. 本地数据可行性审计（Stage B）**
对导出的 HIS/EMR 工作簿做摸底审计，只输出聚合统计与字段缺口清单，不导出患者级数据，用于判断"现有数据能否建模"。

> ⚠️ 边界：以上是**研究和试点工具原型**，不是已验证医疗器械或临床诊断系统。合成数据仅用于流程冒烟测试；正式使用前必须完成伦理审查、真实队列训练、内部/时间外验证、校准、临床专家复核和上线审批。

## 建模思路

申报书中的核心方案被整理为以下工程模块：

- 数据来源：HIS、LIS、PACS、EMR、公卫随访、家庭医生签约、慢病管理、用药、转诊和住院结局。
- 队列构建：成年人群，优先覆盖 35 岁及以上和合并冠心病危险因素人群；按个体划分训练/验证/测试集，推荐 70/15/15 或时间外验证。
- 特征体系：人口学与传统危险因素、慢病共病、检验检查、诊疗行为、药物治疗、随访管理六类变量。
- 三层模型：China-PAR 基准层、Logistic/Cox 可解释统计层、随机森林/XGBoost/LightGBM 机器学习层。
- 评价指标：AUC、灵敏度、特异度、F1、校准曲线、Brier score、H-L 检验、DCA、NRI/IDI。
- 临床转化：输出风险等级、主要风险来源和管理建议，并绑定低危/中危/高危/极高危四级路径。

## 仓库结构

```text
.
├── src/chd_risk/          # 风险评估、特征、分层、CLI、API 原型
├── docs/                  # 建模设计、变量字典、闭环路径、数据安全说明
├── examples/              # 单例 JSON 示例
├── data/                  # 合成数据说明，真实数据不要提交
├── tests/                 # stdlib unittest 测试
├── models/                # 本地模型产物目录，不提交真实模型
└── outputs/               # 本地输出目录
```

## 界面预览（UI Preview）

面向医生的 Web 界面：患者队列 → 风险评估（概率 + 四级分层）→ 风险原因 → 管理建议（复评/转诊）。

<p align="center">
  <img src="docs/screenshots/ui_main.png" alt="Doctor UI - Risk Assessment Report" width="900" style="max-width:100%; height:auto; border:1px solid #e5e7eb; border-radius:10px;">
</p>
<p align="center">
  <img src="docs/screenshots/ui_assess_form.png" alt="Doctor UI - New Assessment Form" width="900" style="max-width:100%; height:auto; border:1px solid #e5e7eb; border-radius:10px;">
</p>

启动方式：

```bash
cd /Users/mac/Documents/冠心病风险评估模型/chd-risk-stratification
source .venv/bin/activate
python -m uvicorn chd_risk.api:app --host 127.0.0.1 --port 8765
# 浏览器打开 http://127.0.0.1:8765/
```

> 评估由 `models/trained_model_bundle.joblib` 中的训练模型完成（无模型时回退权重原型）。

## 桌面版（Desktop App）

打包为独立 macOS 应用（pywebview 原生窗口 + 内置 FastAPI 后端 + 训练模型），无需安装 Python 依赖。

**macOS（Apple Silicon）下载**：`release/CHD-Risk-Stratification-macOS-arm64.zip`（解压后把
`CHD Risk Stratification.app` 拖入"应用程序"即可；首次打开如提示"已损坏/无法验证"，在
"系统设置 → 隐私与安全性"中允许，或运行 `xattr -cr /Applications/CHD Risk Stratification.app`）。

**从源码重新构建**：

```bash
./scripts/build_desktop.sh
# 产物：dist/CHD Risk Stratification.app 与 release/CHD-Risk-Stratification-macOS-arm64.zip
```

**Windows 版**：PyInstaller 无法跨平台编译，Windows 的 `.exe` 需在 Windows 上构建，两种方式任选：

1. **GitHub Actions 自动构建（推荐）**：推送到仓库后，在 **Actions → Build Desktop App → Run workflow**（或打 `v*` 标签），
   会自动在 Windows / macOS 云服务器上构建并产出可下载的构建产物（artifacts）。
2. **本机构建**：在 Windows 机器上运行：

   ```bat
   scripts\build_desktop.bat
   ```

   > 说明：模型 bundle（`models/trained_model_bundle.joblib`）因包含本地去标识化数据产物而**不进入 Git**，
   > 因此 CI/他人构建的应用默认使用"权重原型"演示模式；如需打包训练模型，请把该文件放回 `models/` 再构建。

> macOS 安装包：`release/CHD-Risk-Stratification-macOS-arm64.zip`（Apple Silicon）。

## 快速运行

```bash
PYTHONPATH=src python3 -m chd_risk.cli score-one examples/sample_patient.json
PYTHONPATH=src python3 -m chd_risk.cli generate-synthetic --n 200 --output data/synthetic_patients.csv
PYTHONPATH=src python3 -m chd_risk.cli quality-report data/synthetic_patients.csv --output outputs/quality_report.json
PYTHONPATH=src python3 -m chd_risk.cli train-tabular data/synthetic_patients.csv --output-report outputs/training_report.json
PYTHONPATH=src python3 -m chd_risk.cli score-csv data/synthetic_patients.csv --output outputs/scored_patients.csv
PYTHONPATH=src python3 -m unittest discover -s tests
```

安装为本地包：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
chd-risk score-one examples/sample_patient.json
```

完整机器学习环境：

```bash
pip install -e ".[ml,api,dev]"
```

启动 API 原型：

```bash
uvicorn chd_risk.api:app --reload
```

Stage B 本地真实世界数据可行性审计（不会导出患者级数据，只输出聚合统计）：

```bash
python3 scripts/stage_b_local_data_feasibility.py --workbook /path/to/local.xlsx --sheet 冠心病21 --output-dir outputs/stage_b_local_data
```

装好完整机器学习依赖后，可以训练 tabular baseline：

```bash
chd-risk train-tabular data/deidentified_research_table.csv --outcome-col outcome_chd
# 时间外验证式划分（按 index_date 排序，前 85% 训练 / 后 15% 测试）：
chd-risk train-tabular data/deidentified_research_table.csv --outcome-col outcome_chd --split temporal --date-col index_date

# 训练后评分自动使用保存的模型 bundle（无模型时回退权重原型）：
chd-risk score-one examples/sample_patient.json
chd-risk score-csv data/processed/research_table_local.csv --output outputs/scored_patients.csv
```

## Stage B 本地数据可行性评估

Stage B 用于检查本地 HIS/EMR/检查报告导出是否具备建模条件。该模块只输出聚合统计和缺口清单，不提交原始 Excel、患者级记录、病历文本或个体预测结果。

```bash
python3 scripts/stage_b_local_data_feasibility.py \
  --workbook "/path/to/local_real_world_extract.xlsx" \
  --sheet "冠心病21" \
  --output-dir outputs/stage_b_local_data
```

本次本地 Excel 摸底结论见 `docs/stage_b_local_data_feasibility.md`。数据科导出一人一行研究宽表时，可参考 `data/stage_b_research_table_schema.csv`。

## 公共数据集验证

在 4 个公开心血管数据集上跑同一套「训练 → 评估 → 校准 → SHAP → 报告」流水线，验证流程可复现（不依赖任何本地私有数据）。完整报告见 `docs/stage_public_datasets_validation.md`。

| 数据集 | 样本 | 阳性率 | 最优模型 | 测试集 AUC |
|---|---:|---:|---|---:|
| UCI Heart Disease (Cleveland) | 303 | 45.9% | random_forest | 0.958 |
| UCI Statlog (Heart) | 270 | 44.4% | logistic_regression | 0.896 |
| UCI Heart Disease (Hungarian) | 294 | 36.0% | random_forest | 0.886 |
| ESL South African Heart Disease (SAheart) | 462 | 34.6% | logistic_regression | 0.821 |

图表：

![fig7 数据集概况](outputs/figures/fig7_public_overview.png)

*图7：各数据集样本量与阳性事件率*

![fig8 模型 AUC 对比](outputs/figures/fig8_public_auc_compare.png)

*图8：4 个数据集 × 4 个模型的测试集 AUC*

![fig9 ROC 曲线](outputs/figures/fig9_public_roc.png)

*图9：各数据集 ROC 曲线（Logistic 或最优模型）*

数据文件位于 `data/public/`（`uci_cleveland.data`、`statlog_heart.dat`、`hungarian_heart.data`、`SAheart.data`）。复现命令：

```bash
python scripts/stage_public_multi_validation.py --output-dir outputs/stage_public
```

> ⚠️ 这些是流水线复现性/基准检查，不是临床验证；各库人群、特征与结局定义不同，跨库 AUC 不能横向比较「临床水平」。

## 当前实现边界

- `src/chd_risk/china_par.py` 是 China-PAR 适配边界。因申报书没有提供正式系数，仓库只放了开发用 proxy，不能当成真实 China-PAR 公式。
- `src/chd_risk/model.py` 是透明权重模型，用于跑通软件流程。真实项目应替换为本地队列训练和校准后的模型。
- `data/` 只允许放合成数据或脱敏后的结构模板，真实患者级数据不应提交到 GitHub。
- `scripts/stage_b_local_data_feasibility.py` 只是本地真实世界数据可行性审计，不会训练模型，也不代表临床验证完成。

## 重要提醒：合成数据仅用于流程冒烟测试

`data/synthetic_patients.csv` 的 `outcome_chd` 标签由原型模型自身概率生成，属于循环论证，
**在其上训练得到的任何 AUC/指标都没有评估意义**。它只用于验证训练-评估-报告软件流程。
真实建模必须使用去标识化的本地研究宽表（见 `data/stage_b_research_table_schema.csv`）。

## 当前进度（2026-08-04 更新）

已完成：

- ✅ **评分链路已接入训练模型**：`train-tabular` 默认把最优模型保存为 `models/trained_model_bundle.joblib`；`score-one`/`score-csv`/API 自动加载它（无模型时回退到权重原型）。分层阈值按训练人群分数分位数标定（相对风险带），缺失值不进入"风险原因"。
- ✅ Stage A：UCI 公开数据验证（`scripts/stage_a_uci_validation.py`，Cleveland 303 例，4 模型 CV AUC ~0.91，证明训练-评估-报告流水线可复现），见 `docs/stage_a_uci_validation.md`。
- ✅ 公共数据集多库验证（`scripts/stage_public_multi_validation.py`，Cleveland 303 / Statlog 270 / Hungarian 294 / SAheart 462 例，4 模型 AUC 0.82-0.96），见 `docs/stage_public_datasets_validation.md`。
- ✅ 本地 Stage B 可行性审计（`scripts/stage_b_local_data_feasibility.py`，输出聚合统计，不导出患者级数据）。
- ✅ 本地研究宽表构建 ETL（`scripts/build_research_table.py` → `data/processed/research_table_local.csv`，提取规则见 `docs/research_table_extraction.md`）。
- ✅ 多模型训练与验证报告（Logistic / 随机森林 / XGBoost / LightGBM，随机划分 + 时间外划分，AUC/Brier/灵敏度/特异度/F1/校准分箱/SHAP 解释），见 `docs/stage_c_local_model_exploration.md`。

尚待完成：

- 数据科按 `data/stage_b_research_table_schema.csv` 导出含 LIS 检验、结构化血压/血脂/血糖、**非 CHD 对照**的更大规模研究宽表。
- 文本提取规则 ≥5% 人工抽样复核。
- DCA、NRI/IDI、Cox 生存分析、校准曲线图。
- 将评分结果嵌入随访、复评、转诊和反馈闭环表单。
- 伦理审查、临床专家复核与上线审批。


## 模型报告图

以下图为本地研究宽表（246 例，结局：是否住院）训练 XGBoost 部署模型时生成的报告图，
用于展示队列、模型表现与风险解释流程。仅用于展示，不代表临床验证结论。

![图1 队列基线特征](outputs/figures/fig1_cohort.png)

*图1：队列人群基线特征（性别、年龄等分布）*

![图2 时间外验证 ROC](outputs/figures/fig2_roc_temporal.png)

*图2：时间外验证 ROC 曲线（XGBoost 时间外 AUC 0.835）*

![图3 校准曲线](outputs/figures/fig3_calibration.png)

*图3：校准曲线（预测概率 vs 实际发生率）*

![图4 SHAP 特征重要性](outputs/figures/fig4_shap.png)

*图4：SHAP 特征重要性排序（主要风险来源解释）*

![图5 风险分层](outputs/figures/fig5_tiers.png)

*图5：四级风险分层（分数分位数档位：低危/中危/高危/极高危）*

![图6 多模型对比](outputs/figures/fig6_model_compare.png)

*图6：多模型性能对比（CV AUC 与时间外 AUC）*

> 说明：这些图基于本地示例研究宽表生成，仅用于验证训练-评估-报告软件流程；
> 正式结论需以去标识化、经伦理审查和临床复核的真实队列为准。
