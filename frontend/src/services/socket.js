import { useEffect, useState } from 'react'
import { io } from 'socket.io-client'

let socket = null

export const useSocket = () => {
  const [socketInstance, setSocketInstance] = useState(null)

  useEffect(() => {
    if (!socket) {
      socket = io('http://localhost:5001', {
        transports: ['websocket', 'polling']
      })
      setSocketInstance(socket)
    } else {
      setSocketInstance(socket)
    }

    return () => {
      // Don't disconnect on unmount, keep connection alive
    }
  }, [])

  return socketInstance
}
