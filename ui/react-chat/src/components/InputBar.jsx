import React, { useState, useRef } from "react";
import { Send } from "lucide-react";

/**
 * 메시지 입력 바
 * @param {{ onSend: (text: string) => void, disabled?: boolean }} props
 */
export function InputBar({ onSend, disabled = false }) {
  const [text, setText] = useState("");
  const textareaRef = useRef(null);

  const handleSubmit = () => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
    // 높이 초기화
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleInput = (e) => {
    setText(e.target.value);
    // 자동 높이 조정
    const ta = textareaRef.current;
    if (ta) {
      ta.style.height = "auto";
      ta.style.height = `${Math.min(ta.scrollHeight, 120)}px`;
    }
  };

  return (
    <div className="flex items-end gap-3 p-4 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
      <textarea
        ref={textareaRef}
        rows={1}
        value={text}
        onChange={handleInput}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        placeholder={disabled ? "응답 중..." : "점심에 대해 뭐든 물어보세요! (Enter 전송, Shift+Enter 줄바꿈)"}
        className="
          flex-1 resize-none rounded-xl border border-gray-300 dark:border-gray-600
          bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-gray-100
          px-4 py-3 text-sm leading-snug
          focus:outline-none focus:ring-2 focus:ring-teal-400
          disabled:opacity-50 disabled:cursor-not-allowed
          transition-colors
        "
        style={{ minHeight: "44px", maxHeight: "120px" }}
      />
      <button
        onClick={handleSubmit}
        disabled={disabled || !text.trim()}
        className="
          flex-shrink-0 w-11 h-11 rounded-xl
          bg-teal-500 hover:bg-teal-600 disabled:bg-gray-300 dark:disabled:bg-gray-600
          text-white flex items-center justify-center
          transition-colors disabled:cursor-not-allowed
        "
        aria-label="전송"
      >
        <Send size={18} />
      </button>
    </div>
  );
}
