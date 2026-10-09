import os
import random
import asyncio
import io
import requests
import discord
from discord.ext import commands
from PIL import Image
from ultralytics import YOLO

# ==========================================
# CONFIGURAÇÕES E SEGURANÇA
# ==========================================

TOKEN = "Nenhum" 

CANAL_PERMITIDO = 1487172466684989652
MODEL_PATH = "yolov8n.pt"
PONTOS_POR_ACERTO = 5
TEMPO_ESPERA_IMAGEM = 60


intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

print("Carregando modelo Ultralytics...")
try:
  model = YOLO(MODEL_PATH)
  print("Modelo carregado com sucesso!")
except Exception as e:
  print(f"Erro ao carregar o modelo YOLO: {e}")
  model = None

raridade_global = None
pontos = {}
jogos_ativos = set()

# ==========================================
# EVENTOS DO BOT
# ==========================================
@bot.event
async def on_ready():
    print(f"Logado como {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # O bot só vai responder no canal permitido
    if message.channel.id != CANAL_PERMITIDO:
        return

    await bot.process_commands(message)

@bot.event
async def on_member_join(member):
    canal = member.guild.system_channel
    if canal:
        await canal.send(
            f"👋 Olá {member.mention}, bem-vindo ao servidor!\n"
            "Digite !ajuda para ver as funcionalidades do bot."
        )


# ==========================================
# JOGO DA VELHA INTERATIVO
# ==========================================
class BotaoVelha(discord.ui.Button):
    def __init__(self, x, y):
        super().__init__(style=discord.ButtonStyle.secondary, label='\u200b', row=y)
        self.x = x
        self.y = y

    async def callback(self, interaction: discord.Interaction):
        view: ViewVelha = self.view
        estado = view.tabuleiro[self.x][self.y]

        if interaction.user not in (view.j1, view.j2):
            await interaction.response.send_message("Você não está nessa partida!", ephemeral=True)
            return

        if interaction.user != view.turno_atual:
            await interaction.response.send_message("Ainda não é o seu turno!", ephemeral=True)
            return

        if estado is not None:
            await interaction.response.send_message("Este espaço já está ocupado!", ephemeral=True)
            return

        if view.turno_atual == view.j1:
            self.label = 'X'
            self.style = discord.ButtonStyle.danger
            view.tabuleiro[self.x][self.y] = view.j1
        else:
            self.label = 'O'
            self.style = discord.ButtonStyle.success
            view.tabuleiro[self.x][self.y] = view.j2

        self.disabled = True

        vencedor = view.checar_vitoria()
        if vencedor:
            view.desativar_botoes()
            view.stop()
            await interaction.response.edit_message(content=f"🎉 **{vencedor.mention} VENCEU O JOGO DA VELHA!** 🎉", view=view)
            return

        if view.checar_empate():
            view.desativar_botoes()
            view.stop()
            await interaction.response.edit_message(content="🤝 **DEU VELHA!** O jogo empatou.", view=view)
            return

        view.turno_atual = view.j2 if view.turno_atual == view.j1 else view.j1
        await interaction.response.edit_message(content=f"🎮 **Jogo da Velha!**\nÉ a vez de {view.turno_atual.mention} jogar!", view=view)

class ViewVelha(discord.ui.View):
    def __init__(self, j1: discord.Member, j2: discord.Member):
        super().__init__(timeout=120)
        self.j1 = j1
        self.j2 = j2
        self.turno_atual = j1
        self.tabuleiro = [[None, None, None], [None, None, None], [None, None, None]]
        for x in range(3):
            for y in range(3):
                self.add_item(BotaoVelha(x, y))

    def checar_vitoria(self):
        for i in range(3):
            if self.tabuleiro[i][0] == self.tabuleiro[i][1] == self.tabuleiro[i][2] is not None:
                return self.tabuleiro[i][0]
            if self.tabuleiro[0][i] == self.tabuleiro[1][i] == self.tabuleiro[2][i] is not None:
                return self.tabuleiro[0][i]
        if self.tabuleiro[0][0] == self.tabuleiro[1][1] == self.tabuleiro[2][2] is not None:
            return self.tabuleiro[0][0]
        if self.tabuleiro[0][2] == self.tabuleiro[1][1] == self.tabuleiro[2][0] is not None:
            return self.tabuleiro[0][2]
        return None

    def checar_empate(self):
        for linha in self.tabuleiro:
            if None in linha:
                return False
        return True

    def desativar_botoes(self):
        for child in self.children:
            child.disabled = True

@bot.command()
async def jogodavelha(ctx, oponente: discord.Member):
    if oponente.bot:
        await ctx.send("🤖 Bots ainda não aprenderam a jogar jogo da velha contra humanos!")
        return
    if oponente == ctx.author:
        await ctx.send("Você não pode jogar contra si mesmo!")
        return
    
    view = ViewVelha(ctx.author, oponente)
    await ctx.send(
        f"🎮 **Jogo da Velha Iniciado!**\n{ctx.author.mention} (X) vs {oponente.mention} (O)\n\n"
        f"👉 Vez de {ctx.author.mention} jogar!", 
        view=view
    )


# ==========================================
# COMANDOS GERAIS
# ==========================================
@bot.command()
async def ajuda(ctx):
    await ctx.send(
        "📜 **Lista de Comandos**\n\n"
        "!ajuda → Mostra esta lista de comandos.\n"
        "!jogodavelha @usuario → Joga uma partida interativa de jogo da velha.\n"
        "!jogo → Sugere um jogo aleatório para você jogar.\n"
        "!dica → Envia uma dica aleatória do bot.\n"
        "!python → Receba dicas sobre a linguagem Python.\n"
        "!meme → Envia um meme aleatório da pasta.\n"
        "!pokemon → Mostra a imagem de um Pokémon aleatório.\n"
        "!dado → Rola o dado de raridades.\n"
        "!raridade → Mostra a raridade obtida no último dado.\n"
        "!jogar → Inicia o jogo de caça aos objetos usando IA.\n"
        "!parar → Encerra o jogo de caça aos objetos.\n"
        "!check → Mostra informações sobre um arquivo enviado."
    )

@bot.command()
async def dica(ctx):
    dicas = [
        "💡 Dica: Digite !erro",
        "💡 Dica: Digite !dado para testar sua sorte",
        "💡 Dica: Digite !python para receber dicas sobre programação em Python!"
    ]
    await ctx.send(random.choice(dicas))

@bot.command()
async def erro(ctx):
    await ctx.send("Eu não tenho erros... ou será que tenho? 🤔")

@bot.command()
async def dado(ctx):
    global raridade_global
    resultado = ['Comum', 'Incomum', 'Raro', 'Épico', 'Lendário', 'Mítico', 'Divino', 'Celestial']
    raridade_global = random.choices(resultado, weights=[40, 30, 15, 10, 4, 0.9, 0.09, 0.01], k=1)[0]
    await ctx.send(f"🎲 Você obteve: {raridade_global}")

@bot.command()
async def raridade(ctx):
    if raridade_global is None:
        await ctx.send("Você ainda não rolou o dado!")
    else:
        await ctx.send(f"Sua raridade atual é: {raridade_global}")

@bot.command(name="python")
async def python_dica(ctx):
    dicas = [
        "🐍 Use listas para armazenar vários valores.",
        "🐍 Use dicionários para organizar dados.",
        "🐍 Comece com `print('Hello World')`.",
        "🐍 Use `def` para criar funções."
    ]
    await ctx.send(random.choice(dicas))

@bot.command()
async def jogo(ctx):
    jogos = ["Minecraft", "Roblox", "Fortnite", "Hollow Knight", "Among Us", "Brawl Stars", "Valorant", "Terraria", "Stardew Valley", "Free Fire", "Call of Duty: Warzone"]
    await ctx.send(f"🎮 Sugestão: {random.choice(jogos)}")

@bot.command()
async def meme(ctx):
    pasta = os.path.join(os.path.dirname(__file__), "images")
    if not os.path.exists(pasta):
        await ctx.send("Pasta 'images' não encontrada.")
        return
    arquivos = os.listdir(pasta)
    if not arquivos:
        await ctx.send("Nenhum meme encontrado na pasta.")
        return
    nome = random.choice(arquivos)
    with open(os.path.join(pasta, nome), "rb") as f:
        await ctx.send(file=discord.File(f))


# ==========================================
# POKÉMON (Corrigido)
# ==========================================
@bot.command(aliases=['pokemons'])
async def pokemon(ctx):
    try:
        numero = random.randint(1, 1025)
        url = f"https://pokeapi.co/api/v2/pokemon/{numero}"
        
        res = await asyncio.to_thread(requests.get, url)
        
        if res.status_code == 200:
            data = res.json()
            imagem = data["sprites"]["front_default"]
            nome = data["name"].capitalize()
            
            await ctx.send(f"📖 **Pokédex #{numero}:** {nome}\n{imagem}")
        else:
            await ctx.send("❌ Não consegui encontrar esse Pokémon.")
    except Exception:
        await ctx.send("❌ Ocorreu um erro ao conectar com a Pokédex.")


# ==========================================
# CAÇA AOS OBJETOS (YOLO com Tradução)
# ==========================================
# Dicionário para traduzir as categorias do COCO Dataset (YOLO) para Português
DICIONARIO_YOLO = {
    'person': 'pessoa', 'bicycle': 'bicicleta', 'car': 'carro', 'motorcycle': 'moto', 
    'airplane': 'avião', 'bus': 'ônibus', 'train': 'trem', 'truck': 'caminhão', 'boat': 'barco', 
    'traffic light': 'semáforo', 'fire hydrant': 'hidrante', 'stop sign': 'placa de pare', 
    'parking meter': 'parquímetro', 'bench': 'banco de praça', 'bird': 'pássaro', 'cat': 'gato', 
    'dog': 'cachorro', 'horse': 'cavalo', 'sheep': 'ovelha', 'cow': 'vaca', 'elephant': 'elefante', 
    'bear': 'urso', 'zebra': 'zebra', 'giraffe': 'girafa', 'backpack': 'mochila', 
    'umbrella': 'guarda-chuva', 'handbag': 'bolsa', 'tie': 'gravata', 'suitcase': 'mala', 
    'frisbee': 'frisbee', 'skis': 'esquis', 'snowboard': 'snowboard', 'sports ball': 'bola esportiva', 
    'kite': 'pipa', 'baseball bat': 'taco de beisebol', 'baseball glove': 'luva de beisebol', 
    'skateboard': 'skate', 'surfboard': 'prancha de surf', 'tennis racket': 'raquete de tênis', 
    'bottle': 'garrafa', 'wine glass': 'taça de vinho', 'cup': 'copo', 'fork': 'garfo', 
    'knife': 'faca', 'spoon': 'colher', 'bowl': 'tigela', 'banana': 'banana', 'apple': 'maçã', 
    'sandwich': 'sanduíche', 'orange': 'laranja', 'broccoli': 'brócolis', 'carrot': 'cenoura', 
    'hot dog': 'cachorro-quente', 'pizza': 'pizza', 'donut': 'donut', 'cake': 'bolo', 
    'chair': 'cadeira', 'couch': 'sofá', 'potted plant': 'planta de vaso', 'bed': 'cama', 
    'dining table': 'mesa de jantar', 'toilet': 'vaso sanitário', 'tv': 'tv', 'laptop': 'notebook', 
    'mouse': 'mouse', 'remote': 'controle remoto', 'keyboard': 'teclado', 'cell phone': 'celular', 
    'microwave': 'microondas', 'oven': 'forno', 'toaster': 'torradeira', 'sink': 'pia', 
    'refrigerator': 'geladeira', 'book': 'livro', 'clock': 'relógio', 'vase': 'vaso', 
    'scissors': 'tesoura', 'teddy bear': 'urso de pelúcia', 'hair drier': 'secador de cabelo', 
    'toothbrush': 'escova de dentes'
}

def detectar_imagem(imagem):
    if model is None:
        return None
    return model.predict(source=imagem, conf=0.25, verbose=False)

@bot.command()
async def jogar(ctx):
    if model is None:
        await ctx.send("❌ O modelo IA não foi carregado corretamente no servidor.")
        return

    usuario_id = ctx.author.id

    if usuario_id in jogos_ativos:
        await ctx.send("🎮 Você já está jogando!\nEnvie uma imagem ou use `!parar` para encerrar.")
        return

    jogos_ativos.add(usuario_id)
    pontos[usuario_id] = 0

    await ctx.send(
        "🎯 **BEM-VINDO AO CAÇA AOS OBJETOS!** 🎯\n\n"
        "**Regras:**\n"
        "• O bot pedirá um objeto para você procurar na vida real.\n"
        "• Tire/envie uma foto que contenha o objeto solicitado.\n"
        "• Cada acerto vale 5 pontos.\n"
        "⏱️ Você tem 60 segundos por tentativa!"
    )

    try:
        while True:
            # Pega uma classe em inglês do modelo
            objeto_ing = random.choice(list(model.names.values()))
            # Traduz para português (se não achar no dict, usa o inglês)
            objeto_pt = DICIONARIO_YOLO.get(objeto_ing, objeto_ing)

            await ctx.send(
                f"🔎 **Sua missão:** encontre um(a) **{objeto_pt.upper()}**!\n"
                f"📸 Envie uma imagem neste canal dentro de {TEMPO_ESPERA_IMAGEM}s."
            )

            def verificar_imagem(message):
                return (
                    message.author.id == usuario_id
                    and message.channel.id == ctx.channel.id
                    and len(message.attachments) > 0
                )

            try:
                mensagem = await bot.wait_for("message", timeout=TEMPO_ESPERA_IMAGEM, check=verificar_imagem)
            except asyncio.TimeoutError:
                await ctx.send(f"⏰ Tempo esgotado!\nVocê encerrou com **{pontos.get(usuario_id, 0)} pontos**.")
                break

            anexo = None
            for attachment in mensagem.attachments:
                if attachment.content_type and attachment.content_type.startswith("image/"):
                    anexo = attachment
                    break
                elif attachment.filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                    anexo = attachment
                    break

            if anexo is None:
                await ctx.send("❌ O arquivo enviado não é uma imagem válida. Tente novamente.")
                continue

            await ctx.send("🤖 Analisando imagem...")

            try:
                dados = await anexo.read()
                imagem = Image.open(io.BytesIO(dados)).convert("RGB")
                resultado = await asyncio.to_thread(detectar_imagem, imagem)
            except Exception as erro:
                print("Erro ao processar imagem:", erro)
                await ctx.send("❌ Não consegui processar essa imagem.")
                continue

            encontrou = False
            objetos_detectados_pt = set()

            if resultado:
                primeiro_resultado = resultado[0]
                if primeiro_resultado.boxes is not None:
                    for box in primeiro_resultado.boxes:
                        classe = int(box.cls[0].item())
                        nome_obj_ing = model.names[classe]
                        nome_obj_pt = DICIONARIO_YOLO.get(nome_obj_ing, nome_obj_ing)
                        
                        objetos_detectados_pt.add(nome_obj_pt)
                        
                        if nome_obj_ing.lower() == objeto_ing.lower():
                            encontrou = True

            if encontrou:
                pontos[usuario_id] += PONTOS_POR_ACERTO
                await ctx.send(
                    f"🎉 **PARABÉNS!** Você encontrou: `{objeto_pt}`!\n"
                    f"🏆 Pontuação atual: **{pontos[usuario_id]}**\n\n"
                    "Digite `c` para continuar jogando ou `p` para parar."
                )

                def verificar_escolha(message):
                    return (
                        message.author.id == usuario_id
                        and message.channel.id == ctx.channel.id
                        and message.content.lower().strip() in ["c", "p"]
                    )

                try:
                    escolha = await bot.wait_for("message", timeout=60, check=verificar_escolha)
                except asyncio.TimeoutError:
                    await ctx.send(f"⏰ Tempo esgotado! Pontuação final: **{pontos[usuario_id]}**.")
                    break

                if escolha.content.lower().strip() == "p":
                    await ctx.send(f"🛑 Jogo encerrado! Sua pontuação final foi: **{pontos[usuario_id]}**.")
                    break
            else:
                await ctx.send(f"❌ Não encontrei nenhum(a) `{objeto_pt}` na imagem.")
                if objetos_detectados_pt:
                    await ctx.send(f"🔎 Objetos que eu vi: {', '.join(sorted(objetos_detectados_pt))}")
                else:
                    await ctx.send("🔎 Não consegui reconhecer nenhum objeto claro na foto.")

    finally:
        jogos_ativos.discard(usuario_id)
        pontos.pop(usuario_id, None)

@bot.command()
async def parar(ctx):
    usuario_id = ctx.author.id
    if usuario_id in jogos_ativos:
        pontos.pop(usuario_id, None)
        jogos_ativos.discard(usuario_id)
        await ctx.send("🛑 Jogo de caça aos objetos encerrado.")
    else:
        await ctx.send("Você não está jogando no momento.")

@bot.command()
async def check(ctx):
    if ctx.message.attachments:
        for a in ctx.message.attachments:
            await ctx.send(f"{a.filename}\n{a.url}")
    else:
        await ctx.send("Nenhum arquivo enviado.")


bot.run(TOKEN)