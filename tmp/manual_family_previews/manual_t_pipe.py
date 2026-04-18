import cadquery as cq

# ================= 参数配置区 =================
# 主管道参数
main_pipe_length = 109.0
main_pipe_outer_radius = 21.0
main_pipe_inner_radius = 15.5

# 支管道参数
branch_length = 94.7
branch_outer_radius = 16.5
branch_inner_radius = 11.0

# 主管两端法兰参数
h_flange_thick = 4.0
h_flange_radius = 39.45
h_flange_bolt_radius = 28.15
h_flange_bolt_dia = 4.2
h_flange_offset = 55.5  

# 支管顶部法兰参数
v_flange_thick = 8.1
v_flange_radius = 23.65

# ================= 逻辑计算区 =================
branch_y_offset = branch_length / 2.0 

# 支管顶部法兰位置
v_flange_y_offset = branch_length - (v_flange_thick / 2.0)

# 支管盲孔切削：高度设为 branch_length + 1，确保切破顶部法兰。底端停在 Y=0
branch_cut_len = branch_length + 1.0
branch_cut_y_offset = branch_cut_len / 2.0

# 【新增】主管道通孔切削长度：必须穿透主管本体及其两端法兰（加 1.0 保证切透，防止共面残留）
main_cut_len = main_pipe_length + (h_flange_thick * 2) + 1.0
# =============================================

result = (
    cq.Workplane("XY")
    # --- 步骤 1：主管道外壁 ---
    .union(
        cq.Workplane("XY")
            .cylinder(main_pipe_length, main_pipe_outer_radius)
    )
    # --- 步骤 2：主管道两端法兰 ---
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, -h_flange_offset), rotate=cq.Vector(0, 0, 0))
            .cylinder(h_flange_thick, h_flange_radius)
    )
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, h_flange_offset), rotate=cq.Vector(0, 0, 0))
            .cylinder(h_flange_thick, h_flange_radius)
    )
    # --- 步骤 3：打主法兰螺栓孔阵 ---
    .faces(">Z").workplane()
    .polarArray(h_flange_bolt_radius, 0, 360, 6)
    .hole(h_flange_bolt_dia)
    .faces("<Z").workplane()
    .polarArray(h_flange_bolt_radius, 0, 360, 6)
    .hole(h_flange_bolt_dia)
    
    # --- 步骤 4：Union 支管外壁 ---
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, branch_y_offset, 0), rotate=cq.Vector(-90, 0, 0))
            .cylinder(branch_length, branch_outer_radius)
    )
    # --- 步骤 5：Union 支管法兰 ---
    .union(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, v_flange_y_offset, 0), rotate=cq.Vector(-90, 0, 0))
            .cylinder(v_flange_thick, v_flange_radius)
    )
    
    # --- 步骤 6：挖空支管和顶部法兰 ---
    .cut(
        cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, branch_cut_y_offset, 0), rotate=cq.Vector(-90, 0, 0))
            .cylinder(branch_cut_len, branch_inner_radius)
    )
    
    # --- 步骤 7：最后挖空主管道 ---
    .cut(
        cq.Workplane("XY")
            .cylinder(main_cut_len, main_pipe_inner_radius)
    )
)

# Export
show_object(result)