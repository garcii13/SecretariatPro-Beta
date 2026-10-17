import unittest

from secretariat_core.led_temporal import ReadingConsensus


class ClockProgressionTests(unittest.TestCase):
    def test_slow_countdown_and_countup_publish_without_duplicate_frames(self):
        for values in (("02:03", "02:01", "01:59"), ("01:59", "02:01", "02:03")):
            consensus = ReadingConsensus(2)
            result = [consensus.observe("time", value, captured_at=i * 2.0,
                                        confidence=0.95) for i, value in enumerate(values)]
            self.assertEqual(result, [None, values[1], values[2]])

    def test_jumps_weak_reads_and_long_gaps_do_not_confirm(self):
        for value, timestamp, confidence in (("08:27", 2, .95), ("02:19", 2, .4), ("02:01", 20, .95)):
            consensus = ReadingConsensus(2)
            consensus.observe("time", "02:21", captured_at=0, confidence=.95)
            self.assertIsNone(consensus.observe("time", value, captured_at=timestamp, confidence=confidence))

    def test_empty_read_breaks_confirmation_and_scores_remain_strict(self):
        consensus = ReadingConsensus(2)
        consensus.observe("time", "02:21", captured_at=0, confidence=.95)
        consensus.observe("time", "", captured_at=1, confidence=0)
        self.assertIsNone(consensus.observe("time", "02:19", captured_at=2, confidence=.95))
        self.assertIsNone(consensus.observe("team1_score", "1", captured_at=0, confidence=.95))
        self.assertIsNone(consensus.observe("team1_score", "2", captured_at=1, confidence=.95))
        self.assertEqual(consensus.observe("team1_score", "2", captured_at=2, confidence=.95), "2")
