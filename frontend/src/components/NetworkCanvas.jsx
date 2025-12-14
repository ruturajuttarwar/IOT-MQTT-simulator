import { useEffect, useRef, useState } from 'react'

export default function NetworkCanvas({ nodes, messages, brokerPosition = [500, 500] }) {
  const canvasRef = useRef(null)
  const [animatedMessages, setAnimatedMessages] = useState([])
  const [packetAnimations, setPacketAnimations] = useState([]) // For packet transmission
  const [ackAnimations, setAckAnimations] = useState([]) // For ACK packets

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    const resizeCanvas = () => {
      canvas.width = canvas.offsetWidth
      canvas.height = canvas.offsetHeight
    }

    resizeCanvas()
    window.addEventListener('resize', resizeCanvas)

    return () => window.removeEventListener('resize', resizeCanvas)
  }, [])

  useEffect(() => {
    // Add new messages to animation queue
    if (messages.length > 0) {
      const latestMessage = messages[0]
      setAnimatedMessages(prev => [...prev, {
        ...latestMessage,
        progress: 0,
        id: Date.now()
      }])
      
      // Add packet animation (node to broker)
      setPacketAnimations(prev => [...prev, {
        from: latestMessage.from,
        progress: 0,
        id: Date.now() + '_packet'
      }])
      
      // Add ACK animation (broker to node) after a delay
      setTimeout(() => {
        setAckAnimations(prev => [...prev, {
          to: latestMessage.from,
          progress: 0,
          id: Date.now() + '_ack'
        }])
      }, 300) // ACK comes back after 300ms
    }
  }, [messages])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    let animationFrameId

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height)

      if (nodes.length === 0) {
        // Show loading message
        ctx.fillStyle = '#6b7280'
        ctx.font = '20px sans-serif'
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        ctx.fillText('Waiting for nodes...', canvas.width / 2, canvas.height / 2)
        animationFrameId = requestAnimationFrame(draw)
        return
      }

      // Use broker position (scaled to canvas)
      const scaleX = canvas.width / 1000
      const scaleY = canvas.height / 1000
      const centerX = brokerPosition[0] * scaleX
      const centerY = brokerPosition[1] * scaleY
      const radius = Math.min(canvas.width, canvas.height) * 0.35

      // Helper function to get node position
      const getNodePosition = (node, index) => {
        // If node has custom position, use it (scaled to canvas)
        if (node.position && node.position[0] !== undefined && node.position[1] !== undefined) {
          const scaleX = canvas.width / 1000  // Assuming 1000x1000 simulation area
          const scaleY = canvas.height / 1000
          return {
            x: node.position[0] * scaleX,
            y: node.position[1] * scaleY
          }
        }
        // Otherwise use circular layout
        const angle = (index / nodes.length) * Math.PI * 2 - Math.PI / 2
        return {
          x: centerX + Math.cos(angle) * radius,
          y: centerY + Math.sin(angle) * radius
        }
      }

      // Draw connection lines with distance labels
      nodes.forEach((node, i) => {
        const pos = getNodePosition(node, i)

        ctx.strokeStyle = node.connected ? '#9ca3af' : '#e5e7eb'
        ctx.lineWidth = node.connected ? 2 : 1
        ctx.beginPath()
        ctx.moveTo(centerX, centerY)
        ctx.lineTo(pos.x, pos.y)
        ctx.stroke()

        // Draw distance label on line
        if (node.distance_to_broker !== undefined) {
          const midX = (centerX + pos.x) / 2
          const midY = (centerY + pos.y) / 2
          
          // Background for text
          ctx.fillStyle = 'rgba(255, 255, 255, 0.9)'
          ctx.fillRect(midX - 25, midY - 10, 50, 16)
          
          // Distance text
          ctx.fillStyle = node.connected ? '#374151' : '#9ca3af'
          ctx.font = '11px sans-serif'
          ctx.textAlign = 'center'
          ctx.textBaseline = 'middle'
          ctx.fillText(`${Math.round(node.distance_to_broker)}m`, midX, midY)
        }
      })

      // Draw broker
      ctx.fillStyle = '#ef4444'
      ctx.beginPath()
      ctx.arc(centerX, centerY, 40, 0, Math.PI * 2)
      ctx.fill()
      ctx.strokeStyle = '#b91c1c'
      ctx.lineWidth = 3
      ctx.stroke()

      ctx.fillStyle = 'white'
      ctx.font = 'bold 18px sans-serif'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText('MQTT', centerX, centerY - 8)
      ctx.font = '14px sans-serif'
      ctx.fillText('Broker', centerX, centerY + 12)

      // Draw nodes
      nodes.forEach((node, i) => {
        const pos = getNodePosition(node, i)

        // Node circle
        ctx.fillStyle = node.protocol === 'BLE' ? '#3b82f6' : '#10b981'
        ctx.beginPath()
        ctx.arc(pos.x, pos.y, 25, 0, Math.PI * 2)
        ctx.fill()

        // Border
        ctx.strokeStyle = node.connected ? '#1f2937' : '#9ca3af'
        ctx.lineWidth = 3
        ctx.stroke()

        // Label
        ctx.fillStyle = '#1f2937'
        ctx.font = 'bold 12px sans-serif'
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        const shortId = node.id.split('_').pop()
        ctx.fillText(shortId, pos.x, pos.y + 40)

        // Protocol
        ctx.font = '10px sans-serif'
        ctx.fillStyle = '#6b7280'
        ctx.fillText(node.protocol, pos.x, pos.y + 54)
      })

      // Draw packet animations (light orange dots - node to broker)
      setPacketAnimations(prev => {
        return prev.filter(packet => {
          packet.progress += 0.025
          if (packet.progress > 1) return false

          const fromNode = nodes.find(n => n.id === packet.from)
          if (!fromNode) return false

          const fromIdx = nodes.indexOf(fromNode)
          const fromPos = getNodePosition(fromNode, fromIdx)

          const x = fromPos.x + (centerX - fromPos.x) * packet.progress
          const y = fromPos.y + (centerY - fromPos.y) * packet.progress

          // Light orange packet with glow (node → broker)
          ctx.shadowBlur = 15
          ctx.shadowColor = '#fb923c'
          ctx.fillStyle = '#fb923c'
          ctx.globalAlpha = 0.9 - packet.progress * 0.3
          ctx.beginPath()
          ctx.arc(x, y, 10, 0, Math.PI * 2)
          ctx.fill()
          ctx.shadowBlur = 0
          ctx.globalAlpha = 1

          return true
        })
      })

      // Draw ACK animations (cyan dots - broker to node)
      setAckAnimations(prev => {
        return prev.filter(ack => {
          ack.progress += 0.03
          if (ack.progress > 1) return false

          const toNode = nodes.find(n => n.id === ack.to)
          if (!toNode) return false

          const toIdx = nodes.indexOf(toNode)
          const toPos = getNodePosition(toNode, toIdx)

          const x = centerX + (toPos.x - centerX) * ack.progress
          const y = centerY + (toPos.y - centerY) * ack.progress

          // Cyan ACK packet with glow (broker → node)
          ctx.shadowBlur = 12
          ctx.shadowColor = '#06b6d4'
          ctx.fillStyle = '#06b6d4'
          ctx.globalAlpha = 0.9 - ack.progress * 0.3
          ctx.beginPath()
          ctx.arc(x, y, 9, 0, Math.PI * 2)
          ctx.fill()
          ctx.shadowBlur = 0
          ctx.globalAlpha = 1

          return true
        })
      })

      // Draw animated message pulses (original orange/green)
      setAnimatedMessages(prev => {
        return prev.filter(msg => {
          msg.progress += 0.02
          if (msg.progress > 1) return false

          const fromNode = nodes.find(n => n.id === msg.from)
          if (!fromNode) return false

          const fromIdx = nodes.indexOf(fromNode)
          const fromPos = getNodePosition(fromNode, fromIdx)

          // Pulse effect at node
          const pulseRadius = 30 + msg.progress * 20
          ctx.strokeStyle = msg.msg_type === 'PUBLISH' ? '#fb923c' : '#10b981'
          ctx.lineWidth = 3
          ctx.globalAlpha = 1 - msg.progress
          ctx.beginPath()
          ctx.arc(fromPos.x, fromPos.y, pulseRadius, 0, Math.PI * 2)
          ctx.stroke()
          ctx.globalAlpha = 1

          return true
        })
      })

      animationFrameId = requestAnimationFrame(draw)
    }

    draw()

    return () => cancelAnimationFrame(animationFrameId)
  }, [nodes, animatedMessages, packetAnimations, ackAnimations])

  return (
    <canvas
      ref={canvasRef}
      className="w-full h-[600px] bg-gradient-to-br from-gray-50 to-gray-100"
    />
  )
}
