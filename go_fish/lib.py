#!/usr/bin/env python3
import random
import aiohttp

COLORS = ['red', 'black']

SUITES = [
    ('red', 'diamonds'),
    ('black', 'spades'),
    ('red', 'hearts'),
    ('black', 'clubs')
]

CARDS = [
    'A', 'K', 'Q', 'J',
    '10', '9', '8', '7', '6', '5', '4', '3', '2'
]


class Card:
    def __init__(self, kind, suit, color):
        self.kind = kind
        self.suit = suit
        self.color = color
    @classmethod
    def from_string(cls, string):
        l = string.split(' ')
        kind = l[0]
        suit = l[-1]
        color = [color for color, suit in SUITES if suit == l[-1]][0]
        return cls(kind, suit, color)


DEFAULT_CARD_SET = [Card(kind, suit, color) for kind in CARDS for color, suit in SUITES]

class Deck:
    deck = list()
    discard = list()


    def __init__(self, card_set=None, n=1):
        self.card_set = card_set or DEFAULT_CARD_SET
        for n in range(n):
            self.deck = self.deck + DEFAULT_CARD_SET.copy()

    def shuffle(self):
        random.shuffle(self.deck)

    def draw(self):
        return self.deck.pop()

    def insert_random(self, card):
        self.deck.insert(
            random.randint(1, len(self.deck)),
            card,
        )

    def insert_botton(self, card):
        self.deck.insert(0, card)

    def deal_player(self, handsize):
        hand = list(self.deck[-handsize:])
        self.deck = self.deck[:-handsize]
        return hand


class GameData:
    active_player = None
    player_count = 0
    deck = None
    players = list()
    sets = None
    def __init__(
            self,
            player_count,
            deck):

        self.player_count = player_count
        self.deck = deck
        for i in range(player_count):
            self.players.append(Player(name=i))
        self.sets = {}


class GameStateMachine:
    def __init__(self):
        self.handlers = {}
        self.start_state = None
        self.end_states = []

    def add_state(self, name, handler, end_state=False):
        name = name.upper()
        self.handlers[name] = handler
        if end_state:
            self.end_states.append(name)

    def set_start(self, name):
        self.start_state = name.upper()

    def run(self, game_data):
        try:
            handler = self.handlers[self.start_state]
        except IndexError:
            raise InitializationError("must call .set_start()")
        if not self.end_states:
            raise InitializationError("at least one state must be an end_state")

        while True:
            new_state, game_data = handler(game_data)
            if new_state.upper() is self.end_states:
                print("Game over", new_state)
            else:
                handler = self.handlers[new_state.upper()]


def deal_players(gd):
    print("Dealing players")
    gd.deck.shuffle()
    for player in gd.players:
        player.hand = gd.deck.deal_player(7)
    return 'pick_starting_player', gd


def pick_starting_player(gd):
    gd.active_player = gd.players[0]
    return 'take_turn', gd


def inquire(gd):
    suite = None
    target_player = None
    target_player = input("Which player would you like to ask? ")
    kind = input("Which kind? ")
    cards = [c for c in gd.players[int(target_player)].hand if c.kind == kind]
    print(f"Player has cards: {cards}")
    if len(cards) > 0:
        for c in cards:
            print(f"Got {c.kind} of {c.suit}")
            gd.players[int(target_player)].hand.remove(c)
        gd.active_player.hand = gd.active_player.hand + cards
    else:
        draw_card(gd)

    return gd


def draw_card(gd):
    print("Go fish")
    c = gd.deck.draw()
    gd.active_player.hand.append(c)
    print(f"Drew the {c.kind} of {c.suit}")
    return gd

def player_win(gd):
    print(f"Player {gd.active_player.name} won!")
    return '', gd


def make_sets(gd):
    groups = grouped_by_kind(gd.active_player.hand)

    for kind, cards in groups.items():
        if len(cards) >= 3:
            print(f"Put down set of {kind}")
            if gd.sets.get(kind) is None:
                gd.sets[kind] = cards
            else:
                gd.sets[kind].append(cards)

            for card in cards:
                gd.active_player.hand.remove(card)


    for card in gd.active_player.hand:
        if card.kind in gd.sets:
            print(f"Added card to set of {card.kind}")
            gd.sets[card.kind].append(card)
            gd.active_player.hand.remove(card)

    if len(gd.active_player.hand) == 0:
        return 'player_win', gd
    else:
        return 'next_player', gd


def take_turn(gd):
    print("")
    print(f"It is player {gd.active_player.name}'s turn")
    gd.active_player.print_hand()
    actions = {'pass': lambda state: state, 'inquire': inquire}
    action = gd.active_player.choose_action(actions)
    gd = action(gd)
    return make_sets(gd)


def next_player(gd):
    pid = gd.active_player.name
    if pid == 0:
        gd.active_player = gd.players[gd.player_count - 1]
    else:
        gd.active_player = gd.players[pid - 1]
    return 'take_turn', gd



def grouped_by_kind(hand):
    groups = {}
    for card in hand:
        if groups.get(card.kind) is None:
            groups[card.kind] = [card]
        else:
            groups[card.kind].append(card)
    return groups


class Player:
    hand = None
    name = None

    def __init__(self, init_hand=None, name=None):
        self.hand = list()
        self.name = name

    def print_hand(self):
        print(', '.join(card.kind + " of " + card.suit for card in self.hand))

    def choose_action(self, actions):
        action_map = {}
        print("Choose from the following actions: \n")
        def print_choices():
            for index, (name, fn) in enumerate(actions.items()):
                action_map[index] = fn
                print(f"[{index}]: {name}")

        print_choices()
        while True:
            index = int(input())
            if index not in action_map.keys():
                print("Invalid choice")
                print_choices()
            else:
                break
        return action_map[index]

go_fish = GameStateMachine()
go_fish.add_state('next_player', next_player)
go_fish.add_state('player_wind', player_win, end_state=True)
go_fish.add_state('take_turn', take_turn)
go_fish.add_state('pick_starting_player', pick_starting_player)
go_fish.add_state('deal_players', deal_players)
go_fish.set_start('deal_players')
go_fish.run(GameData(4, Deck()))
