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
            hostmask = irc.state.nickToHostmask(nick)
            host = hostmask.split("@")[1]
            bannable_host = f'*!*@{host}'
            ih = hostmask.split("!")[1]
            bannable_ih = f'*!{ih}'
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

    @wrap(['nick', 'something'])
    def sanick(self, irc, msg, args, current, new):
        """<current><new>

        Issues a SANICK command and forcibly changes the <current> nick to the <new> nick
        """
        arg = [current, new]
        irc.queueMsg(msg=ircmsgs.IrcMsg(command='SANICK',
                            args=arg))
        irc.reply(f'Attempting forced nick change for {current}')


Class = Oraserv


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
