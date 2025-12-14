import { Shield, AlertTriangle, MapPin, Activity } from 'lucide-react'
import { useState } from 'react'

export default function FailoverPanel({ failoverStats }) {
  const [loading, setLoading] = useState(false)

  const triggerFailover = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/failover/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      const data = await response.json()
      if (data.success) {
        console.log('Failover triggered successfully')
      }
    } catch (error) {
      console.error('Failed to trigger failover:', error)
    } finally {
      setTimeout(() => setLoading(false), 2000)
    }
  }

  const triggerRelocation = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/broker/relocate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})  // Random offset
      })
      const data = await response.json()
      if (data.success) {
        console.log('Broker relocation triggered successfully')
      }
    } catch (error) {
      console.error('Failed to trigger relocation:', error)
    } finally {
      setTimeout(() => setLoading(false), 2000)
    }
  }

  if (!failoverStats) {
    return (
      <div className="card">
        <div className="card-header flex items-center space-x-2">
          <Shield className="w-5 h-5 text-blue-600" />
          <span>Broker Topology Events</span>
        </div>
        <div className="card-body">
          <p className="text-gray-500 text-sm">No failover data available</p>
        </div>
      </div>
    )
  }

  return (
    <div className="card">
      <div className="card-header flex items-center space-x-2">
        <Shield className="w-5 h-5 text-blue-600" />
        <span>Broker Topology Events</span>
      </div>
      <div className="card-body space-y-4">
        {/* Current Status */}
        <div className="p-3 bg-gray-50 rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-semibold text-gray-700">Current Broker</span>
            <span className={`px-2 py-1 rounded text-xs font-semibold ${
              failoverStats.primary_alive ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
            }`}>
              {failoverStats.current_broker || 'localhost:1883'}
            </span>
          </div>
          <div className="text-xs text-gray-600 space-y-1">
            <div className="flex justify-between">
              <span>Primary Status:</span>
              <span className={failoverStats.primary_alive ? 'text-green-600' : 'text-red-600'}>
                {failoverStats.primary_alive ? '✓ Online' : '✗ Offline'}
              </span>
            </div>
            <div className="flex justify-between">
              <span>Failover Status:</span>
              <span className={failoverStats.failover_alive ? 'text-green-600' : 'text-red-600'}>
                {failoverStats.failover_alive ? '✓ Ready' : '✗ Offline'}
              </span>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="space-y-2">
          <button
            onClick={triggerFailover}
            disabled={loading || failoverStats.failover_in_progress}
            className="w-full px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2 transition-colors"
          >
            <AlertTriangle className="w-4 h-4" />
            <span>{failoverStats.failover_in_progress ? 'Failover In Progress...' : 'Trigger Broker Failover'}</span>
          </button>
          
          <button
            onClick={triggerRelocation}
            disabled={loading || failoverStats.relocation_in_progress}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2 transition-colors"
          >
            <MapPin className="w-4 h-4" />
            <span>{failoverStats.relocation_in_progress ? 'Relocating...' : 'Relocate Broker (~50m)'}</span>
          </button>
        </div>

        {/* Statistics */}
        <div className="space-y-2">
          <div className="flex justify-between text-xs">
            <span className="text-gray-600">Total Failovers:</span>
            <span className="font-semibold">{failoverStats.failovers || 0}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-gray-600">Broker Relocations:</span>
            <span className="font-semibold">{failoverStats.broker_relocations || 0}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-gray-600">Nodes Registered:</span>
            <span className="font-semibold">{failoverStats.nodes_registered || 0}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-gray-600">Coverage Changes:</span>
            <span className="font-semibold">{failoverStats.coverage_changes || 0}</span>
          </div>
          {failoverStats.reconnection_time > 0 && (
            <div className="flex justify-between text-xs">
              <span className="text-gray-600">Last Reconnection Time:</span>
              <span className="font-semibold text-green-600">{failoverStats.reconnection_time.toFixed(2)}s</span>
            </div>
          )}
        </div>

        {/* Reconnection Wave */}
        {failoverStats.reconnection_wave && failoverStats.reconnection_wave.length > 0 && (
          <div className="p-3 bg-blue-50 rounded-lg">
            <div className="flex items-center space-x-2 mb-2">
              <Activity className="w-4 h-4 text-blue-600" />
              <span className="text-sm font-semibold text-blue-700">Reconnection Wave</span>
            </div>
            <div className="text-xs text-gray-600 space-y-1 max-h-32 overflow-y-auto">
              {failoverStats.reconnection_wave.map(([nodeId, time], idx) => (
                <div key={idx} className="flex justify-between">
                  <span>{nodeId}</span>
                  <span className="text-blue-600">{time.toFixed(2)}s</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Broker Positions */}
        {failoverStats.broker_positions && (
          <div className="p-3 bg-gray-50 rounded-lg">
            <div className="text-xs font-semibold text-gray-700 mb-2">Broker Positions</div>
            <div className="text-xs text-gray-600 space-y-1">
              {Object.entries(failoverStats.broker_positions).map(([broker, pos]) => (
                <div key={broker} className="flex justify-between">
                  <span className="truncate">{broker.split(':')[0]}</span>
                  <span className="font-mono">({pos[0].toFixed(0)}, {pos[1].toFixed(0)})</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
