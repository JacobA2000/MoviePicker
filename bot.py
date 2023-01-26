import discord
import requests
import dotenv
import os
from discord.ui import Select, View
import random
import json
from urllib.parse import quote

# LOAD TOKEN
dotenv.load_dotenv()
DISCORD_TOKEN = str(os.getenv("DISCORD_TOKEN"))
TMDB_TOKEN_V3 = str(os.getenv("TMDB_TOKEN_V3"))

MOVIE_POOL_FILE_PATH = '/home/pi/MoviePicker/movie_pool.json'
CONFIG_FILE_PATH = '/home/pi/MoviePicker/config.json'

#GLOBAL CONFIG VARS
manager_role = ""
movie_role = ""
suggestions_open = True

active_pool = []
seen_pool = []

#LOAD CONFIG DATA FROM config.json
with open(CONFIG_FILE_PATH, "r") as config_file:
    config_data = json.load(config_file)

manager_role = config_data["manager_role"]
movie_role = config_data["movie_role"]
suggestions_open = config_data["suggestions_open"]
active_pool_max_items = config_data["active_pool_max_items"]
    
#LOAD POOL DATA FROM movie_pool.json
with open(MOVIE_POOL_FILE_PATH, "r") as pool_file:
    pool_data = json.load(pool_file)

active_pool = pool_data["active_pool"]
seen_pool = pool_data["seen_pool"]

bot = discord.Bot()

@bot.event
async def on_ready():
    print(f"Bot is online as user {bot.user}")

@bot.slash_command(name='suggest', description='Suggest a movie.')
async def movie_suggest(ctx, *, movie:str):
    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_TOKEN_V3}&query={quote(movie)}"
    
    results = requests.get(url).json()

    if len(results['results']) == 0:
        await ctx.respond("Couldn't find any movies with that name, please ensure you are spelling it correctly.", ephemeral=True)
        return
        
    top_results = results['results'][:10]

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

        url = f"https://api.themoviedb.org/3/movie/{selected_movie_id}?api_key={TMDB_TOKEN_V3}"
        movie_data = requests.get(url).json()

        movie_poster_url = f"https://image.tmdb.org/t/p/w500{movie_data['poster_path']}"

        if suggestions_open == False:
            await interaction.response.edit_message(view=view)
            await interaction.followup.send(f"Suggestions are currently closed try again once they reopen.", ephemeral=True)
            return

        if len(active_pool) >= active_pool_max_items:
            await interaction.response.edit_message(view=view)
            await interaction.followup.send(f"The pool is at capacity, wait for some space to open up.", ephemeral=True)
            return

        for movie in active_pool:
            if selected_movie_id == movie['id']:
                await interaction.response.edit_message(view=view)
                await interaction.followup.send(f"Someone else beat ya to it. That movie is already in the pool.", ephemeral=True)
                return

        #CHECK IF USER HAS REACHED THEIR SUGGESTION CAP
        user_active_suggested_movie_count = 0
        for movie in active_pool:
            if ctx.author.id == movie["suggested_by"]:
                user_active_suggested_movie_count += 1
        
        if user_active_suggested_movie_count >= 3:
            await interaction.response.edit_message(view=view)
            await interaction.followup.send(f"Sorry you have already reached you maximum suggestion count. You will be able to suggest again when you have less than 3 active suggestions.", ephemeral=True)
            return

        selected_movie_json = {
            "id": selected_movie_id,
            "title": movie_data['title'],
            "release_date": movie_data['release_date'],
            "original_title": movie_data['original_title'],
            "original_lang": movie_data['original_language'],
            "rating": int(float(movie_data['vote_average'])*10),
            "poster_url": movie_poster_url,
            "suggested_by": ctx.author.id
        }

        with open(MOVIE_POOL_FILE_PATH, "r") as pool_file:
            pool_data = json.load(pool_file)
        
        pool_data["active_pool"].append(selected_movie_json)
        active_pool.append(selected_movie_json)

        with open(MOVIE_POOL_FILE_PATH, "w") as pool_file:
            json.dump(pool_data, pool_file, indent=4, separators=(',',': '))

        response_embed = discord.Embed(
            title=f"{ctx.author.name} has added a movie to the pool.",
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

    await ctx.respond("Search complete please select the correct movie below. (if it isn't on there ensure the title is correct)", view=view, ephemeral=True)

@bot.slash_command(name="suggest_by_id", description="Alternative suggest command to be used when a movie cannot be found by the search used in /suggest.")
async def movie_suggest_id(ctx, *, id:int):
    id = str(id)
    url = f"https://api.themoviedb.org/3/movie/{id}?api_key={TMDB_TOKEN_V3}"

    movie_by_id = requests.get(url).json()

    if 'success' in movie_by_id:
        if movie_by_id['success'] == False:
            await ctx.respond(movie_by_id['status_message'])
    
    if suggestions_open == False:
        await ctx.respond(f"Suggestions are currently closed try again once they reopen.", ephemeral=True)
        return

    if len(active_pool) >= active_pool_max_items:
        await ctx.respond(f"The pool is at capacity, wait for some space to open up.", ephemeral=True)
        return

    for movie in active_pool:
        if id == movie['id']:
            await ctx.respond(f"Someone else beat ya to it. That movie is already in the pool.", ephemeral=True)
            return

    #CHECK IF USER HAS REACHED THEIR SUGGESTION CAP
    user_active_suggested_movie_count = 0
    for movie in active_pool:
        if ctx.author.id == movie["suggested_by"]:
            user_active_suggested_movie_count += 1
        
    if user_active_suggested_movie_count >= 3:
        await ctx.respond(f"Sorry you have already reached you maximum suggestion count. You will be able to suggest again when you have less than 3 active suggestions.", ephemeral=True)
        return
    
    movie_poster_url = f"https://image.tmdb.org/t/p/w500{movie_by_id['poster_path']}"
    movie_json = {
        "id": id,
        "title": movie_by_id['title'],
        "release_date": movie_by_id['release_date'],
        "original_title": movie_by_id['original_title'],
        "original_lang": movie_by_id['original_language'],
        "rating": int(float(movie_by_id['vote_average'])*10),
        "poster_url": movie_poster_url,
        "suggested_by": ctx.author.id
    }

    with open(MOVIE_POOL_FILE_PATH, "r") as pool_file:
        pool_data = json.load(pool_file)
        
    pool_data["active_pool"].append(movie_json)
    active_pool.append(movie_json)

    with open(MOVIE_POOL_FILE_PATH, "w") as pool_file:
        json.dump(pool_data, pool_file, indent=4, separators=(',',': '))

    response_embed = discord.Embed(
        title=f"{ctx.author.name} has added a movie to the pool.",
        description=f"Congrats! {movie_by_id['title']} has been added to the pool. Good luck in the draw.",
        url=movie_by_id["homepage"]
    )

    response_embed.add_field(name="Rating", inline=True, value=f"{int(float(movie_by_id['vote_average'])*10)}%")
    response_embed.add_field(name="Original Title", inline=True, value=movie_by_id['original_title'])
    response_embed.add_field(name="Original Language", inline=True, value=movie_by_id['original_language'])
    response_embed.set_thumbnail(url=movie_poster_url)

    await ctx.respond(embed=response_embed)

@bot.slash_command(name="remove_suggestion", description="Allows you to remove your own suggestions.")
async def remove_suggestion(ctx):
    user_id = ctx.author.id
    select = Select(placeholder="Choose the correct movie.", min_values=1, max_values=1)

    view = View()
    options = []
    for movie in active_pool:
        if movie['suggested_by'] == user_id:
            options.append(discord.SelectOption(label=movie['title'], value=movie['id']))
    
    select.options = options

    async def remove_select_callback(interaction):
        select.disabled = True
        selected_movie_id = select.values[0]
        movie_title = ""
        
        i = 0
        for movie in active_pool:
            i += 1
            if movie['id'] == selected_movie_id:
                movie_title = movie['title']
                break
        
        with open(MOVIE_POOL_FILE_PATH, "r") as pool_file:
            pool_data = json.load(pool_file)
        
        pool_data['active_pool'].pop(i-1)
        active_pool.pop(i-1)

        with open(MOVIE_POOL_FILE_PATH, "w") as pool_file:
            json.dump(pool_data, pool_file, indent=4, separators=(',',': '))

        await interaction.response.edit_message(view=view)
        await interaction.followup.send(f"{ctx.author.name} removed \"{movie_title}\" from the pool.")
    
    select.callback = remove_select_callback
    view.add_item(select)

    await ctx.respond("Select the correct movie to remove from the pool.", view=view, ephemeral=True)

@bot.slash_command(name="pool", description="Displays all the movies currently in the pool.")
async def pool(ctx):

    pool_embed = discord.Embed(
        title=f"Current Movie Pool ({len(active_pool)}/{active_pool_max_items})",
        description=f"The following movies are currently in the pool to be drawn.",
    )

    embed_field_msg = ""
    for movie in active_pool:
        embed_field_msg += f"{movie['title']} ({movie['release_date'][:4]})\n"

    pool_embed.add_field(name="Movies:", value=embed_field_msg)
    await ctx.respond(embed=pool_embed)

"""
        MANAGER COMMANDS FROM HERE ONWARDS
"""

@bot.slash_command(name='draw', description='Randomly selects a movie from the pool, creates an event and messages the movie channel.')
async def draw(ctx):
    member = ctx.guild.get_member(ctx.author.id)

    if manager_role in [role.id for role in member.roles]:
        random_movie_index = random.randint(0, len(active_pool)-1)
        random_movie_from_pool = active_pool[random_movie_index]

        with open(MOVIE_POOL_FILE_PATH, "r") as pool_file:
            pool_data = json.load(pool_file)
        
        pool_data["seen_pool"].append(random_movie_from_pool)
        seen_pool.append(random_movie_from_pool)

        pool_data["active_pool"].pop(random_movie_index)
        active_pool.pop(random_movie_index)

        with open(MOVIE_POOL_FILE_PATH, "w") as pool_file:
            json.dump(pool_data, pool_file, indent=4, separators=(',',': '))
        
        draw_embed = discord.Embed(
            title=f"{random_movie_from_pool['title']} has been selected.",
            description=f"Congrats! <@{random_movie_from_pool['suggested_by']}> your movie has been selected.",
        )

        draw_embed.add_field(name="Rating", inline=True, value=f"{random_movie_from_pool['rating']}%")
        draw_embed.add_field(name="Original Title", inline=True, value=random_movie_from_pool['original_title'])
        draw_embed.add_field(name="Original Language", inline=True, value=random_movie_from_pool['original_lang'])
        draw_embed.set_image(url=random_movie_from_pool["poster_url"])

        await ctx.respond(embed=draw_embed)
    else:
        await ctx.respond("You do not have permission to run this command.")

@bot.slash_command(name="open_suggestions", description="Opens the pool for suggestions.")
async def open_suggestions(ctx):
    global suggestions_open
    member = ctx.guild.get_member(ctx.author.id)

    if suggestions_open == True:
        await ctx.respond("Suggestions are already open.", ephemeral=True)
        return

    if manager_role in [role.id for role in member.roles]:
        
        with open(CONFIG_FILE_PATH, "r") as config_file:
            config_data = json.load(config_file)

        config_data["suggestions_open"] = True
        suggestions_open = True

        with open(CONFIG_FILE_PATH, "w") as config_file:
            json.dump(config_data, config_file, indent=4, separators=(',',': '))

        await ctx.respond(f"Suggestions have opened! There are currently {active_pool_max_items -len(active_pool)} free slots in the pool.")
    else:
        await ctx.respond("You do not have permission to run this command.", ephemeral=True)

@bot.slash_command(name="close_suggestions", description="Closes the pool for suggestions.")
async def close_suggestions(ctx):
    global suggestions_open
    member = ctx.guild.get_member(ctx.author.id)

    if suggestions_open == False:
        await ctx.respond("Suggestions are already closed.", ephemeral=True)
        return

    if manager_role in [role.id for role in member.roles]:
        
        with open(CONFIG_FILE_PATH, "r") as config_file:
            config_data = json.load(config_file)

        config_data["suggestions_open"] = False
        suggestions_open = False

        with open(CONFIG_FILE_PATH, "w") as config_file:
            json.dump(config_data, config_file, indent=4, separators=(',',': '))

        await ctx.respond(f"Suggestions have closed! Good luck in the draw.")
    else:
        await ctx.respond("You do not have permission to run this command.", ephemeral=True)

@bot.slash_command(name="set_pool_size", description="Sets the size of the maximum number of movies in the pool.")
async def set_pool_size(ctx, *, max_items:int):
    global active_pool_max_items
    member = ctx.guild.get_member(ctx.author.id)

    if manager_role in [role.id for role in member.roles]:
        
        with open(CONFIG_FILE_PATH, "r") as config_file:
            config_data = json.load(config_file)

        config_data["active_pool_max_items"] = max_items
        active_pool_max_items = max_items

        with open(CONFIG_FILE_PATH, "w") as config_file:
            json.dump(config_data, config_file, indent=4, separators=(',',': '))

        await ctx.respond(f"Max pool size updated to {active_pool_max_items}")
    else:
        await ctx.respond("You do not have permission to run this command.", ephemeral=True)

bot.run(DISCORD_TOKEN)