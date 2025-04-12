import React from "react";
import "./LeftSideBar.css";
import profile from "../../assets/images/profile_img.png";
const LeftSideBar = () => {
  const friendlist = [
    {
      name: "Nguyen Van A",
      avatar: profile,
      type: "friend",
      lastMessage: "Hello! How are you?",
    },
    {
      name: "Nguyen Van B",
      avatar: profile,
      type: "friend",
      lastMessage: "Let's meet up tomorrow.",
    },
    {
      name: "Nguyen Van C",
      avatar: profile,
      type: "friend",
      lastMessage: "Do you free tonight?, Miss you so much",
    },
    {
      name: "Gia dinh",
      avatar: profile,
      type: "group",
      lastMessage: "Did you finish the project?",
    },
  ];
  const groupChats = friendlist.filter((friend) => friend.type === "group");
  const friendChats = friendlist.filter((friend) => friend.type === "friend");

const truncateMessage = (message, maxLength) => {
    return message.length > maxLength ? message.substring(0, maxLength) + "..." : message;
};

return (
    <div className="left-sidebar">
        <div className="profile">
            <img src={profile} alt="" />
            Dang Minh Tuan
        </div>
        <div className="chat-section">
            <div className="group-chats">
                <h3>Groups</h3>
                {groupChats.map((group, index) => (
                    <div key={index} className="chat-item">
                        <img src={group.avatar} alt="" />
                        <div className="friend-info">
                            <span>{group.name}</span>
                            <p>{truncateMessage(group.lastMessage, 50)}</p>
                        </div>
                    </div>
                ))}
            </div>
            <div className="friend-chats">
                <h3>Friends</h3>
                {friendChats.map((friend, index) => (
                    <div key={index} className="chat-item">
                        <img src={friend.avatar} alt="" />
                        <div className="friend-info">
                            <span>{friend.name}</span>
                            <p>{truncateMessage(friend.lastMessage, 50)}</p>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    </div>
);
};

export default LeftSideBar;
