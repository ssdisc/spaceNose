/**
 * 系统状态管理
 * 管理WebSocket连接、系统健康等全局状态
 */

import { defineStore } from 'pinia'

export const useSystemStore = defineStore('system', {
  state: () => ({
    // WebSocket连接状态
    wsConnected: false,
    wsReconnecting: false,
    wsUrl: '',

    // 数据接收统计
    dataStats: {
      totalReceived: 0,
      lastUpdateTime: null,
      packetsPerSecond: 0
    },

    // 系统信息
    systemInfo: {
      databaseRecords: 0,
      storageUsage: 0,
      uptime: 0
    },

    // 告警历史
    alerts: [],

    // 页面加载状态
    loading: false,

    // 全局错误
    error: null
  }),

  getters: {
    // 获取连接状态文本
    connectionStatus(state) {
      if (state.wsConnected) return '已连接'
      if (state.wsReconnecting) return '重连中...'
      return '未连接'
    },

    // 获取连接状态颜色
    connectionStatusColor(state) {
      if (state.wsConnected) return 'success'
      if (state.wsReconnecting) return 'warning'
      return 'danger'
    },

    // 获取最近的告警（最多10条）
    recentAlerts(state) {
      return state.alerts.slice(-10).reverse()
    }
  },

  actions: {
    /**
     * 设置WebSocket连接状态
     */
    setWsConnected(connected) {
      this.wsConnected = connected
      if (connected) {
        this.wsReconnecting = false
      }
    },

    /**
     * 设置WebSocket重连状态
     */
    setWsReconnecting(reconnecting) {
      this.wsReconnecting = reconnecting
    },

    /**
     * 设置WebSocket URL
     */
    setWsUrl(url) {
      this.wsUrl = url
    },

    /**
     * 更新数据统计
     */
    updateDataStats() {
      this.dataStats.totalReceived++
      this.dataStats.lastUpdateTime = new Date()

      // 简单的PPS计算（可以优化为滑动窗口）
      // 这里假设数据更新频率为5秒一次
      this.dataStats.packetsPerSecond = 0.2  // 1/5
    },

    /**
     * 更新系统信息
     */
    updateSystemInfo(info) {
      Object.assign(this.systemInfo, info)
    },

    /**
     * 添加告警
     */
    addAlert(alert) {
      this.alerts.push({
        id: Date.now(),
        timestamp: new Date(),
        ...alert
      })

      // 限制告警历史长度为100
      if (this.alerts.length > 100) {
        this.alerts.shift()
      }
    },

    /**
     * 清空告警历史
     */
    clearAlerts() {
      this.alerts = []
    },

    /**
     * 设置加载状态
     */
    setLoading(loading) {
      this.loading = loading
    },

    /**
     * 设置错误
     */
    setError(error) {
      this.error = error
    },

    /**
     * 清除错误
     */
    clearError() {
      this.error = null
    }
  }
})
