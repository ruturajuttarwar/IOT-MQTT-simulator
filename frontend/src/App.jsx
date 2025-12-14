import { useState, useEffect } from 'react'
import Navbar from './components/Navbar'
import NetworkCanvas from './components/NetworkCanvas'
import ConfigPanel from './components/ConfigPanel'
import StatsPanel from './components/StatsPanel'
import NodesList from './components/NodesList'
import MessageLog from './components/MessageLog'
import EnergyPanel from './components/EnergyPanel'
import MobilityPanel from './components/MobilityPanel'
import FailoverPanel from './components/FailoverPanel'
import MACStatsPanel from './components/MACStatsPanel'
import MetricsPanel from './components/MetricsPanel'
import NodeManagement from './components/NodeManagement'
import { useSocket } from './services/socket'

function App() {
  const [nodes, setNodes] = useState([])
  const [stats, setStats] = useState({
    total_messages: 0,
    active_nodes: 0,
    uptime: 0,
    total_subscriptions: 0
  })
  const [messages, setMessages] = useState([])
  const [config, setConfig] = useState(null)
  const [isConnected, setIsConnected] = useState(false)
  const [failoverStats, setFailoverStats] = useState(null)
  const [metrics, setMetrics] = useState(null)
  const [brokerPosition, setBrokerPosition] = useState([500, 500])
  const [activeTab, setActiveTab] = useState('overview') // overview, energy, mobility, mac, metrics, manage

  const socket = useSocket()

  useEffect(() => {
    if (!socket) return

    // Socket event handlers
    socket.on('connect', () => {
      console.log('Connected to server')
      setIsConnected(true)
      fetchConfig()
      fetchFailoverStats()
      fetchMetrics()
    })

    socket.on('disconnect', () => {
      console.log('Disconnected from server')
      setIsConnected(false)
    })

    socket.on('init', (data) => {
      console.log('Initialized with nodes:', data.nodes)
      setNodes(data.nodes)
    })

    socket.on('update', (data) => {
      setNodes(data.nodes)
      setStats(data.stats)
      if (data.failover_stats) {
        setFailoverStats(data.failover_stats)
      }
      if (data.metrics) {
        setMetrics(data.metrics)
      }
      if (data.broker_position) {
        setBrokerPosition(data.broker_position)
      }
    })

    socket.on('message', (data) => {
      setMessages(prev => [data, ...prev].slice(0, 100))
    })

    return () => {
      socket.off('connect')
      socket.off('disconnect')
      socket.off('init')
      socket.off('update')
      socket.off('message')
    }
  }, [socket])

  const fetchConfig = async () => {
    try {
      const response = await fetch('/api/config')
      const data = await response.json()
      setConfig(data)
    } catch (error) {
      console.error('Error fetching config:', error)
    }
  }

  const fetchFailoverStats = async () => {
    try {
      const response = await fetch('/api/failover/stats')
      const data = await response.json()
      setFailoverStats(data)
    } catch (error) {
      console.error('Error fetching failover stats:', error)
    }
  }

  const fetchMetrics = async () => {
    try {
      const response = await fetch('/api/metrics')
      const data = await response.json()
      setMetrics(data)
    } catch (error) {
      console.error('Error fetching metrics:', error)
    }
  }

  // Periodic refresh of failover and metrics
  useEffect(() => {
    const interval = setInterval(() => {
      if (isConnected) {
        fetchFailoverStats()
        fetchMetrics()
      }
    }, 5000) // Every 5 seconds

    return () => clearInterval(interval)
  }, [isConnected])

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar isConnected={isConnected} />
      
      <div className="container mx-auto px-4 py-6">
        {/* Tab Navigation */}
        <div className="mb-6 border-b border-gray-200">
          <nav className="flex space-x-8">
            {[
              { id: 'overview', label: 'Overview' },
              { id: 'manage', label: 'Manage Nodes' },
              { id: 'energy', label: 'Energy' },
              { id: 'mobility', label: 'Mobility' },
              { id: 'mac', label: 'MAC Layer' },
              { id: 'metrics', label: 'Metrics' }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Canvas - Takes 2 columns on large screens */}
          <div className="lg:col-span-2">
            <div className="card">
              <div className="card-body p-0">
                <NetworkCanvas nodes={nodes} messages={messages} brokerPosition={brokerPosition} />
              </div>
            </div>
          </div>

          {/* Sidebar - Takes 1 column - Content changes based on active tab */}
          <div className="space-y-6">
            {activeTab === 'overview' && (
              <>
                <ConfigPanel config={config} />
                <StatsPanel stats={stats} />
                <NodesList nodes={nodes} />
                <MessageLog messages={messages} />
              </>
            )}

            {activeTab === 'manage' && (
              <>
                <NodeManagement 
                  nodes={nodes}
                  simulationRunning={stats.running}
                  onNodeAdded={(node) => {
                    console.log('Node added:', node)
                    // Node will appear via socket update
                  }}
                  onNodeDeleted={(nodeId) => {
                    console.log('Node deleted:', nodeId)
                    // Node will disappear via socket update
                  }}
                />
                <StatsPanel stats={stats} />
                <MessageLog messages={messages} />
              </>
            )}

            {activeTab === 'energy' && (
              <>
                <EnergyPanel nodes={nodes} />
                <StatsPanel stats={stats} />
                <MessageLog messages={messages} />
              </>
            )}

            {activeTab === 'mobility' && (
              <>
                <MobilityPanel nodes={nodes} />
                <FailoverPanel failoverStats={failoverStats} />
                <MessageLog messages={messages} />
              </>
            )}

            {activeTab === 'mac' && (
              <>
                <MACStatsPanel nodes={nodes} />
                <NodesList nodes={nodes} />
                <MessageLog messages={messages} />
              </>
            )}

            {activeTab === 'metrics' && (
              <>
                <MetricsPanel metrics={metrics} />
                <FailoverPanel failoverStats={failoverStats} />
                <StatsPanel stats={stats} />
                <MessageLog messages={messages} />
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
