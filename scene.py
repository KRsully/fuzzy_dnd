import entities
import random, sys
from enum import Enum
import fuzzy
import getopt

class position(Enum):
    NEAR = 1 
    FAR = 2

class status(Enum):
    DEAD = 0
    UNCONCIOUS = 1
    GOOD = 2

class knowledge(Enum):
    LOW = 0
    PLAYER_ONLY = 1
    ENEMY_ONLY = 2
    HIGH = 3

verbose = False

class Actor:
    def __init__(self, entity: entities.Entity):
        self.initiative = entity.roll_initiative()
        self.entity = entity
        self.position = position.NEAR
        self.status = status.GOOD
        self.damage_dealt = 0
        self.downed = False
        self.killed = False

    def __lt__(self, other):
        if self.initiative == other.initiative:
            # break initiative ties with dexterity value
            if self.entity.stats.raw_stats["dexterity"] == other.entity.stats.raw_stats["dexterity"]:
                return random.random() < 0.5
            else:
                return self.entity.stats.raw_stats["dexterity"] < other.entity.stats.raw_stats["dexterity"]
        else:
            return self.initiative < other.initiative

    def __gt__(self,other):
        if self.initiative == other.initiative:
            # break initiative ties with dexterity value
            if self.entity.stats.raw_stats["dexterity"] == other.entity.stats.raw_stats["dexterity"]:
                return random.random() < 0.5
            else:
                return self.entity.stats.raw_stats["dexterity"] > other.entity.stats.raw_stats["dexterity"]
        else:
            return self.initiative > other.initiative

    # for sorting purposes
    def get_initiative(self):
        return self.initiative

    def get_hp(self):
        return self.entity.current_hp

    def can_act(self):
        if self.status != status.GOOD:
            can_act = False
            if self.status == status.UNCONCIOUS:
                self.downed = True
                print("%s lies unconcious..." %self)
                self.entity.death_save_roll()
            else:
                print("%s's corpse is motionless..." %self)
                self.killed = True
        else:
            can_act = True
        return can_act

    def take_turn(self, scene: 'Scene'):
        self.entity.turn_start()
        if self.can_act():
            self.take_action(scene)
            

    def determine_targets(self, scene: 'Scene'):
        possible_targets = []
        if self.position == position.NEAR:
            for actor in scene.actors:
                if actor != self and actor.position == position.NEAR and actor.status != status.DEAD:
                    possible_targets.append(actor)
        return possible_targets

    def disengage(self):
        self.position = position.FAR

    def engage(self):
        if self.position == position.FAR:
            self.position = position.NEAR
    
    def attack(self, target: 'Actor'):
        self.engage()
        damage = self.entity.attack(target.entity)
        self.damage_dealt += damage

    def harry(self, target: 'Actor'):
        self.engage()
        self.entity.harry(target.entity)

    def hinder(self, target: 'Actor'):
        self.engage()
        self.entity.hinder(target.entity)

    def dodge(self):
        self.entity.dodge()

    def __str__(self):
        return str(self.entity)

    def __repr__(self):
        return repr(self.entity)

class PlayerCharacter(Actor):
    def __init__(self, entity: entities.Player):
        super().__init__(entity)

    def get_class(self):
        return self.entity.pc_class

    def get_hit_die(self):
        return self.entity.hit_die

    def take_action(self, scene: 'Scene'):
        nearby_actors = self.determine_targets(scene)
        if len(nearby_actors) == 0:
            print("No one is nearby, though the sounds of battle are close...")
        elif len(nearby_actors) == 1:
            print("%s stands nearby, ready to fight." %(nearby_actors[0]))
        else:
            print("You are engaged in combat with %s and %s." %(nearby_actors[0], nearby_actors[1]))
        
        prompt = True
        while(prompt==True):
            # yeah its bad
            prompt = False
            cmd = input("\nWhat would you like to do on your turn?(-h for help):").lower()
            if cmd == "-h" or cmd == "help":
                display_help()
                prompt = True
            elif cmd == "exit":
                sys.exit(0)
            elif cmd == "attack":
                self.attack(scene.enemy)
            elif cmd == "disengage":
                self.disengage()
            elif cmd == "dodge":
                self.dodge()
            elif cmd == "harry":
                self.harry(scene.enemy)
            elif cmd == "hinder":
                self.hinder(scene.enemy)
            elif cmd == "wait":
                print("%s patiently bides their time..." %self)
            else:
                print("Unrecognized command. Enter \"-h\" to see help.")
                prompt = True

class Sidekick(Actor):
    def __init__(self, entity: entities.Sidekick):
        super().__init__(entity)
        self.knowledge_level = None

    def take_action(self, scene: 'Scene'):
        frame = {
            "player_health": scene.player_character.get_hp(),
            "sidekick_health": self.get_hp(),
            "damage_dealt": self.damage_dealt + scene.player_character.damage_dealt
        }
        suggested_action, rule_strengths = fuzzy.suggest_action(frame)

        if verbose:
            print("%s considers their action carefully..." %self)
            for action_type, strength in rule_strengths:
                print("%s\t%.2f" %(action_type.name, strength))

        if suggested_action == fuzzy.action.AGGRESSIVE:
            self.attack(scene.enemy)
        elif suggested_action == fuzzy.action.SUPPORTIVE:
            self.harry(scene.enemy)
        elif suggested_action == fuzzy.action.DEFENSIVE:
            self.hinder(scene.enemy)
        elif suggested_action == fuzzy.action.SELF_PRESERVE:
            self.dodge()
        else:
            raise("bad action")
    


class Enemy(Actor):
    def __init__(self, entity: entities.Monster):
        super().__init__(entity)

    def get_cr(self):
        return self.entity.cr

    def take_action(self, scene: 'Scene'):
        possible_targets = self.determine_targets(scene)
        if len(possible_targets) == 0:
            self.engage(scene)
            possible_targets = self.determine_targets(scene)
        damage, target = self.entity.take_action([target.entity for target in possible_targets])
        self.damage_dealt += damage

    def engage(self, scene: 'Scene'):
        if self.position == position.FAR:
            self.position = position.NEAR
        
        # if every actor is FAR, engaging makes every actor NEAR
        others = [actor for actor in scene.actors if actor is not self]
        if all(other.position == position.FAR for other in others):
            for other in others:
                other.position = position.NEAR
    
class Scene:
    def __init__(self, player: PlayerCharacter, sidekick: Sidekick, enemy: Enemy):
        self.player_character = player
        self.sidekick = sidekick
        self.enemy = enemy

        self.actors = [self.player_character, self.sidekick, self.enemy]
        # highest initiative gets to act first
        self.actors.sort(key=Actor.get_initiative, reverse=True)

    def display_initiative(self):
        print("\nThe turn order is as follows:")
        for actor in self.actors:
            print("%-20s (IV %d)" %(actor.entity, actor.initiative))
        input("\nPress enter to begin combat!")

    def resolve_turn(self):
        for actor in self.actors:
            if actor.entity.unconcious:
                actor.status = status.UNCONCIOUS
                actor.downed = True
            elif actor.entity.dead:
                actor.status = status.DEAD
                actor.killed = True
            else:
                actor.status = status.GOOD
        print("\nCurrent state:")
        for actor in self.actors:
            print(repr(actor))
        input("\nPress enter to begin the next turn")

    def resolve_smartness(self):
        if self.sidekick.knowledge_level == knowledge.LOW:
            fuzzy.player_knowledge = "unknown"
            fuzzy.enemy_knowledge = "unknown"
        elif self.sidekick.knowledge_level == knowledge.PLAYER_ONLY:
            fuzzy.player_knowledge = self.player_character.get_hit_die()
            fuzzy.enemy_knowledge = "unknown"
        elif self.sidekick.knowledge_level == knowledge.ENEMY_ONLY:
            fuzzy.player_knowledge = "unknown"
            fuzzy.enemy_knowledge = self.enemy.get_cr()
        else:
            fuzzy.player_knowledge = self.player_character.get_hit_die()
            fuzzy.enemy_knowledge = self.enemy.get_cr()

    def run(self):

        counter = 0
        while not self.player_character.status == status.DEAD and not self.enemy.status == status.DEAD:
            self.actors[counter].take_turn(self)
            self.resolve_turn()
            counter = (counter+1)%len(self.actors)

    def display_results(self):
        print("\nThe battle draws to a close...")
        print("%-20s %10s %12s %10s %10s" %("Actor", "Status", "Damage Dealt", "Downed?", "Killed?"))
        for actor in self.actors:
            print("%-20s %10s %12s %10s %10s" %(actor, actor.status.name, actor.damage_dealt, actor.downed, actor.killed))

def display_help():
    print("All of the possible actions are:")
    print("%-12s - attack the enemy monster. Can only be done if the monster is NEAR." %"attack")
    print("%-12s- disengage from combat, and change positions to FAR. \
        A monster in the NEAR position cannot attack you unless it changes positions." %"disengage")
    print("%-12s - take evasive action, providing yourself DEFENSIVE ADVANTAGE against the next attack before your next turn." %"dodge")
    print("%-12s - disrupt the enemy's defenses, providing OFFENSIVE ADVANTAGE for the next attack against the target before your next turn." %"harry")
    print("%-12s - disrupt the enemy's attacks, providing OFFENSIVE DISADVANTAGE for the next attack the enemy makes." %"hinder")
    print("%-12s - Do nothing on this turn." %"wait")
    print("%-12s - stop the simulation." %"exit")

def __gen_random_player():
    player_class= random.choice(list(entities.players.keys()))
    return PlayerCharacter(entities.Player(player_class))

def __gen_player_by_class(player_class):
    return PlayerCharacter(entities.Player(player_class))

def __gen_enemy_by_cr(cr):
    mon_type, mon_info = random.choice(list(entities.monsters[cr].items()))
    return Enemy(entities.Monster(mon_type, mon_info))

def __gen_random_enemy():
    mon_type, mon_info = random.choice(list(entities.monsters[random.choice(list(entities.monsters.keys()))].items()))
    return Enemy(entities.Monster(mon_type, mon_info))

def __gen_enemy_by_type(monster_type):
    for cr in entities.monsters:
        if monster_type in entities.monsters[cr]:
            return Enemy(entities.Monster(monster_type,entities.monsters[cr][monster_type]))
    return None

def __gen_sidekick_by_cr(cr):
    mon_type, mon_info = random.choice(list(entities.monsters[cr].items()))
    return Sidekick(entities.Sidekick(mon_type, mon_info))

def __gen_random_sidekick():
    sk_type, sk_info = random.choice(list(entities.monsters[random.choice(list(entities.monsters.keys()))].items()))
    return Sidekick(entities.Sidekick(sk_type, sk_info))

def __gen_sidekick_by_type(monster_type):
    for cr in entities.monsters:
        if monster_type in entities.monsters[cr]:
            return Sidekick(entities.Sidekick(monster_type, entities.monsters[cr][monster_type]))
    return None

def prompt_knowledge():
    print("How knowledgeable should the sidekick be?")
    print("\t 0 for LOW - the sidekick doesn't know the player's class or the monster's CR")
    print("\t 1 for PLAYER ONLY - the sidekick knows the player's class, but doesn't know the monster's CR")
    print("\t 2 for ENEMY ONLY - the sidekick doesn't know the player's class, but knows the monster's CR")
    print("\t 3 for HIGH - the sidekick knows both the player's class and monster's CR")
    knowledge = int(input("Sidekick knowledge level:"))
    if knowledge < 0 or knowledge > 3:
        knowledge = 0
    return knowledge
    
def make_scene(player: PlayerCharacter = __gen_random_player(), sidekick = __gen_random_sidekick(), enemy = __gen_random_enemy()):
    if type(sidekick) == str:
        sidekick = __gen_sidekick_by_cr(sidekick)

    if type(enemy) == str:
        enemy = __gen_enemy_by_cr(enemy)

    sidekick.knowledge_level = knowledge(prompt_knowledge())

    return Scene(player, sidekick, enemy)


def run_scene(scene: Scene):
    scene.resolve_smartness()
    scene.display_initiative()
    scene.run()
    scene.display_results()

def main(cmdline_args):
    player_class = None
    sidekick_cr = None
    sidekick_type = None
    monster_cr = None
    monster_type = None

    try:
        options, args = getopt.getopt(cmdline_args,"p:s:S:m:M:v",["help","verbose"])
    except getopt.GetoptError:
        print('''Usage: scene.py [-p <player class>][-S <sidekick CR>][-s <sidekick type][-M <monster CR>][-m <monster type>][-v/--verbose]\n
    By default: all actors are chosen at random. Note that actor type takes precendence over actor CR.''')
        sys.exit()
    for opt, arg in options:
        if opt in ("-h","--help"):
            print('''Usage: scene.py [-pc <player class>][-sk <sidekick CR>][-m <monster CR>]\n
    By default: all actors are chosen at random. Note that actor type takes precendence over actor CR.''')
            sys.exit()
        elif opt in ("-p"):
            player_class = arg
        elif opt in ("-S"):
            sidekick_cr = arg
        elif opt in ("-s"):
            sidekick_type = arg
        elif opt in ("-M"):
            monster_cr = arg
        elif opt in ("-m"):
            monster_type = arg
        elif opt in ("-v","--verbose"):
            global verbose
            verbose = True

    if player_class != None:
        player_class = __gen_player_by_class(player_class)
    else:
        player_class = __gen_random_player()

    if sidekick_type != None:
        sidekick_type = __gen_sidekick_by_type(sidekick_type)
    elif sidekick_cr != None:
        sidekick_type = __gen_sidekick_by_cr(sidekick_cr)
    else:
        sidekick_type = __gen_random_sidekick()
    
    if monster_type != None:
        monster_type = __gen_enemy_by_type(monster_type)
    elif monster_cr != None:
        monster_type = __gen_enemy_by_cr(monster_cr)
    else:
        monster_type = __gen_random_enemy()

    run_scene(make_scene(player_class, sidekick_type, monster_type))

if __name__ == "__main__":
    main(sys.argv[1:])
