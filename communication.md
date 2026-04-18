可以。下面给你一个 **50 个 case 的 family 表**，按行业和 CAD use case 来想，目标是：

* 像真实工业件，不像 random shape
* 适合 **CadQuery 参数化批量生成**
* 能覆盖从易到难
* 覆盖车、电子、机床、制造设备、芯片厂、家电、工业加工件等

我把每个 case 都写成：

**`case名 | 行业 | 典型功能特征 | 难度`**

---

## 一、汽车 / 新能源 / 车载电子

1. **sensor_mount_bracket** | 车载传感器 | L 支架、安装孔、长槽、圆角 | 易
2. **camera_bracket** | ADAS/摄像头 | 双面安装孔、倾角面、加强筋 | 中
3. **radar_mount** | 车载雷达 | 平台、孔阵列、侧向支撑、对称界面 | 中
4. **wire_harness_clip_base** | 线束固定 | 底板、卡槽、螺钉孔、倒角 | 易
5. **busbar_support** | 电池/高压电 | 绝缘支撑体、通孔、台阶、定位面 | 中
6. **battery_pack_bracket** | 电池包结构 | 厚板、孔阵列、长槽、筋 | 中
7. **motor_end_cap** | 电驱系统 | 回转体、中心孔、螺栓孔圆周阵列 | 中
8. **bearing_seat_housing** | 旋转支撑 | 轴孔、安装法兰、倒角、台阶 | 中
9. **coolant_manifold_block** | 热管理 | 多孔道接口、法兰孔、腔体 | 难
10. **connector_protection_cover** | 车载电子 | 薄壁盖、卡扣位、开窗、圆角 | 中

**例子**：`sensor_mount_bracket` 就很适合做 easy family：一块底板 + 2 个孔 + 1 个长槽 + 侧边小圆角。

---

## 二、电子 / 控制箱 / 仪器设备

11. **pcb_standoff_plate** | 电子装配 | 板、柱、安装孔、定位孔 | 易
12. **electronics_enclosure_basic** | 控制盒 | box、shell、lid split、螺丝柱 | 中
13. **electronics_enclosure_vented** | 电控箱 | shell、散热槽、接口窗、螺柱 | 难
14. **connector_faceplate** | I/O 面板 | 矩形切口、螺孔、阵列槽 | 易
15. **display_bezel_frame** | 仪表/屏幕 | 外框、内窗、安装柱、圆角 | 中
16. **terminal_block_cover** | 接线端子 | 薄壁罩、通孔、卡槽 | 中
17. **fan_guard_panel** | 散热系统 | 面板、圆孔阵列、安装孔 | 易
18. **control_box_lid** | 工控设备 | 薄板盖、角孔、沉孔、加强边 | 易
19. **sensor_housing_pod** | 电子模块 | 圆角壳体、孔、定位柱、线缆出口 | 难
20. **cable_routing_panel** | 设备布线 | 板、开槽、长孔阵列、边缘倒角 | 中

---

## 三、机床 / 机械设备 / 工装夹具

21. **mounting_plate** | 通用机械 | 板、孔阵列、长槽 | 易
22. **slotted_mounting_plate** | 设备安装 | 多长槽、多孔、沉孔 | 易
23. **l_bracket** | 机械安装 | L 型体、双面孔 | 易
24. **u_bracket** | 轴/轮支撑 | U 槽、双侧孔、对称壁 | 中
25. **gusseted_bracket** | 高刚性支撑 | L 支架、三角筋、孔 | 中
26. **locator_block_vgroove** | 工装定位 | V 槽、销孔、螺孔 | 中
27. **clamp_block** | 夹具 | 槽、压紧孔、导向面 | 中
28. **fixture_plate_grid** | 工装平台 | 孔阵列、定位孔、倒角 | 中
29. **vise_jaw_insert** | 夹持件 | 齿面/槽面、安装孔 | 中
30. **ribbed_support_block** | 设备支撑 | 厚底座、筋、安装孔 | 中

**例子**：`locator_block_vgroove` 很像真实夹具件，结构也很标准：矩形块 + V 槽 + 2 个销孔 + 2 个安装孔。

---

## 四、芯片厂 / 半导体设备 / 自动化设备

31. **wafer_stage_mount_plate** | 半导体设备 | 高精定位孔、沉孔、轻量化 pocket | 中
32. **vacuum_chuck_base** | 晶圆承载 | 圆板、孔阵列、中心孔、台阶 | 难
33. **end_effector_adapter** | 机械手末端 | 法兰、孔阵列、减重槽 | 中
34. **sensor_alignment_block** | 对位治具 | 斜面、孔、定位槽 | 中
35. **linear_guide_carriage_block** | 精密运动 | 导轨安装面、孔、台阶 | 中
36. **cable_chain_mount** | 自动化设备 | 固定板、U 槽、孔位 | 易
37. **vacuum_manifold_plate** | 真空系统 | 多通孔、接口孔、内腔 | 难
38. **process_chamber_window_frame** | 腔体附件 | 框体、开窗、法兰孔 | 中
39. **nozzle_holder** | 点胶/喷射设备 | 细孔、夹持槽、固定孔 | 中
40. **alignment_fixture_frame** | 半导体夹具 | 外框、定位孔、内窗、支撑耳 | 中

---

## 五、传动 / 回转 / 标准机械件

41. **round_flange** | 通用机械 | 圆法兰、中心孔、螺栓孔圆阵 | 易
42. **rectangular_flange** | 管路/安装 | 矩形法兰、孔阵列、中心通孔 | 易
43. **shaft_collar** | 轴系 | 环、开口、紧固孔、倒角 | 中
44. **spacer_ring** | 机械装配 | 内外圆、倒角 | 易
45. **timing_pulley** | 传动件 | 轮体、中心孔、轮毂、齿/槽 | 难
46. **spur_gear_hub** | 齿轮 | 齿、中心孔、轮毂 | 难
47. **sprocket_plate** | 链传动 | 齿形轮廓、中心孔、孔阵列 | 难
48. **bearing_retainer_cap** | 轴承端盖 | 圆盘、孔阵列、中心孔、台阶 | 中
49. **bushing_sleeve** | 衬套 | 回转体、内孔、倒角 | 易
50. **coupling_hub** | 联轴器 | 轮毂、轴孔、紧固孔、沉头孔 | 中

---

# 这 50 个里，最推荐优先实现的 15 个

如果你要先做第一批模板，我建议先上这 15 个，最稳：

1. mounting_plate
2. slotted_mounting_plate
3. l_bracket
4. u_bracket
5. gusseted_bracket
6. round_flange
7. rectangular_flange
8. spacer_ring
9. shaft_collar
10. pcb_standoff_plate
11. connector_faceplate
12. electronics_enclosure_basic
13. electronics_enclosure_vented
14. locator_block_vgroove
15. bearing_retainer_cap

这批的好处是：

* **工业味足**
* **CadQuery 很好写**
* 覆盖很多高价值操作：

  * box
  * circle
  * rect
  * extrude
  * cut
  * hole
  * rarray / polar array
  * faces / workplane
  * fillet / chamfer
  * shell

---

# 如果你要做 difficulty 分层

可以直接这么分：

## Easy

* mounting_plate
* round_flange
* spacer_ring
* rectangular_flange
* l_bracket
* control_box_lid
* fan_guard_panel
* pcb_standoff_plate

## Medium

* slotted_mounting_plate
* u_bracket
* gusseted_bracket
* connector_faceplate
* bearing_seat_housing
* cable_routing_panel
* clamp_block
* bearing_retainer_cap
* coupling_hub
* cable_chain_mount

## Hard

* electronics_enclosure_vented
* sensor_housing_pod
* coolant_manifold_block
* vacuum_chuck_base
* vacuum_manifold_plate
* timing_pulley
* spur_gear_hub
* sprocket_plate
* motor_end_cap
* sensor_alignment_block

---

# 你们后面做 metadata 时，建议每个 case 再挂这些 tag

这样方便 benchmark 和 agent 控制分布：

* `has_hole`
* `has_slot`
* `has_pattern`
* `has_shell`
* `has_fillet`
* `has_chamfer`
* `has_bore`
* `has_pocket`
* `has_rib`
* `thin_wall`
* `rotational`
* `multi_stage`
* `symmetric_result`

注意这里 `symmetric_result` 是**结果是否对称**，不是代码里有没有用 mirror。

---

# 最后一个建议

不要把这 50 个都当成“独立代码模板”。
更好的做法是把它们归成 **10 个母 family**，每个母 family 再出 3 到 8 个子类。

比如：

* `plate_family` → mounting_plate / slotted_plate / fixture_plate / faceplate
* `bracket_family` → L / U / gusseted / sensor bracket
* `flange_family` → round / rectangular / bearing cap / adapter flange
* `enclosure_family` → basic / vented / connector cover / sensor pod
* `rotational_family` → spacer / collar / bushing / hub / pulley / gear

这样 Claude Code 更容易搭 agent。

**例子**：
`round_flange`、`bearing_retainer_cap`、`motor_end_cap` 其实都可以挂在一个 `flange_rotational_family` 下面，共享：

* 中心孔
* 螺栓孔阵列
* 台阶
* 倒角/圆角