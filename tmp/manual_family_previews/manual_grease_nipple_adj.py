import cadquery as cq
import math

def create_din71412_type_a(size_key="M6x1_s7"):
    params = {
        "M6x1_s7":  {"d1": 6.0,  "h": 16.0, "l": 5.5, "d2": 6.5, "b": 3.0, "s": 7.0,  "z": 0.7},
        "M6x1_s9":  {"d1": 6.0,  "h": 16.0, "l": 5.5, "d2": 6.5, "b": 3.0, "s": 9.0,  "z": 0.7},
        "M8x1":     {"d1": 8.0,  "h": 16.0, "l": 5.5, "d2": 6.5, "b": 3.0, "s": 9.0,  "z": 0.7},
        "AR_1/8":   {"d1": 9.73, "h": 16.0, "l": 5.5, "d2": 6.5, "b": 3.0, "s": 11.0, "z": 0.7},
        "M10x1":    {"d1": 10.0, "h": 16.0, "l": 5.5, "d2": 6.5, "b": 3.0, "s": 11.0, "z": 0.7},
        "AR_1/4":   {"d1": 13.16,"h": 16.0, "l": 5.5, "d2": 6.5, "b": 3.0, "s": 14.0, "z": 0.7},
    }

    if size_key not in params:
        raise ValueError(f"尺寸 {size_key} 不在标准参数表中。")

    p = params[size_key]
    d1, h, l, d2, b, s, z_max = p['d1'], p['h'], p['l'], p['d2'], p['b'], p['s'], p['z']
    
    hex_diam = s * 2 / math.sqrt(3)

    # --- 核心几何比例重构 ---
    head_base_z = l + b
    
    # 1. 加粗颈部，解决“下部窄”的视觉感 (从减 2.0 优化为减 1.0)
    d_neck = d2 - 1.0  
    
    # 2. 顶部平台直径 (调整为 d2 的 55%，显得更加敦实)
    d_top = 0.55 * d2 
    
    # 3. 动态推导高度，确保 45° 扩张角在数学上严格成立
    head_max_z = h - 3.2 # 设定最大直径出现的高度
    taper_height = (d2 - d_neck) / 2 # 45度倒角的固定高度需求
    
    # 颈部直段高度由总高度倒推得出，避免破坏 45 度角
    neck_straight = (head_max_z - taper_height) - head_base_z 
    
    # 防御性约束，防止极端参数下直段高度为负
    if neck_straight < 0.2:
        neck_straight = 0.2
        head_max_z = head_base_z + neck_straight + taper_height

    pts = [
        (0, 0),
        (d1 / 2, 0),
        (d1 / 2, l),
        (d_neck / 2, l),
        (d_neck / 2, head_base_z),
        (d_neck / 2, head_base_z + neck_straight),
        (d2 / 2, head_max_z),  
        (d_top / 2, h),        
        (0, h)                 
    ]
    
    body = (
        cq.Workplane("XZ")
        .polyline(pts)
        .close()
        .revolve(360, (0, 0, 0), (0, 1, 0))
    )
    
    # 放大顶部圆角至 1.0，配合加宽的 d_top 形成经典的工业短球头质感
    body = body.edges(">Z").fillet(1.0)
    body = body.edges("<Z").chamfer(z_max)

    hex_flange = (
        cq.Workplane("XY")
        .workplane(offset=l)
        .polygon(6, hex_diam)
        .extrude(b)
    )

    nipple = (
        body.union(hex_flange)
        .faces(">Z").workplane()
        .circle(2.5 / 2) 
        .cutThruAll()
    )
    
    return nipple

# 测试生成
part = create_din71412_type_a("M6x1_s7")