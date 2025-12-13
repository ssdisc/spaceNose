<template>
  <div class="page">
    <header class="page-head">
      <div class="title">
        <p class="eyebrow">Real-time Monitor</p>
        <h2>实时数据监控</h2>
        <p class="lead">
          WebSocket 实时推送 + 数据库历史查询。页面风格与“地面验证实验台”保持一致，用于 Year 1 演示。
        </p>
      </div>
      <div class="head-actions">
        <el-tag :type="connectionTagType" effect="dark">{{ connectionTagText }}</el-tag>
        <el-tag :type="sensorTagType" effect="plain">传感器：{{ sensorStatusText }}</el-tag>
        <el-button type="primary" :disabled="isConnected || wsConnecting" @click="connectWebSocket">
          {{ wsConnecting ? '连接中…' : '连接' }}
        </el-button>
        <el-button :disabled="!isConnected" @click="disconnectWebSocket">断开</el-button>
      </div>
    </header>

    <el-tabs v-model="activeTab" class="tabs">
      <el-tab-pane label="实时" name="realtime">
        <el-row :gutter="14">
          <el-col :xs="24" :sm="12" :md="6">
            <el-card class="glass metric-card" shadow="hover">
              <div class="metric-top">
                <div>
                  <div class="metric-label">ADC 原始值</div>
                  <div class="metric-unit">数字量</div>
                </div>
              </div>
              <div class="metric-value">{{ sensorData.adc }}</div>
            </el-card>
          </el-col>
          <el-col :xs="24" :sm="12" :md="6">
            <el-card class="glass metric-card" shadow="hover">
              <div class="metric-top">
                <div>
                  <div class="metric-label">电压</div>
                  <div class="metric-unit">V</div>
                </div>
              </div>
              <div class="metric-value">{{ formatNumber(sensorData.voltage, 3) }}</div>
            </el-card>
          </el-col>
          <el-col :xs="24" :sm="12" :md="6">
            <el-card class="glass metric-card" shadow="hover">
              <div class="metric-top">
                <div>
                  <div class="metric-label">数据计数</div>
                  <div class="metric-unit">counter</div>
                </div>
              </div>
              <div class="metric-value">{{ sensorData.counter }}</div>
            </el-card>
          </el-col>
          <el-col :xs="24" :sm="12" :md="6">
            <el-card class="glass metric-card" shadow="hover">
              <div class="metric-top">
                <div>
                  <div class="metric-label">酒精浓度</div>
                  <div class="metric-unit">ppm</div>
                </div>
                <el-tag :type="ppmTagType" effect="dark">{{ ppmStatusText }}</el-tag>
              </div>
              <div class="metric-value">{{ formatNumber(sensorData.alcohol_ppm, 2) }}</div>
            </el-card>
          </el-col>
        </el-row>

        <el-row :gutter="14" class="section">
          <el-col :xs="24" :lg="16">
            <el-card class="glass chart-card" shadow="hover">
              <template #header>
                <div class="card-header-row">
                  <div>酒精浓度趋势（alcohol_ppm）</div>
                  <div class="small-meta">
                    <span>点数：{{ chartPoints.length }}</span>
                    <span v-if="sensorData.timestamp">更新时间：{{ sensorData.timestamp }}</span>
                  </div>
                </div>
              </template>
              <v-chart class="chart" :option="chartOption" autoresize />
            </el-card>
          </el-col>
          <el-col :xs="24" :lg="8">
            <el-card class="glass chart-card" shadow="hover">
              <template #header>
                <div class="card-header-row">
                  <div>数据快照</div>
                  <el-button text @click="fetchRecentData">同步历史</el-button>
                </div>
              </template>
              <div class="kv">
                <div class="kv-item">
                  <span class="kv-key">timestamp</span>
                  <span class="kv-value">{{ sensorData.timestamp || '—' }}</span>
                </div>
                <div class="kv-item">
                  <span class="kv-key">sensor_status</span>
                  <span class="kv-value">{{ sensorStatusText }}</span>
                </div>
                <div class="kv-item">
                  <span class="kv-key">adc</span>
                  <span class="kv-value">{{ sensorData.adc }}</span>
                </div>
                <div class="kv-item">
                  <span class="kv-key">voltage</span>
                  <span class="kv-value">{{ formatNumber(sensorData.voltage, 3) }} V</span>
                </div>
                <div class="kv-item">
                  <span class="kv-key">alcohol_ppm</span>
                  <span class="kv-value">{{ formatNumber(sensorData.alcohol_ppm, 2) }} ppm</span>
                </div>
              </div>
              <div class="hint">
                该页面主要用于对接“真实链路”效果展示；更完整的模拟与导出能力请在“实验台”页面使用。
              </div>
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>

      <el-tab-pane label="历史" name="history">
        <el-row :gutter="14">
          <el-col :xs="24" :lg="7">
            <el-card class="glass" shadow="hover">
              <template #header>
                <div class="panel-title">查询条件</div>
              </template>
              <el-form label-position="top" class="form">
                <el-form-item label="最近记录数">
                  <el-select v-model.number="historyLimit" @change="fetchRecentData">
                    <el-option label="最近 20 条" :value="20" />
                    <el-option label="最近 50 条" :value="50" />
                    <el-option label="最近 100 条" :value="100" />
                  </el-select>
                </el-form-item>

                <el-form-item label="快速范围">
                  <el-radio-group v-model="timeFilter.preset" @change="onPresetChange">
                    <el-radio-button label="hour">本小时</el-radio-button>
                    <el-radio-button label="day">今日</el-radio-button>
                    <el-radio-button label="month">本月</el-radio-button>
                    <el-radio-button label="year">今年</el-radio-button>
                    <el-radio-button label="custom">自定义</el-radio-button>
                  </el-radio-group>
                </el-form-item>

                <el-form-item label="时间范围">
                  <el-date-picker
                    v-model="timeFilter.range"
                    type="datetimerange"
                    range-separator="至"
                    start-placeholder="开始时间"
                    end-placeholder="结束时间"
                    @change="onRangeChange"
                  />
                </el-form-item>

                <div class="btn-row">
                  <el-button type="primary" @click="applyTimeFilter">筛选</el-button>
                  <el-button :disabled="!timeFilter.isActive" @click="resetTimeFilter">清除</el-button>
                  <el-button @click="fetchRecentData">刷新</el-button>
                </div>

                <div class="hint">
                  “快速范围”会直接执行筛选；选择自定义时间后点击“筛选”生效。
                </div>
              </el-form>
            </el-card>
          </el-col>

          <el-col :xs="24" :lg="17">
            <el-card class="glass chart-card" shadow="hover">
              <template #header>
                <div class="card-header-row">
                  <div>历史趋势（alcohol_ppm）</div>
                  <div class="small-meta">
                    <el-tag v-if="timeFilter.isActive" type="warning" effect="plain">已筛选</el-tag>
                    <span>共 {{ dataLogs.length }} 条</span>
                  </div>
                </div>
              </template>
              <v-chart class="chart" :option="chartOption" autoresize />
            </el-card>

            <el-card class="glass table-card" shadow="hover">
              <template #header>
                <div class="card-header-row">
                  <div>历史记录</div>
                  <div class="small-meta">
                    <el-button text @click="fetchRecentData">拉取最近</el-button>
                  </div>
                </div>
              </template>
              <el-table :data="dataLogs" stripe height="440">
                <el-table-column prop="timestamp" label="时间" width="180" />
                <el-table-column prop="counter" label="计数" width="90" />
                <el-table-column prop="adc" label="ADC" width="90" />
                <el-table-column label="电压 (V)" width="110">
                  <template #default="scope">
                    {{ formatNumber(scope.row.voltage, 3) }}
                  </template>
                </el-table-column>
                <el-table-column label="酒精 (ppm)" width="110">
                  <template #default="scope">
                    {{ formatNumber(scope.row.alcohol_ppm, 2) }}
                  </template>
                </el-table-column>
                <el-table-column label="传感器" width="120">
                  <template #default="scope">
                    <el-tag :type="sensorStatusTagType(scope.row.sensor_status)" effect="plain">
                      {{ sensorStatusTextOf(scope.row.sensor_status) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="原始对象">
                  <template #default="scope">
                    <span class="raw">{{ rawSummary(scope.row) }}</span>
                  </template>
                </el-table-column>
                <template #empty>
                  <div class="empty">暂无历史数据</div>
                </template>
              </el-table>
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script>
import dayjs from 'dayjs'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'

use([LineChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

export default {
  name: 'RealTimeMonitor',
  components: {
    VChart
  },
  data() {
    return {
      ws: null,
      wsConnecting: false,
      reconnectEnabled: true,

      isConnected: false,
      activeTab: 'realtime',

      sensorData: {
        counter: 0,
        adc: 0,
        voltage: 0,
        alcohol_ppm: 0,
        sensor_status: 3,
        timestamp: ''
      },

      dataLogs: [],
      historyLimit: 50,

      chartPoints: [],
      maxDataPoints: 120,

      timeFilter: {
        range: [],
        preset: 'hour',
        isActive: false
      }
    }
  },
  computed: {
    connectionTagType() {
      return this.isConnected ? 'success' : 'info'
    },
    connectionTagText() {
      if (this.wsConnecting) return '连接中'
      return this.isConnected ? 'WebSocket 已连接' : 'WebSocket 未连接'
    },
    sensorStatusText() {
      return this.sensorStatusTextOf(this.sensorData.sensor_status)
    },
    sensorTagType() {
      return this.sensorStatusTagType(this.sensorData.sensor_status)
    },
    ppmStatusText() {
      const ppm = Number(this.sensorData.alcohol_ppm ?? 0)
      if (ppm >= 200) return '危险'
      if (ppm >= 50) return '预警'
      return '正常'
    },
    ppmTagType() {
      const ppm = Number(this.sensorData.alcohol_ppm ?? 0)
      if (ppm >= 200) return 'danger'
      if (ppm >= 50) return 'warning'
      return 'success'
    },
    chartOption() {
      const labels = this.chartPoints.map((p) => p.label)
      const values = this.chartPoints.map((p) => p.value)
      return {
        tooltip: { trigger: 'axis' },
        legend: {
          top: 0,
          data: ['alcohol_ppm'],
          textStyle: { color: '#475569', fontSize: 12 }
        },
        grid: { left: 44, right: 18, top: 34, bottom: 34 },
        xAxis: {
          type: 'category',
          data: labels,
          axisLabel: { color: '#64748b' },
          axisLine: { lineStyle: { color: '#cbd5e1' } }
        },
        yAxis: {
          type: 'value',
          name: 'ppm',
          nameTextStyle: { color: '#64748b' },
          axisLabel: { color: '#64748b' },
          splitLine: { lineStyle: { color: '#e2e8f0' } }
        },
        series: [
          {
            name: 'alcohol_ppm',
            type: 'line',
            smooth: true,
            showSymbol: false,
            connectNulls: true,
            lineStyle: { color: '#4f46e5', width: 2 },
            itemStyle: { color: '#4f46e5' },
            data: values
          }
        ]
      }
    }
  },
  watch: {
    activeTab(tab) {
      if (tab === 'history') {
        if (this.timeFilter.isActive && this.timeFilter.range.length === 2) {
          this.applyTimeFilter()
        } else {
          this.fetchRecentData()
        }
      }
    }
  },
  mounted() {
    this.initializeTimeFilter()
    this.fetchRecentData()
    this.connectWebSocket()
  },
  beforeUnmount() {
    this.disconnectWebSocket()
  },
  methods: {
    formatNumber(value, precision) {
      const v = Number(value ?? 0)
      if (Number.isNaN(v)) return '—'
      return v.toFixed(precision)
    },
    sensorStatusTextOf(statusValue) {
      const status = Number(statusValue)
      const statusMap = {
        0: '就绪',
        1: '预热中',
        2: '错误',
        3: '未就绪'
      }
      return statusMap[status] !== undefined ? statusMap[status] : '未知'
    },
    sensorStatusTagType(statusValue) {
      const status = Number(statusValue)
      if (status === 0) return 'success'
      if (status === 1) return 'warning'
      if (status === 2) return 'danger'
      if (status === 3) return 'info'
      return 'info'
    },
    rawSummary(row) {
      const adc = row?.adc ?? '—'
      const voltage = this.formatNumber(row?.voltage, 3)
      const ppm = this.formatNumber(row?.alcohol_ppm, 2)
      return `adc=${adc}, voltage=${voltage}V, alcohol=${ppm}ppm`
    },

    apiBaseUrl() {
      const protocol = window.location.protocol === 'https:' ? 'https' : 'http'
      return `${protocol}://${window.location.hostname}:8000`
    },

    initializeTimeFilter() {
      const now = new Date()
      const start = new Date(now)
      start.setMinutes(0, 0, 0)
      this.timeFilter.range = [start, now]
      this.timeFilter.preset = 'hour'
      this.timeFilter.isActive = false
    },

    onPresetChange(preset) {
      if (preset === 'custom') {
        this.timeFilter.isActive = false
        return
      }
      this.setQuickRange(preset)
    },

    onRangeChange() {
      this.timeFilter.preset = 'custom'
      this.timeFilter.isActive = false
    },

    setQuickRange(preset) {
      const now = new Date()
      let start = new Date(now)

      if (preset === 'hour') {
        start.setMinutes(0, 0, 0)
      } else if (preset === 'day') {
        start.setHours(0, 0, 0, 0)
      } else if (preset === 'month') {
        start.setDate(1)
        start.setHours(0, 0, 0, 0)
      } else if (preset === 'year') {
        start.setMonth(0, 1)
        start.setHours(0, 0, 0, 0)
      }

      this.timeFilter.range = [start, now]
      this.timeFilter.preset = preset
      this.applyTimeFilter()
    },

    formatDateTimeForApi(date) {
      return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
    },

    parseTimestamp(ts) {
      if (!ts) return null
      const normalized = String(ts).replace(' ', 'T')
      const parsed = new Date(normalized)
      return Number.isNaN(parsed.getTime()) ? null : parsed
    },

    isWithinFilter(timestamp) {
      if (!this.timeFilter.isActive) return true
      if (!this.timeFilter.range || this.timeFilter.range.length !== 2) return true
      const start = this.timeFilter.range[0]?.getTime?.()
      const end = this.timeFilter.range[1]?.getTime?.()
      const target = this.parseTimestamp(timestamp)?.getTime?.()
      if (!start || !end || !target) return true
      return target >= start && target <= end
    },

    applyTimeFilter() {
      if (!this.timeFilter.range || this.timeFilter.range.length !== 2) return
      const startDate = this.timeFilter.range[0]
      const endDate = this.timeFilter.range[1]
      if (!(startDate instanceof Date) || !(endDate instanceof Date)) return
      if (startDate.getTime() > endDate.getTime()) return

      const start = this.formatDateTimeForApi(startDate)
      const end = this.formatDateTimeForApi(endDate)
      this.fetchDataByRange(start, end)
    },

    resetTimeFilter() {
      this.initializeTimeFilter()
      this.fetchRecentData()
    },

    seedChartFromLogs(logs) {
      const seeded = [...logs]
        .slice()
        .sort((a, b) => {
          const aTime = this.parseTimestamp(a.timestamp)?.getTime?.() ?? 0
          const bTime = this.parseTimestamp(b.timestamp)?.getTime?.() ?? 0
          return aTime - bTime
        })
        .slice(-this.maxDataPoints)
        .map((item) => ({
          label: this.formatTimeLabel(item.timestamp),
          value: Number(item.alcohol_ppm ?? 0)
        }))
      this.chartPoints = seeded
    },

    pushChartPoint(timestamp, value) {
      this.chartPoints.push({
        label: this.formatTimeLabel(timestamp),
        value: Number(value ?? 0)
      })
      if (this.chartPoints.length > this.maxDataPoints) {
        this.chartPoints.shift()
      }
    },

    formatTimeLabel(timestamp) {
      const parsed = this.parseTimestamp(timestamp)
      if (!parsed) return dayjs().format('HH:mm:ss')
      return dayjs(parsed).format('HH:mm:ss')
    },

    async fetchRecentData() {
      try {
        const response = await fetch(`${this.apiBaseUrl()}/api/data/recent?limit=${this.historyLimit}`)
        const json = await response.json()
        if (json.success && Array.isArray(json.data)) {
          const normalized = json.data.map((item) => ({
            counter: item.counter ?? 0,
            adc: item.adc ?? 0,
            voltage: item.voltage ?? 0,
            alcohol_ppm: item.alcohol_ppm ?? 0,
            sensor_status: item.sensor_status ?? 3,
            timestamp: item.timestamp ?? ''
          }))
          this.timeFilter.isActive = false
          this.timeFilter.preset = 'hour'
          this.applyHistoryData(normalized)
        }
      } catch (error) {
        // ignore
      }
    },

    async fetchDataByRange(start, end) {
      try {
        const response = await fetch(
          `${this.apiBaseUrl()}/api/data/range?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`
        )
        const json = await response.json()
        if (json.success && Array.isArray(json.data)) {
          const normalized = json.data.map((item) => ({
            counter: item.counter ?? 0,
            adc: item.adc ?? 0,
            voltage: item.voltage ?? 0,
            alcohol_ppm: item.alcohol_ppm ?? 0,
            sensor_status: item.sensor_status ?? 3,
            timestamp: item.timestamp ?? ''
          }))
          this.timeFilter.isActive = true
          this.applyHistoryData(normalized)
        }
      } catch (error) {
        // ignore
      }
    },

    applyHistoryData(logs) {
      const sortedLogs = [...logs].sort((a, b) => {
        const aTime = this.parseTimestamp(a.timestamp)?.getTime?.() ?? 0
        const bTime = this.parseTimestamp(b.timestamp)?.getTime?.() ?? 0
        return bTime - aTime
      })
      this.dataLogs = sortedLogs

      if (this.activeTab === 'realtime' && this.dataLogs.length > 0) {
        this.sensorData = this.dataLogs[0]
      }

      this.seedChartFromLogs(this.dataLogs)
    },

    connectWebSocket() {
      if (this.isConnected || this.wsConnecting) return
      this.reconnectEnabled = true
      this.wsConnecting = true

      const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
      const wsUrl = `${protocol}://${window.location.hostname}:8000/ws`
      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        this.wsConnecting = false
        this.isConnected = true
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          const normalized = {
            counter: data.counter ?? 0,
            adc: data.adc ?? 0,
            voltage: data.voltage ?? 0,
            alcohol_ppm: data.alcohol_ppm ?? 0,
            sensor_status: data.sensor_status !== undefined ? data.sensor_status : 3,
            timestamp: data.timestamp ?? ''
          }

          this.sensorData = normalized
          const withinFilter = this.isWithinFilter(normalized.timestamp)

          if (!this.timeFilter.isActive || withinFilter) {
            this.dataLogs.unshift(normalized)
            if (!this.timeFilter.isActive && this.dataLogs.length > this.historyLimit) {
              this.dataLogs.pop()
            }
            this.pushChartPoint(normalized.timestamp, normalized.alcohol_ppm)
          }
        } catch (error) {
          // ignore
        }
      }

      this.ws.onerror = () => {
        this.wsConnecting = false
        this.isConnected = false
      }

      this.ws.onclose = () => {
        this.wsConnecting = false
        this.isConnected = false
        if (this.reconnectEnabled) {
          setTimeout(() => {
            this.connectWebSocket()
          }, 5000)
        }
      }
    },

    disconnectWebSocket() {
      this.reconnectEnabled = false
      if (this.ws) {
        try {
          this.ws.close()
        } catch (error) {
          // ignore
        }
      }
      this.ws = null
      this.wsConnecting = false
      this.isConnected = false
    }
  }
}
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.page-head {
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
  max-width: 720px;
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

.metric-card {
  min-height: 120px;
}

.metric-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 10px;
}

.metric-label {
  font-weight: 800;
  color: #0f172a;
}

.metric-unit {
  margin-top: 2px;
  font-size: 12px;
  color: #64748b;
}

.metric-value {
  margin-top: 10px;
  font-size: 28px;
  font-weight: 900;
  letter-spacing: -0.3px;
  color: #111827;
}

.section {
  margin-top: 10px;
}

.chart-card :deep(.el-card__body) {
  padding-top: 10px;
}

.chart {
  height: 360px;
}

.table-card {
  margin-top: 12px;
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

.kv {
  display: grid;
  gap: 10px;
}

.kv-item {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px;
}

.kv-key {
  color: #64748b;
  font-size: 12px;
}

.kv-value {
  color: #0f172a;
  font-weight: 700;
  font-size: 12px;
  text-align: right;
  word-break: break-all;
}

.hint {
  margin-top: 12px;
  color: #475569;
  background: #f8fafc;
  border: 1px dashed #e2e8f0;
  padding: 10px;
  border-radius: 10px;
  line-height: 1.5;
}

.raw {
  color: #64748b;
  font-size: 12px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
}

.empty {
  padding: 24px 0;
  color: #94a3b8;
  text-align: center;
}

@media (max-width: 900px) {
  .page-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .chart {
    height: 300px;
  }
}
</style>
