import React from "react";
import { useState } from "react";
import "./Login.css";
import logo from "../../assets/images/logo_zoizoi.png";
import arrow_icon_w from "../../assets/icons/arrow_icon.png";
const Login = () => {
  const [currState, setCurrState] = useState("Đăng nhập");
  const onLogin = (event) => {};
  const [data, setData] = useState({
    phone: "",
    password: "",
    firstName: "",
    lastName: "",
    sex: "Male",
    address: "123 Main St, Anytown, USA",
    cccd: "",
    email: "",
  });
  const onchangeHandler = (event) => {
    const name = event.target.name;
    const value = event.target.value;
    setData((data) => ({ ...data, [name]: value }));
  };
  const handleOnClick = () => {
    navigate("/chat");
  }
  return (
    <div className="login">
      <form onSubmit={onLogin} className="login-container">
        <div className="login-title">
          <img src={logo} alt="logo" />
        </div>
        <div className="login-input">
          <input
            name="firstName"
            onChange={onchangeHandler}
            value={data.firstName}
            type="text"
            placeholder="Họ"
          />
          <input
            name="lastName"
            onChange={onchangeHandler}
            value={data.lastName}
            type="text"
            placeholder="Tên"
          />
          <input
            name="email"
            onChange={onchangeHandler}
            value={data.email}
            type="email"
            placeholder="Email"
          />
          <input
            type="password"
            name="password"
            onChange={onchangeHandler}
            value={data.password}
            placeholder="Mật khẩu"
          />
        </div>
        {currState === "Đăng kí" ? (
          <div className="login-input">
            <input
              name="cccd"
              onChange={onchangeHandler}
              value={data.cccd}
              type="text"
              placeholder="Số CCCD/Passport"
            />
            <input
              name="phone"
              onChange={onchangeHandler}
              value={data.phone}
              type="tel"
              placeholder="Số điện thoại"
            />
          </div>
        ) : null}
        {currState === "Đăng kí" ? (
          <div className="changeState-login">
            <button
              className="change-state"
              onClick={(event) => {
                event.preventDefault();
                setCurrState("Đăng nhập");
              }}
            >
              Tôi đã có tài khoản
            </button>
            <button className="continue-button" type="submit">
              <div>Đăng kí</div>
            </button>
          </div>
        ) : (
          <div className="changeState-login">
            <button
              className="change-state"
              onClick={(event) => {
                event.preventDefault();
                setCurrState("Đăng kí");
              }}
            >
              Tôi chưa có tài khoản
            </button>
            <button className="continue-button" type="submit">
              <div>Đăng Nhập</div>
            </button>
          </div>
        )}
        <div className="use-term">
            <button onClick={handleOnClick} >Go to chat</button>
          <p>
            Bằng việc tiếp tục, tôi đồng ý với điều khoản sử dụng và chính sách
            quyền riêng tư.
          </p>
        </div>
      </form>
    </div>
  );
};

export default Login;
