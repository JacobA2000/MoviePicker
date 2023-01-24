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
active_pool_max_items = config_data["active_pool_max_items"]
    
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

        url = f"https://api.themoviedb.org/3/movie/{selected_movie_id}?api_key={TMDB_TOKEN_V3}&query={movie}"
        movie_data = requests.get(url).json()

        movie_poster_url = f"https://image.tmdb.org/t/p/w500{movie_data['poster_path']}"

        if suggestions_open == False:
            await interaction.response.edit_message(view=view)
            await interaction.followup.send(f"Pool's Closed.")
            return

        if len(active_pool) >= active_pool_max_items:
            await interaction.response.edit_message(view=view)
            await interaction.followup.send(f"The pool is at capacity, wait for some space to open up.")
            return

        if selected_movie_id in active_pool:
            await interaction.response.edit_message(view=view)
            await interaction.followup.send(f"Someone else beat ya to it. That movie is already in the pool.")
            return

        #CHECK IF USER HAS REACHED THEIR SUGGESTION CAP

        with open("./movie_pool.json", "r") as pool_file:
            pool_data = json.load(pool_file)
        
        pool_data["active_pool"].append(selected_movie_id)

        with open("./movie_pool.json", "w") as pool_file:
            json.dump(pool_data, pool_file, indent=4, separators=(',',': '))

        response_embed = discord.Embed(
            title=f"Movie added to the pool.",
            description=f"Congrats! {movie_data['title']} has been added to the pool. Good luck in the draw.",
            url=movie_data["homepage"]
        )

        response_embed.add_field(name="Rating", inline=True, value=f"{int(float(movie_data['vote_average'])*10)}%")
        response_embed.add_field(name="Original Title", inline=True, value=movie_data['original_title'])
        response_embed.add_field(name="Original Language", inline=True, value=movie_data['original_language'])
        response_embed.set_thumbnail(url=movie_poster_url)

        await interaction.response.edit_message(view=view)
        await interaction.followup.send(embed=response_embed)

    select.callback = movie_select_callback

    view.add_item(select)

    await ctx.respond("Search complete please select the correct movie below. (if it isn't on there ensure the title is correct)", view=view)

@bot.slash_command(name='draw', description='Randomly selects a movie from the pool, creates an event and messages the movie channel.')
async def draw(ctx):
    member = ctx.guild.get_member(ctx.author.id)

    if manager_role in [role.name for role in member.roles]:
        random_movie_from_pool = active_pool[random.randint(0, len(active_pool)-1)]
        await ctx.respond(f"Movie Drawn - ({random_movie_from_pool})")
    else:
        await ctx.respond("You do not have permission to run this command.")
    
bot.run(DISCORD_TOKEN)