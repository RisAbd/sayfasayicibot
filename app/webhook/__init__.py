import time

from datetime import datetime, timedelta
import logging

from sqlalchemy.orm import joinedload

from flask import Blueprint, request, jsonify, current_app, abort

from telegram.telegram import Update, Chat, Bot, Message, InlineKeyboardMarkup

from app import models, db

from .utils import jsonified_response


BOOK_CMD = "/sb_"
CALLBACK_DATA_CMD_PREFIX = "cmd:"


logger = logging.getLogger(__name__)
bp = Blueprint("webhook", __name__)


@bp.route("/<bot_api_token>/", methods="GET POST PUT PATCH DELETE".split())
def index(bot_api_token):
    if bot_api_token != current_app.bot._api_token:
        return abort(404)
    update = Update.from_(request.json)

    if update.type == Update.Type.MESSAGE:
        bot_command = update.message.bot_command
    elif update.type == update.Type.CALLBACK_QUERY:
        if update.callback_query.data:
            data = update.callback_query.data
            if data.startswith(CALLBACK_DATA_CMD_PREFIX):
                bot_command = data[len(CALLBACK_DATA_CMD_PREFIX) :]
            else:
                logger.warning("unknown callback_data: %r", data)
                print(update)
                return jsonify({})
        else:
            logger.warning("unknown callback_query: %r", update.callback_query)
            return jsonify({})
    else:
        logger.warning("TODO: handle %r", update)
        return jsonify({})

    bot = current_app.bot

    if bot_command == "/audio":
        return _send_audio(bot, update)
    elif bot_command == "/books":
        return _send_books_list(bot, update)
    elif bot_command == "/start":
        return _save_user(bot, update)
    elif bot_command == "/stats":
        return _user_stats(bot, update)
    elif bot_command == "/sayfa":
        return _user_sayfa(bot, update)
    elif bot_command == "/mybook":
        return _user_book(bot, update)
    elif bot_command == "/checkpoint":
        return _user_checkpoint(bot, update)
    elif bot_command and bot_command.startswith(BOOK_CMD):
        return _save_user_book(bot, update, bot_command)
    elif update.message.text.strip().isdigit():
        return _save_pages(bot, update)
    else:
        return _send_message_back(bot, update)


@jsonified_response
def _save_user(bot: Bot, update: Update):
    user, is_created = models.User.get_or_create(
        update.message.from_, _flag=True, _update=True
    )
    return bot.send_message(
        chat=update.message.chat,
        text="Welcome{}, {}".format("" if is_created else " back", user.full_name),
        as_webhook_response=True,
    )


@jsonified_response
def _save_user_book(bot: Bot, update: Update, bot_command: str):
    user = models.User.get_or_create(update.callback_query.from_)

    book_id_raw = bot_command.lstrip(BOOK_CMD)
    try:
        book_id = int(book_id_raw)
    except ValueError:
        return bot.send_message(
            chat=update.callback_query.message.chat,
            text="unknown book: %s" % book_id_raw,
            as_webhook_response=True,
        )

    book = models.Book.query.get(book_id)
    if not book:
        return bot.send_message(
            chat=update.callback_query.message.chat,
            text="unknown book: %s" % book_id,
            as_webhook_response=True,
        )

    if book == user.book:
        return bot.answer_callback_query(
            update.callback_query, text="`%s` is already your default book" % book.title
        )

    user.book = book
    db.session.add(user)
    db.session.commit()

    msg = update.callback_query.message

    bot.edit_message_reply_markup(
        chat=msg.chat, message=msg, markup=_books_markup(user_book=book)
    )
    return bot.answer_callback_query(
        update.callback_query, text="`%s` is set as your default book" % book.title
    )


@jsonified_response
def _save_pages(bot: Bot, update: Update):

    raw_sayfa_value = update.message.text

    try:
        sayfa_count = int(raw_sayfa_value)
    except ValueError:
        return bot.send_message(
            chat=update.message.chat,
            text="misunderstood your sayfa value: `%s`" % raw_sayfa_value,
            parse_mode=Message.ParseMode.MARKDOWN,
            as_webhook_response=True,
        )

    user = models.User.get_or_create(update.message.from_)

    if not user.book:
        return bot.send_message(
            chat=update.message.chat,
            text="you haven't set your current book yet",
            as_webhook_response=True,
        )

    sayfa = models.Sayfa(user=user, book=user.book, count=sayfa_count)
    db.session.add(sayfa)
    db.session.commit()

    bot.send_message(
        chat=update.message.chat,
        text="you've read %s sayfa of %s, Allah kabul etsin!"
        % (sayfa.count, user.book.title),
        # as_webhook_response=True,
    )
    return jsonified_response.bypass(_user_stats(bot, update))


def _books_markup(user=None, user_book=None):
    user_book = user_book or (user and user.book)

    books = models.Book.query.options(joinedload("author")).all()

    markup = InlineKeyboardMarkup.from_rows_of(
        buttons=[
            InlineKeyboardMarkup.Button(
                text="{}{}".format(b.title, "" if b != user_book else " (✓)"),
                callback_data="{}{}{}".format(CALLBACK_DATA_CMD_PREFIX, BOOK_CMD, b.id),
            )
            for b in books
        ]
    )
    return markup


@jsonified_response
def _send_books_list(bot: Bot, update: Update):
    user = models.User.get_or_create(update.message.from_)

    markup = _books_markup(user=user)

    return bot.send_message(
        chat=update.message.chat,
        text="here is a list of available books",
        reply_markup=markup,
        as_webhook_response=True,
    )


@jsonified_response
def _user_stats(bot: Bot, update: Update):
    user = models.User.get_or_create(update.message.from_)

    now = datetime.now()

    user_sayfa_q = db.session.query(db.func.sum(models.Sayfa.count)).filter(
        models.Sayfa.user == user
    )

    last_day_sayfa = (
        user_sayfa_q.filter(models.Sayfa.time > now - timedelta(days=1)).scalar() or 0
    )
    last_week_sayfa = (
        user_sayfa_q.filter(models.Sayfa.time > now - timedelta(days=7)).scalar() or 0
    )
    last_month_sayfa = (
        user_sayfa_q.filter(models.Sayfa.time > now - timedelta(days=30)).scalar() or 0
    )

    checkpoint = (
        models.Checkpoint.query.filter_by(user=user)
        .order_by(models.Checkpoint.time.desc())
        .first()
    )
    last_checkpoint_sayfa = checkpoint and (
        user_sayfa_q.filter(models.Sayfa.time > checkpoint.time).scalar() or 0
    )

    text = """
you have read
 - `{ds}` sayfa for last day
 - `{ws}` sayfa for last week
 - `{ms}` sayfa for last month
"""

    if last_checkpoint_sayfa is not None:
        text += " - `{chs}` sayfa from previous checkpoint ({ch})\n"

    text = text.format(
        ds=last_day_sayfa,
        ws=last_week_sayfa,
        ms=last_month_sayfa,
        chs=last_checkpoint_sayfa,
        ch=checkpoint,
    )

    return bot.send_message(
        chat=update.message.chat,
        text=text,
        parse_mode=Message.ParseMode.MARKDOWN,
        as_webhook_response=True,
    )


def _humanize(time: datetime, now: datetime):
    return "at " + time.strftime("%d/%m/%Y %H:%M")


def _map_sayfa(sayfa, now):
    format = "%d/%m/%Y %H:%M" if sayfa.time.year != now.year else "%d/%m %H:%M"
    return "`{time}` - {sayfa.count} - {sayfa.book.title}".format(
        sayfa=sayfa, time=sayfa.time.strftime(format)
    )


@jsonified_response
def _user_sayfa(bot: Bot, update: Update):
    user = models.User.get_or_create(update.message.from_)

    now = datetime.now()
    text = (
        "\n".join(
            _map_sayfa(sayfa, now=now)
            for sayfa in models.Sayfa.query.options(joinedload(models.Sayfa.book))
            .filter(models.Sayfa.user == user)
            .filter(
                models.Sayfa.time
                > datetime.now().replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0
                )
            )
        )
        or "you have not read this month"
    )

    return bot.send_message(
        chat=update.message.chat,
        text=text,
        parse_mode=Message.ParseMode.MARKDOWN,
        as_webhook_response=True,
    )


@jsonified_response
def _user_checkpoint(bot: Bot, update: Update):
    user = models.User.get_or_create(update.message.from_)

    name = update.message.bot_command_argument.strip() or None

    if db.session.query(
        models.Checkpoint.query.filter(models.User.id == user.id).exists()
    ).scalar():
        stats = _user_stats(bot, update)
    else:
        stats = {}

    checkpoint = models.Checkpoint(user=user, name=name)
    db.session.add(checkpoint)
    db.session.commit()

    def main_response(as_resp=True):
        if stats:
            text = "new checkpoint created: %s"
        else:
            text = "you created your first checkpoint: %s"

        return bot.send_message(
            chat=update.message.chat,
            text=text % (checkpoint),
            as_webhook_response=as_resp,
        )

    if not stats:
        return main_response()

    main_response(as_resp=False)
    return jsonified_response.skip(stats)


@jsonified_response
def _user_book(bot: Bot, update: Update):
    user = models.User.get_or_create(update.message.from_)

    if not user.book:
        return bot.send_message(
            chat=update.message.chat,
            text="you haven't set your book yet"
            " (use /listbooks to see avalable books)",
            as_webhook_response=True,
        )

    return bot.send_message(
        chat=update.message.chat,
        text="your current book is `%s`" % user.book.title,
        parse_mode=Message.ParseMode.MARKDOWN,
        as_webhook_response=True,
    )


@jsonified_response
def _send_message_back(bot: Bot, update: Update):
    # bot.send_chat_action(update.message.chat, Chat.Action.TYPING)
    time.sleep(0.4)
    return bot.send_message(
        chat=update.message.chat,
        text="misunderstood: %s" % update.message.text,
        as_webhook_response=True,
    )


@jsonified_response
def _send_audio(bot: Bot, update: Update):
    bot.send_chat_action(update.message.chat, Chat.Action.UPLOAD_AUDIO)
    time.sleep(0.5)
    return bot.send_document(
        update.message.chat,
        "CQADAgADvAMAArCqWEsSWuzVBRHRfRYE",
        "Hicranda gonlum",
        as_webhook_response=True,
    )
