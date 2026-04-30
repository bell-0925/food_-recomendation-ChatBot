import React, { useEffect, useRef, useState } from "react";
import { RefreshCw, Wifi, WifiOff } from "lucide-react";
import { useChat } from "./hooks/useChat";
import { MessageBubble } from "./components/MessageBubble";
import { InputBar } from "./components/InputBar";
import { QuickActions } from "./components/QuickActions";
import { checkHealth } from "./services/chatApi";

const USER_ID = "user_001";
const TEAM_ID = "team_alpha";

export default function App() {
  const { messages, isStreaming, streamingText, error, sendMessage, resetChat } =
    useChat(USER_ID, TEAM_ID);

  const [serverAvailable, setServerAvailable] = useState(null); // null = 확인 중
  const [serverInfo, setServerInfo] = useState({});
  const bottomRef = useRef(null);

  // ── 서버 상태 확인 ─────────────────────────────────
  useEffect(() => {
    checkHealth().then((info) => {
      setServerAvailable(info.available);
      setServerInfo(info);
    });
  }, []);

  // ── 자동 스크롤 ────────────────────────────────────
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText]);

  const isEmpty = messages.length === 0 && !isStreaming;

  return (
    <div className="flex flex-col h-screen bg-gray-50 dark:bg-gray-900">
      {/* 헤더 */}
      <header className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-sm">
        <div className="flex items-center gap-2">
          <span className="text-xl">🍱</span>
          <h1 className="font-semibold text-gray-900 dark:text-gray-100">오늘 뭐 먹지?</h1>
          {serverInfo.llm_model && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400">
              {serverInfo.llm_model}
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
          {/* 서버 연결 상태 */}
          {serverAvailable === null ? (
            <span className="text-xs text-gray-400">연결 확인 중…</span>
          ) : serverAvailable ? (
            <span className="flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
              <Wifi size={14} /> 연결됨
            </span>
          ) : (
            <span className="flex items-center gap-1 text-xs text-red-500">
              <WifiOff size={14} /> 서버 미연결
            </span>
          )}

          {/* 초기화 버튼 */}
          <button
            onClick={resetChat}
            disabled={isStreaming}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-40 transition-colors"
            title="대화 초기화"
          >
            <RefreshCw size={16} className="text-gray-500 dark:text-gray-400" />
          </button>
        </div>
      </header>

      {/* 서버 미연결 경고 */}
      {serverAvailable === false && (
        <div className="bg-amber-50 dark:bg-amber-900/20 border-b border-amber-200 dark:border-amber-700 px-4 py-2 text-xs text-amber-700 dark:text-amber-400">
          ⚠️ FastAPI 서버에 연결할 수 없습니다.{" "}
          <code className="font-mono">uvicorn api.main:app --reload --port 8000</code> 로 서버를 시작해주세요.
        </div>
      )}

      {/* 메시지 영역 */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-2xl mx-auto w-full px-4 py-4">
          {isEmpty ? (
            <QuickActions onAction={sendMessage} />
          ) : (
            <>
              {messages.map((msg) => (
                <MessageBubble key={msg.id} role={msg.role} content={msg.content} />
              ))}

              {/* 스트리밍 중 어시스턴트 응답 */}
              {isStreaming && (
                <MessageBubble
                  role="assistant"
                  content={streamingText || ""}
                  isStreaming={true}
                />
              )}
            </>
          )}

          {/* 에러 표시 */}
          {error && (
            <div className="text-center text-xs text-red-500 py-2">
              ⚠️ {error}
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </main>

      {/* 입력 바 */}
      <InputBar onSend={sendMessage} disabled={isStreaming} />
    </div>
  );
}
