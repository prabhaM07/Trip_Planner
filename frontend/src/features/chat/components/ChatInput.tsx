import { useState, useRef } from "react";
import { useAppDispatch, useAppSelector } from "../../../app/hooks";
import { sendMessage } from "../slices/chatSlice";
import { uploadFileToBackend } from "../services/chatApi";

const ChatInput = () => {
  const [value, setValue] = useState("");
  const [pdfPath, setPdfPath] = useState<string | undefined>();

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const dispatch = useAppDispatch();

  const { loading, hasActiveInterrupt } = useAppSelector(
    (state) => state.chat
  );

  const isDisabled = loading || hasActiveInterrupt;
  const isFileUploaded = Boolean(pdfPath);

  const send = () => {
    if ((!value.trim() && !pdfPath) || isDisabled) return;

    dispatch(
      sendMessage({
        text: value || undefined,
        pdf: pdfPath,
      })
    );

    setValue("");
    setPdfPath(undefined);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      send();
    }
  };

  const handlePlusClick = () => {
    if (isDisabled || isFileUploaded) return;
    fileInputRef.current?.click();
  };

  const handleFileChange = async (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
      const data = await uploadFileToBackend(formData);
      setPdfPath(data.path);
    } catch (error) {
      console.error("File upload failed:", error);
    }

    e.target.value = "";
  };

  return (
    <div style={{ display: "flex", gap: 8, padding: 2 }}>
      
      {/* Upload button */}
      <button
        onClick={handlePlusClick}
        disabled={isDisabled || isFileUploaded}
        style={{
          padding: "8px",
          borderRadius: 4,
          border: "1px solid #ccc",
          background: "#fff",
          cursor: isFileUploaded ? "not-allowed" : "pointer",
          opacity: isDisabled || isFileUploaded ? 0.6 : 1,
        }}
      >
        {isFileUploaded ? "⬇" : "+"}
      </button>

      <input
        type="file"
        ref={fileInputRef}
        accept=".pdf,.png,.jpg,.jpeg"
        onChange={handleFileChange}
        style={{ display: "none" }}
      />

      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={
          pdfPath ? "PDF attached. Add a message…" : "Type your message..."
        }
        disabled={isDisabled}
        style={{
          flex: 1,
          padding: 8,
          border: "1px solid #ccc",
          borderRadius: 4,
        }}
      />

      <button
        onClick={send}
        disabled={isDisabled || (!value.trim() && !pdfPath)}
        style={{
          padding: "8px 16px",
          background: "linear-gradient(90deg, #E11162, #F26538, #EFB85A)",
          color: "#fff",
          border: "none",
          borderRadius: 4,
          cursor: "pointer",
          opacity: isDisabled ? 0.6 : 1,
        }}
      >
        {loading ? "..." : "Send"}
      </button>
    </div>
  );
};

export default ChatInput;
