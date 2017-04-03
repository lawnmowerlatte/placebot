import urllib
import urllib.request
import time
import json
import random
import sys
import getpass
import argparse

parser = argparse.ArgumentParser(description='Bot for r/place.')
parser.add_argument('image_data',
        help='json (file or url if starting with http(s)://) describing your image')
parser.add_argument('--default-delay', type=int,default=5,
                    help='default sleep interval in minutes (default: 5 minutes)')
parser.add_argument('--username',
                    help='username')
parser.add_argument('--password',
                    help='password')

args = parser.parse_args()

delay_minutes = args.default_delay

class Drawing:
    def __init__(self, pixels, size, location):
        self.pixels = pixels
        self.size = size
        self.location = location
        self.pool = []

        self.xmin = self.location[0]
        self.xmax = self.xmin+self.size[0]-1
        self.ymin = self.location[1]
        self.ymax = self.ymin+self.size[1]-1
        for i in range(self.xmin,self.xmax+1):
            for j in range(self.ymin,self.ymax+1):
                self.pool.append((i,j))
        random.shuffle(self.pool)

    def get_pixel_local(self, x, y):
        if x < 0 or y < 0 or x > self.size[0] or y > self.size[1]:
            return -1
        return self.pixels[x+y*self.size[0]]
    def get_pixel(self, x, y):
        dx = x - self.location[0]
        dy = y - self.location[1]
        return self.get_pixel_local(dx,dy)
    def get_random_pixel(self):
        target_color = -1
        while target_color == -1:
            if len(self.pool) == 0:
                raise Exception("No more pixels")
            x,y = self.pool.pop()
            target_color = self.get_pixel(x, y)
        return x, y, target_color

class Canvas:
    def __init__(self, username, password):
        user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.110 Safari/537.36"

        self.read_opener = urllib.request.build_opener()
        self.read_opener.addheaders = [('User-Agent', user_agent)]

        self.write_opener = urllib.request.build_opener()
        self.write_opener.addheaders = [('User-Agent', user_agent)]

        data = urllib.parse.urlencode({'op': 'login-main', 'user': username,
                                       'passwd': password, 'api_type': 'json'})
        resp = self.read_opener.open('https://www.reddit.com/api/login/' +
                           urllib.parse.quote(username), data.encode()).read()
        print(resp)
        session = json.loads(resp)["json"]["data"]["cookie"]
        self.write_opener.addheaders.append(('Cookie', 'reddit_session=' + session))

        modhash = json.loads(self.write_opener.open(
            "https://www.reddit.com/api/me.json").read())["data"]["modhash"]
        self.write_opener.addheaders.append(('x-modhash', modhash))

        self.map = self.read_opener.open("https://www.reddit.com/api/place/board-bitmap").read()

    def get_pixel(self,x,y):
        color = self.map[y*500+int(x/2)]
        if x%2 == 0:
            color >>= 4
        else:
            color &= 0xF
        return color

    def put_pixel(self,x,y,color):
        data = urllib.parse.urlencode({'x': x, 'y': y, 'color': color})
        draw_api = self.write_opener.open(
            "https://www.reddit.com/api/place/draw.json", data.encode()).read()
        time_to_sleep = json.loads(draw_api).get('wait_seconds', 0)
        if time_to_sleep == 0:
            time_to_sleep = delay_minutes*60
        return time_to_sleep



if args.username:
    username = args.username
else:
    username = input("USERNAME: ")
if args.password:
    password = args.password
else:
    password = getpass.getpass("PASSWORD: ")

def fetch_data(username):
    if "http" in args.image_data:
        data = urllib.request.urlopen(args.image_data+"?user="+username)
    else:
        data = open(args.image_data,"r")
    return json.load(data)

print("Running")
while True:
    try:
        data = fetch_data(username)
        drawing = Drawing(data['pixels'], data['size'], data['location'])
        canvas = Canvas(username, password)
        try:
            x, y, target_color = drawing.get_random_pixel()
            actual_color = canvas.get_pixel(x,y)
            while actual_color == target_color:
                x, y, target_color = drawing.get_random_pixel()
                actual_color = canvas.get_pixel(x,y)
                time.sleep(0.1)
            print("wrong color at", x, y, actual_color, "instead of", target_color)
            time_to_sleep = canvas.put_pixel(x,y,target_color)
            print("fixed")
            time.sleep(time_to_sleep)
        except urllib.error.HTTPError as httperr:
            print(httperr)
            if httperr.code == 429:
                print("Requesting too soon, let's sleep a bit (", delay_minutes, " minutes)...")
                time.sleep(delay_minutes*60)
            if httperr.code == 403:
                print(canvas.write_opener.addheaders)
                print("Auth error, exiting...")
                exit(1)
            else:
                print("Unknown problem, going on...")
    except KeyError as k:
        print(k)
        print("Check username/password")
        exit(1)
    except Exception as e:
        print("this is unexpected, maybe investigate!")
        print(e)

    # rest a bit
    time.sleep(1)

