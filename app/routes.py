from flask import render_template, request, jsonify
import sqlite3 as db
import cohere
import os
import google.generativeai as genai
import requests

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

    @app.route('/gamesByYear')
    def gamesByYear():
        conn = connectToDB()
        years = conn.execute('SELECT DISTINCT strftime("%Y", game_date) as year FROM game ORDER BY year').fetchall()
        conn.close()
        return render_template('games_by_year.html', years=years)

    @app.route('/gamesByYear/<year>')
    def gamesInYear(year):
        conn = connectToDB()
        games = conn.execute('SELECT * FROM game WHERE strftime("%Y", game_date) = ? ORDER BY game_date', (year,)).fetchall()
        conn.close()
        return render_template('games_in_year.html', year=year, games=games)

    @app.route('/teams')
    def teams():
        conn = connectToDB()
        teams = conn.execute('SELECT * FROM team ORDER BY full_name').fetchall()
        conn.close()
        return render_template('teams.html', teams=teams) 

    @app.route('/teamYears/<team_id>')
    def teamYears(team_id):
        conn = connectToDB()
        years = conn.execute('SELECT DISTINCT strftime("%Y", game_date) as year FROM game WHERE team_id_home = ? OR team_id_away = ? ORDER BY year', (team_id, team_id)).fetchall()
        conn.close()
        return render_template('team_years.html', team_id=team_id, years=years)

    @app.route('/teamGames/<team_id>/<year>')
    def teamGames(team_id, year):
        conn = connectToDB()
        games = conn.execute('SELECT * FROM game WHERE (team_id_home = ? OR team_id_away = ?) AND strftime("%Y", game_date) = ? ORDER BY game_date', (team_id, team_id, year)).fetchall()
        conn.close()
        return render_template('team_games.html', team_id=team_id, year=year, games=games)

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
        if not play_by_play_text or not box_score_text:
            prompt = f"Summarize the game between {game['team_name_home']} and {game['team_name_away']} on {game['game_date']} check on the internet for relevant information about the game."
        # Generate game summary using Cohere's API
        cohere_api_key = app.config['COHERE_API_KEY']
        google_api_key = app.config['GOOGLE_API_KEY']
        genai.configure(api_key=google_api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        resGoog = model.generate_content(prompt)
        co = cohere.ClientV2(cohere_api_key)
        response = co.chat(
            model="command-r-plus-08-2024",
            messages=[{'role': 'user', 'content': prompt}],
        )
        game_summary = response.message.content[0].text
        #game_summary = resGoog.text 

        return render_template('game_details.html', game=game, home_team=home_team, away_team=away_team, game_summary=game_summary)

    @app.route('/play_by_play/<game_id>')
    def play_by_play(game_id):
        conn = connectToDB()
        playByPlay = conn.execute('SELECT * FROM play_by_play WHERE game_id = ?', (game_id,)).fetchall()
        conn.close()
        return render_template('play_by_play.html', playByPlay=playByPlay, game_id=game_id)
    
    @app.route('/searchTeams', methods=['GET'])
    def searchTeams():
        teamOne= request.args.get('teamOne')
        teamTwo= request.args.get('teamTwo')
        conn=connectToDB()
        years=conn.execute('''SELECT DISTINCT strftime("%Y", game_date) as year 
                           FROM game 
                           where (team_name_home=? and team_name_away=?) or (team_name_home=? and team_name_away=?)
                           ORDER BY year''',(teamOne, teamTwo, teamTwo, teamOne)).fetchall()
        conn.close()
        return render_template('search_results.html', teamOne=teamOne, teamTwo=teamTwo, years=years)
    
    @app.route('/gamesBetweenTeams/<teamOne>/<teamTwo>/<year>')
    def games_between_teams(teamOne, teamTwo, year):
        conn = connectToDB()
        games = conn.execute('''SELECT * FROM game 
                             WHERE (team_name_home = ? AND team_name_away = ? OR team_name_home = ? AND team_name_away = ?) AND strftime("%Y", game_date) = ? 
                             ORDER BY game_date''', (teamOne, teamTwo, teamTwo, teamOne, year)).fetchall()
        conn.close()
        return render_template('games_between_teams.html', teamOne=teamOne, teamTwo=teamTwo, year=year, games=games)
    
    @app.route('/team_names')
    def team_names():
        conn = connectToDB()
        teams = conn.execute('SELECT full_name FROM team ORDER BY full_name').fetchall()
        conn.close()
        team_names = [team['full_name'] for team in teams]
        return jsonify(team_names) 