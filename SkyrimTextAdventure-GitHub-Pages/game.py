"""Browser-ready, turn-based adaptation of Skyrim: The Chronicles of the Dragonborn.
The game rules and state live in Python; the browser supplies choices through act().
"""
import json
import random

class Game:
    def __init__(self, saved=None):
        self.s = saved if saved else {
            "started": False, "stage": "intro", "name": "Dragonborn",
            "race": "Nord", "character_class": "Warrior",
            "level": 1, "xp": 0, "xp_needed": 100,
            "hp": 100, "max_hp": 100, "mana": 50, "max_mana": 50,
            "attack": 15, "spell": 10, "defense": 5, "gold": 50,
            "inventory": ["Sweetroll", "Healing Potion"], "spells": ["Flames"],
            "shouts": [], "companion": None, "location": "Helgen",
            "stormcloaks": False, "imperials": False, "dragonstone": False,
            "paarthurnax_killed": False, "archmage": False, "void_champion": False,
            "enemy": None, "after_combat": None, "log": [],
            "quests": {"Golden Claw": "Not started", "College of Winterhold": "Not started",
                       "Dark Brotherhood": "Not started", "Main Quest": "In progress"}
        }
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
            "location": s["location"], "quests": s["quests"],
            "enemy": s["enemy"], "game_over": s["stage"] == "game_over",
            "won": s["stage"] == "ending"
        }

    def export_state(self):
        return json.dumps(self.s)

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
            self.say(f"LEVEL UP! You are now level {self.s['level']}. Your health, mana, and combat power increase.")

    def _combat(self, name, hp, attack, defense, gold, xp, after):
        self.s["enemy"] = {"name": name, "hp": hp, "max_hp": hp, "attack": attack,
                           "defense": defense, "gold": gold, "xp": xp}
        self.s["after_combat"] = after
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
        self._advance(next_stage)

    def _advance(self, stage):
        s = self.s
        s["stage"] = stage
        if stage == "bear_choice":
            s["location"] = "Helgen Keep"
            self.say("You descend into the tunnels beneath Helgen. A sleeping cave bear guards the exit.")
        elif stage == "riverwood":
            s["location"] = "Riverwood"
            self.say("You emerge beneath the cold sky. The road leads to Riverwood, a quiet logging village.",
                     "Locals whisper of dragon sightings and urge you to seek the Jarl of Whiterun.")
        elif stage == "whiterun":
            s["location"] = "Whiterun"
            self.say("You pass beneath the gates of Whiterun and climb to Dragonsreach.")
            if s["dragonstone"]:
                self.say("Farengar studies the Dragonstone and rewards you with 100 Septims.")
                s["gold"] += 100
                self.say("A guard bursts in: a dragon has been sighted at the Western Watchtower!")
                self._combat("Mirmulnir — Dragon", 150, 25, 10, 200, 150, "after_dragon")
            else:
                self.say("Farengar needs the Dragonstone from Bleak Falls Barrow before he can help.")
                self._advance("barrow_intro")
        elif stage == "after_dragon":
            self.say("The dragon's energy flows into your chest. The guards stare in disbelief: Dragonborn!")
            if "Fus Ro Dah" not in s["shouts"]:
                s["shouts"].append("Fus Ro Dah")
            s["companion"] = "Lydia"
            self.say("You learn the shout Fus Ro Dah. Jarl Balgruuf names you Thane and assigns Lydia as your housecarl.")
            self._xp(150)
            self._advance("branching")
        elif stage == "branching":
            s["location"] = "Skyrim"
            self.say("The Greybeards summon you to High Hrothgar, but powerful guilds have noticed your deeds.")
        elif stage == "after_college":
            s["archmage"] = True
            s["quests"]["College of Winterhold"] = "Completed"
            s["spells"].append("Blizzard")
            self.say("The mages elect you Archmage of Winterhold. You learn Blizzard.")
            self._xp(120)
            self._advance("branching")
        elif stage == "after_brotherhood":
            s["quests"]["Dark Brotherhood"] = "Completed"
            self._advance("branching")
        elif stage == "paarthurnax":
            self.say("At the summit of the Throat of the World, Paarthurnax reveals the path to Sovngarde.",
                     "Delphine demands that you kill the ancient dragon. The choice is yours.")
        elif stage == "sovngarde":
            s["location"] = "Sovngarde"
            self.say("You pass through the portal into the glowing skies of Sovngarde.",
                     "Alduin, the World-Eater, descends upon the heroes of old!")
            self._combat("Alduin — World-Eater", 250, 35, 20, 500, 300, "ending")
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
        elif character_class == "Mage":
            s["spells"].append("Spark"); s["inventory"].append("Staff of Sparks")
        else:
            s["inventory"].append("Steel Dagger"); s["gold"] += 50
        return self.result()

    def result(self):
        opts = self.options()
        return {"lines": self.lines, "state": self.state(), "options": opts}

    def options(self):
        stage = self.s["stage"]
        if stage == "intro": return []
        if stage == "helgen_choice": return [
            {"id":"ralof","label":"Follow Ralof into the tower","detail":"Stand with the Stormcloaks"},
            {"id":"hadvar","label":"Follow Hadvar into the keep","detail":"Stand with the Imperials"}]
        if stage == "bear_choice": return [
            {"id":"sneak","label":"Creep past the sleeping bear","detail":"Avoid a dangerous fight"},
            {"id":"bear","label":"Ambush the cave bear","detail":"Risk combat for experience"}]
        if stage == "riverwood": return [
            {"id":"shop","label":"Visit Alvor's blacksmith","detail":"Buy equipment or sell trinkets"},
            {"id":"trader","label":"Speak with Lucan Valerius","detail":"The Golden Claw quest"},
            {"id":"travel","label":"Travel to Whiterun","detail":"Continue the main story"},
            {"id":"stats","label":"Review character status","detail":"Inspect your character"}]
        if stage == "shop": return [
            {"id":"blade","label":"Buy Steel Blade — 50 gold","detail":"+10 attack"},
            {"id":"armor","label":"Buy Iron Armor — 40 gold","detail":"+5 defense"},
            {"id":"sell","label":"Sell old trinkets","detail":"+15 gold"},
            {"id":"back","label":"Return to Riverwood","detail":""}]
        if stage == "trader": return [
            {"id":"barrow","label":"Retrieve the Golden Claw","detail":"Explore Bleak Falls Barrow"},
            {"id":"decline","label":"Decline the offer","detail":"Return to the village"}]
        if stage == "barrow_intro": return [{"id":"enter_barrow","label":"Enter Bleak Falls Barrow","detail":"Face the ancient ruin"}]
        if stage == "branching": return [
            {"id":"main","label":"Path of the Dragonborn","detail":"High Hrothgar and Alduin"},
            {"id":"college","label":"Join the College of Winterhold","detail":"The Eye of Magnus"},
            {"id":"brotherhood","label":"Join the Dark Brotherhood","detail":"A contract in an abandoned shack"},
            {"id":"stats","label":"Review character status","detail":"Inspect your character"}]
        if stage == "brotherhood_choice": return [
            {"id":"merchant","label":"Kill the fearful merchant","detail":"Accept Astrid's test"},
            {"id":"mercenary","label":"Kill the arrogant mercenary","detail":"Accept Astrid's test"},
            {"id":"astrid","label":"Refuse and attack Astrid","detail":"Challenge the Brotherhood"}]
        if stage == "paarthurnax": return [
            {"id":"kill_paarthurnax","label":"Kill Paarthurnax","detail":"Satisfy the Blades"},
            {"id":"spare_paarthurnax","label":"Spare Paarthurnax","detail":"Remain loyal to the Greybeards"}]
        if stage == "combat":
            e = self.s["enemy"]
            return [
                {"id":"attack","label":"Strike with weapon","detail":"Physical attack"},
                {"id":"magic","label":"Cast a spell","detail":"Costs 15 magicka"},
                {"id":"shout","label":"Use Fus Ro Dah","detail":"40 damage; requires the shout"},
                {"id":"potion","label":"Drink healing potion","detail":"Restore 50 health"},
                {"id":"run","label":"Attempt to flee","detail":"May fail"}]
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
            self.say(f"{s['name']} the {s['race']} {s['character_class']} — Level {s['level']}",
                     f"Health {s['hp']}/{s['max_hp']} · Magicka {s['mana']}/{s['max_mana']}",
                     f"Attack {s['attack']} · Spell {s['spell']} · Defense {s['defense']} · Gold {s['gold']} Septims",
                     "Inventory: " + (", ".join(s["inventory"]) if s["inventory"] else "Empty"),
                     "Spells: " + (", ".join(s["spells"]) if s["spells"] else "None"),
                     "Shouts: " + (", ".join(s["shouts"]) if s["shouts"] else "None"))
            return self.result()

        if stage == "helgen_choice":
            if action == "ralof":
                s["stormcloaks"] = True
                self.say("Ralof cuts your bindings. An Imperial soldier bursts into the tower!")
                self._combat("Imperial Soldier", 40, 8, 3, 15, 25, "bear_choice")
            elif action == "hadvar":
                s["imperials"] = True
                self.say("Hadvar pulls you behind his shield. A Stormcloak rebel attacks!")
                self._combat("Stormcloak Rebel", 40, 10, 2, 12, 25, "bear_choice")
        elif stage == "bear_choice":
            if action == "bear":
                self.say("You ready your weapon and charge the sleeping beast!")
                self._combat("Cave Bear", 65, 14, 4, 10, 40, "riverwood")
            else:
                self.say("You hold your breath and slip past the sleeping bear.")
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
            elif action == "travel":
                self.say("You pack your gear and follow the road toward Whiterun.")
                self._advance("whiterun")
        elif stage == "shop":
            if action == "blade":
                if s["gold"] >= 50:
                    s["gold"] -= 50; s["attack"] += 10; s["inventory"].append("Steel Blade")
                    self.say("You purchase a Steel Blade. Attack increased.")
                else: self.say("You don't have enough Septims.")
            elif action == "armor":
                if s["gold"] >= 40:
                    s["gold"] -= 40; s["defense"] += 5; s["inventory"].append("Iron Armor")
                    self.say("You purchase Iron Armor. Defense increased.")
                else: self.say("You don't have enough Septims.")
            elif action == "sell":
                s["gold"] += 15; self.say("You sell a bundle of old trinkets for 15 Septims.")
            elif action == "back":
                self._advance("riverwood")
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
            self._combat("Giant Frostbite Spider", 65, 14, 5, 20, 45, "barrow_complete")
        elif stage == "barrow_complete":
            pass
        elif stage == "branching":
            if action == "main":
                self.say("You climb the seven thousand steps to High Hrothgar. The Greybeards reveal the path to Sovngarde.")
                self._advance("paarthurnax")
            elif action == "college":
                self.say("At the College of Winterhold, the Eye of Magnus pulses with dangerous power. Ancano's magic must be stopped.")
                s["quests"]["College of Winterhold"] = "In progress"
                self._combat("Magical Anomaly", 80, 18, 12, 50, 80, "after_college")
            elif action == "brotherhood":
                self.say("You wake in an abandoned shack. Astrid watches from the shadows.",
                         "“Kill one of these captives, and you may join the family.”")
                s["quests"]["Dark Brotherhood"] = "In progress"
                self._advance("brotherhood_choice")
        elif stage == "brotherhood_choice":
            if action in ("merchant", "mercenary"):
                victim = "fearful merchant" if action == "merchant" else "arrogant mercenary"
                self.say(f"You choose the {victim}. Astrid smiles: “Welcome to the family. We speak in whispers.”")
                s["inventory"].append("Shrouded Hood (+15% Spell Damage)")
                s["gold"] += 150; s["void_champion"] = True
                self._xp(100); self._advance("after_brotherhood")
            elif action == "astrid":
                self.say("You refuse the contract and draw your weapon against Astrid!")
                self._combat("Astrid", 100, 20, 8, 150, 100, "after_brotherhood")
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
            if action == "attack":
                dmg = max(5, s["attack"] + random.randint(-3, 5) - e["defense"])
                e["hp"] -= dmg
                self.say(f"You strike {e['name']} for {dmg} damage.")
            elif action == "magic":
                if s["mana"] < 15:
                    self.say("Not enough magicka. Choose another action.")
                    return self.result()
                s["mana"] -= 15
                dmg = max(8, s["spell"] + random.randint(2, 8))
                e["hp"] -= dmg
                self.say(f"Your spell hits {e['name']} for {dmg} damage.")
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
                s["inventory"].remove("Healing Potion")
                healed = min(50, s["max_hp"] - s["hp"])
                s["hp"] += healed
                self.say(f"You drink a Healing Potion and restore {healed} health.")
            elif action == "run":
                if random.random() > .4:
                    self.say("You escape the battle and retreat.")
                    self._advance(s["after_combat"])
                    return self.result()
                self.say("Your escape fails. The enemy blocks your retreat.")
            if e["hp"] <= 0:
                self._win_combat()
                return self.result()
            enemy_dmg = max(2, e["attack"] + random.randint(-2, 3) - s["defense"])
            s["hp"] -= enemy_dmg
            self.say(f"{e['name']} strikes back for {enemy_dmg} damage.")
            if s["hp"] <= 0:
                s["hp"] = 0
                s["stage"] = "game_over"
                self._advance("game_over")
        return self.result()

# Complete the post-barrow transition when a fight is won.
_original_advance = Game._advance
def _advance_with_barrow(self, stage):
    if stage == "barrow_complete":
        self.s["dragonstone"] = True
        self.s["inventory"].extend(["Golden Claw", "Dragonstone"])
        self.s["quests"]["Golden Claw"] = "Completed"
        self.say("You cut Arvel free, recover the Golden Claw and discover the Dragonstone tablet.",
                 "Bleak Falls Barrow is complete. The Jarl of Whiterun needs this discovery.")
        self._xp(80)
        _original_advance(self, "riverwood")
    else:
        _original_advance(self, stage)
Game._advance = _advance_with_barrow
