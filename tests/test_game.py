import json
import random
import unittest
from unittest.mock import patch

import game


class GameRegressionTests(unittest.TestCase):
    def make_thief(self):
        g = game.Game()
        g.start("QA_Test", "Khajiit", "Thief")
        return g

    def test_khajiit_thief_creation(self):
        g = self.make_thief()
        s = g.s
        self.assertEqual(s["hp"], 100)
        self.assertEqual(s["mana"], 50)
        self.assertEqual(s["attack"], 23)
        self.assertEqual(s["spell"], 10)
        self.assertEqual(s["defense"], 5)
        self.assertEqual(s["gold"], 100)
        self.assertEqual(
            s["inventory"],
            ["Sweetroll", "Healing Potion", "Skooma", "Steel Dagger"],
        )

    def test_sweetroll_can_only_be_sold_once(self):
        g = self.make_thief()
        g.s["stage"] = "shop"
        starting_gold = g.s["gold"]

        g.act("sell")
        self.assertEqual(g.s["gold"], starting_gold + 5)
        self.assertNotIn("Sweetroll", g.s["inventory"])

        g.act("sell")
        self.assertEqual(g.s["gold"], starting_gold + 5)
        self.assertIn("nothing to sell", " ".join(g.lines).lower())

    def test_successful_flee_clears_combat_state(self):
        g = self.make_thief()
        g._combat("Test Bandit", 40, 8, 2, 10, 10, "bear_choice", retreat="helgen_choice")

        with patch("game.random.random", return_value=0.9):
            result = g.act("run")

        # Fleeing returns to the scene before the fight, not forward in the story.
        self.assertEqual(g.s["stage"], "helgen_choice")
        self.assertIsNone(g.s["enemy"])
        self.assertIsNone(g.s["after_combat"])
        self.assertIsNone(g.s["retreat_to"])
        self.assertEqual(result["state"]["stage"], "helgen_choice")

    def test_failed_flee_keeps_combat_state(self):
        g = self.make_thief()
        g._combat("Test Bandit", 40, 8, 2, 10, 10, "bear_choice", retreat="helgen_choice")
        starting_hp = g.s["hp"]

        with patch("game.random.random", return_value=0.1), \
             patch("game.random.randint", return_value=2):
            g.act("run")

        self.assertEqual(g.s["stage"], "combat")
        self.assertIsNotNone(g.s["enemy"])
        self.assertEqual(g.s["hp"], starting_hp - 5)  # 8 attack + 2 roll - 5 defense

    def test_unknown_combat_action_does_not_trigger_enemy_turn(self):
        g = self.make_thief()
        g._combat("Test Bandit", 40, 8, 2, 10, 10, "bear_choice")
        starting_hp = g.s["hp"]
        g.act("not-a-real-action")
        self.assertEqual(g.s["hp"], starting_hp)
        self.assertEqual(g.s["enemy"]["hp"], 40)

    def test_save_load_roundtrip_preserves_state(self):
        g = self.make_thief()
        g.act("ralof")
        payload = g.export_state()
        restored = game.Game(json.loads(payload))
        self.assertEqual(restored.s, g.s)
        self.assertEqual(restored.result()["state"]["stage"], "combat")

    def test_combat_victory_clears_enemy_and_destination(self):
        g = self.make_thief()
        g._combat("Weak Rat", 1, 1, 0, 2, 3, "bear_choice")
        with patch("game.random.randint", return_value=5):
            g.act("attack")
        self.assertEqual(g.s["stage"], "bear_choice")
        self.assertIsNone(g.s["enemy"])
        self.assertIsNone(g.s["after_combat"])


if __name__ == "__main__":
    unittest.main()
