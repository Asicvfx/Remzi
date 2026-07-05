"use client";

import { FormEvent, useEffect, useMemo, useRef, useState, useTransition } from "react";

import {
  ApiError,
  askInChatStream,
  createChat,
  getChatMessages,
  getChats,
  getDocuments,
  login,
  uploadDocument,
} from "@/lib/api";
import type { ChatMessage, ChatSession, RemziDocument, RemziUser } from "@/lib/types";

const TOKEN_STORAGE_KEY = "remzi.accessToken";
const USER_STORAGE_KEY = "remzi.user";

function statusLabel(status: RemziDocument["status"]) {
  const labels = {
    uploaded: "Загружен",
    processing: "Обработка",
    ready: "Готов",
    failed: "Ошибка",
  };

  return labels[status];
}

function getFriendlyErrorMessage(err: unknown, fallback: string) {
  if (err instanceof ApiError) {
    if (err.status === 0) {
      return err.message;
    }
    if (err.status === 401) {
      return "Сессия истекла или токен больше не подходит. Войдите в Remzi заново.";
    }
    if (err.status === 400) {
      return `Проверьте данные формы: ${err.message}`;
    }
    if (err.status === 404) {
      return "Объект не найден. Обновите workspace и попробуйте снова.";
    }
    if (err.status >= 500) {
      return "Backend вернул ошибку сервера. Проверьте Docker logs backend/worker и попробуйте снова.";
    }

    return err.message || fallback;
  }

  return err instanceof Error ? err.message : fallback;
}

export default function Home() {
  const [token, setToken] = useState("");
  const [user, setUser] = useState<RemziUser | null>(null);
  const [username, setUsername] = useState("remzi-user");
  const [password, setPassword] = useState("StrongPass123");
  const [documents, setDocuments] = useState<RemziDocument[]>([]);
  const [chats, setChats] = useState<ChatSession[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<number | undefined>();
  const [selectedChatId, setSelectedChatId] = useState<number | undefined>();
  const [question, setQuestion] = useState("что написано про опыт работы");
  const [limit, setLimit] = useState(5);
  const [uploadTitle, setUploadTitle] = useState("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [typingMessageId, setTypingMessageId] = useState<number | null>(null);
  const [typingAnswer, setTypingAnswer] = useState("");
  const [streamingQuestion, setStreamingQuestion] = useState("");
  const [streamingAnswer, setStreamingAnswer] = useState("");
  const typingIntervalRef = useRef<number | null>(null);
  const [isPending, startTransition] = useTransition();
  const processingDocuments = useMemo(
    () => documents.filter((document) => document.status === "uploaded" || document.status === "processing"),
    [documents],
  );
  const readyDocumentsCount = useMemo(
    () => documents.filter((document) => document.status === "ready").length,
    [documents],
  );
  const hasProcessingDocuments = processingDocuments.length > 0;

  useEffect(() => {
    const savedToken = window.localStorage.getItem(TOKEN_STORAGE_KEY);
    const savedUser = window.localStorage.getItem(USER_STORAGE_KEY);

    if (savedToken) {
      setToken(savedToken);
    }
    if (savedUser) {
      setUser(JSON.parse(savedUser) as RemziUser);
    }
  }, []);

  useEffect(() => {
    if (!token) {
      return;
    }

    void refreshWorkspace(token);
  }, [token]);

  useEffect(() => {
    if (!token || !selectedChatId) {
      setMessages([]);
      return;
    }

    void refreshMessages(token, selectedChatId);
  }, [token, selectedChatId]);
  useEffect(() => {
    if (!token || !hasProcessingDocuments) {
      return;
    }

    const intervalId = window.setInterval(() => {
      void refreshWorkspace(token, { silent: true });
    }, 3000);

    return () => window.clearInterval(intervalId);
  }, [token, hasProcessingDocuments]);

  useEffect(() => {
    return () => stopTypingEffect();
  }, []);

  function resetSessionState() {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    window.localStorage.removeItem(USER_STORAGE_KEY);
    stopTypingEffect();
    setTypingMessageId(null);
    setTypingAnswer("");
    setStreamingQuestion("");
    setStreamingAnswer("");
    setToken("");
    setUser(null);
    setDocuments([]);
    setChats([]);
    setMessages([]);
    setSelectedChatId(undefined);
    setSelectedDocumentId(undefined);
  }

  function handleRequestError(err: unknown, fallback: string) {
    const message = getFriendlyErrorMessage(err, fallback);

    if (err instanceof ApiError && err.status === 401) {
      resetSessionState();
      setError(message);
      return;
    }

    setError(message);
  }

  async function refreshWorkspace(activeToken = token, options: { silent?: boolean } = {}) {
    if (!options.silent) {
      setError("");
    }
    try {
      const [documentData, chatData] = await Promise.all([
        getDocuments(activeToken),
        getChats(activeToken),
      ]);
      setDocuments(documentData);
      setChats(chatData);

      if (!selectedDocumentId && documentData.length > 0) {
        const firstReadyDocument = documentData.find((document) => document.status === "ready") ?? documentData[0];
        setSelectedDocumentId(firstReadyDocument.id);
      }
      if (!selectedChatId && chatData.length > 0) {
        setSelectedChatId(chatData[0].id);
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        handleRequestError(err, "Не удалось загрузить workspace");
        return;
      }
      if (!options.silent) {
        handleRequestError(err, "Не удалось загрузить workspace");
      }
    }
  }

  async function refreshMessages(activeToken = token, chatId = selectedChatId) {
    if (!activeToken || !chatId) {
      return;
    }

    try {
      const data = await getChatMessages(activeToken, chatId);
      setMessages(data);
    } catch (err) {
      handleRequestError(err, "Не удалось загрузить историю чата");
    }
  }

  function stopTypingEffect() {
    if (typingIntervalRef.current !== null) {
      window.clearInterval(typingIntervalRef.current);
      typingIntervalRef.current = null;
    }
  }

  function playTypingEffect(message: ChatMessage) {
    stopTypingEffect();
    setTypingMessageId(message.id);
    setTypingAnswer("");

    const fullAnswer = message.answer;
    const stepSize = Math.max(2, Math.ceil(fullAnswer.length / 140));
    let cursor = 0;

    typingIntervalRef.current = window.setInterval(() => {
      cursor = Math.min(cursor + stepSize, fullAnswer.length);
      setTypingAnswer(fullAnswer.slice(0, cursor));

      if (cursor >= fullAnswer.length) {
        stopTypingEffect();
        setTypingMessageId(null);
        setTypingAnswer("");
      }
    }, 18);
  }

  function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setNotice("");

    startTransition(() => {
      void (async () => {
        try {
          const data = await login(username, password);
          window.localStorage.setItem(TOKEN_STORAGE_KEY, data.access);
          window.localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(data.user));
          setToken(data.access);
          setUser(data.user);
          setNotice("Вошли в Remzi. Загружаю документы и историю.");
          await refreshWorkspace(data.access);
        } catch (err) {
          handleRequestError(err, "Не удалось войти");
        }
      })();
    });
  }

  function handleLogout() {
    resetSessionState();
    setNotice("Вы вышли из Remzi.");
  }

  function handleNewChat() {
    if (!token) {
      return;
    }

    startTransition(() => {
      void (async () => {
        try {
          const chat = await createChat(token, "New chat", selectedDocumentId);
          setChats((current) => [chat, ...current]);
          setSelectedChatId(chat.id);
          setMessages([]);
          setNotice("Создан новый чат. Следующий вопрос сохранится в историю.");
        } catch (err) {
          handleRequestError(err, "Не удалось создать чат");
        }
      })();
    });
  }

  function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || !uploadFile) {
      setError("Выберите файл PDF, DOCX или TXT.");
      return;
    }

    setError("");
    setNotice("Загружаю документ. После загрузки worker начнет обработку текста.");

    startTransition(() => {
      void (async () => {
        try {
          const uploaded = await uploadDocument(token, uploadFile, uploadTitle);
          setUploadTitle("");
          setUploadFile(null);
          setSelectedDocumentId(uploaded.id);
          setNotice("Документ загружен. Я сам обновляю статус каждые 3 секунды, пока он не станет Ready.");
          await refreshWorkspace();
        } catch (err) {
          handleRequestError(err, "Не удалось загрузить документ");
        }
      })();
    });
  }

  function handleAsk(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) {
      setError("Сначала войдите в аккаунт.");
      return;
    }

    if (selectedDocument?.status === "failed") {
      setError(`Документ "${selectedDocument.title}" не обработался: ${selectedDocument.error_message || "ошибка извлечения текста"}. Загрузите другой файл или проверьте исходный документ.`);
      return;
    }
    if (selectedDocument?.status === "uploaded" || selectedDocument?.status === "processing") {
      setError(`Документ "${selectedDocument.title}" еще обрабатывается. Дождитесь статуса Ready, затем спросите снова.`);
      return;
    }
    if (!selectedDocument && documents.length > 0 && readyDocumentsCount === 0) {
      setError("Пока нет документов со статусом Ready. Дождитесь обработки или загрузите другой файл.");
      return;
    }

    setError("");
    setNotice("Ищу chunks, спрашиваю модель и сохраняю ответ в историю.");

    startTransition(() => {
      void (async () => {
        try {
          let chatId = selectedChatId;
          if (!chatId) {
            const chat = await createChat(token, "New chat", selectedDocumentId);
            chatId = chat.id;
            setChats((current) => [chat, ...current]);
            setSelectedChatId(chat.id);
          }

          setStreamingQuestion(question);
          setStreamingAnswer("");
          const data = await askInChatStream(token, chatId, question, limit, selectedDocumentId, {
            onDelta: (delta) => setStreamingAnswer((current) => current + delta),
          });
          setStreamingQuestion("");
          setStreamingAnswer("");
          setMessages((current) => [...current, data.message]);
          setChats((current) => [data.session, ...current.filter((chat) => chat.id !== data.session.id)]);
          setSelectedChatId(data.session.id);
          setNotice(
            data.message.answer_mode === "openai"
              ? "Ответ сохранен в историю и собран через OpenAI."
              : "Ответ сохранен в историю локальным fallback-режимом.",
          );
        } catch (err) {
          setStreamingQuestion("");
          setStreamingAnswer("");
          handleRequestError(err, "Не удалось получить ответ");
        }
      })();
    });
  }

  const selectedDocument = documents.find((document) => document.id === selectedDocumentId);
  const selectedChat = chats.find((chat) => chat.id === selectedChatId);
  const lastMessage = messages[messages.length - 1];

  return (
    <main className="shell">
      <section className="hero panel">
        <div>
          <p className="eyebrow">Remzi Stage 15</p>
          <h1>Ответы теперь идут потоком, без ожидания полной генерации.</h1>
          <p className="heroCopy">
            Remzi открывает streaming endpoint, показывает answer delta по мере генерации и сохраняет финальный ответ в историю.
            Старый ask pipeline остается рядом как надежная основа.
          </p>
        </div>
        <div className="heroBadge">
          <span>{streamingQuestion ? "Streaming" : typingMessageId ? "Typing" : lastMessage?.answer_mode === "openai" ? "OpenAI" : "Memory"}</span>
          <strong>{streamingQuestion ? "live answer" : typingMessageId ? "live answer" : hasProcessingDocuments ? `${processingDocuments.length} processing` : lastMessage?.model || `${messages.length} saved`}</strong>
        </div>
      </section>

      <section className="workspace">
        <aside className="sidebar panel">
          {!token ? (
            <form className="stack" onSubmit={handleLogin}>
              <div>
                <p className="eyebrow">Login</p>
                <h2>Войти в Remzi</h2>
              </div>
              <label>
                Username
                <input value={username} onChange={(event) => setUsername(event.target.value)} />
              </label>
              <label>
                Password
                <input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
              </label>
              <p className="loginHint">
                Нажми большую кнопку ниже. После входа здесь появятся Upload, Documents и Chats.
              </p>
              <button disabled={isPending} type="submit">
                {isPending ? "Входим..." : "Войти в Remzi"}
              </button>
            </form>
          ) : (
            <div className="stack">
              <div className="accountCard">
                <div>
                  <p className="eyebrow">Account</p>
                  <h2>{user?.username ?? "Remzi user"}</h2>
                </div>
                <button className="ghost" onClick={handleLogout} type="button">
                  Выйти
                </button>
              </div>

              <form className="uploadBox" onSubmit={handleUpload}>
                <p className="eyebrow">Upload</p>
                <input
                  placeholder="Название документа"
                  value={uploadTitle}
                  onChange={(event) => setUploadTitle(event.target.value)}
                />
                <input
                  accept=".pdf,.docx,.txt"
                  type="file"
                  onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)}
                />
                <button disabled={isPending} type="submit">
                  Загрузить
                </button>
              </form>

              <div className="documentsHeader">
                <div>
                  <p className="eyebrow">Chats</p>
                  <h2>{chats.length} чатов</h2>
                </div>
                <button className="ghost" onClick={handleNewChat} type="button">
                  New
                </button>
              </div>

              <div className="documentList">
                {chats.map((chat) => (
                  <button
                    className={`documentCard ${selectedChatId === chat.id ? "active" : ""}`}
                    key={chat.id}
                    onClick={() => setSelectedChatId(chat.id)}
                    type="button"
                  >
                    <span className="status ready">{chat.message_count} msg</span>
                    <strong>{chat.title}</strong>
                    <small>{chat.document_title || "Все документы"}</small>
                  </button>
                ))}
              </div>

              <div className="documentsHeader">
                <div>
                  <p className="eyebrow">Documents</p>
                  <h2>{documents.length} файлов</h2>
                  <span className={`pollingPill ${hasProcessingDocuments ? "active" : ""}`}>
                    {hasProcessingDocuments ? "Auto refresh on" : "Auto refresh idle"}
                  </span>
                </div>
                <button className="ghost" onClick={() => void refreshWorkspace()} type="button">
                  Refresh now
                </button>
              </div>

              <div className="documentList">
                {documents.map((document) => (
                  <button
                    className={`documentCard ${selectedDocumentId === document.id ? "active" : ""}`}
                    key={document.id}
                    onClick={() => setSelectedDocumentId(document.id)}
                    type="button"
                  >
                    <span className={`status ${document.status}`}>{statusLabel(document.status)}</span>
                    <strong>{document.title}</strong>
                    <small>{document.filename}</small>
                    <small>{document.extracted_text_length || 0} chars</small>
                    {document.status === "failed" && document.error_message && (
                      <small className="documentError">{document.error_message}</small>
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}
        </aside>

        <section className="chat panel">
          <div className="chatTop">
            <div>
              <p className="eyebrow">Ask</p>
              <h2>{selectedChat ? selectedChat.title : selectedDocument?.title || "Все документы"}</h2>
            </div>
            {selectedDocument && <span className={`status ${selectedDocument.status}`}>{statusLabel(selectedDocument.status)}</span>}
          </div>

          {selectedDocument?.status === "failed" && (
            <div className="message error">
              Этот документ не готов для вопросов: {selectedDocument.error_message || "ошибка обработки файла"}
            </div>
          )}
          {(selectedDocument?.status === "uploaded" || selectedDocument?.status === "processing") && (
            <div className="message">
              Документ еще обрабатывается. Remzi сам обновит статус, когда он станет Ready.
            </div>
          )}

          <form className="askForm" onSubmit={handleAsk}>
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Например: что написано про опыт работы?"
            />
            <div className="askControls">
              <label>
                Limit
                <input
                  max={10}
                  min={1}
                  type="number"
                  value={limit}
                  onChange={(event) => setLimit(Number(event.target.value))}
                />
              </label>
              <label>
                Scope
                <select
                  value={selectedDocumentId ?? ""}
                  onChange={(event) => setSelectedDocumentId(event.target.value ? Number(event.target.value) : undefined)}
                >
                  <option value="">Все документы</option>
                  {documents.map((document) => (
                    <option key={document.id} value={document.id}>
                      #{document.id} {document.title}
                    </option>
                  ))}
                </select>
              </label>
              <button disabled={isPending || !token || (selectedDocument ? selectedDocument.status !== "ready" : documents.length > 0 && readyDocumentsCount === 0)} type="submit">
                {isPending ? "Думаю..." : "Спросить и сохранить"}
              </button>
            </div>
          </form>

          {(notice || error) && (
            <div className={`message ${error ? "error" : ""}`}>{error || notice}</div>
          )}

          {(messages.length > 0 || streamingQuestion) ? (
            <div className="historyList">
              {messages.map((message) => {
                const isTyping = typingMessageId === message.id;

                return (
                <article className={`answerCard ${isTyping ? "typingCard" : ""}`} key={message.id}>
                  <div className="answerMeta">
                    <span>{message.answer_mode === "openai" ? "OpenAI answer" : "Local fallback"}</span>
                    <span>{message.model || "no model"}</span>
                  </div>
                  <h3>{message.question}</h3>
                  <p className={`answerText ${isTyping ? "typing" : ""}`}>
                    {isTyping ? typingAnswer : message.answer}
                    {isTyping && <span aria-hidden="true" className="typingCursor" />}
                  </p>
                  <div className="citations">
                    <h3>Цитаты</h3>
                    {message.citations.map((citation) => (
                      <div className="citation" key={`${message.id}-${citation.chunk_id}`}>
                        <div>
                          <strong>{citation.document_title}</strong>
                          <span>chunk #{citation.chunk_id} / score {citation.score.toFixed(3)}</span>
                        </div>
                        <p>{citation.text}</p>
                      </div>
                    ))}
                  </div>
                </article>
                );
              })}
              {streamingQuestion && (
                <article className="answerCard typingCard">
                  <div className="answerMeta">
                    <span>Streaming answer</span>
                    <span>live</span>
                  </div>
                  <h3>{streamingQuestion}</h3>
                  <p className="answerText typing">
                    {streamingAnswer}
                    <span aria-hidden="true" className="typingCursor" />
                  </p>
                </article>
              )}
            </div>
          ) : (
            <div className="emptyState">
              <span>15</span>
              <h3>Рабочее место готово к streaming-вопросу.</h3>
              <p>Войди, загрузи документ и дождись Ready. Новый ответ будет появляться здесь прямо во время генерации.</p>
            </div>
          )}
        </section>
      </section>
    </main>
  );
}

