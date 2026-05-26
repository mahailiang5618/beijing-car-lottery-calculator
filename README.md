# 北京小客车家庭摇号积分计算器

北京市小客车指标家庭申请积分计算工具，支持多成员、多代际的家庭积分精确计算。

## 功能特性

- 支持主申请人、配偶、父母、子女等多成员积分计算
- 自动根据开始摇号时间计算累计未中签次数
- 区分 2021 年前后的阶梯积分规则（前: 每6次+1分，后: 每2次+1分）
- 支持 1/2/3 代际系数
- 支持 C5 驾照额外加分
- 输出详细的积分明细报告（Markdown / JSON 格式）

## 积分规则

### 个人积分 = 基础积分 + 阶梯积分

| 成员角色 | 基础积分 |
|---------|---------|
| 主申请人 | 2分 |
| 其他家庭成员 | 每人1分 |

### 阶梯积分

- 2021年前：每累计6次未中签 +1分
- 2021年起：每累计2次未中签 +1分
- 每年摇号2次（上半年、下半年各1次）

### 家庭总积分

- 含配偶：`[(主申请人积分 + 配偶积分) × 2 + 其他成员积分之和] × 代际数`
- 不含配偶：`[主申请人积分 + 其他成员积分之和] × 代际数`

### 代际系数

| 代际 | 系数 | 示例 |
|------|------|------|
| 1代 | ×1 | 仅夫妻 |
| 2代 | ×2 | 父母+子女 |
| 3代 | ×3 | 祖父母+父母+子女 |

## 使用方式

### 命令行调用

```bash
python3 scripts/calculate_family_score.py --json '<JSON数据>'
```

### JSON 输入格式

```json
{
  "primary_applicant": {
    "name": "张三",
    "start_year": 2014,
    "start_month": 1
  },
  "spouse": {
    "name": "李四",
    "start_year": 2016,
    "start_month": 1
  },
  "other_members": [
    {
      "name": "张父",
      "relationship": "父亲",
      "start_year": 2018,
      "start_month": 1
    }
  ],
  "generations": 2,
  "reference_date": "2026-05"
}
```

### 参数说明

| 字段 | 说明 | 必填 |
|------|------|------|
| `primary_applicant` | 主申请人信息 | 是 |
| `spouse` | 配偶信息，无配偶设为 `null` | 否 |
| `other_members` | 其他家庭成员数组 | 否 |
| `generations` | 代际数 (1/2/3) | 是 |
| `reference_date` | 计算截止日期 YYYY-MM，默认当前月 | 否 |
| `start_year` / `start_month` | 成员开始摇号的年月 | 是* |
| `unsuccessful_rounds` | 累计未中签次数（提供则忽略年月） | 否 |
| `has_c5` | 是否持有 C5 驾照（仅主申请人有效） | 否 |

### 输出选项

```bash
# Markdown 报告（默认）
python3 scripts/calculate_family_score.py --json '...'

# JSON 格式输出
python3 scripts/calculate_family_score.py --json '...' --output-json

# 从文件读取输入
python3 scripts/calculate_family_score.py --file input.json

# 指定计算截止日期
python3 scripts/calculate_family_score.py --json '...' --reference-date 2027-01
```

## 示例输出

```
# 北京小客车家庭摇号积分计算结果

## 计算基准日期：2026年上半年

## 家庭成员积分明细

| 成员 | 角色 | 基础积分 | 摇号次数 | 阶梯积分 | 个人总积分 |
|------|------|---------|---------|---------|-----------|
| 张三 | 主申请人 | 2 | 5次 | 3 | 5 |
| 李四 | 配偶 | 1 | 3次 | 2 | 3 |

## 家庭总积分：16 分
```

## 注意事项

- 摇号制度从 2014 年 1 月开始，之前的参与不计入
- 本工具仅计算家庭积分，不预测中签概率
- 如需查询个人摇号记录，请访问 [北京市小客车指标调控管理信息系统](https://xkczb.beijing.gov.cn)

## 环境要求

- Python 3.6+
- 无第三方依赖（仅使用标准库）

## 许可证

[MIT](LICENSE)
