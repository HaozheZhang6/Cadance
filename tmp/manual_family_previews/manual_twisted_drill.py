import math
import cadquery as cq

"""
参数化直柄麻花钻 (Parametric Straight Shank Twist Drill - DIN 338)

本脚本基于 CadQuery 自动生成符合德国工业标准的精密麻花钻头。
采用“正向截面扭转拉伸 (Twist Extrusion)”与“包络交集法 (Envelope Intersection)”技术。

================================================================================
【核心标准规范依据: DIN 338 & 钻削几何学】

1. DIN 338 (直柄短麻花钻):
   - 钻尖角 (Point Angle): 标准 N型(通用型) 固定为 118°。
   - 螺旋角 (Helix Angle): 标准要求 γ = 25° ~ 30°。通过螺距 (pitch) 约束实现。

2. 物理与几何约束 (Physical Constraints):
   - 刚性约束: 刃长与半径的比值 (L/R0) 不宜过大，否则物理强度无法支撑切削载荷。
   - 螺旋约束: 螺距必须与直径联动，以维持恒定的螺旋角，保证排屑通畅。
   - 几何安全: 刃长必须大于钻尖的锥体高度，否则无法形成有效的螺旋刃口。

================================================================================
【参数详细对照表与物理取值范围】

| 参数变量 (Code) | 推荐标准取值范围 (Recommended Range) | 物理约束与联动关系 (Physical Constraints) |
| :---           | :---                               | :---                                     |
| rod_radius (R0)| 0.5 ~ 10.0 mm                      | 基准参数。决定所有微观截面尺寸。             |
| rod_length (L) | 8.0 * R0 ~ 15.0 * R0               | 必须满足 L > (R0 / tan(tip_angle/2))。      |
| pitch (P)      | 11.0 * R0 ~ 13.5 * R0              | 维持螺旋角 γ ≈ 28°。P = (2*π*R0) / tan(γ)。 |
| tip_angle (θ)  | 90.0° ~ 140.0°                     | 标准值 118.0°。角度越钝轴向推力需求越大。    |

微观几何联动 (内部自动缩放计算):
    - r_phi (钻芯半厚) = 0.18 * rod_radius (保证抗扭刚度)
    - Ra (刃背圆弧半径) = 0.6 * rod_radius (保证排屑空间)
    - phi_deg (切削刃偏角) = 30° (控制主切削刃形状)
================================================================================

主要输入参数:
    rod_radius (float): 钻头实体的外圆半径。
    rod_length (float): 带有螺旋排屑槽的有效切削刃长度 (不包含钻柄)。
    pitch      (float): 螺旋排屑槽的升程/螺距。
    tip_angle  (float): 钻头端部锥角，默认为 118.0 度。

输出:
    生成 cq.Workplane 实体对象，中心轴线沿 Z 轴，底面(接柄处)位于 Z=0，钻尖位于 Z=rod_length。
"""

def _arc_midpoint(
    center: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
) -> tuple[float, float]:
    """[内部辅助函数] 计算小圆弧中点"""
    cx, cy = center
    a1 = math.atan2(p1[1] - cy, p1[0] - cx)
    a2 = math.atan2(p2[1] - cy, p2[0] - cx)

    delta = a2 - a1
    while delta > math.pi:
        delta -= 2.0 * math.pi
    while delta < -math.pi:
        delta += 2.0 * math.pi

    amid = a1 + 0.5 * delta
    radius = math.hypot(p1[0] - cx, p1[1] - cy)

    return (
        cx + radius * math.cos(amid),
        cy + radius * math.sin(amid),
    )


def _build_cutter_profile(
    R0: float,
    r_phi: float,
    Ra: float,
    phi_deg: float,
) -> cq.Workplane:
    """[内部辅助函数] 基于高精度数学模型构建单侧切削刀具 2D 轮廓"""
    phi = math.radians(phi_deg)

    I = (0.0, r_phi)
    R = (
        R0 * math.cos(phi),
        R0 * math.sin(phi),
    )

    Rb = (
        (R0 ** 2 - 2.0 * R0 * r_phi * math.sin(phi) + r_phi ** 2)
        / (2.0 * (R0 * math.sin(phi) - r_phi))
    )

    Ca = (0.0, r_phi + Ra)
    Cb = (0.0, r_phi + Rb)

    y_q = (R0 ** 2 + r_phi ** 2 + 2.0 * r_phi * Ra) / (2.0 * (r_phi + Ra))
    x_q = -math.sqrt(max(R0 ** 2 - y_q ** 2, 0.0))
    Q = (x_q, y_q)

    mid_big = _arc_midpoint(Ca, Q, I)
    mid_small = _arc_midpoint(Cb, I, R)

    theta_q = math.atan2(Q[1], Q[0])
    theta_r = math.atan2(R[1], R[0])
    if theta_q < theta_r:
        theta_q += 2.0 * math.pi
    theta_mid = 0.5 * (theta_q + theta_r)
    mid_outer = (
        R0 * math.cos(theta_mid),
        R0 * math.sin(theta_mid),
    )

    profile = (
        cq.Workplane("XY")
        .moveTo(*Q)
        .threePointArc(mid_big, I)
        .threePointArc(mid_small, R)
        .threePointArc(mid_outer, Q)
        .close()
    )

    return profile


def build_din338_drill(
    rod_radius: float = 4.0,
    rod_length: float = 40.0,
    pitch: float = 47.0,
    tip_angle: float = 118.0
) -> cq.Workplane:
    """
    生成 DIN 338 标准直柄麻花钻的主干方法。
    """
    
    # ==========================================
    # 0. 内部参数联动计算 (基于 rod_radius)
    # ==========================================
    r_phi = 0.18 * rod_radius  
    Ra = 0.6 * rod_radius      
    phi_deg = 30.0             

    # ==========================================
    # 1. 提取并生成对称的二维截面槽
    # ==========================================
    cutter1_wp = _build_cutter_profile(R0=rod_radius, r_phi=r_phi, Ra=Ra, phi_deg=phi_deg)
    cutter2_wp = cutter1_wp.rotate((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), 180.0)
    
    cutter1_face = cq.Face.makeFromWires(cutter1_wp.val())
    cutter2_face = cq.Face.makeFromWires(cutter2_wp.val())

    drill_profile_sketch = (
        cq.Sketch()
        .circle(rod_radius)
        .face(cutter1_face, mode="s") 
        .face(cutter2_face, mode="s") 
        .clean()
    )

    # ==========================================
    # 2. twistExtrude 扭转拉伸 (增加 Overshoot 避免布尔引擎崩溃)
    # ==========================================
    overshoot = 5.0  # 🔥 关键修复：多拉伸 5mm 的毛坯余量
    total_length = rod_length + overshoot
    
    # 旋转角度需要根据总长度重新计算，保证螺距依然准确
    total_twist_angle = 360.0 * (total_length / pitch) 
    
    drill_body = (
        cq.Workplane("XY")
        .placeSketch(drill_profile_sketch)
        .twistExtrude(total_length, total_twist_angle)
    )

    # ==========================================
    # 3. 削钻尖 (Envelope Intersection Pointing)
    # ==========================================
    tip_height = rod_radius / math.tan(math.radians(tip_angle / 2.0))
    straight_length = rod_length - tip_height
    
    # 构建虚拟包络刀模 (这个刀模的顶点正好在 Z = rod_length)
    envelope = (
        cq.Workplane("XY")
        .circle(rod_radius)
        .extrude(straight_length) 
        .faces(">Z").workplane()
        .circle(rod_radius)
        .workplane(offset=tip_height)
        .circle(0.001) 
        .loft(combine=True) 
    )
    
    # 布尔交集切削：刀模在螺旋体内部切削，绝对不会掉面！
    final_drill = drill_body.intersect(envelope)

    return final_drill

# 运行测试
result = build_din338_drill(
    rod_radius=4.0,
    rod_length=40.0,
    pitch=47.0,
    tip_angle=118.0
)