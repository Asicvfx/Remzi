import type {
  AskResponse,
  ChatAskResponse,
  ChatMessage,
  ChatSession,
  LoginResponse,
  RemziDocument,
} from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000/api";

export class ApiError extends Error {
  status: number;
  payload: unknown;

  constructor(message: string, status: number, payload?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

type RequestOptions = {
  token?: string;
  method?: string;
  body?: BodyInit | object;
  headers?: HeadersInit;
};

function extractErrorMessage(payload: unknown, status: number) {
  if (typeof payload === "object" && payload !== null) {
    if ("detail" in payload) {
      return String(payload.detail);
    }

    const fieldErrors = Object.entries(payload)
      .map(([field, value]) => `${field}: ${Array.isArray(value) ? value.join(", ") : String(value)}`)
      .join("; ");

    if (fieldErrors) {
      return fieldErrors;
    }
  }

  if (typeof payload === "string" && payload.trim()) {
    return payload;
  }

  return `Request failed with ${status}`;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);

  if (options.token) {
    headers.set("Authorization", `Bearer ${options.token}`);
  }

  let body = options.body as BodyInit | undefined;
  if (options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(options.body);
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: options.method ?? "GET",
      headers,
      body,
    });
  } catch (err) {
    throw new ApiError(
      "Не удалось подключиться к backend. Проверь, что Docker и сервер на localhost:8000 запущены.",
      0,
      err,
    );
  }

  const contentType = response.headers.get("content-type") ?? "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    throw new ApiError(extractErrorMessage(payload, response.status), response.status, payload);
  }

  return payload as T;
}

export function login(username: string, password: string) {
  return request<LoginResponse>("/auth/login/", {
    method: "POST",
    body: { username, password },
  });
}

export function getDocuments(token: string) {
  return request<RemziDocument[]>("/documents/", { token });
}

export function uploadDocument(token: string, file: File, title: string) {
  const formData = new FormData();
  formData.append("file", file);
  if (title.trim()) {
    formData.append("title", title.trim());
  }

  return request<RemziDocument>("/documents/upload/", {
    token,
    method: "POST",
    body: formData,
  });
}

export function askQuestion(
  token: string,
  question: string,
  limit: number,
  documentId?: number,
) {
  return request<AskResponse>("/ask/", {
    token,
    method: "POST",
    body: {
      question,
      limit,
      ...(documentId ? { document_id: documentId } : {}),
    },
  });
}

export function getChats(token: string) {
  return request<ChatSession[]>("/chats/", { token });
}

export function createChat(token: string, title = "New chat", documentId?: number) {
  return request<ChatSession>("/chats/", {
    token,
    method: "POST",
    body: {
      title,
      ...(documentId ? { document_id: documentId } : {}),
    },
  });
}

export function getChatMessages(token: string, chatId: number) {
  return request<ChatMessage[]>(`/chats/${chatId}/messages/`, { token });
}

export function askInChat(
  token: string,
  chatId: number,
  question: string,
  limit: number,
  documentId?: number,
) {
  return request<ChatAskResponse>(`/chats/${chatId}/ask/`, {
    token,
    method: "POST",
    body: {
      question,
      limit,
      ...(documentId ? { document_id: documentId } : {}),
    },
  });
}
type StreamHandlers = {
  onDelta?: (delta: string) => void;
  onMetadata?: (metadata: unknown) => void;
};

function parseSseMessage(message: string) {
  const lines = message.split("\n");
  const event = lines.find((line) => line.startsWith("event: "))?.slice(7).trim() ?? "message";
  const data = lines
    .filter((line) => line.startsWith("data: "))
    .map((line) => line.slice(6))
    .join("\n");

  return { event, data: data ? JSON.parse(data) : null };
}

export async function askInChatStream(
  token: string,
  chatId: number,
  question: string,
  limit: number,
  documentId: number | undefined,
  handlers: StreamHandlers = {},
) {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/chats/${chatId}/ask/stream/`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        question,
        limit,
        ...(documentId ? { document_id: documentId } : {}),
      }),
    });
  } catch (err) {
    throw new ApiError(
      "Не удалось подключиться к streaming endpoint. Проверь, что backend на localhost:8000 запущен.",
      0,
      err,
    );
  }

  if (!response.ok) {
    const contentType = response.headers.get("content-type") ?? "";
    const payload = contentType.includes("application/json")
      ? await response.json()
      : await response.text();
    throw new ApiError(extractErrorMessage(payload, response.status), response.status, payload);
  }

  if (!response.body) {
    throw new ApiError("Браузер не вернул streaming body для ответа.", 0);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalPayload: ChatAskResponse | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const messages = buffer.split("\n\n");
    buffer = messages.pop() ?? "";

    for (const rawMessage of messages) {
      if (!rawMessage.trim()) {
        continue;
      }
      const { event, data } = parseSseMessage(rawMessage);
      if (event === "metadata") {
        handlers.onMetadata?.(data);
      } else if (event === "answer_delta") {
        handlers.onDelta?.(String(data?.delta ?? ""));
      } else if (event === "done") {
        finalPayload = data as ChatAskResponse;
      } else if (event === "error") {
        throw new ApiError(String(data?.detail ?? "Streaming failed"), 500, data);
      }
    }
  }

  if (!finalPayload) {
    throw new ApiError("Streaming завершился без финального сообщения.", 500);
  }

  return finalPayload;
}