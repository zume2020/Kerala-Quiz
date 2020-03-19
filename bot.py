#!/usr/bin/env python

import logging
import json
import requests
import random
from time import sleep
from telegram.ext import Updater, CommandHandler
from telegram.ext import MessageHandler, Filters

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

url = 'https://opentdb.com/api.php?amount=5&category=22&difficulty=easy&type=multiple'

print("starting engine.")
r = requests.get(url)
j = r.json()

global pool
global delay_flag


correct_answer = 0
delay_flag = 0

def start(update, context):
    update.message.reply_text('Hi {}! Use /quiz to start quiz'.format(update.message.chat.first_name))


def send_quiz(context):
    """Send the alarm message."""
    global answer
    global category
    global correct_answer
    
    pool = j['results']
    # print(pool)
    random.shuffle(pool)

    try:
        x = pool.pop()


        question = x['question']
        answer   = x['correct_answer'].lower()
        category = x['category']

        print(answer)

        job = context.job


        qLoop = 0
        

        for x in range(4):
            if correct_answer == 0:
                if x > 0:
                    hint = "Hint: {}".format(answer[-x:])
                    print(hint)
                else:
                    hint = ""

                q_message = "{} \n{} \n{}".format(category,question,hint)
                context.bot.send_message(job.context, text=q_message)
                sleep(12)
            else:
                print("Correct answer triggered")

        correct_answer = 0 #check this

    except IndexError as e:
        job = context.job
        context.bot.send_message(job.context, text="stoped")
        job.schedule_removal()




def set_quiz(update, context):

    chat_id = update.message.chat_id
    try:
        # Add job to queue and stop current one if there is a timer already
        update.message.reply_text('round starts!')

        if 'job' in context.chat_data:
            old_job = context.chat_data['job']
            old_job.schedule_removal()
        new_job = context.job_queue.run_repeating(send_quiz, 2, context=chat_id)
        context.chat_data['job'] = new_job
        # update.message.reply_text('question!')


    except (IndexError, ValueError):
        update.message.reply_text('error')


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
    if update.message.text.lower() == answer:
        global correct_answer
        correct_answer = 1
        answer_result = "Correct answer: {}\n{}".format(answer,update.message.chat.first_name)
        context.bot.send_message(chat_id=update.effective_chat.id, text=answer_result)

def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def getToken():
    with open('token.json') as f:
        data = json.load(f)
        token = data['token']
    return token

def main():
    """Run bot."""

    updater = Updater(getToken(), use_context=True)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", start))
    dp.add_handler(CommandHandler("quiz", set_quiz,
                                  pass_args=True,
                                  pass_job_queue=True,
                                  pass_chat_data=True))
    dp.add_handler(CommandHandler("stop", unset, pass_chat_data=True))

    dp.add_handler(MessageHandler(Filters.text, check))

    dp.add_error_handler(error)

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()