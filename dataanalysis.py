import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
import matplotlib
from open_mastr import Mastr
import os

# 设置中文字体，避免图表中文乱码
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
matplotlib.rcParams['axes.unicode_minus'] = False

# ============ 第一步：下载数据 ============
print("🚀 正在检查/下载德国储能数据...")
db = Mastr()
db.download(data=["storage_units"])

# ============ 第二步：读取数据 ============
print("📊 正在解析数据...")
db_path = r"C:\Users\hlhua\.open-MaStR\data\sqlite\open-mastr.db"
conn = sqlite3.connect(db_path)
query = "SELECT * FROM storage_units"
df = pd.read_sql(query, conn)
conn.close()
print(f"原始数据量：{len(df)} 条")

# ============ 第三步：数据清洗 ============
# 1. 转换注册日期为 datetime 类型
df['Registrierungsdatum'] = pd.to_datetime(df['Registrierungsdatum'], errors='coerce')

# 2. 筛选 2018-2026 年的数据
df = df[
    (df['Registrierungsdatum'] >= '2018-01-01') &
    (df['Registrierungsdatum'] <= '2026-12-31')
].copy()

# 3. 删除注册日期为空的无效记录
df = df.dropna(subset=['Registrierungsdatum'])
print(f"清洗后数据量：{len(df)} 条")

# 4. 查看有哪些字段（列名），方便后续分析
print("\n数据字段如下：")
for i, col in enumerate(df.columns):
    print(f"  {i+1}. {col}")

# ============ 第四步：制作时间序列图表 ============
# 提取年月作为分组键
df['年月'] = df['Registrierungsdatum'].dt.to_period('M')

# 按月统计新增设备数量
monthly_count = df.groupby('年月').size().reset_index(name='新增设备数量')
monthly_count['年月'] = monthly_count['年月'].astype(str)

# 按月统计累计设备数量（时间序列的核心）
monthly_count['累计设备数量'] = monthly_count['新增设备数量'].cumsum()

# 绘制图表
fig, ax1 = plt.subplots(figsize=(14, 6))

# 柱状图：每月新增数量
bars = ax1.bar(monthly_count['年月'], monthly_count['新增设备数量'],
               color='steelblue', alpha=0.7, label='每月新增数量')
ax1.set_xlabel('年月', fontsize=12)
ax1.set_ylabel('每月新增设备数量', fontsize=12, color='steelblue')
ax1.tick_params(axis='y', labelcolor='steelblue')
ax1.set_xticks(range(0, len(monthly_count), 6))  # 每6个月显示一个刻度
ax1.set_xticklabels(monthly_count['年月'][::6], rotation=45)

# 折线图：累计数量（叠加在右侧Y轴）
ax2 = ax1.twinx()
line = ax2.plot(monthly_count['年月'], monthly_count['累计设备数量'],
                color='red', linewidth=2, marker='o', markersize=3, label='累计设备数量')
ax2.set_ylabel('累计设备数量', fontsize=12, color='red')
ax2.tick_params(axis='y', labelcolor='red')

# 标题和图例
plt.title('德国储能设备注册量时间序列（2018-2026）', fontsize=14, fontweight='bold')
fig.legend(loc='upper left', bbox_to_anchor=(0.1, 0.95))
plt.tight_layout()

# 保存图表
chart_path = os.path.join(os.path.dirname(__file__), "germany_storage_timeseries.png")
plt.savefig(chart_path, dpi=150, bbox_inches='tight')
print(f"\n✅ 时间序列图表已保存：{chart_path}")

# 同时导出清洗后的数据为 CSV
csv_path = os.path.join(os.path.dirname(__file__), "germany_storage_cleaned.csv")
df.to_csv(csv_path, index=False, encoding="utf-8-sig")
print(f"✅ 清洗后数据已导出：{csv_path}")

plt.show()
print("\n🎉 程序运行结束！")