"""

"""

import smtplib
from email.mime.text import MIMEText
from queue import Queue
import threading
import time
import logging


class MailBox(threading.Thread):
    """
    登陆邮箱
    @host, smtp server domain or ip
    @port, smtp server port
    @auth=(USERNAME, PASSWORD), used to login to the smtp server
    @enable_ssl, Use Secure Socket Layer to communicate with the server.
    @enable_tls, Use Transport layer security to communicate with the server; if enable_ssl is used, then this should not be enabled.
    """

    _MAX_QUEUE = 100

    def __init__(self, server, port, auth=("", ""),
                 enable_tls=False,enable_ssl=False,
                 debug=False):
        super().__init__()
        self.server = server
        self.port = port
        self.username = auth[0]
        self.password = auth[1]
        self.enable_tls = enable_tls
        self.enable_ssl = enable_ssl
        self.debug=debug

        self.waiting_queue = Queue(self._MAX_QUEUE)
        self.stop = False
        self._connect()

        
    def send_mail(self, mail, async=False, callback=None):
        """send email
        @async: the mail will be send in the background, when finised, callback will be called.
        """

        # TODO: need more checks of the format
        if not isinstance(mail, Email):
            raise Exception("Mail Format Error")
        mail.callback = callback

        if async:
            self.waiting_queue.put(mail)
            return True

        return self._send_mail(mail)

    def run(self, *args, **kwargs):
        """Background Email Service, send email in the queue
        ! called by threading.Thread, Do not call it yourself.
        """
        while True:
            if self.stop:
                try:
                    self.smtp.quit()
                except:
                    pass
                break
            if self.waiting_queue.empty():
                time.sleep(2)
                continue
            mail = self.waiting_queue.get(False)
            self._send_mail(mail)

    def quit(self, timeout=10):
        self.stop = True
        self.join(timeout)

    def _send_mail(self, mail):
        content_type = "html" if mail.content_type == "html" else "plain"
        msg = MIMEText(mail.content, mail.content_type)
        msg["Subject"] = mail.subject
        msg["From"] = mail.sender
        msg["To"] = ",".join(mail.receivers)

        print(msg.as_string())

        # check if smtp is still alive
        is_alive = True
        try:
            status = self.smtp.noop()[0]
            is_alive = True if status == 250 else False
        except smtp.SMTPServerDisconnected as e:
            is_alive = False
        except Exception as e:
            is_alive = False
            logging.error("Unkown Exception Occured While Ping the smtp server", e)

        if not is_alive:
            logging.info("The smtp Connection is down, tring to reconnect.")
            self._connect()

        try:
            self.smtp.sendmail(msg["From"], msg["To"], msg.as_string())
        except smtplib.SMTPSenderRefused  as e:
            logging.error("Sender Refused for mail: %s", mail)
            return False

        except smtplib.SMTPRecipientsRefused as e:
            logging.error("Recipient Refused for mail: %s", mail)
            return False
        except Exception as e:
            logging.error("Unkown Execption occured: ", e)
            return False

        if mail.callback:
            mail.callback("success", mail)
        return True


    def _connect(self):
        if hasattr(self, "smtp"):
            try:
                self.smtp.quit()
            except:
                pass
        
        if self.enable_ssl:
            self.smtp = smtplib.SMTP_SSL(self.server, self.port)
        else:
            self.smtp = smtplib.SMTP(self.server,self.port)
        
        self.smtp.set_debuglevel(self.debug)
        self.smtp.ehlo()

        if not self.enable_ssl and self.enable_tls:
            self.smtp.starttls()
        if self.username: self.smtp.login(self.username, self.password)

        self.smtp.ehlo()

class Email(object):

    def __init__(self, sender="", receivers=[], subject="", content="",
                 content_type="plain"):
        """
        @sender: sender's email addr, formated as "user@domain.com" or "ALIAS <user@domain.com>"
        @receivers: a list of receivers, each is formated the same as sender
        @content: the content of the mail
        @content_type: html or plain
        """
        self.sender = sender
        self.receivers = receivers
        self.subject = subject
        self.content = content
        self.content_type = content_type

        self.callback = None
        


    
