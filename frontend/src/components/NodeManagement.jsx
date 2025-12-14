import { useState, useEffect } from 'react'
import { Plus, Trash2, Cpu, Loader, RotateCcw, Play, Square } from 'lucide-react'

export default function NodeManagement({ nodes, onNodeAdded, onNodeDeleted, simulationRunning }) {
  const [isAdding, setIsAdding] = useState(false)
  const [newNode, setNewNode] = useState({
    node_id: '',
    protocol: 'wifi',
    is_mobile: false,
    position_x: '',
    position_y: '',
    role: 'both',
    subscribe_to: [],
    qos: 1,
    sensor_interval: 10
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [availableNodes, setAvailableNodes] = useState([])
  const [isRunning, setIsRunning] = useState(false)

  useEffect(() => {
    fetchAvailableNodes()
    fetchSimulationStatus()
  }, [nodes])

  useEffect(() => {
    if (simulationRunning !== undefined) {
      setIsRunning(simulationRunning)
    }
  }, [simulationRunning])

  const fetchSimulationStatus = async () => {
    try {
      const response = await fetch('/api/simulation/status')
      const data = await response.json()
      if (data.success) {
        setIsRunning(data.running)
      }
    } catch (err) {
      console.error('Error fetching simulation status:', err)
    }
  }

  const fetchAvailableNodes = async () => {
    try {
      const response = await fetch('/api/nodes/list')
      const data = await response.json()
      if (data.success) {
        setAvailableNodes(data.nodes)
      }
    } catch (err) {
      console.error('Error fetching nodes:', err)
    }
  }

  const handleAddNode = async () => {
    if (!newNode.node_id.trim()) {
      setError('Node ID is required')
      return
    }

    if (!newNode.position_x || !newNode.position_y) {
      setError('Position X and Y are required')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const nodeData = {
        ...newNode,
        position_x: parseFloat(newNode.position_x),
        position_y: parseFloat(newNode.position_y)
      }

      const response = await fetch('/api/nodes', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(nodeData)
      })

      const data = await response.json()

      if (data.success) {
        setNewNode({
          node_id: '',
          protocol: 'wifi',
          is_mobile: false,
          position_x: '',
          position_y: '',
          role: 'both',
          subscribe_to: [],
          qos: 1,
          sensor_interval: 10
        })
        setIsAdding(false)
        if (onNodeAdded) onNodeAdded(data.node)
      } else {
        setError(data.error || 'Failed to add node')
      }
    } catch (err) {
      setError('Network error: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteNode = async (nodeId) => {
    if (!confirm(`Delete node ${nodeId}?`)) return

    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`/api/nodes/${nodeId}`, {
        method: 'DELETE'
      })

      const data = await response.json()

      if (data.success) {
        if (onNodeDeleted) onNodeDeleted(nodeId)
      } else {
        setError(data.error || 'Failed to delete node')
      }
    } catch (err) {
      setError('Network error: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleRestartSimulation = async () => {
    if (!confirm('Restart simulation? This will delete ALL nodes and reload the page!')) return

    setLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/simulation/restart', {
        method: 'POST'
      })

      const data = await response.json()

      if (data.success) {
        // Reload the page to start fresh
        window.location.reload()
      } else {
        setError(data.error || 'Failed to restart simulation')
      }
    } catch (err) {
      setError('Network error: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleStartSimulation = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/simulation/start', { method: 'POST' })
      const data = await response.json()
      if (data.success) {
        setIsRunning(true)
      } else {
        setError('Failed to start simulation')
      }
    } catch (err) {
      console.error('Error starting simulation:', err)
      setError('Network error starting simulation')
    } finally {
      setLoading(false)
    }
  }

  const handleStopSimulation = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/simulation/stop', { method: 'POST' })
      const data = await response.json()
      if (data.success) {
        setIsRunning(false)
      } else {
        setError('Failed to stop simulation')
      }
    } catch (err) {
      console.error('Error stopping simulation:', err)
      setError('Network error stopping simulation')
    } finally {
      setLoading(false)
    }
  }

  const toggleSubscription = (nodeId) => {
    setNewNode(prev => ({
      ...prev,
      subscribe_to: prev.subscribe_to.includes(nodeId)
        ? prev.subscribe_to.filter(id => id !== nodeId)
        : [...prev.subscribe_to, nodeId]
    }))
  }

  return (
    <div className="card">
      <div className="card-header flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Cpu className="w-5 h-5 text-blue-600" />
          <span>Node Management</span>
        </div>
        <div className="flex space-x-2">
          <button
            onClick={handleStartSimulation}
            className={`px-3 py-1 text-white rounded-md transition-colors flex items-center space-x-1 text-sm ${
              isRunning || loading ? 'bg-gray-400 cursor-not-allowed' : 'bg-green-600 hover:bg-green-700'
            }`}
            disabled={loading || isRunning}
            title={isRunning ? "Simulation is running" : "Start simulation"}
          >
            {loading && !isRunning ? <Loader className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            <span>Start</span>
          </button>
          <button
            onClick={handleStopSimulation}
            className={`px-3 py-1 text-white rounded-md transition-colors flex items-center space-x-1 text-sm ${
              !isRunning || loading ? 'bg-gray-400 cursor-not-allowed' : 'bg-yellow-600 hover:bg-yellow-700'
            }`}
            disabled={loading || !isRunning}
            title={!isRunning ? "Simulation is stopped" : "Stop simulation"}
          >
            {loading && isRunning ? <Loader className="w-4 h-4 animate-spin" /> : <Square className="w-4 h-4" />}
            <span>Stop</span>
          </button>
          <button
            onClick={handleRestartSimulation}
            className="px-3 py-1 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors flex items-center space-x-1 text-sm"
            disabled={loading}
            title="Restart simulation (delete all nodes and reload)"
          >
            <RotateCcw className="w-0 h-0" />
            <span>Restart</span>
          </button>
          <button
            onClick={() => setIsAdding(!isAdding)}
            className="px-3 py-1 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors flex items-center space-x-1 text-sm"
            disabled={loading}
          >
            <Plus className="w-0 h-0" />
            <span>Add Node</span>
          </button>
        </div>
      </div>

      <div className="card-body">
        {/* Add Node Form */}
        {isAdding && (
          <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg max-h-[500px] overflow-y-auto">
            <h4 className="font-semibold text-blue-900 mb-3">Add New Node</h4>
            
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Node ID *
                </label>
                <input
                  type="text"
                  value={newNode.node_id}
                  onChange={(e) => setNewNode({ ...newNode, node_id: e.target.value })}
                  placeholder="e.g., node_1, sensor_temp_1"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={loading}
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Protocol
                  </label>
                  <select
                    value={newNode.protocol}
                    onChange={(e) => setNewNode({ ...newNode, protocol: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    disabled={loading}
                  >
                    <option value="wifi">WiFi</option>
                    <option value="ble">BLE</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Role
                  </label>
                  <select
                    value={newNode.role}
                    onChange={(e) => setNewNode({ ...newNode, role: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    disabled={loading}
                  >
                    <option value="both">Publisher & Subscriber</option>
                    <option value="publisher">Publisher Only</option>
                    <option value="subscriber">Subscriber Only</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    QoS Level
                  </label>
                  <select
                    value={newNode.qos}
                    onChange={(e) => setNewNode({ ...newNode, qos: parseInt(e.target.value) })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    disabled={loading}
                  >
                    <option value="0">QoS 0 - At most once (no ACK)</option>
                    <option value="1">QoS 1 - At least once (with ACK)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Sensor Interval (seconds)
                  </label>
                  <input
                    type="number"
                    value={newNode.sensor_interval}
                    onChange={(e) => setNewNode({ ...newNode, sensor_interval: parseFloat(e.target.value) })}
                    placeholder="10"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    disabled={loading}
                    min="1"
                    max="60"
                    step="0.5"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Position X *
                  </label>
                  <input
                    type="number"
                    value={newNode.position_x}
                    onChange={(e) => setNewNode({ ...newNode, position_x: e.target.value })}
                    placeholder="0-1000"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    disabled={loading}
                    min="0"
                    max="1000"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Position Y *
                  </label>
                  <input
                    type="number"
                    value={newNode.position_y}
                    onChange={(e) => setNewNode({ ...newNode, position_y: e.target.value })}
                    placeholder="0-1000"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    disabled={loading}
                    min="0"
                    max="1000"
                    required
                  />
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="is_mobile"
                  checked={newNode.is_mobile}
                  onChange={(e) => setNewNode({ ...newNode, is_mobile: e.target.checked })}
                  className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  disabled={loading}
                />
                <label htmlFor="is_mobile" className="text-sm font-medium text-gray-700">
                  Mobile Node
                </label>
              </div>

              {(newNode.role === 'subscriber' || newNode.role === 'both') && availableNodes.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Subscribe To (optional - leave empty for all)
                  </label>
                  <div className="max-h-32 overflow-y-auto border border-gray-300 rounded-md p-2 space-y-1">
                    {availableNodes.map(node => (
                      <label key={node.id} className="flex items-center space-x-2 text-sm">
                        <input
                          type="checkbox"
                          checked={newNode.subscribe_to.includes(node.id)}
                          onChange={() => toggleSubscription(node.id)}
                          className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                          disabled={loading}
                        />
                        <span>{node.id} ({node.protocol})</span>
                      </label>
                    ))}
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    {newNode.subscribe_to.length === 0 
                      ? 'Will subscribe to all publishers' 
                      : `Will subscribe to ${newNode.subscribe_to.length} node(s)`}
                  </p>
                </div>
              )}

              {error && (
                <div className="p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                  {error}
                </div>
              )}

              <div className="flex space-x-2">
                <button
                  onClick={handleAddNode}
                  disabled={loading}
                  className="flex-1 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors disabled:bg-gray-400 flex items-center justify-center space-x-2"
                >
                  {loading ? (
                    <>
                      <Loader className="w-4 h-4 animate-spin" />
                      <span>Adding...</span>
                    </>
                  ) : (
                    <>
                      <Plus className="w-4 h-4" />
                      <span>Add Node</span>
                    </>
                  )}
                </button>
                <button
                  onClick={() => {
                    setIsAdding(false)
                    setError(null)
                  }}
                  disabled={loading}
                  className="px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400 transition-colors disabled:bg-gray-200"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Nodes List */}
        <div className="space-y-2">
          <h4 className="text-sm font-semibold text-gray-700 mb-2">
            Current Nodes ({nodes.length})
          </h4>
          
          {nodes.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Cpu className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>No nodes yet</p>
              <p className="text-xs mt-1">Click "Add Node" to create one</p>
            </div>
          ) : (
            nodes.map((node) => (
              <div
                key={node.id}
                className={`flex items-center justify-between p-3 rounded-lg border ${
                  node.protocol === 'BLE'
                    ? 'bg-blue-50 border-blue-200'
                    : 'bg-green-50 border-green-200'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <div className={`w-2 h-2 rounded-full ${
                    node.connected ? 'bg-green-500' : 'bg-red-500'
                  }`} />
                  <div>
                    <p className="font-semibold text-sm text-gray-900">
                      {node.id}
                    </p>
                    <p className="text-xs text-gray-600">
                      {node.protocol} • {node.is_mobile ? 'Mobile' : 'Static'} • QoS {node.qos !== undefined ? node.qos : 1}
                    </p>
                  </div>
                </div>
                
                <button
                  onClick={() => handleDeleteNode(node.id)}
                  disabled={loading}
                  className="p-2 text-red-600 hover:bg-red-100 rounded-md transition-colors disabled:opacity-50"
                  title="Delete node"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
