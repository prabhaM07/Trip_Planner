import { useState } from "react";
import { useAppDispatch, useAppSelector } from "../../../app/hook";
import { sendMessage } from "../slices/chatSlice";

const ChatInput = () => {
  const [value, setValue] = useState("");
  const dispatch = useAppDispatch();
  const loading = useAppSelector((state) => state.chat.loading);

  const send = () => {
    if (!value.trim() || loading) return;

    dispatch(sendMessage({ text: value }));
    setValue("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      send();
    }
  };

  return (
    <div style={{ display: "flex", gap: 8, padding: 2 }}>
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Type your message..."
        disabled={loading}
        style={{
          flex: 1,
          padding: 8,
          border: "1px solid #ccc",
          borderRadius: 4,
        }}
      />

      <button
        onClick={send}
        disabled={loading || !value.trim()}
        style={{
          padding: "8px 16px",
          background: "linear-gradient(90deg, #E11162, #F26538, #EFB85A)",

          color: "#fff",
          border: "none",
          borderRadius: 4,
          cursor: "pointer",
          opacity: loading ? 0.6 : 1,
        }}
      >
        {loading ? "..." : "Send"}
      </button>
    </div>
  );
};

export default ChatInput;
