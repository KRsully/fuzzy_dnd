from enum import Enum

class action(Enum):
    AGGRESSIVE = 0
    SUPPORTIVE = 1
    DEFENSIVE = 2
    SELF_PRESERVE = 3

class rectangle_coefficients:
  def __init__(self, a, b):
    self.a = a
    self.b = b

class triangle_coefficients:
  def __init__(self, a, b, c):
    self.a = a
    self.b = b
    self.c = c

class trapezoid_coefficients:
  def __init__(self, a, b, c, d):
    self.a = a
    self.b = b
    self.c = c
    self.d = d



def trapezoid_membership(coefficients: trapezoid_coefficients, value: float):
  if (value > coefficients.d):
    return_value = 0
  elif value == coefficients.d and coefficients.d == coefficients.c:
    return_value = 1
  elif (value > coefficients.c):
    return_value = (coefficients.d - value)/(coefficients.d - coefficients.c)
  elif (value >= coefficients.b):
    return_value = 1
  elif (value > coefficients.a):
    return_value = (value - coefficients.a)/(coefficients.b - coefficients.a)
  else:
    return_value = 0

  return return_value

def triangle_membership(coefficients: triangle_coefficients, value):
  if (value > coefficients.c):
    return_value = 0
  elif (value > coefficients.b):
    return_value = (coefficients.c - value)/(coefficients.c - coefficients.b)
  elif (value == coefficients.b):
    return_value = 1
  elif (value > coefficients.a):
    return_value = (value - coefficients.a)/(coefficients.b - coefficients.a)
  else:
    return_value = 0

  return return_value

def calculate_membership_value(coefficients, value):
  membership_value = -1
  if type(coefficients) == triangle_coefficients:
    membership_value = triangle_membership(coefficients, value)
  elif type(coefficients) == trapezoid_coefficients:
    membership_value = trapezoid_membership(coefficients, value)
  return membership_value
    # error

# PC max health range = 8 to 28
# barbarian health range = 12 to 28
# fighter health range = paladin health range = 10 to 24
# warlock health range = rogue health range = 8 to 20

# enemy damage range
# CR 1/8 = 1 to 13
#          Expected Value 3.5 to 8.5
#          Median Expected Value 6
# CR 1/4 = 1 to 16
#          Expected Value 2.5 to 10.5
#          Median Expected Value 6.5
# CR 1/2 = 3 to 18
#          Expected Value 6.5 to 13
#          Median Expected Value 9.75
membership_fxns = {
  "player_health": {
    "unknown": { # don't know the hit die
      "low": trapezoid_coefficients(0, 0, 6, 10),
      "medium": trapezoid_coefficients(6, 12, 16, 20),
      "high": trapezoid_coefficients(16, 20, 28, 28)
    },
    8: { # d8 hit die - expected value of max hp is ~ 13
      "low": trapezoid_coefficients(0, 0, 6, 10),
      "medium": triangle_coefficients(8, 10, 14),
      "high": trapezoid_coefficients(12, 20, 20, 20)
    },
    10: { # d10 hit die - expected value of max hp is ~ 16
      "low": trapezoid_coefficients(0, 0, 6, 8),
      "medium": trapezoid_coefficients(7, 8, 12, 16),
      "high": trapezoid_coefficients(14, 20, 24, 24)
    },
    12: { # d12 hit die - expected value of max hp is ~ 19
      "low": trapezoid_coefficients(0, 0, 6, 10),
      "medium": trapezoid_coefficients(7, 10, 15, 19),
      "high": trapezoid_coefficients(17, 20, 28, 28)
    },
  },
  
  "sidekick_health": {
    "unknown": { # don't know the challenge rating - enemy expected damage ranges from 2.5 to 13
      "low": trapezoid_coefficients(0, 0, 8, 10),
      "medium": trapezoid_coefficients(8, 14, 19, 22),
      "high": trapezoid_coefficients(20, 24, 32, 32)
    },
    # CR 1/8 = 1 to 13
    #          Expected Value 2.5 to 8.5
    #          Median Expected Value 5.5
    "1/8": {
      "low": trapezoid_coefficients(0, 0, 6, 9),
      "medium": trapezoid_coefficients(8, 11, 14, 18),
      "high": trapezoid_coefficients(16, 20, 32, 32)
    },
    # CR 1/4 = 1 to 16
    #          Expected Value 2.5 to 10.5
    #          Median Expected Value 6.5  
    "1/4": {
      "low": trapezoid_coefficients(0, 0, 7, 9),
      "medium": trapezoid_coefficients(7, 9, 12, 16),
      "high": trapezoid_coefficients(14, 18, 32, 32)
    },
    # CR 1/2 = 3 to 18
    #          Expected Value 6.5 to 13
    #          Median Expected Value 9.75
    "1/2": {
      "low": trapezoid_coefficients(0, 0, 8, 11),
      "medium": trapezoid_coefficients(10, 13, 19, 24),
      "high": trapezoid_coefficients(22, 27, 32, 32)
    },
  },

  "damage_dealt": {
    "unknown": { # don't know the challenge rating - enemy HP ranges from 5 to 32
      "low": trapezoid_coefficients(0, 0, 6, 10),
      "medium": trapezoid_coefficients(6, 12, 16, 20),
      "high": trapezoid_coefficients(16, 20, 28, 28)
    },
    "1/8": { # enemy hp ranges from 5 to 11 (median 8)
      "low": trapezoid_coefficients(0, 0, 3, 5),
      "medium": triangle_coefficients(4, 5, 6),
      "high": trapezoid_coefficients(5, 7, 11, 11)
    },
    "1/4": { # enemy hp ranges from 7 to 22
      "low": trapezoid_coefficients(0, 0, 7, 9),
      "medium": trapezoid_coefficients(7, 9, 12, 16),
      "high": trapezoid_coefficients(14, 18, 22, 22)
    },
    "1/2": { # enemy hp ranges from 15 to 32
      "low": trapezoid_coefficients(0, 0, 6, 11),
      "medium": trapezoid_coefficients(9, 12, 20, 24),
      "high": trapezoid_coefficients(22, 25, 32, 32)
    },
  }
}

def goguen_t(x, y):
  return x * y
def goguen_s(x, y):
  return x + y - x*y

def godel_t(x,y):
  return min(x,y)
def godel_s(x,y):
  return max(x,y)

def lukasiewicz_t(x,y):
  return max(0, x+y-1)
def lukasiewicz_s(x,y):
  return min(1, x+y)

def drastic_t(x,y):
  if x == 1:
    return y
  elif y == 1:
    return x
  else:
    return 0
def drastic_s(x,y):
  if x == 0:
    return y
  elif y == 0:
    return x
  else:
    return 1
  
def calculate_memberships(frame):
  memberships = {
    "player_health": {
      "low" : 0,
      "medium": 0,
      "high":  0
    },
    "sidekick_health": {
      "low" : 0,
      "medium": 0,
      "high":  0
    },
    "damage_dealt": {
      "low" : 0,
      "medium": 0,
      "high":  0
    }
  }
  for stat in memberships:
    if stat == "player_health":
      for level in memberships[stat]:
        memberships[stat][level] = calculate_membership_value(membership_fxns[stat][player_knowledge][level],frame[stat])
    else:
      for level in memberships[stat]:
        memberships[stat][level] = calculate_membership_value(membership_fxns[stat][enemy_knowledge][level],frame[stat])
  return memberships

# Goals:  1. PC does not die
#         2. PC does not get downed
#         3. PC causes the enemy to reach 0 HP
#         4. Sidekick does not reach 0 HP
#         5. Sidekick's damage contribution is not significantly higher than the PC's
def apply_rules(memberships):
  damage_dealt = memberships["damage_dealt"]
  player_health = memberships["player_health"]
  sidekick_health = memberships["sidekick_health"]

  rule_strengths = {
    # IF (damage is NOT high AND sidekick health is NOT low) OR (player health is low AND sidekick health is low) THEN aggressive
    action.AGGRESSIVE: s_norm(t_norm((1-damage_dealt["high"]), (1-sidekick_health["low"])), t_norm(player_health["low"], sidekick_health["low"])),

    # IF player health is NOT low AND damage is NOT low THEN supporting
    action.SUPPORTIVE: t_norm((1-player_health["low"]), (1-damage_dealt["low"])),

    # IF player health is low AND (sidekick health is NOT low OR damage is NOT low) THEN defensive
    action.DEFENSIVE: t_norm(player_health["low"], s_norm((1-sidekick_health["low"]), (1-damage_dealt["low"]))),

    # IF player health is NOT low AND sidekick health is low THEN self-preserve
    action.SELF_PRESERVE: t_norm((1-player_health["low"]),sidekick_health["low"])
  }

  return max(rule_strengths, key=rule_strengths.get), rule_strengths.items()

def suggest_action(frame):
  return apply_rules(calculate_memberships(frame))

player_knowledge = "unknown"
enemy_knowledge ="unknown"

t_norm = lukasiewicz_t
s_norm = lukasiewicz_s