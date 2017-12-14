from telebot import types
from cryptography.fernet import Fernet, MultiFernet
import qrcode,math,telebot,zbarlight,base64,os
import numpy as np
from baseconv import base2
from PIL import Image
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import MySQLdb
hostname = 'mysql-hostname'
username = 'mysql-username'
passw = 'mysql-passw'
database = 'mysql-database'

'''cur = conn.cursor()
cur.execute('CREATE TABLE data ( userid varchar(25),file_add varchar(255),pass_qr varchar(255),todo varchar(2))')
conn.commit()
'''

bot = telebot.TeleBot("telegram-bot-token")
print("bot is up .... ")
def sql():
    conn = MySQLdb.connect( host=hostname, user=username, passwd=passw, db=database)
    return  conn, conn.cursor()
@bot.message_handler(content_types=["document","photo","text"])
def a(message):
    conn,cur=sql()
    if message.content_type=="document":
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        with open(message.document.file_name, 'wb') as new_file:
            new_file.write(downloaded_file)
        markup=types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Encrypt",callback_data="En_%s,%s"%(str(message.chat.id),message.document.file_name)),
                    types.InlineKeyboardButton("Decrypt",callback_data="De_%s,%s"%(str(message.chat.id),message.document.file_name)))
        bot.send_message(message.chat.id,"what do you want to do ?!",reply_to_message_id=message.message_id,reply_markup=markup)
    elif message.content_type=="photo":
        cur.execute("SELECT * FROM data where userid='%s';"%str(message.chat.id))
        r=cur.fetchall()
        if len(r)>0:
            userid=r[0][0]
            file_add=r[0][1]
            if r[0][3]=="dQ":
                try:    
                    bot.reply_to(message,"processing please wait ....")
                    file_info=bot.get_file(message.photo[-1].file_id)
                    downloaded_file = bot.download_file(file_info.file_path)
                    with open(str(message.chat.id)+'.jpg', 'wb') as new_file:
                        new_file.write(downloaded_file)
                    with open(str(message.chat.id)+'.jpg', 'rb') as image_file:
                        image = Image.open(image_file)
                        image.load()
                    codes = zbarlight.scan_codes('qrcode', image)
                    key2 = Fernet(codes[0])
                    f = MultiFernet([key2])
                    img = Image.open(file_add)
                    arr = np.array(img)
                    temp='';token=''
                    for row in arr:
                        for p in row:
                            if int(p[0])+int(p[1])+int(p[2]) <382:
                                temp+='0'
                            else:
                                temp+='1'
                            if len(temp)==8:
                                token+= chr(int(base2.decode(temp)))
                                temp=''
                    a=f.decrypt(str.encode(token))
                    w=open('de_'+file_add,'wb')
                    w.write(a)
                    w.close()
                    bot.send_photo(userid,open('de_'+file_add,'rb'))
                    os.remove(file_add)
                    os.remove(str(message.chat.id)+'.jpg')
                    os.remove('de_'+file_add)
                except Exception as e:
                    bot.reply_to(message,"QR-key is wrong...")
                    os.remove(file_add)
                    os.remove(str(message.chat.id)+'.jpg')
                
        else:
            bot.reply_to(message ,"?!!...")
    elif message.content_type=="text":
        cur.execute("SELECT * FROM data where userid='%s';"%str(message.chat.id))
        r=cur.fetchall()
        if len(r)>0:
            bot.reply_to(message,"processing please wait ....")
            userid=r[0][0]
            file_add=r[0][1]
            password = str.encode(message.text)
            salt = b'01s39*-/ q2@1z6!'
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend())
            key = base64.urlsafe_b64encode(kdf.derive(password))
            f = MultiFernet([Fernet(key)])
            if r[0][3]=="de":                
                img = Image.open(file_add)
                arr = np.array(img)
                temp='';token=''
                for row in arr:
                    for p in row:
                        if int(p[0])+int(p[1])+int(p[2]) <382:
                            temp+='0'
                        else:
                            temp+='1'
                        if len(temp)==8:
                            token+= chr(int(base2.decode(temp)))
                            temp=''
                try:
                    a=f.decrypt(str.encode(token))
                    w=open('de_%s'%file_add,'wb')
                    w.write(a)
                    w.close()
                    bot.send_photo(userid,open('de_%s'%file_add,'rb'))
                    os.remove(file_add)
                    os.remove('de_'+file_add)
                except Exception as e:
                    bot.reply_to(message,"passkey is wrong...")
                    os.remove(file_add)
            elif r[0][3]=="en":
                w=open(file_add,'rb')
                b = f.encrypt(w.read())
                h=int(math.sqrt(len(b)*8)+1)
                data = np.zeros((h, h, 3), dtype=np.uint8)
                i=0;j=0
                for byte in b:
                    if len(base2.encode(byte))<8:
                        a="00000000"+base2.encode(byte)
                        a=a[len(a)-8:len(a)]
                        for bit in a:
                            if bit=='1':
                                data[j,i]=(255,255,255)
                            else:
                                data[j,i]=(bit,bit,bit)
                            if i+1<h:
                                i+=1
                            else:
                                i=0
                                j+=1
                img = Image.fromarray(data,"RGB")
                img.save('en_%s'%file_add)
                bot.send_document(userid,open('en_%s'%file_add,'rb'),caption="")
                os.remove(file_add)
                os.remove('en_%s'%file_add)
            cur.execute("DELETE FROM data WHERE userid='%s';"%str(userid))
            conn.commit()
        else:
            bot.reply_to(message ,"?!!...")
@bot.callback_query_handler(func=lambda call: True)
def  test_callback(call):
    conn,cur=sql()
    if str(call.data.split(',')[0]).count('En_')==1:
        userid=int(call.data.split(',')[0].replace('En_',''))
        file_add=str(call.data.split(',')[1])
        markup=types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Generate a QR-key.",callback_data="eNQR_%s,%s"%(str(userid),file_add)),
                    types.InlineKeyboardButton("I have a passkey.",callback_data="eNP_%s,%s"%(str(userid),file_add)))
        bot.edit_message_text("What is your choice ...",userid,call.message.message_id,reply_markup=markup)
    elif str(call.data.split(',')[0]).count('eNP_')==1:
        userid=int(call.data.split(',')[0].replace('eNP_',''))
        file_add=str(call.data.split(',')[1])
        bot.edit_message_text("send me your key ...",userid,call.message.message_id,reply_markup=None)
        cur.execute("SELECT * FROM data WHERE userid=%s;"%str(userid))
        r=cur.fetchall()
        if len(r)>0:
            cur.execute("UPDATE data SET file_add='%s',todo='en' WHERE userid=%s;"%(file_add,str(userid)))
            conn.commit()
        else:
            cur.execute("INSERT INTO data (userid,file_add,todo)VALUES('%s','%s','en');"%(str(userid),file_add)
            conn.commit()
    elif str(call.data.split(',')[0]).count('eNQR_')==1:
        userid=int(call.data.split(',')[0].replace('eNQR_',''))
        file_add=str(call.data.split(',')[1])
        bot.edit_message_text("processing please wait ....",userid,call.message.message_id)
        a=Fernet.generate_key()
        img = qrcode.make(a)
        img.save(str(userid)+".png")
        f = MultiFernet([Fernet(a)])
        w=open(file_add,'rb')
        b = f.encrypt(w.read())
        h=int(math.sqrt(len(b)*8)+1)
        data = np.zeros((h, h, 3), dtype=np.uint8)
        i=0;j=0
        for byte in b:
            if len(base2.encode(byte))<8:
                a="00000000"+base2.encode(byte)
                a=a[len(a)-8:len(a)]
                for bit in a:
                    if bit=='1':
                        data[j,i]=(255,255,255)
                    else:
                        data[j,i]=(bit,bit,bit)
                    if i+1<h:
                        i+=1
                    else:
                        i=0
                        j+=1
        img = Image.fromarray(data,"RGB")
        img.save(file_add)
        bot.send_document(userid,open(file_add,'rb'),caption="")
        bot.send_photo(userid,open(str(userid)+".png",'rb'),caption="")
        os.remove(file_add)
        os.remove(str(userid)+".png")
    elif str(call.data.split(',')[0]).count('De_')==1:
        userid=int(call.data.split(',')[0].replace('De_',''))
        file_add=str(call.data.split(',')[1])
        markup=types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("I have a QR-key.",callback_data="dEQR_%s,%s"%(str(userid),file_add),
                    types.InlineKeyboardButton("I have a passkey.",callback_data="dEP_%s,%s"%(str(userid),file_add))
        bot.edit_message_text('What is your choice ...',userid,call.message.message_id,reply_markup=markup)
    elif str(call.data.split(',')[0]).count('dEQR_')==1:
        userid=int(call.data.split(',')[0].replace('dEQR_',''))
        file_add=str(call.data.split(',')[1])
        bot.edit_message_text("send me QR-key as a 'Photo'",userid,call.message.message_id,reply_markup=None)
        cur.execute("SELECT * FROM data WHERE userid=%s;"%str(userid))
        r=cur.fetchall()
        if len(r)>0:
            cur.execute("UPDATE data SET file_add='%s',todo='dQ' WHERE userid=%s;"%(file_add,str(userid)))
            conn.commit()
        else:
            cur.execute("INSERT INTO data (userid,file_add,todo)VALUES('%s','%s','dQ');"%(str(userid),file_add)
            conn.commit()
    elif str(call.data.split(',')[0]).count('dEP_')==1:
        userid=int(call.data.split(',')[0].replace('dEP_',''))
        file_add=str(call.data.split(',')[1])
        bot.edit_message_text("send me passkey",userid,call.message.message_id,reply_markup=None)
        cur.execute("SELECT * FROM data WHERE userid=%s;"%str(userid))
        r=cur.fetchall()
        if len(r)>0:
            cur.execute("UPDATE data SET file_add='%s',todo='de' WHERE userid=%s;"%(file_add,str(userid)))
            conn.commit()
        else:
            cur.execute("INSERT INTO data (userid,file_add,todo)VALUES('%s','%s','de');"%(str(userid),file_add)
            conn.commit()
bot.polling()
