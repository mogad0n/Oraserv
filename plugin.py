###
# Copyright (c) 2020, mogad0n
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

from supybot import utils, plugins, ircutils, callbacks, irclib, ircmsgs, conf, world, log
from supybot.commands import *
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('Oraserv')
except ImportError:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x: x

import pickle
import sys

filename = conf.supybot.directories.data.dirize("Oraserv.db")

class Oraserv(callbacks.Plugin):
    """Suite of tools to interact with oragonoIRCd"""

    _whois = {}

    def __init__(self, irc):
        self.__parent = super(Oraserv, self)
        self.__parent.__init__(irc)
        self.db = {}
        self._loadDb()
        world.flushers.append(self._flushDb)

    def _loadDb(self):
        """Loads the (flatfile) database mapping nicks to masks."""

        try:
            with open(filename, "rb") as f:
                self.db = pickle.load(f)
        except Exception as e:
            self.log.debug("Oraserv: Unable to load pickled database: %s", e)

    def _flushDb(self):
        """Flushes the (flatfile) database mapping nicks to masks."""

        try:
            with open(filename, "wb") as f:
                pickle.dump(self.db, f, 2)
        except Exception as e:
            self.log.warning("Oraserv: Unable to write pickled database: %s", e)

    def die(self):
        self._flushDb()
        world.flushers.remove(self._flushDb)
        self.__parent.die()

    ###
    # Oper commands
    ###

    @wrap(['nick', optional('something')])
    def kill(self, irc, msg, args, nick, reason):
        """<nick> [<reason>]

        Issues a KILL command on the <nick> with <reason> if provided.
        """
        arg = [nick]
        if reason:
            arg.append(reason)
        irc.queueMsg(msg=ircmsgs.IrcMsg(command='KILL',
                    args=arg))
        irc.replySuccess(f'Killed connection for {nick}')



    @wrap(['validChannel', 'something', optional('something')])
    def renamechan(self, irc, msg, args, channel, newname, reason):
        """<channel> <newname> [<reason>]

        Renames the given <channel> with the given <reason>, if provided.
        <newname> must begin with a '#'
        """
        if newname[0] != '#':
            irc.error('Invalid channel name')
        else:
            arg = [channel, newname]
            if reason:
                arg.append(reason)
            irc.queueMsg(msg=ircmsgs.IrcMsg(command='RENAME',
                            args=arg))
            irc.replySuccess(f'Renaming {channel} to {newname}')



    @wrap([getopts({'nick': 'nick'}), many('validChannel')])
    def sajoin(self, irc, msg, args, opts. channel):
        """[--nick <nick>] <channel> .. [<channel>]

        Forcibly joins a user to a channel, ignoring restrictions like bans, user limits
        and channel keys. If <nick> is omitted, it defaults to the bot itself.
        """
        opts = dict(opts)
        arg = []
        if 'nick' in opts:
            arg = [opts['nick']]
        for chans in channel:
            arg.append[channel]
        irc.queueMsg(msg=ircmsgs.IrcMsg(command='SAJOIN',
                            args=arg))
        if 'nick' in opts:
            re = f'attempting to force join {opts} to {channel}'
        else:
            re = f'I am attempting to forcibly join {channel}'
        irc.reply(re)


    @wrap(['nick', 'something'])
    def sanick(self, irc, msg, args, current, new):
        """<current><new>

        Issues a SANICK command and forcibly changes the <current> nick to the <new> nick
        """
        arg = [current, new]
        irc.queueMsg(msg=ircmsgs.IrcMsg(command='SANICK',
                            args=arg))
        irc.reply(f'Attempting forced nick change for {current}')



    @wrap([getopts({'duration': 'something'}), 'nick', optional('something')])
    def nban(self, irc, msg, args, opts, nick, reason):
        """[--duration <duration>] <nick> [<reason>]

        will add a KLINE for the host associated with <nick> and also KILL the connection.
        If <nick> is registered it will suspend the respective account
        <duration> is of the format '1y 12mo 31d 10h 8m 13s'
        not adding a <duration> will add a permanent KLINE
        <reason> is optional as well.
        """

        opts = dict(opts)

        label = ircutils.makeLabel()
        try:
            (nick, ident, host) = ircutils.splitHostmask(irc.state.nickToHostmask(nick))
            bannable_host = '*!*@' + host
            bannable_ih = f'*!{ident}@{host}'
        except KeyError:
            irc.error(
                "No such nick",
                Raise=True,
            )

        # Registered Nicks
        # Implement do330 and RPL_WHOISOPERATOR instead
        if host == 'irc.liberta.casa':
            irc.queueMsg(msg=ircmsgs.IrcMsg(command='NS',
                        args=('SUSPEND', nick), server_tags={"label": label}))
            irc.reply(f'Suspending account for {nick} Note: <duration> and'
                    ' <reason> are currently not applicable here and will be ignored')
            self.db[nick] = 'suspended'

        # Discord Nicks
        # Workaround for hardcoded host values.
        elif host == '4b4hvj35u73k4.liberta.casa' or host == 'gfvnhk5qj5qaq.liberta.casa' or host == 'fescuzdjai52n.liberta.casa':
            arg = ['ANDKILL']
            if 'duration' in opts:
                arg.append(opts['duration'])
            arg.append(bannable_ih)
            if reason:
                arg.append(reason)
            irc.queueMsg(msg=ircmsgs.IrcMsg(command='KLINE',
                         args=arg, server_tags={"label": label}))
            irc.reply(f'Adding a KLINE for discord user: {bannable_ih}')
            self.db[nick] = bannable_ih

        # Unregistered Nicks
        else:
            arg = ['ANDKILL']
            if 'duration' in opts:
                arg.append(opts['duration'])
            arg.append(bannable_host)
            if reason:
                arg.append(reason)
            irc.queueMsg(msg=ircmsgs.IrcMsg(command='KLINE',
                        args=arg, server_tags={"label": label}))
            irc.reply(f'Adding a KLINE for unregistered user: {bannable_host}')
            self.db[nick] = bannable_host

    def nunban(self, irc, msg, args, nick):
        """<nick>
        If found, will unban mask/account associated with <nick>
        """
        label = ircutils.makeLabel()

        if nick not in self.db:
            irc.error(f'There are no bans associated with {nick}')
        else:
            if self.db[nick] == 'suspended':
                irc.queueMsg(msg=ircmsgs.IrcMsg(command='NS',
                            args=('UNSUSPEND', nick), server_tags={"label": label}))
                irc.reply(f'Enabling suspended account {nick}')
                self.db.pop(nick)
            else:
                irc.queueMsg(msg=ircmsgs.IrcMsg(command='UNKLINE',
                            args=('', self.db[nick]), server_tags={"label": label}))
                irc.reply(f'Removing KLINE for {self.db[nick]}')
                self.db.pop(nick)

    nunban = wrap(nunban, ['something'])

    def nbanlist(self, irc, msg, args):
        """This command takes no arguments

        Displays a list of masks/accounts banned or suspended respectively
        Currently only lists masks/accounts and not expiry and reason. Can be heavy use wisely
        """
        for nick in self.db:
            arg = self.db[nick]
            irc.reply(f'{nick}  denied as {arg}')
    nbanlist = wrap(nbanlist)

    ###
    # Chanserv commands
    ###
    @wrap(['channel', 'something', many('nick')])
    def automode(self, irc, msg, args, channel, mode, nicks):
        """[<channel>] <mode> <nick> [<nick>....]

        set's amode <mode> on given <nick>/<nicks> for <channel>
        The nick/nicks must be registered and <mode> must be (de)voice, (de)halfop or (de)op
        """
        # label = ircutils.makeLabel()

        if mode == 'voice':
            flag = '+v'
        elif mode == 'halfop':
            flag = '+h'
        elif mode == 'op':
            flag = '+o'
        elif mode == 'devoice':
            flag = '-v'
        elif mode == 'dehalfop':
            flag = '-h'
        elif mode == 'deop':
            flag = '-o'
        else:
            irc.error(f'Supplied mode {mode} is not allowed/valid')
            return

        for nick in nicks:
            irc.queueMsg(msg=ircmsgs.IrcMsg(command='PRIVMSG',
                            args=('chanserv', f'amode {channel} {flag} {nick}')))
        irc.replySuccess(f'Setting mode {flag} on given nick(s), if nick(s) weren\'t given the {flag} mode it/they are unregistered')

    @wrap([many('channel')])
    def chanreg(self, irc, msg, args, channels):
        """[<channel>].. [<channel>..]

        Registered the given channel/s by the bot
        """

        for channel in channels:
            arg = ['register']
            arg.append(channel)
            irc.queueMsg(msg=ircmsgs.IrcMsg(command='CS', args=arg))
        irc.reply('Registered the channel(s) successfully')



    @wrap(['channel', 'something'])
    def chanpurge(self, irc, msg, args, channel, reason):
        """[<channel>] <reason>

        Purges the given <channel> and blacklists it on the ircd
        making a note of the <reason>.
        <channel> is only necessary if the message is not sent on the channel itself
        """
        arg = ['PURGE']
        arg.append(channel)
        if reason:
            arg.append(reason)
        irc.queueMsg(msg=ircmsgs.IrcMsg(command='CS',
                            args=arg))
        irc.replySuccess(f'Purging channel {channel} {reason or ""}')

    @wrap(['validChannel'])
    def chanunpurge(self, irc, msg, args, channel):
        """<channel>

        unpurges the given <channel> and restores it's status on the ircd
        """
        arg = ['UNPURGE']
        arg.append(channel)
        irc.queueMsg(msg=ircmsgs.IrcMsg(command='CS',
                            args=arg))
        irc.replySuccess(f'Restoring channel {channel} to an unpurged state')


    @wrap(['channel',('literal', ('users', 'access'))])
    def chanreset(self, irc, msg, args, channel, target):
        """[<channel>] <target>

        <target> can either be 'users' (kicks all users except the bot)
        or 'access' (resets all stored bans, invites, ban exceptions,
        and persistent user-mode grants) for <channel>.
        <channel> is only necessary if the message is not sent on the channel itself
        """
        arg = ['CLEAR']
        arg.append(channel)
        arg.append(target)
        irc.queueMsg(msg=ircmsgs.IrcMsg(command='CS',
                            args=arg))
        if target == 'users':
            irc.reply(f'Kicking all users out of {channel} besides me')
        else:
            irc.reply(f'Resetting bans and privileges for {channel}')
    @wrap(['channel'])

    ###
    # Hostserv commands
    ###

    @wrap(['nick', 'something'])
    def setvhost(self, irc, msg, args, nick, vhost):
        """<nick> <vhost>

        sets a <nick>'s vhost, bypassing the request system.
        """
        arg = ['SET', nick, vhost]
        irc.queueMsg(msg=ircmsgs.IrcMsg(command='HS',
                    args=arg))
        irc.replySuccess(f'Killed connection for {nick}')



Class = Oraserv


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
