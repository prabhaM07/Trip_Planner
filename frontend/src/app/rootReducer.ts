import { combineReducers } from "@reduxjs/toolkit";
import chatReducer from "../features/chat/slices/chatSlice";

export const rootReducer = combineReducers({
  chat: chatReducer,
});

export type RootState = ReturnType<typeof rootReducer>;
