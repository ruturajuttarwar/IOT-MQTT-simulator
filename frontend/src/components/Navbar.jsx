import { Activity, Wifi, WifiOff } from 'lucide-react'

export default function Navbar({ isConnected }) {
  return (
    <nav className="bg-gradient-to-r from-blue-600 to-blue-700 text-white shadow-lg">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Activity className="w-8 h-8" />
            <div>
              <h1 className="text-2xl font-bold">IoT MQTT Simulation</h1>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            {isConnected ? (
              <>
                <Wifi className="w-5 h-5 text-green-300" />
                <span className="text-sm font-medium">Connected</span>
              </>
            ) : (
              <>
                <WifiOff className="w-5 h-5 text-red-300" />
                <span className="text-sm font-medium">Disconnected</span>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}
