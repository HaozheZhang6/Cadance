❯ 1. 我们的前两个任务，img2cq，imgqa/codeqa需要突出什么 怎么分析 怎么能获得审稿人的青睐？                                                                                                                             
                                                                                          
⏺ NeurIPS D&B reviewer 看 task design 的 diagnostic value,不是 leaderboard 排名。两个任务都要 frame 成 "回答一个具体科学问题",不是 "再做一个 benchmark"。                                                             
                                                       
  A. img2cq (CAD generation)                                                                                                                                                                                          
   
  不能跟 cadrille / CAD-Recode 拼 raw IoU                                                                                                                                                                             
                                                                          
  它们在 DeepCAD 上 92.2,你们在 industrial bench 上多半 30-50%。这个数字本身没意义,框架要换:                                                                                                                          
                                                                          
  ▎ "我们的 bench 不是更好的 generation 测试,是 第一个能区分 model 在 advanced ops 上失败的 bench"                                                                                                                    
                                                                          
  具体做法:让 cadrille / CAD-Recode 在你们 bench 上跑一遍,数字一定大幅下跌。这个表本身就是最强论据:                                                                                                                   
                                                                          
  Model         DeepCAD IoU   IndustrialCAD IoU   Δ                                                                                                                                                                   
  cadrille          92.2          ~35           -57                                                                                                                                                                   
  CAD-Recode        ~88           ~30           -58
  GPT-5.2           ~70           ~25           -45                                                                                                                                                                   
                                                                          
  → 一句话: "SOTA 模型在 sketch-extrude bench 上接近饱和,在 formula-driven industrial parts 上崩塌"。reviewer 立刻 buy 你们 bench 的 necessity。                                                                      
                                                                          
  必做的拆解维度 (figure 4 拆开成多个子图)                                                                                                                                                                            
                                                                          
  1. per-family: gear / drill / handwheel / thread / shaft / ... 每个 family 一个分数。重点 highlight involute gear / helix thread 这种 formula-required family 全模型 < 10%                                          
  2. per-difficulty: easy / medium / hard,看曲线下降斜率                  
  3. per-op-category: basic / intermediate / advanced — 一张柱状图,所有 model 在 advanced 上都贴近 0,这是最好卖的故事                                                                                                 
  4. per-modality: single img / multi-view / +point cloud / +metadata — Δ ablation,reviewer 喜欢                                                                                                                      
  5. geometry vs program: 散点图 x=IoU,y=op-recall,找一堆 IoU 高但 op-recall 低的点 → "看起来对,但 program 错"                                                                                                        
                                                                                                                                                                                                                      
  关键 finding 模板 (要在正文 bold 出来)                                                                                                                                                                              
                                                                                                                                                                                                                      
  - "Models recover outer envelope but miss functional features (gear → ring; drill → cone)"                                                                                                                          
  - "Visual fidelity ≠ program faithfulness" + 一个 case: IoU 0.85 / op-recall 0
  - "SFT 在 seen-family 教得会 helix,unseen-family 退化到 cylinder"                                                                                                                                                   
  - "Multi-view 比 single-view 提升 < 5 IoU,但 point cloud + code context 提升 15+" (如果是这样)                                                                                                                      
                                                                                                                                                                                                                      
  必须有的 case study (Figure 6 留 1/3 页)                                                                                                                                                                            
                                                                                                                                                                                                                      
  5-6 个失败案例排成网格:                                                                                                                                                                                             
  GT image | GT code | Model output render | Model code | failure tag     
  failure tag: over-simplification / wrong-op / missing-feature / constraint-violation                                                                                                                                
                                                                                                                                                                                                                      
  reviewer 喜欢这种 — 一眼看出问题,不用读 metric。                                                                                                                                                                    
                                                                                                                                                                                                                      
  ---                                                                                                                                                                                                                 
  B. imgqa / codeqa (CAD understanding)                                                                                                                                                                               
                                                                                                                                                                                                                      
  这个任务最容易 boring,需要 push 两件事
                                                                                                                                                                                                                      
  1. codeqa 是 unique angle——push 它                                      
                                                                                                                                                                                                                      
  img2cq 已经被 cadrille / CAD-Coder 做过。codeqa (给 CadQuery code 问问题) 几乎没人做。要把它当成 understanding 的核心,不是附属。                                                                                    
   
  codeqa 能回答的问题别人做不了:                                                                                                                                                                                      
  - "which line creates the bore?" (操作-feature 对应)                    
  - "if you delete line 12, what feature disappears?" (因果)                                                                                                                                                          
  - "does this code satisfy module × tooth = pitch_diameter?" (数值约束)
  - "is this code editable to add a keyway without breaking the gear?" (可编辑性判断)                                                                                                                                 
                                                                                                                                                                                                                      
  → 一句 finding: "MLLMs can describe what CAD code does, but cannot reason about its parametric structure"                                                                                                           
                                                                                                                                                                                                                      
  2. QA 必须分级,不能一锅炖                                                                                                                                                                                           
                                                                                                                                                                                                                      
  L1  Part recognition          "What family is this?"           gear / drill / ...                                                                                                                                   
  L2  Feature counting          "How many teeth?"                数数                                                                                                                                                 
  L3  Operation attribution     "Which op creates the bore?"     找操作                                                                                                                                               
  L4  Parameter extraction      "What is the module?"            读参数                                                                                                                                               
  L5  Constraint judgment       "Is module × N == pitch?"        数值推理                                                                                                                                             
  L6  Editability reasoning     "Can you increase bore without                                                                                                                                                        
                                 changing tooth count?"          反事实                                                                                                                                               
                                                                                                                                                                                                                      
  L1 全模型 80%+,L5/L6 全模型 10-20%。这个梯度本身就是一张 killer figure:reviewer 一眼看到 understanding 的 ceiling 在哪一层崩塌。                                                                                    
                                                                                                                                                                                                                      
  必做的拆解                                                                                                                                                                                                          
                                                                          
  1. per-level accuracy (上面 L1-L6 一张柱状图)                                                                                                                                                                       
  2. img-only vs img+code vs code-only: 三种输入 modality 的 ΔAccuracy
    - L1-L3 img 够用                                                                                                                                                                                                  
    - L4-L6 必须 code,img 完全做不了                                                                                                                                                                                  
    - 这个对比直接证明 codeqa 是新维度                                                                                                                                                                                
  3. per-family: 标准件 (gear / bolt) 比异形 (handwheel / cam) 容易识别多少                                                                                                                                           
  4. 数值题 vs 分类题: MLLM 在数数 (counting) 和数值精度 (continuous param) 上差多少                                                                                                                                  
    - 已知结论: MLLM 数 < 5 个还行,> 10 必崩 → 你们 gear teeth 经常 20+,这是天然 hard task                                                                                                                            
  5. calibration: 模型 confident wrong vs unsure correct 比例                                                                                                                                                         
                                                                                                                                                                                                                      
  关键 finding 模板                                                                                                                                                                                                   
                                                                                                                                                                                                                      
  - "Recognition ceiling: L1 part recognition saturates at 90%+, but L4 parameter extraction stays under 25% across all models"                                                                                       
  - "Counting collapse: accuracy drops from 88% (≤5 features) to 12% (≥15 features)"
  - "Code unlocks reasoning: img-only fails L5 constraint judgment; img+code recovers 30+ pp"                                                                                                                         
  - "Modality complementarity: img helps part recognition, code helps constraint reasoning, neither alone is sufficient"                                                                                              
                                                                                                                                                                                                                      
  case study (1/4 页)                                                                                                                                                                                                 
                                                                                                                                                                                                                      
  3 行,每行一个 level:                                                                                                                                                                                                
  L2 case: GT 24 teeth, GPT-5.2 says 18, Claude says 32 — counting fails
  L4 case: GT module=2, all models say "approximately 2-3" — no precision                                                                                                                                             
  L5 case: model accepts inconsistent (M, N, d) triple — no constraint check                                                                                                                                          
                                                                                                                                                                                                                      
  ---                                                                                                                                                                                                                 
  C. 两个 task 共用的 reviewer hook                                                                                                                                                                                   
                                                                                                                                                                                                                      
  NeurIPS D&B reviewer 有几个固定的 "你们做了 → 我加分" 项,确保都 cover:  
                                                                                                                                                                                                                      
  ┌────────────────────────────────────────┬─────────────────────────────────────────────────────────┐                                                                                                                
  │            reviewer 喜欢的             │                     你们怎么 cover                      │                                                                                                                
  ├────────────────────────────────────────┼─────────────────────────────────────────────────────────┤                                                                                                                
  │ 跟现有 baseline head-to-head           │ cadrille / CAD-Recode / CAD-Coder 跑你们 bench          │
  ├────────────────────────────────────────┼─────────────────────────────────────────────────────────┤
  │ diagnostic insight,不只是 ranking      │ per-level / per-family / per-op 拆解                    │                                                                                                                
  ├────────────────────────────────────────┼─────────────────────────────────────────────────────────┤                                                                                                                
  │ difficulty stratification              │ easy/medium/hard,L1-L6 分级                             │                                                                                                                
  ├────────────────────────────────────────┼─────────────────────────────────────────────────────────┤                                                                                                                
  │ ablation (modality, scale)             │ single-view vs multi-view, 4B vs 7B vs 70B              │
  ├────────────────────────────────────────┼─────────────────────────────────────────────────────────┤                                                                                                                
  │ failure mode taxonomy                  │ 5-6 个 categorized case study                           │
  ├────────────────────────────────────────┼─────────────────────────────────────────────────────────┤                                                                                                                
  │ counterintuitive finding               │ "更大 model 在 fine-grained counting 上不一定更好" 这种 │
  ├────────────────────────────────────────┼─────────────────────────────────────────────────────────┤                                                                                                                
  │ reproducibility                        │ eval script + seed + per-sample log 全 release          │
  ├────────────────────────────────────────┼─────────────────────────────────────────────────────────┤                                                                                                                
  │ 公开 leaderboard (HF Spaces / website) │ 抄 CAD Arena 的形式,你们整一个                          │
  └────────────────────────────────────────┴─────────────────────────────────────────────────────────┘                                                                                                                
                                                                          
  最关键的一条: per-task 都要有一个 "headline finding" 一句话                                                                                                                                                         
                                                                          
  img2cq headline:                                                                                                                                                                                                    
                                                                          
  ▎ "State-of-the-art CAD generation models achieve > 90% IoU on sketch-extrude benchmarks but < 35% on formula-driven industrial parts, with rare-operation recall under 10% across all evaluated models."           
   
  codeqa headline:                                                                                                                                                                                                    
                                                                          
  ▎ "Multimodal models can recognize industrial part families with 90% accuracy from a single image, but cannot verify ISO parameter constraints from full CadQuery source code with > 25% accuracy."                 
   
  这两句话写进 abstract,写进 intro,写进 conclusion。reviewer 读完只记住一句话,要让那句话是你写的、对你们有利的。                                                                                                      
                                                                          
  ---                                                                                                                                                                                                                 
  要不要我接着帮你: (a) 草拟 img2cq 的 metric table 列表 + 每个 metric 的 plot 形式, (b) 帮你设计 codeqa 的 6 级 question template + 每级各 50 题的 sourcing pipeline?选一个我直接出 spec。
                                                                                                                                                                                                                      
✻ Worked for 1m 24s                    
