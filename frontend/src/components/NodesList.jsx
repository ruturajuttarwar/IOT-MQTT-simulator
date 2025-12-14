import { Cpu, Wifi, Bluetooth } from 'lucide-react'

export default function NodesList({ nodes }) {
  return (
    <div className="card">
      <div className="card-header flex items-center space-x-2">
        <Cpu className="w-5 h-5 text-blue-600" />
        <span>Nodes ({nodes.length})</span>
      </div>
      <div className="card-body max-h-64 overflow-y-auto">
        {nodes.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <Cpu className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p>No nodes available</p>
          </div>
        ) : (
          <div className="space-y-2">
            {nodes.map((node) => (
              <div
                key={node.id}
                className={`flex items-center justify-between p-3 rounded-lg border ${
                  node.protocol === 'BLE'
                    ? 'bg-blue-50 border-blue-200'
                    : 'bg-green-50 border-green-200'
                }`}
              >
                <div className="flex items-center space-x-3">
                  {node.protocol === 'BLE' ? (
                    <Bluetooth className="w-5 h-5 text-blue-600" />
                  ) : (
                    <Wifi className="w-5 h-5 text-green-600" />
                  )}
                  <div>
                    <p className="font-semibold text-sm">{node.id}</p>
                    <p className="text-xs text-gray-600">
                      {node.protocol} • Battery: {Math.round(node.battery)}%
                    </p>
                  </div>
                </div>
                <div className={`w-3 h-3 rounded-full ${
                  node.connected ? 'bg-green-500' : 'bg-red-500'
                }`} />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
