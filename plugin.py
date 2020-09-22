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

from supybot import utils, plugins, ircutils, callbacks, irclib, ircmsgs
from supybot.commands import *
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('Oraserv')
except ImportError:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x: x

banned_dict = {}

class Oraserv(callbacks.Plugin):
    """Suite of tools to interact with oragonoIRCd"""

    @wrap(['nick', optional('something'), optional('something')])
    def nban(self, irc, msg, args, nick, duration , reason):
        """<nick> <duration> <reason>

        will add a KLINE for the host associated with <nick> and also KILL the connection.
        If <nick> is registered it will suspend the respective account
        <duration> is of the format '1y 12mo 31d 10h 8m 13s'
        not adding a <duration> will add a permanent KLINE
        <reason> is optional as well.
        """
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
            banned_dict[nick] = 'suspended'

        # Discord Nicks
        # Workaround for hardcoded host values.
        elif host == '4b4hvj35u73k4.liberta.casa' or host == 'gfvnhk5qj5qaq.liberta.casa' or host == 'fescuzdjai52n.liberta.casa':
            arg = ['ANDKILL']
            if duration:
                arg.append(duration)
            arg.append(bannable_ih)
            if reason:
                arg.append(reason)
            irc.queueMsg(msg=ircmsgs.IrcMsg(command='KLINE',
                         args=arg, server_tags={"label": label}))
            irc.reply(f'Adding a KLINE for discord user: {bannable_ih}')
            banned_dict[nick] = bannable_ih

        # Unregistered Nicks
        else:
            arg = ['ANDKILL']
            if duration:
                arg.append(duration)
            arg.append(bannable_host)
            if reason:
                arg.append(reason)
            irc.queueMsg(msg=ircmsgs.IrcMsg(command='KLINE',
                        args=arg, server_tags={"label": label}))
            irc.reply(f'Adding a KLINE for unregistered user: {bannable_host}')
            banned_dict[nick] = bannable_host

    def nunban(self, irc, msg, args, nick):
        """<nick>

        If found, will unban mask/account associated with <nick>
        """
        label = ircutils.makeLabel()

        # This shouldn't survive restarts so need db?
        if banned_dict[nick] is None:
            irc.error(f'There are no bans associated with {nick}')
        else:
            if banned_dict[nick] == 'suspended':
                irc.queueMsg(msg=ircmsgs.IrcMsg(command='NS',
                            args=('UNSUSPEND', nick), server_tags={"label": label}))
                irc.reply(f'Enabling suspended account {nick}')
                banned_dict.pop(nick)
            else:
                irc.queueMsg(msg=ircmsgs.IrcMsg(command='UNKLINE',
                            args=('', banned_dict[nick]), server_tags={"label": label}))
                irc.reply(f'Removing KLINE for {banned_dict[nick]}')
                banned_dict.pop(nick)

    nunban = wrap(nunban, ['something'])


Class = Oraserv


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

