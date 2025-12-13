/**
 * 传感器数据状态管理
 * 管理多气体传感器的实时数据和历史数据
 */

import { defineStore } from 'pinia'
import dayjs from 'dayjs'

export const useSensorStore = defineStore('sensor', {
  state: () => ({
    // 实时数据 - 6种气体
    realTimeData: {
      ch4: { value: 0, unit: 'ppm', status: 'normal', timestamp: '', label: '甲烷 (CH₄)', detectionLimit: 0.01, isMocked: false },
      ph3: { value: 0, unit: 'ppb', status: 'normal', timestamp: '', label: '磷化氢 (PH₃)', detectionLimit: 1, isMocked: true },
      so2: { value: 0, unit: 'ppm', status: 'normal', timestamp: '', label: '二氧化硫 (SO₂)', detectionLimit: 0.1, isMocked: true },
      h2s: { value: 0, unit: 'ppm', status: 'normal', timestamp: '', label: '硫化氢 (H₂S)', detectionLimit: 0.01, isMocked: true },
      co2: { value: 0, unit: 'ppm', status: 'normal', timestamp: '', label: '二氧化碳 (CO₂)', detectionLimit: 1, isMocked: true },
      vocs: { value: 0, unit: 'ppb', status: 'normal', timestamp: '', label: 'VOCs', detectionLimit: 10, isMocked: true }
    },

    // 历史数据（用于图表）- 最近100个数据点
    historyData: {
      labels: [],  // 时间轴标签
      datasets: {
        ch4: [],
        ph3: [],
        so2: [],
        h2s: [],
        co2: [],
        vocs: []
      }
    },

    // 传感器健康状态
    sensorHealth: {
      mos: { status: 'ready', temp: 25, power: 30, label: 'MOS (金属氧化物)' },
      ec: { status: 'ready', temp: 25, power: 10, label: 'EC (电化学)' },
      ndir: { status: 'ready', temp: 25, power: 100, label: 'NDIR (红外)' },
      pid: { status: 'ready', temp: 25, power: 50, label: 'PID (光离子)' }
    },

    // 阈值配置
    thresholds: {
      ch4: { warning: 100, danger: 500 },
      ph3: { warning: 50, danger: 200 },
      so2: { warning: 5, danger: 20 },
      h2s: { warning: 10, danger: 50 },
      co2: { warning: 5000, danger: 10000 },
      vocs: { warning: 100, danger: 500 }
    }
  }),

  getters: {
    // 获取所有气体的实时数据数组
    allGasData(state) {
      return Object.entries(state.realTimeData).map(([key, data]) => ({
        id: key,
        ...data
      }))
    },

    // 获取传感器健康数据数组
    allSensorHealth(state) {
      return Object.entries(state.sensorHealth).map(([key, data]) => ({
        id: key,
        ...data
      }))
    },

    // 检查是否有任何气体超标
    hasAnyAlert(state) {
      return Object.values(state.realTimeData).some(gas =>
        gas.status === 'warning' || gas.status === 'danger'
      )
    }
  },

  actions: {
    /**
     * 更新单个气体的实时数据
     */
    updateGasData(gasType, value) {
      if (this.realTimeData[gasType]) {
        const gas = this.realTimeData[gasType]
        gas.value = value
        gas.timestamp = dayjs().format('YYYY-MM-DD HH:mm:ss')

        // 根据阈值判断状态
        const threshold = this.thresholds[gasType]
        if (value >= threshold.danger) {
          gas.status = 'danger'
        } else if (value >= threshold.warning) {
          gas.status = 'warning'
        } else {
          gas.status = 'normal'
        }

        // 更新历史数据（保持最近100个点）
        this.historyData.labels.push(dayjs().format('HH:mm:ss'))
        this.historyData.datasets[gasType].push(value)

        // 限制历史数据长度
        if (this.historyData.labels.length > 100) {
          this.historyData.labels.shift()
          Object.keys(this.historyData.datasets).forEach(key => {
            this.historyData.datasets[key].shift()
          })
        }
      }
    },

    /**
     * 批量更新多个气体数据
     */
    updateMultipleGasData(dataMap) {
      Object.entries(dataMap).forEach(([gasType, value]) => {
        this.updateGasData(gasType, value)
      })
    },

    /**
     * 更新传感器健康状态
     */
    updateSensorHealth(sensorType, data) {
      if (this.sensorHealth[sensorType]) {
        Object.assign(this.sensorHealth[sensorType], data)
      }
    },

    /**
     * 清空历史数据
     */
    clearHistoryData() {
      this.historyData.labels = []
      Object.keys(this.historyData.datasets).forEach(key => {
        this.historyData.datasets[key] = []
      })
    },

    /**
     * 设置气体阈值
     */
    setThreshold(gasType, warning, danger) {
      if (this.thresholds[gasType]) {
        this.thresholds[gasType] = { warning, danger }
      }
    }
  }
})
