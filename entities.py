import dndice
import math, random
from enum import Enum, IntEnum

class advantage_type(Enum):
    OFFENSE = 0
    DEFENSE = 1
    DIS_OFFENSE = 2
    DIS_DEFENSE = 3

class entity_type(Enum):
    PLAYER = 0 
    SIDEKICK = 1
    MONSTER = 2

class death_save(IntEnum):
    FAILURE = 0
    SUCCESS = 1

class entity_stats:
    def __init__(self, strength, dexterity, constitution, intelligence, wisdom, charisma):
        self.raw_stats = {
            "strength": strength,
            "dexterity": dexterity,
            "constitution": constitution,
            "intelligence": intelligence,
            "wisdom": wisdom,
            "charisma": charisma
        }

        self.stat_modifiers = {}
        for stat, value in self.raw_stats.items():
            self.stat_modifiers[stat[:3].upper()] = (value-10)//2
        

class Entity:
    def __init__(self, name, stats: entity_stats, hp, ac, hit_modifier, damage_die, damage_dice_amount=1, damage_modifier=0):
        self.name = name
        self.stats = stats
        self.max_hp = hp
        self.current_hp = hp
        self.ac = ac
        self.hit_modifier = hit_modifier
        self.damage_die = damage_die
        self.damage_dice_amount = damage_dice_amount
        self.damage_modifier = damage_modifier

        # only dealing with level 2 entities for now
        self.proficiency_bonus = 2
        self.death_saving_counters = [0,0]
        self.advantage_defense = False
        self.advantage_offense = False
        self.unconcious = False
        self.stable = False
        self.dead = False

        self.harrying = None
        self.harried_by = None

        self.hindering = None
        self.hindered_by = None

        self.multiattack_modifiers = None

    def roll_initiative(self):
        return dndice.basic("1d20", 0, self.stats.stat_modifiers["DEX"])

    def multiattack(self, target: 'Entity'):
        attack_roll = dndice.basic("1d20", 0, self.hit_modifier)

        if attack_roll-self.hit_modifier == 20:
            # rolling a nat 20 is an automatic hit, and the damage dice are doubled
            damage = max(dndice.basic(self.multiattack_modifiers[0],dndice.Mode.CRIT,self.multiattack_modifiers[1]),0)
            result = "%s's multiattack critically hits %s for %d damage!" %(self, target, damage)
            target.last_struck_by = self
        elif attack_roll >= target.ac:
            # attacks land if they are greather than or equal to the target's armour class
            damage = max(dndice.basic(self.multiattack_modifiers[0],0,self.multiattack_modifiers[1]),0)
            result = "%s's multiattack strikes %s for %d damage" %(self, target, damage)
            target.last_struck_by = self
        else:
            damage = 0
            result = "%s's multiattack misses" %(self)
        print(result)
        return damage

    def attack(self, target: 'Entity'):
        attack_roll_str = "1d20"
        
        if self.advantage_offense == advantage_type.OFFENSE and target.advantage_defense != advantage_type.DEFENSE\
            or self.advantage_offense != advantage_type.DIS_OFFENSE and target.advantage_defense == advantage_type.DIS_DEFENSE:
            # roll two d20, keep highest 1
            attack_roll_str = "2d20h1"
            
        elif target.advantage_defense == advantage_type.DEFENSE:
            attack_roll_str = "2d20l1"

        # advantages/disadvantages are used after an attempted attack
        self.advantage_offense = None
        target.advantage_defense = None

        attack_roll = dndice.basic(attack_roll_str, 0, self.hit_modifier)

        if attack_roll-self.hit_modifier == 20:
            # rolling a nat 20 is an automatic hit, and the damage dice are doubled
            damage = max(dndice.basic(str(self.damage_dice_amount)+"dc"+str(self.damage_die),0,self.damage_modifier),0)
            result = "A critical hit! %s takes %d damage from %s's attack" %(target, damage, self)
            target.last_struck_by = self
        elif attack_roll >= target.ac:
            # attacks land if they are greather than or equal to the target's armour class
            damage = max(dndice.basic(str(self.damage_dice_amount)+"d"+str(self.damage_die), 0, self.damage_modifier),0)
            result = "%s takes %d damage from %s's attack" %(target, damage, self)
            target.last_struck_by = self
        else:
            damage = 0
            result = "%s's attack misses" %(self)

        print(result)

        if self.multiattack_modifiers != None and not target.dead:
            damage += self.multiattack(target)

        damage_dealt = min(damage, target.current_hp)

        target.take_damage(damage)

        return damage_dealt

    def take_damage(self, damage):       
        if self.current_hp - damage <= -(self.max_hp):  # If the entity has taken massive damage, they die outright
            self.current_hp = 0
            self.dead = True
            self.unconcious = False
            print("A massive strike has taken %s's life." %self)
        elif self.current_hp <= 0:
            # even if damage is 0, attacks automatically hit unconcious targets
            self.death_saving_counters[death_save.FAILURE]+=1
            self.stable = False
            self.resolve_death_counters()
        elif self.current_hp <= damage: # if the entity falls below 0 HP, they fall unconcious
            self.current_hp = 0
            self.unconcious = True
            self.stable = False
            print("With a thump, %s falls to the ground, unconcious." %self)
        else:
            self.current_hp -= damage

    def get_advantage(self, type: advantage_type):
        if type is advantage_type.OFFENSE or advantage_type.DIS_OFFENSE:
            self.advantage_offense = type
        elif type is advantage_type.DEFENSE or advantage_type.DIS_DEFENSE:
            self. advantage_defense = type

    def harry(self, target: 'Entity'):
        print("%s harries %s, making attacks against them more likely to land" %(self, target))
        target.get_advantage(advantage_type.DIS_DEFENSE)
        target.harried_by = self
        self.harrying = target
    
    def hinder(self, target: 'Entity'):
        print("%s hinders %s's efforts, making their attacks less likely to hit" %(self, target))
        target.get_advantage(advantage_type.DIS_OFFENSE)
        target.hindered_by = self
        self.hindering = target

    def dodge(self):
        print("%s takes evasive action, becoming more difficult to hit." %self)
        self.get_advantage(advantage_type.DEFENSE)

    def resolve_death_counters(self):
        if self.death_saving_counters[death_save.FAILURE] > 2:
            self.dead = True
            self.unconcious = False
            self.stable = False
            print("Alas, %s has died in battle." %self)
        elif self.death_saving_counters[death_save.SUCCESS] > 2:
            self.unconcious = True
            self.stable = True
            self.death_saving_counters = [0,0]

    def death_save_roll(self):
        if not self.stable:
            roll = dndice.basic("1d20")
            if roll == 1:
                self.death_saving_counters[death_save.FAILURE] = 3
            elif roll == 20:
                self.death_saving_counters = [0,0]
                self.unconcious = False
                self.current_hp = 1
                print("With a gasp, %s rises to fight again!" %self)
            elif roll < 10:
                self.death_saving_counters[death_save.FAILURE]+=1
            else:
                self.death_saving_counters[death_save.SUCCESS]+=1
            
            if self.current_hp < 1:
                self.resolve_death_counters()

    def turn_start(self):
        if self.harrying != None and self.harrying.harried_by == self:
            self.harrying.advantage_offense = False
            self.harrying = None
        self.advantage_defense = False

    def __str__(self):
        return self.name.upper()
    
    def __repr__(self):
        return "%-15s <HP:%d/%d | AC: %d | to hit: %d | dmg: %dd%d+%d>" %(self, self.current_hp, self.max_hp, 
        self.ac, self.hit_modifier, self.damage_dice_amount, self.damage_die, self.damage_modifier)

class Player(Entity):
    def __init__(self, player_class):
        player = players[player_class]
        super().__init__(player_class, player["stats"], player["hp"], player["ac"], player["hit"], player["dmg_die"])
        self.pc_class = player_class
        self.hit_die = player["hp"]

        self.calculate_attack_modifiers()
        self.resolve_hp()

        if player_class == "rogue":
            self.multiattack_modifiers = ("1d"+str(player["dmg_die"]),0,0)

    def calculate_attack_modifiers(self):
            # proficiency bonus + either STR or DEX modifier (assuming all weapons are versatile)
            self.hit_modifier = self.proficiency_bonus + max(self.stats.stat_modifiers["STR"], self.stats.stat_modifiers["DEX"])
            self.damage_modifier = max(self.stats.stat_modifiers["STR"], self.stats.stat_modifiers["DEX"])
    
    def resolve_hp(self):
        # at level 1, player receives (or loses) CON max_hp
        self.max_hp += self.stats.stat_modifiers["CON"]

        # reroll ones
        # can't lose hp on level up (would only matter on modifiers less than -2)
        self.max_hp += max(0, self.stats.stat_modifiers["CON"] + dndice.basic("1d"+str(self.hit_die)+"R1"))

        self.current_hp = 0 + self.max_hp

    def __str__(self):
        return "(PC)"+self.name.title()

def resolve_CR(monster_type):
    for cr in monsters:
        if monster_type in monsters[cr]:
            return cr

class Monster(Entity):
    def __init__(self, monster_type, monster, name=False):
        if not name:
            name = monster_type
        super().__init__(name, monster["stats"], monster["hp"], monster["ac"], monster["hit"],
        monster["dmg_die"], monster["dice_amount"], monster["dmg_mod"])
        self.cr = resolve_CR(monster_type)
        self.last_struck_by = None
        if "multiattack" in monster:
            self.multiattack_modifiers = monster["multiattack"]

    def take_action(self, possible_targets):
        # we'll keep the assumption of at most 1 PC and 1 sidekick as targets

        # The enemy will focus on a bloodied entity, else will attack the entity that last struck them
        #   otherwise, randomly selects a target

        # We'll assume that monsters rarely try to dodge
        if random.random()<0.1:
            self.dodge()
            return 0, None

        target = None
        if len(possible_targets) == 1:
            target = possible_targets[0]
        else:
            if bloodied(possible_targets[0]) and not bloodied(possible_targets[1]):
                target = possible_targets[0]
            elif not bloodied(possible_targets[0]) and bloodied(possible_targets[1]):
                target = possible_targets[1]
            elif self.last_struck_by != None:
                target = self.last_struck_by
            else:
                if random.random() < 0.5:
                    target = possible_targets[0]
                else:
                    target = possible_targets[1]
        damage = self.attack(target)
        return damage, target

    def take_damage(self, damage):
        if self.current_hp <= damage: # if the Monster falls below 0 HP, they die
            self.current_hp = 0
            self.dead = True
            self.stable = False
            print("The wicked %s has been slain!" %self)
        else:
            self.current_hp -= damage

    def __str__(self):
        return "(M)"+self.name.title()

class Sidekick(Entity):
    def __init__(self, sidekick_type, sidekick, name=False):
        if not name:
            name = sidekick_type
        super().__init__(name, sidekick["stats"], sidekick["hp"], sidekick["ac"], sidekick["hit"],
        sidekick["dmg_die"], sidekick["dice_amount"], sidekick["dmg_mod"])

        if "multiattack" in sidekick:
            self.multiattack_modifiers = sidekick["multiattack"]

    def take_action(self, damage_dealt, player_health):
        return 0

    def __str__(self):
        return "(SK)"+self.name.title()

def bloodied(target: Entity):
    # an entity is "bloodied" if they have half HP or less
    if target.current_hp>0 and target.current_hp <= target.max_hp//2:
        return True
    return False

monsters = {
    "1/8":{
        "kobold" : {
            "stats": entity_stats(7,15,9,8,7,8),
            "hp": 5,
            "ac": 12,
            "hit": 2,
            "dmg_die": 4,
            "dice_amount": 1,
            "dmg_mod": 2
        },
        "flying snake" : {
            "stats": entity_stats(4,18,11,2,12,5),
            "hp": 5,
            "ac": 14,
            "hit": 6,
            "dmg_die": 4,
            "dice_amount": 3,
            "dmg_mod": 1
        },
        "giant rat" : {
            "stats": entity_stats(7,15,11,2,10,4),
            "hp": 7,
            "ac": 12,
            "hit": 4,
            "dmg_die": 4,
            "dice_amount": 1,
            "dmg_mod": 2
        },
        "giant weasel" : {
            "stats": entity_stats(11,16,10,4,12,5),
            "hp": 9,
            "ac": 13,
            "hit": 5,
            "dmg_die": 4,
            "dice_amount": 1,
            "dmg_mod": 3
        },
        "giant crab" : {
            "stats": entity_stats(13,15,11,1,9,3),
            "hp": 13,
            "ac": 15,
            "hit": 3,
            "dmg_die": 6,
            "dice_amount": 1,
            "dmg_mod": 1
        },
        "merfolk" : {
            "stats": entity_stats(10,13,12,11,11,12),
            "hp": 11,
            "ac": 11,
            "hit": 2,
            "dmg_die": 6,
            "dice_amount": 1,
            "dmg_mod": 0
        },
        "bandit" : {
            "stats": entity_stats(11,12,12,10,10,10),
            "hp": 11,
            "ac": 12,
            "hit": 3,
            "dmg_die": 6,
            "dice_amount": 1,
            "dmg_mod": 1
        },
        "guard" : {
            "stats": entity_stats(13,12,12,10,11,10),
            "hp": 11,
            "ac": 16,
            "hit": 3,
            "dmg_die": 8,
            "dice_amount": 1,
            "dmg_mod": 1
        },
        "cultist" : {
            "stats": entity_stats(11,12,10,10,11,10),
            "hp": 9,
            "ac": 12,
            "hit": 3,
            "dmg_die": 6,
            "dice_amount": 1,
            "dmg_mod": 1
        },
        "tribal warrior" : {
            "stats": entity_stats(13,11,12,8,11,8),
            "hp": 11,
            "ac": 12,
            "hit": 3,
            "dmg_die": 8,
            "dice_amount": 1,
            "dmg_mod": 1
        },
    },
    "1/4": {
        "acolyte" : {
            "stats": entity_stats(10,10,10,10,14,11),
            "hp": 9,
            "ac": 10,
            "hit": 2,
            "dmg_die": 4,
            "dice_amount": 1,
            "dmg_mod": 0
        },
        "axe beak" : {
            "stats": entity_stats(14,12,12,2,10,5),
            "hp": 19,
            "ac": 11,
            "hit": 4,
            "dmg_die": 8,
            "dice_amount": 1,
            "dmg_mod": 2
        },
        "goblin" : {
            "stats": entity_stats(8,14,10,10,8,8),
            "hp": 7,
            "ac": 15,
            "hit": 4,
            "dmg_die": 6,
            "dice_amount": 1,
            "dmg_mod": 2
        },
        "blink dog" : {
            "stats": entity_stats(12,17,12,10,13,11),
            "hp": 22,
            "ac": 13,
            "hit": 3,
            "dmg_die": 6,
            "dice_amount": 1,
            "dmg_mod": 1
        },
        "skeleton" : {
            "stats": entity_stats(10,14,15,6,8,5),
            "hp": 13,
            "ac": 13,
            "hit": 4,
            "dmg_die": 6,
            "dice_amount": 1,
            "dmg_mod": 2
        },
        "giant frog" : {
            "stats": entity_stats(12,13,11,2,10,3),
            "hp": 18,
            "ac": 11,
            "hit": 3,
            "dmg_die": 6,
            "dice_amount": 1,
            "dmg_mod": 1
        },
        "drow" : {
            "stats": entity_stats(10,14,10,11,11,12),
            "hp": 13,
            "ac": 15,
            "hit": 4,
            "dmg_die": 6,
            "dice_amount": 1,
            "dmg_mod": 2
        },
        "dretch" : {
            "stats": entity_stats(11,11,12,5,8,3),
            "hp": 18,
            "ac": 11,
            "hit": 2,
            "dmg_die": 4,
            "dice_amount": 2,
            "dmg_mod": 0,
            "multiattack": ("2d4",0)
        },
        "grimlock" : {
            "stats": entity_stats(16,12,12,9,8,6),
            "hp": 11,
            "ac": 11,
            "hit": 5,
            "dmg_die": 4,
            "dice_amount": 2,
            "dmg_mod": 3
        },
        "wolf" : {
            "stats": entity_stats(12,15,12,3,12,6),
            "hp": 11,
            "ac": 13,
            "hit": 4,
            "dmg_die": 4,
            "dice_amount": 2,
            "dmg_mod": 2
        },
        "giant lizard" : {
            "stats": entity_stats(15,12,13,2,10,5),
            "hp": 19,
            "ac": 12,
            "hit": 4,
            "dmg_die": 8,
            "dice_amount": 1,
            "dmg_mod": 2
        },
        "giant owl" : {
            "stats": entity_stats(13,15,12,8,13,10),
            "hp": 19,
            "ac": 12,
            "hit": 3,
            "dmg_die": 6,
            "dice_amount": 2,
            "dmg_mod": 1
        },
        "giant bat" : {
            "stats": entity_stats(15,16,11,2,12,6),
            "hp": 22,
            "ac": 13,
            "hit": 4,
            "dmg_die": 6,
            "dice_amount": 1,
            "dmg_mod": 2
        },
        "giant badger" : {
            "stats": entity_stats(13,10,15,2,12,5),
            "hp": 13,
            "ac": 10,
            "hit": 3,
            "dmg_die": 6,
            "dice_amount": 1,
            "dmg_mod": 1,
            "multiattack": ("2d4",1)
        },
        "elk" : {
            "stats": entity_stats(16,10,12,2,10,6),
            "hp": 13,
            "ac": 10,
            "hit": 4,
            "dmg_die": 4,
            "dice_amount": 2,
            "dmg_mod": 3
        },
        "flying sword" : {
            "stats": entity_stats(12,15,11,1,5,1),
            "hp": 17,
            "ac": 17,
            "hit": 3,
            "dmg_die": 8,
            "dice_amount": 1,
            "dmg_mod": 1
        },
        "panther" : {
            "stats": entity_stats(13,15,10,3,14,7),
            "hp": 13,
            "ac": 12,
            "hit": 4,
            "dmg_die": 6,
            "dice_amount": 1,
            "dmg_mod": 2
        },
        "zombie" : {
            "stats": entity_stats(13,6,16,3,6,5),
            "hp": 22,
            "ac": 8,
            "hit": 3,
            "dmg_die": 6,
            "dice_amount": 1,
            "dmg_mod": 1
        }
    },
    "1/2": {
        "ape" : {
            "stats": entity_stats(16,14,14,6,12,7),
            "hp": 19,
            "ac": 12,
            "hit": 5,
            "dmg_die": 6,
            "dice_amount": 1,
            "dmg_mod": 3,
            "multiattack": ("1d6",3)
        },
        "black bear" : {
            "stats": entity_stats(15,10,14,2,12,7),
            "hp": 19,
            "ac": 11,
            "hit": 5,
            "dmg_die": 6,
            "dice_amount": 1,
            "dmg_mod": 2,
            "multiattack": ("2d4",2)
        },
        "svirfneblin" : {
            "stats": entity_stats(15,14,14,12,10,9),
            "hp": 16,
            "ac": 15,
            "hit": 4,
            "dmg_die": 8,
            "dice_amount": 1,
            "dmg_mod": 2
        },
        "lizardfolk" : {
            "stats": entity_stats(15,10,13,7,12,7),
            "hp": 22,
            "ac": 15,
            "hit": 4,
            "dmg_die": 6,
            "dice_amount": 1,
            "dmg_mod": 2,
            "multiattack": ("1d6",2)
        },
        "orc" : {
            "stats": entity_stats(16,12,16,7,11,10),
            "hp": 15,
            "ac": 13,
            "hit": 5,
            "dmg_die": 12,
            "dice_amount": 1,
            "dmg_mod": 3
        },
        "sahuagin" : {
            "stats": entity_stats(13,11,12,12,13,9),
            "hp": 22,
            "ac": 12,
            "hit": 3,
            "dmg_die": 4,
            "dice_amount": 1,
            "dmg_mod": 1,
            "multiattack": ("1d8",1)
        },
        "satyr" : {
            "stats": entity_stats(12,16,11,12,10,14),
            "hp": 31,
            "ac": 14,
            "hit": 3,
            "dmg_die": 6,
            "dice_amount": 1,
            "dmg_mod": 3
        },
        "scout" : {
            "stats": entity_stats(11,14,12,11,13,11),
            "hp": 16,
            "ac": 13,
            "hit": 4,
            "dmg_die": 6,
            "dice_amount": 1,
            "dmg_mod": 2,
            "multiattack": ("1d6",2)
        },
        "thug" : {
            "stats": entity_stats(15,11,14,10,10,11),
            "hp": 32,
            "ac": 11,
            "hit": 4,
            "dmg_die": 6,
            "dice_amount": 1,
            "dmg_mod": 2,
            "multiattack": ("1d6",2)
        },
        "worg" : {
            "stats": entity_stats(16,13,13,7,11,8),
            "hp": 26,
            "ac": 13,
            "hit": 5,
            "dmg_die": 6,
            "dice_amount": 2,
            "dmg_mod": 3
        },
    },
}

players = {
    # we'll keep the players as very simplified entities for now
    # just with standard array stats, no race modifiers
    "fighter": {
        "stats": entity_stats(15,13,14,8,12,10),
        "hp": 10,
        # shield
        "ac": 16+2,
        "hit": 0,
        # longsword (1-hand)
        "dmg_die": 8
    },
    "rogue": {
        "stats": entity_stats(8,15,13,10,14,12),
        "hp": 8,
        "ac": 11+2,
        "hit": 0,
        # shortsword
        "dmg_die": 6,
    },
    "barbarian": {
        "stats": entity_stats(14,13,15,10,12,8),
        "hp": 12,
        "ac": 10+1+2,
        "hit": 0,
        # greataxe
        "dmg_die": 12,
    },
    "paladin": {
        "stats": entity_stats(15,8,14,10,12,13),
        "hp": 10,
        "ac": 16,
        "hit": 0,
        # battleaxe (2-hand)
        "dmg_die": 10,
    },
    "warlock": {
        "stats": entity_stats(12,8,10,14,13,15),
        "hp": 8,
        "ac": 11,
        "hit": 0,
        # mace
        "dmg_die": 6,
    },
}