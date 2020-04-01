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
from database import get_total_table, get_week_table, inc_or_new_user, perpetual_get_status, perpetual_toggle_status

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger("QUIZ")

logger.info("Starting Engine!")
updater = Updater(config.TOKEN, use_context=True)
dp = updater.dispatcher
logger.info("Successfully started!")


# Time between hints
PER_HINT_TIME = 15
# Maximum number of hints + 2 (Q+M)
MAX_HINT = 5
# Keys per line in Categories
PER_LINE_KEYS = 3
# Trophy icons for Leaderboard
TROPHY_ICONS = ["🥇", "🥈", "🥉"]

# Categories
# These are taken from the website which provides questions, which is
# https://opentdb.com/ . So in case of any changes to existing or in
# case of new categories, refer to the mentioned website. Option
# named All Categories does not exist in https://opentdb.com/ thus it
# is a placeholder for removing category input from API call
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
    "Animals": 27,
    "All Categories": 0
}

# CATEGORIES_KEYBOARD is the telegram Inline keyboard which shows
# all the categories in CATEGORIES dictionary. Number of buttons
# per line is configured based on PER_LINE_KEYS variable above
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

# ROUND_KEYBOARD is the telegram Inline keyboard which shows available
# options to choose from a number of rounds
ROUND_KEYBOARD = InlineKeyboardMarkup([[InlineKeyboardButton("5 Rounds", callback_data="round5"),
                                        InlineKeyboardButton("10 Rounds", callback_data="rounds10")],
                                       [InlineKeyboardButton("25 Rounds", callback_data="round25"),
                                        InlineKeyboardButton(
                                            "50 Rounds", callback_data="round50"),
                                        InlineKeyboardButton("∞ Rounds", callback_data="round0")]])


# Generating API uri by taking category id and difficulty as **kwargs
def gen_api_uri(category=None, difficulty=None):
    if category:
        cat = f"&category={category}"
        # If category is 0, it means All Category and thus category string in
        # API call should be removed hence no specified category
        # NOTE Refactor this
        if category == 0:
            cat = ""
    else:
        cat = ""
    if difficulty:
        dif = f"&difficulty={difficulty}"
    else:
        dif = "&difficulty=medium"
    return f"https://opentdb.com/api.php?amount=1&type=multiple{cat}{dif}"


# Get data from API. This is a recursive function
# TODO Refactor this
def get_api_data(category_id):
    data = requests.get(gen_api_uri(category=category_id)).json()["results"][0]
    if ("following" in html.unescape(data["question"]) or "these" in html.unescape(data["question"])):
        data = get_api_data(category_id)
        if not (1 < len(data["correct_answer"]) < 16):
            data = get_api_data(category_id)
        if "," in data["correct_answer"]:
            data["correct_answer"] = data["correct_answer"].replace(",", "")
    return data


# TODO Refactor top() and weekly() to reduce duplicate code
# Get global top table from database and parse it
def top(update, context):
    table = get_total_table()[:10]
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

    msg = "*Global Leaderboard*\n\n"
    c = 0
    for user_id, score in reversed(sorted(score.items(), key=lambda x: x[1])):
        tag = f"#{c+1}"
        if c < 3:
            tag = TROPHY_ICONS[c]
        msg += f"`{tag}` {ident[user_id]} 🏆{score}\n"
        c += 1
    context.bot.send_message(update.effective_chat.id,
                             msg, parse_mode=ParseMode.MARKDOWN)


# Get weekly top table from database and parse it
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
    for user_id, score in reversed(sorted(score.items(), key=lambda x: x[1])):
        tag = f"#{c+1}"
        if c < 3:
            tag = TROPHY_ICONS[c]
        msg += f"`{tag}` {ident[user_id]} 🏆{score}\n"
        c += 1
    context.bot.send_message(update.effective_chat.id,
                             msg, parse_mode=ParseMode.MARKDOWN)


# Shows start message
def start(update, context):
    update.message.reply_text(
        f"Hi {update.effective_user.first_name}! Use /quiz to start quiz")


# Send question, hints and other messages
def send_quiz(context):
    """Send the alarm message."""

    job = context.job
    # Job context passed from set_quiz() is (chat_id, chat_data)
    # because both chat_id and chat_data are not directly 
    # available from context
    chat_id = job.context[0]
    chat_data = job.context[1]
    rounds = chat_data["rounds"]
    rounds_display = rounds

    # If rounds is 0, then infinite mode should be turned on such
    # that quiz will never end. There is an exception to this
    # when perpetual mode is turned ON. Change rounds's value to
    # 1 because loop will not run while the value is 0
    if rounds == 0:
        chat_data["infinite_mode"] = True
        rounds_display = "∞"
        rounds = 1

    # Both score and ident are passed as empty dictionaries in chat_data    
    score = chat_data["score"]
    ident = chat_data["ident"]

    # Initialize and run while loop. For loop can not be used since we
    # can not run infinite mode in for loop
    index = 1
    while index < rounds + 1:
        # If infinite mode is turned ON, increment value of rounds in each
        # iteration so that the condition being checked will never be false
        if "infinite_mode" in chat_data:
            rounds += 1
            # Get perpetual mode status from database
            perpetual_status = perpetual_get_status(chat_id)
            # If perpetual status is turned OFF and there are more
            # than 2 idle (>=3)rounds, then stop the quiz by
            # breaking the while loop
            if not perpetual_status and chat_data["idle"] >= 3:
                break

        # Get data from API
        data = get_api_data(chat_data["cat_id"])

        question = chat_data["question"] = html.unescape(data["question"])
        answer = chat_data["answer"] = html.unescape(data["correct_answer"])
        category = chat_data["category"] = html.unescape(data["category"])

        chat_data["answered"] = False

        hints = MAX_HINT
        # If answer is too short, number of hints needed should be fewer
        if len(answer) < MAX_HINT:
            hints = len(answer)

        # Generate hints based on answer. See hint.py
        hin_t = hintGen(answer)

        for x in range(hints):
            # Check if question has already been answered. See check()
            if chat_data["answered"] == False:
                hint = ""
                # Check if iteration has reached last step
                if x == hints-1:
                    del chat_data["answer"]
                    context.bot.send_message(chat_id,
                                             text=f"⛔️ Nobody guessed, Correct answer was *{answer}*",
                                             parse_mode=ParseMode.MARKDOWN)
                    # Increment number of continues idle rounds by 1.
                    # If someone answers, counter will be reset to 0
                    # See check()
                    chat_data["idle"] += 1
                    break
                elif x > 0:
                    hint = "<i>Hint: {}</i>".format(hin_t[x-1])

                context.bot.send_message(chat_id,
                                         text=f"❓<b>QUESTION</b> <i>[{category}]</i> {index}/{rounds_display}\n\n{question}\n\n{hint}",
                                         parse_mode=ParseMode.HTML)
                
                # Wait for answer
                sleep(PER_HINT_TIME)
            else:
                break
        index += 1

    score_message = "*Winners:*\n\n"
    # Generate a message to parsed when the quiz ends
    sorted_score = reversed(sorted(score.items(), key=lambda x: x[1]))
    for k, v in sorted_score:
        score_message += f"{ident[k]} 🏆`+{v}`\n"
        inc_or_new_user(k, ident[k], v, chat_id, datetime.datetime.now())
    score_message += f"\n*Global Leaderboard:* {escape_markdown('/top')}\n*This Week:* {escape_markdown('/weekly')}"

    # Sends the generated message (above) if there is at-least one winner
    # NOTE Send a message if there is no winners (?)
    # TODO Check if there is a winner using score dictionary
    if "🏆" in score_message:
        context.bot.send_message(chat_id, text=score_message,
                                 parse_mode=ParseMode.MARKDOWN)

    # Remove job from queue and clear chat_data
    job.schedule_removal()
    chat_data.clear()


# Set quiz environment
# This is a callback button handler, 
# therefore multiple inputs will need support
def set_quiz(update, context):
    # Check if this is an input for ROUNDS_KEYBOARD
    if "round" in update.callback_query.data:
        # Set value of rounds in chat_data as integer from 
        # callback_data which passed in ROUND_KEYBOARD
        context.chat_data["rounds"] = int(
            update.callback_query.data.replace("round", ""))
        # Initialize idle value as 0
        context.chat_data["idle"] = 0
        # Delete ROUND_KEYBOARD which is already sent to channel
        context.bot.delete_message(
            update.effective_chat.id, update.effective_message.message_id)
        chat_id = update.effective_chat.id
        try:
            context.bot.send_message(
                update.effective_chat.id, "🏁 *Round Starts*!", parse_mode=ParseMode.MARKDOWN)

            # initialize score and ident in chat_data as empty dictionary
            context.chat_data["score"] = {}
            context.chat_data["ident"] = {}

            # Add job to queue and stop current one if there is a timer already
            # NOTE This can probably be removed
            if 'job' in context.chat_data:
                old_job = context.chat_data['job']
                old_job.schedule_removal()

            # Run job
            new_job = context.job_queue.run_repeating(
                send_quiz, 2, context=(chat_id, context.chat_data))
            context.chat_data['job'] = new_job

        except (IndexError, ValueError):
            update.message.reply_text('error')
    # Since this is not ROUND_KEYBOARDS's input, this can only be
    # input of CATEGORIES_KEYBOARD which is the first stage of two stages
    else:
        # Set cat_id (category id) in chat_data as callback_data 
        context.chat_data["cat_id"] = update.callback_query.data
        # Delete CATEGORIES_KEYBOARD sent to channel
        context.bot.delete_message(
            update.effective_chat.id, update.effective_message.message_id)
        # Send ROUND_KEYBOARD to channel
        # TODO Improve message
        context.bot.send_message(update.effective_chat.id, "*Choose number of rounds:*",
                                 parse_mode=ParseMode.MARKDOWN, reply_markup=ROUND_KEYBOARD)


# Send CATEGORIES_BUTTON
def send_categories(update, context):
    """Send a list of categories to choose from"""
    # If there is a job in chat_data, meaning
    # a quiz is already running, abort operation
    if 'job' in context.chat_data:
        update.message.reply_text('You have an active Quiz running!')
        return
    # TODO Improve message
    context.bot.send_message(update.effective_chat.id, "*Choose one:*",
                             parse_mode=ParseMode.MARKDOWN, reply_markup=CATEGORIES_KEYBOARD)


# Stop Quiz
def unset(update, context):
    """Remove the job if the user changed their mind."""
    # Get perpetual mode status from database
    perpetual_status = perpetual_get_status(update.effective_chat.id)

    # Check if a quiz is running by checking 'job' in chat_data. 
    # If not, abort operation
    if 'job' not in context.chat_data:
        update.message.reply_text('You have no active quiZZzZes!')
        return

    # Only an admin can stop the quiz if perpetual mode is set to ON
    if perpetual_status and (update.effective_user.id not in [admin.user.id for admin in update.effective_chat.get_administrators()]):
        update.message.reply_markdown("Ask an *admin* to stop quiz!")
        return

    job = context.chat_data['job']

    # Remove job from queue and clear chat_data
    job.schedule_removal()
    context.chat_data.clear()

    update.message.reply_text('✋ *Stopped*!', parse_mode=ParseMode.MARKDOWN)


# Check if message received is correct answer
def check(update, context):
    # Check if there is answer set. If not, abort
    try:
        answer = context.chat_data["answer"]
    except KeyError:
        return

    # Check if received answer is correct 
    if update.message.text.lower() == answer.lower():
        context.chat_data["answered"] = True
        del context.chat_data["answer"]
        score = context.chat_data["score"]
        ident = context.chat_data["ident"]
        f_name = update.effective_user.first_name
        u_id = update.effective_user.id
        answer_result = "🍀 Yes, *{}*!\n\n🏆 {} +1".format(answer, f_name)
        context.chat_data["idle"] = 0
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=answer_result,
                                 parse_mode=ParseMode.MARKDOWN)

        if u_id in score:
            score[u_id] += 1
        else:
            score[u_id] = 1
            ident[u_id] = f_name


# Toggle perpetual mode
def perpetual_toggle(update, context):
    # Get channel admin list
    admin_list = [
        admin.user.id for admin in update.effective_chat.get_administrators()]
    
    # If user is in admin_list, toggle perpetual mode
    if update.effective_user.id in admin_list:
        status = perpetual_toggle_status(
            update.effective_chat.id, update.effective_user.id)
        msg = "Perpetual Mode set to: *OFF*"
        if status:
            msg = "Perpetual Mode set to: *ON*"
        update.message.reply_markdown(msg)


# Error handler
def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


# Main function
def main():
    """Run bot."""
    dp.add_handler(CommandHandler("start", start, Filters.private))
    dp.add_handler(CommandHandler("help", start))
    # NOTE Filter quiz to groups only (?)
    dp.add_handler(CommandHandler("quiz", send_categories))
    dp.add_handler(CallbackQueryHandler(set_quiz))
    dp.add_handler(CommandHandler("stop", unset))
    dp.add_handler(CommandHandler("top", top))
    dp.add_handler(CommandHandler("weekly", weekly))
    dp.add_handler(CommandHandler(
        "perpetual", perpetual_toggle, Filters.group))
    dp.add_handler(MessageHandler(Filters.text, check))
    dp.add_error_handler(error)

    updater.start_polling()
    updater.idle()


# Run main()
if __name__ == '__main__':
    main()
