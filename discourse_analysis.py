"""
discourse_analysis.py
Discourse and Argumentation Analysis Module
Provides structured analysis of discussions and arguments
"""

import json
from datetime import datetime


class DiscourseAnalyzer:
    """Analyzes discussion discourse and argument structures"""
    
    def __init__(self):
        self.analysis_cache = {}
    
    def analyze_messages(self, messages):
        """
        Analyze messages for argument structure
        
        Args:
            messages: List of message dicts with 'user', 'message', 'role' keys
            
        Returns:
            dict with analysis results
        """
        if not messages or len(messages) < 2:
            return {
                "status": "insufficient_data",
                "message": "Need at least 2 messages to analyze"
            }
        
        analysis = {
            "total_messages": len(messages),
            "participants": self._extract_participants(messages),
            "message_distribution": self._analyze_distribution(messages),
            "argument_indicators": self._find_argument_markers(messages),
            "timestamp": datetime.now().isoformat()
        }
        
        return analysis
    
    def _extract_participants(self, messages):
        """Extract unique participants"""
        participants = {}
        for msg in messages:
            user = msg.get('user', 'Unknown')
            if user not in participants:
                participants[user] = {
                    "message_count": 0,
                    "first_appearance": None,
                    "last_appearance": None
                }
            participants[user]["message_count"] += 1
            if not participants[user]["first_appearance"]:
                participants[user]["first_appearance"] = msg.get('timestamp')
            participants[user]["last_appearance"] = msg.get('timestamp')
        
        return participants
    
    def _analyze_distribution(self, messages):
        """Analyze message distribution by participant"""
        distribution = {}
        for msg in messages:
            user = msg.get('user', 'Unknown')
            distribution[user] = distribution.get(user, 0) + 1
        return distribution
    
    def _find_argument_markers(self, messages):
        """Find markers of argumentation in messages"""
        markers = {
            "support_phrases": [
                "I agree", "I think", "In my opinion", "I believe",
                "support", "因为", "because", "理由是"
            ],
            "counter_phrases": [
                "However", "But", "On the contrary", "I disagree",
                "但是", "然而", "反对", "opposite"
            ],
            "evidence_phrases": [
                "evidence", "example", "research", "study", "证据",
                "例如", "数据", "实例", "research shows"
            ],
            "question_phrases": [
                "?", "Why", "How", "What", "为什么", "怎样", "什么"
            ]
        }
        
        found_markers = {
            "support": 0,
            "counter": 0,
            "evidence": 0,
            "questions": 0
        }
        
        for msg in messages:
            content = msg.get('message', '').lower()
            
            for phrase in markers["support_phrases"]:
                if phrase.lower() in content:
                    found_markers["support"] += 1
            
            for phrase in markers["counter_phrases"]:
                if phrase.lower() in content:
                    found_markers["counter"] += 1
            
            for phrase in markers["evidence_phrases"]:
                if phrase.lower() in content:
                    found_markers["evidence"] += 1
            
            for phrase in markers["question_phrases"]:
                if phrase.lower() in content:
                    found_markers["questions"] += 1
        
        return found_markers


# Create global analyzer instance
analyzer = DiscourseAnalyzer()