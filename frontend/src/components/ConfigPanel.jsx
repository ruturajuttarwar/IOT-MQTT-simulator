import { Settings } from 'lucide-react'

export default function ConfigPanel({ config }) {
  if (!config) {
    return (
      <div className="card">
        <div className="card-header flex items-center space-x-2">
          <Settings className="w-5 h-5 text-blue-600" />
          <span>Configuration</span>
        </div>
        <div className="card-body">
          <p className="text-gray-500 text-sm">Loading configuration...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="card">
      <div className="card-header flex items-center space-x-2">
        <Settings className="w-5 h-5 text-blue-600" />
        <span>Configuration</span>
      </div>
      <div className="card-body">
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600">Total Nodes</span>
            <span className="font-semibold text-lg">{config.total_nodes}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600">WiFi Nodes</span>
            <span className="font-semibold text-green-600">{config.wifi_nodes}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600">BLE Nodes</span>
            <span className="font-semibold text-blue-600">{config.ble_nodes}</span>
          </div>
        </div>
      </div>
    </div>
  )
}
