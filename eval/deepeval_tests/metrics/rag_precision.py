"""
RAG Precision Metric for VLLM Evaluation

This metric evaluates the precision of Retrieval-Augmented Generation (RAG) systems
by measuring how relevant the retrieved context is to the generated answer.
"""

import asyncio
import logging
import re
from difflib import SequenceMatcher
from typing import Optional

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase

logger = logging.getLogger(__name__)


class RAGPrecisionMetric(BaseMetric):
    """
    RAG Precision Metric

    Evaluates the precision of RAG systems by measuring:
    1. Context relevance to the question
    2. Answer grounding in the provided context
    3. Factual accuracy of the generated response

    Args:
        threshold (float): Minimum precision score to pass (0.0 to 1.0)
        model (str): Model name for evaluation (optional)
        include_reason (bool): Include detailed reasoning in results
        strict_mode (bool): Use strict evaluation criteria
    """

    def __init__(
        self,
        threshold: float = 0.7,
        model: Optional[str] = None,
        include_reason: bool = True,
        strict_mode: bool = False,
        async_mode: bool = True,
    ):
        self.threshold = threshold
        self.model = model
        self.include_reason = include_reason
        self.strict_mode = strict_mode
        self.async_mode = async_mode

        # Initialize metric properties
        self.score = 0.0
        self.success = False
        self.reason = ""

    def measure(self, test_case: LLMTestCase) -> float:
        """Synchronous measurement entry point"""
        if self.async_mode:
            return asyncio.run(self.a_measure(test_case))
        return self._evaluate_sync(test_case)

    async def a_measure(self, test_case: LLMTestCase, _show_indicator: bool = True) -> float:
        """Asynchronous measurement"""
        return self._evaluate_sync(test_case)

    def _evaluate_sync(self, test_case: LLMTestCase) -> float:
        """Core evaluation logic"""
        try:
            # Extract components from test case
            question = test_case.input
            actual_output = test_case.actual_output
            expected_output = test_case.expected_output
            retrieval_context = getattr(test_case, "retrieval_context", [])

            # Calculate precision components
            context_relevance = self._calculate_context_relevance(question, retrieval_context)
            answer_grounding = self._calculate_answer_grounding(actual_output, retrieval_context)
            factual_accuracy = self._calculate_factual_accuracy(actual_output, expected_output)

            # Weighted precision score
            precision_score = self._calculate_weighted_precision(
                context_relevance, answer_grounding, factual_accuracy
            )

            # Set metric properties
            self.score = precision_score
            self.success = precision_score >= self.threshold

            if self.include_reason:
                self.reason = self._generate_detailed_reason(
                    precision_score, context_relevance, answer_grounding, factual_accuracy
                )

            logger.info(f"RAG Precision Score: {precision_score:.3f}")
            return precision_score

        except Exception as e:
            logger.error(f"Error in RAG precision evaluation: {e}")
            self.score = 0.0
            self.success = False
            self.reason = f"Evaluation failed: {e!s}"
            return 0.0

    def _calculate_context_relevance(self, question: str, context: list[str]) -> float:
        """Calculate how relevant the retrieved context is to the question"""
        if not context:
            return 0.0

        question_keywords = self._extract_keywords(question)
        if not question_keywords:
            return 0.0

        relevance_scores = []

        for ctx in context:
            ctx_keywords = self._extract_keywords(ctx)
            if not ctx_keywords:
                relevance_scores.append(0.0)
                continue

            # Calculate keyword overlap
            overlap = len(question_keywords.intersection(ctx_keywords))
            total_keywords = len(question_keywords.union(ctx_keywords))

            if total_keywords == 0:
                relevance_scores.append(0.0)
            else:
                # Jaccard similarity
                jaccard_score = overlap / total_keywords

                # Semantic similarity (simplified)
                semantic_score = self._calculate_semantic_similarity(question, ctx)

                # Combined relevance score
                combined_score = 0.6 * jaccard_score + 0.4 * semantic_score
                relevance_scores.append(combined_score)

        # Return average relevance across all context pieces
        return sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0

    def _calculate_answer_grounding(self, answer: str, context: list[str]) -> float:
        """Calculate how well the answer is grounded in the provided context"""
        if not context or not answer:
            return 0.0

        answer_sentences = self._split_into_sentences(answer)
        grounding_scores = []

        for sentence in answer_sentences:
            sentence_grounding = 0.0

            for ctx in context:
                # Check for direct text overlap
                similarity = SequenceMatcher(None, sentence.lower(), ctx.lower()).ratio()
                sentence_grounding = max(sentence_grounding, similarity)

            grounding_scores.append(sentence_grounding)

        # Average grounding across all sentences
        avg_grounding = sum(grounding_scores) / len(grounding_scores) if grounding_scores else 0.0

        # Apply strict mode penalty if enabled
        if self.strict_mode:
            # Penalize if any sentence has low grounding
            min_grounding = min(grounding_scores) if grounding_scores else 0.0
            avg_grounding = 0.7 * avg_grounding + 0.3 * min_grounding

        return avg_grounding

    def _calculate_factual_accuracy(self, actual_output: str, expected_output: str) -> float:
        """Calculate factual accuracy by comparing with expected output"""
        if not expected_output:
            return 1.0  # No ground truth to compare against

        # Extract key facts from both outputs
        actual_facts = self._extract_facts(actual_output)
        expected_facts = self._extract_facts(expected_output)

        if not expected_facts:
            return 1.0

        # Calculate fact overlap
        correct_facts = 0
        for expected_fact in expected_facts:
            for actual_fact in actual_facts:
                similarity = SequenceMatcher(
                    None, expected_fact.lower(), actual_fact.lower()
                ).ratio()
                if similarity > 0.8:  # High similarity threshold for facts
                    correct_facts += 1
                    break

        accuracy = correct_facts / len(expected_facts)
        return accuracy

    def _calculate_weighted_precision(
        self, context_relevance: float, answer_grounding: float, factual_accuracy: float
    ) -> float:
        """Calculate weighted precision score"""
        # Weights for different components
        weights = {"context_relevance": 0.3, "answer_grounding": 0.4, "factual_accuracy": 0.3}

        precision = (
            weights["context_relevance"] * context_relevance
            + weights["answer_grounding"] * answer_grounding
            + weights["factual_accuracy"] * factual_accuracy
        )

        return min(1.0, max(0.0, precision))

    def _extract_keywords(self, text: str) -> set:
        """Extract keywords from text (simplified implementation)"""
        # Remove punctuation and convert to lowercase
        cleaned_text = re.sub(r"[^\w\s]", "", text.lower())

        # Split into words and filter out common stop words
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "can",
            "this",
            "that",
            "these",
            "those",
        }

        words = cleaned_text.split()
        keywords = {word for word in words if len(word) > 2 and word not in stop_words}

        return keywords

    def _calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity (simplified implementation)"""
        # This is a simplified implementation
        # In production, you might use sentence transformers or other embeddings

        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union) if union else 0.0

    def _split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences"""
        # Simple sentence splitting
        sentences = re.split(r"[.!?]+", text)
        return [s.strip() for s in sentences if s.strip()]

    def _extract_facts(self, text: str) -> list[str]:
        """Extract factual statements from text (simplified)"""
        sentences = self._split_into_sentences(text)

        # Filter sentences that likely contain facts
        facts = []
        for sentence in sentences:
            # Look for sentences with numbers, dates, or specific entities
            if re.search(r"\d+", sentence) or re.search(
                r"\b(is|are|was|were|has|have|will|can|should)\b", sentence.lower()
            ):
                facts.append(sentence)

        return facts

    def _generate_detailed_reason(
        self,
        precision_score: float,
        context_relevance: float,
        answer_grounding: float,
        factual_accuracy: float,
    ) -> str:
        """Generate detailed reasoning for the precision score"""
        status = "✅ PASSED" if self.success else "❌ FAILED"

        reason = f"{status} - RAG Precision Score: {precision_score:.3f}\n\n"
        reason += "Component Breakdown:\n"
        reason += f"• Context Relevance: {context_relevance:.3f}\n"
        reason += f"• Answer Grounding: {answer_grounding:.3f}\n"
        reason += f"• Factual Accuracy: {factual_accuracy:.3f}\n\n"

        # Provide specific feedback
        if context_relevance < 0.5:
            reason += (
                "⚠️ Low context relevance - retrieved context may not be relevant to the question\n"
            )

        if answer_grounding < 0.5:
            reason += "⚠️ Poor answer grounding - answer may contain information not supported by context\n"

        if factual_accuracy < 0.5:
            reason += "⚠️ Low factual accuracy - answer may contain incorrect information\n"

        if precision_score >= self.threshold:
            reason += f"✅ Score meets threshold of {self.threshold}"
        else:
            reason += f"❌ Score below threshold of {self.threshold}"

        return reason

    def is_successful(self) -> bool:
        """Return whether the evaluation was successful"""
        return self.success

    @property
    def __name__(self):
        return "RAG Precision"


# Convenience function for easy metric creation
def create_rag_precision_metric(threshold: float = 0.7, **kwargs) -> RAGPrecisionMetric:
    """Create a RAG Precision metric with default settings"""
    return RAGPrecisionMetric(threshold=threshold, **kwargs)
