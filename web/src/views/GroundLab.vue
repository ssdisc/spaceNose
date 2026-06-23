<template>
  <div class="lab">
    <header class="lab-head">
      <div class="title">
        <p class="eyebrow">Year 1 · Ground Verification</p>
        <h2>地面验证实验台</h2>
        <p class="lead">
          用于展示原理样机数据、模拟气体探测流程、告警阈值与导出报告（PDF/Excel），便于演示效果与复现实验。
        </p>
      </div>
      <div class="head-actions">
        <el-tag :type="modeTagType" effect="dark">{{ modeTagText }}</el-tag>
        <el-tag v-if="mode === 'realtime'" :type="wsConnected ? 'success' : 'info'" effect="plain">
          {{ wsConnected ? 'WebSocket 已连接' : 'WebSocket 未连接' }}
        </el-tag>
        <el-button type="primary" @click="$router.push('/visualization')">打开实时监控页</el-button>
      </div>
    </header>

    <el-row :gutter="10">
      <el-col :xs="24" :lg="12">
        <el-card class="glass panel" shadow="hover">
          <template #header>
            <div class="panel-title">实验控制台</div>
          </template>

          <el-form label-position="top" class="form">
            <el-form-item label="数据来源">
              <el-radio-group v-model="mode" @change="onModeChange">
                <el-radio-button label="simulation">模拟实验</el-radio-button>
                <el-radio-button label="realtime">对接后端</el-radio-button>
              </el-radio-group>
            </el-form-item>

            <el-form-item v-if="mode === 'simulation'" label="场景预设">
              <el-select v-model="scenario" placeholder="请选择场景" @change="applyScenarioPreset">
                <el-option
                  v-for="item in scenarioOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>

            <!-- 场景科学信息面板 -->
            <div v-if="mode === 'simulation' && currentScenarioInfo" class="scenario-info-panel">
              <div class="scenario-info-header">
                <span class="scenario-name">{{ currentScenarioInfo.name }}</span>
                <el-tag v-if="currentScenarioInfo.keyGas" size="small" type="warning">
                  关键气体: {{ getGasLabel(currentScenarioInfo.keyGas) }}
                </el-tag>
              </div>
              <div class="scenario-info-goal">
                <span class="goal-label">科学目标:</span> {{ currentScenarioInfo.goal }}
              </div>
              <div v-if="currentScenarioInfo.note" class="scenario-info-note">
                <span class="note-label">特征:</span> {{ currentScenarioInfo.note }}
              </div>
              <div v-if="currentScenarioInfo.source" class="scenario-info-source">
                <span class="source-label">数据来源:</span> {{ currentScenarioInfo.source }}
              </div>
            </div>

            <el-form-item label="采样频率 (Hz)">
              <el-slider v-model="sampleHz" :min="0.2" :max="5" :step="0.2" show-input />
            </el-form-item>

            <el-form-item v-if="mode === 'simulation'" label="温度 (°C)">
              <el-slider v-model="temperatureC" :min="-20" :max="60" :step="1" show-input />
            </el-form-item>

            <el-form-item v-if="mode === 'simulation'" label="噪声强度 (%)">
              <el-slider v-model="noisePercent" :min="0" :max="20" :step="1" show-input />
            </el-form-item>

            <el-form-item v-if="mode === 'simulation'" label="漂移强度 (‰/min)">
              <el-slider v-model="driftPermillePerMin" :min="0" :max="10" :step="0.5" show-input />
            </el-form-item>

            <el-form-item v-if="mode === 'simulation'" label="交叉干扰（演示用）">
              <el-switch v-model="enableInterference" active-text="开启" inactive-text="关闭" />
            </el-form-item>

            <div class="btn-row">
              <template v-if="mode === 'simulation'">
                <el-button type="primary" :disabled="simulationRunning" @click="startSimulation">开始模拟</el-button>
                <el-button :disabled="!simulationRunning" @click="stopSimulation">停止</el-button>
              </template>
              <template v-else>
                <el-button
                  type="primary"
                  :disabled="wsConnected || wsConnecting"
                  @click="connectWs"
                >{{ wsConnecting ? '连接中…' : '连接 WebSocket' }}</el-button>
                <el-button :disabled="!wsConnected" @click="disconnectWs">断开</el-button>
              </template>
              <el-button @click="resetData">清空数据</el-button>
            </div>

            <el-divider />

            <!-- 使用 Tabs 分组折叠面板 -->
            <el-tabs v-model="settingsTab" type="border-card" class="settings-tabs">
              <el-tab-pane label="配置" name="config">
                <el-collapse accordion>
                  <el-collapse-item title="后端字段映射" name="mapping">
                <el-form-item label="来源字段">
                  <el-select v-model="realtimeSourceField">
                    <el-option label="alcohol_ppm" value="alcohol_ppm" />
                    <el-option label="co2_ppm" value="co2_ppm" />
                    <el-option label="voltage" value="voltage" />
                    <el-option label="adc" value="adc" />
                  </el-select>
                </el-form-item>
                <el-form-item label="映射到气体">
                  <el-select v-model="realtimeMapGas">
                    <el-option v-for="gas in gases" :key="gas.key" :label="gas.label" :value="gas.key" />
                  </el-select>
                </el-form-item>
                <el-form-item label="缩放倍率">
                  <el-input-number v-model="realtimeScale" :min="0" :step="0.1" :precision="2" />
                </el-form-item>
                <div class="hint">
                  当前硬件若只有单通道（如 MQ-3），可将其映射到任意气体曲线用于演示；其余气体保持为空。
                </div>
              </el-collapse-item>

              <el-collapse-item title="自定义基线（仅模拟）" name="baseline">
                <div class="grid-2">
                  <el-form-item v-for="gas in gases" :key="gas.key" :label="`${gas.label} 基线 (${gas.unit})`">
                    <el-input-number
                      v-model="baseline[gas.key]"
                      :min="0"
                      :step="gas.unit === 'ppb' ? 1 : 0.1"
                      :precision="gas.unit === 'ppb' ? 0 : 2"
                      :disabled="scenario !== 'custom'"
                    />
                  </el-form-item>
                </div>
                <div class="hint">选择“自定义”场景后可编辑基线。</div>
              </el-collapse-item>

              <el-collapse-item title="阈值告警" name="thresholds">
                <div class="grid-2">
                  <el-form-item v-for="gas in gases" :key="gas.key" :label="`${gas.label} 预警阈值`">
                    <el-input-number
                      v-model="thresholds[gas.key].warning"
                      :min="0"
                      :step="gas.unit === 'ppb' ? 1 : 0.1"
                      :precision="gas.unit === 'ppb' ? 0 : 2"
                    />
                  </el-form-item>
                  <el-form-item v-for="gas in gases" :key="`${gas.key}-d`" :label="`${gas.label} 危险阈值`">
                    <el-input-number
                      v-model="thresholds[gas.key].danger"
                      :min="0"
                      :step="gas.unit === 'ppb' ? 1 : 0.1"
                      :precision="gas.unit === 'ppb' ? 0 : 2"
                    />
                  </el-form-item>
                </div>
              </el-collapse-item>

              <el-collapse-item title="异常注入（仅模拟）" name="anomaly">
                <el-form-item label="目标气体">
                  <el-select v-model="anomaly.gasKey">
                    <el-option v-for="gas in gases" :key="gas.key" :label="gas.label" :value="gas.key" />
                  </el-select>
                </el-form-item>
                <el-form-item label="倍数">
                  <el-input-number v-model="anomaly.multiplier" :min="1" :step="0.5" :precision="1" />
                </el-form-item>
                <el-form-item label="持续 (秒)">
                  <el-input-number v-model="anomaly.durationSec" :min="1" :step="1" />
                </el-form-item>
                <el-button type="danger" plain :disabled="mode !== 'simulation'" @click="injectAnomaly">
                  注入异常
                </el-button>
                <div class="hint">用于演示星上异常检测触发高采样/下传关键片段的效果。</div>
              </el-collapse-item>
                </el-collapse>
              </el-tab-pane>

              <el-tab-pane label="测试" name="test">
                <el-collapse accordion>
                  <el-collapse-item title="测试用例管理" name="testcases">
                <div class="hint">预定义测试场景，自动执行并验证ML模型的预测结果。</div>

                <div class="test-actions">
                  <el-button
                    size="small"
                    type="primary"
                    :loading="testRunning"
                    :disabled="mode !== 'simulation'"
                    @click="runAllTests"
                  >运行全部测试</el-button>
                  <el-button size="small" @click="resetTestResults">清除结果</el-button>
                </div>

                <el-progress
                  v-if="testRunning"
                  :percentage="testProgress"
                  :format="() => `${Math.round(testProgress)}%`"
                  style="margin: 10px 0;"
                />

                <div class="test-list">
                  <div
                    v-for="tc in testCases"
                    :key="tc.id"
                    class="test-item"
                    :class="{ 'test-running': currentTestId === tc.id }"
                  >
                    <div class="test-item-header">
                      <span class="test-name">{{ tc.name }}</span>
                      <div class="test-item-actions">
                        <el-tag size="small" effect="plain">{{ SCENARIO_INFO[tc.scenario]?.name || tc.scenario }}</el-tag>
                        <el-tag
                          v-if="testResults[tc.id]"
                          size="small"
                          :type="testResults[tc.id].passed ? 'success' : 'danger'"
                        >
                          {{ testResults[tc.id].passed ? '通过' : '失败' }}
                        </el-tag>
                        <el-button
                          size="small"
                          text
                          :loading="currentTestId === tc.id"
                          :disabled="testRunning && currentTestId !== tc.id"
                          @click="runSingleTest(tc)"
                        >运行</el-button>
                      </div>
                    </div>
                    <div class="test-item-detail">
                      <span v-if="tc.anomaly">异常: {{ getGasLabel(tc.anomaly.gasKey) }} ×{{ tc.anomaly.multiplier }}</span>
                      <span v-else>无异常注入</span>
                      <span>期望: {{ tc.expected.label }} (≥{{ tc.expected.minConfidence * 100 }}%)</span>
                    </div>
                    <div v-if="testResults[tc.id] && !testResults[tc.id].passed" class="test-error">
                      实际: {{ testResults[tc.id].actual?.label || '无' }}
                      ({{ ((testResults[tc.id].actual?.confidence || 0) * 100).toFixed(1) }}%)
                    </div>
                  </div>
                </div>
              </el-collapse-item>
                </el-collapse>
              </el-tab-pane>

              <el-tab-pane label="机器学习" name="ml">
                <el-collapse accordion>
                  <el-collapse-item title="场景识别（传统ML）" name="ml">
                <div class="hint">
                  使用前端模拟数据（ch4/ph3/so2/h2s/co2/vocs）上传训练集并训练模型；硬件多气体接入后可直接复用。
                </div>
                <div class="ml-actions">
                  <el-button size="small" :loading="mlLoading" @click="refreshMlStatus">刷新状态</el-button>
                  <el-button
                    size="small"
                    type="primary"
                    :disabled="mode !== 'simulation'"
                    :loading="mlUploading"
                    @click="uploadScenarioSample"
                  >上传样本</el-button>
                  <el-button size="small" type="warning" :loading="mlTraining" @click="trainScenarioModel">
                    训练模型
                  </el-button>
                  <el-button size="small" type="success" :loading="mlPredicting" @click="predictScenario">
                    预测当前
                  </el-button>
                </div>

                <div v-if="mlError" class="ml-error">{{ mlError }}</div>

                <div v-if="mlStatus" class="ml-grid">
                  <div class="ml-kv">
                    <span>ML 可用</span>
                    <el-tag :type="mlStatus.ml_available ? 'success' : 'danger'" effect="plain" size="small">
                      {{ mlStatus.ml_available ? 'Yes' : 'No' }}
                    </el-tag>
                  </div>
                  <div class="ml-kv">
                    <span>数据集条数</span>
                    <span class="ml-value">{{ mlStatus.scenario.dataset_count }}</span>
                  </div>
                  <div class="ml-kv">
                    <span>模型状态</span>
                    <el-tag
                      :type="mlStatus.scenario.model.enabled ? 'success' : 'info'"
                      effect="plain"
                      size="small"
                    >{{ mlStatus.scenario.model.enabled ? '已训练' : '未训练' }}</el-tag>
                  </div>
                  <div class="ml-kv">
                    <span>训练时间</span>
                    <span class="ml-value">{{ mlStatus.scenario.model.trained_at || '—' }}</span>
                  </div>
                </div>

                <div v-if="mlPrediction && mlPrediction.ok" class="ml-result">
                  <el-tag type="success" effect="dark" size="small">预测</el-tag>
                  <span class="ml-result-text">
                    {{ mlPrediction.label }}（置信度 {{ (mlPrediction.confidence * 100).toFixed(1) }}%）
                  </span>
                </div>
                <div v-else-if="mlPrediction && !mlPrediction.ok" class="ml-result">
                  <el-tag type="info" effect="plain" size="small">预测失败</el-tag>
                  <span class="ml-result-text">{{ mlPrediction.error }}</span>
                </div>

                <div class="hint" v-if="mode !== 'simulation'">
                  当前处于“对接后端”模式，多气体特征不足；请先切回“模拟实验”上传训练样本。
                </div>
              </el-collapse-item>

              <el-collapse-item title="机器学习（传感器阵列分类）" name="enose">
                <div class="hint">
                  使用电子鼻数据集（默认内置 ec-gcms-inference-dataset.csv）训练 delta 特征分类模型，演示“传感器阵列+模式识别”闭环。
                </div>
                <div class="ml-actions">
                  <el-button size="small" :loading="enoseLoading" @click="refreshMlStatus">刷新状态</el-button>
                  <el-button size="small" type="warning" :loading="enoseTraining" @click="trainEnoseModel">
                    训练阵列模型
                  </el-button>
                  <el-button size="small" type="primary" :loading="enoseSampling" @click="sampleEnoseDataset">
                    随机抽样
                  </el-button>
                  <el-button size="small" type="success" :loading="enosePredicting" @click="predictEnose">
                    预测该样本
                  </el-button>
                </div>

                <div v-if="enoseError" class="ml-error">{{ enoseError }}</div>

                <div v-if="enoseStatus" class="ml-grid">
                  <div class="ml-kv">
                    <span>默认数据集</span>
                    <el-tag
                      :type="enoseStatus.dataset_exists_default ? 'success' : 'danger'"
                      effect="plain"
                      size="small"
                    >{{ enoseStatus.dataset_exists_default ? '已就绪' : '缺失' }}</el-tag>
                  </div>
                  <div class="ml-kv">
                    <span>模型状态</span>
                    <el-tag
                      :type="enoseStatus.model.enabled ? 'success' : 'info'"
                      effect="plain"
                      size="small"
                    >{{ enoseStatus.model.enabled ? '已训练' : '未训练' }}</el-tag>
                  </div>
                  <div class="ml-kv">
                    <span>类别</span>
                    <span class="ml-value">{{ (enoseStatus.model.classes || []).join(', ') || '—' }}</span>
                  </div>
                  <div class="ml-kv">
                    <span>训练时间</span>
                    <span class="ml-value">{{ enoseStatus.model.trained_at || '—' }}</span>
                  </div>
                </div>

                <div v-if="enoseTrainResult && enoseTrainResult.trained" class="ml-grid mt-10">
                  <div class="ml-kv">
                    <span>测试准确率</span>
                    <span class="ml-value">{{ formatNumber(enoseTrainResult.test_accuracy * 100, 1) }}%</span>
                  </div>
                  <div class="ml-kv">
                    <span>Macro-F1</span>
                    <span class="ml-value">{{ formatNumber(enoseTrainResult.test_macro_f1, 3) }}</span>
                  </div>
                  <div class="ml-kv">
                    <span>类别数</span>
                    <span class="ml-value">{{ enoseTrainResult.classes.length }}</span>
                  </div>
                  <div class="ml-kv">
                    <span>样本数</span>
                    <span class="ml-value">{{ enoseTrainResult.sample_count }}</span>
                  </div>
                </div>

                <div v-if="enoseTrainResult && enoseTrainResult.confusion_matrix?.length" class="ml-section">
                  <div class="section-title">混淆矩阵（测试集）</div>
                  <el-table :data="confusionRows" size="small" border>
                    <el-table-column prop="label" label="True \\ Pred" width="140" />
                    <el-table-column
                      v-for="cls in enoseTrainResult.confusion_matrix_labels"
                      :key="cls"
                      :prop="cls"
                      :label="cls"
                      align="center"
                    />
                  </el-table>
                </div>

                <div v-if="enoseSample" class="ml-section">
                  <div class="section-title">样本特征（delta = stimulus - baseline）</div>
                  <el-descriptions :column="2" border size="small">
                    <el-descriptions-item v-for="(v, k) in enoseSample.features" :key="k" :label="k">
                      {{ v == null ? '—' : formatNumber(v, 6) }}
                    </el-descriptions-item>
                  </el-descriptions>
                  <div class="hint mt-8">
                    标签（基于 delta 最大通道）: <strong>{{ enoseSample.label }}</strong>
                  </div>
                </div>

                <div v-if="enosePrediction" class="ml-result mt-8">
                  <el-tag :type="enosePrediction.ok ? 'success' : 'info'" effect="dark" size="small">
                    预测
                  </el-tag>
                  <span class="ml-result-text" v-if="enosePrediction.ok">
                    {{ enosePrediction.label }}（{{ formatNumber(enosePrediction.confidence * 100, 1) }}%）
                  </span>
                  <span class="ml-result-text" v-else>
                    {{ enosePrediction.error || '预测失败' }}
                  </span>
                </div>
              </el-collapse-item>

              <!-- 深度学习训练与轻量化监控 -->
              <el-collapse-item title="深度学习模型（Year 1 轻量化）" name="dl">
                <div class="dl-panel">
                  <div class="panel-hint">
                    训练轻量化深度学习模型（1D-CNN + GRU），满足星上部署要求：模型 &lt; 100KB，推理 &lt; 100ms
                  </div>

                  <!-- 模型轻量化指标仪表盘 -->
                  <div class="metrics-dashboard">
                    <div class="metric-gauge" :class="{ 'metric-ok': dlMetrics.model_size_kb < 100 }">
                      <div class="gauge-value">{{ dlMetrics.model_size_kb?.toFixed(1) || '—' }}</div>
                      <div class="gauge-label">模型大小 (KB)</div>
                      <div class="gauge-target">目标 &lt; 100 KB</div>
                      <div class="gauge-bar">
                        <div class="gauge-fill" :style="{ width: Math.min((dlMetrics.model_size_kb || 0) / 100 * 100, 100) + '%' }"></div>
                      </div>
                    </div>
                    <div class="metric-gauge" :class="{ 'metric-ok': dlMetrics.inference_time_ms < 100 }">
                      <div class="gauge-value">{{ dlMetrics.inference_time_ms?.toFixed(2) || '—' }}</div>
                      <div class="gauge-label">推理时间 (ms)</div>
                      <div class="gauge-target">目标 &lt; 100 ms</div>
                      <div class="gauge-bar">
                        <div class="gauge-fill" :style="{ width: Math.min((dlMetrics.inference_time_ms || 0) / 100 * 100, 100) + '%' }"></div>
                      </div>
                    </div>
                    <div class="metric-gauge metric-accuracy">
                      <div class="gauge-value">{{ dlMetrics.accuracy ? (dlMetrics.accuracy * 100).toFixed(1) + '%' : '—' }}</div>
                      <div class="gauge-label">验证准确率</div>
                      <div class="gauge-target">F1 &gt; 0.92</div>
                      <div class="gauge-bar accuracy-bar">
                        <div class="gauge-fill" :style="{ width: (dlMetrics.accuracy || 0) * 100 + '%' }"></div>
                      </div>
                    </div>
                  </div>

                  <!-- 训练控制 -->
                  <div class="dl-actions">
                    <el-button size="small" @click="fetchDLMetrics" :loading="dlMetricsLoading">
                      刷新指标
                    </el-button>
                    <el-button size="small" type="warning" @click="trainDLSynthetic" :loading="dlTraining">
                      训练（合成数据）
                    </el-button>
                    <el-button size="small" type="primary" @click="predictWithDecision" :loading="dlPredicting" :disabled="mode !== 'simulation'">
                      智能决策预测
                    </el-button>
                  </div>

                  <!-- 训练进度 -->
                  <div v-if="dlTraining" class="training-progress">
                    <el-progress :percentage="dlTrainProgress" :stroke-width="10" :color="['#22d3ee', '#a855f7']" />
                    <div class="progress-text">训练中... {{ dlTrainProgress }}%</div>
                  </div>

                  <!-- 训练结果 -->
                  <div v-if="dlTrainResult" class="dl-train-result">
                    <div class="result-header">
                      <el-tag :type="dlTrainResult.trained ? 'success' : 'danger'" effect="dark">
                        {{ dlTrainResult.trained ? '训练成功' : '训练失败' }}
                      </el-tag>
                    </div>
                    <div v-if="dlTrainResult.trained" class="result-metrics">
                      <div class="result-item">
                        <span class="item-label">训练准确率</span>
                        <span class="item-value">{{ (dlTrainResult.train_accuracy * 100).toFixed(2) }}%</span>
                      </div>
                      <div class="result-item">
                        <span class="item-label">验证准确率</span>
                        <span class="item-value highlight">{{ (dlTrainResult.val_accuracy * 100).toFixed(2) }}%</span>
                      </div>
                      <div class="result-item">
                        <span class="item-label">模型大小</span>
                        <span class="item-value">{{ dlTrainResult.model_size_kb?.toFixed(2) }} KB</span>
                      </div>
                      <div class="result-item">
                        <span class="item-label">推理时间</span>
                        <span class="item-value">{{ dlTrainResult.inference_time_ms?.toFixed(2) }} ms</span>
                      </div>
                    </div>

                    <!-- 训练历史曲线图 -->
                    <div v-if="dlTrainResult.training_history" class="training-charts">
                      <div class="chart-title">训练监控曲线</div>
                      <v-chart class="training-chart" :option="trainingLossChartOption" autoresize />
                      <v-chart class="training-chart" :option="trainingAccuracyChartOption" autoresize />
                    </div>
                  </div>

                  <!-- 智能决策结果 -->
                  <div v-if="dlDecision" class="decision-panel">
                    <div class="decision-header">智能决策结果</div>
                    <div class="decision-content">
                      <!-- 分类结果 -->
                      <div class="decision-section">
                        <div class="section-label">场景分类</div>
                        <div class="classification-result">
                          <span class="class-label">{{ dlDecision.classification?.label || '—' }}</span>
                          <span class="class-confidence">{{ dlDecision.classification?.confidence ? (dlDecision.classification.confidence * 100).toFixed(1) + '%' : '' }}</span>
                        </div>
                      </div>

                      <!-- 决策类型 -->
                      <div class="decision-section">
                        <div class="section-label">决策</div>
                        <el-tag
                          :type="getDecisionTagType(dlDecision.decision?.action)"
                          effect="dark"
                          size="large"
                        >
                          {{ getDecisionText(dlDecision.decision?.action) }}
                        </el-tag>
                      </div>

                      <!-- 科学价值雷达图 -->
                      <div class="decision-section" v-if="dlDecision.decision">
                        <div class="section-label">科学价值评分</div>
                        <div class="science-score">
                          <div class="score-value">{{ (dlDecision.decision.scientific_value * 100).toFixed(0) }}</div>
                          <div class="score-label">/ 100</div>
                        </div>
                        <v-chart class="radar-chart" :option="decisionRadarOption" autoresize />
                      </div>
                    </div>
                  </div>
                </div>
              </el-collapse-item>
                </el-collapse>
              </el-tab-pane>
            </el-tabs>

            <el-divider />

            <div class="export-row">
              <el-button type="success" plain :disabled="points.length === 0" @click="exportXlsx">
                导出 Excel
              </el-button>
              <el-button type="warning" plain :disabled="points.length === 0" @click="exportPdf">
                生成 PDF 报告
              </el-button>
            </div>
          </el-form>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="12">
        <el-row :gutter="10">
          <el-col :xs="24" :sm="12" :md="8" v-for="gas in gasCards" :key="gas.key">
            <el-card shadow="hover" class="glass gas-card">
              <div class="gas-top">
                <div>
                  <div class="gas-label">{{ gas.label }}</div>
                  <div class="gas-unit">{{ gas.unit }}</div>
                </div>
                <el-tag :type="gas.tagType" effect="dark">{{ gas.statusText }}</el-tag>
              </div>
              <div class="gas-value">{{ gas.display }}</div>
              <div class="gas-sub">
                <span>预警 {{ thresholds[gas.key].warning }}</span>
                <span>危险 {{ thresholds[gas.key].danger }}</span>
              </div>
            </el-card>
          </el-col>
        </el-row>

        <el-row :gutter="10" class="section">
          <el-col :xs="24">
            <el-card shadow="hover" class="glass chart-card">
              <template #header>
                <div class="card-header-row">
                  <div>浓度曲线（ppm/ppb 双轴）</div>
                  <div class="small-meta">
                    <el-tag :type="samplingMode === 'high' ? 'danger' : 'success'" effect="plain">
                      {{ samplingMode === 'high' ? '高采样模式' : '常规模式' }}
                    </el-tag>
                    <span>点数：{{ points.length }}</span>
                  </div>
                </div>
              </template>
              <v-chart class="chart" :option="lineOption" autoresize />
            </el-card>
          </el-col>
        </el-row>

        <el-row :gutter="10" class="section">
          <el-col :xs="24">
            <el-card shadow="hover" class="glass chart-card">
              <template #header>
                <div class="card-header-row">
                  <div>星上决策（演示）</div>
                  <el-button text @click="clearEvents">清空事件</el-button>
                </div>
              </template>
              <div class="metric">
                <div class="metric-row">
                  <span class="metric-label">科学价值评分</span>
                  <span class="metric-value">{{ scienceScore }} / 100</span>
                </div>
                <el-progress :percentage="scienceScore" :status="scienceScore >= 70 ? 'exception' : 'success'" />
              </div>
              <div class="metric">
                <div class="metric-row">
                  <span class="metric-label">下传比例</span>
                  <span class="metric-value">{{ downlinkPercent }}%</span>
                </div>
                <el-progress :percentage="downlinkPercent" :color="downlinkPercent > 30 ? '#ef4444' : '#22c55e'" />
              </div>
              <div class="hint">
                常规模式默认“只下传 10%”，异常时切换高采样并提高下传比例，用于展示星上筛查与压缩策略。
              </div>
              <div class="mini-log">
                <div v-if="events.length === 0" class="empty">暂无事件</div>
                <div v-else class="mini-log-list">
                  <div v-for="evt in recentEvents" :key="evt.id" class="mini-log-item">
                    <el-tag :type="evt.tagType" size="small" effect="plain">{{ evt.type }}</el-tag>
                    <span class="mini-log-text">{{ evt.text }}</span>
                  </div>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import dayjs from 'dayjs'
import { use } from 'echarts/core'
import { LineChart, RadarChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent, TitleComponent, MarkLineComponent, VisualMapComponent, RadarComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import * as XLSX from 'xlsx'
import { jsPDF } from 'jspdf'
import { autoTable } from 'jspdf-autotable'

use([LineChart, RadarChart, GridComponent, LegendComponent, TooltipComponent, TitleComponent, MarkLineComponent, VisualMapComponent, RadarComponent, CanvasRenderer])

const GAS_META = [
  { key: 'ch4', label: '甲烷 CH₄', unit: 'ppm', axis: 0, color: '#22d3ee' },
  { key: 'ph3', label: '磷化氢 PH₃', unit: 'ppb', axis: 1, color: '#a855f7' },
  { key: 'so2', label: '二氧化硫 SO₂', unit: 'ppm', axis: 0, color: '#f59e0b' },
  { key: 'h2s', label: '硫化氢 H₂S', unit: 'ppm', axis: 0, color: '#ef4444' },
  { key: 'co2', label: '二氧化碳 CO₂', unit: 'ppm', axis: 0, color: '#3b82f6' },
  { key: 'vocs', label: 'VOCs', unit: 'ppb', axis: 1, color: '#cbd5e1' }
]

/**
 * 场景预设 - 基于 NASA/ESA 行星探测数据
 * 单位: ppm (百万分之一)
 * 数据来源:
 * - Mars: NASA Curiosity/TGO (CH4 季节性波动 0.24-0.65 ppb)
 * - Venus: ESA Venus Express (SO2 ~150 ppm, PH3 争议 ~20 ppb)
 * - Comet: ESA Rosetta/67P (H2S ~1.5%, CH4 ~0.5%)
 * - Titan: NASA Cassini (CH4 ~5%)
 * - Europa: 理论模型 (假设热液活动)
 * - Earth: NOAA 2023 (CH4 1.9 ppm, CO2 420 ppm)
 */
const SCENARIO_PRESETS = {
  // 火星大气 - 好奇号/TGO数据
  // 关键: CH4 是唯一潜在生物标志，浓度极低
  mars: { ch4: 0.0005, ph3: 0, so2: 0.001, h2s: 0.001, co2: 9500, vocs: 0.01 },

  // 金星云层 - 金星快车/先驱者数据
  // 关键: SO2 高, PH3 争议性探测 (Greaves et al. 2020)
  venus: { ch4: 0.001, ph3: 0.00002, so2: 150, h2s: 0.5, co2: 9600, vocs: 0.01 },

  // 彗星67P彗发 - Rosetta ROSINA数据
  // 关键: H2S 和 VOCs 丰富, 原始太阳系物质
  comet: { ch4: 500, ph3: 0.0001, so2: 10, h2s: 1500, co2: 1000, vocs: 2000 },

  // 木卫二 - 假设冰下海洋热液喷口
  // 关键: H2S 是热液活动标志 (理论推测)
  europa: { ch4: 0.1, ph3: 0, so2: 0.01, h2s: 10, co2: 50, vocs: 0.5 },

  // 土卫六 - 卡西尼-惠更斯数据
  // 关键: CH4 循环 (液态甲烷湖), 复杂有机物
  titan: { ch4: 50000, ph3: 0, so2: 0.001, h2s: 0.01, co2: 10, vocs: 500 },

  // 地球生命基线 - NOAA 2023
  // 关键: CH4 生物源, CO2 当前水平
  earth_life: { ch4: 1.9, ph3: 0.00001, so2: 0.005, h2s: 0.05, co2: 420, vocs: 0.5 },

  // 深空背景/仪器本底
  background: { ch4: 0.00001, ph3: 0, so2: 0.00001, h2s: 0.00001, co2: 0.1, vocs: 0.001 },

  custom: null
}

// 场景科学信息
const SCENARIO_INFO = {
  mars: {
    name: '火星大气',
    keyGas: 'ch4',
    goal: '检测 ppb 级 CH₄，区分生物源/地质源',
    source: 'NASA Curiosity SAM, ESA TGO',
    note: 'CH₄ 季节性波动 0.24-0.65 ppb，CO₂ 占 95%'
  },
  venus: {
    name: '金星云层',
    keyGas: 'so2',
    goal: '验证 PH₃ 争议探测，分析 SO₂/H₂SO₄',
    source: 'ESA Venus Express, Greaves 2020',
    note: 'SO₂ ~150 ppm，PH₃ ~20 ppb (争议)'
  },
  comet: {
    name: '彗星 67P 彗发',
    keyGas: 'vocs',
    goal: '分析原始太阳系有机物组成',
    source: 'ESA Rosetta ROSINA',
    note: 'H₂S ~1.5%, VOCs 丰富，含氨基酸前体'
  },
  europa: {
    name: '木卫二热液',
    keyGas: 'h2s',
    goal: '探测冰下海洋热液活动迹象',
    source: '理论模型 + HST 观测',
    note: 'H₂S 是热液活动关键标志'
  },
  titan: {
    name: '土卫六甲烷湖',
    keyGas: 'ch4',
    goal: '研究甲烷循环与复杂有机化学',
    source: 'NASA Cassini-Huygens',
    note: 'CH₄ ~5%，存在液态甲烷湖'
  },
  earth_life: {
    name: '地球生命基线',
    keyGas: 'ch4',
    goal: '建立生物信号参考基准',
    source: 'NOAA GML 2023',
    note: 'CH₄ 1.9 ppm，CO₂ 420 ppm'
  },
  background: {
    name: '深空背景',
    keyGas: null,
    goal: '校准传感器本底噪声',
    source: '仪器基线',
    note: '用于零点校准'
  },
  custom: {
    name: '自定义场景',
    keyGas: null,
    goal: '用户自定义气体配比',
    source: '用户输入',
    note: ''
  }
}

// 默认测试用例
const DEFAULT_TEST_CASES = [
  {
    id: 1,
    name: '火星甲烷异常检测',
    scenario: 'mars',
    anomaly: { gasKey: 'ch4', multiplier: 5, durationSec: 10 },
    expected: { label: 'mars', minConfidence: 0.6, anomalyDetected: true }
  },
  {
    id: 2,
    name: '金星磷化氢峰值',
    scenario: 'venus',
    anomaly: { gasKey: 'ph3', multiplier: 3, durationSec: 8 },
    expected: { label: 'venus', minConfidence: 0.5, anomalyDetected: true }
  },
  {
    id: 3,
    name: '背景噪声识别',
    scenario: 'background',
    anomaly: null,
    expected: { label: 'background', minConfidence: 0.4, anomalyDetected: false }
  },
  {
    id: 4,
    name: '木卫二硫化物检测',
    scenario: 'europa',
    anomaly: { gasKey: 'h2s', multiplier: 4, durationSec: 6 },
    expected: { label: 'europa', minConfidence: 0.5, anomalyDetected: true }
  },
  {
    id: 5,
    name: '地球生命基线验证',
    scenario: 'earth_life',
    anomaly: null,
    expected: { label: 'earth_life', minConfidence: 0.5, anomalyDetected: false }
  }
]

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max)
}

function randn() {
  let u = 0
  let v = 0
  while (u === 0) u = Math.random()
  while (v === 0) v = Math.random()
  return Math.sqrt(-2.0 * Math.log(u)) * Math.cos(2.0 * Math.PI * v)
}

export default {
  name: 'GroundLab',
  components: {
    VChart
  },
  data() {
    const defaultThresholds = {}
    const defaultBaseline = {}
    GAS_META.forEach((g) => {
      defaultThresholds[g.key] = {
        warning: g.unit === 'ppb' ? 50 : 5,
        danger: g.unit === 'ppb' ? 200 : 20
      }
      defaultBaseline[g.key] = g.unit === 'ppb' ? 10 : 1
    })

    return {
      settingsTab: 'config',
      mode: 'simulation',
      scenario: 'mars',
      scenarioOptions: [
        { label: '火星 CH₄ 基线', value: 'mars' },
        { label: '金星 PH₃ 痕量', value: 'venus' },
        { label: '彗星挥发物', value: 'comet' },
        { label: '木卫二冰下海洋', value: 'europa' },
        { label: '土卫六甲烷湖', value: 'titan' },
        { label: '地球生命基线', value: 'earth_life' },
        { label: '深空背景噪声', value: 'background' },
        { label: '自定义', value: 'custom' }
      ],

      sampleHz: 1,
      temperatureC: 25,
      noisePercent: 3,
      driftPermillePerMin: 1,
      enableInterference: true,

      points: [],
      maxPoints: 240,
      lastStatuses: {},
      events: [],

      simulationRunning: false,
      simulationTimer: null,
      driftOffsets: {},

      ws: null,
      wsConnected: false,
      wsConnecting: false,

      realtimeSourceField: 'alcohol_ppm',
      realtimeMapGas: 'vocs',
      realtimeScale: 1000,

      baseline: defaultBaseline,
      thresholds: defaultThresholds,

      anomaly: {
        gasKey: 'ch4',
        multiplier: 3,
        durationSec: 10,
        remainingTicks: 0
      },

      mlStatus: null,
      mlLoading: false,
      mlUploading: false,
      mlTraining: false,
      mlPredicting: false,
      mlPrediction: null,
      mlError: '',

      enoseStatus: null,
      enoseLoading: false,
      enoseTraining: false,
      enoseSampling: false,
      enosePredicting: false,
      enoseSample: null,
      enosePrediction: null,
      enoseTrainResult: null,
      enoseError: '',

      // 深度学习模型
      dlMetrics: {
        model_size_kb: null,
        inference_time_ms: null,
        accuracy: null,
        available: false
      },
      dlMetricsLoading: false,
      dlTraining: false,
      dlTrainProgress: 0,
      dlTrainResult: null,
      dlPredicting: false,
      dlDecision: null,

      // 测试用例管理
      testCases: JSON.parse(JSON.stringify(DEFAULT_TEST_CASES)),
      testRunning: false,
      currentTestId: null,
      testResults: {},
      testProgress: 0,
      SCENARIO_INFO: SCENARIO_INFO
    }
  },
  computed: {
    gases() {
      return GAS_META
    },
    currentScenarioInfo() {
      return SCENARIO_INFO[this.scenario] || null
    },
    modeTagText() {
      return this.mode === 'simulation' ? '模拟实验' : '对接后端'
    },
    modeTagType() {
      return this.mode === 'simulation' ? 'warning' : 'success'
    },
    gasCards() {
      const latest = this.points.length > 0 ? this.points[this.points.length - 1] : null
      return GAS_META.map((gas) => {
        const value = latest ? latest[gas.key] : null
        const status = this.getStatus(gas.key, value)
        return {
          ...gas,
          value,
          display: value === null || value === undefined ? '—' : this.formatNumber(value, gas.unit),
          statusText: status.text,
          tagType: status.tagType
        }
      })
    },
    lineOption() {
      const labels = this.points.map((p) => p.tLabel)
      const series = GAS_META.map((gas) => ({
        name: `${gas.label} (${gas.unit})`,
        type: 'line',
        yAxisIndex: gas.axis,
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 2, color: gas.color },
        itemStyle: { color: gas.color },
        connectNulls: true,
        data: this.points.map((p) => (p[gas.key] === undefined ? null : p[gas.key]))
      }))

      return {
        backgroundColor: 'transparent',
        tooltip: {
          trigger: 'axis',
          backgroundColor: 'rgba(15, 23, 42, 0.9)',
          borderColor: 'rgba(34, 211, 238, 0.3)',
          textStyle: { color: '#e2e8f0', fontSize: 12 }
        },
        legend: {
          top: 0,
          textStyle: { color: '#94a3b8', fontSize: 12 },
          inactiveColor: '#475569'
        },
        grid: { left: 40, right: 46, top: 40, bottom: 30, borderColor: 'rgba(148, 163, 184, 0.1)' },
        xAxis: {
          type: 'category',
          data: labels,
          axisLabel: { color: '#94a3b8' },
          axisLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.2)' } }
        },
        yAxis: [
          {
            type: 'value',
            name: 'ppm',
            nameTextStyle: { color: '#94a3b8' },
            axisLabel: { color: '#94a3b8' },
            splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.1)' } }
          },
          {
            type: 'value',
            name: 'ppb',
            nameTextStyle: { color: '#94a3b8' },
            axisLabel: { color: '#94a3b8' },
            splitLine: { show: false }
          }
        ],
        series
      }
    },
    samplingMode() {
      return this.scienceScore >= 70 ? 'high' : 'normal'
    },
    scienceScore() {
      const latest = this.points.length > 0 ? this.points[this.points.length - 1] : null
      if (!latest) return 0
      const ratios = GAS_META.map((gas) => {
        const value = latest[gas.key]
        if (value === null || value === undefined) return 0
        const warning = this.thresholds[gas.key].warning || 1
        return value / warning
      })
      const maxRatio = Math.max(...ratios, 0)
      const anomalyBonus = this.anomaly.remainingTicks > 0 ? 0.3 : 0
      return Math.round(clamp((maxRatio + anomalyBonus) * 50, 0, 100))
    },
    downlinkPercent() {
      return this.samplingMode === 'high' ? 60 : 10
    },
    recentEvents() {
      return this.events.slice(-8).reverse()
    },
    confusionRows() {
      if (!this.enoseTrainResult?.confusion_matrix || !this.enoseTrainResult?.confusion_matrix_labels) return []
      const labels = this.enoseTrainResult.confusion_matrix_labels
      return this.enoseTrainResult.confusion_matrix.map((row, idx) => {
        const obj = { label: labels[idx] }
        labels.forEach((cls, j) => {
          obj[cls] = row[j]
        })
        return obj
      })
    },
    // 智能决策雷达图配置
    decisionRadarOption() {
      if (!this.dlDecision?.decision) return {}
      const decision = this.dlDecision.decision
      const classification = this.dlDecision.classification || {}
      return {
        backgroundColor: 'transparent',
        radar: {
          indicator: [
            { name: '分类置信度', max: 1 },
            { name: '科学价值', max: 1 },
            { name: '异常程度', max: 1 },
            { name: '数据质量', max: 1 },
            { name: '优先级', max: 1 }
          ],
          shape: 'polygon',
          splitNumber: 4,
          axisName: { color: '#94a3b8', fontSize: 10 },
          splitLine: { lineStyle: { color: 'rgba(71, 85, 105, 0.5)' } },
          splitArea: { areaStyle: { color: ['rgba(34, 211, 238, 0.05)', 'rgba(168, 85, 247, 0.05)'] } },
          axisLine: { lineStyle: { color: 'rgba(71, 85, 105, 0.5)' } }
        },
        series: [{
          type: 'radar',
          data: [{
            value: [
              classification.confidence || 0,
              decision.scientific_value || 0,
              1 - (this.dlDecision.anomaly_detection?.is_normal ? 1 : 0.3),
              0.85,
              decision.action === 'priority' ? 1 : decision.action === 'high_sample' ? 0.9 : decision.action === 'normal' ? 0.5 : 0.2
            ],
            name: '决策指标',
            areaStyle: {
              color: {
                type: 'linear',
                x: 0, y: 0, x2: 1, y2: 1,
                colorStops: [
                  { offset: 0, color: 'rgba(34, 211, 238, 0.4)' },
                  { offset: 1, color: 'rgba(168, 85, 247, 0.4)' }
                ]
              }
            },
            lineStyle: { color: '#22d3ee', width: 2 },
            itemStyle: { color: '#22d3ee' }
          }]
        }]
      }
    },
    // 训练损失曲线图配置
    trainingLossChartOption() {
      if (!this.dlTrainResult?.training_history?.loss) return {}
      const losses = this.dlTrainResult.training_history.loss
      const epochs = losses.map((_, i) => i + 1)
      return {
        backgroundColor: 'transparent',
        title: {
          text: '训练损失',
          left: 'center',
          top: 0,
          textStyle: { color: '#94a3b8', fontSize: 12, fontWeight: 'normal' }
        },
        tooltip: {
          trigger: 'axis',
          backgroundColor: 'rgba(15, 23, 42, 0.9)',
          borderColor: 'rgba(34, 211, 238, 0.3)',
          textStyle: { color: '#e2e8f0', fontSize: 11 }
        },
        grid: { left: 40, right: 20, top: 30, bottom: 25 },
        xAxis: {
          type: 'category',
          data: epochs,
          name: 'Epoch',
          nameTextStyle: { color: '#64748b', fontSize: 10 },
          axisLabel: { color: '#64748b', fontSize: 10 },
          axisLine: { lineStyle: { color: 'rgba(71, 85, 105, 0.5)' } }
        },
        yAxis: {
          type: 'value',
          name: 'Loss',
          nameTextStyle: { color: '#64748b', fontSize: 10 },
          axisLabel: { color: '#64748b', fontSize: 10 },
          splitLine: { lineStyle: { color: 'rgba(71, 85, 105, 0.3)' } }
        },
        series: [{
          name: 'Loss',
          type: 'line',
          smooth: true,
          showSymbol: false,
          lineStyle: { color: '#ef4444', width: 2 },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(239, 68, 68, 0.3)' },
                { offset: 1, color: 'rgba(239, 68, 68, 0)' }
              ]
            }
          },
          data: losses
        }]
      }
    },
    // 训练准确率曲线图配置
    trainingAccuracyChartOption() {
      if (!this.dlTrainResult?.training_history) return {}
      const history = this.dlTrainResult.training_history
      const trainAcc = history.train_accuracy || []
      const valAcc = history.val_accuracy || []
      const epochs = trainAcc.map((_, i) => i + 1)
      return {
        backgroundColor: 'transparent',
        title: {
          text: '准确率趋势',
          left: 'center',
          top: 0,
          textStyle: { color: '#94a3b8', fontSize: 12, fontWeight: 'normal' }
        },
        tooltip: {
          trigger: 'axis',
          backgroundColor: 'rgba(15, 23, 42, 0.9)',
          borderColor: 'rgba(34, 211, 238, 0.3)',
          textStyle: { color: '#e2e8f0', fontSize: 11 },
          formatter: (params) => {
            let result = `Epoch ${params[0].axisValue}<br/>`
            params.forEach((p) => {
              result += `${p.marker} ${p.seriesName}: ${(p.value * 100).toFixed(1)}%<br/>`
            })
            return result
          }
        },
        legend: {
          top: 20,
          data: ['训练准确率', '验证准确率'],
          textStyle: { color: '#94a3b8', fontSize: 10 }
        },
        grid: { left: 40, right: 20, top: 50, bottom: 25 },
        xAxis: {
          type: 'category',
          data: epochs,
          name: 'Epoch',
          nameTextStyle: { color: '#64748b', fontSize: 10 },
          axisLabel: { color: '#64748b', fontSize: 10 },
          axisLine: { lineStyle: { color: 'rgba(71, 85, 105, 0.5)' } }
        },
        yAxis: {
          type: 'value',
          name: 'Accuracy',
          min: 0,
          max: 1,
          nameTextStyle: { color: '#64748b', fontSize: 10 },
          axisLabel: {
            color: '#64748b',
            fontSize: 10,
            formatter: (v) => `${(v * 100).toFixed(0)}%`
          },
          splitLine: { lineStyle: { color: 'rgba(71, 85, 105, 0.3)' } }
        },
        series: [
          {
            name: '训练准确率',
            type: 'line',
            smooth: true,
            showSymbol: false,
            lineStyle: { color: '#22c55e', width: 2 },
            data: trainAcc
          },
          {
            name: '验证准确率',
            type: 'line',
            smooth: true,
            showSymbol: false,
            lineStyle: { color: '#22d3ee', width: 2 },
            data: valAcc
          }
        ]
      }
    }
  },
  watch: {
    sampleHz() {
      if (this.simulationRunning) {
        this.restartSimulationTimer()
      }
      if (this.wsConnected) {
        this.addEvent('info', `采样频率调整为 ${this.sampleHz} Hz（仅影响模拟/显示）`)
      }
    }
  },
  mounted() {
    this.applyScenarioPreset()
    this.resetData()
    this.refreshMlStatus()
  },
  beforeUnmount() {
    this.stopSimulation()
    this.disconnectWs()
  },
  methods: {
    onModeChange() {
      this.stopSimulation()
      this.disconnectWs()
      this.resetData()
      this.mlPrediction = null
    },
    getGasLabel(gasKey) {
      const gas = GAS_META.find((g) => g.key === gasKey)
      return gas ? gas.label : gasKey
    },
    formatNumber(value, unitOrPrecision, precisionOverride) {
      let precision
      if (typeof unitOrPrecision === 'number') {
        precision = unitOrPrecision
      } else if (typeof precisionOverride === 'number') {
        precision = precisionOverride
      } else {
        precision = unitOrPrecision === 'ppb' ? 0 : 3
      }
      return Number(value).toFixed(precision)
    },
    getStatus(gasKey, value) {
      if (value === null || value === undefined) {
        return { text: '未接入', tagType: 'info' }
      }
      const { warning, danger } = this.thresholds[gasKey]
      if (value >= danger) return { text: '危险', tagType: 'danger' }
      if (value >= warning) return { text: '预警', tagType: 'warning' }
      return { text: '正常', tagType: 'success' }
    },
    addEvent(type, text) {
      const tagMap = { info: 'info', warning: 'warning', danger: 'danger', success: 'success' }
      this.events.push({
        id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
        time: dayjs().format('HH:mm:ss'),
        type,
        tagType: tagMap[type] || 'info',
        text
      })
      if (this.events.length > 200) {
        this.events.shift()
      }
    },
    clearEvents() {
      this.events = []
    },
    resetData() {
      this.points = []
      this.events = []
      this.lastStatuses = {}
      this.driftOffsets = {}
      GAS_META.forEach((gas) => {
        this.lastStatuses[gas.key] = 'unknown'
        this.driftOffsets[gas.key] = 0
      })
      this.anomaly.remainingTicks = 0
      this.enoseSample = null
      this.enosePrediction = null
    },
    applyScenarioPreset() {
      if (this.scenario === 'custom') return
      const preset = SCENARIO_PRESETS[this.scenario]
      if (!preset) return
      Object.keys(preset).forEach((key) => {
        this.baseline[key] = preset[key]
      })
      this.addEvent('info', `应用场景预设：${this.scenario}`)
    },
    restartSimulationTimer() {
      this.stopSimulation()
      this.startSimulation()
    },
    startSimulation() {
      if (this.simulationRunning) return
      if (this.mode !== 'simulation') return
      this.disconnectWs()

      this.simulationRunning = true
      const intervalMs = Math.round(1000 / this.sampleHz)
      this.simulationTimer = window.setInterval(() => {
        this.tickSimulation(intervalMs)
      }, intervalMs)
      this.addEvent('success', `开始模拟（${this.sampleHz} Hz）`)
    },
    stopSimulation() {
      if (!this.simulationRunning) return
      window.clearInterval(this.simulationTimer)
      this.simulationTimer = null
      this.simulationRunning = false
      this.addEvent('info', '停止模拟')
    },
    tickSimulation(intervalMs) {
      const tempFactor = clamp(1 + (this.temperatureC - 25) * 0.006, 0.7, 1.3)
      const noiseScale = this.noisePercent / 100
      const driftScalePerMs = (this.driftPermillePerMin / 1000) / 60000

      const values = {}
      GAS_META.forEach((gas) => {
        const base = Number(this.baseline[gas.key] || 0)
        this.driftOffsets[gas.key] += base * driftScalePerMs * intervalMs * (Math.random() > 0.5 ? 1 : -1)
        let v = (base + this.driftOffsets[gas.key]) * tempFactor
        v = v * (1 + randn() * noiseScale)
        values[gas.key] = Math.max(0, v)
      })

      if (this.enableInterference) {
        values.vocs = Math.max(0, values.vocs + values.ch4 * 8 + values.h2s * 30)
        values.ch4 = Math.max(0, values.ch4 + values.vocs / 500)
      }

      if (this.anomaly.remainingTicks > 0) {
        values[this.anomaly.gasKey] = Math.max(0, values[this.anomaly.gasKey] * this.anomaly.multiplier)
        this.anomaly.remainingTicks -= 1
      }

      const point = {
        t: Date.now(),
        tLabel: dayjs().format('HH:mm:ss'),
        ...values
      }
      this.appendPoint(point)
      this.checkAlerts(point)
    },
    injectAnomaly() {
      if (this.mode !== 'simulation') return
      const ticks = Math.max(1, Math.round(this.anomaly.durationSec * this.sampleHz))
      this.anomaly.remainingTicks = ticks
      this.addEvent(
        'danger',
        `注入异常：${this.anomaly.gasKey} ×${this.anomaly.multiplier}（${this.anomaly.durationSec}s）`
      )
    },
    checkAlerts(point) {
      GAS_META.forEach((gas) => {
        const value = point[gas.key]
        const status = this.getStatus(gas.key, value).text
        const last = this.lastStatuses[gas.key]
        if (status !== last) {
          this.lastStatuses[gas.key] = status
          if (status === '预警') {
            this.addEvent('warning', `${gas.label} 进入预警：${this.formatNumber(value, gas.unit)} ${gas.unit}`)
          } else if (status === '危险') {
            this.addEvent('danger', `${gas.label} 进入危险：${this.formatNumber(value, gas.unit)} ${gas.unit}`)
          }
        }
      })
    },
    appendPoint(point) {
      this.points.push(point)
      if (this.points.length > this.maxPoints) {
        this.points.shift()
      }
    },
    connectWs() {
      if (this.wsConnected || this.wsConnecting) return
      this.stopSimulation()
      this.wsConnecting = true

      const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
      const wsUrl = `${protocol}://${window.location.hostname}:8000/ws`
      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        this.wsConnecting = false
        this.wsConnected = true
        this.addEvent('success', `WebSocket 已连接：${wsUrl}`)
      }

      this.ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data)
          this.handleRealtimePayload(payload)
        } catch (err) {
          this.addEvent('warning', `解析后端数据失败：${String(err)}`)
        }
      }

      this.ws.onerror = () => {
        this.wsConnecting = false
        this.wsConnected = false
        this.addEvent('warning', 'WebSocket 连接错误')
      }

      this.ws.onclose = () => {
        this.wsConnecting = false
        const wasConnected = this.wsConnected
        this.wsConnected = false
        if (wasConnected) this.addEvent('info', 'WebSocket 已断开')
      }
    },
    disconnectWs() {
      if (this.ws) {
        try {
          this.ws.close()
        } catch (err) {
          // ignore
        }
      }
      this.ws = null
      this.wsConnected = false
      this.wsConnecting = false
    },
    handleRealtimePayload(payload) {
      const getFieldValue = () => {
        if (this.realtimeSourceField === 'adc') return payload.adc
        if (this.realtimeSourceField === 'voltage') return payload.voltage
        if (this.realtimeSourceField === 'co2_ppm') return payload.co2_ppm
        return payload.alcohol_ppm
      }

      const raw = getFieldValue()
      const scale = Number(this.realtimeScale || 1)
      const mappedValue = raw == null ? null : Number(raw) * scale
      const point = {
        t: Date.now(),
        tLabel: payload.timestamp ? String(payload.timestamp).slice(11, 19) : dayjs().format('HH:mm:ss')
      }
      GAS_META.forEach((gas) => {
        point[gas.key] = null
      })
      point[this.realtimeMapGas] = Number.isNaN(mappedValue) ? null : mappedValue
      this.appendPoint(point)
      this.checkAlerts(point)
    },

    apiBaseUrl() {
      const protocol = window.location.protocol === 'https:' ? 'https' : 'http'
      return `${protocol}://${window.location.hostname}:8000`
    },

    currentScenarioVector() {
      const latest = this.points.length > 0 ? this.points[this.points.length - 1] : null
      const vector = {}
      GAS_META.forEach((gas) => {
        const v = latest && latest[gas.key] !== undefined ? latest[gas.key] : this.baseline[gas.key]
        vector[gas.key] = v == null ? null : Number(v)
      })
      return vector
    },

    async refreshMlStatus() {
      this.mlError = ''
      this.enoseError = ''
      this.mlLoading = true
      this.enoseLoading = true
      try {
        const response = await fetch(`${this.apiBaseUrl()}/api/ml/status`)
        const json = await response.json()
        if (json.success && json.data) {
          this.mlStatus = json.data
          this.enoseStatus = json.data.enose || null
        } else {
          this.mlError = json.data?.error || '获取 ML 状态失败'
          this.enoseError = this.mlError
        }
      } catch (err) {
        this.mlError = `获取 ML 状态失败：${String(err)}`
        this.enoseError = this.mlError
      } finally {
        this.mlLoading = false
        this.enoseLoading = false
      }
    },

    async uploadScenarioSample() {
      if (this.mode !== 'simulation') return
      this.mlError = ''
      this.mlUploading = true
      try {
        const payload = {
          label: this.scenario,
          features: this.currentScenarioVector(),
          meta: {
            temperature_c: this.temperatureC,
            noise_percent: this.noisePercent,
            drift_permille_per_min: this.driftPermillePerMin,
            interference: this.enableInterference
          },
          source: 'ground_lab'
        }
        const response = await fetch(`${this.apiBaseUrl()}/api/ml/scenario/sample`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        })
        const json = await response.json()
        if (json.success) {
          this.addEvent('success', `已上传训练样本（${this.scenario}）`)
          await this.refreshMlStatus()
        } else {
          this.mlError = json.data?.error || '上传训练样本失败'
        }
      } catch (err) {
        this.mlError = `上传训练样本失败：${String(err)}`
      } finally {
        this.mlUploading = false
      }
    },

    async trainScenarioModel() {
      this.mlError = ''
      this.mlTraining = true
      try {
        const response = await fetch(`${this.apiBaseUrl()}/api/ml/scenario/train?min_samples=20`, {
          method: 'POST'
        })
        const json = await response.json()
        if (json.success && json.data?.trained) {
          this.addEvent('success', '场景模型训练完成')
          await this.refreshMlStatus()
        } else {
          this.mlError = json.data?.error || '训练失败'
        }
      } catch (err) {
        this.mlError = `训练失败：${String(err)}`
      } finally {
        this.mlTraining = false
      }
    },

    async predictScenario() {
      this.mlError = ''
      this.mlPredicting = true
      try {
        const payload = { features: this.currentScenarioVector() }
        const response = await fetch(`${this.apiBaseUrl()}/api/ml/scenario/predict`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        })
        const json = await response.json()
        this.mlPrediction = json.data || { ok: false, error: '预测失败' }
        if (!json.success) {
          this.mlError = this.mlPrediction.error || '预测失败'
        }
      } catch (err) {
        this.mlPrediction = { ok: false, error: String(err) }
        this.mlError = `预测失败：${String(err)}`
      } finally {
        this.mlPredicting = false
      }
    },

    async trainEnoseModel() {
      this.enoseError = ''
      this.enoseTraining = true
      try {
        const response = await fetch(`${this.apiBaseUrl()}/api/ml/enose/train`, { method: 'POST' })
        const json = await response.json()
        if (json.success && json.data?.trained) {
          this.enoseTrainResult = json.data
          this.addEvent('success', '传感器阵列模型训练完成')
          await this.refreshMlStatus()
        } else {
          this.enoseError = json.data?.error || '训练失败'
        }
      } catch (err) {
        this.enoseError = `训练失败：${String(err)}`
      } finally {
        this.enoseTraining = false
      }
    },

    async sampleEnoseDataset() {
      this.enoseError = ''
      this.enoseSampling = true
      try {
        const response = await fetch(`${this.apiBaseUrl()}/api/ml/enose/sample`)
        const json = await response.json()
        if (json.success && json.data?.ok) {
          this.enoseSample = json.data
          this.addEvent('info', `抽样 index=${json.data.index}，标签=${json.data.label}`)
        } else {
          this.enoseError = json.data?.error || '抽样失败'
        }
      } catch (err) {
        this.enoseError = `抽样失败：${String(err)}`
      } finally {
        this.enoseSampling = false
      }
    },

    async predictEnose() {
      this.enoseError = ''
      this.enosePredicting = true
      try {
        if (!this.enoseSample?.features) {
          this.enoseError = '请先抽样得到特征'
          this.enosePredicting = false
          return
        }
        const response = await fetch(`${this.apiBaseUrl()}/api/ml/enose/predict`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ features: this.enoseSample.features })
        })
        const json = await response.json()
        this.enosePrediction = json.data || { ok: false, error: '预测失败' }
        if (!json.success) {
          this.enoseError = this.enosePrediction.error || '预测失败'
        }
      } catch (err) {
        this.enosePrediction = { ok: false, error: String(err) }
        this.enoseError = `预测失败：${String(err)}`
      } finally {
        this.enosePredicting = false
      }
    },
    exportXlsx() {
      const rows = this.points.map((p) => {
        const row = { time: p.tLabel }
        GAS_META.forEach((gas) => {
          row[`${gas.key}_${gas.unit}`] = p[gas.key]
        })
        return row
      })
      const ws = XLSX.utils.json_to_sheet(rows)
      const wb = XLSX.utils.book_new()
      XLSX.utils.book_append_sheet(wb, ws, 'data')
      const filename = `ground-lab-data_${dayjs().format('YYYYMMDD_HHmmss')}.xlsx`
      XLSX.writeFile(wb, filename)
      this.addEvent('success', `已导出 Excel：${filename}`)
    },
    exportPdf() {
      const doc = new jsPDF()
      doc.setFontSize(14)
      doc.text('Ground Verification Report (Year 1)', 14, 18)
      doc.setFontSize(10)
      doc.text(`Generated: ${dayjs().format('YYYY-MM-DD HH:mm:ss')}`, 14, 26)
      doc.text(`Mode: ${this.modeTagText}`, 14, 32)
      if (this.mode === 'simulation') {
        doc.text(`Scenario: ${this.scenario}`, 14, 38)
        doc.text(`Sample: ${this.sampleHz} Hz, Temp: ${this.temperatureC} C`, 14, 44)
      } else {
        doc.text(`Mapping: ${this.realtimeSourceField} -> ${this.realtimeMapGas} x${this.realtimeScale}`, 14, 38)
      }

      const statsBody = GAS_META.map((gas) => {
        const values = this.points
          .map((p) => p[gas.key])
          .filter((v) => v !== null && v !== undefined && !Number.isNaN(Number(v)))
          .map((v) => Number(v))
        const min = values.length ? Math.min(...values) : null
        const max = values.length ? Math.max(...values) : null
        const avg = values.length ? values.reduce((a, b) => a + b, 0) / values.length : null
        return [
          gas.label,
          gas.unit,
          min === null ? '—' : this.formatNumber(min, gas.unit),
          max === null ? '—' : this.formatNumber(max, gas.unit),
          avg === null ? '—' : this.formatNumber(avg, gas.unit),
          `${this.thresholds[gas.key].warning} / ${this.thresholds[gas.key].danger}`
        ]
      })

      autoTable(doc, {
        startY: 52,
        head: [['Gas', 'Unit', 'Min', 'Max', 'Avg', 'Warn/Danger']],
        body: statsBody,
        styles: { fontSize: 9 }
      })

      const eventSample = this.events.slice(-12).reverse().map((e) => [`${e.time}`, e.type, e.text])
      autoTable(doc, {
        startY: doc.lastAutoTable ? doc.lastAutoTable.finalY + 8 : 110,
        head: [['Time', 'Type', 'Event']],
        body: eventSample.length ? eventSample : [['—', 'info', 'No events']],
        styles: { fontSize: 9 }
      })

      const filename = `ground-lab-report_${dayjs().format('YYYYMMDD_HHmmss')}.pdf`
      doc.save(filename)
      this.addEvent('success', `已生成 PDF：${filename}`)
    },

    // ========== 测试用例管理 ==========
    sleep(ms) {
      return new Promise((resolve) => setTimeout(resolve, ms))
    },
    async runSingleTest(testCase, isPartOfBatch = false) {
      this.currentTestId = testCase.id
      if (!isPartOfBatch) {
        this.testRunning = true
      }

      try {
        // 1. 停止当前模拟，清空数据
        this.stopSimulation()
        this.resetData()
        await this.sleep(300)

        // 2. 应用测试场景
        this.scenario = testCase.scenario
        this.applyScenarioPreset()

        // 3. 启动模拟收集数据
        this.startSimulation()
        await this.sleep(2000) // 收集基线数据

        // 4. 如果有异常配置，注入异常
        if (testCase.anomaly) {
          this.anomaly.gasKey = testCase.anomaly.gasKey
          this.anomaly.multiplier = testCase.anomaly.multiplier
          this.anomaly.durationSec = testCase.anomaly.durationSec
          this.injectAnomaly()
          await this.sleep(testCase.anomaly.durationSec * 1000 + 1000)
        } else {
          await this.sleep(3000) // 稳定状态采集
        }

        // 5. 执行预测
        await this.predictScenario()

        // 6. 验证结果
        const result = this.validateTestResult(testCase)
        this.testResults = {
          ...this.testResults,
          [testCase.id]: result
        }

        this.addEvent(
          result.passed ? 'success' : 'danger',
          `测试「${testCase.name}」${result.passed ? '通过' : '失败'}`
        )
      } catch (err) {
        this.testResults = {
          ...this.testResults,
          [testCase.id]: { passed: false, error: String(err), actual: null }
        }
        this.addEvent('danger', `测试「${testCase.name}」出错: ${err}`)
      } finally {
        this.stopSimulation()
        this.currentTestId = null
        if (!isPartOfBatch) {
          this.testRunning = false
        }
      }

      return this.testResults[testCase.id]
    },
    validateTestResult(testCase) {
      const prediction = this.mlPrediction
      if (!prediction || !prediction.ok) {
        return { passed: false, actual: null, error: '预测失败' }
      }

      const actualLabel = prediction.label
      const actualConfidence = prediction.confidence || 0
      const expectedLabel = testCase.expected.label
      const minConfidence = testCase.expected.minConfidence

      const labelMatch = actualLabel === expectedLabel
      const confidenceMatch = actualConfidence >= minConfidence

      return {
        passed: labelMatch && confidenceMatch,
        actual: { label: actualLabel, confidence: actualConfidence },
        expected: testCase.expected,
        labelMatch,
        confidenceMatch
      }
    },
    async runAllTests() {
      this.testRunning = true
      this.testProgress = 0
      const total = this.testCases.length

      for (let i = 0; i < total; i++) {
        const tc = this.testCases[i]
        await this.runSingleTest(tc, true)  // isPartOfBatch = true
        this.testProgress = ((i + 1) / total) * 100
        await this.sleep(500) // 测试间隔
      }

      this.testRunning = false
      this.testProgress = 100

      const passed = Object.values(this.testResults).filter((r) => r.passed).length
      this.addEvent('info', `测试完成: ${passed}/${total} 通过`)
    },
    resetTestResults() {
      this.testResults = {}
      this.testProgress = 0
      this.addEvent('info', '已清除测试结果')
    },

    // ========== 深度学习相关方法 ==========
    async fetchDLMetrics() {
      this.dlMetricsLoading = true
      try {
        const response = await fetch(`${this.apiBaseUrl()}/api/ml/dl/metrics`)
        const json = await response.json()
        if (json.success && json.data) {
          const data = json.data
          this.dlMetrics = {
            model_size_kb: data.classifier?.size_kb || null,
            inference_time_ms: data.classifier?.inference_time_ms || null,
            accuracy: this.dlTrainResult?.val_accuracy || null,
            available: data.available || false
          }
        }
      } catch (err) {
        this.addEvent('warning', `获取 DL 指标失败: ${err}`)
      } finally {
        this.dlMetricsLoading = false
      }
    },

    async trainDLSynthetic() {
      this.dlTraining = true
      this.dlTrainProgress = 0
      this.dlTrainResult = null

      // 模拟训练进度
      const progressInterval = setInterval(() => {
        if (this.dlTrainProgress < 90) {
          this.dlTrainProgress += Math.random() * 15
        }
      }, 500)

      try {
        const response = await fetch(`${this.apiBaseUrl()}/api/ml/dl/train/synthetic?epochs=50&batch_size=32`, {
          method: 'POST'
        })
        const json = await response.json()
        this.dlTrainProgress = 100

        if (json.success && json.data) {
          this.dlTrainResult = json.data
          this.addEvent('success', `深度学习模型训练完成，验证准确率: ${(json.data.val_accuracy * 100).toFixed(1)}%`)

          // 更新指标
          this.dlMetrics = {
            model_size_kb: json.data.model_size_kb,
            inference_time_ms: json.data.inference_time_ms,
            accuracy: json.data.val_accuracy,
            available: true
          }
        } else {
          this.dlTrainResult = { trained: false, error: json.data?.error || '训练失败' }
          this.addEvent('danger', `深度学习模型训练失败: ${json.data?.error || '未知错误'}`)
        }
      } catch (err) {
        this.dlTrainResult = { trained: false, error: String(err) }
        this.addEvent('danger', `深度学习模型训练失败: ${err}`)
      } finally {
        clearInterval(progressInterval)
        this.dlTraining = false
      }
    },

    async predictWithDecision() {
      if (this.mode !== 'simulation') return
      this.dlPredicting = true
      this.dlDecision = null

      try {
        const features = this.currentScenarioVector()
        const response = await fetch(`${this.apiBaseUrl()}/api/ml/dl/predict`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ features })
        })
        const json = await response.json()

        if (json.success && json.data?.ok) {
          this.dlDecision = {
            classification: {
              label: json.data.classification?.class_name || '—',
              confidence: json.data.classification?.confidence || 0,
              probabilities: json.data.classification?.probabilities || {}
            },
            anomaly_detection: json.data.anomaly_detection || {},
            decision: json.data.decision || {},
            metrics: json.data.metrics || {}
          }
          this.addEvent('info', `智能决策: ${json.data.decision?.action} (科学价值: ${(json.data.decision?.scientific_value * 100).toFixed(0)})`)
        } else {
          this.addEvent('warning', `智能决策预测失败: ${json.data?.error || '未知错误'}`)
        }
      } catch (err) {
        this.addEvent('danger', `智能决策预测失败: ${err}`)
      } finally {
        this.dlPredicting = false
      }
    },

    getDecisionTagType(action) {
      const typeMap = {
        compress: 'info',
        normal: 'success',
        priority: 'warning',
        high_sample: 'danger'
      }
      return typeMap[action] || 'info'
    },

    getDecisionText(action) {
      const textMap = {
        compress: '压缩存储',
        normal: '正常存储',
        priority: '优先下传',
        high_sample: '高采样模式'
      }
      return textMap[action] || action || '—'
    }
  }
}
</script>

<style scoped>
.lab {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.lab-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 10px;
  padding: 2px 6px 0;
}

.eyebrow {
  margin: 0;
  font-size: 11px;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: #22d3ee;
  text-shadow: 0 0 15px rgba(34, 211, 238, 0.5);
}

.title h2 {
  margin: 2px 0;
  font-size: 20px;
  font-weight: 800;
  background: linear-gradient(135deg, #e2e8f0 0%, #22d3ee 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: 0.5px;
}

.lead {
  margin: 0;
  color: #94a3b8;
  line-height: 1.35;
  max-width: 680px;
  font-size: 12px;
}

.head-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-top: 2px;
  flex-wrap: wrap;
}

/* 太空玻璃态卡片 */
.glass {
  background: rgba(15, 23, 42, 0.8) !important;
  border: 1px solid rgba(71, 85, 105, 0.4) !important;
  backdrop-filter: blur(12px);
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

.glass:hover {
  border-color: rgba(34, 211, 238, 0.3) !important;
  box-shadow: 0 4px 30px rgba(0, 0, 0, 0.3), 0 0 20px rgba(34, 211, 238, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

.panel-title {
  font-weight: 800;
  color: #e2e8f0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.panel-title::before {
  content: '';
  display: inline-block;
  width: 4px;
  height: 16px;
  background: linear-gradient(180deg, #22d3ee, #a855f7);
  border-radius: 2px;
}

.form :deep(.el-form-item) {
  margin-bottom: 8px;
}

.form :deep(.el-form-item__label) {
  line-height: 18px;
  padding-bottom: 2px;
}

.form :deep(.el-form-item__label) {
  color: #94a3b8 !important;
}

.form :deep(.el-input__wrapper),
.form :deep(.el-select__wrapper) {
  background: rgba(30, 41, 59, 0.8) !important;
  border-color: rgba(71, 85, 105, 0.5) !important;
  box-shadow: none !important;
}

.form :deep(.el-input__inner),
.form :deep(.el-select__inner) {
  color: #e2e8f0 !important;
}

.form :deep(.el-slider__runway) {
  background: rgba(71, 85, 105, 0.5);
}

.form :deep(.el-slider__bar) {
  background: linear-gradient(90deg, #22d3ee, #a855f7);
}

.form :deep(.el-slider__button) {
  border-color: #22d3ee;
  background: #0f172a;
}

.form :deep(.el-radio-button__inner) {
  background: rgba(30, 41, 59, 0.8) !important;
  border-color: rgba(71, 85, 105, 0.5) !important;
  color: #94a3b8 !important;
}

.form :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: linear-gradient(135deg, rgba(34, 211, 238, 0.3), rgba(168, 85, 247, 0.3)) !important;
  border-color: rgba(34, 211, 238, 0.6) !important;
  color: #22d3ee !important;
  box-shadow: 0 0 15px rgba(34, 211, 238, 0.3);
}

.form :deep(.el-switch.is-checked .el-switch__core) {
  background: linear-gradient(90deg, #22d3ee, #a855f7);
  border-color: transparent;
}

.form :deep(.el-collapse-item__header) {
  background: transparent !important;
  color: #94a3b8 !important;
  border-color: rgba(71, 85, 105, 0.3) !important;
}

.form :deep(.el-collapse-item__content) {
  color: #e2e8f0;
}

.form :deep(.el-divider) {
  border-color: rgba(71, 85, 105, 0.3);
}

.btn-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 2px;
}

.export-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

/* 设置 Tabs 样式 */
.settings-tabs {
  background: transparent !important;
  border: none !important;
}

.settings-tabs :deep(.el-tabs__header) {
  background: rgba(30, 41, 59, 0.4);
  border-radius: 8px;
  margin-bottom: 8px;
  border: 1px solid rgba(71, 85, 105, 0.3);
}

.settings-tabs :deep(.el-tabs__nav-wrap) {
  background: transparent;
}

.settings-tabs :deep(.el-tabs__item) {
  color: #94a3b8;
  font-weight: 500;
  padding: 0 12px;
  height: 30px;
  line-height: 30px;
}

.settings-tabs :deep(.el-tabs__item.is-active) {
  color: #22d3ee;
  background: rgba(34, 211, 238, 0.1);
}

.settings-tabs :deep(.el-tabs__item:hover) {
  color: #22d3ee;
}

.settings-tabs :deep(.el-tabs__content) {
  padding: 0;
  max-height: 320px;
  overflow-y: auto;
}

.settings-tabs :deep(.el-tab-pane) {
  padding: 4px;
}

/* 折叠面板优化 */
:deep(.el-collapse-item__header) {
  background: rgba(30, 41, 59, 0.4);
  border: 1px solid rgba(71, 85, 105, 0.3);
  border-radius: 8px;
  padding: 8px 12px;
  margin-bottom: 6px;
  font-weight: 600;
  color: #e2e8f0;
  transition: all 0.3s ease;
}

:deep(.el-collapse-item__header:hover) {
  background: rgba(30, 41, 59, 0.6);
  border-color: rgba(34, 211, 238, 0.4);
}

:deep(.el-collapse-item__wrap) {
  background: transparent;
  border: none;
}

:deep(.el-collapse-item__content) {
  padding: 8px 10px;
  background: rgba(15, 23, 42, 0.3);
  border: 1px solid rgba(71, 85, 105, 0.2);
  border-radius: 8px;
  margin-bottom: 6px;
}

/* ========== 动画效果 ========== */

/* 卡片入场动画 */
@keyframes cardFadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.glass {
  animation: cardFadeIn 0.5s ease-out;
}

/* 气体卡片悬停动画 */
.gas-card {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.gas-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4), 0 0 30px rgba(34, 211, 238, 0.15);
}

/* 数值变化动画 */
@keyframes valueFlash {
  0% { color: #22d3ee; }
  50% { color: #67e8f9; text-shadow: 0 0 20px rgba(34, 211, 238, 0.8); }
  100% { color: #22d3ee; }
}

.gas-value {
  transition: all 0.3s ease;
}

/* 状态标签脉冲动画 */
@keyframes statusPulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.status-tag-danger {
  animation: statusPulse 1.5s ease-in-out infinite;
}

/* 按钮悬停动画 */
:deep(.el-button) {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

:deep(.el-button:hover) {
  transform: translateY(-2px);
}

:deep(.el-button:active) {
  transform: translateY(0);
}

/* 进度条动画 */
:deep(.el-progress-bar__inner) {
  transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 折叠面板展开动画 */
:deep(.el-collapse-item__wrap) {
  transition: height 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 图表容器渐入 */
.chart-card {
  animation: cardFadeIn 0.6s ease-out 0.2s both;
}

/* 测试项动画 */
.test-item {
  transition: all 0.3s ease;
}

.test-item:hover {
  transform: translateX(4px);
  border-color: rgba(34, 211, 238, 0.4);
}

.test-running {
  animation: testRunningPulse 1s ease-in-out infinite;
}

@keyframes testRunningPulse {
  0%, 100% {
    border-color: rgba(34, 211, 238, 0.5);
    box-shadow: 0 0 10px rgba(34, 211, 238, 0.2);
  }
  50% {
    border-color: rgba(34, 211, 238, 0.8);
    box-shadow: 0 0 20px rgba(34, 211, 238, 0.4);
  }
}

/* 数据加载动画 */
@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

.loading-shimmer {
  background: linear-gradient(
    90deg,
    rgba(30, 41, 59, 0.5) 25%,
    rgba(51, 65, 85, 0.5) 50%,
    rgba(30, 41, 59, 0.5) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

/* 事件日志滚动动画 */
.event-item {
  animation: eventSlideIn 0.3s ease-out;
}

@keyframes eventSlideIn {
  from {
    opacity: 0;
    transform: translateX(-10px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

/* ML 预测结果动画 */
.ml-result {
  animation: resultFadeIn 0.4s ease-out;
}

@keyframes resultFadeIn {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

/* 图表数据点闪烁（用于新数据） */
@keyframes dataPointFlash {
  0% { opacity: 1; }
  50% { opacity: 0.5; }
  100% { opacity: 1; }
}

.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 10px;
}

.hint {
  margin-top: 6px;
  color: #94a3b8;
  background: rgba(30, 41, 59, 0.6);
  border: 1px dashed rgba(71, 85, 105, 0.5);
  padding: 7px 9px;
  border-radius: 8px;
  line-height: 1.35;
  font-size: 11px;
}

.ml-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 10px 0 6px;
}

.ml-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 10px;
  margin-top: 10px;
}

.ml-kv {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border: 1px solid rgba(71, 85, 105, 0.4);
  background: rgba(30, 41, 59, 0.6);
  border-radius: 10px;
  color: #94a3b8;
  font-size: 12px;
}

.ml-value {
  color: #22d3ee;
  font-weight: 700;
}

.ml-result {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid rgba(34, 197, 94, 0.3);
}

.ml-result-text {
  color: #22c55e;
  font-size: 12px;
  font-weight: 700;
}

.ml-error {
  margin-top: 10px;
  color: #f87171;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  padding: 10px 12px;
  border-radius: 10px;
  line-height: 1.5;
  font-size: 12px;
}

.ml-section {
  margin-top: 14px;
}

.section-title {
  font-weight: 700;
  color: #e2e8f0;
  margin-bottom: 8px;
}

.mt-8 {
  margin-top: 8px;
}

.mt-10 {
  margin-top: 10px;
}

/* 气体卡片 - 太空风格 */
.gas-card {
  min-height: 96px;
  position: relative;
  overflow: hidden;
}

.gas-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--gas-color, #22d3ee), transparent);
  opacity: 0.6;
}

.gas-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 6px;
}

.gas-label {
  font-weight: 800;
  color: #e2e8f0;
  font-size: 12px;
}

.gas-unit {
  font-size: 10px;
  color: #64748b;
  margin-top: 1px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.gas-value {
  margin-top: 7px;
  font-size: 24px;
  font-weight: 900;
  letter-spacing: 0;
  background: linear-gradient(135deg, #e2e8f0 0%, #22d3ee 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  text-shadow: none;
  filter: drop-shadow(0 0 20px rgba(34, 211, 238, 0.3));
}

.gas-sub {
  margin-top: 6px;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  color: #64748b;
  font-size: 10px;
}

.gas-sub span {
  padding: 2px 6px;
  background: rgba(30, 41, 59, 0.6);
  border-radius: 6px;
  border: 1px solid rgba(71, 85, 105, 0.3);
}

.section {
  margin-top: 8px;
}

/* 图表卡片 */
.chart-card {
  position: relative;
}

.chart-card :deep(.el-card__header) {
  border-color: rgba(71, 85, 105, 0.3) !important;
  color: #e2e8f0;
}

.chart {
  height: 260px;
}

.card-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  color: #e2e8f0;
}

.small-meta {
  display: flex;
  gap: 8px;
  align-items: center;
  color: #64748b;
  font-size: 11px;
}

/* 指标区域 */
.metric {
  margin-bottom: 10px;
}

.metric-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 5px;
  color: #e2e8f0;
}

.metric-label {
  font-weight: 700;
  color: #e2e8f0;
  font-size: 12px;
}

.metric-value {
  color: #22d3ee;
  font-size: 11px;
  font-weight: 600;
}

.metric :deep(.el-progress__text) {
  color: #94a3b8 !important;
}

.metric :deep(.el-progress-bar__outer) {
  background: rgba(71, 85, 105, 0.4) !important;
}

/* 事件日志 */
.mini-log {
  margin-top: 8px;
  border-top: 1px solid rgba(71, 85, 105, 0.3);
  padding-top: 8px;
}

.mini-log-list {
  display: grid;
  gap: 5px;
  max-height: 130px;
  overflow-y: auto;
}

.mini-log-list::-webkit-scrollbar {
  width: 4px;
}

.mini-log-list::-webkit-scrollbar-track {
  background: rgba(30, 41, 59, 0.5);
  border-radius: 2px;
}

.mini-log-list::-webkit-scrollbar-thumb {
  background: rgba(71, 85, 105, 0.8);
  border-radius: 2px;
}

.mini-log-item {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 6px;
  align-items: start;
  padding: 4px 6px;
  background: rgba(30, 41, 59, 0.4);
  border-radius: 6px;
  border-left: 2px solid transparent;
}

.mini-log-item:has(.el-tag--danger) {
  border-left-color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
}

.mini-log-item:has(.el-tag--warning) {
  border-left-color: #f59e0b;
  background: rgba(245, 158, 11, 0.1);
}

.mini-log-item:has(.el-tag--success) {
  border-left-color: #22c55e;
  background: rgba(34, 197, 94, 0.1);
}

.mini-log-text {
  color: #94a3b8;
  line-height: 1.3;
  font-size: 11px;
}

.empty {
  color: #64748b;
  font-size: 11px;
  text-align: center;
  padding: 10px;
}

/* Element Plus 暗色主题覆盖 */
:deep(.el-card) {
  --el-card-bg-color: transparent;
}

:deep(.el-card__header) {
  background: transparent !important;
  border-bottom: 1px solid rgba(71, 85, 105, 0.3) !important;
  padding: 9px 12px !important;
}

:deep(.el-card__body) {
  padding: 10px !important;
}

:deep(.el-tag) {
  border: none !important;
}

:deep(.el-tag--success) {
  background: rgba(34, 197, 94, 0.2) !important;
  color: #22c55e !important;
}

:deep(.el-tag--warning) {
  background: rgba(245, 158, 11, 0.2) !important;
  color: #f59e0b !important;
}

:deep(.el-tag--danger) {
  background: rgba(239, 68, 68, 0.2) !important;
  color: #ef4444 !important;
}

:deep(.el-tag--info) {
  background: rgba(100, 116, 139, 0.2) !important;
  color: #94a3b8 !important;
}

:deep(.el-button--primary) {
  background: linear-gradient(135deg, #0891b2, #7c3aed) !important;
  border: none !important;
  box-shadow: 0 4px 15px rgba(8, 145, 178, 0.3);
}

:deep(.el-button--primary:hover) {
  background: linear-gradient(135deg, #0ea5e9, #8b5cf6) !important;
  box-shadow: 0 4px 20px rgba(8, 145, 178, 0.5);
}

:deep(.el-button--success) {
  background: rgba(34, 197, 94, 0.2) !important;
  border: 1px solid rgba(34, 197, 94, 0.4) !important;
  color: #22c55e !important;
}

:deep(.el-button--warning) {
  background: rgba(245, 158, 11, 0.2) !important;
  border: 1px solid rgba(245, 158, 11, 0.4) !important;
  color: #f59e0b !important;
}

:deep(.el-button--danger) {
  background: rgba(239, 68, 68, 0.2) !important;
  border: 1px solid rgba(239, 68, 68, 0.4) !important;
  color: #ef4444 !important;
}

@media (max-width: 900px) {
  .lab-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .grid-2 {
    grid-template-columns: 1fr;
  }

  .chart {
    height: 300px;
  }
}

/* 场景科学信息面板 */
.scenario-info-panel {
  background: linear-gradient(135deg, rgba(34, 211, 238, 0.08) 0%, rgba(139, 92, 246, 0.08) 100%);
  border: 1px solid rgba(34, 211, 238, 0.2);
  border-radius: 8px;
  padding: 12px 14px;
  margin-bottom: 16px;
}

.scenario-info-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.scenario-name {
  font-weight: 600;
  font-size: 14px;
  color: #22d3ee;
}

.scenario-info-goal {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
  line-height: 1.5;
}

.scenario-info-note {
  font-size: 11px;
  color: #22d3ee;
  margin-top: 6px;
  padding: 6px 8px;
  background: rgba(34, 211, 238, 0.1);
  border-radius: 4px;
}

.scenario-info-source {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.4);
  margin-top: 6px;
  font-style: italic;
}

.goal-label,
.note-label,
.source-label {
  color: rgba(255, 255, 255, 0.5);
  margin-right: 4px;
}

/* 测试用例管理样式 */
.test-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.test-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 300px;
  overflow-y: auto;
}

.test-item {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  padding: 10px 12px;
  transition: all 0.2s;
}

.test-item.test-running {
  border-color: #22d3ee;
  background: rgba(34, 211, 238, 0.08);
}

.test-item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.test-name {
  font-weight: 500;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.9);
}

.test-item-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.test-item-detail {
  display: flex;
  gap: 16px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.5);
}

.test-error {
  margin-top: 6px;
  font-size: 11px;
  color: #ef4444;
}

/* ========== 深度学习面板样式 ========== */
.dl-panel {
  padding: 4px 0;
}

.panel-hint {
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 12px;
  padding: 8px 10px;
  background: rgba(30, 41, 59, 0.5);
  border-radius: 6px;
  border-left: 3px solid #22d3ee;
}

/* 模型轻量化仪表盘 */
.metrics-dashboard {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-bottom: 14px;
}

.metric-gauge {
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(71, 85, 105, 0.4);
  border-radius: 10px;
  padding: 12px;
  text-align: center;
  transition: all 0.3s ease;
}

.metric-gauge:hover {
  border-color: rgba(34, 211, 238, 0.4);
  transform: translateY(-2px);
}

.metric-gauge.metric-ok {
  border-color: rgba(34, 197, 94, 0.5);
  background: rgba(34, 197, 94, 0.08);
}

.metric-gauge.metric-ok .gauge-value {
  color: var(--el-color-success);
}

.gauge-value {
  font-size: 24px;
  font-weight: 800;
  color: var(--color-primary);
  margin-bottom: 4px;
}

.gauge-label {
  font-size: 11px;
  color: #94a3b8;
  margin-bottom: 2px;
}

.gauge-target {
  font-size: 10px;
  color: #64748b;
  margin-bottom: 8px;
}

.gauge-bar {
  height: 4px;
  background: rgba(71, 85, 105, 0.5);
  border-radius: 2px;
  overflow: hidden;
}

.gauge-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary), var(--color-secondary));
  border-radius: 2px;
  /* Transition */
  transition: all 0.3s ease;
}

.metric-accuracy .gauge-fill {
  background: linear-gradient(90deg, var(--el-color-success), var(--color-primary));
}

/* 深度学习操作按钮 */
.dl-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

/* 训练进度 */
.training-progress {
  margin: 12px 0;
  padding: 12px;
  background: rgba(30, 41, 59, 0.5);
  border-radius: 8px;
  border: 1px solid rgba(34, 211, 238, 0.3);
}

.progress-text {
  text-align: center;
  font-size: 12px;
  color: var(--color-primary);
  margin-top: 8px;
}

/* 训练结果 */
.dl-train-result {
  margin-top: 12px;
  padding: 12px;
  background: var(--el-bg-color-overlay);
  border-radius: 8px;
  border: 1px solid var(--color-border);
}

.result-header {
  margin-bottom: 10px;
}

.result-metrics {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.result-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 10px;
  background: rgba(15, 23, 42, 0.5);
  border-radius: 6px;
  border: 1px solid var(--color-border);
}

.item-label {
  font-size: 11px;
  color: var(--color-text-muted);
}

.item-value {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-main);
}

.item-value.highlight {
  color: var(--color-primary);
  font-size: 14px;
}

/* 训练历史曲线图 */
.training-charts {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--color-border);
}

.chart-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-main);
  margin-bottom: 10px;
  text-align: center;
}

.training-chart {
  height: 180px;
  margin-bottom: 10px;
}

/* 智能决策面板 */
.decision-panel {
  margin-top: 14px;
  padding: 14px;
  background: linear-gradient(135deg, rgba(34, 211, 238, 0.05) 0%, rgba(168, 85, 247, 0.05) 100%);
  border: 1px solid rgba(34, 211, 238, 0.2);
  border-radius: 10px;
}

.decision-header {
  font-size: 13px;
  font-weight: 700;
  color: var(--color-text-main);
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--color-border);
}

.decision-content {
  display: grid;
  gap: 12px;
}

.decision-section {
  padding: 10px;
  background: rgba(15, 23, 42, 0.4);
  border-radius: 8px;
}

.section-label {
  font-size: 10px;
  color: var(--color-text-dim);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: 6px;
}

.classification-result {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.class-label {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-primary);
}

.class-confidence {
  font-size: 12px;
  color: var(--color-text-muted);
}

/* 科学价值评分 */
.science-score {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin-bottom: 10px;
}

.score-value {
  font-size: 32px;
  font-weight: 800;
  background: linear-gradient(135deg, var(--color-primary), var(--color-secondary));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.score-label {
  font-size: 14px;
  color: var(--color-text-dim);
}

/* 雷达图 */
.radar-chart {
  height: 200px;
}

@media (max-width: 600px) {
  .metrics-dashboard {
    grid-template-columns: 1fr;
  }

  .result-metrics {
    grid-template-columns: 1fr;
  }

  .training-chart {
    height: 150px;
  }

  .radar-chart {
    height: 160px;
  }
}
</style>
