from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskThresholds:
    """Probability thresholds for four-level risk stratification."""

    low_max: float = 0.05
    medium_max: float = 0.10
    high_max: float = 0.20


@dataclass(frozen=True)
class ManagementPlan:
    owner: str
    follow_up_days: int
    actions: tuple[str, ...]
    referral: str


DEFAULT_THRESHOLDS = RiskThresholds()

RISK_LABELS = {
    "low": "低危",
    "medium": "中危",
    "high": "高危",
    "very_high": "极高危",
}

MANAGEMENT_PLANS = {
    "low": ManagementPlan(
        owner="社区卫生服务中心/家庭医生团队",
        follow_up_days=365,
        actions=(
            "健康教育和生活方式指导",
            "年度风险复评",
            "维持血压、血脂、血糖常规监测",
        ),
        referral="无症状时不建议常规上转",
    ),
    "medium": ManagementPlan(
        owner="社区卫生服务中心/家庭医生团队",
        follow_up_days=180,
        actions=(
            "强化生活方式干预",
            "复查血压、血脂、血糖等核心指标",
            "评估用药依从性和随访连续性",
        ),
        referral="指标持续异常或症状提示时建议专科咨询",
    ),
    "high": ManagementPlan(
        owner="家庭医生团队+牵头医院专科协同",
        follow_up_days=90,
        actions=(
            "纳入重点随访",
            "开展用药规范性核查",
            "生成专科复核或上转建议",
        ),
        referral="建议心血管专科复核",
    ),
    "very_high": ManagementPlan(
        owner="牵头医院心血管专科+家庭医生团队",
        follow_up_days=30,
        actions=(
            "启动高优先级预警",
            "安排专科复核和双向转诊闭环",
            "记录转诊反馈和下一次管理时间",
        ),
        referral="疑似急性症状需按急诊流程处理",
    ),
}

