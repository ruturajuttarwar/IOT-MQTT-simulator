import { Battery, Zap } from 'lucide-react'

export default function EnergyPanel({ nodes }) {
  return (
    <div className="card">
      <div className="card-header flex items-center space-x-2">
        <Battery className="w-5 h-5 text-blue-600" />
        <span>Energy Status</span>
      </div>
      <div className="card-body max-h-96 overflow-y-auto">
        {nodes.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <Battery className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p>No nodes available</p>
          </div>
        ) : (
          <div className="space-y-3">
            {nodes.map((node) => (
              <div key={node.id} className="p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-semibold text-sm">{node.id}</span>
                  <span className="text-xs text-gray-600">{node.protocol}</span>
                </div>
                
                <div className="space-y-2">
                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span>Battery</span>
                      <span className="font-semibold">{Math.round(node.battery)}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full transition-all ${
                          node.battery > 50
                            ? 'bg-green-500'
                            : node.battery > 20
                            ? 'bg-yellow-500'
                            : 'bg-red-500'
                        }`}
                        style={{ width: `${node.battery}%` }}
                      />
                    </div>
                  </div>
                  
                  {node.energy_stats && (
                    <div className="text-xs text-gray-600 flex items-center space-x-1">
                      <Zap className="w-3 h-3" />
                      <span>
                        {(node.energy_stats.total_energy_mj || 0).toFixed(2)} mJ consumed
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
