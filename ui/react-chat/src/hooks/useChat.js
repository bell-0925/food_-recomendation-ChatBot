import { useState, useCallback } from "react";
import { streamMessage, resetChat as apiResetChat } from "../services/chatApi";

/**
 * 채팅 상태 관리 커스텀 훅
 * @param {string} userId
 * @param {string} teamId
 */
export function useChat(userId = "user_001", teamId = "team_alpha") {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [error, setError] = useState(null);

  const sendMessage = useCallback(
    async (text) => {
      if (!text.trim() || isStreaming) return;

      // 사용자 메시지 추가
      const userMsg = { role: "user", content: text, id: Date.now() };
      setMessages((prev) => [...prev, userMsg]);
      setError(null);
      setIsStreaming(true);
      setStreamingText("");

      try {
        let accumulated = "";

        await streamMessage(
          text,
          userId,
          teamId,
          // onToken: 토큰 누적
          (token) => {
            accumulated += token;
            setStreamingText(accumulated);
          },
          // onDone: 최종 메시지를 messages에 추가
          (_meta) => {
            const assistantMsg = {
              role: "assistant",
              content: accumulated,
              id: Date.now() + 1,
            };
            setMessages((prev) => [...prev, assistantMsg]);
            setStreamingText("");
            setIsStreaming(false);
          }
        );
      } catch (err) {
        setError(err.message || "응답 생성 중 오류가 발생했습니다.");
        setIsStreaming(false);
        setStreamingText("");
      }
    },
    [userId, teamId, isStreaming]
  );

  const resetChat = useCallback(async () => {
    try {
      await apiResetChat(userId, teamId);
      setMessages([]);
      setStreamingText("");
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }, [userId, teamId]);

  return {
    messages,
    isLoading,
    isStreaming,
    streamingText,
    error,
    sendMessage,
    resetChat,
  };
}
