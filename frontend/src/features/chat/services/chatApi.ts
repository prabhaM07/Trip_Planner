import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000",
});

export const sendMessageToBackend = async (
  message?: string,
  interruptResponse?: string,
  sessionId?: string,
  pdf?: string
) => {
  const { data } = await api.post("/travel", {
    user_query: message ?? null,
    interrupt_response: interruptResponse ?? null,
    session_id: sessionId,
    pdf: pdf ?? null
  });
  return data;
};

export const uploadFileToBackend = async (formData: FormData) => {
  const { data } = await api.post("/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

  return data; 
};


