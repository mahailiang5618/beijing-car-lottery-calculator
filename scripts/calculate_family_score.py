#!/usr/bin/env python3
"""北京小客车家庭摇号积分计算器"""

import argparse
import json
import math
import sys
from datetime import datetime

PRIMARY_BASE_SCORE = 2
OTHER_BASE_SCORE = 1

# 2021年前：每6次未中签 +1 阶梯积分
PRE_2021_ROUNDS_PER_TIER = 6
# 2021年起：每2次未中签 +1 阶梯积分
POST_2021_ROUNDS_PER_TIER = 2
# 2021年起每年2次摇号（上半年1次，下半年1次）
ROUNDS_PER_YEAR_POST_2021 = 2


def count_half_years(start_year, start_half, ref_year, ref_half):
    """计算从起始半年到参考半年的摇号次数（含首尾，每半年1次）"""
    count = (ref_year - start_year) * 2 + (ref_half - start_half) + 1
    return max(0, count)


def get_half(month):
    """月份转半年：1-6月=1（上半年），7-12月=2（下半年）"""
    return 1 if month <= 6 else 2


def calculate_tier_score(pre_2021_rounds, post_2021_rounds, has_c5=False):
    """
    计算阶梯积分
    - 2020年12月31日以前：每6次 +1分
    - 2021年1月1日以后：每2次 +1分
    - C5驾照（残疾人专用）：主申请人额外 +1
    """
    pre_tier = math.ceil(pre_2021_rounds / PRE_2021_ROUNDS_PER_TIER) if pre_2021_rounds > 0 else 0
    post_tier = math.ceil(post_2021_rounds / POST_2021_ROUNDS_PER_TIER) if post_2021_rounds > 0 else 0
    tier = pre_tier + post_tier
    if has_c5:
        tier += 1
    return tier, pre_tier, post_tier


def calculate_family_total(primary_score, spouse_score, other_scores, generations, has_spouse):
    if has_spouse:
        couple_part = (primary_score + spouse_score) * 2
        others_part = sum(other_scores)
        subtotal = couple_part + others_part
    else:
        subtotal = primary_score + sum(other_scores)
    total = subtotal * generations
    return total, subtotal


def parse_reference_date(ref_str):
    if ref_str:
        parts = ref_str.split("-")
        return int(parts[0]), int(parts[1])
    now = datetime.now()
    return now.year, now.month


def process_member(member, is_primary, ref_year, ref_month):
    """处理单个成员的积分计算"""
    base = PRIMARY_BASE_SCORE if is_primary else OTHER_BASE_SCORE
    has_c5 = member.get("has_c5", False) and is_primary

    # 如果直接提供了摇号次数
    if member.get("pre_2021_rounds") is not None or member.get("post_2021_rounds") is not None:
        pre_rounds = member.get("pre_2021_rounds", 0)
        post_rounds = member.get("post_2021_rounds", 0)
    elif member.get("unsuccessful_rounds") is not None:
        # 兼容旧格式：全部算作 post_2021（适用于2021年后才开始摇号的人）
        start_year = member.get("start_year", 2021)
        if start_year >= 2021:
            pre_rounds = 0
            post_rounds = member["unsuccessful_rounds"]
        else:
            # 如果2021年前开始但只给了总次数，无法精确拆分，全算pre
            pre_rounds = member["unsuccessful_rounds"]
            post_rounds = 0
    else:
        # 根据开始年月自动计算
        start_year = member.get("start_year", 2021)
        start_month = member.get("start_month", 1)
        pre_rounds, post_rounds = count_rounds_by_date(start_year, start_month, ref_year, ref_month)

    total_rounds = pre_rounds + post_rounds
    tier, pre_tier, post_tier = calculate_tier_score(pre_rounds, post_rounds, has_c5)
    total = base + tier

    return {
        "name": member.get("name", "未命名"),
        "relationship": member.get("relationship", "主申请人" if is_primary else "成员"),
        "base": base,
        "pre_2021_rounds": pre_rounds,
        "post_2021_rounds": post_rounds,
        "total_rounds": total_rounds,
        "tier": tier,
        "pre_tier": pre_tier,
        "post_tier": post_tier,
        "has_c5": has_c5,
        "total": total,
    }


def count_rounds_by_date(start_year, start_month, ref_year, ref_month):
    """
    根据开始年月和参考日期计算2021年前后的摇号次数。
    ref_year/ref_month 代表家庭摇号开始时间，个人摇号截止到其前一期。
    """
    pre_rounds = 0
    post_rounds = 0

    # 计算参考日期的前一个半年（个人摇号的最后一期）
    ref_half = get_half(ref_month)
    if ref_half == 1:
        last_individual_year = ref_year - 1
        last_individual_half = 2
    else:
        last_individual_year = ref_year
        last_individual_half = 1

    if start_year >= 2021:
        start_half = get_half(start_month)
        if (start_year, start_half) > (last_individual_year, last_individual_half):
            post_rounds = 0
        else:
            post_rounds = count_half_years(start_year, start_half, last_individual_year, last_individual_half)
    elif last_individual_year <= 2020:
        pre_rounds = 0
    else:
        # 跨越2021年，2021年前部分需用户提供 pre_2021_rounds
        pre_rounds = 0
        post_rounds = count_half_years(2021, 1, last_individual_year, last_individual_half)

    return pre_rounds, post_rounds


def format_report(results, generations, has_spouse, family_total, subtotal, ref_year, ref_month):
    lines = []
    lines.append("# 北京小客车家庭摇号积分计算结果")
    lines.append("")
    lines.append(f"## 计算基准日期：{ref_year}年{'上' if ref_month <= 6 else '下'}半年")
    lines.append("")
    lines.append("## 家庭成员积分明细")
    lines.append("")
    lines.append("| 成员 | 角色 | 基础积分 | 摇号次数（2021前+2021后） | 阶梯积分 | 个人总积分 |")
    lines.append("|------|------|---------|------------------------|---------|-----------|")

    for r in results:
        rounds_str = f"{r['pre_2021_rounds']}+{r['post_2021_rounds']}={r['total_rounds']}次"
        if r['pre_2021_rounds'] == 0:
            rounds_str = f"{r['post_2021_rounds']}次"
        c5_mark = " (含C5+1)" if r.get("has_c5") else ""
        lines.append(f"| {r['name']} | {r['relationship']} | {r['base']} | {rounds_str} | {r['tier']}{c5_mark} | {r['total']} |")

    lines.append("")
    lines.append("## 阶梯积分计算说明")
    lines.append("")
    for r in results:
        detail_parts = []
        if r['pre_2021_rounds'] > 0:
            detail_parts.append(f"2021前{r['pre_2021_rounds']}次→{r['pre_tier']}分")
        if r['post_2021_rounds'] > 0:
            detail_parts.append(f"2021后{r['post_2021_rounds']}次→{r['post_tier']}分")
        if r.get("has_c5"):
            detail_parts.append("C5驾照→+1分")
        detail = " + ".join(detail_parts) if detail_parts else "0分"
        lines.append(f"- **{r['name']}**：{detail}，阶梯积分 = {r['tier']}")

    lines.append("")
    lines.append("## 家庭总积分计算")
    lines.append("")

    primary = results[0]
    if has_spouse:
        spouse = results[1]
        others = results[2:]
        lines.append(f"- 公式：**[(主申请人积分 + 配偶积分) × 2 + 其他成员积分之和] × 代际数**")
        lines.append(f"- 代际数：{generations}代（系数 ×{generations}）")
        lines.append(f"- 计算步骤：")
        couple_sum = primary["total"] + spouse["total"]
        couple_part = couple_sum * 2
        others_sum = sum(r["total"] for r in others)
        lines.append(f"  - 主申请人积分 + 配偶积分 = {primary['total']} + {spouse['total']} = {couple_sum}")
        lines.append(f"  - ({couple_sum}) × 2 = {couple_part}")
        if others:
            others_detail = " + ".join(str(r["total"]) for r in others)
            if len(others) > 1:
                lines.append(f"  - 其他成员积分之和 = {others_detail} = {others_sum}")
            else:
                lines.append(f"  - 其他成员积分之和 = {others_sum}")
            lines.append(f"  - {couple_part} + {others_sum} = {subtotal}")
        else:
            lines.append(f"  - 无其他成员，小计 = {couple_part}")
        lines.append(f"  - {subtotal} × {generations}（代际系数）= **{family_total}**")
    else:
        others = results[1:]
        lines.append(f"- 公式：**[主申请人积分 + 其他成员积分之和] × 代际数**")
        lines.append(f"- 代际数：{generations}代（系数 ×{generations}）")
        lines.append(f"- 计算步骤：")
        others_sum = sum(r["total"] for r in others)
        if others:
            others_detail = " + ".join(str(r["total"]) for r in others)
            lines.append(f"  - 主申请人积分 = {primary['total']}")
            if len(others) > 1:
                lines.append(f"  - 其他成员积分之和 = {others_detail} = {others_sum}")
            else:
                lines.append(f"  - 其他成员积分之和 = {others_sum}")
            lines.append(f"  - {primary['total']} + {others_sum} = {subtotal}")
        else:
            lines.append(f"  - 主申请人积分 = {primary['total']}，小计 = {subtotal}")
        lines.append(f"  - {subtotal} × {generations}（代际系数）= **{family_total}**")

    lines.append("")
    lines.append(f"## 家庭总积分：{family_total} 分")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*阶梯积分规则：2021年前每6次+1分，2021年起每2次+1分。每年摇号2次（上/下半年各1次）。*")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="北京小客车家庭摇号积分计算器")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--json", dest="json_str", help="JSON字符串输入")
    group.add_argument("--file", dest="json_file", help="JSON文件路径输入")
    parser.add_argument("--reference-date", help="计算截止日期 YYYY-MM（默认当前月）")
    parser.add_argument("--output-json", action="store_true", help="以JSON格式输出结果")

    args = parser.parse_args()

    if args.json_str:
        try:
            data = json.loads(args.json_str)
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失败: {e}", file=sys.stderr)
            return 1
    else:
        try:
            with open(args.json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            print(f"❌ 读取文件失败: {e}", file=sys.stderr)
            return 1

    ref_date = args.reference_date or data.get("reference_date")
    ref_year, ref_month = parse_reference_date(ref_date)

    if "primary_applicant" not in data or not data["primary_applicant"]:
        print("❌ 缺少主申请人信息", file=sys.stderr)
        return 1

    generations = data.get("generations", 1)
    if generations not in (1, 2, 3):
        print("❌ 代际数必须为 1、2 或 3", file=sys.stderr)
        return 1

    results = []

    primary_result = process_member(data["primary_applicant"], True, ref_year, ref_month)
    primary_result["relationship"] = "主申请人"
    results.append(primary_result)

    has_spouse = data.get("spouse") is not None and data.get("spouse") != {}
    if has_spouse:
        spouse_result = process_member(data["spouse"], False, ref_year, ref_month)
        spouse_result["relationship"] = data["spouse"].get("relationship", "配偶")
        results.append(spouse_result)

    other_members = data.get("other_members", [])
    for member in other_members:
        member_result = process_member(member, False, ref_year, ref_month)
        if "relationship" in member:
            member_result["relationship"] = member["relationship"]
        results.append(member_result)

    primary_score = results[0]["total"]
    spouse_score = results[1]["total"] if has_spouse else 0
    other_scores = [r["total"] for r in results[(2 if has_spouse else 1):]]

    family_total, subtotal = calculate_family_total(primary_score, spouse_score, other_scores, generations, has_spouse)

    if args.output_json:
        output = {
            "reference_date": f"{ref_year}-{ref_month:02d}",
            "generations": generations,
            "has_spouse": has_spouse,
            "members": results,
            "subtotal": subtotal,
            "family_total": family_total,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        report = format_report(results, generations, has_spouse, family_total, subtotal, ref_year, ref_month)
        print(report)

    return 0


if __name__ == "__main__":
    sys.exit(main())
