import React from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Chat from './pages/Chat/Chat'
import Login from './pages/Login/Login'
import Live from './pages/Live/Live'
const App = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/live" element={<Live />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App