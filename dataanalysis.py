import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
import matplotlib
import os

# ============ 基础设置 ============
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
matplotlib.rcParams['axes.unicode_minus'] = False

# ============ 第一步：连接数据库 ============
print("正在读取德国储能数据...")
db_path = r"C:\Users\hlhua\.open-MaStR\data\sqlite\open-mastr.db"
conn = sqlite3.connect(db_path)
query = "SELECT * FROM storage_units"
df = pd.read_sql(query, conn)
conn.close()
print(f"原始数据量：{len(df)} 条")

# ============ 第二步：数据清洗 ============
df['Registrierungsdatum'] = pd.to_datetime(df['Registrierungsdatum'], errors='coerce')
df = df[
    (df['Registrierungsdatum'] >= '2018-01-01') &
    (df['Registrierungsdatum'] <= '2026-12-31')
    ].copy()
df = df.dropna(subset=['Registrierungsdatum'])
print(f"清洗后数据量：{len(df)} 条")

# ============ 第三步：按容量分类 ============
capacity_col = None
if 'NutzbareSpeicherkapazitaet' in df.columns:
    capacity_col = 'NutzbareSpeicherkapazitaet'
else:
    print("未在数据中找到 'NutzbareSpeicherkapazitaet' 字段，请检查数据库！")
    print(f"当前字段包含: {df.columns.tolist()}")
    exit()

print(f"成功找到容量字段：{capacity_col} (单位: kWh)")

df = df.dropna(subset=[capacity_col])
df[capacity_col] = pd.to_numeric(df[capacity_col], errors='coerce')
df = df.dropna(subset=[capacity_col])

df['类型'] = '未知'
df.loc[df[capacity_col] <= 30, '类型'] = '户用储能'
df.loc[(df[capacity_col] > 30) & (df[capacity_col] <= 1000), '类型'] = '工商业储能'
df.loc[df[capacity_col] > 1000, '类型'] = '大型储能'

print("\n分类统计结果：")
print(df['类型'].value_counts())

# ============ 第四步：按年份和类型统计容量（MWh） ============
df['容量_MWh'] = df[capacity_col] / 1000
df['年份'] = df['Registrierungsdatum'].dt.year

yearly_capacity = df.groupby(['年份', '类型'])['容量_MWh'].sum().reset_index(name='容量_MWh')
pivot = yearly_capacity.pivot(index='年份', columns='类型', values='容量_MWh').fillna(0)

for t in ['户用储能', '工商业储能', '大型储能']:
    if t not in pivot.columns:
        pivot[t] = 0

pivot['总计_MWh'] = pivot[['户用储能', '工商业储能', '大型储能']].sum(axis=1)

# 单独提取大储数据（用于大储专属图）
big_storage_capacity = df[df['类型'] == '大型储能'].copy()
big_storage_capacity['容量_MWh'] = big_storage_capacity[capacity_col] / 1000
big_storage_capacity['年份'] = big_storage_capacity['Registrierungsdatum'].dt.year
big_yearly = big_storage_capacity.groupby('年份')['容量_MWh'].sum().reset_index(name='容量_MWh')

# ============ 第五步：绘制两张图 ============

# ----- 图1：全景对比图（2021年用灰色标注）-----
fig1, ax1 = plt.subplots(figsize=(16, 8))

colors = {
    '户用储能': '#4A90D9',
    '工商业储能': '#F5A623',
    '大型储能': '#E74C3C'
}

order = ['户用储能', '工商业储能', '大型储能']
bottom = 0

for t in order:
    # 2021年的大储柱子用灰色特殊显示
    values = pivot[t].copy()
    if 2021 in values.index:
        original_val = values.loc[2021]
        values.loc[2021] = 0  # 先清零，后面单独画灰色柱子

    ax1.bar(pivot.index, values, bottom=bottom, label=f'{t} 容量',
            color=colors[t], alpha=0.85, width=0.6)
    bottom += values

# 单独画2021年的大储灰色柱子
if 2021 in pivot.index:
    big_storage_2021 = pivot.loc[2021, '大型储能']
    # 灰色柱子从底部开始（包含户储和工商业的2021年值）
    other_2021 = pivot.loc[2021, ['户用储能', '工商业储能']].sum()
    ax1.bar([2021], [big_storage_2021], bottom=[other_2021],
            color='#808080', alpha=0.85, width=0.6, label='大型储能(2021旧项目注册)', zorder=5)

# 总计折线（排除2021年，避免异常值压缩视觉）
pivot_clean = pivot.drop(index=2021, errors='ignore')
ax1.plot(pivot_clean.index, pivot_clean['总计_MWh'],
         color='black', linewidth=3, marker='o', markersize=8,
         label='市场总容量(不含2021异常值)', zorder=10)

# 标注总计数值
for year in pivot_clean.index:
    total = pivot_clean.loc[year, '总计_MWh']
    ax1.annotate(f'{total:,.0f} MWh',
                 xy=(year, total),
                 xytext=(0, 20),
                 textcoords='offset points',
                 ha='center', fontsize=10, fontweight='bold',
                 bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="gray", alpha=0.9))

# 标注2021年灰色柱子数值
if 2021 in pivot.index:
    big_storage_2021 = pivot.loc[2021, '大型储能']
    ax1.annotate(f'{big_storage_2021:,.0f} MWh\n(旧项目集中注册)',
                 xy=(2021, big_storage_2021),
                 xytext=(0, 20),
                 textcoords='offset points',
                 ha='center', fontsize=10, fontweight='bold',
                 color='#555555',
                 bbox=dict(boxstyle="round,pad=0.2", fc="lightgray", ec="gray", alpha=0.9))

ax1.set_xlabel('年份', fontsize=14)
ax1.set_ylabel('新增设备容量 (MWh)', fontsize=14)
ax1.set_title(
    '德国储能市场全景图：户储存量 vs 大储爆发（2018-2026）\n—— 行业评估口径：按容量（MWh）统计 | 灰色=2021旧项目集中注册',
    fontsize=16, fontweight='bold')
ax1.set_xticks(range(2018, 2027))
ax1.legend(loc='upper left', fontsize=12, framealpha=0.9)
ax1.grid(axis='y', alpha=0.3)

plt.tight_layout()

chart_path1 = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "germany_storage_panoramic_clean_2021.png")
plt.savefig(chart_path1, dpi=150, bbox_inches='tight')
print(f"\n全景对比图(含2021标注)已保存：{chart_path1}")

# ----- 图2：剔除2021年后的干净全景对比图 -----
fig2, ax2 = plt.subplots(figsize=(14, 7))

bottom2 = 0
for t in order:
    ax2.bar(pivot_clean.index, pivot_clean[t], bottom=bottom2, label=f'{t} 容量',
            color=colors[t], alpha=0.85, width=0.6)
    bottom2 += pivot_clean[t]

# 总计折线
ax2.plot(pivot_clean.index, pivot_clean['总计_MWh'],
         color='black', linewidth=3, marker='o', markersize=8,
         label='市场总容量', zorder=10)

# 标注数值
for year in pivot_clean.index:
    total = pivot_clean.loc[year, '总计_MWh']
    ax2.annotate(f'{total:,.0f} MWh',
                 xy=(year, total),
                 xytext=(0, 20),
                 textcoords='offset points',
                 ha='center', fontsize=10, fontweight='bold',
                 bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="gray", alpha=0.9))

ax2.set_xlabel('年份', fontsize=14)
ax2.set_ylabel('新增设备容量 (MWh)', fontsize=14)
ax2.set_title('德国储能市场全景对比（2018-2026，剔除2021异常值）\n—— 清晰展示户储存量 vs 大储真实爆发趋势',
              fontsize=16, fontweight='bold')
ax2.set_xticks(range(2018, 2027))
ax2.legend(loc='upper left', fontsize=13, framealpha=0.9)
ax2.grid(axis='y', alpha=0.3)

plt.tight_layout()

chart_path2 = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "germany_storage_panoramic_clean_no2021.png")
plt.savefig(chart_path2, dpi=150, bbox_inches='tight')
print(f"干净对比图(剔除2021)已保存：{chart_path2}")

# ----- 图3：大储专属容量趋势图（剔除2021年） -----
fig3, ax3 = plt.subplots(figsize=(14, 7))

# 筛选2021以外的年份
big_yearly_clean = big_yearly[big_yearly['年份'] != 2021].copy()

bars = ax3.bar(big_yearly_clean['年份'], big_yearly_clean['容量_MWh'],
               color='#E74C3C', alpha=0.85, width=0.6, label='大型储能新增容量')
ax3.plot(big_yearly_clean['年份'], big_yearly_clean['容量_MWh'],
         color='#C0392B', linewidth=3, marker='o', markersize=8, zorder=5)

# 标注数值
for i, row in big_yearly_clean.iterrows():
    ax3.annotate(f'{row["容量_MWh"]:.1f} MWh',
                 xy=(row['年份'], row['容量_MWh']),
                 xytext=(0, 15),
                 textcoords='offset points',
                 ha='center', fontsize=10, fontweight='bold')

ax3.set_xlabel('年份', fontsize=13)
ax3.set_ylabel('新增容量 (MWh)', fontsize=13)
ax3.set_title('德国大型储能（大储）新增容量趋势（2018-2026，剔除2021异常值）\n—— 捕捉大储真实爆发拐点',
              fontsize=15, fontweight='bold')
ax3.set_xticks(range(2018, 2027))
ax3.legend(loc='upper left', fontsize=12)
ax3.grid(axis='y', alpha=0.3)

plt.tight_layout()

chart_path3 = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "germany_big_storage_capacity_clean.png")
plt.savefig(chart_path3, dpi=150, bbox_inches='tight')
print(f"大储干净趋势图已保存：{chart_path3}")

# 导出数据
csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "germany_storage_capacity_final_data.csv")
pivot.to_csv(csv_path, encoding='utf-8-sig')
print(f"\n年度容量明细数据已导出：{csv_path}")

plt.show()
print("\n程序运行结束！共生成3张图表 + 1个CSV数据文件")