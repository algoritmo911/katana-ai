import unittest
import time
from hydra_observer.reactor.reaction_core import reaction_core
from hydra_observer.reactor.handlers import handle_high_cpu

class TestStress(unittest.TestCase):
    def test_stress_reaction_core(self):
        """Tests the Reaction Core under a high volume of events."""
        reaction_core.register("high_cpu", handle_high_cpu)

        start_time = time.time()
        for i in range(100):
            reaction_core.trigger("high_cpu", {"cpu_percent": 90 + i / 100})
        end_time = time.time()

        duration = end_time - start_time
        print(f"Stress test completed in {duration:.4f} seconds.")
        # We are looking for this to complete in a reasonable amount of time,
        # and not raise any exceptions.
        self.assertTrue(duration < 1, "Stress test took too long.")

if __name__ == '__main__':
    unittest.main()
