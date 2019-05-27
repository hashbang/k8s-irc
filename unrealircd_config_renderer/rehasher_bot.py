import pydle


class RehasherBot(pydle.Client):
    def __init__(self, *args, oper_user, oper_credentials, **kwargs):
        super(pydle.Client, self).__init__(*args, **kwargs)
        self.oper_user = oper_user
        self.oper_credentials = oper_credentials

    async def oper(self, user, password):
        await self.rawmsg("OPER", user, password)

    async def rehash(self):
        await self.rawmsg("REHASH")

    async def on_connect(self):
        await super().on_connect()
        await self.oper(self.oper_user, self.oper_credentials)
        await self.rehash()
        await self.disconnect()
