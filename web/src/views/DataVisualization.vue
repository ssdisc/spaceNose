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
        <el-tag :type="mlAnomalyTagType" effect="plain">ML异常：{{ mlAnomalyTagText }}</el-tag>
        <el-button type="primary" :disabled="isConnected || wsConnecting" @click="connectWebSocket">
          {{ wsConnecting ? '连接中…' : '连接' }}
        </el-button>
        <el-button :disabled="!isConnected" @click="disconnectWebSocket">断开</el-button>
      </div>
    </header>

    <el-tabs v-model="activeTab" class="tabs">
      <el-tab-pane label="实时" name="realtime">
        <el-row :gutter="14">
          <el-col :xs="24" :sm="12" :md="8">
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
          <el-col :xs="24" :sm="12" :md="8">
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
          <el-col :xs="24" :sm="12" :md="8">
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
          <el-col :xs="24" :sm="12" :md="8">
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
          <el-col :xs="24" :sm="12" :md="8">
            <el-card class="glass metric-card" shadow="hover">
              <div class="metric-top">
                <div>
                  <div class="metric-label">二氧化碳 CO₂</div>
                  <div class="metric-unit">ppm</div>
                </div>
                <el-tag :type="co2TagType" effect="dark">{{ co2StatusText }}</el-tag>
              </div>
              <div class="metric-value">{{ co2Display }}</div>
            </el-card>
          </el-col>
        </el-row>

        <el-row :gutter="14" class="section">
          <el-col :xs="24" :lg="16">
            <el-card class="glass chart-card" shadow="hover">
              <template #header>
                <div class="card-header-row">
                  <div>趋势（alcohol_ppm / co2_ppm）</div>
                  <div class="small-meta">
                    <span>点数：{{ chartPoints.length }}</span>
                    <span v-if="sensorData.timestamp">更新时间：{{ sensorData.timestamp }}</span>
                  </div>
                </div>
              </template>
              <v-chart class="chart" :option="chartOption" autoresize />
            </el-card>

            <!-- 异常检测时序图 -->
            <el-card class="glass chart-card anomaly-chart-card" shadow="hover">
              <template #header>
                <div class="card-header-row">
                  <div>异常检测分数</div>
                  <div class="small-meta">
                    <el-tag :type="currentAnomalyStatus.tagType" effect="dark" size="small">
                      {{ currentAnomalyStatus.text }}
                    </el-tag>
                    <span>阈值: 0</span>
                  </div>
                </div>
              </template>
              <v-chart class="chart anomaly-chart" :option="anomalyChartOption" autoresize />
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
                <div class="kv-item">
                  <span class="kv-key">co2_ppm</span>
                  <span class="kv-value">{{ sensorData.co2_ppm == null ? '—' : `${formatNumber(sensorData.co2_ppm, 1)} ppm` }}</span>
                </div>
                <div class="kv-item">
                  <span class="kv-key">ml.anomaly</span>
                  <span class="kv-value">{{ mlAnomalyDetailText }}</span>
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
                  <div>历史趋势（alcohol_ppm / co2_ppm）</div>
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
                    <span>共 {{ totalLogs }} 条</span>
                    <el-button text @click="fetchRecentData">拉取最近</el-button>
                  </div>
                </div>
              </template>
              <el-table :data="paginatedLogs" stripe height="400">
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
                <el-table-column label="CO₂ (ppm)" width="110">
                  <template #default="scope">
                    {{ scope.row.co2_ppm == null ? '—' : formatNumber(scope.row.co2_ppm, 1) }}
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
              <div class="pagination-wrap">
                <el-pagination
                  v-model:current-page="pagination.currentPage"
                  v-model:page-size="pagination.pageSize"
                  :page-sizes="pagination.pageSizes"
                  :total="totalLogs"
                  layout="total, sizes, prev, pager, next, jumper"
                  background
                  @size-change="onPageSizeChange"
                  @current-change="onPageChange"
                />
              </div>
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
import { GridComponent, LegendComponent, TooltipComponent, TitleComponent, MarkLineComponent, VisualMapComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'

use([LineChart, GridComponent, LegendComponent, TooltipComponent, TitleComponent, MarkLineComponent, VisualMapComponent, CanvasRenderer])

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
        co2_ppm: null,
        sensor_status: 3,
        timestamp: '',
        ml: null
      },

      dataLogs: [],
      historyLimit: 50,

      chartPoints: [],
      anomalyPoints: [],            // 异常检测分数时序数据
      maxDataPoints: 120,           // 实时模式最大点数
      maxChartPointsHistory: 0,     // 历史模式：0表示不限制，显示全部

      // 表格分页
      pagination: {
        currentPage: 1,
        pageSize: 50,
        pageSizes: [20, 50, 100, 200]
      },

      timeFilter: {
        range: [],
        preset: 'hour',
        isActive: false
      },

      mlAnomalyTraining: false,
      mlAnomalyTrainResult: null
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
    co2StatusText() {
      const co2 = this.sensorData.co2_ppm
      if (co2 == null) return '未接入'
      const ppm = Number(co2)
      if (Number.isNaN(ppm)) return '未知'
      if (ppm >= 10000) return '危险'
      if (ppm >= 5000) return '预警'
      return '正常'
    },
    co2TagType() {
      const co2 = this.sensorData.co2_ppm
      if (co2 == null) return 'info'
      const ppm = Number(co2)
      if (Number.isNaN(ppm)) return 'info'
      if (ppm >= 10000) return 'danger'
      if (ppm >= 5000) return 'warning'
      return 'success'
    },
    co2Display() {
      const co2 = this.sensorData.co2_ppm
      if (co2 == null) return '—'
      const ppm = Number(co2)
      if (Number.isNaN(ppm)) return '—'
      return ppm.toFixed(1)
    },
    mlAnomalyTagText() {
      const anomaly = this.sensorData.ml?.anomaly
      if (!anomaly) return '未计算'
      if (!anomaly.ok) return anomaly.error || '未训练'
      return anomaly.label === 'anomaly' ? '异常' : '正常'
    },
    mlAnomalyTagType() {
      const anomaly = this.sensorData.ml?.anomaly
      if (!anomaly) return 'info'
      if (!anomaly.ok) return 'info'
      return anomaly.label === 'anomaly' ? 'danger' : 'success'
    },
    mlAnomalyDetailText() {
      const anomaly = this.sensorData.ml?.anomaly
      if (!anomaly) return '—'
      if (!anomaly.ok) return anomaly.error || '—'
      const score = typeof anomaly.score === 'number' ? anomaly.score.toFixed(4) : String(anomaly.score)
      return `${anomaly.label} (score=${score})`
    },
    // 分页后的表格数据
    paginatedLogs() {
      const start = (this.pagination.currentPage - 1) * this.pagination.pageSize
      const end = start + this.pagination.pageSize
      return this.dataLogs.slice(start, end)
    },
    totalLogs() {
      return this.dataLogs.length
    },
    chartOption() {
      const labels = this.chartPoints.map((p) => p.label)
      const alcoholValues = this.chartPoints.map((p) => p.alcohol)
      const co2Values = this.chartPoints.map((p) => p.co2)
      const isLargeData = this.chartPoints.length > 500

      return {
        backgroundColor: 'transparent',
        // 大数据优化：关闭动画
        animation: !isLargeData,
        tooltip: {
          trigger: 'axis',
          backgroundColor: 'rgba(15, 23, 42, 0.9)',
          borderColor: 'rgba(34, 211, 238, 0.3)',
          textStyle: { color: '#e2e8f0' }
        },
        legend: {
          top: 0,
          data: ['alcohol_ppm', 'co2_ppm'],
          textStyle: { color: '#94a3b8', fontSize: 12 }
        },
        grid: { left: 44, right: 44, top: 34, bottom: 34 },
        xAxis: {
          type: 'category',
          data: labels,
          axisLabel: {
            color: '#64748b',
            // 大数据时减少标签数量
            interval: isLargeData ? Math.floor(labels.length / 10) : 'auto'
          },
          axisLine: { lineStyle: { color: 'rgba(71, 85, 105, 0.5)' } },
          axisTick: { lineStyle: { color: 'rgba(71, 85, 105, 0.5)' } }
        },
        yAxis: [
          {
            type: 'value',
            name: '酒精 ppm',
            nameTextStyle: { color: '#94a3b8' },
            axisLabel: { color: '#64748b' },
            axisLine: { lineStyle: { color: 'rgba(71, 85, 105, 0.5)' } },
            splitLine: { lineStyle: { color: 'rgba(71, 85, 105, 0.2)' } }
          },
          {
            type: 'value',
            name: 'CO₂ ppm',
            nameTextStyle: { color: '#94a3b8' },
            axisLabel: { color: '#64748b' },
            axisLine: { lineStyle: { color: 'rgba(71, 85, 105, 0.5)' } },
            splitLine: { show: false }
          }
        ],
        series: [
          {
            name: 'alcohol_ppm',
            type: 'line',
            smooth: !isLargeData, // 大数据时关闭平滑
            showSymbol: false,
            connectNulls: true,
            // 大数据优化
            large: isLargeData,
            largeThreshold: 500,
            sampling: 'lttb', // 最大三角形三桶降采样，保留视觉特征
            lineStyle: {
              color: '#a855f7',
              width: isLargeData ? 1 : 2,
              // 大数据时关闭阴影
              shadowColor: isLargeData ? 'transparent' : 'rgba(168, 85, 247, 0.5)',
              shadowBlur: isLargeData ? 0 : 10
            },
            itemStyle: { color: '#a855f7' },
            areaStyle: isLargeData ? null : {
              color: {
                type: 'linear',
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [
                  { offset: 0, color: 'rgba(168, 85, 247, 0.3)' },
                  { offset: 1, color: 'rgba(168, 85, 247, 0)' }
                ]
              }
            },
            data: alcoholValues
          },
          {
            name: 'co2_ppm',
            type: 'line',
            yAxisIndex: 1,
            smooth: !isLargeData,
            showSymbol: false,
            connectNulls: true,
            large: isLargeData,
            largeThreshold: 500,
            sampling: 'lttb',
            lineStyle: {
              color: '#22d3ee',
              width: isLargeData ? 1 : 2,
              shadowColor: isLargeData ? 'transparent' : 'rgba(34, 211, 238, 0.5)',
              shadowBlur: isLargeData ? 0 : 10
            },
            itemStyle: { color: '#22d3ee' },
            areaStyle: isLargeData ? null : {
              color: {
                type: 'linear',
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [
                  { offset: 0, color: 'rgba(34, 211, 238, 0.3)' },
                  { offset: 1, color: 'rgba(34, 211, 238, 0)' }
                ]
              }
            },
            data: co2Values
          }
        ]
      }
    },
    // 当前异常状态
    currentAnomalyStatus() {
      const anomaly = this.sensorData.ml?.anomaly
      if (!anomaly || !anomaly.ok) {
        return { text: '未检测', tagType: 'info' }
      }
      if (anomaly.label === 'anomaly') {
        return { text: '检测到异常', tagType: 'danger' }
      }
      return { text: '正常', tagType: 'success' }
    },
    // 异常检测时序图配置
    anomalyChartOption() {
      const labels = this.anomalyPoints.map((p) => p.label)
      // ECharts 标准空值 '-' 替代 null：避免 visualMap/areaStyle 渲染异常
      const scores = this.anomalyPoints.map((p) => (p.score == null ? '-' : p.score))
      const isAnomalies = this.anomalyPoints.map((p) => p.isAnomaly)

      return {
        backgroundColor: 'transparent',
        tooltip: {
          trigger: 'axis',
          backgroundColor: 'rgba(15, 23, 42, 0.9)',
          borderColor: 'rgba(239, 68, 68, 0.3)',
          textStyle: { color: '#e2e8f0' },
          formatter: (params) => {
            const idx = params[0].dataIndex
            const score = scores[idx]
            const isAnomaly = isAnomalies[idx]
            return `${params[0].axisValue}<br/>
              分数: ${typeof score === 'number' ? score.toFixed(4) : '—'}<br/>
              状态: ${isAnomaly ? '<span style="color:#ef4444">异常</span>' : '<span style="color:#22c55e">正常</span>'}`
          }
        },
        grid: { left: 50, right: 20, top: 20, bottom: 30 },
        xAxis: {
          type: 'category',
          data: labels,
          axisLabel: { color: '#64748b', fontSize: 10 },
          axisLine: { lineStyle: { color: 'rgba(71, 85, 105, 0.5)' } }
        },
        yAxis: {
          type: 'value',
          name: '异常分数',
          nameTextStyle: { color: '#94a3b8', fontSize: 10 },
          axisLabel: { color: '#64748b', fontSize: 10 },
          splitLine: { lineStyle: { color: 'rgba(71, 85, 105, 0.2)' } }
        },
        series: [
          {
            name: '异常分数',
            type: 'line',
            smooth: true,
            showSymbol: false,
            lineStyle: { color: '#22d3ee', width: 2 },
            areaStyle: {
              color: {
                type: 'linear',
                x: 0, y: 0, x2: 0, y2: 1,
                colorStops: [
                  { offset: 0, color: 'rgba(239, 68, 68, 0.3)' },
                  { offset: 0.5, color: 'rgba(239, 68, 68, 0.1)' },
                  { offset: 1, color: 'rgba(34, 197, 94, 0.1)' }
                ]
              }
            },
            markLine: {
              silent: true,
              symbol: 'none',
              lineStyle: { color: '#f59e0b', type: 'dashed', width: 1 },
              data: [{ yAxis: 0, label: { formatter: '阈值', color: '#f59e0b', fontSize: 10 } }]
            },
            data: scores
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
      const co2 = row?.co2_ppm == null ? '—' : this.formatNumber(row?.co2_ppm, 1)
      return `adc=${adc}, voltage=${voltage}V, alcohol=${ppm}ppm, co2=${co2}ppm`
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
      // 根据当前tab决定最大显示点数（0表示不限制）
      const maxPoints = this.activeTab === 'history' ? this.maxChartPointsHistory : this.maxDataPoints

      // 对数据按时间排序
      let processedLogs = [...logs]
        .slice()
        .sort((a, b) => {
          const aTime = this.parseTimestamp(a.timestamp)?.getTime?.() ?? 0
          const bTime = this.parseTimestamp(b.timestamp)?.getTime?.() ?? 0
          return aTime - bTime
        })

      // 如果设置了最大点数且数据量超过阈值，进行降采样
      if (maxPoints > 0 && processedLogs.length > maxPoints) {
        processedLogs = this.downsampleData(processedLogs, maxPoints)
      }

      const seeded = processedLogs.map((item) => ({
        label: this.formatTimeLabel(item.timestamp),
        alcohol: item.alcohol_ppm == null ? null : Number(item.alcohol_ppm),
        co2: item.co2_ppm == null ? null : Number(item.co2_ppm)
      }))
      this.chartPoints = seeded

      // 初始化异常检测数据（历史数据可能没有 ml 字段）
      const anomalySeeded = processedLogs.map((item) => {
        const anomaly = item.ml?.anomaly
        return {
          label: this.formatTimeLabel(item.timestamp),
          score: anomaly?.ok ? anomaly.score : null,
          isAnomaly: anomaly?.ok ? anomaly.label === 'anomaly' : false
        }
      })
      this.anomalyPoints = anomalySeeded
    },

    // 降采样算法：保留首尾和均匀采样
    downsampleData(data, targetCount) {
      if (data.length <= targetCount) return data
      const result = []
      const step = (data.length - 1) / (targetCount - 1)
      for (let i = 0; i < targetCount; i++) {
        const index = Math.round(i * step)
        result.push(data[index])
      }
      return result
    },

    pushChartPoint(timestamp, alcoholPpm, co2Ppm) {
      this.chartPoints.push({
        label: this.formatTimeLabel(timestamp),
        alcohol: alcoholPpm == null ? null : Number(alcoholPpm),
        co2: co2Ppm == null ? null : Number(co2Ppm)
      })
      if (this.chartPoints.length > this.maxDataPoints) {
        this.chartPoints.shift()
      }
    },

    pushAnomalyPoint(timestamp, anomalyData) {
      const score = anomalyData?.ok ? anomalyData.score : null
      const isAnomaly = anomalyData?.ok ? anomalyData.label === 'anomaly' : false
      this.anomalyPoints.push({
        label: this.formatTimeLabel(timestamp),
        score: score,
        isAnomaly: isAnomaly
      })
      if (this.anomalyPoints.length > this.maxDataPoints) {
        this.anomalyPoints.shift()
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
            co2_ppm: item.co2_ppm ?? null,
            sensor_status: item.sensor_status ?? 3,
            timestamp: item.timestamp ?? '',
            ml: null
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
            co2_ppm: item.co2_ppm ?? null,
            sensor_status: item.sensor_status ?? 3,
            timestamp: item.timestamp ?? '',
            ml: null
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
      // 重置分页到第一页
      this.pagination.currentPage = 1

      if (this.activeTab === 'realtime' && this.dataLogs.length > 0) {
        this.sensorData = this.dataLogs[0]
      }

      this.seedChartFromLogs(this.dataLogs)
    },

    // 分页事件处理
    onPageSizeChange(size) {
      this.pagination.pageSize = size
      this.pagination.currentPage = 1
    },

    onPageChange(page) {
      this.pagination.currentPage = page
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
            co2_ppm: data.co2_ppm ?? null,
            sensor_status: data.sensor_status !== undefined ? data.sensor_status : 3,
            timestamp: data.timestamp ?? '',
            ml: data.ml ?? null
          }

          this.sensorData = normalized
          const withinFilter = this.isWithinFilter(normalized.timestamp)

          if (!this.timeFilter.isActive || withinFilter) {
            this.dataLogs.unshift(normalized)
            if (!this.timeFilter.isActive && this.dataLogs.length > this.historyLimit) {
              this.dataLogs.pop()
            }
            this.pushChartPoint(normalized.timestamp, normalized.alcohol_ppm, normalized.co2_ppm)

            // 收集异常检测分数数据
            this.pushAnomalyPoint(normalized.timestamp, normalized.ml?.anomaly)
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
    },

    async trainAnomalyModel() {
      this.mlAnomalyTraining = true
      try {
        const response = await fetch(`${this.apiBaseUrl()}/api/ml/anomaly/train?limit=2000&min_samples=50`, {
          method: 'POST'
        })
        const json = await response.json()
        this.mlAnomalyTrainResult = json.data || null
      } catch (error) {
        this.mlAnomalyTrainResult = { trained: false, error: String(error) }
      } finally {
        this.mlAnomalyTraining = false
      }
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
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: #22d3ee;
  text-shadow: 0 0 15px rgba(34, 211, 238, 0.5);
}

.title h2 {
  margin: 4px 0;
  font-size: 22px;
  font-weight: 800;
  letter-spacing: -0.2px;
  background: linear-gradient(135deg, #22d3ee 0%, #a855f7 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.lead {
  margin: 0;
  color: #94a3b8;
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

/* Dark Glass Cards */
.glass {
  background: rgba(15, 23, 42, 0.8) !important;
  border: 1px solid rgba(71, 85, 105, 0.4) !important;
  backdrop-filter: blur(12px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

.glass:hover {
  border-color: rgba(34, 211, 238, 0.3) !important;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), 0 0 20px rgba(34, 211, 238, 0.1);
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
  color: #e2e8f0;
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
  background: linear-gradient(135deg, #e2e8f0 0%, #22d3ee 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  filter: drop-shadow(0 0 8px rgba(34, 211, 238, 0.3));
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

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  padding: 12px 0 0;
  border-top: 1px solid rgba(71, 85, 105, 0.3);
  margin-top: 12px;
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
  gap: 10px;
  align-items: center;
  color: #64748b;
  font-size: 12px;
}

.panel-title {
  font-weight: 800;
  color: #e2e8f0;
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
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(71, 85, 105, 0.3);
  border-radius: 10px;
  padding: 10px;
  transition: all 0.3s ease;
}

.kv-item:hover {
  border-color: rgba(34, 211, 238, 0.3);
  background: rgba(30, 41, 59, 0.8);
}

.kv-key {
  color: #64748b;
  font-size: 12px;
}

.kv-value {
  color: #22d3ee;
  font-weight: 700;
  font-size: 12px;
  text-align: right;
  word-break: break-all;
}

.hint {
  margin-top: 12px;
  color: #94a3b8;
  background: rgba(30, 41, 59, 0.5);
  border: 1px dashed rgba(71, 85, 105, 0.5);
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
  color: #64748b;
  text-align: center;
}

/* Element Plus Dark Overrides */
.glass :deep(.el-card__header) {
  background: rgba(30, 41, 59, 0.5);
  border-bottom: 1px solid rgba(71, 85, 105, 0.3);
  color: #e2e8f0;
}

/* Tabs */
.tabs :deep(.el-tabs__header) {
  margin-bottom: 16px;
}

.tabs :deep(.el-tabs__nav-wrap::after) {
  background-color: rgba(71, 85, 105, 0.3);
}

.tabs :deep(.el-tabs__item) {
  color: #64748b;
  font-weight: 500;
}

.tabs :deep(.el-tabs__item:hover) {
  color: #94a3b8;
}

.tabs :deep(.el-tabs__item.is-active) {
  color: #22d3ee;
  text-shadow: 0 0 10px rgba(34, 211, 238, 0.5);
}

.tabs :deep(.el-tabs__active-bar) {
  background: linear-gradient(90deg, #22d3ee, #a855f7);
  box-shadow: 0 0 10px rgba(34, 211, 238, 0.5);
}

/* Tags */
:deep(.el-tag) {
  border-radius: 6px;
}

:deep(.el-tag--success) {
  background: rgba(34, 197, 94, 0.15);
  border-color: rgba(34, 197, 94, 0.3);
  color: #22c55e;
}

:deep(.el-tag--warning) {
  background: rgba(245, 158, 11, 0.15);
  border-color: rgba(245, 158, 11, 0.3);
  color: #f59e0b;
}

:deep(.el-tag--danger) {
  background: rgba(239, 68, 68, 0.15);
  border-color: rgba(239, 68, 68, 0.3);
  color: #ef4444;
}

:deep(.el-tag--info) {
  background: rgba(100, 116, 139, 0.15);
  border-color: rgba(100, 116, 139, 0.3);
  color: #94a3b8;
}

/* Buttons */
:deep(.el-button--primary) {
  background: linear-gradient(135deg, #0891b2, #22d3ee) !important;
  border: none !important;
  box-shadow: 0 4px 15px rgba(34, 211, 238, 0.3);
}

:deep(.el-button--primary:hover) {
  background: linear-gradient(135deg, #22d3ee, #67e8f9) !important;
  box-shadow: 0 4px 20px rgba(34, 211, 238, 0.5);
}

:deep(.el-button--warning) {
  background: linear-gradient(135deg, #d97706, #f59e0b) !important;
  border: none !important;
  box-shadow: 0 4px 15px rgba(245, 158, 11, 0.3);
}

:deep(.el-button--warning.is-plain) {
  background: rgba(245, 158, 11, 0.1) !important;
  border: 1px solid rgba(245, 158, 11, 0.5) !important;
  color: #f59e0b !important;
}

:deep(.el-button--default) {
  background: rgba(51, 65, 85, 0.6) !important;
  border: 1px solid rgba(71, 85, 105, 0.5) !important;
  color: #94a3b8 !important;
}

:deep(.el-button--default:hover) {
  background: rgba(71, 85, 105, 0.6) !important;
  border-color: rgba(34, 211, 238, 0.5) !important;
  color: #e2e8f0 !important;
}

:deep(.el-button.is-text) {
  color: #22d3ee !important;
}

:deep(.el-button.is-text:hover) {
  color: #67e8f9 !important;
  background: rgba(34, 211, 238, 0.1) !important;
}

:deep(.el-button.is-disabled) {
  opacity: 0.5;
}

/* Form Elements */
:deep(.el-form-item__label) {
  color: #94a3b8 !important;
}

:deep(.el-select) {
  --el-fill-color-blank: rgba(30, 41, 59, 0.8);
}

:deep(.el-input__wrapper) {
  background: rgba(30, 41, 59, 0.8) !important;
  border: 1px solid rgba(71, 85, 105, 0.5) !important;
  box-shadow: none !important;
}

:deep(.el-input__wrapper:hover) {
  border-color: rgba(34, 211, 238, 0.5) !important;
}

:deep(.el-input__wrapper.is-focus) {
  border-color: #22d3ee !important;
  box-shadow: 0 0 10px rgba(34, 211, 238, 0.2) !important;
}

:deep(.el-input__inner) {
  color: #e2e8f0 !important;
}

:deep(.el-input__inner::placeholder) {
  color: #64748b !important;
}

:deep(.el-radio-button__inner) {
  background: rgba(30, 41, 59, 0.8) !important;
  border-color: rgba(71, 85, 105, 0.5) !important;
  color: #94a3b8 !important;
}

:deep(.el-radio-button__inner:hover) {
  color: #e2e8f0 !important;
}

:deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: linear-gradient(135deg, rgba(34, 211, 238, 0.2), rgba(168, 85, 247, 0.2)) !important;
  border-color: rgba(34, 211, 238, 0.5) !important;
  color: #22d3ee !important;
  box-shadow: 0 0 10px rgba(34, 211, 238, 0.3) !important;
}

/* Date Picker */
:deep(.el-date-editor) {
  --el-fill-color-blank: rgba(30, 41, 59, 0.8);
}

:deep(.el-range-input) {
  background: transparent !important;
  color: #e2e8f0 !important;
}

:deep(.el-range-separator) {
  color: #64748b !important;
}

/* Table */
:deep(.el-table) {
  background: transparent !important;
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: rgba(30, 41, 59, 0.6);
  --el-table-row-hover-bg-color: rgba(34, 211, 238, 0.05);
  --el-table-border-color: rgba(71, 85, 105, 0.3);
  --el-table-text-color: #e2e8f0;
  --el-table-header-text-color: #94a3b8;
}

:deep(.el-table__inner-wrapper::before) {
  background-color: rgba(71, 85, 105, 0.3);
}

:deep(.el-table--striped .el-table__body tr.el-table__row--striped td.el-table__cell) {
  background: rgba(30, 41, 59, 0.3);
}

:deep(.el-table th.el-table__cell) {
  background: rgba(30, 41, 59, 0.6) !important;
  font-weight: 600;
}

:deep(.el-table__empty-text) {
  color: #64748b;
}

/* Pagination */
:deep(.el-pagination) {
  --el-pagination-bg-color: rgba(30, 41, 59, 0.8);
  --el-pagination-text-color: #94a3b8;
  --el-pagination-button-color: #94a3b8;
  --el-pagination-button-bg-color: rgba(30, 41, 59, 0.8);
  --el-pagination-button-disabled-color: #475569;
  --el-pagination-button-disabled-bg-color: rgba(30, 41, 59, 0.4);
  --el-pagination-hover-color: #22d3ee;
}

:deep(.el-pagination.is-background .el-pager li) {
  background: rgba(30, 41, 59, 0.8);
  border: 1px solid rgba(71, 85, 105, 0.5);
}

:deep(.el-pagination.is-background .el-pager li:hover) {
  color: #22d3ee;
  border-color: rgba(34, 211, 238, 0.5);
}

:deep(.el-pagination.is-background .el-pager li.is-active) {
  background: linear-gradient(135deg, rgba(34, 211, 238, 0.3), rgba(168, 85, 247, 0.3));
  border-color: rgba(34, 211, 238, 0.5);
  color: #22d3ee;
}

:deep(.el-pagination.is-background .btn-prev),
:deep(.el-pagination.is-background .btn-next) {
  background: rgba(30, 41, 59, 0.8);
  border: 1px solid rgba(71, 85, 105, 0.5);
}

:deep(.el-pagination.is-background .btn-prev:hover),
:deep(.el-pagination.is-background .btn-next:hover) {
  color: #22d3ee;
  border-color: rgba(34, 211, 238, 0.5);
}

:deep(.el-pagination__total),
:deep(.el-pagination__jump) {
  color: #94a3b8;
}

:deep(.el-pagination__sizes .el-select) {
  width: 110px;
}

/* Select Dropdown (needs global style for popper) */
:deep(.el-select__wrapper) {
  background: rgba(30, 41, 59, 0.8) !important;
  border: 1px solid rgba(71, 85, 105, 0.5) !important;
  box-shadow: none !important;
}

:deep(.el-select__wrapper:hover) {
  border-color: rgba(34, 211, 238, 0.5) !important;
}

:deep(.el-select__wrapper.is-focused) {
  border-color: #22d3ee !important;
  box-shadow: 0 0 10px rgba(34, 211, 238, 0.2) !important;
}

:deep(.el-select__selected-item) {
  color: #e2e8f0 !important;
}

:deep(.el-select__placeholder) {
  color: #64748b !important;
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

/* 指标卡片悬停动画 */
.metric-card {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.metric-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4), 0 0 30px rgba(34, 211, 238, 0.15);
}

/* 数值变化动画 */
.metric-value {
  transition: all 0.3s ease;
}

/* 连接状态脉冲 */
@keyframes connectionPulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.4);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(34, 197, 94, 0);
  }
}

:deep(.el-tag--success) {
  animation: connectionPulse 2s ease-in-out infinite;
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

/* 表格行悬停动画 */
:deep(.el-table__row) {
  transition: all 0.2s ease;
}

:deep(.el-table__row:hover) {
  transform: scale(1.005);
}

/* Tab 切换动画 */
.tabs :deep(.el-tabs__content) {
  transition: all 0.3s ease;
}

/* 图表容器渐入 */
.chart-card {
  animation: cardFadeIn 0.6s ease-out 0.2s both;
}

/* 数据刷新闪烁 */
@keyframes dataRefresh {
  0% { opacity: 1; }
  50% { opacity: 0.6; }
  100% { opacity: 1; }
}

.data-refreshing {
  animation: dataRefresh 0.5s ease;
}

/* 分页按钮动画 */
:deep(.el-pagination .el-pager li) {
  transition: all 0.2s ease;
}

:deep(.el-pagination .el-pager li:hover) {
  transform: scale(1.1);
}

/* 加载状态动画 */
@keyframes loadingDots {
  0%, 20% { opacity: 0; }
  50% { opacity: 1; }
  80%, 100% { opacity: 0; }
}

/* KV 项悬停动画 */
.kv-item {
  transition: all 0.3s ease;
}

.kv-item:hover {
  transform: translateX(4px);
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

/* 异常检测图表样式 */
.anomaly-chart-card {
  margin-top: 14px;
}

.anomaly-chart {
  height: 200px;
}

@media (max-width: 900px) {
  .anomaly-chart {
    height: 160px;
  }
}
</style>
