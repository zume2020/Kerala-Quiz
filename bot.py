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
import datetime

from time import sleep
from hint import hintGen
from telegram import ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, run_async, CallbackQueryHandler
from telegram.utils.helpers import escape_markdown
from database import get_total_table, get_week_table, inc_or_new_user

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
MAX_HINT = 5
# Keys per line in Categories
PER_LINE_KEYS = 3
# Trophy icons for Leaderboard
TROPHY_ICONS = ["🥇", "🥈", "🥉"]

# Categories
CATEGORIES = {
    "General Knowledge": 9,
    "Books": 10,
    "Films": 11,
    "Music": 12,
    "Television": 14,
    "Video Games": 15,
    "Board Games": 16,
    "Science & Nature": 17,
    "Computers": 18,
    "Mathematics": 19,
    "Mythology": 20,
    "Sports": 21,
    "Geography": 22,
    "History": 23,
    "Politics": 24,
    "Art": 25,
    "Celebrities": 26,
    "Animals": 27
}

CATEGORIES_KEYBOARD = []
count = 0
temp = []
for item in CATEGORIES:
    count += 1
    temp.append(InlineKeyboardButton(item, callback_data=CATEGORIES[item]))
    if count % PER_LINE_KEYS == 0:
        CATEGORIES_KEYBOARD.append(temp)
        temp = []
    elif count == len(CATEGORIES):
        CATEGORIES_KEYBOARD.append(temp)
CATEGORIES_KEYBOARD = InlineKeyboardMarkup(CATEGORIES_KEYBOARD)


def gen_api_uri(category=None, difficulty=None):
    if category:
        cat = f"&category={category}"
    else:
        cat = ""
    if difficulty:
        dif = f"&difficulty={difficulty}"
    else:
        dif = "&difficulty=medium"
    return f"https://opentdb.com/api.php?amount=1&type=multiple{cat}{dif}"


def top(update, context):
    table = get_total_table()[:10]
    if table == []:
        return
    msg = "*Global Leaderboard*\n\n"
    c = 0
    for user in table:
        tag = f"#{c+1}"
        if c < 3:
            tag = TROPHY_ICONS[c]
        msg += f"`{tag}` {user.user_name} 🏆{user.score}"
        c += 1
    context.bot.send_message(update.effective_chat.id,
                             msg, parse_mode=ParseMode.MARKDOWN)


def weekly(update, context):
    table = get_week_table(update.effective_chat.id)
    if table == []:
        return
    
    score = {}
    ident = {}
    for entry in table:
        if entry.user_id in score:
            score[entry.user_id] += entry.score
        else:
            score[entry.user_id] = entry.score
            ident[entry.user_id] = entry.user_name

    msg = "*Weekly Leaderboard*\n\n"
    if update.effective_chat.id == update.effective_user.id:
        msg = "*Your weekly stat:*\n\n"
    c = 0
    for user_id, score in sorted(score.items(), key=lambda x: x[1]):
        tag = f"#{c+1}"
        if c < 3:
            tag = TROPHY_ICONS[c]
        msg += f"`{tag}` {ident[user_id]} 🏆{score}"
        c += 1
    context.bot.send_message(update.effective_chat.id,
                             msg, parse_mode=ParseMode.MARKDOWN)


def start(update, context):
    update.message.reply_text(
        f"Hi {update.effective_user.first_name}! Use /quiz to start quiz")


def send_quiz(context):
    """Send the alarm message."""

    job = context.job
    chat_id = job.context[0]
    chat_data = job.context[1]
    score = chat_data["score"]
    ident = chat_data["ident"]

    for i in range(1, PER_SESSION_ROUND + 1):
        data = requests.get(gen_api_uri(category=chat_data["cat_id"])).json()[
            "results"][0]

        question = chat_data["question"] = html.unescape(data["question"])
        answer = chat_data["answer"] = html.unescape(data["correct_answer"])
        category = chat_data["category"] = html.unescape(data["category"])

        chat_data["answered"] = False

        hints = MAX_HINT
        if len(answer) < MAX_HINT:
            hints = len(answer)

        hin_t = hintGen(answer)

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
                    hint = "<i>Hint: {}</i>".format(hin_t[x-1])

                context.bot.send_message(chat_id,
                                         text=f"❓<b>QUESTION</b> <i>[{category}]</i> \n\n{question}\n\n{hint}",
                                         parse_mode=ParseMode.HTML)

                sleep(PER_HINT_TIME)
            else:
                break

    score_message = "*Rank List:*\n\n"
    sorted_score = sorted(score.items(), key=lambda x: x[1])
    for k, v in sorted_score:
        score_message += f"{ident[k]} 🏆`+{v}`\n"
        inc_or_new_user(k, ident[k], v, chat_id, datetime.datetime.now())
    score_message += f"\n*Global Leaderboard:* {escape_markdown('/top')}\n*This Week:* {escape_markdown('/weekly')}"

    if score_message != "*Rank List:*\n\n":
        context.bot.send_message(chat_id, text=score_message,
                                 parse_mode=ParseMode.MARKDOWN)
    job.schedule_removal()
    chat_data.clear()


def set_quiz(update, context):
    context.chat_data["cat_id"] = update.callback_query.data
    context.bot.delete_message(
        update.effective_chat.id, update.effective_message.message_id)
    chat_id = update.effective_chat.id
    try:
        # Add job to queue and stop current one if there is a timer already
        context.bot.send_message(
            update.effective_chat.id, "🏁 *Round Starts*!", parse_mode=ParseMode.MARKDOWN)

        context.chat_data["score"] = {}
        context.chat_data["ident"] = {}

        if 'job' in context.chat_data:
            old_job = context.chat_data['job']
            old_job.schedule_removal()
        new_job = context.job_queue.run_repeating(
            send_quiz, 2, context=(chat_id, context.chat_data))
        context.chat_data['job'] = new_job

    except (IndexError, ValueError):
        update.message.reply_text('error')


def send_categories(update, context):
    """Send a list of categories to choose from"""
    context.bot.send_message(update.effective_chat.id, "*Choose one:*",
                             parse_mode=ParseMode.MARKDOWN, reply_markup=CATEGORIES_KEYBOARD)


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
    try:
        answer = context.chat_data["answer"]
    except KeyError:
        return
    if update.message.text.lower() == answer.lower():
        context.chat_data["answered"] = True
        del context.chat_data["answer"]
        score = context.chat_data["score"]
        ident = context.chat_data["ident"]
        f_name = update.effective_user.first_name
        u_id = update.effective_user.id
        answer_result = "🍀 Yes, *{}*!\n\n🏆 {} +1".format(answer, f_name)
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=answer_result,
                                 parse_mode=ParseMode.MARKDOWN)

        if u_id in score:
            score[u_id] += 1
        else:
            score[u_id] = 1
            ident[u_id] = f_name


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    """Run bot."""
    dp.add_handler(CommandHandler("start", start, Filters.private))
    dp.add_handler(CommandHandler("help", start))
    dp.add_handler(CommandHandler("quiz", send_categories))
    dp.add_handler(CallbackQueryHandler(set_quiz))
    dp.add_handler(CommandHandler("stop", unset))
    dp.add_handler(CommandHandler("top", top))
    dp.add_handler(CommandHandler("weekly", weekly))
    dp.add_handler(MessageHandler(Filters.text, check))
    dp.add_error_handler(error)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
