/**
 * FastAPI 백엔드와 통신하는 API 서비스 모듈
 */

const API_BASE = "/api/chat";

/**
 * 비스트리밍 채팅 메시지 전송
 * @param {string} message
 * @param {string} userId
 * @param {string} teamId
 * @returns {Promise<{reply: string, intent: string, elapsed_ms: number}>}
 */
export async function sendMessage(message, userId = "user_001", teamId = "team_alpha") {
  const res = await fetch(API_BASE, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, user_id: userId, team_id: teamId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `서버 오류 (${res.status})`);
  }
  return res.json();
}

/**
 * SSE 스트리밍 채팅
 * @param {string} message
 * @param {string} userId
 * @param {string} teamId
 * @param {(token: string) => void} onToken  — 토큰 콜백
 * @param {(meta: object) => void}  onDone   — 완료 콜백
 */
export async function streamMessage(message, userId = "user_001", teamId = "team_alpha", onToken, onDone) {
  const url =
    `${API_BASE}/stream?` +
    `message=${encodeURIComponent(message)}&` +
    `user_id=${encodeURIComponent(userId)}&` +
    `team_id=${encodeURIComponent(teamId)}`;

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`서버 오류 (${response.status})`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // SSE는 "\n\n"으로 이벤트를 구분합니다.
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? ""; // 마지막 불완전한 청크는 버퍼에 유지

    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data: ")) continue;
      try {
        const data = JSON.parse(line.slice(6)); // "data: " 이후 파싱
        if (data.type === "token" && onToken) {
          onToken(data.content);
        } else if (data.type === "done" && onDone) {
          onDone(data.metadata || {});
        } else if (data.type === "error") {
          throw new Error(data.content || "스트리밍 오류");
        }
      } catch (e) {
        console.warn("SSE 파싱 오류:", e, line);
      }
    }
  }
}

/**
 * 대화 초기화
 */
export async function resetChat(userId = "user_001", teamId = "team_alpha") {
  const res = await fetch(`${API_BASE}/reset`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, team_id: teamId }),
  });
  if (!res.ok) throw new Error(`초기화 실패 (${res.status})`);
  return res.json();
}

/**
 * 서버 상태 확인
 * @returns {Promise<{status: string, llm_provider: string, llm_model: string}>}
 */
export async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) return { status: "error", available: false };
    const data = await res.json();
    return { ...data, available: data.status === "ok" };
  } catch {
    return { status: "error", available: false };
  }
}
