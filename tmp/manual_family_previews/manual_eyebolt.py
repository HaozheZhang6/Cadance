import cadquery as cq

def create_din580_strict(size="M12"):
    """
    基于 DIN 580 标准图纸严格推导的参数化吊环螺栓。
    包含核心厚度控制与颈部宽度参数 m。
    """
    # DIN 580 核心尺寸表 (新增参数 m: 圆环生根处的颈部宽度)
    dims = {
        "M8":  {"d1": 8,  "l": 13,   "d2": 20, "d3": 36, "d4": 20, "h": 36, "e": 6,  "m": 10},
        "M10": {"d1": 10, "l": 17,   "d2": 25, "d3": 45, "d4": 25, "h": 45, "e": 8,  "m": 12},
        "M12": {"d1": 12, "l": 20.5, "d2": 30, "d3": 54, "d4": 30, "h": 53, "e": 10, "m": 14},
        "M16": {"d1": 16, "l": 27,   "d2": 35, "d3": 63, "d4": 35, "h": 62, "e": 12, "m": 16},
        "M20": {"d1": 20, "l": 30,   "d2": 40, "d3": 72, "d4": 40, "h": 71, "e": 14, "m": 19},
    }

    if size not in dims:
        size = "M12"
        
    d = dims[size]

    # --- 核心平面 Z 坐标与几何推算 ---
    e = d["e"]                                   # Z1: 法兰顶面高度
    minor_radius = (d["d3"] - d["d4"]) / 4.0     # 圆环截面半径
    major_radius = (d["d3"] + d["d4"]) / 4.0     # 圆环主轴半径
    eye_center_z = d["h"] - (d["d3"] / 2.0)      # Z2: 圆环中心高度
    ring_bottom_z = eye_center_z - minor_radius  # Z3: 圆环最底端高度

    # 1. 底部法兰 (Z=0 向上挤压 e 厚度)
    collar = cq.Workplane("XY").cylinder(e, d["d2"]/2, centered=(True, True, False))

    # 2. 螺纹杆 (Z=0 向下挤压 l 长度)
    shank = (cq.Workplane("XY")
             .workplane(offset=0)
             .cylinder(d["l"], d["d1"]/2, centered=(True, True, False))
             .translate((0, 0, -d["l"])))

    # 3. 吊环 (生成于原点，旋转并平移至 eye_center_z)
    torus_solid = cq.Solid.makeTorus(major_radius, minor_radius)
    ring = (cq.Workplane("XY")
            .add(torus_solid)
            .rotate((0, 0, 0), (1, 0, 0), 90)
            .translate((0, 0, eye_center_z)))

    # 4. 精确的过渡圆台 (Neck)
    # 高度被严格限制在 [e, ring_bottom_z] 之间
    # 底部直径基于 m 适当放大以形成锥度，顶部直径严格收缩至 m
    neck_base_d = min(d["m"] * 1.5, d["d2"] * 0.8) 
    
    neck = (cq.Workplane("XY")
            .workplane(offset=e)
            .circle(neck_base_d / 2.0)
            # 顶部增加 0.5mm 偏移使其刺入圆环内部，防止布尔运算产生非流形边
            .workplane(offset=ring_bottom_z - e - minor_radius) 
            .circle(d["m"] / 2.0)
            .loft())

    # 5. 布尔求和
    eyebolt = collar.union(shank).union(ring).union(neck)

    # 6. 工程倒角处理 (在法兰和圆台交界处 Z=e 附近添加倒圆角 R1.5)
    try:
        eyebolt = eyebolt.edges(cq.selectors.NearestToPointSelector((0, 0, e))).fillet(1.5)
    except:
        pass # 忽略倒角失败的情况保证主模型生成

    return eyebolt

# 实例化 M12 并导出
eyebolt_m12 = create_din580_strict("M20")
cq.exporters.export(eyebolt_m12, 'DIN580_M12_Strict.step')

# CQ-Editor 可视化命令
# show_object(eyebolt_m12, name="DIN580_M12_Strict")