import asyncio
import os
import sys
from datetime import datetime, timedelta
from time import time, sleep
from pyrogram import Client, idle, filters
from pyrogram.enums import ParseMode, ChatType, ChatMemberStatus
from pyrogram.handlers import MessageHandler, CallbackQueryHandler, ChatMemberUpdatedHandler, ChatJoinRequestHandler
from pyrogram.session.session import Session
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import Database


async def requests_handler(bot, update):
    canali = await db.getCanale(update.chat.id)
    if not canali: return

    t1 = time()
    print("ricevuta request")

    tempo = await db.getTempo(update.chat.id)
    now = datetime.now()
    orario = now + timedelta(minutes=tempo[0])
    futuroMenoOra = orario - now

    secondiDaSleppare = futuroMenoOra.total_seconds()
    asyncio.create_task(accettareq(bot, update, secondiDaSleppare))

    await db.adduser(update.from_user.id)

    print('Ended in:', round(time()-t1, 4), '\n')
    return

async def channel_handler(bot, update):
    old_member = update.old_chat_member
    new_member = update.new_chat_member
    if old_member and not old_member.user.id == DEFAULT_BOT_ID: return
    if new_member and not new_member.user.id == DEFAULT_BOT_ID: return

    evento = "Update sul bot in un canale avvenuto! "
    t1 = time()

    if (not update.old_chat_member or update.old_chat_member.status == ChatMemberStatus.BANNED): # controllo se l'evento è specificamente di aggiunta
        print(evento + "Evento handlato di tipo: Bot aggiunto")
        conto = await db.getChannelsCount(update.from_user.id)
        if conto[0][0]<5 or update.from_user.id in ADMINS:
            tempoAttesa= await db.getDefaultTime(update.from_user.id)
            add = await db.addchannel(update.chat.id, update.from_user.id, tempoAttesa[0])
            try:
                await bot.send_message(update.from_user.id, "✅ Admin: <a href='tg://user?id=" + str(update.from_user.id) + "'>" + update.from_user.first_name + "</a>\nhai aggiunto il bot a un canale: " + update.chat.title + " | <code>"+ str(update.chat.id) + "</code>")
            except Exception as e:
                print(str(e))
        else:
            try:
                await bot.send_message(update.from_user.id, "Hai già aggiunto 5/5 canali, per aggiungerne altri acquista il piano premium.")
            except Exception as e:
                print(str(e))

    elif (not update.new_chat_member or update.new_chat_member.status == ChatMemberStatus.BANNED): # controllo se l'evento è specificamente di rimozione
        print(evento + "Evento handlato di tipo: Bot rimosso") #ovviamente se il bot viene rimosso anche da gente non admin del bot va tolto il canale se no casino
        await db.removechannel(update.chat.id)
        
    else:
        return

    
    print('Ended in:', round(time()-t1, 4), '\n')
    return

async def bot_handler(bot, message, is_callback=False):
    if is_callback:
        original = message
        cbid = original.id
        msgid = original.message.id
        userid = original.from_user.id
        nome = original.from_user.first_name
        try:
            text = str(original.data)
        except: return
        message = message.message

    chatid = message.chat.id

    if not is_callback:
        userid = message.from_user.id
        nome = message.from_user.first_name
        try:
            text = str(message.text)
        except: return

    print('Text: ' + str(text))
    t1 = time()

    if text == '/start':
        add = await db.adduser(userid)
        await db.updateAction('', userid)
        menu = [[{'text': '🗂 Canali', 'callback_data': '/canali'}]]
        menu = await gen_menu(menu)
        defaultTempo = await db.getDefaultTime(userid)
        text = f"👋🏻 <b>Benvenuto <a href='tg://user?id=" + str(userid) + "'>" + str(nome) + f"</a></b>\n\n🤖 @{bot.me.username} ti aiuterà ad accettare automaticamente le richieste di accesso ai tuoi canali senza che tu debba fare nulla! Per cominciare aggiungi semplicemente questo bot.\n\nTempo di accettazione default: <b>{defaultTempo[0]} minuti.</b>\n\n🧑‍💻 Creato da @nukleodev"
        if is_callback:
            await edit(bot, chatid, text, menu, msgid, cbid)
        else:
            await wrap_send_del(bot, chatid, text, menu)

    elif text=="/canali":
        if not is_callback: return
        await db.updateAction('', userid)
        menu=[]
        conto = await db.getChannelsCount(userid)
        maxch = f"{'Unlimited' if userid in ADMINS else '5'}"
        canali = await db.getChannels(userid)
        text= f"<b>🗂 I tuoi canali</b>:\n\n"
        if canali:
            text+=f"🔢 Numero: {conto[0][0]}/{maxch}"
            text+=f"\n\nSeleziona ora il canale che vuoi <b>gestire</b>, per aggiungerne uno nuovo rendimi amministratore in un altro canale."
            for canale in canali:
                info = await bot.get_chat(canale[0])
                menu.append([{'text': info.title, 'callback_data': f'/gestisci{canale[0]}'}])
        else:
            text+="Non hai aggiunto <b>nessun canale</b> al momento, aggiungine uno mettendo questo bot come amministratore in un canale e poi torna qui"
        menu.append([{'text': '⬅️ Indietro', 'callback_data': '/start'}])
        menu = await gen_menu(menu)
        await edit(bot, chatid, text, menu, msgid, cbid)

    elif text.startswith('/gestisci'):
        if not is_callback: return
        await db.updateAction('', userid)
        canale = text.replace('/gestisci', '')
        info = await bot.get_chat(canale)
        tempo = await db.getTempo(canale)
        text=f"📢 | {info.title}\n\n⏳ Tempo accettazione: {tempo[0]} minuti\n\nPremi il bottone qua sotto per modificare il tempo di accettazione."
        menu = [[{'text': '⏱ Imposta tempo', 'callback_data': f'/modificatempo{canale}'}],[{'text': '⬅️ Indietro', 'callback_data': '/canali'}]]
        menu = await gen_menu(menu)
        await edit(bot, chatid, text, menu, msgid, cbid)


    elif text.startswith('/modificatempo'):
        if not is_callback: return
        canale = text.replace('/modificatempo', '')
        await db.updateAction('nuovoTempo'+ str(canale), userid)
        text = "⏱ Scrivi il numero di minuti da attendere per l'approvazione delle richieste d'ingresso al canale\nMinimo 0 Massimo 1440 (24 ore)"
        menu = [
            [
                {'text': '🔙 Back', 'callback_data': f'/gestisci{canale}'},
            ]
        ]
        menu = await gen_menu(menu)
        await edit(bot, chatid, text, menu, msgid, cbid)


    elif text.startswith('/time'):
        await db.updateAction('', userid)
        splitText = text.split()
        if len(splitText)!=2:
            text="👎 Il comando si usa così: <code>/time x</code>, dove x sono i minuti di attesa che vuoi avere di default a ogni canale"
        else:
            minutesTime=text.split()[1]
            await db.updateDefaultTime(minutesTime, userid)
            text="👍 Tempo di default aggiornato con successo a "+minutesTime+" minuti."

        menu = [[{'text': '🔙 Back', 'callback_data': '/start'},]]
        menu = await gen_menu(menu)
        await wrap_send_del(bot, chatid, text, menu)


    elif not text.startswith('/'):
        act = await db.getAction(userid)
        act = act[0]
        if act == "":
            await bot.send_message(chatid, "Premi /start per cominciare")
        if act.startswith('nuovoTempo'):
            canale=act.replace('nuovoTempo', '')
            try:
                minuti = int(text)
                if 0 <= minuti <= 1440:
                    await db.updateTempo(minuti, canale)
                    await db.updateAction('', userid)
                    await bot.send_message(chatid, "Minuti aggiornati con successo, premi /start o il bottone back qui sopra per tornare indietro")
                else:
                    await bot.send_message(chatid, "Minuti non validi assicurati che il valore sia compreso tra 0 e 1440, premi /start se vuoi tornare indietro")    
            except:
                await bot.send_message(chatid, "Minuti non validi, assicurati di inserire un valore numerico intero, premi /start se vuoi annullare")

    print('Ended in:', round(time()-t1, 4), '\n')
    return


async def mandaPost(bot, chat_to, chat_from, msg_id):
    try:
        await bot.copy_message(chat_id=chat_to,from_chat_id=chat_from, message_id=msg_id)
    except Exception as e:
        print(str(e))

async def accettareq(bot, update, tempo):
    await asyncio.sleep(tempo)
    try:
        await bot.approve_chat_join_request(update.chat.id, update.from_user.id)
    except:
        pass
    return

async def pyro(token):
    Session.notice_displayed = True

    API_HASH = ''
    API_ID = ''

    bot_id = str(token).split(':')[0]
    app = Client(
        'sessioni/session_bot' + str(bot_id),
        api_hash=API_HASH,
        api_id=API_ID,
        bot_token=token,
        workers=20,
        sleep_threshold=30
    )
    return app

async def gen_menu(menu):
    menu = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=y['text'], callback_data=y['callback_data']) for y in x] for x in menu])
    return menu


async def edit(client, chat_id, text=False, menu=False, msg_id=False, cb_id=False, not_text=False):

    if msg_id:
        try:
            await client.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                reply_markup=menu
            )
        except:
            pass

    if cb_id:
        try:
            await client.answer_callback_query(
                callback_query_id=cb_id,
                text=not_text
            )
        except:
            pass


async def wrap_send_del(bot: Client, chatid: int, text: str, menu: InlineKeyboardMarkup):
    delete=await db.getLastmsg(chatid)
    delete=delete[0]
    if int(delete) != 0:
        try:
            await bot.delete_messages(chatid, int(delete))
        except:
            pass
    try:
        send = await bot.send_message(chatid, text, reply_markup=menu)
        await db.updateLastmsg(send.id, chatid)
    except Exception as e:
        print("EXC in wrap_send_del:", e)



async def update_handler_cb(bot, message):
    await bot_handler(bot, message, True)

async def main():
    print(f'Genero session > ', end='')
    SESSION = await pyro(token=TOKEN)
    HANDLERS = {
        'msg': MessageHandler(bot_handler, filters.private),
        'call': CallbackQueryHandler(update_handler_cb),
        'channel': ChatMemberUpdatedHandler(channel_handler),
        'requests': ChatJoinRequestHandler(requests_handler)
    }
    SESSION.add_handler(HANDLERS['msg'])
    SESSION.add_handler(HANDLERS['call'])
    SESSION.add_handler(HANDLERS['channel'])
    SESSION.add_handler(HANDLERS['requests'])


    print('avvio > ', end='')
    await SESSION.start()

    print('avviati!')
    await idle()

    print('Stopping > ', end='')
    await SESSION.stop()

    await db.close()
    loop.stop()
    print('stopped!\n')
    exit()

if __name__ == '__main__':
    canaleLog=0 #log channel id here
    ADMINS = [1780793442]
    TOKEN = ''
    DEFAULT_BOT_ID = int(TOKEN.split(':')[0])
    loop = asyncio.get_event_loop()
    db = Database(loop=loop)
    loop.run_until_complete(main())
    exit()