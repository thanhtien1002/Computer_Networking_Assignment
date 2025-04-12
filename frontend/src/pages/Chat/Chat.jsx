import React from 'react'
import './Chat.css'
import ChatBox from '../../components/ChatBox/ChatBox'
import LeftSideBar from '../../components/LeftSideBar/LeftSideBar'

const Chat = () => {
  return (
      <div className="chat-container">
        <LeftSideBar/>
        <ChatBox/>
      </div>
  )
}

export default Chat