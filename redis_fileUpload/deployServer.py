#Script under the redis server side
#!/usr/bin/python3

from termcolor import colored
import sys, redis

client = "XXXX"
redis_server = "XXX.XXX.XX.XX"

print(colored("Deploying to ", "red") + colored(client, "green"))

branch = input("Enter the branch name: ")

if branch == "":
        print(colored("Enter a valid branch name", "red"))
        sys.exit()

confirm = input("Are you sure to deploy branch " + colored(branch, "yellow") + " (Y/n) ")

if confirm != "Y":
        print(colored("Exiting ...", "red"))
        sys.exit()

try:
        r = redis.StrictRedis(host=redis_server, port=XXX, password="XXXX")

        p = r.pubsub()
        p.subscribe(client)

        r.publish(client, branch)

        print(colored("Request has been queued", "green"))

except Exception as e:
        print("!!!!!!!!!! EXCEPTION !!!!!!!!!")
        print(str(e))
        print(traceback.format_exc())

