import { useEffect, useRef } from "react";
import Lottie from "lottie-react";
import ChatInput from "../features/chat/components/ChatInput";
import ChatMessages from "../features/chat/components/ChatMessages";
import animation from "../animations/animate1.json";
import { useAppSelector } from "../app/hook";

const ChatPage = () => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const messages = useAppSelector((state) => state.chat.messages);
  const loading = useAppSelector((state) => state.chat.loading);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  return (
    <div
      style={{
        height: "100vh",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* HEADER */}
      <div
        style={{
          padding: 16,
          borderBottom: "1px solid #cccccc",
          background: "#242324",
          flexShrink: 0,
          textAlign: "center",
        }}
      >
        <h2
          style={{
            margin: 0,
            background: "linear-gradient(90deg, #E11162, #F26538, #EFB85A)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            fontWeight: 700,
          }}
        >
          Trip Planner
        </h2>
      </div>


      {/* MESSAGES SECTION */}
      <div
        style={{
          flex: 1,
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Fixed Background Animation */}
        <div
          style={{
            position: "absolute",
            top: "40%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            width: "50%",
            height: "50%",
            opacity: 0.4,
            pointerEvents: "none",
            zIndex: 0,
          }}
        >
          <Lottie animationData={animation} loop />
        </div>

        {/* Scrollable Messages */}
        <div
          ref={scrollRef}
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            overflowY: "auto",
            zIndex: 1,
          }}
        >
          <ChatMessages />
        </div>
      </div>

      {/* INPUT SECTION */}
      <div
        style={{
          borderTop: "1px solid #c0baba",
          padding: 12,
          background: "#fff",
          flexShrink: 0,
        }}
      >
        <ChatInput />
      </div>
    </div>
  );
};

export default ChatPage;