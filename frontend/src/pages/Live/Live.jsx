import React from "react";
import "./Live.css";
import { useState } from "react";
import send_icon from "../../assets/icons/send_icon_blue.png";
import ex_video from "../../assets/images/example.mp4";
import { useNavigate } from "react-router-dom";
const Live = () => {
  const [exampleText, setexampleText] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const navigate = useNavigate();
  const handleInput = (event) => {
    setInputValue(event.target.value);
    if (event.key === "Enter" && event.target.value.trim() !== "") {
      setexampleText([...exampleText, event.target.value]);
      setInputValue("");
    }
  };
  const handleOnClick = (e) => {
    e.preventDefault(); // Prevent default form behavior
    navigate("/chat"); // Navigate to chat page regardless of input state
  };
  return (
    <div className="container">
      <div className="video-display">
        <video src={ex_video} className="video" controls autoPlay muted></video>
        <button onClick={handleOnClick}>Terminate</button>
      </div>
      <div className="chat-display">
        <div className="chat-message">
          {exampleText.length > 0
            ? exampleText.map((text, index) => <div className="chat-message-item" key={index}>{text}</div>)
            : "Chat messages will appear here"}
        </div>
        <div className="input-field">
          <input
            type="text"
            className="chat-input"
            placeholder="Type your message..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleInput}
          />
          <button
            onClick={() => {
              if (inputValue.trim() !== "") {
                setexampleText([...exampleText, inputValue]);
                setInputValue("");
              }
            }}
          >
            <img src={send_icon} className="send-icon" alt="" />
          </button>{" "}
        </div>
      </div>
    </div>
  );
};

export default Live;
