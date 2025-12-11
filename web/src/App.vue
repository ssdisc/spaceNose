<template>
  <div id="app">
    <div class="header">
      <h1>🛰️ 星际嗅探者 - 实时数据监控</h1>
      <div class="status">
        <span class="status-indicator" :class="{ connected: isConnected }"></span>
        <span>{{ connectionStatus }}</span>
      </div>
      <div class="nav-tabs">
        <button
          class="nav-btn"
          :class="{ active: activeTab === 'realtime' }"
          @click="switchTab('realtime')"
        >
          实时数据
        </button>
        <button
          class="nav-btn"
          :class="{ active: activeTab === 'history' }"
          @click="switchTab('history')"
        >
          历史数据
        </button>
      </div>
    </div>

    <div class="container" v-if="activeTab === 'realtime'">
      <!-- 主要数据显示卡片 -->
      <div class="card-grid">
        <div class="data-card">
          <div class="card-header">
            <span class="icon">📊</span>
            <span class="title">ADC原始值</span>
          </div>
          <div class="card-value">{{ sensorData.adc }}</div>
          <div class="card-unit">数字量</div>
        </div>

        <div class="data-card voltage-card">
          <div class="card-header">
            <span class="icon">⚡</span>
            <span class="title">电压值</span>
          </div>
          <div class="card-value">{{ sensorData.voltage.toFixed(3) }}</div>
          <div class="card-unit">伏特 (V)</div>
        </div>

        <div class="data-card">
          <div class="card-header">
            <span class="icon">🔢</span>
            <span class="title">数据计数</span>
          </div>
          <div class="card-value">{{ sensorData.counter }}</div>
          <div class="card-unit">次</div>
        </div>
      </div>

      <!-- 历史数据图表 -->
      <div class="chart-container">
        <h2>📈 实时数据趋势</h2>
        <div class="chart">
          <canvas ref="chartCanvas"></canvas>
        </div>
      </div>
    </div>

    <div class="container" v-else>
      <div class="log-container">
        <div class="log-header">
          <h2>📝 历史数据（数据库）</h2>
          <div class="log-actions">
            <select v-model.number="historyLimit" @change="fetchRecentData">
              <option :value="20">最近 20 条</option>
              <option :value="50">最近 50 条</option>
              <option :value="100">最近 100 条</option>
            </select>
            <button class="refresh-button" @click="fetchRecentData">刷新</button>
          </div>
        </div>
        <div class="log-content">
          <div v-if="dataLogs.length === 0" class="log-empty">暂无历史数据</div>
          <div v-else>
            <div v-for="(log, index) in dataLogs" :key="index" class="log-item">
              <span class="log-time">{{ log.timestamp }}</span>
              <span class="log-data">
                计数: {{ log.counter }} | ADC: {{ log.adc }} | 电压: {{ log.voltage.toFixed(3) }}V
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'App',
  data() {
    return {
      ws: null,
      isConnected: false,
      sensorData: {
        counter: 0,
        adc: 0,
        voltage: 0.0,
        timestamp: ''
      },
      activeTab: 'realtime',
      dataLogs: [],
      chart: null,
      chartData: {
        labels: [],
        voltageData: [],
        adcData: []
      },
      maxDataPoints: 20,
      historyLimit: 50
    }
  },
  computed: {
    connectionStatus() {
      return this.isConnected ? '已连接' : '未连接'
    }
  },
  mounted() {
    this.initChart()
    this.fetchRecentData()
    this.connectWebSocket()
  },
  beforeUnmount() {
    if (this.ws) {
      this.ws.close()
    }
  },
  methods: {
    switchTab(tab) {
      this.activeTab = tab
      if (tab === 'history') {
        this.fetchRecentData()
      } else {
        // 重新挂载实时视图时重建画布并重绘
        this.$nextTick(() => {
          this.initChart()
          this.drawChart()
        })
      }
    },

    apiBaseUrl() {
      const protocol = window.location.protocol === 'https:' ? 'https' : 'http'
      return `${protocol}://${window.location.hostname}:8000`
    },

    async fetchRecentData() {
      try {
        const response = await fetch(`${this.apiBaseUrl()}/api/data/recent?limit=${this.historyLimit}`)
        const json = await response.json()
        if (json.success && Array.isArray(json.data)) {
          // 填充数据库最新记录（后端已按时间倒序返回）
          this.dataLogs = json.data.map(item => ({
            counter: item.counter ?? 0,
            adc: item.adc ?? 0,
            voltage: item.voltage ?? 0,
            timestamp: item.timestamp ?? ''
          }))

          // 若 WebSocket 尚未推送，用最新一条作为当前显示值（仅实时页时使用）
          if (this.activeTab === 'realtime' && this.dataLogs.length > 0) {
            this.sensorData = this.dataLogs[0]
          }

          // 重新绘制图表，按时间顺序取最近 maxDataPoints 条
          this.resetChart()
          const chartSeed = [...this.dataLogs].reverse().slice(-this.maxDataPoints)
          chartSeed.forEach(data => this.updateChart(data, { skipTrim: true }))
          this.drawChart()
        } else {
          console.warn('获取历史数据失败，返回值异常:', json)
        }
      } catch (error) {
        console.error('加载历史数据失败:', error)
      }
    },

    connectWebSocket() {
      // 使用当前页面的主机名连接WebSocket
      const wsUrl = `ws://${window.location.hostname}:8000/ws`
      console.log('正在连接WebSocket:', wsUrl)
      
      this.ws = new WebSocket(wsUrl)
      
      this.ws.onopen = () => {
        console.log('✓ WebSocket连接成功')
        this.isConnected = true
        // 连接后拉取一次数据库历史，保证列表同步
        this.fetchRecentData()
      }
      
      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          console.log('收到数据:', data)
          
          // 更新当前数据
          this.sensorData = data
          
          // 添加到日志（最多保留 historyLimit 条）
          this.dataLogs.unshift(data)
          if (this.dataLogs.length > this.historyLimit) {
            this.dataLogs.pop()
          }
          
          // 更新图表
          this.updateChart(data)
          
        } catch (error) {
          console.error('解析数据失败:', error)
        }
      }
      
      this.ws.onerror = (error) => {
        console.error('✗ WebSocket错误:', error)
        this.isConnected = false
      }
      
      this.ws.onclose = () => {
        console.log('✗ WebSocket连接关闭')
        this.isConnected = false
        
        // 5秒后尝试重连
        setTimeout(() => {
          console.log('尝试重新连接...')
          this.connectWebSocket()
        }, 5000)
      }
    },
    
    initChart() {
      const canvas = this.$refs.chartCanvas
      if (!canvas) {
        this.chart = null
        return
      }
      const ctx = canvas.getContext('2d')
      
      // 简单的手动绘图（避免引入Chart.js依赖）
      this.chart = {
        canvas: canvas,
        ctx: ctx
      }
    },
    
    resetChart() {
      this.chartData = {
        labels: [],
        voltageData: [],
        adcData: []
      }
    },

    updateChart(data, options = {}) {
      // 更新数据数组
      this.chartData.labels.push(data.counter)
      this.chartData.voltageData.push(data.voltage)
      this.chartData.adcData.push(data.adc)
      
      // 限制数据点数量
      if (!options.skipTrim && this.chartData.labels.length > this.maxDataPoints) {
        this.chartData.labels.shift()
        this.chartData.voltageData.shift()
        this.chartData.adcData.shift()
      }
      
      // 绘制图表
      this.drawChart()
    },
    
    drawChart() {
      if (!this.chart) return
      
      const canvas = this.chart.canvas
      const ctx = this.chart.ctx
      
      // 设置画布大小
      canvas.width = canvas.offsetWidth
      canvas.height = 300
      
      const width = canvas.width
      const height = canvas.height
      const padding = 40
      
      // 清空画布
      ctx.clearRect(0, 0, width, height)
      
      // 绘制背景
      ctx.fillStyle = '#f8f9fa'
      ctx.fillRect(0, 0, width, height)
      
      if (this.chartData.voltageData.length === 0) return
      
      // 计算缩放比例
      const maxVoltage = Math.max(...this.chartData.voltageData, 3.3)
      const minVoltage = 0
      const voltageRange = maxVoltage - minVoltage
      
      const xStep = (width - 2 * padding) / (this.maxDataPoints - 1)
      const yScale = (height - 2 * padding) / voltageRange
      
      // 绘制网格线
      ctx.strokeStyle = '#dee2e6'
      ctx.lineWidth = 1
      for (let i = 0; i <= 4; i++) {
        const y = padding + i * (height - 2 * padding) / 4
        ctx.beginPath()
        ctx.moveTo(padding, y)
        ctx.lineTo(width - padding, y)
        ctx.stroke()
        
        // 绘制Y轴刻度
        ctx.fillStyle = '#6c757d'
        ctx.font = '12px Arial'
        const value = (maxVoltage - i * voltageRange / 4).toFixed(2)
        ctx.fillText(value + 'V', 5, y + 4)
      }
      
      // 绘制电压曲线
      ctx.strokeStyle = '#007bff'
      ctx.lineWidth = 2
      ctx.beginPath()
      
      this.chartData.voltageData.forEach((voltage, index) => {
        const x = padding + index * xStep
        const y = height - padding - (voltage - minVoltage) * yScale
        
        if (index === 0) {
          ctx.moveTo(x, y)
        } else {
          ctx.lineTo(x, y)
        }
      })
      
      ctx.stroke()
      
      // 绘制数据点
      ctx.fillStyle = '#007bff'
      this.chartData.voltageData.forEach((voltage, index) => {
        const x = padding + index * xStep
        const y = height - padding - (voltage - minVoltage) * yScale
        
        ctx.beginPath()
        ctx.arc(x, y, 3, 0, 2 * Math.PI)
        ctx.fill()
      })
    }
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: 100vh;
  padding: 20px;
}

.header {
  text-align: center;
  color: white;
  margin-bottom: 30px;
}

.header h1 {
  font-size: 2.5em;
  margin-bottom: 15px;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.2);
}

.nav-tabs {
  margin-top: 15px;
  display: flex;
  justify-content: center;
  gap: 12px;
}

.nav-btn {
  border: none;
  padding: 10px 18px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  cursor: pointer;
  transition: background 0.2s, transform 0.2s;
  backdrop-filter: blur(6px);
}

.nav-btn.active {
  background: white;
  color: #764ba2;
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
}

.nav-btn:hover {
  transform: translateY(-1px);
}

.status {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  font-size: 1.2em;
}

.status-indicator {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #dc3545;
  box-shadow: 0 0 10px rgba(220, 53, 69, 0.5);
  animation: pulse 2s infinite;
}

.status-indicator.connected {
  background: #28a745;
  box-shadow: 0 0 10px rgba(40, 167, 69, 0.5);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.container {
  max-width: 1200px;
  margin: 0 auto;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.data-card {
  background: white;
  border-radius: 15px;
  padding: 25px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  transition: transform 0.3s, box-shadow 0.3s;
}

.data-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 12px rgba(0, 0, 0, 0.15);
}

.voltage-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 15px;
  font-size: 1.1em;
  opacity: 0.8;
}

.icon {
  font-size: 1.5em;
}

.card-value {
  font-size: 3em;
  font-weight: bold;
  margin: 10px 0;
}

.card-unit {
  font-size: 0.9em;
  opacity: 0.7;
}

.chart-container, .log-container {
  background: white;
  border-radius: 15px;
  padding: 25px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  margin-bottom: 30px;
}

.chart-container h2, .log-container h2 {
  color: #333;
  margin-bottom: 20px;
  font-size: 1.5em;
}

.log-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 20px;
}

.log-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.log-actions select {
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid #ced4da;
  background: #fff;
}

.refresh-button {
  border: none;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s, box-shadow 0.2s, opacity 0.2s;
}

.refresh-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 12px rgba(0, 0, 0, 0.15);
  opacity: 0.95;
}

.refresh-button:active {
  transform: translateY(0);
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.chart {
  width: 100%;
  height: 300px;
}

.chart canvas {
  width: 100%;
  height: 100%;
}

.log-content {
  max-height: 400px;
  overflow-y: auto;
  background: #f8f9fa;
  border-radius: 10px;
  padding: 15px;
}

.log-item {
  padding: 10px;
  margin-bottom: 8px;
  background: white;
  border-radius: 8px;
  border-left: 4px solid #667eea;
  font-family: 'Courier New', monospace;
  transition: background 0.3s;
}

.log-item:hover {
  background: #e9ecef;
}

.log-time {
  color: #6c757d;
  margin-right: 15px;
}

.log-data {
  color: #333;
}

.log-empty {
  text-align: center;
  color: #6c757d;
  padding: 20px 0;
}

/* 滚动条样式 */
.log-content::-webkit-scrollbar {
  width: 8px;
}

.log-content::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 10px;
}

.log-content::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 10px;
}

.log-content::-webkit-scrollbar-thumb:hover {
  background: #555;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .header h1 {
    font-size: 1.8em;
  }
  
  .card-grid {
    grid-template-columns: 1fr;
  }
  
  .card-value {
    font-size: 2.5em;
  }
}
</style>
