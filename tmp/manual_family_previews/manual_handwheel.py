import cadquery as cq

def create_din950_handwheel(d1=250, has_handle=True):
    """
    根据 DIN 950 标准生成参数化轮辐式手轮。
    :param d1: 手轮外径 (支持 125, 160, 200, 250, 315)
    :param has_handle: 是否生成配套的旋转手柄 (DIN 98 风格)
    """
    # =========================
    # 核心字典：DIN 950 离散参数查表
    # 参数映射：spokes(轮辐数), hub_d(轮毂外径), bore_d(轴孔径), hub_l(轮毂长),
    #          rim_w(轮缘宽), rim_l(轮缘长), dish(轴向沉降), m(手柄螺纹), h_len(手柄长)
    # =========================
    din950_table = {
        125: {'spokes': 3, 'hub_d': 28, 'bore_d': 12, 'hub_l': 28, 'rim_w': 15, 'rim_l': 18, 'dish': 18, 'm': 8,  'h_len': 65},
        160: {'spokes': 3, 'hub_d': 32, 'bore_d': 14, 'hub_l': 32, 'rim_w': 18, 'rim_l': 20, 'dish': 20, 'm': 10, 'h_len': 80},
        200: {'spokes': 3, 'hub_d': 38, 'bore_d': 18, 'hub_l': 38, 'rim_w': 22, 'rim_l': 24, 'dish': 24, 'm': 10, 'h_len': 80},
        250: {'spokes': 5, 'hub_d': 45, 'bore_d': 22, 'hub_l': 44, 'rim_w': 26, 'rim_l': 26, 'dish': 30, 'm': 12, 'h_len': 90},
        315: {'spokes': 5, 'hub_d': 53, 'bore_d': 26, 'hub_l': 53, 'rim_w': 28, 'rim_l': 28, 'dish': 33, 'm': 12, 'h_len': 90},
    }

    if d1 not in din950_table:
        raise ValueError(f"尺寸 d1={d1} 不在参数表中。支持的尺寸: {list(din950_table.keys())}")

    p = din950_table[d1]

    # 解析当前档位的几何参数
    hub_r = p['hub_d'] / 2.0
    bore_r = p['bore_d'] / 2.0
    hub_len = p['hub_l']

    rim_ro = d1 / 2.0
    rim_ri = rim_ro - p['rim_w']
    rim_len = p['rim_l']
    rim_x_shift = p['dish']  

    # =========================
    # Step 1: 轮毂 (Hub) 与 轮缘 (Rim)
    # 策略：轮毂在原点居中对称，轮缘向 +X 方向产生沉降
    # =========================
    hub_start = -hub_len / 2.0
    rim_start = rim_x_shift - rim_len / 2.0

    hub = (
        cq.Workplane("YZ")
        .workplane(offset=hub_start)
        .circle(hub_r).circle(bore_r)
        .extrude(hub_len)
    )

    rim = (
        cq.Workplane("YZ")
        .workplane(offset=rim_start)
        .circle(rim_ro).circle(rim_ri)
        .extrude(rim_len)
    )

    wheel = hub.union(rim)

    # =========================
    # Step 2: 轮辐 (Spokes)
    # 策略：通过截面轮廓构建梯形连杆，使其自适应 hub 和 rim 的宽度
    # =========================
    spoke_thickness = p['hub_d'] * 0.25  # 轮辐厚度根据轮毂外径自适应

    r_in = hub_r - 2.0
    r_out = rim_ri + 2.0

    # 绘制连续的四边形截面 (逆时针/顺时针闭合)
    p1 = (hub_start + 2.0, r_in)                 # 轮毂左下
    p2 = (hub_start + hub_len - 2.0, r_in)       # 轮毂右下
    p3 = (rim_start + rim_len - 2.0, r_out)      # 轮缘右上
    p4 = (rim_start + 2.0, r_out)                # 轮缘左上

    base_spoke = (
        cq.Workplane("XY")
        .polyline([p1, p2, p3, p4])
        .close()
        .extrude(spoke_thickness / 2.0, both=True)
    )

    # 环形阵列轮辐
    num_spokes = p['spokes']
    for i in range(num_spokes):
        angle = i * (360.0 / num_spokes)
        rotated_spoke = base_spoke.rotate((0, 0, 0), (1, 0, 0), angle)
        wheel = wheel.union(rotated_spoke)

    # =========================
    # Step 3: 手柄 (Crank Handle - DIN 98 标准简化版)
    # 策略：切换局部坐标系到轮缘面中心，向外拉伸
    # =========================
    if has_handle:
        handle_r_pos = (rim_ro + rim_ri) / 2.0   # 安装在轮缘宽度的正中间
        handle_z_start = rim_start + rim_len     # 从轮缘的前端面开始向外突出
        
        base_cyl_r = p['m'] * 0.75               # 手柄底座螺柱半径
        grip_r = p['m'] * 1.2                    # 手柄握把最大半径
        base_cyl_l = 8.0                         # 底座高度

        handle = (
            cq.Workplane("YZ")
            .workplane(offset=handle_z_start)
            .center(handle_r_pos, 0)             # ***关键***：将局部坐标系平移到轮缘孔位
            .circle(base_cyl_r).extrude(base_cyl_l)
            .faces(">X")                         # 选择刚刚拉伸出的顶面
            .circle(grip_r).extrude(p['h_len'] - base_cyl_l)
            .edges(">X").chamfer(p['m'] * 0.4)   # 顶部安全倒角
        )
        wheel = wheel.union(handle)

    return wheel

# =========================
# 实例化调用与测试
# =========================
# 你可以直接修改 d1 的值为 125, 160, 200, 250, 315 来查看拓扑结构的变化
result = create_din950_handwheel(d1=250, has_handle=True)

if 'show_object' in locals():
    show_object(result, name="DIN_950_Handwheel_Parameterized")