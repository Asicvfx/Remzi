export type RemziUser = {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
};

export type LoginResponse = {
  access: string;
  refresh: string;
  user: RemziUser;
};

export type DocumentStatus = "uploaded" | "processing" | "ready" | "failed";

export type RemziDocument = {
  id: number;
  title: string;
  filename: string;
  file: string;
  file_type: string;
  status: DocumentStatus;
  error_message: string;
  extracted_text_length: number;
  text_preview: string;
  chunk_count?: number;
  created_at: string;
  updated_at: string;
};

export type AnswerCitation = {
  document_id: number;
  document_title: string;
  chunk_id: number;
  chunk_index: number;
  score: number;
  text: string;
};

export type AskResponse = {
  question: string;
  answer: string;
  answer_mode: "local" | "openai";
  model: string;
  document_id: number | null;
  citations: AnswerCitation[];
};

export type ChatSession = {
  id: number;
  title: string;
  document_id: number | null;
  document_title: string | null;
  message_count: number;
  created_at: string;
  updated_at: string;
};

export type ChatMessage = {
  id: number;
  question: string;
  answer: string;
  answer_mode: "local" | "openai";
  model: string;
  document_id: number | null;
  document_title: string | null;
  citations: AnswerCitation[];
  created_at: string;
};

export type ChatAskResponse = {
  session: ChatSession;
  message: ChatMessage;
};
