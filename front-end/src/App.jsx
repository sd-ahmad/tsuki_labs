import { BrowserRouter, Routes, Route } from 'react-router-dom'

import Home from './pages/Home'
import SelectionPage from './pages/SelectionPage'
import Moon from './pages/Moon'
import Mars from './pages/Mars'
import Earth from './pages/Earth'

function App() {
  return (
    <BrowserRouter>
      

      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/selection" element={<SelectionPage />} />
        <Route path="/moon" element={<Moon />} />
        <Route path="/mars" element={<Mars />} />
        <Route path="/earth" element={<Earth />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
