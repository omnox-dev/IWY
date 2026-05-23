import { useState, useEffect } from 'react'
import './App.css'
import VisionAssistant from './VisionAssistant'

function App() {
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    setIsLoaded(true);
  }, []);

  return (
    <div className="App">
      {isLoaded && <VisionAssistant />}
    </div>
  )
}

export default App
