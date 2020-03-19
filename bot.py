#!/usr/bin/env python

import logging
import json
import requests
import random
from telegram.ext import Updater, CommandHandler
from telegram.ext import MessageHandler, Filters

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

url = 'https://opentdb.com/api.php?amount=10&category=22&difficulty=easy&type=multiple'

print("starting engine.")
r = requests.get(url)
j = r.json()

global pool

def start(update, context):
    update.message.reply_text('Hi! Use /quiz to start quiz')


def alarm(context):
    """Send the alarm message."""
    global answer
    global category

    pool = j['results']
    # print(pool)
    random.shuffle(pool)

    try:
        x = pool.pop()
        question = x['question']
        answer   = x['correct_answer'].lower()
        category = x['category']

        print("answer from alarm ",answer)

        job = context.job
        context.bot.send_message(job.context, text=question)

    except IndexError as e:
        update.message.reply_text('quis ends')



def set_timer(update, context):
    """Add a job to the queue."""
    chat_id = update.message.chat_id
    try:
        # Add job to queue and stop current one if there is a timer already
        update.message.reply_text('round starts!')

        if 'job' in context.chat_data:
            old_job = context.chat_data['job']
            old_job.schedule_removal()
        new_job = context.job_queue.run_repeating(alarm, 15, context=chat_id)
        context.chat_data['job'] = new_job

        update.message.reply_text('question!')

    except (IndexError, ValueError):
        update.message.reply_text('Usage: /set <seconds>')


def unset(update, context):
    """Remove the job if the user changed their mind."""
    if 'job' not in context.chat_data:
        update.message.reply_text('You have no active quizes')
        return

    job = context.chat_data['job']
    job.schedule_removal()
    del context.chat_data['job']

    update.message.reply_text('cancelled!')

def check(update, context):
    print("answer in check ", update.message.text)
    if update.message.text.lower() == answer:
        context.bot.send_message(chat_id=update.effective_chat.id, text="correct answer")

def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    """Run bot."""
    updater = Updater("1009736867:AAGOKj8i4ru2J299gpRerAVaO88bOsbV3R0", use_context=True)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", start))
    dp.add_handler(CommandHandler("set", set_timer,
                                  pass_args=True,
                                  pass_job_queue=True,
                                  pass_chat_data=True))
    dp.add_handler(CommandHandler("unset", unset, pass_chat_data=True))

    dp.add_handler(MessageHandler(Filters.text, check))

    dp.add_error_handler(error)

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()