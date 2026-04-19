import cadquery as cq
import math

def create_din2088_rock_solid(
    wire_dia=2.0, 
    mean_dia=15.0, 
    coils=5.25, 
    pitch=4.0,     # <--- 核心救命参数：必须明显大于 wire_dia 才能防止内核卡死！
    leg1_len=20.0, 
    leg2_len=20.0
):
    R = mean_dia / 2.0
    H = pitch * coils
    
    # ==========================================
    # 1. 绝对安全的底层几何螺旋线 (零拟合)
    # ==========================================
    helix = cq.Wire.makeHelix(pitch=pitch, height=H, radius=R)
    path = cq.Workplane("XY").add(helix)
    
    # ==========================================
    # 2. 扫掠中央线圈 (精确计算 t=0 处的法平面)
    # ==========================================
    # 在 t=0 处，坐标为 (R, 0, 0)
    dy0 = R
    dz0 = pitch / (2 * math.pi)
    mag0 = math.sqrt(dy0**2 + dz0**2)
    dir0 = cq.Vector(0, dy0/mag0, dz0/mag0)
    
    plane0 = cq.Plane(origin=(R, 0, 0), normal=dir0.toTuple())
    coil = cq.Workplane(plane0).circle(wire_dia / 2.0).sweep(path, isFrenet=True)
    
    # ==========================================
    # 3. 起点扭臂 (在同一个法平面上，向后反向拉伸)
    # ==========================================
    # extrude 传负数代表沿着法向量反方向拉伸，与线圈绝对完美对接
    leg1 = cq.Workplane(plane0).circle(wire_dia / 2.0).extrude(-leg1_len)
    
    # ==========================================
    # 4. 终点扭臂 (精确计算 t=end 处的法平面)
    # ==========================================
    t_end = coils * 2 * math.pi
    px = R * math.cos(t_end)
    py = R * math.sin(t_end)
    pz = H
    
    dx1 = -R * math.sin(t_end)
    dy1 =  R * math.cos(t_end)
    dz1 = pitch / (2 * math.pi)
    mag1 = math.sqrt(dx1**2 + dy1**2 + dz1**2)
    dir1 = cq.Vector(dx1/mag1, dy1/mag1, dz1/mag1)
    
    plane1 = cq.Plane(origin=(px, py, pz), normal=dir1.toTuple())
    # 顺着终点切线方向拉伸
    leg2 = cq.Workplane(plane1).circle(wire_dia / 2.0).extrude(leg2_len)
    
    # ==========================================
    # 5. 组合三个纯净实体
    # ==========================================
    spring = coil.union(leg1).union(leg2)
    
    return spring

# 执行生成
torsion_spring = create_din2088_rock_solid()

if 'show_object' in locals():
    show_object(torsion_spring, name="Stable_Spring")