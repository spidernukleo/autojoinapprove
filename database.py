import asyncio
import aiosqlite


class Database:
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.conn, self.loop = None, loop
        self.test_mode = False  # Set to True to print while testing



    # CONNESSIONI E GESTIONI BASSO LIVELLO
    async def connect(self):
        self.conn = await aiosqlite.connect('data/maindb.db', loop=self.loop)
        await self.execute("CREATE TABLE IF NOT EXISTS users (`ID` INTEGER PRIMARY KEY AUTOINCREMENT , `chat_id` BIGINT(15) NOT NULL, `lastmsg` INT(8) DEFAULT 0, `defaultTime` INTEGER DEFAULT 2, `action` VARCHAR(100) NULL DEFAULT NULL);", [], commit=True)
        await self.execute("CREATE TABLE IF NOT EXISTS channels (`ID` INTEGER PRIMARY KEY AUTOINCREMENT , `chat_id` BIGINT(15) NOT NULL, `tempoAttesa` INTEGER, `welcomePost` VARCHAR, `userid` BIGINT);", [], commit=True)
        return self.conn

    async def execute(self, sql: str, values: tuple, commit: bool = False, fetch: int = 0):
        # If no connection is established, connect
        if not self.conn:
            await self.connect()
            await asyncio.sleep(0.1)

        # Test mode, print sql and values
        if self.test_mode:
            print(sql, values)

        # Execute the query
        try:
            cursor = await self.conn.cursor()
        except aiosqlite.ProgrammingError:
            await self.connect()
            cursor = await self.conn.cursor()

        try:
            executed = await cursor.execute(sql, values)
        except aiosqlite.ProgrammingError:
            await self.connect()
            executed = await cursor.execute(sql, values)


        # If fetch is True, return the result
        fetch = await cursor.fetchone() if fetch == 1 else cursor.rowcount if fetch == 2 else await cursor.fetchall() if fetch == 3 else None


        # Commit Db
        if commit:
            await self.conn.commit()

        return fetch

    async def close(self):
        if self.conn:
            await self.conn.close()



    # GESTIONE INSERIMENTI | ELIMINAZIONI
    async def adduser(self, chat_id: int):
        fc = await self.execute('SELECT * FROM users WHERE chat_id = ?', (chat_id,), fetch=1)
        if not fc:
            await self.execute('INSERT INTO users (chat_id) VALUES (?)', (chat_id,), commit=True)
        return True if not fc else False
    
    async def addchannel(self, chat_id: int, userid: int, time):
        fc = await self.execute('SELECT * FROM channels WHERE chat_id = ?', (chat_id,), fetch=1)
        if not fc:
            await self.execute('INSERT INTO channels (chat_id, userid, tempoAttesa) VALUES (?, ?, ?)', (chat_id, userid, time), commit=True)
        return True if not fc else False

    async def removechannel(self, chat_id: int):
        fc = await self.execute('SELECT * FROM channels WHERE chat_id = ?', (chat_id,), fetch=1)
        if fc:
            await self.execute('DELETE FROM channels WHERE chat_id= ?', (chat_id,), commit=True)
        return True if fc else False

    async def getChannels(self, userid):
        return await self.execute('SELECT chat_id FROM channels WHERE userid= ?', (userid, ), fetch=3)

    async def getChannelsCount(self, userid):
        return await self.execute('SELECT COUNT(*) FROM channels WHERE userid= ?', (userid, ), fetch=3)

    async def getChannelCheckAdmin(self, chat_id, userid):
        return await self.execute('SELECT chat_id FROM channels WHERE userid= ? AND chat_id = ?', (userid, chat_id,), fetch=1)
    
    async def getCanale(self, chat_id: int):
        return await self.execute('SELECT chat_id FROM channels WHERE chat_id = ?', (chat_id,), fetch=1)



    # WRAPPER GET

    async def getLastmsg(self, chat_id: int):
        return await self.execute('SELECT lastmsg FROM users WHERE chat_id = ?', (chat_id,), fetch=1)

    async def getDaBannare(self, chat_id: int):
        return await self.execute('SELECT daBannare FROM users WHERE chat_id = ?', (chat_id,), fetch=1)

    async def getTempo(self, chat_id: int):
        return await self.execute('SELECT tempoAttesa FROM channels WHERE chat_id = ?', (chat_id,), fetch=1)
    
    async def getWelcome(self, chat_id: int):
        return await self.execute('SELECT welcomePost FROM channels WHERE chat_id = ?', (chat_id,), fetch=1)

    async def getDefaultTime(self, userid):
        return await self.execute('SELECT defaultTime FROM users WHERE chat_id = ?', (userid,), fetch=1)

    async def getUsers(self):
        return await self.execute('SELECT chat_id FROM users', (), fetch=3)

    # WRAPPER UPDATE

    async def updateLastmsg(self, lastmsg: int, chat_id: int):
        await self.execute('UPDATE users SET lastmsg = ? WHERE chat_id = ?', (lastmsg, chat_id, ), commit=True)

    async def updateTempo(self, nuoveOre: int, chat_id: int):
        await self.execute('UPDATE channels SET tempoAttesa = ? WHERE chat_id= ?', (nuoveOre, chat_id,), commit=True)

    async def updateWelcome(self, nuovoWelcome: int, chat_id: int):
        await self.execute('UPDATE channels SET welcomePost = ? WHERE chat_id = ?', (nuovoWelcome, chat_id,), commit=True)

    async def updateDefaultTime(self, nuovoTime: int, chat_id: int):
        await self.execute('UPDATE users SET defaultTime = ? WHERE chat_id = ?', (nuovoTime, chat_id,), commit=True)
    

    async def totcanali(self):
        return await self.execute('SELECT COUNT(*) FROM channels', [], fetch=3)

    async def totusers(self):
        return await self.execute('SELECT COUNT(*) FROM users', [], fetch=3)


    async def updateAction(self, action: str, chat_id: int):
        await self.execute('UPDATE users SET action = ? WHERE chat_id = ?', (action, chat_id, ), commit=True)

    async def getAction(self, chat_id: int):
        return await self.execute('SELECT action FROM users WHERE chat_id = ?', (chat_id,), fetch=1)
