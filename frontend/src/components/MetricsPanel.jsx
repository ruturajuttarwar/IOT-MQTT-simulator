import { TrendingUp, Download, FileText, Activity, Shield } from 'lucide-react'

export default function MetricsPanel({ metrics }) {
  const handleExport = async (endpoint, filename) => {
    try {
      const response = await fetch(endpoint)
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${filename}_${new Date().toISOString().slice(0,19).replace(/:/g,'-')}.csv`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      console.error(`Error exporting ${filename}:`, error)
      alert(`Failed to export ${filename}`)
    }
  }

  const handleExportLogs = () => handleExport('/api/export/logs', 'mqtt_logs')
  const handleExportDutyCycle = () => handleExport('/api/export/duty-cycle', 'duty_cycle_results')
  const handleExportProtocol = () => handleExport('/api/export/protocol-comparison', 'protocol_comparison')
  const handleExportFailover = () => handleExport('/api/export/failover', 'failover_results')
  if (!metrics) {
    return (
      <div className="card">
        <div className="card-header flex items-center space-x-2">
          <TrendingUp className="w-5 h-5 text-blue-600" />
          <span>Performance Metrics</span>
        </div>
        <div className="card-body">
          <p className="text-gray-500 text-sm">No metrics available</p>
        </div>
      </div>
    )
  }

  return (
    <div className="card">
      <div className="card-header flex items-center space-x-2">
        <TrendingUp className="w-5 h-5 text-blue-600" />
        <span>Performance Metrics & Exports</span>
      </div>
      <div className="card-body space-y-4">
        {/* Metrics Display */}
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600">Total Messages</span>
            <span className="font-semibold text-lg">{metrics.total_messages_sent || 0}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600">Avg Latency</span>
            <span className="font-semibold text-blue-600">
              {metrics.average_latency?.toFixed(2) || 0} ms
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600">Throughput</span>
            <span className="font-semibold text-green-600">
              {metrics.throughput?.toFixed(2) || 0} msg/s
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600">Packet Loss</span>
            <span className="font-semibold text-red-600">
              {metrics.packet_loss_rate?.toFixed(2) || 0}%
            </span>
          </div>
        </div>

        {/* Export Buttons */}
        <div className="border-t pt-4">
          <div className="text-sm font-semibold text-gray-700 mb-3">📊 Experiment Data Exports</div>
          <div className="space-y-2">
            <button
              onClick={handleExportDutyCycle}
              className="w-full px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors flex items-center justify-between text-sm"
              title="Export E1: Duty Cycle Impact (sleep ratio, latency, battery)"
            >
              <div className="flex items-center space-x-2">
                <Activity className="w-4 h-4" />
                <span>E1: Duty Cycle Impact</span>
              </div>
              <Download className="w-4 h-4" />
            </button>
            
            <button
              onClick={handleExportProtocol}
              className="w-full px-3 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors flex items-center justify-between text-sm"
              title="Export E2: Protocol Comparison (BLE vs WiFi performance)"
            >
              <div className="flex items-center space-x-2">
                <TrendingUp className="w-4 h-4" />
                <span>E2: Protocol Comparison</span>
              </div>
              <Download className="w-4 h-4" />
            </button>
            
            <button
              onClick={handleExportFailover}
              className="w-full px-3 py-2 bg-orange-600 text-white rounded-md hover:bg-orange-700 transition-colors flex items-center justify-between text-sm"
              title="Export E3: Failover & Topology (resilience, reconnection)"
            >
              <div className="flex items-center space-x-2">
                <Shield className="w-4 h-4" />
                <span>E3: Failover & Topology</span>
              </div>
              <Download className="w-4 h-4" />
            </button>
            
            <button
              onClick={handleExportLogs}
              className="w-full px-3 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 transition-colors flex items-center justify-between text-sm"
              title="Export raw MQTT message logs"
            >
              <div className="flex items-center space-x-2">
                <FileText className="w-4 h-4" />
                <span>Raw Message Logs</span>
              </div>
              <Download className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
