from flask import render_template
import sqlite3 as db
import cohere
import os

def connectToDB():
    conn = db.connect('nba.sqlite')
    conn.row_factory = db.Row
    return conn

def init_routes(app):
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/listOfGames')
    def listOfGames():
        conn = connectToDB()
        games = conn.execute('SELECT * FROM game').fetchall()
        conn.close()
        return render_template('listOfGames.html', games=games)

    @app.route('/game/<game_id>')
    def game(game_id):
        conn = connectToDB()
        game = conn.execute('SELECT * FROM game WHERE game_id = ?', (game_id,)).fetchone()
        box_scores = conn.execute('''
            SELECT 
                p.game_id, 
                p.player1_name AS player_name, 
                p.player1_team_abbreviation AS team, 
                COUNT(*) AS events, 
                SUM(CASE WHEN p.eventmsgtype = 1 THEN 1 ELSE 0 END) AS field_goals_made,
                SUM(CASE WHEN p.eventmsgtype = 2 THEN 1 ELSE 0 END) AS field_goals_attempted,
                SUM(CASE WHEN p.eventmsgtype = 3 THEN 1 ELSE 0 END) AS three_pointers_made,
                SUM(CASE WHEN p.eventmsgtype = 4 THEN 1 ELSE 0 END) AS free_throws_made,
                SUM(CASE WHEN p.eventmsgtype = 5 THEN 1 ELSE 0 END) AS free_throws_attempted,
                SUM(CASE WHEN p.eventmsgtype = 6 THEN 1 ELSE 0 END) AS rebounds,
                SUM(CASE WHEN p.eventmsgtype = 7 THEN 1 ELSE 0 END) AS assists,
                SUM(CASE WHEN p.eventmsgtype = 8 THEN 1 ELSE 0 END) AS steals,
                SUM(CASE WHEN p.eventmsgtype = 9 THEN 1 ELSE 0 END) AS blocks,
                SUM(CASE WHEN p.eventmsgtype = 10 THEN 1 ELSE 0 END) AS turnovers,
                SUM(CASE WHEN p.eventmsgtype = 11 THEN 1 ELSE 0 END) AS personal_fouls
            FROM play_by_play p
            WHERE p.game_id = ?
            GROUP BY p.player1_name, p.player1_team_abbreviation, p.game_id
        ''', (game_id,)).fetchall()

        play_by_play = conn.execute('SELECT * FROM play_by_play WHERE game_id = ?', (game_id,)).fetchall()
        conn.close()

        home_team = [score for score in box_scores if score['team'] == game['team_abbreviation_home']]
        away_team = [score for score in box_scores if score['team'] == game['team_abbreviation_away']]

        # Prepare context for Cohere's API
        box_score_text = "\n".join([f"{score['player_name']} ({score['team']}): {score['field_goals_made']} FGM, {score['field_goals_attempted']} FGA, {score['three_pointers_made']} 3PM, {score['free_throws_made']} FTM, {score['free_throws_attempted']} FTA, {score['rebounds']} REB, {score['assists']} AST, {score['steals']} STL, {score['blocks']} BLK, {score['turnovers']} TO, {score['personal_fouls']} PF" for score in box_scores])

        play_by_play_text = "\n".join([f"Period {play['period']}, Time {play['pctimestring']}: {play['homedescription']} {play['visitordescription']} (Score: {play['score']})" for play in play_by_play])

        prompt = f"Summarize the game between {game['team_name_home']} and {game['team_name_away']} on {game['game_date']}.\n\nBox Score:\n{box_score_text}\n\nPlay by Play:\n{play_by_play_text}"

        # Generate game summary using Cohere's API
        cohere_api_key = app.config['COHERE_API_KEY']
        co = cohere.ClientV2(cohere_api_key)
        response = co.chat(
            model="command-r-plus-08-2024",
            messages=[{'role': 'user', 'content': prompt}],
        )
        game_summary = response.message.content[0].text

        return render_template('game_details.html', game=game, home_team=home_team, away_team=away_team, game_summary=game_summary)

    @app.route('/play_by_play/<game_id>')
    def play_by_play(game_id):
        conn = connectToDB()
        playByPlay = conn.execute('SELECT * FROM play_by_play WHERE game_id = ?', (game_id,)).fetchall()
        conn.close() 
        return render_template('play_by_play.html', playByPlay=playByPlay, game_id=game_id)