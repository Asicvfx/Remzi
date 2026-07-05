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