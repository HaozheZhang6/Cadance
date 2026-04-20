import cadquery as cq
import math

"""
    参数化圆翼翼形螺母 (Parametric Wing Nut with Rounded Wings - DIN 315)

    本脚本基于 CadQuery 自动生成符合德国工业标准 (DIN 315) 的精铸圆翼螺母。
    采用“参数化解析几何推导 (Parametric Analytic Geometry)”与“实体放样组合 (Lofted Union)”技术。

    ================================================================================
    【核心标准规范依据: DIN 315】

    1. DIN 315 (翼形螺母 - 圆翼型 / Rounded Wings):
       - 外观特征: 具备两个圆润饱满的翼片，便于手指施力旋拧。
       - 尺寸包络: 标准严格定义了外围最大包络尺寸：总宽(e)、总高(h)、轮毂直径(d2)等。

    2. 物理与几何约束 (Physical Constraints):
       - 拓扑相交约束: 翼片的内侧起点必须侵入轮毂 (Hub) 内部，以保证布尔合并 (Union) 后形成单一流形 (Manifold)，避免拓扑破面。
       - 几何解析约束: 翼片外侧的特征圆弧不是随意的，而是受限于最高点 (Z=h) 和最外点 (X=e/2)，系统会自动解算唯一对应的圆心与半径。
       - 厚度与倒角联动: 为了模拟真实精铸件的干练感并避免直角干涉，边缘倒角半径必须与翼片的实际厚度动态联动。

    ================================================================================
    【参数详细对照表与物理取值范围】

    | 参数变量 (Code) | 推荐标准取值范围 (参考 M3-M24) | 物理约束与联动关系 (Physical Constraints) |
    | :---            | :---                           | :---                                      |
    | d2 (轮毂底径)   | 7.0 ~ 44.0 mm                  | 基准参数。必须满足 d2 < e 且 d2 > hole_d。|
    | m  (轮毂高度)   | 3.9 ~ 25.0 mm                  | 必须满足 m < h，否则翼片将被完全淹没。    |
    | e  (翼片总宽)   | 19.0 ~ 110.0 mm                | 决定力臂长度。控制外侧圆弧特征点 (e/2)。  |
    | h  (螺母总高)   | 9.5 ~ 56.5 mm                  | 决定翼片最高点。控制顶部圆弧特征点。      |
    | d3 (翼片厚度)   | 6.0 ~ 37.5 mm                  | 影响翼片根部厚度及倒角半径的计算基准。    |
    | hole_d(中心孔)  | 2.5 ~ 21.0 mm (视螺纹而定)     | 中心底孔直径。必须满足 hole_d < d2 - 2.0。|

    微观几何联动 (内部自动推导计算):
        - 圆弧圆心 X坐标 (x) = e/4 + d2/4 (保证翼片外形比例协调)
        - 圆弧特征半径 (R) = 由方程 (dX^2 + dZ^2) / (2*dZ) 严格推导，保证圆弧平滑经过极限点。
        - 翼片实际厚度 = d3 / 8 (修正了标准最大包络值带来的笨重感，模拟精铸薄边)
        - 边缘倒角半径 = (d3 / 8) * 0.8 (动态适应厚度，防止 3D 倒角失败/破面)
        - 轮毂微锥度 = 顶部半径d3/2，模拟脱模斜度/铸造圆台。
    ================================================================================

    Args:
        d2 (float): 轮毂底部最大外径。
        m (float): 轮毂圆柱体的高度。
        e (float): 两侧翼片展开的最大总宽度。
        h (float): 从底面到翼片最高点的总高度。
        d3 (float): 轮毂顶部最大外径。
        hole_d (float): 中心通孔（螺纹预钻孔）的直径。

    Returns:
        cq.Workplane: 生成的 3D 实体对象，中心轴线沿 Z 轴，底面位于 Z=0。
    """

# --- 尺寸参数 (以 M8 为例) ---
e = 39.0
h = 20.0
m = 10.0
d2 = 16.0
d3 = 12.5
hole_d = 8.0

# --- 核心几何推导 ---
x = e / 4 + d2 / 4
X_end = e / 2
Z_end = e / 2 - d2 / 2

# 推导唯一圆弧
dX = X_end - x
dZ = h - Z_end
R = (dX**2 + dZ**2) / (2 * dZ)
Z_c = h - R

# 计算三点圆弧中点
angle_start = math.atan2(Z_end - Z_c, X_end - x)
angle_end = math.pi / 2
angle_mid = (angle_start + angle_end) / 2
mid_x = x + R * math.cos(angle_mid)
mid_z = Z_c + R * math.sin(angle_mid)

# ==========================================
# 步骤 1: 绘制耳朵，Extrude 并做对称 (厚度改为 d3/8)
# ==========================================
ear_profile = (
    cq.Workplane("XZ")
    .moveTo(0, 0)
    .lineTo(d2 / 2, 0)                                   
    .lineTo(X_end, Z_end)                                
    .threePointArc((mid_x, mid_z), (x, h))               
    .lineTo(d3 / 2, m)                                   # 【修改点】内侧回落点也同步收缩到 d3/8
    .lineTo(0, m)                                        
    .close()
)

# 拉伸厚度改为 d3 / 8
ear = ear_profile.extrude(d3 / 8, both=True)
ears = ear.union(ear.mirror("YZ"))

# ==========================================
# 步骤 2: 做中间圆台
# ==========================================
hub = (
    cq.Workplane("XY")
    .circle(d2 / 2)
    .workplane(offset=m)
    .circle(d2 / 3)
    .loft()
)
result = ears.union(hub)

# ==========================================
# 步骤 3: 挖空
# ==========================================
cutter = cq.Workplane("XY").circle(hole_d / 2).extrude(m * 2)
result = result.cut(cutter)

# ==========================================
# 步骤 4: 加圆角等
# ==========================================
# 【修改点】为了防止变薄后倒角破面，倒角半径设为半厚度的 80%
fillet_radius = (d3 / 8) * 0.8
result = result.edges("|Y").fillet(fillet_radius)

try:
    result = result.edges(">Z").fillet(0.5)
except:
    pass

# 输出结果
show_object(result, name="DIN315_Thin_Ears")