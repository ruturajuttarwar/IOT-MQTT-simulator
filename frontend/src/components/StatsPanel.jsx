import { BarChart3, MessageCircle, Users, Clock } from 'lucide-react'

export default function StatsPanel({ stats }) {
  const formatUptime = (seconds) => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = seconds % 60
    return `${hours}h ${minutes}m ${secs}s`
  }

  return (
    <div className="card">
      <div className="card-header flex items-center space-x-2">
        <BarChart3 className="w-5 h-5 text-blue-600" />
        <span>Statistics</span>
      </div>
      <div className="card-body">
        <div className="grid grid-cols-2 gap-4">
          <div className="text-center p-3 bg-blue-50 rounded-lg">
            <MessageCircle className="w-6 h-6 mx-auto mb-2 text-blue-600" />
            <div className="text-2xl font-bold text-blue-600">{stats.total_messages}</div>
            <div className="text-xs text-gray-600">Messages</div>
          </div>
          
          <div className="text-center p-3 bg-green-50 rounded-lg">
            <Users className="w-6 h-6 mx-auto mb-2 text-green-600" />
            <div className="text-2xl font-bold text-green-600">{stats.active_nodes}</div>
            <div className="text-xs text-gray-600">Active Nodes</div>
          </div>
          
          <div className="text-center p-3 bg-orange-50 rounded-lg">
            <Clock className="w-6 h-6 mx-auto mb-2 text-orange-600" />
            <div className="text-xl font-bold text-orange-600">{stats.total_subscriptions || 0}</div>
            <div className="text-xs text-gray-600">Subscribers</div>
          </div>
          
          <div className="text-center p-3 bg-purple-50 rounded-lg">
            <Clock className="w-6 h-6 mx-auto mb-2 text-purple-600" />
            <div className="text-xl font-bold text-purple-600">{formatUptime(stats.uptime || 0)}</div>
            <div className="text-xs text-gray-600">Runtime</div>
          </div>
        </div>
      </div>
    </div>
  )
}
