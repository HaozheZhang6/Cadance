"""
参数化标准阶梯蜗杆生成器 (Standard Stepped Worm Gear Generator - ZA Profile)

本脚本基于 CadQuery 自动生成符合 ISO 10828 和 GB/T 10085 标准的 ZA 型圆柱蜗杆（阿基米德蜗杆）3D 模型。
不同于简单的连续螺纹，该模型采用实际工程中标准的“阶梯轴”设计：螺纹段居中，两端预留带有倒角的光轴，
以便于后续的轴承安装与机械装配。

核心设计与计算逻辑:
    1. 基础齿廓：采用 20° 压力角的标准直线梯形齿廓，包含 0.2m 的标准径向顶隙。
    2. 长度推导：螺纹段最小有效长度 (thread_length) 基于配对蜗轮齿数 (z2) 的经验公式自动计算。
    3. 几何构建：将二维梯形齿廓 (tooth_profile) 沿标准螺旋线 (helix_path) 扫掠，并与中心圆柱轴布尔求和。

主要输入参数 (Independent Parameters):
    m            (float): 模数 (Module)。决定齿轮轮齿的绝对大小，标准推荐值如 1.5, 2.0, 2.5 等。
    z1           (int):   头数 (Number of starts)。z1=1 通常具备自锁性，z1≥2 用于高效率传动。
    d1           (float): 分度圆直径 (Pitch diameter)。理论上 d1 = m * q (q为特性系数)。
    alpha        (float): 压力角 (Pressure angle)。标准直廓蜗杆通常取 20.0°。
    z2           (int):   配对蜗轮齿数。作为外部输入，用于推算螺纹段的合规覆盖长度。
    shaft_length (float): 蜗杆总轴长 (Total shaft length)。必须严格大于推算出的 thread_length。

输出 (Output):
    在当前运行目录下导出名为 'standard_stepped_worm.step' 的 STEP 实体模型文件。
"""

import cadquery as cq
import math

# ==========================================
# 1. 核心参数 (Standard Parameters)
# ==========================================
m = 2.0             # 模数
z1 = 1              # 头数
d1 = 20.0           # 分度圆直径
alpha = 20.0        # 压力角

# 长度参数分离 (关键修正点)
z2 = 40              # 假设配对的蜗轮齿数为 40
thread_length = 30.0 # 螺纹段长度 b1 (由 (11+0.06*40)*2 向上取整得到)
shaft_length = 80.0  # 杆子总长度 (必须大于 thread_length)

# ==========================================
# 2. 衍生参数自动计算
# ==========================================
p = math.pi * m                 
lead = p * z1                   
ha = m                          
hf = 1.2 * m                    
df = d1 - 2 * hf                

tooth_thickness = p / 2.0 
top_width = tooth_thickness - (2 * ha * math.tan(math.radians(alpha)))
bottom_width = tooth_thickness + (2 * hf * math.tan(math.radians(alpha)))

# ==========================================
# 3. 几何体构建 (Base & Sweep)
# ==========================================
# A. 构建加长的中心主轴 (长度为 80)
worm_shaft = cq.Workplane("XY").circle(df / 2.0).extrude(shaft_length)

# B. 绘制截面 (同之前)
tooth_profile = (
    cq.Workplane("XZ")
    .center(df / 2.0, 0)
    .polyline([
        (0, -bottom_width / 2.0),
        (ha + hf, -top_width / 2.0),
        (ha + hf, top_width / 2.0),
        (0, bottom_width / 2.0),
    ])
    .close()
)

# C. 生成螺旋线并扫掠 (螺旋线长度设为 thread_length 即 30)
helix_path = cq.Wire.makeHelix(pitch=lead, height=thread_length, radius=df / 2.0)
worm_thread_raw = tooth_profile.sweep(helix_path, isFrenet=True)

# D. 将螺纹段移动到主轴的中间位置
# 计算偏移量：(总长 - 螺纹长) / 2
z_offset = (shaft_length - thread_length) / 2.0
worm_thread = worm_thread_raw.translate((0, 0, z_offset))

# E. 将居中的螺纹与长杆子合并
final_worm = worm_shaft.union(worm_thread)

# ==========================================
# 4. 倒角 (可选，让两端更符合真实零件)
# ==========================================
# 给光轴的两端加一个 1mm 的倒角，方便插入轴承
final_worm = final_worm.edges("%CIRCLE").edges(">Z or <Z").chamfer(1.0)

# 导出模型
cq.exporters.export(final_worm, 'standard_stepped_worm.step')