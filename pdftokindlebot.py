import configparser
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import formatdate
from email import encoders
import logging
import logging.handlers
import os
# import requests
import smtplib
import sqlite3
# import sys
import telebot
from telebot import types
import urllib.request
from validate_email import validate_email


# Get file from URL
def open_file(file_url, chatid):

    file_name, headers = urllib.request.urlretrieve(file_url, 'send2kindle_'
        + str(chatid) + '.pdf')
    return file_name


# Send e-mail function
def send_mail(chatid, send_from, send_to, subject, text, file_url):
    msg = MIMEMultipart()
    msg['From'] = send_from
    msg['To'] = send_to
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject

    msg.attach(MIMEText('Send2KindleBot'))

    try:
        files = open_file(file_url, chatid)
    except:
        bot.send_message(chatid, 'File not found. Aborted.')
        return 0

    bot.send_message(chatid, str(u'\U0001F5DE')
        + '<b>Sending file</b>.\nPlease, wait a moment.', parse_mode='HTML')

    part = MIMEBase('application', 'octet-stream')
    part.set_payload(open(files, 'rb').read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition',
        'attachment; filename="{0}"'.format(os.path.basename(files)))
    msg.attach(part)

    smtp = smtplib.SMTP('127.0.0.1')

    try:
        smtp.sendmail(send_from, send_to, msg.as_string())
    except smtplib.SMTPRecipientsRefused:
        msg = bot.send_message(chatid,
            str(u'\U000026A0') + '<b>Error</b>.\n'
            + 'Please, check your e-mail and try again.', parse_mode='HTML')
        smtp.close()
        logger_info.info(str(datetime.datetime.now()) + '\tError:\t'
            + str(chatid) + '\t' + send_from + '\t' + send_to)
        upd_user_last(db, table, chatid)
        return 0

    smtp.close()

    upd_user_last(db, table, chatid)

    logger_info.info(str(datetime.datetime.now()) + '\tSENT:\t' + str(chatid)
        + '\t' + send_from + '\t' + send_to)

    os.remove(files)
    bot.send_message(chatid,
        str(u'\U0001F4EE') + '<b>File sent</b>.'
        + '\nWait a few minutes and check on your device.'
        + '\n\nSend a new command.', parse_mode='HTML', reply_markup=button)


# Add user to database
def add_user(db, table, chatid):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    aux = ('''INSERT INTO {} (chatid, remetente, destinatario, criacao, usado)
        VALUES ('{}', '', '',
        '{}', '{}')''').format(table, chatid,
        str(datetime.datetime.now()), str(datetime.datetime.now()))
    logger_info.info(str(datetime.datetime.now()) + '\tUSER:\t' + str(chatid))
    cursor.execute(aux)
    conn.commit()
    conn.close()


# Update user last usage
def upd_user_last(db, table, chatid):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    aux = ('''UPDATE {} SET usado = {}
        WHERE chatid = {}''').format(table, '"' + str(datetime.datetime.now())
        + '"', chatid)
    cursor.execute(aux)
    conn.commit()
    conn.close()
    # logger_info.info(str(datetime.datetime.now()) + '\tLAST:\t'
    #   + str(chatid))

def upd_user_file(db, table, chatid, file_url):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    aux = ('''UPDATE {} SET arquivo = {}
        WHERE chatid = {}''').format(table, '"' + str(file_url) + '"', chatid)
    cursor.execute(aux)
    conn.commit()
    conn.close()

# Update user e-mail
def upd_user_email(db, table, chatid, email):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    if '@kindle.com' in email.lower():
        aux = ('''UPDATE {} SET destinatario = {}
            WHERE chatid = {}''').format(table, email, chatid)
    else:
        aux = ('''UPDATE {} SET remetente = {}
            WHERE chatid = {}''').format(table, email, chatid)
    # print(aux)
    logger_info.info(str(datetime.datetime.now()) + '\tUPD:\t' + str(chatid)
        + '\t' + email)
    cursor.execute(aux)
    conn.commit()
    conn.close()


# Select user on database
def select_user(db, table, chatid, field):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    aux = ('''SELECT {} FROM "{}" WHERE
        chatid="{}"''').format(field, table, str(chatid))
    cursor.execute(aux)
    usuarios = cursor.fetchone()
    if usuarios:
        # print('Existe')
        data = usuarios
    else:
        # print('Nao existe')
        add_user(db, table, chatid)
        data = ''
    # for usuarios in cursor.fetchall():
    #     print(str(usuarios))
    conn.close()
    # print(data)
    return data

if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.sections()
    BOT_CONFIG_FILE = 'kindle.conf'
    config.read(BOT_CONFIG_FILE)
    log_file = config['DEFAULT']['logfile']
    TOKEN = config['DEFAULT']['TOKEN']
    db = config['SQLITE3']['data_base']
    table = config['SQLITE3']['table']

    bot = telebot.TeleBot(TOKEN)
    button = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton('Send file', callback_data='/send')
    btn2 = types.InlineKeyboardButton('Set e-mail', callback_data='/email')
    button.row(btn1, btn2)
    button2 = types.InlineKeyboardMarkup()
    btn3 = types.InlineKeyboardButton('As is', callback_data='/as_is')
    btn4 = types.InlineKeyboardButton('Converted', callback_data='/converted')
    button2.row(btn3, btn4)
    LOG_INFO_FILE = log_file
    logger_info = logging.getLogger('InfoLogger')
    logger_info.setLevel(logging.DEBUG)
    handler_info = logging.handlers.RotatingFileHandler(LOG_INFO_FILE,
        maxBytes=10240, backupCount=5, encoding='utf-8')
    logger_info.addHandler(handler_info)

    # select_user(db, table, sys.argv[1])
    @bot.message_handler(commands=['start'])
    def start(message):
        upd_user_last(db, table, message.from_user.id)
        data = select_user(db, table, message.from_user.id, '*')
        # bot.send_message(message.from_user.id, str(data))
        # print(data)
        # print('Data[3] ' + str(data[3]))
        # print(data[4])
        try:
            aux1 = data[2]
            aux2 = data[3]
        except:
            aux1 = ' '
            aux2 = ' '
        if len(aux1) < 3 or len(aux2) < 3:
            msg = bot.send_message(message.from_user.id, 'Hi!\n' +
                'This bot sends files to your Kindle.\n' +
                'First, type your Kindle e-mail.', parse_mode='HTML')
            bot.register_next_step_handler(msg, add_email)
        else:
            bot.send_message(message.from_user.id, (
                '<b>Welcome back</b>!\n'
                + 'Your registered e-mails are:\n{} {}\n{} {}\n' +
                'To send a file to your Kindle, click <b>Send file</b>.\n' +
                'To change an e-mail, click <b>Set e-mail</b>.').format(
                str(u'\U0001F4E4'), data[2], str(u'\U0001F4E5'), data[3]
            ), parse_mode='HTML', reply_markup=button)

    @bot.message_handler(commands=['email'])
    def ask_email(message):
        msg = bot.send_message(message.from_user.id,
            'Type your Kindle e-mail.')
        bot.register_next_step_handler(msg, add_email)

    def add_email(message):
        if '/' not in message.text:
            if validate_email(message.text.lower()):
                if '@kindle.com' in message.text.lower():
                    upd_user_email(db, table, message.from_user.id, '"' +
                        str(message.text) + '"')
                    # check = select_user(db, table, message.from_user.id,
                    #     'remetente')
                    msg = bot.reply_to(message,
                        'Type your email used on your Amazon account.')
                    bot.register_next_step_handler(msg, add_email)
                else:
                    upd_user_email(db, table, message.from_user.id, '"' +
                        str(message.text) + '"')
                    bot.reply_to(message,
                        str(u'\U00002705') + '<b>Success</b>.\n' +
                        'To send a file to your Kindle, click <b>Send file</b>'
                        + '.\nTo change your e-mail, click <b>Set e-mail</b>.',
                        parse_mode='HTML', reply_markup=button)
            else:
                msg = bot.send_message(message.from_user.id, str(u'\U000026A0')
                    + '<b>Error</b>. \n'
                    + message.text + ' is not valid.\n' +
                    'Type your Kindle e-mail.', parse_mode='HTML')
                bot.register_next_step_handler(msg, add_email)

    @bot.message_handler(commands=['send'])
    def ask_file(message):
        msg = bot.send_message(message.from_user.id,
            'Send me the file (up to 20MB) or the link to the file.')
        bot.register_next_step_handler(msg, get_file)

    def get_file(message):
        if message.content_type == 'document':
            file_size = message.document.file_size
            bot.reply_to(message, str(u'\U00002705') + 'Downloaded '
                + str(file_size) + ' bytes.')
            file_info = bot.get_file(message.document.file_id)
            file_url = ('https://api.telegram.org/file/bot' + TOKEN + '/'
                + file_info.file_path)
            # print(file_url)
        elif message.content_type == 'text':
            if '/start' in message.text or '/send' in message.text:
                return 0
            file_url = message.text
        else:
            msg = bot.send_message(message.from_user.id,
                'Please, send as a file.')
            bot.register_next_step_handler(msg, get_file)
            return 0

        # data = select_user(db, table, message.from_user.id, '*')
        # f = requests.get(file_url)
        upd_user_file(db, table, message.from_user.id, file_url)
        msg = bot.send_message(message.from_user.id,
            'Send file <b>as is</b> or <b>converted</b> to Kindle format?',
            parse_mode='HTML', reply_markup=button2)
        # bot.register_next_step_handler(msg, ask_conv)

    @bot.callback_query_handler(lambda q: q.data == '/converted')
    def ask_conv(call):
        data = select_user(db, table, call.from_user.id, '*')
        send_mail(str(call.from_user.id), data[2],
            data[3], 'Convert', str(call.from_user.id), data[7])

    @bot.callback_query_handler(lambda q: q.data == '/as_is')
    def ask_conv(call):
        data = select_user(db, table, call.from_user.id, '*')
        send_mail(str(call.from_user.id), data[2],
            data[3], ' ', str(call.from_user.id), data[7])

    @bot.callback_query_handler(lambda q: q.data == '/email')
    def email(call):
        msg = bot.send_message(call.from_user.id,
            'Type the e-mail you want to set.')
        bot.register_next_step_handler(msg, add_email)

    @bot.callback_query_handler(lambda q: q.data == '/send')
    def ask_file(call):
        msg = bot.send_message(call.from_user.id,
            'Send me the file or the link to the file.')
        bot.register_next_step_handler(msg, get_file)

    bot.polling(none_stop=True)
