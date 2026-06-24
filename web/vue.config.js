const { defineConfig } = require('@vue/cli-service')

const ignoredRuntimeOverlayErrors = [
  'ResizeObserver loop completed with undelivered notifications.',
  'ResizeObserver loop limit exceeded'
]

module.exports = defineConfig({
  transpileDependencies: true,
  devServer: {
    client: {
      overlay: {
        errors: true,
        warnings: false,
        runtimeErrors: (error) => {
          return !ignoredRuntimeOverlayErrors.includes(error?.message)
        }
      }
    }
  }
})
