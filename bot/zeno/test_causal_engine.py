import unittest
from datetime import datetime, timedelta
from bot.zeno.causal_engine import CausalConsistencyEngine, Event, CausalLinkHypothesis

class TestCausalConsistencyEngine(unittest.TestCase):

    def setUp(self):
        self.engine = CausalConsistencyEngine()

    def test_logical_consistency_success(self):
        """Test that validation succeeds when premise happens before conclusion."""
        event1 = Event(id="A", timestamp=datetime.now(), content="Cause")
        event2 = Event(id="B", timestamp=datetime.now() + timedelta(seconds=1), content="Effect")
        hypothesis = CausalLinkHypothesis(premise=event1, conclusion=event2, explanation="Explanation")
        self.assertTrue(self.engine._validate_logical_consistency(hypothesis))

    def test_logical_consistency_failure(self):
        """Test that validation fails when premise happens after conclusion."""
        event1 = Event(id="A", timestamp=datetime.now() + timedelta(seconds=1), content="Cause")
        event2 = Event(id="B", timestamp=datetime.now(), content="Effect")
        hypothesis = CausalLinkHypothesis(premise=event1, conclusion=event2, explanation="Explanation")
        self.assertFalse(self.engine._validate_logical_consistency(hypothesis))

    def test_semantic_relevance_success(self):
        """Test that validation succeeds for semantically similar content."""
        event1 = Event(id="A", timestamp=datetime.now(), content="The cat sat on the mat.")
        event2 = Event(id="B", timestamp=datetime.now(), content="A feline was resting on the rug.")
        hypothesis = CausalLinkHypothesis(premise=event1, conclusion=event2, explanation="Explanation")
        self.assertTrue(self.engine._validate_semantic_relevance(hypothesis))

    def test_semantic_relevance_failure(self):
        """Test that validation fails for semantically dissimilar content."""
        event1 = Event(id="A", timestamp=datetime.now(), content="The cat sat on the mat.")
        event2 = Event(id="B", timestamp=datetime.now(), content="The price of bitcoin reached a new high.")
        hypothesis = CausalLinkHypothesis(premise=event1, conclusion=event2, explanation="Explanation")
        self.assertFalse(self.engine._validate_semantic_relevance(hypothesis))

if __name__ == '__main__':
    unittest.main()