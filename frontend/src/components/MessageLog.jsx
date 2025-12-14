import { MessageSquare, ArrowUpCircle, ArrowDownCircle, Plug } from 'lucide-react'

export default function MessageLog({ messages }) {
  const getMessageIcon = (type) => {
    switch (type) {
      case 'PUBLISH':
        return <ArrowUpCircle className="w-4 h-4" />
      case 'SUBSCRIBE':
        return <ArrowDownCircle className="w-4 h-4" />
      case 'RECEIVED':
        return <ArrowDownCircle className="w-4 h-4" />
      case 'PUBACK':
        return <ArrowDownCircle className="w-4 h-4" />
      case 'CONNECT':
        return <Plug className="w-4 h-4" />
      case 'SYSTEM':
        return <MessageSquare className="w-4 h-4" />
      default:
        return <MessageSquare className="w-4 h-4" />
    }
  }

  const getMessageStyle = (type) => {
    switch (type) {
      case 'PUBLISH':
        return 'border-blue-500 bg-blue-50'
      case 'SUBSCRIBE':
        return 'border-green-500 bg-green-50'
      case 'RECEIVED':
        return 'border-purple-500 bg-purple-50'
      case 'PUBACK':
        return 'border-cyan-500 bg-cyan-50'
      case 'CONNECT':
        return 'border-yellow-500 bg-yellow-50'
      case 'SYSTEM':
        return 'border-orange-500 bg-orange-50'
      default:
        return 'border-gray-500 bg-gray-50'
    }
  }

  const getMessageColor = (type) => {
    switch (type) {
      case 'PUBLISH':
        return 'text-blue-700'
      case 'SUBSCRIBE':
        return 'text-green-700'
      case 'RECEIVED':
        return 'text-purple-700'
      case 'PUBACK':
        return 'text-cyan-700'
      case 'CONNECT':
        return 'text-yellow-700'
      case 'SYSTEM':
        return 'text-orange-700'
      default:
        return 'text-gray-700'
    }
  }
  
  const parsePayload = (payload) => {
    if (!payload) return null
    // Parse "temp:25.3,humidity:52.7" format
    const parts = payload.split(',')
    const data = {}
    parts.forEach(part => {
      const [key, value] = part.split(':')
      if (key && value) {
        data[key.trim()] = value.trim()
      }
    })
    return data
  }

  const formatTime = (timestamp) => {
    if (!timestamp) return new Date().toLocaleTimeString()
    return new Date(timestamp * 1000).toLocaleTimeString()
  }

  return (
    <div className="card">
      <div className="card-header flex items-center space-x-2">
        <MessageSquare className="w-5 h-5 text-blue-600" />
        <span>MQTT Message Log</span>
      </div>
      <div className="card-body p-2 max-h-96 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <MessageSquare className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p>No messages yet</p>
            <p className="text-xs mt-1">Waiting for MQTT activity...</p>
          </div>
        ) : (
          <div className="space-y-2">
            {messages.map((msg, index) => (
              <div
                key={index}
                className={`p-3 rounded-lg border-l-4 ${getMessageStyle(msg.msg_type)}`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className={`flex items-center space-x-2 font-semibold ${getMessageColor(msg.msg_type)}`}>
                    {getMessageIcon(msg.msg_type)}
                    <span className="text-sm">
                      {msg.msg_type === 'PUBLISH' && `📤 ${msg.from} published`}
                      {msg.msg_type === 'RECEIVED' && `📥 ${msg.from} received from ${msg.from_node}`}
                      {msg.msg_type === 'PUBACK' && msg.from === 'broker' && `✅ Broker → ${msg.to} ACK`}
                      {msg.msg_type === 'PUBACK' && msg.from !== 'broker' && `✅ ${msg.from} → Broker ACK`}
                      {msg.msg_type === 'SUBSCRIBE' && `${msg.from} subscribed`}
                      {msg.msg_type === 'SYSTEM' && msg.payload}
                    </span>
                  </div>
                  <span className="text-xs text-gray-500">
                    {formatTime(msg.timestamp)}
                  </span>
                </div>

                {msg.msg_type === 'PUBLISH' && (() => {
                  const data = parsePayload(msg.payload)
                  return (
                    <div className="text-xs space-y-1 text-gray-700">
                      <div className="font-mono">
                        <span className="font-semibold">Topic:</span> {msg.topic}
                      </div>
                      {data && (
                        <div className="flex space-x-4">
                          {data.temp && (
                            <span className="bg-orange-100 px-2 py-1 rounded">
                              🌡️ <span className="font-semibold">{data.temp}°C</span>
                            </span>
                          )}
                          {data.humidity && (
                            <span className="bg-blue-100 px-2 py-1 rounded">
                              💧 <span className="font-semibold">{data.humidity}%</span>
                            </span>
                          )}
                        </div>
                      )}
                      <div className="flex space-x-4 text-xs">
                        <span className={`px-2 py-0.5 rounded ${msg.qos === 0 ? 'bg-gray-200' : 'bg-green-200'}`}>
                          QoS {msg.qos} {msg.qos === 0 ? '(no ACK)' : '(with ACK)'}
                        </span>
                      </div>
                    </div>
                  )
                })()}

                {msg.msg_type === 'RECEIVED' && (() => {
                  const data = parsePayload(msg.payload)
                  return (
                    <div className="text-xs space-y-1 text-gray-700">
                      {data && (
                        <div className="flex space-x-4">
                          {data.temp && (
                            <span className="bg-orange-100 px-2 py-1 rounded">
                              🌡️ <span className="font-semibold">{data.temp}°C</span>
                            </span>
                          )}
                          {data.humidity && (
                            <span className="bg-blue-100 px-2 py-1 rounded">
                              💧 <span className="font-semibold">{data.humidity}%</span>
                            </span>
                          )}
                        </div>
                      )}
                      <div className="text-xs text-gray-600">
                        from topic: <span className="font-mono">{msg.topic}</span>
                      </div>
                    </div>
                  )
                })()}

                {msg.msg_type === 'PUBACK' && (
                  <div className="text-xs text-gray-700">
                    <span className="bg-cyan-100 px-2 py-1 rounded">
                      ✓ Acknowledgment for QoS 1 message
                    </span>
                  </div>
                )}

                {msg.msg_type === 'SUBSCRIBE' && (
                  <div className="text-xs space-y-1 font-mono text-gray-700">
                    <div>
                      <span className="font-semibold">Topic:</span> {msg.topic}
                    </div>
                    <div>
                      <span className="font-semibold">QoS:</span> {msg.qos}
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
