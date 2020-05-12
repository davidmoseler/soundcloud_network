import neomodel as nm
import soundcloud
import configparser
from urllib.parse import urlparse, parse_qs

settings = configparser.ConfigParser()
settings._interpolation = configparser.ExtendedInterpolation()
settings.read('settings.ini')

username = settings.get('neo', 'username')
password = settings.get('neo', 'password')
host = settings.get('neo', 'host')
port = settings.get('neo', 'port')
nm.config.DATABASE_URL = f"bolt://{username}:{password}@{host}:{port}"

client = soundcloud.Client(client_id=settings.get('soundcloud', 'client_id'),
        client_secret=settings.get('soundcloud', 'client_secret'))

class DeepScanning:
    @staticmethod
    def add(id):
        with open('deep_scanned', 'a') as file:
            if not id in DeepScanning.list():
                file.write("{}\n".format(id))

    @staticmethod
    def list():
        with open('deep_scanned', 'r') as file:
            return file.read().splitlines()

    @staticmethod
    def remove(id):
        ids = []
        with open('deep_scanned', 'r') as file:
            ids = file.read().splitlines()
            ids.remove(id)
        with open('deep_scanned', 'w') as file:
            for id in ids:
                file.write(f"{id}\n")


class SoundcloudUser(nm.StructuredNode):
    userid = nm.StringProperty(unique_index=True)
    permalink = nm.StringProperty(unique_index=True)
    first_name = nm.StringProperty()
    last_name = nm.StringProperty()
    description = nm.StringProperty()
    country = nm.StringProperty()
    city = nm.StringProperty()
    followings = nm.RelationshipTo('SoundcloudUser', 'follows')
    followers = nm.RelationshipTo('SoundcloudUser', 'followed_by')
    scanned = nm.BooleanProperty(default=False)
    deep_scanned = nm.BooleanProperty(default=False)
    cursor = nm.StringProperty()

    @classmethod
    def attrs(kls):
        attrs = [x for x in dir(kls) if isinstance(getattr(kls, x), nm.Property)]
        attrs.remove('scanned')
        attrs.remove('deep_scanned')
        attrs.remove('cursor')
        attrs.remove('userid')
        attrs.append('id')
        return attrs

    @classmethod
    def hash(kls, user):
        hsh = {attr: getattr(user, attr) for attr in kls.attrs()}
        hsh['userid'] = hsh['id']
        del hsh['id']
        return hsh

    @classmethod
    def add(kls, user):
        if not SoundcloudUser.nodes.first_or_none() or not SoundcloudUser.nodes.first_or_none(userid=user.id):
            return SoundcloudUser(**kls.hash(user)).save()
        return SoundcloudUser.nodes.get(userid=user.id)

    def add_pages(self, users, callback):
        for user in users.collection:
            user = self.__class__.add(user)
            callback(user)
        if users.next_href:
            self.cursor = parse_qs(urlparse(users.next_href).query)['cursor'][0]
            self.save()
            self.add_pages(client.get(users.next_href), callback)

    def add_followers(self):
        followers = client.get('/users/' + str(self.userid) + '/followers', cursor=self.cursor, page_size=200)
        def callback(user):
            user.followings.connect(self)
            self.followers.connect(user)
        self.add_pages(followers, callback)
        self.cursor = None
        self.save()

    def add_followings(self):
        followings = client.get('/users/' + str(self.userid) + '/followings', cursor=self.cursor, page_size=200)
        def callback(user):
            self.followings.connect(user)
            user.followers.connect(self)
        self.__class__.add_pages(followings, callback)
        self.cursor = None
        self.save()

    def scan(self):
        if not self.scanned:
            print("Soft scanning {}".format(self.permalink))
            self.add_followers()
            self.add_followings()
        self.scanned = True
        self.save()

    def scan_deep(self):
        if not self.deep_scanned and not self.userid in DeepScanning.list():
            DeepScanning.add(self.userid)
            self.scan()
            print("Deep scanning {}".format(self.permalink))
            print("{} followers and {} followings".format(len(self.followers), len(self.followings)))
            for user in self.followers:
                user.scan_deep()
            for user in self.followings:
                user.scan_deep()
            DeepScanning.remove(self.userid)
            self.deep_scanned = True
            self.save()

user = client.get('/resolve', url=settings.get('soundcloud', 'initial_uri'))
user = SoundcloudUser.add(user)
user.scan_deep()
