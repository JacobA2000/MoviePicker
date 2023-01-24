import discord
import requests
import dotenv
import os
from discord.ui import Select, View
import random
import json

# LOAD TOKEN
dotenv.load_dotenv()
DISCORD_TOKEN = str(os.getenv("DISCORD_TOKEN"))
TMDB_TOKEN_V3 = str(os.getenv("TMDB_TOKEN_V3"))

#GLOBAL CONFIG VARS
manager_role = ""
suggestions_open = True

active_pool = []
seen_pool = []

#LOAD CONFIG DATA FROM config.json
with open("./config.json", "r") as config_file:
    config_data = json.load(config_file)

manager_role = config_data["manager_role"]
suggestions_open = config_data["suggestions_open"]
    
#LOAD POOL DATA FROM movie_pool.json
with open("./movie_pool.json", "r") as pool_file:
    pool_data = json.load(pool_file)

active_pool = pool_data["active_pool"]
seen_pool = pool_data["seen_pool"]

bot = discord.Bot()

@bot.event
async def on_ready():
    print(f"Bot is online as user {bot.user}")

@bot.slash_command(name='suggest', description='Suggest a movie.')
async def movie_suggest(ctx, *, movie:str):
    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_TOKEN_V3}&query={movie}"
    results = requests.get(url).json()
    top_results = results['results'][:4]

    select = Select(placeholder="Choose the correct movie.", min_values=1, max_values=1)
    
    options = []
    view = View()
    for result in top_results:
        movie_title_and_year = f"{result['title']} ({result['release_date'][:4]})"
        movie_tmdb_id = result['id']
        movie_desc = f"{result['overview'][:97]}..."

        options.append(discord.SelectOption(label=movie_title_and_year, value=str(movie_tmdb_id), description=movie_desc))
    
    select.options = options

    async def movie_select_callback(interaction):
        select.disabled = True
        selected_movie_id = select.values[0]

        #CHECK IF THE POOL IS FULL
        #CHECK IF USER HAS ALREADY MADE A SUGGESTION THATS IN THE POOL
        #CHECK IF MOVIE IN SUGGESTION POOL ALREADY
        #IF NOT ADD IT LOCALLY AND IN FILES

        await interaction.response.edit_message(view=view)
        await interaction.followup.send(f"Awesome! I like {select.values[0]} too!")

    select.callback = movie_select_callback

    view.add_item(select)

    await ctx.send("hi", view=view)

@bot.slash_command(name='draw', description='Randomly selects a movie from the pool, creates an event and messages the movie channel.')
async def draw(ctx):
    member = ctx.guild.get_member(ctx.author.id)

    if manager_role in [role.name for role in member.roles]:
        random_movie_from_pool = active_pool[random.randint(0, len(active_pool)-1)]
        await ctx.respond(f"Movie Drawn - ({random_movie_from_pool})")
    else:
        await ctx.respond("You do not have permission to run this command.")
    
bot.run(DISCORD_TOKEN)