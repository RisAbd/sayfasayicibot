
import time
from datetime import datetime, timedelta
import logging

from flask import Blueprint, request, jsonify, current_app

from telegram.telegram import Update, Chat, Bot, Message, InlineKeyboardMarkup

from app import models, db

from sqlalchemy.orm import joinedload


BOOK_CMD = '/sb_'
CALLBACK_DATA_CMD_PREFIX = 'cmd:'


logger = logging.getLogger(__name__)
bp = Blueprint('webhook', __name__)


@bp.route('/', methods='GET POST PUT PATCH DELETE'.split())
def index():
    update = Update.from_(request.json)
    
    if update.type == Update.Type.MESSAGE:
        bot_command = update.message.bot_command
    elif update.type == update.Type.CALLBACK_QUERY:
        if update.callback_query.data:
            data = update.callback_query.data
            if data.startswith(CALLBACK_DATA_CMD_PREFIX):
                bot_command = data[len(CALLBACK_DATA_CMD_PREFIX):]
            else:
                logger.warning('unknown callback_data: %r', data)
                print(update)
                return jsonify({})
        else:
            logger.warning('unknown callback_query: %r', update.callback_query)
            return jsonify({})
    else:
        logger.warning('TODO: handle %r', update)
        return jsonify({})

    bot = current_app.bot

    if bot_command == '/audio':
        return _send_audio(bot, update)
    elif bot_command == '/books':
        return _send_books_list(bot, update)
    elif bot_command == '/start':
        return _save_user(bot, update)
    elif bot_command == '/stats':
        return _user_stats(bot, update)
    elif bot_command == '/sayfa':
        return _user_sayfa(bot, update)
    elif bot_command == '/mybook':
        return _user_book(bot, update)
    elif bot_command and bot_command.startswith(BOOK_CMD):
        return _save_user_book(bot, update, bot_command)
    elif update.message.text.strip().isdigit():
        return _save_pages(bot, update)
    else:
        return _send_message_back(bot, update)


def _save_user(bot: Bot, update: Update):
    user, is_created = models.User.get_or_create(update.message.from_, _flag=True, _update=True)
    return jsonify(bot.send_message(
        chat=update.message.chat, 
        text='Welcome{}, {}'.format('' if is_created else ' back', user.full_name),
        as_webhook_response=True,
    ))


def _save_user_book(bot: Bot, update: Update, bot_command: str):
    user = models.User.get_or_create(update.callback_query.from_)

    book_id = bot_command.lstrip(BOOK_CMD)
    try:
        book_id = int(book_id)
    except ValueError:
        return jsonify(bot.send_message(
            chat=update.callback_query.message.chat, 
            text='unknown book: %s' % book_id, 
            as_webhook_response=True,
        ))

    book = models.Book.query.get(book_id)
    if not book:
        return jsonify(bot.send_message(
            chat=update.callback_query.message.chat, 
            text='unknown book: %s' % book_id, 
            as_webhook_response=True,
        ))

    user.book = book
    db.session.add(user)
    db.session.commit()

    return jsonify(bot.send_message(
        chat=update.callback_query.message.chat, 
        text='`%s` is set as your default book' % book.title, 
        parse_mode=Message.ParseMode.MARKDOWN,
        as_webhook_response=True,
    ))


def _save_pages(bot: Bot, update: Update):
    
    raw_sayfa_value = update.message.text

    try:
        sayfa_count = int(raw_sayfa_value)
    except ValueError:
        return jsonify(bot.send_message(
            chat=update.message.chat,
            text='misunderstood your sayfa value: `%s`' % raw_sayfa_value,
            parse_mode=Message.ParseMode.MARKDOWN,
            as_webhook_response=True,
        ))
    
    user = models.User.get_or_create(update.message.from_)

    if not user.book:
        return jsonify(bot.send_message(
            chat=update.message.chat,
            text="you haven't set your current book yet",
            as_webhook_response=True,
        ))
    
    sayfa = models.Sayfa(user=user, book=user.book, count=sayfa_count)
    db.session.add(sayfa)
    db.session.commit()

    return jsonify(bot.send_message(
        chat=update.message.chat,
        text="you've read %s sayfa of %s, Allah kabul etsin!" % (sayfa.count, user.book.title),
        as_webhook_response=True,
    ))


def _send_books_list(bot: Bot, update: Update):

    books = models.Book.query.options(joinedload('author')).all()
    
    user = models.User.get_or_create(update.message.from_)
    user_book = user.book

    # books_list_text = '\n'.join(
    #     '{book_cmd}{book.id} {book.title}'.format(book_cmd=BOOK_CMD, book=book)
    #     for book in books
    # )
    markup = InlineKeyboardMarkup.from_rows_of(
        buttons=[
            InlineKeyboardMarkup.Button(text='{}{}'.format(b.title, '' if b != user_book else '(+)'),
                                        callback_data='{}{}{}'.format(CALLBACK_DATA_CMD_PREFIX, BOOK_CMD, b.id))
            for b in books
        ]
    )

    return jsonify(bot.send_message(
        chat=update.message.chat, 
        text='here is a list of available books',
        reply_markup=markup,
        as_webhook_response=True,
    ))


def _user_stats(bot: Bot, update: Update):
    user = models.User.get_or_create(update.message.from_)

    now = datetime.now()
    last_day_sayfa = db.session.query(db.func.sum(models.Sayfa.count))\
        .filter(models.Sayfa.user == user)\
        .filter(models.Sayfa.time > now - timedelta(days=1)).scalar() or 0
    last_week_sayfa = db.session.query(db.func.sum(models.Sayfa.count))\
        .filter(models.Sayfa.user == user)\
        .filter(models.Sayfa.time > now - timedelta(days=7)).scalar() or 0
    last_month_sayfa = db.session.query(db.func.sum(models.Sayfa.count))\
        .filter(models.Sayfa.user == user)\
        .filter(models.Sayfa.time > now - timedelta(days=30)).scalar() or 0
    
    text = '''
you have read
 - `{ds}` sayfa for last day
 - `{ws}` sayfa for last week
 - `{ms}` sayfa for last month
'''.format(ds=last_day_sayfa, 
           ws=last_week_sayfa,
           ms=last_month_sayfa,
           )

    return jsonify(bot.send_message(
        chat=update.message.chat,
        text=text,
        parse_mode=Message.ParseMode.MARKDOWN,
        as_webhook_response=True,
    ))


def _humanize(time: datetime, now: datetime):
    return 'at ' + time.strftime('%d/%m/%Y %H:%M')


def _map_sayfa(sayfa, now):
    format = '%d/%m/%Y %H:%M' if sayfa.time.year != now.year else '%d/%m %H:%M'
    return '`{time}` - {sayfa.count} - {sayfa.book.title}'.format(sayfa=sayfa, time=sayfa.time.strftime(format))


def _user_sayfa(bot: Bot, update: Update):
    user = models.User.get_or_create(update.message.from_)

    now = datetime.now()
    text = '\n'.join(
        _map_sayfa(sayfa, now=now)
        for sayfa in models.Sayfa.query.options(joinedload(models.Sayfa.book))\
            .filter(models.Sayfa.user == user)\
            .filter(models.Sayfa.time > datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0))
    ) or 'you have not read this month'

    return jsonify(bot.send_message(
        chat=update.message.chat,
        text=text,
        parse_mode=Message.ParseMode.MARKDOWN,
        as_webhook_response=True,
    ))


def _user_book(bot: Bot, update: Update):
    user = models.User.get_or_create(update.message.from_)

    if not user.book:
        return jsonify(bot.send_message(
            chat=update.message.chat,
            text='you haven\'t set your book yet (use /listbooks to see avalable books)',
            as_webhook_response=True,
        ))

    return jsonify(bot.send_message(
        chat=update.message.chat,
        text='your current book is `%s`' % user.book.title,
        parse_mode=Message.ParseMode.MARKDOWN,
        as_webhook_response=True,
    ))


def _send_message_back(bot: Bot, update: Update):
    bot.send_chat_action(update.message.chat, Chat.Action.TYPING)
    time.sleep(0.4)
    return jsonify(bot.send_message(
        chat=update.message.chat, 
        text='misunderstood: %s' % update.message.text, 
        as_webhook_response=True,
    ))


def _send_audio(bot: Bot, update: Update):
    bot.send_chat_action(update.message.chat, Chat.Action.UPLOAD_AUDIO)
    time.sleep(0.5)
    return jsonify(bot.send_document(
        update.message.chat, 
        'CQADAgADvAMAArCqWEsSWuzVBRHRfRYE', 
        'Hicranda gonlum', 
        as_webhook_response=True,
    ))