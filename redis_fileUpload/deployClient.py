#This script palce on the server which need to pull the code. Prod server
#!/usr/bin/python3

import git, os, shutil, redis, time, sys, in_place, re
from pprint import pprint
import socket, smtplib, logging, signal
import traceback
from email.mime.text import MIMEText as text
from time import gmtime, strftime
from daemon import runner
import pwd
import grp

class App():
        client = "rca-prod"
        redis_server = "172.17.1.100"
        alert_email = ['clarity.v.2@katzion.com']


        hostname = socket.gethostname()
        old_version = ''
        new_version = ''

        def __init__(self):
                self.stdin_path = '/dev/null'
                self.stdout_path = '/dev/null'
                self.stderr_path = '/dev/null'
                self.pidfile_path =  '/tmp/deploy.pid'
                self.pidfile_timeout = 5


        def fixPermission(self):
                uid = pwd.getpwnam("www-data").pw_uid
                gid = grp.getgrnam("www-data").gr_gid
                for your_dir in ['/var/www/html']:
                        for root, dirs, files in os.walk(your_dir):
                                for d in dirs:
                                        os.chmod(os.path.join(root, d), 0o755)
                                        os.chown(os.path.join(root, d), uid, gid)
                                for f in files:
                                        os.chmod(os.path.join(root, f), 0o644)
                                        os.chown(os.path.join(root, f), uid, gid)

                os.chmod('/var/www/html', 0o755)

                os.chown('/var/www/html', uid, gid)


        def increment_version(self):
                FILE = "/var/www/access_settings.php"


                with in_place.InPlace(FILE) as file:
                        for line in file:
                                match = re.search(r'define\(\'CURRENT_VERSION\', \'clarity_(2_0_\d+_\d+)\'\)', line)
                                if match:

                                        old_ver = match.group(1)
                                        new_ver = old_ver.split("_")

                                        if int(new_ver[-1]) >= 50:
                                                new_ver[-2] = int(new_ver[-2]) + 1
                                                new_ver[-1] = 0
                                        else:
                                                new_ver[-1] = int(new_ver[-1]) + 1

                                        new_ver = "_".join(map(str, new_ver))

                                        line = line.replace(old_ver, new_ver)

                                        self.old_version = old_ver
                                        self.new_version = new_ver


                                file.write(line)


        def send_email(self, subject, message):
                gmail_user = 'katzion.info@gmail.com'
                gmail_password = 'katz123*'

                sent_from = gmail_user

                subject = self.hostname + ': ' + subject

                m = text(message)

                m['Subject'] = subject
                m['From'] = 'Deployment Alert<' + sent_from + '>'
                m['To'] = ", ".join(self.alert_email)

                try:
                        server = smtplib.SMTP('smtp.gmail.com', 587)
                        server.starttls()
                        server.login(gmail_user, gmail_password)
                        server.sendmail(sent_from, self.alert_email, m.as_string())
                        server.close()

                except Exception as e:
                        msg = "!!!!!!!!!! EXCEPTION !!!!!!!!!"
                        msg = msg + str(e)
                        msg = msg + traceback.format_exc()
                        logger.error(msg)

        def deploy_branch(self, branch):

                logger.info("Deployment started")

                DIR_NAME = "temp_code_dir"
                REMOTE_URL = "git@git.assembla.com:katzion/clarity-2-0.git"

                if os.path.isdir(DIR_NAME):
                        shutil.rmtree(DIR_NAME)

                os.mkdir(DIR_NAME)

                repo = git.Repo.init(DIR_NAME)
                origin = repo.create_remote('origin',REMOTE_URL)
                origin.fetch()

                branches = repo.git.branch("-a").split("\n")

                flag = False

                for b in branches:
                        if b.strip() == 'remotes/origin/' + branch:
                                flag = True

                if flag == False:
                        logger.error("Cannot find branch " + branch)
                        self.send_email("Cannot find branch " + branch, "Deployment failed as branch '%s' was not found." % branch)
                        return


                repo.git.checkout('remotes/origin/' + branch)

                time_stamp = strftime("%Y-%m-%d-%H-%M-%S", gmtime())

                DOCUMENT_ROOT = '/var/www/html'

                shutil.rmtree(DOCUMENT_ROOT)
                shutil.copytree(DIR_NAME, DOCUMENT_ROOT)


                self.increment_version()
                logger.info("Old version" + self.old_version)
                logger.info("New version" + self.new_version)

                self.fixPermission()
                logger.info("Permission fixed")

                logger.info("Deployment finished")
                self.send_email("Deployment success", "Deployment of branch %s was successfull.\n\n Old version: %s\n New version: %s" % (branch, self.old_version, self.new_version))

        def exit(self):
            logger.info("Exiting")
            sys.exit(0)

        def run(self):

                logger.info("Started")

                try:
                        r = redis.StrictRedis(host=self.redis_server, port=6379, password="Xy745wLbE3")

                        p = r.pubsub()
                        p.subscribe(self.client)

                        for message in p.listen():
                                logger.info("Received signal")
                                if message and message['type'] == "message":
                                        logger.info("Received message signal")
                                        branch = message['data']
                                        logger.info("Branch is " + branch.decode("utf-8"))
                                        self.deploy_branch(branch.decode("utf-8"))

                except Exception as e:
                        msg = "!!!!!!!!!! EXCEPTION !!!!!!!!!\n"
                        msg = msg + str(e) + "\n"
                        msg = msg + traceback.format_exc()
                        logger.error(msg)
                        self.send_email("Exception", msg)




# set up logger for daemon
logger = logging.getLogger("Code Deploy")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler = logging.FileHandler('/tmp/deploy.log')
handler.setFormatter(formatter)
logger.addHandler(handler)

app = App()
daemon_runner = runner.DaemonRunner(app)

daemon_runner.daemon_context.files_preserve = [handler.stream]
daemon_runner.daemon_context.signal_map[signal.SIGTERM] = app.exit

daemon_runner.do_action()

