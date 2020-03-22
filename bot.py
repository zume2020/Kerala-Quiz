#!/usr/bin/env python

# -------------------------------------------------------------
# Kerala Quiz - A Telegram Bot for playing quiz in communities.
# @author: Sumithran a.k.a zume
# @github: https://github.com/zume2020
# license: MIT
# -------------------------------------------------------------

import logging
import json
import requests
import config
import re
import html

from time import sleep
from telegram import ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, run_async

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger("QUIZ")

logger.info("Starting Engine!")
updater = Updater(config.TOKEN, use_context=True)
dp = updater.dispatcher
logger.info("Successfully started!")


# Number of Questions/Rounds per Session
PER_SESSION_ROUND = 5
# Time between hints
PER_HINT_TIME = 12
# Maximum number of hints + 2 (Q+M)
MAX_HINT = 6

# URI to grab 1 Question each
# TODO Create categories
API_URI = "https://opentdb.com/api.php?amount=1&type=multiple"


def start(update, context):
    update.message.reply_text(
        f"Hi {update.effective_user.first_name}! Use /quiz to start quiz")


def send_quiz(context):
    """Send the alarm message."""

    job = context.job
    chat_id = job.context[0]
    chat_data = job.context[1]
    score = chat_data["score"]

    for i in range(1, PER_SESSION_ROUND + 1):
        data = requests.get(API_URI).json()["results"][0]

        question = chat_data["question"] = html.unescape(data["question"])
        answer = chat_data["answer"] = html.unescape(data["correct_answer"])
        category = chat_data["category"] = html.unescape(data["category"])

        chat_data["answered"] = False

        hints = MAX_HINT
        if len(answer) < MAX_HINT:
            hints = len(answer)+1

        for x in range(hints):
            if chat_data["answered"] == False:
                hint = ""
                if x == hints-1:
                    del chat_data["answer"]
                    context.bot.send_message(chat_id,
                                             text=f"⛔️ Nobody guessed, Correct answer was *{answer}*",
                                             parse_mode=ParseMode.MARKDOWN)
                    break
                elif x > 0:
                    # TODO Improve hint
                    hint = "_Hint:_ {}".format(answer[-x:])

                context.bot.send_message(chat_id,
                                         text=f"❓*QUESTION* _[{category}]_ \n\n{question}\n\n{hint}",
                                         parse_mode=ParseMode.MARKDOWN)

                sleep(PER_HINT_TIME)
            else:
                break

    # TODO Improve rank list
    score_message = "*Rank List:*\n\n"
    sorted_score = sorted(score.items(), key=lambda x: x[1])
    for k, v in sorted_score:
        score_message += f"{k} - `{v}`\n"

    if score_message != "*Rank List:*\n\n":
        context.bot.send_message(chat_id, text=score_message,
                                 parse_mode=ParseMode.MARKDOWN)
    job.schedule_removal()
    chat_data.clear()


def set_quiz(update, context):
    chat_id = update.effective_chat.id
    try:
        # Add job to queue and stop current one if there is a timer already
        update.message.reply_text(
            '🏁 *Round Starts*!', parse_mode=ParseMode.MARKDOWN)

        context.chat_data["score"] = {}

        if 'job' in context.chat_data:
            old_job = context.chat_data['job']
            old_job.schedule_removal()
        new_job = context.job_queue.run_repeating(
            send_quiz, 2, context=(chat_id, context.chat_data))
        context.chat_data['job'] = new_job

    except (IndexError, ValueError):
        update.message.reply_text('error')


def unset(update, context):
    """Remove the job if the user changed their mind."""
    if 'job' not in context.chat_data:
        update.message.reply_text('You have no active quiZZzZes!')
        return

    job = context.chat_data['job']
    job.schedule_removal()
    context.chat_data.clear()

    update.message.reply_text('✋ *Stopped*!', parse_mode=ParseMode.MARKDOWN)


def check(update, context):
    answer = context.chat_data["answer"]
    if update.message.text.lower() == answer.lower():
        context.chat_data["answered"] = True
        del context.chat_data["answer"]
        score = context.chat_data["score"]
        f_name = update.effective_user.first_name
        answer_result = "🍀 Yes, *{}*!\n\n🏆 {} +1".format(answer, f_name)
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=answer_result,
                                 parse_mode=ParseMode.MARKDOWN)

        if f_name in score:
            score[f_name] += 1
        else:
            score[f_name] = 1


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    """Run bot."""
    dp.add_handler(CommandHandler("start", start, Filters.private))
    dp.add_handler(CommandHandler("help", start))
    dp.add_handler(CommandHandler("quiz", set_quiz))
    dp.add_handler(CommandHandler("stop", unset))
    dp.add_handler(MessageHandler(Filters.text, check))
    dp.add_error_handler(error)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
