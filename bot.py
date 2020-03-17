#!/usr/bin/env python

import os
import json
from telegram.ext import Updater, CommandHandler

with open('token.json') as f:
  data = json.load(f)
  token = data['token']

def start(update, context):
  update.message.reply_text(
        'Hello {}'.format(update.message.from_user.first_name))


updater = Updater(token, use_context=True)
updater.dispatcher.add_handler(CommandHandler('start', start))
updater.start_polling()
updater.idle()