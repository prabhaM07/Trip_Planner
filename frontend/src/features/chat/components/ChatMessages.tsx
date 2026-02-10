import { useAppSelector } from "../../../app/hook";
import InterruptBox from "./InterruptBox";

const ChatMessages = () => {
  const messages = useAppSelector((state) => state.chat.messages);
  const loading = useAppSelector((state) => state.chat.loading);

  let fromDate: string | null = null;

  return (
    <div style={{ padding: 16 }}>
      {messages.map((msg, index) => {
        if ("text" in msg) {
          if (
            msg.sender === "user" &&
            msg.text.match(/^\d{2}\.\d{2}\.\d{4}$/)
          ) {
            fromDate = msg.text;
          }

          return (
            <div
              key={index}
              style={{
                background: msg.sender === "user" ? "#fce3d7" : "#f5f5f5",
                padding: 8,
                borderRadius: 8,
                maxWidth: "80%",
                marginBottom: 12,
                marginLeft: msg.sender === "user" ? "auto" : 0,
              }}
            >
              <div style={{ fontSize: 11, color: "#363535", marginBottom: 4, fontWeight: "bold" }}>
                {msg.sender === "user" ? "You" : "Bot"}
              </div>

              <div
                style={{ whiteSpace: "pre-wrap" }}
                dangerouslySetInnerHTML={{
                  __html: msg.text
                    .replace(/### (.*?)(\n|$)/g, "<h3>$1</h3>")
                    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>"),
                }}
              />
            </div>
          );
        }

        if ("interrupt" in msg) {
          const isActive = index === messages.length - 1 && !loading;
          return (
            <div key={index} style={{ marginBottom: 12 }}>
              <InterruptBox
                interrupt={msg.interrupt}
                fromDate={fromDate}
                disabled={!isActive}
              />
            </div>
          );
        }

        return null;
      })}

      {/* BOT PROCESSING */}
      {loading && (
        <div
          style={{
            background: "#f5f5f5",
            padding: 8,
            borderRadius: 8,
            maxWidth: "80%",
            marginBottom: 12,
          }}
        >
          <div style={{ fontSize: 11, color: "#363535", marginBottom: 4, fontWeight: "bold"  }}>
            Bot
          </div>
          <div style={{ fontSize: 13, color: "#666" }}>
            ⏳ Processing...
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatMessages;