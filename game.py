"""Browser-ready, turn-based adaptation of Skyrim: The Chronicles of the Dragonborn.
The game rules and state live in Python; the browser supplies choices through act().
"""
import json
import random

class Game:
    @staticmethod
    def _defaults():
        return {
            "started": False, "stage": "intro", "name": "Dragonborn",
            "race": "Nord", "character_class": "Warrior",
            "level": 1, "xp": 0, "xp_needed": 100,
            "hp": 100, "max_hp": 100, "mana": 50, "max_mana": 50,
            "attack": 15, "spell": 10, "defense": 5, "gold": 50,
            "inventory": ["Sweetroll", "Healing Potion"], "spells": ["Flames"],
            "shouts": [], "companion": None, "location": "Helgen",
            "discovered": ["Helgen"],
            "stormcloaks": False, "imperials": False, "dragonstone": False,
            "paarthurnax_killed": False, "archmage": False, "void_champion": False,
            "farengar_paid": False, "retreat_to": None,
            "enemy": None, "after_combat": None, "log": [],
            "skills": {
                "One-Handed": 15,
                "Destruction": 15,
                "Sneak": 15,
                "Speech": 15,
            },
            "perk_points": 0,
            "perks": [],
            "quests": {"Golden Claw": "Not started", "College of Winterhold": "Not started",
                       "Dark Brotherhood": "Not started", "Main Quest": "In progress"}
        }

    def __init__(self, saved=None):
        self.s = self._defaults()
        if saved:
            # Merge over defaults so saves from older builds (missing newer keys) still load.
            quests = dict(self.s["quests"])
            quests.update(saved.get("quests") or {})
            self.s.update(saved)
            self.s["quests"] = quests
        self.lines = []

    def say(self, *lines):
        self.lines.extend(lines)

    def state(self):
        s = self.s
        return {
            "stage": s["stage"], "name": s["name"], "race": s["race"],
            "character_class": s["character_class"], "level": s["level"],
            "xp": s["xp"], "xp_needed": s["xp_needed"], "hp": s["hp"],
            "max_hp": s["max_hp"], "mana": s["mana"], "max_mana": s["max_mana"],
            "attack": s["attack"], "spell": s["spell"], "defense": s["defense"],
            "gold": s["gold"], "inventory": s["inventory"], "spells": s["spells"],
            "shouts": s["shouts"], "companion": s["companion"],
            "location": s["location"], "discovered": s.get("discovered", []),
            "quests": s["quests"],
            "skills": s.get("skills", {}), "perk_points": s.get("perk_points", 0),
            "perks": s.get("perks", []),
            "enemy": s["enemy"], "ending_title": s.get("ending_title"),
            "game_over": s["stage"] == "game_over",
            "won": s["stage"] == "ending"
        }

    def _discover(self, loc):
        """Record that the player has visited a location (for travel menu + UI theme)."""
        disc = self.s.setdefault("discovered", [])
        if loc and loc not in disc:
            disc.append(loc)

    def _set_location(self, loc):
        self.s["location"] = loc
        self._discover(loc)

    def export_state(self):
        return json.dumps(self.s)

    def improve_skill(self, skill, amount=1):
        skills = self.s.setdefault("skills", {
            "One-Handed": 15, "Destruction": 15, "Sneak": 15, "Speech": 15
        })
        if skill not in skills:
            return
        prev = skills[skill]
        skills[skill] = min(100, skills[skill] + amount)
        # Announce every 10-point threshold crossed
        for threshold in range((prev // 10 + 1) * 10, skills[skill] + 1, 10):
            self.say(f"{skill} increased to {skills[skill]}!")
            break  # one message per call is enough

    def _xp(self, amount):
        self.say(f"You gained {amount} experience.")
        self.s["xp"] += amount
        while self.s["xp"] >= self.s["xp_needed"]:
            self.s["xp"] -= self.s["xp_needed"]
            self.s["level"] += 1
            self.s["xp_needed"] = int(self.s["xp_needed"] * 1.5)
            self.s["max_hp"] += 20
            self.s["max_mana"] += 15
            self.s["hp"] = self.s["max_hp"]
            self.s["mana"] = self.s["max_mana"]
            self.s["attack"] += 5
            self.s["spell"] += 4
            self.s["defense"] += 2
            self.s["perk_points"] = self.s.get("perk_points", 0) + 1
            self.say(f"LEVEL UP! You are now level {self.s['level']}. Your health, mana, and combat power increase.",
                     f"You gained a perk point! ({self.s['perk_points']} available)")

    def _combat(self, name, hp, attack, defense, gold, xp, after, retreat=None):
        self.s["enemy"] = {"name": name, "hp": hp, "max_hp": hp, "attack": attack,
                           "defense": defense, "gold": gold, "xp": xp}
        self.s["after_combat"] = after
        self.s["retreat_to"] = retreat  # None = no escape
        self.s["stage"] = "combat"
        self.say(f"{name} blocks your path. Prepare for battle!")

    def _win_combat(self):
        e = self.s["enemy"]
        self.say(f"You defeated {e['name']}!", f"You looted {e['gold']} Septims.")
        self.s["gold"] += e["gold"]
        self._xp(e["xp"])
        self.s["enemy"] = None
        next_stage = self.s["after_combat"]
        self.s["after_combat"] = None
        self.s["retreat_to"] = None
        self._advance(next_stage)

    def _advance(self, stage):
        s = self.s
        s["stage"] = stage
        if stage == "bear_choice":
            self._set_location("Helgen Keep")
            self.say("You descend into the tunnels beneath Helgen. A sleeping cave bear guards the exit.")
        elif stage == "riverwood":
            self._set_location("Riverwood")
            self.say("You emerge beneath the cold sky. The road leads to Riverwood, a quiet logging village.",
                     "Locals whisper of dragon sightings and urge you to seek the Jarl of Whiterun.")
        elif stage == "whiterun":
            self._set_location("Whiterun")
            self.say("You pass beneath the gates of Whiterun and climb to Dragonsreach.")
            if s["dragonstone"]:
                if not s["farengar_paid"]:
                    self.say("Farengar studies the Dragonstone and rewards you with 100 Septims.")
                    s["gold"] += 100
                    s["farengar_paid"] = True
                else:
                    self.say("Farengar nods as you return to Dragonsreach.")
                self.say("A guard bursts in: a dragon has been sighted at the Western Watchtower!")
                self._combat("Mirmulnir — Dragon", 150, 25, 10, 200, 150, "after_dragon",
                             retreat="riverwood")
            else:
                self.say("Farengar needs the Dragonstone from Bleak Falls Barrow before he can help.")
                self._advance("barrow_intro")
        elif stage == "barrow_intro":
            self._set_location("Bleak Falls Barrow")
        elif stage == "barrow_complete":
            s["dragonstone"] = True
            s["inventory"].extend(["Golden Claw", "Dragonstone"])
            s["quests"]["Golden Claw"] = "Completed"
            self.say("You cut Arvel free, recover the Golden Claw and discover the Dragonstone tablet.",
                     "Bleak Falls Barrow is complete. The Jarl of Whiterun needs this discovery.")
            self._xp(80)
            self._advance("riverwood")
        elif stage == "after_dragon":
            self.say("The dragon's energy flows into your chest. The guards stare in disbelief: Dragonborn!")
            if "Fus Ro Dah" not in s["shouts"]:
                s["shouts"].append("Fus Ro Dah")
            s["companion"] = "Lydia"
            self.say("You learn the shout Fus Ro Dah. Jarl Balgruuf names you Thane and assigns Lydia as your housecarl.")
            self._xp(150)
            self._discover("Whiterun")
            self._advance("branching")
        elif stage == "branching":
            self._set_location("Skyrim")
            self.say("The Greybeards summon you to High Hrothgar, but powerful guilds have noticed your deeds.")
        elif stage == "after_college":
            s["archmage"] = True
            s["quests"]["College of Winterhold"] = "Completed"
            s["spells"].append("Blizzard")
            self._discover("College of Winterhold")
            self.say("The mages elect you Archmage of Winterhold. You learn Blizzard.")
            self._xp(120)
            self._advance("branching")
        elif stage == "after_brotherhood":
            s["quests"]["Dark Brotherhood"] = "Completed"
            self._discover("Dark Brotherhood Sanctuary")
            if not s["void_champion"]:
                self.say("You have destroyed the Dark Brotherhood leadership! You are a hero of the light.")
            self._advance("branching")
        elif stage == "paarthurnax":
            self._set_location("High Hrothgar")
            self.say("At the summit of the Throat of the World, Paarthurnax reveals the path to Sovngarde.",
                     "Delphine demands that you kill the ancient dragon. The choice is yours.")
        elif stage == "sovngarde":
            self._set_location("Sovngarde")
            self.say("You pass through the portal into the glowing skies of Sovngarde.",
                     "Alduin, the World-Eater, descends upon the heroes of old!")
            self._combat("Alduin — World-Eater", 250, 35, 20, 500, 300, "ending")
        elif stage == "travel":
            self.say("The roads of Skyrim stretch before you. Where will you travel?")
        elif stage == "ending":
            self._ending()
        elif stage == "game_over":
            self.say("Your vision fades. The cold winds of Sovngarde call your name. GAME OVER.")

    def _ending(self):
        s = self.s
        s["quests"]["Main Quest"] = "Completed"
        if s["void_champion"] and s["paarthurnax_killed"]:
            title = "THE DARK DESTROYER"
            desc = "Having slain Alduin and Paarthurnax, you embrace the whispers of the Dark Brotherhood. Skyrim fears the Dragonborn, assassin and tyrant."
        elif s["archmage"] and not s["paarthurnax_killed"]:
            title = "THE ENLIGHTENED SOVEREIGN"
            desc = "With Alduin defeated and Paarthurnax spared, you guide the College of Winterhold as Archmage. Magic and dragon lore flourish."
        elif s["stormcloaks"]:
            title = "THE LIBERATOR OF SKYRIM"
            desc = "You lead the Stormcloaks to victory. Skyrim is free from Imperial rule, and your name is sung in every tavern."
        elif s["imperials"]:
            title = "THE EMPIRE'S SHIELD"
            desc = "You secure Skyrim for the Empire. The Emperor awards you a medal of highest honor."
        else:
            title = "THE WANDERING HERO"
            desc = "You decline power and political alliances, wandering Skyrim as a legendary protector of the weak."
        self.say(f"THE SAGA IS WRITTEN — {title}", desc, "Thank you for playing The Chronicles of the Dragonborn.")
        s["ending_title"] = title

    def start(self, name, race, character_class):
        if race not in ("Nord", "High Elf", "Khajiit"): race = "Nord"
        if character_class not in ("Warrior", "Mage", "Thief"): character_class = "Warrior"
        s = self.s
        s.update({"started": True, "name": (name or "Dragonborn")[:24], "race": race,
                  "character_class": character_class, "stage": "helgen_choice"})
        self.say("THE CHRONICLES OF THE DRAGONBORN",
                 "“Hey you, you're finally awake...” The cart rattles toward Helgen.",
                 "A blond prisoner whispers that you were trying to cross the border. The Imperial captain calls your name.",
                 f"The scribe studies you: a {race} who claims to be a {character_class}.",
                 "The executioner's axe rises. A terrible roar shakes the mountains. Alduin has come!")
        if race == "Nord":
            s["max_hp"] += 20; s["hp"] = s["max_hp"]; s["defense"] += 3
        elif race == "High Elf":
            s["max_mana"] += 30; s["mana"] = s["max_mana"]; s["spell"] += 8
        else:
            s["attack"] += 8; s["inventory"].append("Skooma")
        if character_class == "Warrior":
            s["attack"] += 5; s["inventory"].append("Iron Sword")
            s["skills"]["One-Handed"] = 25
        elif character_class == "Mage":
            s["spells"].append("Spark"); s["inventory"].append("Staff of Sparks")
            s["skills"]["Destruction"] = 25
        else:
            s["inventory"].append("Steel Dagger"); s["gold"] += 50
            s["skills"]["Sneak"] = 25
            s["skills"]["Speech"] = 25
        return self.result()

    def result(self):
        opts = self.options()
        return {"lines": self.lines, "state": self.state(), "options": opts}

    def _travel_options(self):
        """Build destination list from story progress and discovered locations."""
        s = self.s
        current = s.get("location", "")
        disc = set(s.get("discovered", []))
        opts = []

        # Riverwood is always available once the player has reached it.
        if "Riverwood" in disc and current != "Riverwood":
            opts.append({"id": "go_riverwood", "label": "Riverwood",
                         "detail": "Quiet logging village on the White River"})

        # Whiterun opens after the player has left Helgen (Riverwood reached).
        if "Riverwood" in disc and current != "Whiterun":
            opts.append({"id": "go_whiterun", "label": "Whiterun",
                         "detail": "City of the plains · Dragonsreach"})

        # Bleak Falls if the claw quest is active or already done.
        claw = s["quests"].get("Golden Claw", "Not started")
        if claw != "Not started" and current != "Bleak Falls Barrow":
            opts.append({"id": "go_barrow", "label": "Bleak Falls Barrow",
                         "detail": "Ancient Nordic ruin in the mountains"})

        # Open world hubs after the dragon fight (branching unlocked).
        open_world = "Skyrim" in disc or s.get("companion") == "Lydia" or s["quests"].get("Main Quest") == "Completed"
        if open_world:
            if current != "College of Winterhold" and s["quests"].get("College of Winterhold") != "Not started":
                opts.append({"id": "go_college", "label": "College of Winterhold",
                             "detail": "Arcane citadel of the north"})
            if current != "High Hrothgar" and ("High Hrothgar" in disc or open_world):
                opts.append({"id": "go_hrothgar", "label": "High Hrothgar",
                             "detail": "Monastery of the Greybeards"})
            if "Dark Brotherhood Sanctuary" in disc and current != "Dark Brotherhood Sanctuary":
                opts.append({"id": "go_sanctuary", "label": "Dark Brotherhood Sanctuary",
                             "detail": "Hidden refuge of the Night Mother"})

        # Sovngarde only if already visited (story takes you there).
        if "Sovngarde" in disc and current != "Sovngarde":
            opts.append({"id": "go_sovngarde", "label": "Sovngarde",
                         "detail": "Hall of the honored dead"})

        if not opts:
            opts.append({"id": "travel_none", "label": "No new roads yet",
                         "detail": "Continue the main path to open destinations"})
        opts.append({"id": "travel_back", "label": "Stay where you are",
                     "detail": "Return without traveling"})
        return opts

    def _handle_travel(self, action):
        """Process a travel-menu choice and move the player."""
        s = self.s
        back = s.pop("travel_return", "riverwood")

        if action in ("travel_back", "travel_none"):
            self.say("You remain where you stand.")
            s["stage"] = back
            return

        if action == "go_riverwood":
            self.say("You follow the forest path back to the quiet village of Riverwood.")
            self._advance("riverwood")
        elif action == "go_whiterun":
            self.say("The road climbs through the plains toward the gates of Whiterun.")
            # If the early main quest is still open, running Whiterun continues it.
            # After the dragon fight the city is a safe hub that returns to branching.
            if s.get("companion") == "Lydia" or s["quests"].get("Main Quest") == "Completed":
                self._set_location("Whiterun")
                s["stage"] = "branching"
                self.say("Whiterun's markets bustle. Lydia waits near the Bannered Mare if you need her.")
            else:
                self._advance("whiterun")
        elif action == "go_barrow":
            self.say("You climb the frozen trail toward Bleak Falls Barrow.")
            if s["quests"].get("Golden Claw") == "Completed":
                self._set_location("Bleak Falls Barrow")
                s["stage"] = "riverwood"
                self.say("The barrow is silent now. The Dragonstone and claw are already yours.")
            else:
                self._advance("barrow_intro")
        elif action == "go_college":
            self.say("Northward winds guide you to the College of Winterhold.")
            self._set_location("College of Winterhold")
            s["stage"] = "branching"
            self.say("Mages study under the cold aurora. The Eye of Magnus still hums if unfinished business remains.")
        elif action == "go_hrothgar":
            self.say("You ascend the seven thousand steps once more to High Hrothgar.")
            self._set_location("High Hrothgar")
            # If Paarthurnax choice not yet made, offer the summit encounter.
            if not s.get("paarthurnax_killed") and s["quests"].get("Main Quest") != "Completed":
                self._advance("paarthurnax")
            else:
                s["stage"] = "branching"
                self.say("The Greybeards meditate in silence. The path to Sovngarde is known to you.")
        elif action == "go_sanctuary":
            self.say("You slip through the shadows to the Dark Brotherhood Sanctuary.")
            self._set_location("Dark Brotherhood Sanctuary")
            s["stage"] = "branching"
            self.say("Black doors and whispered contracts. The family remembers your deeds.")
        elif action == "go_sovngarde":
            self.say("The portal opens once more onto the golden mist of Sovngarde.")
            self._advance("sovngarde")
        else:
            self.say("That road is closed to you.")
            s["stage"] = back

    def options(self):
        stage = self.s["stage"]
        if stage == "intro": return []
        if stage == "helgen_choice": return [
            {"id":"ralof","label":"Follow Ralof into the tower","detail":"Stand with the Stormcloaks"},
            {"id":"hadvar","label":"Follow Hadvar into the keep","detail":"Stand with the Imperials"}]
        if stage == "bear_choice": return [
            {"id":"sneak","label":"Creep past the sleeping bear","detail":"Avoid a dangerous fight"},
            {"id":"bear","label":"Ambush the cave bear","detail":"Risk combat for experience"}]
        if stage == "riverwood":
            opts = [
                {"id":"shop","label":"Visit Alvor's blacksmith","detail":"Buy equipment or sell trinkets"},
                {"id":"trader","label":"Speak with Lucan Valerius","detail":"The Golden Claw quest"},
                # Direct main-path travel (also keeps regression tests / older saves working)
                {"id":"travel","label":"Travel to Whiterun","detail":"Continue the main story"},
                {"id":"open_travel","label":"Travel the roads of Skyrim","detail":"Choose any unlocked destination"},
                {"id":"stats","label":"Review character status","detail":"Inspect your character"}]
            if self.s.get("perk_points", 0) > 0:
                opts.append({"id":"perks","label":"Spend perk point","detail":f"{self.s['perk_points']} available"})
            return opts
        if stage == "shop": return [
            {"id":"blade","label":"Buy Steel Blade — 50 gold","detail":"+10 attack"},
            {"id":"armor","label":"Buy Iron Armor — 40 gold","detail":"+5 defense"},
            {"id":"sell","label":"Sell your Sweetroll","detail":"+5 gold (one-time)"},
            {"id":"back","label":"Return to Riverwood","detail":""}]
        if stage == "trader": return [
            {"id":"barrow","label":"Retrieve the Golden Claw","detail":"Explore Bleak Falls Barrow"},
            {"id":"decline","label":"Decline the offer","detail":"Return to the village"}]
        if stage == "barrow_intro": return [{"id":"enter_barrow","label":"Enter Bleak Falls Barrow","detail":"Face the ancient ruin"}]
        if stage == "travel":
            return self._travel_options()
        if stage == "branching":
            q = self.s["quests"]
            opts = [{"id":"main","label":"Path of the Dragonborn","detail":"High Hrothgar and Alduin"}]
            if q["College of Winterhold"] != "Completed":
                opts.append({"id":"college","label":"Join the College of Winterhold","detail":"The Eye of Magnus"})
            if q["Dark Brotherhood"] != "Completed":
                opts.append({"id":"brotherhood","label":"Join the Dark Brotherhood","detail":"A contract in an abandoned shack"})
            opts.append({"id":"open_travel","label":"Travel the roads of Skyrim","detail":"Choose a destination"})
            opts.append({"id":"stats","label":"Review character status","detail":"Inspect your character"})
            if self.s.get("perk_points", 0) > 0:
                opts.append({"id":"perks","label":"Spend perk point","detail":f"{self.s['perk_points']} available"})
            return opts
        if stage == "perk_menu":
            skills = self.s.get("skills", {})
            owned = set(self.s.get("perks", []))
            opts = []
            if "Armsman" not in owned and skills.get("One-Handed", 0) >= 20:
                opts.append({"id":"perk_armsman","label":"Armsman","detail":"One-Handed 20 · +5 weapon damage"})
            if "Pyromancer" not in owned and skills.get("Destruction", 0) >= 20:
                opts.append({"id":"perk_pyromancer","label":"Pyromancer","detail":"Destruction 20 · +10 spell damage"})
            if "Shadowfoot" not in owned and skills.get("Sneak", 0) >= 20:
                opts.append({"id":"perk_shadowfoot","label":"Shadowfoot","detail":"Sneak 20 · +20% escape chance"})
            if not opts:
                opts.append({"id":"perk_none","label":"No perks available yet","detail":"Raise skills to 20 to unlock perks"})
            opts.append({"id":"perk_back","label":"Return","detail":"Leave the perk menu"})
            return opts
        if stage == "brotherhood_choice": return [
            {"id":"merchant","label":"Kill the fearful merchant","detail":"Accept Astrid's test"},
            {"id":"mercenary","label":"Kill the arrogant mercenary","detail":"Accept Astrid's test"},
            {"id":"astrid","label":"Refuse and attack Astrid","detail":"Challenge the Brotherhood"}]
        if stage == "paarthurnax": return [
            {"id":"kill_paarthurnax","label":"Kill Paarthurnax","detail":"Satisfy the Blades"},
            {"id":"spare_paarthurnax","label":"Spare Paarthurnax","detail":"Remain loyal to the Greybeards"}]
        if stage == "combat":
            e = self.s["enemy"]
            opts = [
                {"id":"attack","label":"Strike with weapon","detail":"Physical attack"},
                {"id":"magic","label":"Cast a spell","detail":"Costs 15 magicka"},
                {"id":"shout","label":"Use Fus Ro Dah","detail":"40 damage; requires the shout"},
                {"id":"potion","label":"Drink healing potion","detail":"Restore 50 health"}]
            if self.s.get("retreat_to"):
                opts.append({"id":"run","label":"Attempt to flee","detail":"May fail"})
            return opts
        if stage in ("ending","game_over"): return [{"id":"restart","label":"Begin a new adventure","detail":"Create another Dragonborn"}]
        return []

    def act(self, action):
        self.lines = []
        s = self.s
        stage = s["stage"]
        if action == "restart":
            self.__init__()
            self.say("A new saga begins. The cart rolls toward Helgen.")
            return self.result()
        if action == "stats":
            skills = s.get("skills", {})
            skill_line = " · ".join(f"{k} {v}" for k, v in skills.items())
            perks = s.get("perks", [])
            self.say(f"{s['name']} the {s['race']} {s['character_class']} — Level {s['level']}",
                     f"Health {s['hp']}/{s['max_hp']} · Magicka {s['mana']}/{s['max_mana']}",
                     f"Attack {s['attack']} · Spell {s['spell']} · Defense {s['defense']} · Gold {s['gold']} Septims",
                     f"Skills: {skill_line}",
                     f"Perk points: {s.get('perk_points', 0)} · Perks: {', '.join(perks) if perks else 'None'}",
                     "Inventory: " + (", ".join(s["inventory"]) if s["inventory"] else "Empty"),
                     "Spells: " + (", ".join(s["spells"]) if s["spells"] else "None"),
                     "Shouts: " + (", ".join(s["shouts"]) if s["shouts"] else "None"))
            return self.result()
        if action == "perks":
            if s.get("perk_points", 0) <= 0:
                self.say("You have no perk points to spend.")
                return self.result()
            s["perk_return"] = stage  # remember where to go back
            s["stage"] = "perk_menu"
            self.say("Choose a perk to unlock. Requirements must be met.")
            return self.result()

        # Enforce the rules in the engine, not just the UI: only actions currently on
        # offer are accepted (blocks stale/crafted calls such as repeating a finished quest).
        if action not in {o["id"] for o in self.options()}:
            self.say("That action is not available.")
            return self.result()

        if stage == "helgen_choice":
            if action == "ralof":
                s["stormcloaks"], s["imperials"] = True, False
                self.say("Ralof cuts your bindings. An Imperial soldier bursts into the tower!")
                self._combat("Imperial Soldier", 40, 8, 3, 15, 25, "bear_choice", retreat="helgen_choice")
            elif action == "hadvar":
                s["imperials"], s["stormcloaks"] = True, False
                self.say("Hadvar pulls you behind his shield. A Stormcloak rebel attacks!")
                self._combat("Stormcloak Rebel", 40, 10, 2, 12, 25, "bear_choice", retreat="helgen_choice")
        elif stage == "bear_choice":
            if action == "bear":
                self.say("You ready your weapon and charge the sleeping beast!")
                self._combat("Cave Bear", 65, 14, 4, 10, 40, "riverwood", retreat="bear_choice")
            else:
                self.say("You hold your breath and slip past the sleeping bear.")
                self.improve_skill("Sneak", 2)
                self._advance("riverwood")
                self._xp(50)
        elif stage == "riverwood":
            if action == "shop":
                self.say("Alvor wipes soot from his hands. “Need some steel? Or perhaps armor?”")
                self._advance("shop")
            elif action == "trader":
                if s["dragonstone"]:
                    self.say("Lucan thanks you again. The Golden Claw's mystery is solved.")
                else:
                    self.say("Lucan explains that thieves took his antique Golden Claw to Bleak Falls Barrow.")
                    self._advance("trader")
            elif action == "open_travel":
                s["travel_return"] = "riverwood"
                self._advance("travel")
            elif action == "travel":
                # Legacy single-destination action (older saves / tests)
                self.say("You pack your gear and follow the road toward Whiterun.")
                self._advance("whiterun")
        elif stage == "travel":
            self._handle_travel(action)
            return self.result()
        elif stage == "shop":
            if action == "blade":
                if s["gold"] >= 50:
                    s["gold"] -= 50; s["attack"] += 10; s["inventory"].append("Steel Blade")
                    self.say("You purchase a Steel Blade. Attack increased.")
                    self.improve_skill("Speech")
                else: self.say("You don't have enough Septims.")
            elif action == "armor":
                if s["gold"] >= 40:
                    s["gold"] -= 40; s["defense"] += 5; s["inventory"].append("Iron Armor")
                    self.say("You purchase Iron Armor. Defense increased.")
                    self.improve_skill("Speech")
                else: self.say("You don't have enough Septims.")
            elif action == "sell":
                # The player must actually own the item being sold. Every character
                # starts with one Sweetroll, so this is a one-time, testable sale.
                if "Sweetroll" in s["inventory"]:
                    s["inventory"].remove("Sweetroll")
                    s["gold"] += 5
                    self.say("You sell your Sweetroll for 5 Septims.")
                    self.improve_skill("Speech")
                else:
                    self.say("You have nothing to sell.")
            elif action == "back":
                self._advance("riverwood")
        elif stage == "perk_menu":
            owned = s.setdefault("perks", [])
            skills = s.get("skills", {})
            if action == "perk_armsman" and "Armsman" not in owned and skills.get("One-Handed", 0) >= 20 and s.get("perk_points", 0) > 0:
                owned.append("Armsman")
                s["perk_points"] -= 1
                self.say("You unlock Armsman. Your weapon strikes hit harder (+5 damage).")
            elif action == "perk_pyromancer" and "Pyromancer" not in owned and skills.get("Destruction", 0) >= 20 and s.get("perk_points", 0) > 0:
                owned.append("Pyromancer")
                s["perk_points"] -= 1
                self.say("You unlock Pyromancer. Your destructive spells burn hotter (+10 damage).")
            elif action == "perk_shadowfoot" and "Shadowfoot" not in owned and skills.get("Sneak", 0) >= 20 and s.get("perk_points", 0) > 0:
                owned.append("Shadowfoot")
                s["perk_points"] -= 1
                self.say("You unlock Shadowfoot. You are harder to pin down when fleeing (+20% escape chance).")
            elif action == "perk_none":
                self.say("Raise your skills to 20 to unlock new perks.")
            elif action == "perk_back":
                pass
            else:
                self.say("That perk is not available.")
                return self.result()
            # Return to previous stage
            back = s.pop("perk_return", "riverwood")
            s["stage"] = back
            return self.result()
        elif stage == "trader":
            if action == "barrow":
                self.say("You accept Lucan's request and climb the frozen steps to Bleak Falls Barrow.")
                s["quests"]["Golden Claw"] = "In progress"
                self._advance("barrow_intro")
            else:
                self.say("You leave the trader and return to Riverwood.")
                self._advance("riverwood")
        elif stage == "barrow_intro" and action == "enter_barrow":
            self.say("The ruin smells of dust and decay. A giant Frostbite Spider drops from the ceiling!")
            self._combat("Giant Frostbite Spider", 65, 14, 5, 20, 45, "barrow_complete", retreat="barrow_intro")
        elif stage == "barrow_complete":
            pass
        elif stage == "branching":
            if action == "main":
                self.say("You climb the seven thousand steps to High Hrothgar. The Greybeards reveal the path to Sovngarde.")
                self._advance("paarthurnax")
            elif action == "college":
                self.say("At the College of Winterhold, the Eye of Magnus pulses with dangerous power. Ancano's magic must be stopped.")
                s["quests"]["College of Winterhold"] = "In progress"
                self._set_location("College of Winterhold")
                self._combat("Magical Anomaly", 80, 18, 12, 50, 80, "after_college", retreat="branching")
            elif action == "brotherhood":
                self.say("You wake in an abandoned shack. Astrid watches from the shadows.",
                         "“Kill one of these captives, and you may join the family.”")
                s["quests"]["Dark Brotherhood"] = "In progress"
                self._set_location("Dark Brotherhood Sanctuary")
                self._advance("brotherhood_choice")
            elif action == "open_travel":
                s["travel_return"] = "branching"
                self._advance("travel")
        elif stage == "brotherhood_choice":
            if action in ("merchant", "mercenary"):
                victim = "fearful merchant" if action == "merchant" else "arrogant mercenary"
                self.say(f"You choose the {victim}. Astrid smiles: “Welcome to the family. We speak in whispers.”")
                s["inventory"].append("Shrouded Hood (+15% Spell Damage)")
                s["gold"] += 150; s["void_champion"] = True
                self._xp(100); self._advance("after_brotherhood")
            elif action == "astrid":
                self.say("You refuse the contract and draw your weapon against Astrid!")
                self._combat("Astrid", 100, 20, 8, 150, 100, "after_brotherhood", retreat="brotherhood_choice")
                s["void_champion"] = False
        elif stage == "paarthurnax":
            if action == "kill_paarthurnax":
                s["paarthurnax_killed"] = True
                self.say("You draw your blade and slay Paarthurnax upon the mountain peak.")
                self._xp(150)
            else:
                self.say("You refuse to betray Paarthurnax. The Greybeards remain your guides.")
                self._xp(100)
            self._advance("sovngarde")
        elif stage == "combat":
            e = s["enemy"]
            perks = set(s.get("perks", []))
            if action == "attack":
                bonus = 5 if "Armsman" in perks else 0
                dmg = max(5, s["attack"] + bonus + random.randint(-3, 5) - e["defense"])
                e["hp"] -= dmg
                self.say(f"You strike {e['name']} for {dmg} damage.")
                self.improve_skill("One-Handed")
            elif action == "magic":
                if s["mana"] < 15:
                    self.say("Not enough magicka. Choose another action.")
                    return self.result()
                s["mana"] -= 15
                bonus = 10 if "Pyromancer" in perks else 0
                dmg = max(8, s["spell"] + bonus + random.randint(2, 8))
                e["hp"] -= dmg
                self.say(f"Your spell hits {e['name']} for {dmg} damage.")
                self.improve_skill("Destruction")
            elif action == "shout":
                if "Fus Ro Dah" not in s["shouts"]:
                    self.say("You have not unlocked Fus Ro Dah yet.")
                    return self.result()
                e["hp"] -= 40
                self.say("FUS RO DAH! The Voice strikes for 40 damage.")
            elif action == "potion":
                if "Healing Potion" not in s["inventory"]:
                    self.say("You have no Healing Potions.")
                    return self.result()
                if s["hp"] >= s["max_hp"]:
                    self.say("You are already at full health.")
                    return self.result()
                s["inventory"].remove("Healing Potion")
                healed = min(50, s["max_hp"] - s["hp"])
                s["hp"] += healed
                self.say(f"You drink a Healing Potion and restore {healed} health.")
            elif action == "run":
                if not s.get("retreat_to"):
                    self.say("There is no escape from this fight!")
                    return self.result()
                # Original base success is 60% (random > 0.4). Shadowfoot adds 20%.
                fail_threshold = 0.4 - (0.2 if "Shadowfoot" in perks else 0)
                if random.random() > fail_threshold:
                    self.say("You escape the battle and retreat.")
                    self.improve_skill("Sneak", 2)
                    retreat_stage = s["retreat_to"]
                    # Clear the encounter before changing scenes so a retreat
                    # cannot leave a defeated/escaped enemy in the saved state.
                    s["enemy"] = None
                    s["after_combat"] = None
                    s["retreat_to"] = None
                    self._advance(retreat_stage)
                    return self.result()
                self.say("Your escape fails. The enemy blocks your retreat.")
            else:
                self.say("That action is not available.")
                return self.result()
            if e["hp"] <= 0:
                self._win_combat()
                return self.result()
            enemy_dmg = max(2, e["attack"] + random.randint(-2, 3) - s["defense"])
            s["hp"] -= enemy_dmg
            self.say(f"{e['name']} strikes back for {enemy_dmg} damage.")
            if s["hp"] <= 0:
                s["hp"] = 0
                s["enemy"] = None
                s["after_combat"] = None
                s["retreat_to"] = None
                self._advance("game_over")
        return self.result()
