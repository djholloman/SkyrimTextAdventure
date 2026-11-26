"""Round-2 QA regression tests. Run from the project root:
    python -m unittest discover -s tests -v
"""
import json, os, sys, unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from game import Game


def new_game(race="Nord", cls="Warrior"):
    g = Game()
    g.start("Tester", race, cls)
    return g


def ids(g):
    return [o["id"] for o in g.options()]


class FleeTests(unittest.TestCase):
    def flee(self, g):
        with mock.patch("game.random.random", return_value=0.99):  # guaranteed escape
            return g.act("run")

    def test_fleeing_helgen_fight_returns_to_choice_without_rewards(self):
        g = new_game(); g.act("ralof")
        xp, gold = g.s["xp"], g.s["gold"]
        self.flee(g)
        self.assertEqual(g.s["stage"], "helgen_choice")
        self.assertIsNone(g.s["enemy"])
        self.assertEqual((g.s["xp"], g.s["gold"]), (xp, gold))

    def test_switching_helgen_side_after_fleeing_leaves_one_faction(self):
        g = new_game(); g.act("ralof"); self.flee(g); g.act("hadvar")
        self.assertTrue(g.s["imperials"]); self.assertFalse(g.s["stormcloaks"])

    def test_fleeing_barrow_does_not_grant_dragonstone(self):
        g = new_game(); g.s["stage"] = "barrow_intro"; g.act("enter_barrow")
        self.flee(g)
        self.assertEqual(g.s["stage"], "barrow_intro")
        self.assertFalse(g.s["dragonstone"])
        self.assertNotIn("Dragonstone", g.s["inventory"])
        self.assertEqual(g.s["quests"]["Golden Claw"], "Not started")

    def test_fleeing_dragon_does_not_grant_shout_or_companion(self):
        g = new_game(); g.s["dragonstone"] = True; g._advance("whiterun")
        self.assertEqual(g.s["stage"], "combat")
        self.flee(g)
        self.assertEqual(g.s["stage"], "riverwood")
        self.assertEqual(g.s["shouts"], [])
        self.assertIsNone(g.s["companion"])

    def test_farengar_pays_only_once(self):
        g = new_game(); g.s["dragonstone"] = True; g.s["gold"] = 0
        g._advance("whiterun"); self.flee(g); g.act("travel")
        self.assertEqual(g.s["gold"], 100)

    def test_alduin_cannot_be_fled(self):
        g = new_game(); g._advance("sovngarde")
        self.assertNotIn("run", ids(g))
        with mock.patch("game.random.random", return_value=0.99):
            r = g.act("run")
        self.assertEqual(g.s["stage"], "combat")
        self.assertNotEqual(g.s["stage"], "ending")
        self.assertIsNone(g.s.get("ending_title"))

    def test_flee_offered_only_when_allowed(self):
        g = new_game(); g.act("ralof")
        self.assertIn("run", ids(g))

    def test_college_and_astrid_flee_return_to_their_menus(self):
        g = new_game(); g.s["stage"] = "branching"; g.act("college"); self.flee(g)
        self.assertEqual(g.s["stage"], "branching")
        self.assertEqual(g.s["archmage"], False)
        g.act("brotherhood"); g.act("astrid"); self.flee(g)
        self.assertEqual(g.s["stage"], "brotherhood_choice")


class GuildQuestTests(unittest.TestCase):
    def test_brotherhood_is_one_time(self):
        g = new_game(); g.s["stage"] = "branching"
        g.act("brotherhood"); g.act("merchant")
        self.assertEqual(g.s["stage"], "branching")
        self.assertNotIn("brotherhood", ids(g))
        gold = g.s["gold"]
        for _ in range(3):                       # crafted repeat attempts must be rejected
            g.act("brotherhood"); g.act("merchant")
        self.assertEqual(g.s["gold"], gold)
        self.assertEqual(g.s["stage"], "branching")
        self.assertEqual(sum("Hood" in i for i in g.s["inventory"]), 1)

    def test_actions_from_the_wrong_stage_are_ignored(self):
        g = new_game()                            # stage: helgen_choice
        before = json.dumps(g.s, sort_keys=True)
        for bad in ("brotherhood", "enter_barrow", "kill_paarthurnax", "blade", "nonsense"):
            r = g.act(bad)
            self.assertIn("That action is not available.", r["lines"])
        self.assertEqual(json.dumps(g.s, sort_keys=True), before)

    def test_college_is_one_time_and_blizzard_not_duplicated(self):
        g = new_game(); g.s["stage"] = "branching"
        g._advance("after_college")
        self.assertNotIn("college", ids(g))
        self.assertEqual(g.s["spells"].count("Blizzard"), 1)

    def test_astrid_defeat_closes_brotherhood_and_keeps_hero_flag(self):
        g = new_game(); g.s["stage"] = "branching"
        g.act("brotherhood"); g.act("astrid")
        g.s["enemy"]["hp"] = 1
        with mock.patch("game.random.randint", return_value=5):
            g.act("attack")
        self.assertEqual(g.s["stage"], "branching")
        self.assertFalse(g.s["void_champion"])
        self.assertNotIn("brotherhood", ids(g))

    def test_unfinished_guild_quests_stay_available_after_flee(self):
        g = new_game(); g.s["stage"] = "branching"; g.act("college")
        with mock.patch("game.random.random", return_value=0.99):
            g.act("run")
        self.assertIn("college", ids(g))


class MiscFixTests(unittest.TestCase):
    def test_potion_not_wasted_at_full_health(self):
        g = new_game(); g.act("ralof")
        before = g.s["inventory"].count("Healing Potion")
        hp = g.s["hp"]; g.act("potion")
        self.assertEqual(g.s["inventory"].count("Healing Potion"), before)
        self.assertEqual(g.s["hp"], hp)

    def test_sell_label_matches_payout(self):
        g = new_game(); g.s["stage"] = "shop"
        label = next(o for o in g.options() if o["id"] == "sell")["detail"]
        gold = g.s["gold"]; g.act("sell")
        self.assertIn(f"+{g.s['gold'] - gold}", label)

    def test_location_is_barrow_inside_the_barrow(self):
        g = new_game(); g._advance("barrow_intro")
        self.assertEqual(g.s["location"], "Bleak Falls Barrow")

    def test_barrow_victory_still_grants_dragonstone(self):
        g = new_game(); g.s["stage"] = "barrow_intro"; g.act("enter_barrow")
        g.s["enemy"]["hp"] = 1
        with mock.patch("game.random.randint", return_value=5):
            g.act("attack")
        self.assertTrue(g.s["dragonstone"])
        self.assertEqual(g.s["stage"], "riverwood")
        self.assertEqual(g.s["quests"]["Golden Claw"], "Completed")

    def test_old_save_without_new_keys_loads(self):
        g = new_game()
        old = json.loads(g.export_state())
        for k in ("farengar_paid", "retreat_to"):
            old.pop(k)
        g2 = Game(old)
        self.assertFalse(g2.s["farengar_paid"])
        self.assertIsNone(g2.s["retreat_to"])
        self.assertEqual(g2.s["name"], "Tester")
        self.assertIn("options", g2.result())

    def test_save_round_trip_mid_combat_keeps_retreat_rule(self):
        g = new_game(); g.act("ralof")
        g2 = Game(json.loads(g.export_state()))
        self.assertIn("run", ids(g2))

    def test_full_playthrough_reaches_an_ending(self):
        g = new_game()
        g.act("ralof")
        def win():
            while g.s["stage"] == "combat":
                g.s["enemy"]["hp"] = 1
                with mock.patch("game.random.randint", return_value=5):
                    g.act("attack" if "Fus Ro Dah" not in g.s["shouts"] else "shout")
        win(); g.act("sneak"); g.act("travel"); g.act("enter_barrow"); win()
        g.act("travel"); win(); g.act("main"); g.act("spare_paarthurnax"); win()
        self.assertEqual(g.s["stage"], "ending")
        self.assertTrue(g.s["ending_title"])


if __name__ == "__main__":
    unittest.main()
