import { Navigation } from 'lucide-react'

export default function MobilityPanel({ nodes }) {
  const mobileNodes = nodes.filter(n => n.is_mobile)

  return (
    <div className="card">
      <div className="card-header flex items-center space-x-2">
        <Navigation className="w-5 h-5 text-blue-600" />
        <span>Mobility Status</span>
      </div>
      <div className="card-body">
        {mobileNodes.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <Navigation className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p>No mobile nodes</p>
            <p className="text-xs mt-1">All nodes are static</p>
          </div>
        ) : (
          <div className="space-y-3">
            {mobileNodes.map((node) => (
              <div key={node.id} className="p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-semibold text-sm">{node.id}</span>
                  <span className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded">
                    Mobile
                  </span>
                </div>
                
                <div className="text-xs text-gray-600 space-y-1">
                  <div className="flex justify-between">
                    <span>Position:</span>
                    <span className="font-mono">
                      ({node.position?.[0]?.toFixed(1) || 0}, {node.position?.[1]?.toFixed(1) || 0})
                    </span>
                  </div>
                  {node.stats?.position_updates !== undefined && (
                    <div className="flex justify-between">
                      <span>Updates:</span>
                      <span className="font-semibold">{node.stats.position_updates}</span>
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
