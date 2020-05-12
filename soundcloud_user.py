import neomodel as nm
import soundcloud
import configparser

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

class DeepScanned:
    @staticmethod
    def add(id):
        with open('deep_scanned', 'a') as file:
            if not id in DeepScanned.list():
                file.write("{}\n".format(id))

    @staticmethod
    def list():
        with open('deep_scanned', 'r') as file:
            return file.read().splitlines()

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
    followings_cursor = nm.StringProperty()
    followers_cursor = nm.StringProperty()

    @classmethod
    def attrs(kls):
        attrs = [x for x in dir(kls) if isinstance(getattr(kls, x), nm.Property)]
        attrs.remove('scanned')
        attrs.remove('followings_cursor')
        attrs.remove('followers_cursor')
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

    @classmethod
    def add_pages(kls, users, callback):
        for user in users.collection:
            user = kls.add(user)
            callback(user)
        if users.next_href:
            file = open('next_href', 'w')
            file.write(str(len(users.collection)))
            file.write(str(users.next_href))
            file.close()
            kls.add_pages(client.get(users.next_href), callback)

    def add_followers(self):
        followers = client.get('/users/' + str(self.userid) + '/followers', cursor=self.followers_cursor)
        def callback(user):
            user.followings.connect(self)
            self.followers.connect(user)
        self.__class__.add_pages(followers, callback)

    def add_followings(self):
        followings = client.get('/users/' + str(self.userid) + '/followings', cursor=self.followings_cursor)
        def callback(user):
            self.followings.connect(user)
            user.followers.connect(self)
        self.__class__.add_pages(followings, callback)

    def scan(self):
        if not self.scanned:
            print("Soft scanning {}".format(self.permalink))
            self.add_followers()
            self.add_followings()
        self.scanned = True
        self.save()

    def scan_deep(self):
        if not self.userid in DeepScanned.list():
            self.scan()
            print("Deep scanning {}".format(self.permalink))
            print("{} followers and {} followings".format(len(self.followers), len(self.followings)))
            for user in self.followers:
                user.scan_deep()
            for user in self.followings:
                user.scan_deep()
            DeepScanned.add(self.userid)

user = client.get('/resolve', url=settings.get('soundcloud', 'initial_uri'))
user = SoundcloudUser.add(user)
user.scan_deep()
