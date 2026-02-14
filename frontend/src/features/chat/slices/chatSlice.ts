import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { sendMessageToBackend } from "../services/chatApi";
import type { ChatState, InterruptPayload } from "../../../types/chat-types";

const generateSessionId = () =>
  `session-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

const initialState: ChatState = {
  messages: [],
  loading: false,
  sessionId: generateSessionId(),
  hasActiveInterrupt: false
};

export const sendMessage = createAsyncThunk(
  "chat/sendMessage",
  async (
    payload: { text?: string; interruptAnswer?: string; pdf?: string },
    { getState }
  ) => {
    const state = getState() as { chat: ChatState };

    const response = await sendMessageToBackend(
      payload.text,
      payload.interruptAnswer,
      state.chat.sessionId,
      payload.pdf
    );

    return response;
  }
);

const chatSlice = createSlice({
  name: "chat",
  initialState,
  reducers: {
    clearChat(state) {
      state.messages = [];
      state.sessionId = generateSessionId();
    },
  },
  extraReducers: (builder) => {
    builder

      /* USER MESSAGE APPEARS IMMEDIATELY */
      .addCase(sendMessage.pending, (state, action) => {
        state.loading = true;

        const { text, interruptAnswer, pdf } = action.meta.arg;

        if(pdf){
          state.messages.push({ sender: "user", text: `${text} and Uploaded PDF path: ${pdf}` });
        }
        else if(text) {
          state.messages.push({ sender: "user", text });
        }

        if (interruptAnswer) {
          state.messages.push({ sender: "user", text: interruptAnswer });
        }
      })

      /* BOT ANSWER APPEARS AFTER RESPONSE */
      .addCase(sendMessage.fulfilled, (state, action) => {
        state.loading = false;

        const res = action.payload;

        if (res.type === "interrupt") {
          state.loading = false;
          state.hasActiveInterrupt = true;
          state.messages.push({
            sender: "bot",
            interrupt: res as InterruptPayload,
          });
        } else {
          state.loading = false;
          state.hasActiveInterrupt = false;
          state.messages.push({
            sender: "bot",
            text: res.answer,
          });
        }
      })

      /* ERROR CASE */
      .addCase(sendMessage.rejected, (state) => {
        state.loading = false;
        state.messages.push({
          sender: "bot",
          text: "Something went wrong. Please try again.",
        });
      });
  },
});

export const { clearChat } = chatSlice.actions;
export default chatSlice.reducer;
