# 合成数据集科学性改进方案

## 当前状态评估

### 科学依据来源
- NASA PDS Atmospheres Node (https://pds-atmospheres.nmsu.edu/)
- NASA Mars Fact Sheet
- ESA Venus Express 数据
- Rosetta 67P/C-G ROSINA 质谱数据
- NOAA 全球大气监测

### 已使用的科学数据

| 行星 | 气体 | 数值 | 来源 |
|------|------|------|------|
| Mars | CO₂ | 95.32% | NASA |
| Mars | CH₄ | 0.41 ppb (基线) | MSL Curiosity TLS |
| Venus | CO₂ | 96.5% | NASA |
| Venus | SO₂ | 150 ppm | Venus Express |
| Venus | PH₃ | <0.5-20 ppb (争议) | Greaves et al. 2020 |
| Venus | H₂S | 3-1000 ppb | Venus Express |
| Comet | H₂S | 1.5% | Rosetta ROSINA |
| Comet | CH₄ | 0.5% | Rosetta ROSINA |
| Earth | CH₄ | 1900 ppb | NOAA |
| Earth | CO₂ | 420 ppm | NOAA |

## 当前局限性

### 1. 传感器模型简化
**问题**: 使用简单对数响应模型
```python
# 当前简化模型
response = (log10(conc) - log10(min)) / (log10(max) - log10(min))
```

**改进**: 应使用真实传感器标定曲线
```python
# 理想模型 (需要实验数据)
# MQ-4 甲烷传感器实际响应曲线
Rs_R0 = a * (ppm ** b)  # 幂律响应
# 其中 a, b 需要从数据手册或实验获取
```

### 2. 环境因素缺失
**问题**: 未考虑温度、压力、湿度影响

| 环境 | 地球 | 火星 | 金星 |
|------|------|------|------|
| 压力 (kPa) | 101.3 | 0.636 | 9200 |
| 温度 (K) | 288 | 210 | 737 |
| 湿度 | 变化 | 极低 | H₂SO₄云 |

**改进**: 添加环境校正因子
```python
# 温度校正
T_correction = exp(-Ea / (R * T))

# 压力校正 (气体扩散)
P_correction = (P / P_ref) ** 0.5
```

### 3. 交叉敏感性数据
**问题**: 基于估计值，非实验数据

**改进**: 使用传感器数据手册的实际交叉敏感性图

## 建议的改进路径

### Phase 1: 短期改进 (可立即实施)
1. 使用真实 MQ 传感器数据手册参数
2. 添加更多行星大气论文引用
3. 增加数据不确定性标注

### Phase 2: 中期改进 (需要实验)
1. 实验室标定传感器响应曲线
2. 测量交叉敏感性矩阵
3. 环境因素影响测试

### Phase 3: 长期改进 (需要真实任务数据)
1. 使用 CubeSat 在轨数据微调
2. 与地面验证实验对比
3. 迁移学习整合多源数据

## 参考文献

1. Mumma, M. J., et al. (2009). "Strong Release of Methane on Mars in Northern Summer 2003." Science, 323(5917), 1041-1045.

2. Webster, C. R., et al. (2018). "Background levels of methane in Mars' atmosphere show strong seasonal variations." Science, 360(6393), 1093-1096.

3. Greaves, J. S., et al. (2020). "Phosphine gas in the cloud decks of Venus." Nature Astronomy, 5, 655-664. [争议性论文]

4. Snellen, I. A. G., et al. (2020). "Re-analysis of the 267 GHz ALMA observations of Venus." Astronomy & Astrophysics, 644, L2.

5. Le Roy, L., et al. (2015). "Inventory of the volatiles on comet 67P/Churyumov-Gerasimenko from Rosetta/ROSINA." Astronomy & Astrophysics, 583, A1.

6. Figaro Engineering Inc. MQ-4 Technical Data Sheet.

7. NASA Planetary Data System. Mars Atmospheric Data Sets. https://pds-atmospheres.nmsu.edu/

## 结论

当前合成数据集的**气体浓度参数具有科学依据**，但**传感器响应模型需要改进**。

建议将合成数据集定位为：
- ✅ 算法开发和初步验证的工具
- ✅ 模型架构测试
- ⚠️ 不能直接用于科学结论
- ⚠️ 需要真实传感器数据进行最终验证
