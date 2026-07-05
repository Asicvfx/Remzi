import re

from apps.answers.llm import OpenAIAnswerClient
from apps.common.text import repair_mojibake
from apps.search.embeddings import TOKEN_PATTERN
from apps.search.services import SearchChunksService


MAX_ANSWER_BULLETS = 4
MAX_BULLET_LENGTH = 260
MAX_CITATION_TEXT_LENGTH = 700
CLAUSE_PATTERN = re.compile(r"(?<=[.!?。！？])\s+|\n+|;\s+|:\s+")


class LocalExtractiveAnswerComposer:
    @staticmethod
    def compose(question, search_results):
        question = repair_mojibake(question).strip()
        if not search_results:
            return LocalExtractiveAnswerComposer._empty_answer(question)

        selected_clauses = LocalExtractiveAnswerComposer._select_clauses(
            question=question,
            search_results=search_results,
        )
        if not selected_clauses:
            selected_clauses = [LocalExtractiveAnswerComposer._shorten(search_results[0]["text"])]

        if LocalExtractiveAnswerComposer._looks_cyrillic(question):
            lines = ["По найденным фрагментам:"]
            lines.extend(f"- {clause}" for clause in selected_clauses[:MAX_ANSWER_BULLETS])
            lines.append("\nОтвет основан только на найденных цитатах ниже.")
        else:
            lines = ["Based on the retrieved document chunks:"]
            lines.extend(f"- {clause}" for clause in selected_clauses[:MAX_ANSWER_BULLETS])
            lines.append("\nThis answer is based only on the citations below.")

        return "\n".join(lines)

    @staticmethod
    def _select_clauses(question, search_results):
        question_tokens = set(TOKEN_PATTERN.findall(question.lower()))
        scored_clauses = []

        for result in search_results:
            text = repair_mojibake(result["text"])
            for clause in CLAUSE_PATTERN.split(text):
                clause = LocalExtractiveAnswerComposer._shorten(clause.strip())
                if len(clause) < 20:
                    continue
                clause_tokens = set(TOKEN_PATTERN.findall(clause.lower()))
                overlap = len(question_tokens & clause_tokens)
                score = overlap + float(result["score"])
                scored_clauses.append((score, clause))

        scored_clauses.sort(key=lambda item: item[0], reverse=True)
        seen = set()
        selected = []
        for _, clause in scored_clauses:
            normalized = clause.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            selected.append(clause)
            if len(selected) >= MAX_ANSWER_BULLETS:
                break

        return selected

    @staticmethod
    def _shorten(text, max_length=MAX_BULLET_LENGTH):
        text = " ".join(repair_mojibake(text).split())
        if len(text) <= max_length:
            return text
        return text[: max_length - 3].rstrip() + "..."

    @staticmethod
    def _empty_answer(question):
        if LocalExtractiveAnswerComposer._looks_cyrillic(question):
            return "Я не нашёл релевантных фрагментов в ваших документах для этого вопроса."
        return "I could not find relevant document chunks for this question."

    @staticmethod
    def _looks_cyrillic(text):
        return any("а" <= char.lower() <= "я" or char.lower() == "ё" for char in text)


class AskQuestionService:
    @staticmethod
    def execute(user, question, limit=5, document_id=None):
        repaired_question = repair_mojibake(question)
        search_results = SearchChunksService.execute(
            user=user,
            query=repaired_question,
            limit=limit,
            document_id=document_id,
        )
        citations = AskQuestionService._trim_citations(search_results)
        generated_answer = OpenAIAnswerClient().generate_answer(
            question=repaired_question,
            citations=citations,
        )

        if generated_answer:
            answer = generated_answer.answer
            answer_mode = "openai"
            model = generated_answer.model
        else:
            answer = LocalExtractiveAnswerComposer.compose(
                question=repaired_question,
                search_results=search_results,
            )
            answer_mode = "local"
            model = ""

        return {
            "question": repaired_question,
            "answer": answer,
            "answer_mode": answer_mode,
            "model": model,
            "document_id": document_id,
            "citations": citations,
        }

    @staticmethod
    def _trim_citations(search_results):
        trimmed = []
        for result in search_results:
            item = result.copy()
            item["text"] = LocalExtractiveAnswerComposer._shorten(
                item["text"],
                max_length=MAX_CITATION_TEXT_LENGTH,
            )
            trimmed.append(item)
        return trimmed
