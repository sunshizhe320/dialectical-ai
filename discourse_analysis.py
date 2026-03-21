import re

class DiscourseAnalyzer:
    def __init__(self):
        # Define English Discourse Patterns
        self.patterns = {
            "Questioning": r"\?|what|how|why|can you|could you",
            "Claim/Opinion": r"i think|i believe|in my opinion|from my perspective|i suggest",
            "Agreement": r"i agree|exactly|correct|right|support|true",
            "Disagreement": r"i disagree|however|but|on the contrary|not really",
            "Clarification": r"mean|specifically|example|instance|to clarify",
            "Elaboration": r"because|since|therefore|moreover|furthermore|additionally"
        }

    def analyze_text(self, text):
        """Analyze the discourse type of the input text"""
        text = text.lower()
        results = {
            "detected_types": [],
            "word_count": len(text.split()),
            "sentiment_hint": "Neutral"
        }

        # Match patterns
        for d_type, pattern in self.patterns.items():
            if re.search(pattern, text):
                results["detected_types"].append(d_type)

        # Simple Sentiment Hint
        if any(word in text for word in ["good", "great", "excellent", "agree", "support"]):
            results["sentiment_hint"] = "Positive"
        elif any(word in text for word in ["bad", "wrong", "disagree", "flaw", "error"]):
            results["sentiment_hint"] = "Critical"

        # Default type if none detected
        if not results["detected_types"]:
            results["detected_types"].append("General Statement")

        return results

analyzer = DiscourseAnalyzer()