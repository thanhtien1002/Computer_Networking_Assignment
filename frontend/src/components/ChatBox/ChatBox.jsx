import React from "react";
import "./ChatBox.css";
import profile from "../../assets/images/profile_img.png";
import live_icon from "../../assets/icons/live_icon.png";
import send_icon from "../../assets/icons/send_icon.png";
import { useNavigate } from "react-router-dom";

const ChatBox = () => {
    const navigate = useNavigate();
    const clickLiveHandler = () => {
        navigate("/live");
    }
return (
    <div className="chat-box">
        <div className="title">
            <div className="chat-infor">
                <img src={profile} />
                <span>Hoang Van Long</span>
            </div>
            <div className="live" onClick={clickLiveHandler}>
                <span>Live</span>
            <img src={live_icon} className="live_icon" />
            </div>
            
        </div>
        <div className="chat-text-display">
            <div className="s-msg">
                    <p className="msg">Chào, hôm nay bạn thế nào?</p>
                    <img src={profile} alt="" />
            </div>
            <div className="r-msg">
                    <img src={profile} alt="" />
                    <p className="msg">Mình ổn, cảm ơn! Còn bạn thì sao?</p>
            </div>
            <div className="s-msg">
                    <p className="msg">Mình cũng ổn. Bạn đã làm xong bài tập chưa?</p>
                    <img src={profile} alt="" />
            </div>
            <div className="r-msg">
                    <img src={profile} alt="" />
                    <p className="msg">Chưa, mình vẫn đang làm. Khá là khó.</p>
            </div>
            <div className="s-msg">
                    <p className="msg">Ừ, mình đồng ý. Nếu cần giúp gì thì cứ nói nhé.</p>
                    <img src={profile} alt="" />
            </div>
            <div className="r-msg">
                    <img src={profile} alt="" />
                    <p className="msg">Cảm ơn! Có thể mình sẽ nhờ bạn sau.</p>
            </div>
            <div className="s-msg">
                    <p className="msg">Không có gì. Hẹn gặp lại sau nhé!</p>
                    <img src={profile} alt="" />
            </div>
            <div className="r-msg">
                    <img src={profile} alt="" />
                    <p className="msg">Ừ, nói chuyện sau nhé!</p>
            </div>
        </div>
            <div className="chat-input">
                    <input type="text" placeholder="Nhập tin nhắn của bạn..." />
                    <button>
                            <img src={send_icon} className="send-icon" alt="" />
                    </button>
            </div>
    </div>
);
};

export default ChatBox;
