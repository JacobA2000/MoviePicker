import discord
import requests
import dotenv
import os
from discord.ui import Select, View, Button, Select

# LOAD TOKEN
dotenv.load_dotenv()
DISCORD_TOKEN = str(os.getenv("DISCORD_TOKEN"))
TMDB_TOKEN_V3 = str(os.getenv("TMDB_TOKEN_V3"))

bot = discord.Bot()

@bot.slash_command(name='suggest', description='Suggest a movie.')
async def movie_suggest(ctx, *, movie:str):
    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_TOKEN_V3}&query={movie}"
    results = requests.get(url).json()
    top_results = results['results'][:4]

    select = Select(placeholder="Choose the correct movie.", min_values=1, max_values=1)
    
    options = []
    view = View()
    for result in top_results:
        movie_title = result['title']
        movie_tmdb_id = result['id']

        options.append(discord.SelectOption(label=movie_title, value=str(movie_tmdb_id)))
    
    select.options = options

    async def movie_select_callback(interaction):
        select.disabled = True
        selected_movie_id = select.values[0]

        print(selected_movie_id)

        #WRITE SELECTION TO FILE/DB

        await interaction.response.edit_message(view=view)
        await interaction.followup.send(f"Awesome! I like {select.values[0]} too!")

    select.callback = movie_select_callback

    view.add_item(select)

    await ctx.send("hi", view=view)

    
    
bot.run(DISCORD_TOKEN)