import requests
url="http://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams"
response = requests.get(url)
data = response.json()

temp=data['sports'][0]['leagues'][0]['teams'][0]['team']
te=data['sports'][0]['leagues'][0]['teams']
for teams in te:
    print(teams)
#print(data['sports'][0]['leagues'][0]['teams'])