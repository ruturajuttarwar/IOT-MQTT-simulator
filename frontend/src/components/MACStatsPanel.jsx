import { Radio } from 'lucide-react'

export default function MACStatsPanel({ nodes }) {
  return (
    <div className="card">
      <div className="card-header flex items-center space-x-2">
        <Radio className="w-5 h-5 text-blue-600" />
        <span>MAC Layer Statistics</span>
      </div>
      <div className="card-body max-h-96 overflow-y-auto">
        {nodes.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <Radio className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p>No nodes available</p>
          </div>
        ) : (
          <div className="space-y-3">
            {nodes.map((node) => (
              <div key={node.id} className="p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-semibold text-sm">{node.id}</span>
                  <span className={`text-xs px-2 py-1 rounded ${
                    node.protocol === 'BLE' ? 'bg-blue-100 text-blue-700' : 'bg-green-100 text-green-700'
                  }`}>
                    {node.protocol}
                  </span>
                </div>
                
                {node.mac_stats && (
                  <div className="text-xs text-gray-600 space-y-1">
                    <div className="flex justify-between">
                      <span>Packets Sent:</span>
                      <span className="font-semibold">{node.mac_stats.packets_sent || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Packets Received:</span>
                      <span className="font-semibold">{node.mac_stats.packets_received || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Collisions:</span>
                      <span className="font-semibold text-red-600">{node.mac_stats.collisions || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Retransmissions:</span>
                      <span className="font-semibold text-yellow-600">{node.mac_stats.packets_retried || 0}</span>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
