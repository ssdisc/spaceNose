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

    <el-row :gutter="14">
      <el-col :xs="24" :lg="7">
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

            <el-collapse>
              <el-collapse-item title="后端字段映射（仅对接后端）" name="mapping">
                <el-form-item label="来源字段">
                  <el-select v-model="realtimeSourceField">
                    <el-option label="alcohol_ppm" value="alcohol_ppm" />
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

      <el-col :xs="24" :lg="17">
        <el-row :gutter="14">
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

        <el-row :gutter="14" class="section">
          <el-col :xs="24" :lg="16">
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
          <el-col :xs="24" :lg="8">
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
import { LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import * as XLSX from 'xlsx'
import { jsPDF } from 'jspdf'
import { autoTable } from 'jspdf-autotable'

use([LineChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

const GAS_META = [
  { key: 'ch4', label: '甲烷 CH₄', unit: 'ppm', axis: 0, color: '#22c55e' },
  { key: 'ph3', label: '磷化氢 PH₃', unit: 'ppb', axis: 1, color: '#a855f7' },
  { key: 'so2', label: '二氧化硫 SO₂', unit: 'ppm', axis: 0, color: '#f59e0b' },
  { key: 'h2s', label: '硫化氢 H₂S', unit: 'ppm', axis: 0, color: '#ef4444' },
  { key: 'co2', label: '二氧化碳 CO₂', unit: 'ppm', axis: 0, color: '#0ea5e9' },
  { key: 'vocs', label: 'VOCs', unit: 'ppb', axis: 1, color: '#64748b' }
]

const SCENARIO_PRESETS = {
  mars: { ch4: 2.0, ph3: 1, so2: 0.1, h2s: 0.05, co2: 800, vocs: 20 },
  venus: { ch4: 0.2, ph3: 20, so2: 0.8, h2s: 0.02, co2: 2000, vocs: 10 },
  comet: { ch4: 0.6, ph3: 3, so2: 0.05, h2s: 0.1, co2: 300, vocs: 80 },
  custom: null
}

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
      mode: 'simulation',
      scenario: 'mars',
      scenarioOptions: [
        { label: '火星 CH₄ 基线', value: 'mars' },
        { label: '金星 PH₃ 痕量', value: 'venus' },
        { label: '彗星挥发物', value: 'comet' },
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
      }
    }
  },
  computed: {
    gases() {
      return GAS_META
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
        tooltip: { trigger: 'axis' },
        legend: {
          top: 0,
          textStyle: { color: '#475569', fontSize: 12 }
        },
        grid: { left: 40, right: 46, top: 44, bottom: 34 },
        xAxis: {
          type: 'category',
          data: labels,
          axisLabel: { color: '#64748b' },
          axisLine: { lineStyle: { color: '#cbd5e1' } }
        },
        yAxis: [
          {
            type: 'value',
            name: 'ppm',
            nameTextStyle: { color: '#64748b' },
            axisLabel: { color: '#64748b' },
            splitLine: { lineStyle: { color: '#e2e8f0' } }
          },
          {
            type: 'value',
            name: 'ppb',
            nameTextStyle: { color: '#64748b' },
            axisLabel: { color: '#64748b' },
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
    },
    formatNumber(value, unit) {
      const precision = unit === 'ppb' ? 0 : 3
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
        if (this.realtimeSourceField === 'adc') return Number(payload.adc ?? 0)
        if (this.realtimeSourceField === 'voltage') return Number(payload.voltage ?? 0)
        return Number(payload.alcohol_ppm ?? 0)
      }

      const mappedValue = getFieldValue() * Number(this.realtimeScale || 1)
      const point = {
        t: Date.now(),
        tLabel: payload.timestamp ? String(payload.timestamp).slice(11, 19) : dayjs().format('HH:mm:ss')
      }
      GAS_META.forEach((gas) => {
        point[gas.key] = null
      })
      point[this.realtimeMapGas] = mappedValue
      this.appendPoint(point)
      this.checkAlerts(point)
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
    }
  }
}
</script>

<style scoped>
.lab {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.lab-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 14px;
  padding: 6px 8px 2px;
}

.eyebrow {
  margin: 0;
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #6b7280;
}

.title h2 {
  margin: 4px 0;
  font-size: 22px;
  font-weight: 800;
  color: #0f172a;
  letter-spacing: -0.2px;
}

.lead {
  margin: 0;
  color: #4b5563;
  line-height: 1.6;
  max-width: 680px;
}

.head-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-top: 2px;
  flex-wrap: wrap;
}

.glass {
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(148, 163, 184, 0.22);
}

.panel-title {
  font-weight: 800;
  color: #111827;
}

.form :deep(.el-form-item) {
  margin-bottom: 12px;
}

.btn-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 6px;
}

.export-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px 12px;
}

.hint {
  margin-top: 8px;
  color: #475569;
  background: #f8fafc;
  border: 1px dashed #e2e8f0;
  padding: 8px 10px;
  border-radius: 10px;
  line-height: 1.5;
}

.gas-card {
  min-height: 120px;
}

.gas-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
}

.gas-label {
  font-weight: 800;
  color: #0f172a;
}

.gas-unit {
  font-size: 12px;
  color: #64748b;
  margin-top: 2px;
}

.gas-value {
  margin-top: 10px;
  font-size: 28px;
  font-weight: 900;
  letter-spacing: -0.3px;
  color: #111827;
}

.gas-sub {
  margin-top: 8px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  color: #64748b;
  font-size: 12px;
}

.section {
  margin-top: 10px;
}

.chart {
  height: 360px;
}

.card-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.small-meta {
  display: flex;
  gap: 10px;
  align-items: center;
  color: #64748b;
  font-size: 12px;
}

.metric {
  margin-bottom: 14px;
}

.metric-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  color: #111827;
}

.metric-label {
  font-weight: 700;
  color: #0f172a;
}

.metric-value {
  color: #475569;
  font-size: 12px;
}

.mini-log {
  margin-top: 10px;
  border-top: 1px solid #e2e8f0;
  padding-top: 10px;
}

.mini-log-list {
  display: grid;
  gap: 8px;
}

.mini-log-item {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 8px;
  align-items: start;
}

.mini-log-text {
  color: #334155;
  line-height: 1.4;
  font-size: 12px;
}

.empty {
  color: #94a3b8;
  font-size: 12px;
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
</style>
