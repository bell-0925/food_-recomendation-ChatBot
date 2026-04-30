import React from "react";

const QUICK_ACTIONS = [
  { icon: "🍽️", label: "오늘 추천",   message: "오늘 점심 추천해줘" },
  { icon: "🗳️", label: "투표현황",   message: "투표 현황 알려줘" },
  { icon: "📊", label: "영양리포트", message: "이번 주 영양 상태 알려줘" },
  { icon: "🌤️", label: "날씨",       message: "오늘 날씨 어때?" },
];

/**
 * 빠른 액션 버튼 — 대화가 비어있을 때만 표시
 * @param {{ onAction: (message: string) => void }} props
 */
export function QuickActions({ onAction }) {
  return (
    <div className="flex flex-col items-center py-12 px-4 gap-8">
      {/* 환영 메시지 */}
      <div className="text-center">
        <div className="text-5xl mb-4">🍱</div>
        <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100 mb-1">
          오늘 뭐 먹지?
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          날씨 · 영양 · 팀 투표를 종합한 AI 점심 추천
        </p>
      </div>

      {/* 빠른 액션 버튼 */}
      <div className="grid grid-cols-2 gap-3 w-full max-w-sm">
        {QUICK_ACTIONS.map((action) => (
          <button
            key={action.label}
            onClick={() => onAction(action.message)}
            className="
              flex flex-col items-center gap-2 p-4 rounded-xl
              border border-gray-200 dark:border-gray-700
              bg-white dark:bg-gray-800
              hover:border-teal-400 hover:bg-teal-50 dark:hover:bg-teal-900/30
              transition-colors text-sm font-medium
              text-gray-700 dark:text-gray-200
            "
          >
            <span className="text-2xl">{action.icon}</span>
            <span>{action.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
