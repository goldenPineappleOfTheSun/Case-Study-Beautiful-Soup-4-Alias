import codecs
import random
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

def generate_id(n):
    return ''.join([chr(random.randint(97, 122)) for x in range(n)])

class Player:
    def __init__(self, code):
        self.code = code

class Team:
    def __init__(self, code, name):
        self.code = code
        self.name = name
        self.players = []
        self.current_player = None
        self.next_player_generator = self.get_next_player()
        self.words = []

    def add_player(self):
        player_code = generate_id(8)
        self.players.append(Player(player_code))
        return player_code

    def find_player(self, code):
        for player in self.players:
            if player.code == code:
                return player
        return None

    def next_player(self):
        self.current_player = next(self.next_player_generator)

    def get_next_player(self):
        while True:
            if len(self.players) == 0:
                yield None
            for player in self.players:
                yield player

    def plus(self, word):
        self.words.append(word)

class Game:
    def __init__(self, teams_count, win_count, words, wordpackname):
        self.code = generate_id(8)
        self.teams = [Team(generate_id(8), chr(65+x)) for x in range(teams_count)]
        self.players = []
        self.win_count = win_count
        self.words = words
        self.wordpackname = wordpackname
        self.started = False
        self.round_start_time = None
        self.round_size = 60
        self.current_team = None
        self.next_team_generator = self.get_next_team()
        self.current_word = self.get_random_word()
        self.winner = None

    def join(self, team):
        return team.add_player()

    def find_team(self, code):
        for team in self.teams:
            if team.code == code:
                return team
        return None

    def start(self):
        self.started = True
        self.load_next_round()

    def start_round(self, team_code, player_code):
        if self.current_team.code != team_code:
            raise "!"
        if self.current_team.current_player.code != player_code:
            raise "?"
        self.round_start_time = datetime.now()

    def load_next_round(self):
        self.current_team = next(self.next_team_generator)
        self.current_team.next_player()
        self.round_start_time = None
        winner = None
        for team in self.teams:
            if len(team.words) >= self.win_count:
                if winner == None:
                    winner = team
                else:
                    winner = None
                    break
        self.winner = winner

    def get_next_team(self):
        while True:
            if len(self.teams) == 0:
                yield None
            for team in self.teams:
                yield team
    
    def get_random_word(self):
        return random.choice(self.words)

    def plus(self, word):
        self.current_team.plus(word)
        self.current_word = self.get_random_word()

    def is_round_ended(self):
        if self.round_start_time == None:
            return True
        return (datetime.now() - self.round_start_time).total_seconds() > self.round_size

games = {}

def find_game(game_code):
    if game_code not in games:
        return None
    else:
        return games[game_code]

def find_game_and_team(game_code, team_code):
    if game_code not in games:
        return None, None
    game = games[game_code]
    team = game.find_team(team_code)
    return game, team

def find_game_and_team_and_player(game_code, team_code, player_code):
    if game_code not in games:
        return None, None
    game = games[game_code]
    team = game.find_team(team_code)
    if team == None:
        return game, None, None
    player = team.find_player(player_code)
    return game, team, player

@app.get("/create_game/")
async def create_game(request: Request):
    import os
    import pathlib
    wordpacks = []
    for file in os.listdir(pathlib.Path(__file__).parent.resolve()):
        if file.endswith(".wdpck"):
            wordpacks.append(file)
    return templates.TemplateResponse("create-game.html", {'request': request, 'app':app, 'wordpacks':wordpacks})

@app.get("/generate_game/")
async def generate_game(request: Request):
    words = []
    post = dict(request.query_params.items())
    wordpack = post['wordpack'] if 'wordpack' in post else 'python.wdpck'
    teams_count = int(post['teams-count'])
    win_count = int(post['win-count'])
    with codecs.open(f'{wordpack}', "r", "utf-8") as f:
        words = f.read().split(',');
    game = Game(teams_count, win_count, words, wordpack)
    games[game.code] = game
    return templates.TemplateResponse("game-created.html", {'request': request, 'app': app, 'game': game})

@app.get("/join/{game_code:str}/{team_code:str}")
async def join(request: Request, game_code, team_code):
    game, team = find_game_and_team(game_code, team_code)
    if game == None:
        return "game is not found"
    if game.started:
        return "game is already started"
    if team == None:
        return "team is not found"
    player_code = game.join(team)
    return RedirectResponse(app.url_path_for('game', game_code=game_code, team_code=team_code, player_code=player_code))

@app.get("/start/{game_code:str}")
async def start(request: Request, game_code):
    game = find_game(game_code)
    game.start()
    return templates.TemplateResponse("statistics.html", {'request': request, 'game': game, })

@app.get("/ready/{game_code:str}/{team_code:str}/{player_code:str}")
async def ready(request: Request, game_code, team_code, player_code):
    game = find_game(game_code)
    game.start_round(team_code, player_code)
    return RedirectResponse(app.url_path_for('game', game_code=game_code, team_code=team_code, player_code=player_code))

@app.get("/plus/{game_code:str}/{team_code:str}/{player_code:str}/{word:str}")
async def plus(request: Request, game_code, team_code, player_code, word):
    game = find_game(game_code)
    game.plus(word)
    if game.is_round_ended():
        game.load_next_round()
    return RedirectResponse(app.url_path_for('game', game_code=game_code, team_code=team_code, player_code=player_code))

@app.get("/game/{game_code:str}/{team_code:str}/{player_code:str}")
async def game(request: Request, game_code, team_code, player_code):
    game, team, player = find_game_and_team_and_player(game_code, team_code, player_code)
    if game == None:
        return "game is not found"
    if team == None:
        return "team is not found"
    if not game.started:
        return templates.TemplateResponse("wait-start.html", {
            'request': request, 
            'app': app, 
            'game': game, 
            'team': team, 
            'player': player
        })
    if game.winner:
        return templates.TemplateResponse("winner.html", {
            'request': request, 
            'app': app, 
            'game': game, 
            'team': team, 
            'player': player,
            'winner': game.winner
        })
    if game.current_team.code != team_code:
        return templates.TemplateResponse("wait-other-team.html", {
            'request': request, 
            'app': app, 
            'game': game, 
            'team': team, 
            'player': player,
            'current_team': game.current_team
        })
    if game.current_team.current_player.code != player_code:
        return templates.TemplateResponse("listen.html", {
            'request': request, 
            'app': app, 
            'game': game, 
            'team': team, 
            'player': player,
            'current_team': game.current_team
        })
    if game.round_start_time == None:
        return templates.TemplateResponse("ready.html", {
            'request': request, 
            'app': app, 
            'game': game, 
            'team': team, 
            'player': player,
            'current_team': game.current_team
        })
    if game.current_team.current_player.code == player_code:
        return templates.TemplateResponse("speak.html", {
            'request': request, 
            'app': app, 
            'game': game, 
            'team': team, 
            'player': player,
            'current_team': game.current_team,
            'word': game.current_word
        })